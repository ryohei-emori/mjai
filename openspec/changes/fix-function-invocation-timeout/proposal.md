## Why

Production now reports Vercel's `FUNCTION_INVOCATION_TIMEOUT` (a platform 504) on `POST /api/suggestions`. That response is strictly worse than any app-level failure: it carries no per-provider breakdown, no `timed_out` flag, no pool sizes, and no partially generated critique — the exact diagnostics `fix-suggestion-retry-budget-hard-failure` had just added are unreachable, because the function never got to return.

The wall-clock budget was supposed to make this impossible, but it only bounded **when** a provider call could start, never **when it could finish**:

- `_raise_if_wall_clock_exceeded()` asked "has the deadline already passed?". Every provider then called with its own static timeout — Gemini 22s, Groq 25s, Cloudflare 20s — regardless of how little budget was left.
- So a Groq call could legitimately start at t=44s (44 < 55, the check passed) and run to t=69s. Two Gemini timeouts followed by one Groq timeout is 22+22+25 = 69s against a 60s `maxDuration`, and nothing exotic is needed to reach it.
- The sibling-model gate added by the previous change did not close this. It was computed *before* the first attempt, from the budget available then, so it could not know how much that attempt would actually spend. On a 45s-class budget the first Gemini attempt still left the gate satisfied and the second one starved Groq entirely.
- Each pooled credential also received a fresh full timeout, so an N-key pool cost up to N × the provider timeout inside one phase.

Two smaller contributors to the same overrun:

- The budget started inside `generate_suggestions()`, so the stored-prompt lookup (up to 3s), JWT verification and cold start were outside it while still counting against `maxDuration`. A 55s budget left ~5s for all of that.
- `asyncpg.connect()` was called with no timeout, and asyncpg's default is 60s — precisely the platform limit. An unreachable or paused Supabase turned every DB route into a 504 with nothing in the response naming the database as the cause.

## What Changes

- Every outbound provider call is sized to the budget that is actually left (`budget.resolve_call_timeout`), and that value is a hard ceiling on the attempt — enforced with `asyncio.wait_for`, because httpx applies its timeout per operation and connect plus read can each take the full value.
- A provider whose remaining slice is shorter than its own measured latency is skipped rather than started: a 3s call to a model that answers in 10s is not an attempt, it is a way to spend the seconds a faster provider downstream still needs. Each provider declares that minimum (`GEMINI_MIN_SLICE_S` 10s, `GROQ_MIN_SLICE_S` 5s, `CF_MIN_SLICE_S` 6s) from measured latency.
- Each provider gets a **phase deadline**: the request deadline minus what the providers after it need to get a turn. Every attempt inside the phase — first model, sibling model, each pooled credential — is re-checked against the clock, so a first attempt that overran cannot leave the chain committed to a call the budget can no longer cover. This replaces the `allow_model_retry` flag entirely: one mechanism, decided from elapsed time rather than predicted before the fact.
- The pooled-credential loops share the phase deadline, so N keys cost at most the phase, not N × the timeout.
- The request budget is derived from the platform limit rather than hand-picked (`SUGGESTIONS_WALL_CLOCK_S = PLATFORM_MAX_DURATION_S − PLATFORM_RESERVE_S`, 60 − 15 = 45s) and is measured from **request entry**, so the stored-prompt lookup counts against the same limit as the LLM calls. A test asserts `PLATFORM_MAX_DURATION_S` still equals `vercel.json`.
- A failure caused by the budget — a skipped provider, or one that answered late on a clamped slice — reports `timed_out`, so the user is advised to retry instead of to check credentials.
- `asyncpg.connect()` is bounded (8s connect, 15s command), so a database outage surfaces as a fast, legible error instead of a platform timeout.
- The frontend names a platform timeout in Japanese instead of displaying `FUNCTION_INVOCATION_TIMEOUT`, for the residual case where the invocation itself overruns.

Deliberately unchanged: failover order, each provider's own timeout constant, prompt rules and few-shot, response schema, retry-pass semantics from the previous change, and オフラインモード gating.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: a suggestion request MUST complete within the platform function limit, which requires that no outbound call be started that cannot finish inside the remaining budget, that a provider too poor in remaining time be skipped rather than started, that a slow provider not consume the turn of the ones after it, and that a budget-caused failure be reported as such.

## Impact

- `backend/app/llm/budget.py` (new: shared deadline arithmetic, platform limit and reserve)
- `backend/app/llm/suggestions.py` (phase budgets replace the pass/return-time guard; budget derived from the platform limit; `timed_out` on budget-constrained failures)
- `backend/app/llm/gemini_provider.py`, `backend/app/llm/groq_provider.py`, `backend/app/llm/cloudflare_provider.py` (per-attempt clamp, hard ceiling, minimum useful slice, `allow_model_retry` removed)
- `backend/app/main.py` (deadline measured from request entry)
- `backend/app/db_helper.py` (bounded connect/command)
- `frontend/src/app/api.ts` (platform-timeout message)
- `backend/tests/test_llm_budget.py` (new), `backend/tests/test_llm_suggestions.py`, `frontend/src/app/__tests__/suggestionsFailureDetail.test.ts`
- `AGENTS.md`, `docs/SYSTEM-DESIGN.md`
- No DB schema, secret, or deployment configuration change
