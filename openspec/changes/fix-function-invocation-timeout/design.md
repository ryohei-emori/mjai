## Context

`POST /api/suggestions` runs as a Vercel Python function with `maxDuration: 60`. Exceeding that produces a platform 504 `FUNCTION_INVOCATION_TIMEOUT`: a response with no application body, so none of the pool sizes, per-provider errors, `timed_out` flag or partially generated critique that `fix-suggestion-retry-budget-hard-failure` added can be returned. Staying under the limit is therefore a correctness property of the request path, not a quality-of-service nicety.

`SUGGESTIONS_WALL_CLOCK_S` was intended to provide that, but it was a *check between calls* rather than a *bound on calls*. `_raise_if_wall_clock_exceeded()` asked whether the deadline had already passed; every provider then used its own static timeout. The chain's arithmetic therefore never added up:

| Step | Static timeout | Clock after |
|---|---|---|
| Gemini, first model | 22s | 22s |
| Gemini, sibling model | 22s | 44s |
| Groq (44 < 55, so the check passed) | 25s | **69s** |

69s against a 60s limit, with no step doing anything unusual. Two further multipliers existed: each pooled credential got a fresh full timeout inside one provider, and the budget clock started inside `generate_suggestions()` — after the up-to-3s stored-prompt lookup, JWT verification and cold start, all of which count against `maxDuration`.

## Goals / Non-Goals

Goals:

- A request cannot exceed the platform limit, as an invariant of how calls are sized rather than a property that has to be re-derived when a timeout constant changes.
- A slow primary cannot starve a fast secondary, decided from time actually spent.
- A failure that is really "we ran out of time" says so.
- A database outage is legible instead of arriving as a platform timeout.

Non-Goals:

- Changing failover order, provider timeout constants, prompts, or the response schema.
- Changing the retry-pass semantics introduced by the previous change (best body wins over a 503; recommended-form cap).
- Streaming, or moving generation to a background job, to escape the limit — a different design, out of scope here.

## Decisions

### Size every call to the remaining budget, and make that a hard ceiling

`budget.resolve_call_timeout(deadline, provider_timeout, min_useful)` returns `min(provider_timeout, remaining − RESPONSE_OVERHEAD_S)`, or `None` when that is below `min_useful`. Providers apply the result with `asyncio.wait_for` around the HTTP call, in addition to passing it to httpx.

The `wait_for` is not redundant: httpx's `timeout=` is per operation, so a connect and a read can each consume the full value, and a call sized to the exact remaining budget could still overshoot it. `wait_for` bounds the attempt as a whole, which is what the invariant needs.

Alternative considered: keep static timeouts and lower them until the worst-case chain fits (e.g. Gemini 12s, Groq 10s, CF 8s). Rejected — it penalises the *healthy* path, where Gemini legitimately needs 7–16s, in order to protect a path that only occurs when providers are failing. Sizing to the remaining budget leaves the healthy path untouched.

### Skip a provider that cannot answer in the time left

Each provider declares a minimum useful slice from measured latency: Gemini 10s (probes: 7.2–13.8s with `thinkingLevel=low`), Groq 5s (1–3s), Cloudflare 6s (2–5s). Below that, the provider is skipped and the reason recorded — `Gemini skipped: 4.2s of the request budget left, under the 10s a call needs`.

The alternative, granting a 4s slice to Gemini, is worse than doing nothing: it will time out, and the 4s it burns are 4s that Groq — which answers in 1–3s — could have used to actually produce a critique.

### Give each provider a phase deadline instead of predicting its retry

The previous change gated the sibling-model attempt with a boolean, `allow_model_retry`, computed by the chain *before* the provider's first attempt. That cannot work: the decision depends on how long the first attempt takes, which is unknown when the flag is computed. Concretely, with a 45s budget the flag was satisfied at t=0, the first Gemini attempt ran 22s, the sibling was then still permitted, and Groq was left with nothing.

The flag is therefore removed and replaced by a phase deadline: `_phase_deadline(deadline, after=...)` subtracts `_later_provider_reserve()` — the minimum useful slices of the configured providers still to come — from the request deadline, and the provider clamps *every* attempt against it. The decision is re-taken from the clock before each attempt, so an attempt that overran cannot leave the chain committed to a call the budget can no longer cover.

