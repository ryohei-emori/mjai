## Context

See `proposal.md` — Why. What matters for the design:

- `key_pool.py` already has the selection behavior we want: `_acquire()` round-robins among credentials that are not cooled down, and `mark_cooldown(cred_id, seconds, scope=model)` records a refusal on a monotonic clock. The only defect is where that state lives — a module-level dict in a process that Vercel discards after the response.
- The generation request already opens one Postgres connection before calling any provider, to read the stored system prompt (`resolve_system_prompt_override()`). That existing round trip is the budget we have to work inside.
- `fix-function-invocation-timeout` established the wall-clock rules this must not violate: the deadline is taken at request entry, every outbound call is sized to what is left, and `_later_provider_reserve()` holds back time for the providers still to come.
- Providers report retry timing in different shapes: Groq sends `retry-after` and `x-ratelimit-reset-requests` headers, Gemini returns a `RetryInfo` entry with a `retryDelay` inside a 429 body, Cloudflare sends neither reliably. None offers a free quota pre-flight.

Terminology, to avoid a collision with the previous change: **budget** means wall-clock time (`budget.py`); **availability** or **health** means provider quota and credential state. The two are independent — a provider can be available but too slow to fit, or fast but exhausted.

## Goals / Non-Goals

**Goals**

- A fresh invocation starts with what previous invocations learned about credential refusals.
- A provider whose whole pool is refused is skipped without a request.
- Cooldown duration reflects what the provider actually said, bounded.
- Zero added connections on the generation path, and no new way for generation to fail.

**Non-Goals**

- **Reordering providers by observed latency.** Preference order encodes critique quality, not speed. Demoting Gemini because it has been slow would trade the output quality this project has spent several changes tuning for a few seconds, silently and without the user asking. Slowness is already handled by phase deadlines, which give the secondary its turn without giving up on the primary. Within a provider, preferring the healthier of two sibling models is in scope, because that is an availability decision with no quality trade-off.
- **Predicting remaining quota.** We record refusals we were told about; we do not model consumption or count requests toward a limit we cannot see. A counter maintained by many stateless isolates would drift, and drift here means either skipping a working provider or a false sense of headroom.
- **Probing providers to check health.** A probe costs a request against the quota it is checking, and tells us only about the moment it ran.
- **Cross-request coordination.** Two concurrent requests may both discover the same refusal. That is one wasted call, not a correctness problem, and locking to prevent it would cost more than it saves.

## Decisions

### Persist availability in Postgres, keyed by provider / model / credential fingerprint

Postgres is already a hard dependency of the request, so the read costs no new connection and no new service. The alternatives were worse for this repo: Redis or a KV store fits TTL state better but adds an external dependency, which `AGENTS.md` requires reviewing infrastructure changes for and which is disproportionate for one small table; a Vercel edge config or file is either write-hostile or per-instance, which is the problem we are fixing.

The row key is `(provider, model, credential_fingerprint)`, mirroring the scoping the in-process cooldown already uses (`_cooldown_key`): Groq and Gemini limits are per model, so a 429 on one model must not withhold the key from its sibling. `model` is empty for providers whose limits are credential-wide (Cloudflare).

The fingerprint is a short hash of the credential, never the credential. A pool index would be shorter but is positional — reordering `GEMINI_API_KEYS` would silently re-point every row at a different key.

### Seed the existing in-process cooldowns from the snapshot, rather than consulting the store during selection

The alternative — teaching `_acquire()` to check shared state — would put a database call inside credential selection, which happens inside the provider retry loop, on the hot path, under a wall-clock deadline. Instead the request reads one snapshot up front and calls `mark_cooldown()` for each still-valid entry. Selection logic is then untouched, and every existing behavior (round-robin, model scoping, exclusion of already-tried keys) applies unchanged to shared knowledge.

This requires converting the stored wall-clock instant into the monotonic deadline `mark_cooldown` expects, at seed time. Monotonic clocks are per-process and cannot be stored; wall-clock instants cannot be compared to a monotonic deadline. The conversion happens once, at the boundary, which is the only place both clocks are in hand.

### Read availability on the connection the prompt lookup already opens

