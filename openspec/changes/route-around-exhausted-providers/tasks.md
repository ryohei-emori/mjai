## 1. Storage for shared availability

- [ ] 1.1 Add `backend/supabase/migrations/008_provider_health.sql`: `(provider, model, credential_fingerprint)` primary key, recovery instant, reason, observed-at, RLS matching the other tables
- [ ] 1.2 Add availability DAO to `db_helper.py`: read all still-valid rows, and upsert one row resolving concurrent writers with `GREATEST` on the recovery instant
- [ ] 1.3 Treat a missing table as "no shared knowledge" on both read and write

## 2. Availability module

- [ ] 2.1 Add `backend/app/llm/provider_health.py` with the snapshot type, a fingerprint that hashes the credential rather than storing it, and the wall-clock ↔ monotonic conversion at the boundary
- [ ] 2.2 Seed the in-process cooldowns from a snapshot, scoped per model exactly as `_cooldown_key` does
- [ ] 2.3 Record a refusal only when the remaining request budget allows, bounded by a short timeout, never raising
- [ ] 2.4 Clamp a provider's retry hint to the 15-minute maximum, and fall back to the existing default when there is no hint

## 3. Parse what the providers tell us

- [ ] 3.1 Parse `retry-after` (seconds or HTTP date) and `x-ratelimit-reset-*` from Groq responses
- [ ] 3.2 Parse Gemini's `RetryInfo.retryDelay` from a 429 body
- [ ] 3.3 Carry the parsed hint on the provider error so the caller can record it without re-reading the response
- [ ] 3.4 Pass the hint to `mark_cooldown` so in-process cooldown matches the recorded one

## 4. Route around what is known to be unavailable

- [ ] 4.1 Expose "are all of this provider's credentials cooled down, and until when" from the key pool
- [ ] 4.2 Skip a fully-refused provider in the chain without calling it, with a reason naming the expected recovery time and the record's age
- [ ] 4.3 Keep preference order among the providers that remain
- [ ] 4.4 Exclude a skipped provider from `_later_provider_reserve` so a usable provider gets the time the skipped one would have held
- [ ] 4.5 Always attempt the soonest-recovering credential when every provider looks unavailable

## 5. Wire it into the request

- [ ] 5.1 Read the prompt override and the availability snapshot on one connection, under one timeout, with one fallback
- [ ] 5.2 Seed cooldowns from that snapshot before generation starts
- [ ] 5.3 Record refusals observed during generation, subject to 2.3

## 6. Tests

- [ ] 6.1 A snapshot from a previous request prevents a call to the recorded credential; an expired entry does not
- [ ] 6.2 Model-scoped: a refusal on one model leaves the sibling model selectable with the same key
- [ ] 6.3 A short provider hint is honored; a long one is capped; a missing one falls back to the default
- [ ] 6.4 A fingerprint identifies a credential without containing it
- [ ] 6.5 Missing table, unreachable database, and slow read each degrade to today's behavior
- [ ] 6.6 An exhausted primary is skipped without a call and the next provider answers
- [ ] 6.7 Preference order is preserved when both providers are usable
- [ ] 6.8 Every provider recorded unavailable still produces one attempt, against the soonest-recovering one
- [ ] 6.9 The prompt and availability reads share one connection
- [ ] 6.10 A refusal observed with little budget left is not recorded, and the response does not overrun the deadline
- [ ] 6.11 The breakdown distinguishes not-configured, learned-limit-with-recovery-time, and skipped-for-time
- [ ] 6.12 Run backend pytest, frontend jest, `tsc`, and lint

## 7. Docs

- [ ] 7.1 `AGENTS.md`: the shared availability table, what it does and does not do about quota, the 15-minute clamp, and the always-one-attempt guard
- [ ] 7.2 `docs/SYSTEM-DESIGN.md`: availability as distinct from the wall-clock budget, plus the alternatives rejected here
- [ ] 7.3 Note the new migration in the migration/deploy ordering guidance

## 8. Live verification (needs a deployed build)

- [ ] 8.1 After deploy, confirm a generation succeeds and that a subsequent forced rate limit shows the learned-skip reason with a recovery time
- [ ] 8.2 Confirm the availability read adds no visible latency to a healthy generation
