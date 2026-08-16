## 1. Locate the overrun

- [x] 1.1 Confirm the platform limit and where it is configured — `vercel.json` `functions["api/index.py"].maxDuration = 60`
- [x] 1.2 Add up the chain's static timeouts against the guard: Gemini 22 + sibling 22 = 44s passes the "deadline not yet reached" check, then Groq 25s ends at 69s
- [x] 1.3 Find the multipliers: pooled credentials each get a fresh full timeout, and the budget clock starts after the stored-prompt lookup, JWT verification and cold start
- [x] 1.4 Confirm the previous change's `allow_model_retry` gate cannot close this — it is computed before the first attempt, so it cannot know what that attempt spends

## 2. Make the budget bound calls, not just their start

- [x] 2.1 Add `backend/app/llm/budget.py`: `seconds_left`, `resolve_call_timeout`, `describe_skip`, platform limit and reserve
- [x] 2.2 Declare each provider's minimum useful slice from measured latency (Gemini 10s, Groq 5s, Cloudflare 6s)
- [x] 2.3 Thread a deadline into `call_gemini` / `call_groq` / `call_cloudflare` and clamp every attempt, including each pooled credential
- [x] 2.4 Enforce the clamp as a whole-attempt ceiling with `asyncio.wait_for` (httpx's timeout is per operation)
- [x] 2.5 Prefer a provider's real error over "and then we ran out of time" when both apply

## 3. Stop a slow provider starving the next one

- [x] 3.1 Add `_later_provider_reserve` / `_phase_deadline` / `_phase_budget` to the chain
- [x] 3.2 Give each provider a phase deadline short of the request deadline by what the configured providers after it need
- [x] 3.3 Remove `allow_model_retry` from both rotation wrappers and from the chain — the phase deadline decides it from the clock
- [x] 3.4 Skip a provider whose slice is below its minimum, recording a reason that names the provider and the time left
- [x] 3.5 Return an existing soft body instead of walking to the failure when the rest of the chain cannot fit

## 4. Cover the whole request

- [x] 4.1 Derive `SUGGESTIONS_WALL_CLOCK_S` from `PLATFORM_MAX_DURATION_S − PLATFORM_RESERVE_S` (45s)
- [x] 4.2 Take the deadline at request entry in `POST /suggestions` so the stored-prompt lookup shares the budget
- [x] 4.3 Bound `asyncpg.connect()` (8s connect, 15s command) so a database outage is not a platform timeout

## 5. Report the cause

- [x] 5.1 Set `timed_out` when a provider was skipped for budget or granted less than its own timeout
- [x] 5.2 Recognise a platform timeout on the client (`isPlatformTimeout`) and explain it in Japanese

## 6. Tests

- [x] 6.1 `PLATFORM_MAX_DURATION_S` matches `vercel.json`; budget plus reserve reconcile with it
- [x] 6.2 `resolve_call_timeout`: clamps, never exceeds what remains, returns None below the minimum and past the deadline, unbounded without a deadline
- [x] 6.3 A Gemini attempt is granted the remaining budget, and one that cannot fit is not made
- [x] 6.4 Pooled keys share one budget instead of one full timeout each
- [x] 6.5 The production sequence (Gemini twice, then Groq) finishes inside the budget and Groq still answers
- [x] 6.6 All three providers burning every granted second still fit the budget, and the failure is marked `timed_out`
- [x] 6.7 A spent budget skips every provider and reports `timed_out` with per-provider skip reasons
- [x] 6.8 A caller-supplied deadline is honoured (time already spent before generation counts)
- [x] 6.9 Phase reserve covers only configured, still-to-come providers; the chain hands its phase deadline to the provider
- [x] 6.10 Frontend: a non-JSON 504 is explained in Japanese, without the platform identifier
- [x] 6.11 Run backend pytest and frontend jest / tsc / lint — 369 passed + 1 skipped, 279 jest passed, tsc clean, ruff findings unchanged on touched app files

## 7. Docs

- [x] 7.1 Update `AGENTS.md` (call sizing, minimum slices, phase deadlines, derived budget, bounded DB)
- [x] 7.2 Update `docs/SYSTEM-DESIGN.md` (timeout budget as an invariant, and how a failure is classified)
- [x] 7.3 Note in `fix-suggestion-retry-budget-hard-failure` that `allow_model_retry` is superseded

## 8. Live verification (needs a deployed build)

- [ ] 8.1 After deploy, generate once in production and confirm a critique returns, or a 503 with the per-provider breakdown — not `FUNCTION_INVOCATION_TIMEOUT`
- [ ] 8.2 If the failure reports `Groq（鍵0件）`, set `GROQ_API_KEYS` on Vercel (production + preview) and redeploy so the secondary can rescue a slow Gemini