`resolve_system_prompt_override()` currently opens its own connection. We replace the two independent reads with one function that opens a single connection and returns both the prompt override and the availability snapshot. Connection setup through the Supabase pooler dominates the cost of either query, so this keeps the request at one connect while adding a second cheap `SELECT`, and it holds the whole thing under one short timeout with one fallback: on any failure, default prompt and empty snapshot — today's behavior exactly.

### Record a refusal only when the request can afford it

Writing costs a connection on a path that has already failed. The write is therefore attempted only when a meaningful amount of the request budget remains, and is bounded by a short timeout. Skipping the write is cheap to be wrong about: the next request re-learns the refusal, which is exactly today's behavior. Missing a write is a lost optimization; overrunning the deadline to perform one is the bug class the previous change existed to remove.

Upserts resolve concurrent writers with `GREATEST(existing, new)` on the recovery instant, so two isolates recording the same refusal converge rather than shortening each other's cooldown.

### Honor the provider's retry hint, clamped to 15 minutes

A stated hint is strictly better information than a constant. The clamp exists because free-tier daily limits produce hints measured in hours, and trusting one means a single 429 can withhold a provider until tomorrow — including when the hint is wrong, or the key is replaced, or the limit is lifted. Re-checking every 15 minutes costs one fast 429, which is negligible; being wrong for a day is not. The clamp is deliberately the conservative direction: we would rather waste one round trip than lose a provider.

### Always attempt the soonest-recovering provider when everything looks unavailable

Without this, one bad record can take generation offline for the life of that record — a worse failure than the one this change fixes, because it is caused by our own cache rather than by the provider. Attempting the soonest-recovering credential keeps a lower bound of one real attempt per request while still preferring the most plausible candidate. It also self-heals: a successful call means the record expires unused, and a genuine refusal re-records with fresh timing.

### Report the skip reason, including when recovery is expected

`fix-suggestion-retry-budget-hard-failure` established that the per-provider breakdown is the first thing to ask for when triaging. A learned skip is a fourth category alongside not-configured, failed, and skipped-for-time, and it implies a different action (wait, or add a key from a different project) than the others. The reason states the expected recovery time and whether the refusal was learned in this request or carried over from an earlier one, so a skip that happened without any call in this request is visible as such. Each cooldown entry therefore records its origin alongside its expiry, which is cheaper than storing an observation timestamp and is the distinction the reader actually acts on.

## Risks / Trade-offs

- **A wrong or stale record withholds a working provider** → Three bounds: records expire on their own, hints are clamped to 15 minutes, and one real attempt is always made against the soonest-recovering credential. The worst case is one preference step of quality for at most 15 minutes, not an outage.
- **The availability read adds latency to every generation** → It shares the connection the prompt read already opens, so the added cost is one indexed `SELECT` on a table with tens of rows. It is inside the same short timeout as the prompt read, and the wall-clock deadline already covers the whole handler.
- **A new table means a deploy where code and schema disagree** → Both directions are safe: absent table is treated as "no shared knowledge" (today's behavior), and the table with older code is simply unread. Same pattern as `app_settings` in migration 006.
- **Recording refusals writes to the database on a failure path** → Bounded by remaining budget and a short timeout, and skipped rather than allowed to delay a response. The write happens on the rare path only; success never writes.
- **Rows accumulate** → Cardinality is bounded by providers × models × credentials, which is tens of rows, and rows are overwritten rather than appended. No cleanup job is warranted; a stale row is inert once its recovery instant has passed.
- **Fewer requests reach the primary, so quota problems become less visible** → The breakdown states when a provider was skipped for a known limit, and the skip reason includes the recovery time, so the condition is more legible than today's silent per-request 429, not less.

## Migration Plan

1. Apply `008_provider_health.sql` to the shared Supabase project. The merge-triggered migration workflow does this; applying it early is harmless because nothing reads the table until the new code deploys.
2. Deploy. With the table present, the first refusal populates it and subsequent requests route around it; with the table absent, behavior is identical to today.
3. Rollback is a code revert. The table can be left in place — it is inert without the code that reads it, and it holds no user data.
