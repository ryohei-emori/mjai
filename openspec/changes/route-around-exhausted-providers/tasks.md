## 1. Storage for shared availability

- [x] 1.1 Add `backend/supabase/migrations/008_provider_health.sql`: `(provider, model, credential_fingerprint)` primary key, recovery instant, reason, observed-at, RLS matching the other tables
- [x] 1.2 Add availability DAO to `db_helper.py`: read all still-valid rows, and upsert one row resolving concurrent writers with `GREATEST` on the recovery instant
- [x] 1.3 Treat a missing table as "no shared knowledge" on both read and write

## 2. Availability module

- [x] 2.1 Add `backend/app/llm/provider_health.py` with the snapshot type, a fingerprint that hashes the credential rather than storing it, and the wall-clock ↔ monotonic conversion at the boundary
- [x] 2.2 Seed the in-process cooldowns from a snapshot, scoped per model exactly as `_cooldown_key` does
- [x] 2.3 Record a refusal only when the remaining request budget allows, bounded by a short timeout, never raising
- [x] 2.4 Clamp a provider's retry hint to the 15-minute maximum, and fall back to the existing default when there is no hint

## 3. Parse what the providers tell us

- [x] 3.1 Parse `retry-after` (seconds or HTTP date) and `x-ratelimit-reset-*` from Groq responses
- [x] 3.2 Parse Gemini's `RetryInfo.retryDelay` from a 429 body
- [x] 3.3 Carry the parsed hint on the provider error so the caller can record it without re-reading the response
- [x] 3.4 Pass the hint to `mark_cooldown` so in-process cooldown matches the recorded one

## 4. Route around what is known to be unavailable

- [x] 4.1 Expose "are all of this provider's credentials cooled down, and until when" from the key pool
- [x] 4.2 Skip a fully-refused provider in the chain without calling it, with a reason naming the expected recovery time and whether it was learned earlier
- [x] 4.3 Keep preference order among the providers that remain
- [x] 4.4 Exclude a skipped provider from `_later_provider_reserve` so a usable provider gets the time the skipped one would have held
- [x] 4.5 Always attempt the soonest-recovering credential when every provider looks unavailable

## 5. Wire it into the request

- [x] 5.1 Read the prompt override and the availability snapshot on one connection, under one timeout, with one fallback
- [x] 5.2 Seed cooldowns from that snapshot before generation starts
- [x] 5.3 Record refusals observed during generation, subject to 2.3

## 6. Tests

- [x] 6.1 A snapshot from a previous request prevents a call to the recorded credential; an expired entry does not
- [x] 6.2 Model-scoped: a refusal on one model leaves the sibling model selectable with the same key
- [x] 6.3 A short provider hint is honored; a long one is capped; a missing one falls back to the default
- [x] 6.4 A fingerprint identifies a credential without containing it
- [x] 6.5 Missing table, unreachable database, and slow read each degrade to today's behavior
- [x] 6.6 An exhausted primary is skipped without a call and the next provider answers
- [x] 6.7 Preference order is preserved when both providers are usable
- [x] 6.8 Every provider recorded unavailable still produces one attempt, against the soonest-recovering one
- [x] 6.9 The prompt and availability reads share one connection
- [x] 6.10 A refusal observed with little budget left is not recorded, and the response does not overrun the deadline
- [x] 6.11 The breakdown distinguishes not-configured, learned-limit-with-recovery-time, and skipped-for-time
- [x] 6.12 Run backend pytest (421 passed, 1 skipped), frontend jest (278 passed), `tsc`, and lint

Also added, because the state these tests rely on is process-global and now decides
which provider the chain calls: an autouse `conftest.py` fixture clearing credential
cooldowns and buffered observations between tests, and endpoint-level tests that the
`/suggestions` handler actually reads the snapshot, seeds from it, and writes back —
the wiring whose absence would leave everything above inert.

## 7. Docs

- [x] 7.1 `AGENTS.md`: the shared availability table, what it does and does not do about quota, the 15-minute clamp, the always-one-attempt guard, and that availability never reorders providers
- [x] 7.2 `docs/SYSTEM-DESIGN.md`: availability as distinct from the wall-clock budget, the `provider_health` table, and six rejected alternatives (pre-flight quota query, shared consumption counter, latency reordering/hedging, memory-only cooldowns, Redis/KV, treating records as authoritative)
- [x] 7.3 Note the new migration in the deploy-ordering guidance (all three recent migrations are order-independent by design, and the reason each is still worth applying)

## 8. Live verification (needs a deployed build)

- [ ] 8.1 After deploy, confirm a generation succeeds and that a subsequent forced rate limit shows the learned-skip reason with a recovery time
- [ ] 8.2 Confirm the availability read adds no visible latency to a healthy generation
