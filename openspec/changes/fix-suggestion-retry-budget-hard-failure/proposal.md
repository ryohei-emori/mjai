## Why

Production reported `All cloud providers failed. Try WebLLM offline mode.` right after `editable-prompt-model-log-and-critique-fix` shipped, while `/api/health` and `/api/keepalive` stayed green — so the function and database were fine and the failure was inside the suggestions failover chain.

That message is only reachable from `SuggestionsError`, which `suggestions.py` raises in two situations: no provider returned any HTTP body, **or** the wall-clock guard (`SUGGESTIONS_WALL_CLOCK_S`, 55s) fired. The second path is a regression the merged change made easy to hit:

- `has_non_japanese_recommendation()` became a fourth content check. A body that fails a content check is not returned; the whole Gemini → Groq → Cloudflare pass is retried, up to `MAX_PARSE_RETRY_ATTEMPTS` (4) times.
- A model that answers with a Chinese recommended form is *exactly* the behaviour that check exists to catch, and such a model tends to repeat it, so all four passes are typically spent.
- The same change grew the prompt (rules body plus a six-item few-shot), so each pass costs more seconds. Four Gemini passes at 7–16s each reach the 55s budget.
- Once the budget was gone, `_raise_if_wall_clock_exceeded()` raised and **discarded the body earlier passes had already produced** — a parseable Chinese critique whose only flaw was one Chinese-quoted form. The user got a hard 503 after ~55s instead of a readable critique after ~10s, and each attempt also burned a free-tier request on every configured provider.

The guard was also over-eager: critique prose narrates a meaning shift with the same verbs it uses to recommend (`译文把原文的"对比"改成了"比较"…应写成「対比する」`), so bodies that *did* hand over a usable Japanese form were rejected too.

Independently, the UI could not distinguish these causes. The backend returns `gemini_error` / `groq_error` / `cf_error` plus pool sizes, but the frontend type omitted the Gemini fields entirely and the UI showed only the generic message — so an unset Groq key, an exhausted Gemini quota and a 22s timeout all looked identical, and diagnosing production required guessing.

## What Changes

- A pass that already produced a body MUST NOT be turned into a 503. When a later retry pass cannot run — providers failed, or the budget is gone — the best body so far is returned. `SuggestionsError` is now reserved for "no body at all".
- A retry pass is not started unless the remaining budget still covers a pass as long as the previous one (measured, not assumed), so a pass is never begun only to be aborted mid-flight.
- Within a pass, an exhausted budget before Groq/Cloudflare salvage returns the soft body the primary produced instead of raising.
- The Chinese-recommended-form check stops after `MAX_RECOMMENDATION_RETRIES` (1) extra pass. Unlike unparseable output or Japanese explanations, that body is readable critique, so more latency and free-tier requests are not justified.
- A provider's second in-provider model attempt is skipped when it would leave the next provider in the chain no room: two Gemini timeouts alone cost 44s of the 55s budget, which could also push the request past Vercel's 60s `maxDuration`.
- `has_non_japanese_recommendation()` no longer flags a reason that also introduces a Japanese recommended form.
- `SuggestionsError` carries `timed_out`, exposed as `timed_out` in the 503 body, so a wall-clock abort gets retry-oriented advice instead of "all providers failed".
- The frontend types `gemini_error` / `gemini_pool_size` / `timed_out`, includes the Gemini error in its rate-limit classification, and appends a per-provider breakdown (`内訳: Gemini（鍵1件）: … / Groq（鍵0件）: …`) to the toast and the failed job card.

Deliberately unchanged: failover order, provider timeouts, `SUGGESTIONS_WALL_CLOCK_S`, `MAX_PARSE_RETRY_ATTEMPTS` for parse/language failures, the prompt rules and few-shot, the response schema, and オフラインモード gating (WebLLM still never auto-starts).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: content-quality retries MUST NOT downgrade an already-generated critique into a failed request; retry passes MUST be bounded by the remaining wall-clock budget and, for the recommended-form check, by an explicit pass cap; a second in-provider model attempt MUST NOT crowd out the next provider; and a cloud failure MUST report per-provider cause and credential counts to the user.

## Impact

- `backend/app/llm/suggestions.py` (retry loop, budget gates, `timed_out`)
- `backend/app/llm/parser.py` (`has_non_japanese_recommendation` precision)
- `backend/app/llm/gemini_provider.py`, `backend/app/llm/groq_provider.py` (`allow_model_retry`)
- `backend/app/main.py` (503 body `timed_out`, distinct message)
- `frontend/src/app/api.ts`, `frontend/src/app/page.tsx` (provider breakdown)
- `backend/tests/test_llm_suggestions.py`, `backend/tests/test_llm_parser.py`, `frontend/src/app/__tests__/suggestionsFailureDetail.test.ts`, `frontend/src/app/__tests__/suggestionsFailureUi.test.tsx`
- `AGENTS.md`, `docs/SYSTEM-DESIGN.md`
- No DB, schema, secret, or deployment changes
