## Why

Today every serverless invocation re-discovers which providers are usable by *spending a request on each one*. The credential cooldown that records "this key is rate-limited" lives in process memory (`key_pool.py`), and Vercel gives each invocation a fresh isolate, so the knowledge is thrown away between requests. A user whose Gemini free-tier quota is exhausted pays for that discovery on every single generation: Gemini is called, every pooled key returns 429, and only then does Groq get asked — for as long as the quota stays exhausted.

The waiting this causes is smaller than it looks, and worth measuring before designing for it. A quota-exhausted provider answers **fast** (a 429 is a few hundred milliseconds), so the wasted time is roughly 0.3–1s per pooled key, not tens of seconds. The tens of seconds come from a provider that is *working but slow*, and that case is already handled by the phase deadlines in `fix-function-invocation-timeout`. So the honest scope here is: remove the repeated, pointless round trips; stop treating a fixed 60s as the recovery time when the provider told us the real one; and make the failure legible when everything genuinely is exhausted.

There is a second reason this matters more than a second of latency. Those wasted 429s are **counted against the quota that is already exhausted**, and the fixed 60s cooldown is wrong in both directions: too long when the provider says "retry after 8s" (we skip a provider that has already recovered) and far too short when a daily request limit is spent (we re-burn a 429 every minute for the rest of the day).

None of the three providers offers a free way to *ask* how much quota is left — there is no pre-flight quota endpoint, and probing costs exactly the request we are trying to save. But all of them **tell us on the way out**: Groq returns `retry-after` and `x-ratelimit-*` headers, Gemini's 429 carries a `RetryInfo` retry delay. The design principle follows from that: **do not ask in advance, remember what you were told.**

## What Changes

- **Provider availability becomes shared and durable.** A new `provider_health` table records, per provider / model / credential, when a credential is expected to be usable again and why. Every invocation reads one snapshot and seeds the existing in-process cooldowns from it, so a fresh isolate starts out knowing what the previous one learned.
- **The chain sends requests only to providers that are not known to be unavailable**, keeping the existing quality-first order (Gemini → Groq → Cloudflare) among those that remain. A provider whose entire credential pool is in shared cooldown is skipped without a call.
- **Recovery time comes from the provider, not from a constant.** `retry-after` / `x-ratelimit-reset-*` / Gemini `RetryInfo` are parsed and honored, replacing the fixed 60s where a hint exists. Hints are clamped to a maximum so a bad or hostile value cannot disable a provider for a day.
- **One real attempt is always made.** If every credential looks unavailable, the chain still tries the one whose cooldown expires soonest, so stale shared state can never take the feature offline.
- **No extra database round trip on the hot path.** The availability snapshot is read on the same connection as the stored prompt, which the request already opens.
- **Failures say which kind of "no" it was.** The per-provider breakdown distinguishes "key not configured" from "all 2 keys were already known to be rate-limited, expected usable in 42s", so triage does not need server logs.
- **Availability recording never fails a request.** A missing table, an unreachable database, or a slow write degrades to exactly today's behavior: in-process cooldowns only.

Not changing: provider preference order, the wall-clock budget and phase deadlines, provider timeouts, prompts, the response schema, and the offline WebLLM toggle.

## Capabilities

### New Capabilities
<!-- None: this extends two existing capabilities rather than introducing one. -->

### Modified Capabilities

- `llm-api-key-pool`: credential availability MUST survive beyond one invocation, MUST derive its duration from the provider's own retry hint within a bounded maximum, and MUST degrade to in-process-only when the shared store is unavailable.
- `ai-suggestions`: the failover chain MUST skip providers whose credentials are all known unavailable rather than calling them, MUST still make one attempt when everything looks unavailable, MUST NOT add a database round trip or a new failure mode to the generation path, and MUST report a learned skip distinctly from a missing configuration.

## Impact

- **New**: `backend/app/llm/provider_health.py`, `backend/supabase/migrations/008_provider_health.sql`, tests for both.
- **Modified**: `backend/app/llm/key_pool.py` (seed cooldowns from a snapshot; accept a duration hint), the three providers (parse retry hints, record observations), `backend/app/llm/suggestions.py` (skip fully-unavailable providers, distinct skip reason, availability-aware phase reserve), `backend/app/main.py` (read the snapshot with the prompt on one connection), `backend/app/db_helper.py` (availability DAO).
- **Database**: one new table. Deploy order is safe in both directions — the code treats the table's absence as "no shared knowledge".
- **Frontend**: no API contract change; the richer skip reason flows through the existing per-provider breakdown.
- **Quota**: strictly fewer provider requests than today. No new outbound calls are introduced.