Worst case with all three providers configured and each burning everything it is granted:

| Step | Granted | Clock after |
|---|---|---|
| Gemini, first model | 22.0s | 22.0s |
| Gemini, sibling model | 10.5s | 32.5s |
| Groq | 5.0s | 37.5s |
| Cloudflare | 6.0s | 43.5s |

43.5s inside a 45s budget, every provider still gets a turn, and this is asserted as a test rather than left as a comment.

One mechanism replaces two on purpose. Keeping both would have meant two places deciding the same question by different rules, which is how the original guard and the static timeouts came to disagree in the first place.

### Derive the budget from the platform limit, and start it at request entry

`SUGGESTIONS_WALL_CLOCK_S = PLATFORM_MAX_DURATION_S − PLATFORM_RESERVE_S` (60 − 15 = 45s). Naming the reserve makes explicit what the old hand-picked 55s left implicit and too small: cold start (importing FastAPI, httpx, asyncpg and the JWT stack on a fresh isolate), JWT verification, and request/response transfer are all inside the platform limit but outside anything the handler can measure. A test reads `vercel.json` and asserts `PLATFORM_MAX_DURATION_S` still matches it, so raising `maxDuration` without re-deriving the budget is caught.

The endpoint takes the deadline at request entry and passes it down, so the stored-prompt lookup is spent from the same budget as the LLM calls rather than added to it.

The 10s the budget gives up relative to 55s costs nothing on a healthy request (Gemini ~7–16s plus at most one fast secondary) and only shortens already-degraded ones — where the alternative was a 504 with no diagnostics at all.

### Report a clamped-and-failed chain as a timeout

`timed_out` is now set when any provider was skipped for budget **or** was granted less than its own timeout. A Groq call that got 5s instead of 25s and timed out is a budget symptom, and "retry" is the right advice for it; "check your keys" is not. `rate_limited` and `timed_out` can both be true (a 429 primary that also ate the budget); both are reported as facts and the client picks which advice leads.

### Bound the database, and name a platform timeout in the UI

`asyncpg.connect()` had no timeout, and asyncpg's default is 60s — the same number as the platform limit, so a paused Supabase project produced a 504 rather than an error. Bounded at 8s connect / 15s command, an outage becomes a fast legible failure. (`resolve_system_prompt_override()` was already protected by its own 3s `wait_for`; the history routes were not.)

For the residual case where the invocation itself overruns, `isPlatformTimeout()` recognises a 5xx with no application body, or Vercel's identifier in the text, and the UI explains it in Japanese rather than showing `FUNCTION_INVOCATION_TIMEOUT`.

## Risks / Trade-offs

- **A clamped provider is likelier to time out** than one with its full timeout, so degraded requests may fail slightly more often at the last provider. Accepted: the alternative for those requests was a platform 504, which is a failure too — and one with no diagnostics and no chance of returning an earlier body.
- **The minimum useful slices are measured constants, not adaptive.** If a provider's latency profile changes, a slice that is generous today could skip calls that would have succeeded (or admit calls that cannot). They sit next to each provider's timeout with the measurement recorded in a comment, so they are revised together.
- **`PLATFORM_RESERVE_S` (15s) is an estimate** of cold start plus transfer. Erring generous costs seconds only in degraded requests; erring tight reintroduces the bug. The test tying it to `vercel.json` keeps the relationship visible rather than accurate — a genuinely slow cold start would still need the reserve widened.
- **Verification is offline.** No provider credentials exist in this environment, so the timeline is asserted with a controllable clock and a fake that spends exactly what it is granted, rather than against live providers. The arithmetic table above is reproduced by that test.

## Migration Plan

None. No DB, schema, env or deployment configuration change; `vercel.json` is unchanged and the fix ships with the normal Vercel deploy.

## Open Questions

- Whether the observed production timeout was the provider chain or a stalled database connection. Both are now bounded, and after this deploy the two are distinguishable: the chain returns a 503 with a per-provider breakdown and `timed_out`, while a database problem returns a fast connect error naming Postgres.
