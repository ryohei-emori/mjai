## 1. Locate the failure

- [x] 1.1 Confirm the deployed function and database are healthy — `GET /api/health` 200, `GET /api/keepalive` 200 (DB reachable), `POST /api/suggestions` 401 without a token
- [x] 1.2 Trace every code path that can emit `All cloud providers failed. Try WebLLM offline mode.` — only `SuggestionsError` with `rate_limited` false: all providers failed at the network level, or the wall-clock guard fired
- [x] 1.3 Identify the regression: the fourth content check shares the 4-pass budget, the guard raises unconditionally, and the raise discards the body earlier passes produced

## 2. Stop retries from failing a generated body

- [x] 2.1 Keep the best body across passes and return it when a retry pass raises `SuggestionsError`
- [x] 2.2 Return the pass's soft body when the budget dies before Groq / Cloudflare salvage
- [x] 2.3 Skip a retry pass whose cost (measured from the previous pass) does not fit the remaining budget
- [x] 2.4 Cap recommended-form retries at `MAX_RECOMMENDATION_RETRIES`

## 3. Keep the chain inside the platform limit

- [x] 3.1 Add `allow_model_retry` to `call_gemini_with_rotation` / `call_groq_with_rotation`
- [x] 3.2 Compute it in the chain from the remaining budget and the next configured provider's timeout

## 4. Make the recommendation check precise

- [x] 4.1 Do not flag a reason that also introduces a Japanese recommended form
- [x] 4.2 Keep kanji-only forms and digit notation unflagged (existing cases still pass)

## 5. Report the cause to the user

- [x] 5.1 Add `timed_out` to `SuggestionsError` and to the 503 body, with distinct advice
- [x] 5.2 Type `gemini_error` / `gemini_pool_size` / `timed_out` on the client and include the Gemini error in rate-limit classification
- [x] 5.3 Append the per-provider breakdown to the toast and the failed job card, rendering newlines and keeping the full text in `title`
- [x] 5.4 Compose the user-facing message in Japanese from the flags (`describeSuggestionsFailure`) instead of forwarding the backend's English `message`
- [x] 5.5 Stop classifying rate limits from the raw response text, whose `"rate_limited"` key matched the pattern and flagged every 503 with a body

## 6. Tests

- [x] 6.1 Backend: provider failure on retry returns the earlier body
- [x] 6.2 Backend: exhausted budget on retry returns the earlier body; a pass that cannot finish is not started
- [x] 6.3 Backend: budget gone mid-pass returns the primary's soft body without calling the secondary
- [x] 6.4 Backend: no body at all still raises, with `timed_out` set for a wall-clock abort
- [x] 6.5 Backend: persistent Chinese recommended form stops after the cap
- [x] 6.6 Backend: `_allow_model_retry` / `_next_provider_timeout` units, and the chain passes the flag through
- [x] 6.7 Parser: a reason that also recommends a Japanese form is not flagged
- [x] 6.8 Frontend: `describeProviderFailures`, Gemini-only quota classified as rate-limited, `timed_out` exposed, JSON key names not read as quota wording
- [x] 6.9 Frontend: failed job and toast both show the breakdown, in Japanese, without the backend's English message
- [x] 6.10 Run backend pytest and frontend jest / tsc / lint — 350 passed + 1 skipped, 277 jest passed, tsc clean, lint unchanged (pre-existing font warning only)

## 7. Docs

- [x] 7.1 Update `AGENTS.md` (retry caps, budget gates, `timed_out`, breakdown)
- [x] 7.2 Update `docs/SYSTEM-DESIGN.md` (failover chain behaviour and failure reporting)

## 8. Live verification (needs credentials)

- [ ] 8.1 After deploy, generate once in production and record the per-provider breakdown shown on failure (or the successful model caption)
- [ ] 8.2 If the breakdown reports `Groq（鍵0件）`, set `GROQ_API_KEYS` on Vercel (production + preview) and redeploy so the secondary can rescue a slow Gemini
