## Context

`suggestions.py` has two composable retry axes: each provider's own model rotation (transport failures) and this module's pass-level retry for unusable content. A wall-clock guard (`SUGGESTIONS_WALL_CLOCK_S`, 55s) exists so a slow chain returns an app-level 503 with pool diagnostics instead of Vercel's opaque 504 `FUNCTION_INVOCATION_TIMEOUT` at 60s.

`editable-prompt-model-log-and-critique-fix` added `has_non_japanese_recommendation()` as a fourth content check, sharing the existing `MAX_PARSE_RETRY_ATTEMPTS` (4) budget, and grew the prompt. Both moves were reasonable in isolation; together they turned the guard into a failure amplifier, because the guard raised unconditionally and the raise discarded whatever earlier passes had produced.

## Goals / Non-Goals

Goals:

- A user who could have been shown a critique is shown one, even when the critique is imperfect and the retries ran long.
- Retry cost is bounded by the remaining budget and by the severity of the fault, not just by an attempt count.
- A production cloud failure is diagnosable from the UI, without server log access.

Non-Goals:

- Changing failover order, provider timeouts, the wall-clock budget, or Vercel `maxDuration`.
- Changing the prompt rules or the few-shot exemplar (both stay as shipped).
- Auto-starting WebLLM on a cloud failure — オフラインモード stays explicit.
- Semantic validation of recommended forms (`需要` for `必要` is still a prompt-side concern; the check is script-level by design).

## Decisions

### Return the best body instead of raising, and stop guessing pass cost

`generate_suggestions()` now keeps `best_outcome` across passes (via the existing `_prefer_outcome`, which prefers a non-parse-failure body) and catches `SuggestionsError` from a retry pass: with a body in hand it logs and returns it, otherwise it re-raises. `_generate_suggestions_once()` likewise returns the pass's soft body when the budget dies before Groq/Cloudflare salvage.

Retries are additionally gated by `_can_afford_another_pass()`, which compares the remaining budget against the *measured* duration of the previous pass times `RETRY_BUDGET_MARGIN` (1.1). Measuring beats a constant because provider latency depends on prompt length, model and thinking level — and the cost of guessing low is precisely the failure mode being fixed.

Alternative considered: lowering `MAX_PARSE_RETRY_ATTEMPTS`. Rejected because it trades away legitimate JSON/language recovery on fast providers (Groq answers in 1–3s, so four passes are cheap there) while still allowing the same hard failure on a slow one.

### Cap recommended-form retries at one pass

`MAX_RECOMMENDATION_RETRIES = 1`. The three older checks reject bodies that are unusable *as data* (unparseable JSON) or *as language* (Japanese explanations for a Chinese-reading user). A Chinese recommended form is different in kind: the critique parses, reads in Chinese, and locates a real problem — only one quoted form is unusable. Spending three more passes (and three more free-tier requests per provider) on that is a bad trade, especially since a model that does it tends to keep doing it. The nudge is still sent once, which is where the win was.

### Gate the sibling-model attempt on the next provider's timeout

`call_gemini_with_rotation()` / `call_groq_with_rotation()` take `allow_model_retry`. The chain computes it from the remaining budget and the next configured provider's timeout (`_allow_model_retry`, `_next_provider_timeout`). Two Gemini timeouts alone are 44s of the 55s budget, after which starting Groq's 25s call could exceed Vercel's 60s limit — the exact platform-504 outcome the wall clock exists to avoid. The gate lives in the chain, not the provider, because "who answers next" is chain knowledge.

**Superseded by `fix-function-invocation-timeout`.** This gate was not sufficient, and the follow-up change removes it. Because the flag is computed *before* the provider's first attempt, it cannot account for how long that attempt actually takes: the first Gemini call still satisfied the gate, ran its full 22s, and the sibling attempt then starved Groq anyway — and none of it bounded the *duration* of a call, only whether one could start. It is replaced by a per-provider phase deadline that every attempt is re-checked against.

### Require an absent Japanese form before flagging a Chinese one

`has_non_japanese_recommendation()` now collects every recommended form in a reason and flags only when at least one is Chinese and none is Japanese. Recommendation verbs (`改成` / `改为` / `写成`) are also how critique narrates the shift it found, so the previous rule punished good critiques. `_form_is_japanese()` accepts kana, or CJK with no Simplified-only character, which keeps kanji-only forms (`叙事詩`) and digit notation (`9.5時間`) legitimate.

### Report the per-provider breakdown in the UI

The backend already returned `gemini_error` / `groq_error` / `cf_error` and pool sizes; the client dropped the Gemini ones from its type and showed only `message`. `describeProviderFailures()` renders `Gemini（鍵1件）: … / Groq（鍵0件）: …`, appended under the message on the toast and the failed job card (which now renders newlines and carries the full text in `title`). `timed_out` is threaded through so a budget abort reads as "retry" rather than "check your keys".

The message itself is now composed on the client (`describeSuggestionsFailure`) from those flags, because forwarding `apiError.message` is how ops-facing English (`All cloud providers failed. Try WebLLM offline mode.`) became the user-visible text of a Japanese UI. The backend keeps its English message for logs and non-UI consumers.

Fixing that surfaced a second bug behind it: `SuggestionsAPIError` classified rate limits by pattern-matching a haystack that included the raw response text — i.e. the JSON body, which always contains the key `"rate_limited"`. Every 503 with a body therefore matched `/rate.?limit/`, so the flag carried no information (and the old code path masked it by throwing the backend message either way). Classification now reads parsed fields, falling back to the raw message only when there is no body, which is the network-error case it was written for.

## Risks / Trade-offs

- **A flawed critique can now reach the user** where it previously produced an error. That is the intended trade: the alternative shown in production was no critique at all after 55s. The nudge still runs once, and the model provenance caption tells the user which model wrote it.
- **`RETRY_BUDGET_MARGIN` is heuristic.** A pass that is much slower than its predecessor can still be cut short mid-flight — but that now returns the earlier body instead of raising, so the failure mode is degraded quality, not a failed request.
- **The provider breakdown shows raw backend error strings** (English, e.g. `Gemini request timed out after 22.0s`). They contain no secrets — pool sizes are counts — and honest detail beats a message that cannot distinguish causes.
- **Verification is offline.** No provider credentials exist in the agent environment, so the retry-storm path is covered by deterministic tests with a controllable clock (`FakeClock`) rather than a live probe. The live-cause hypothesis is inferred from the code paths that can emit the reported message, plus the confirmed-healthy `/api/health` and `/api/keepalive`.

## Migration Plan

None. No DB, schema, env or deployment change; the fix ships with the normal Vercel deploy from `main`.

## Open Questions

- Whether production also has an ops-side cause (only Gemini configured, or its free-tier quota exhausted). The new breakdown answers this from the UI on the next failure: `Groq（鍵0件）: Groq API key not configured` means adding `GROQ_API_KEYS` on Vercel is the remaining action, while a cooldown/quota error with `鍵1件` points at the Gemini project's limits.
