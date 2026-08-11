## Why

The backend currently pins Groq inference to a single hardcoded default model (`llama-3.3-70b-versatile`), with no fallback to another Groq model before dropping out to Cloudflare Workers AI. This is riskier than it looks for three reasons: (1) a single model can hit its per-model daily/rate limits (Groq enforces limits per model, not account-wide) or produce an occasional malformed/garbled response, forcing an unnecessary drop to the slower Cloudflare fallback; (2) relying on one model id means one upstream deprecation silently breaks suggestion generation; and (3) **this is not hypothetical** — a live check of Groq's own deprecation page during this proposal (see `design.md` for sources and timestamps) confirms `llama-3.3-70b-versatile`, the current hardcoded default, is scheduled for shutdown on **2026-08-16**, days away at the time of writing. Rotating across a small, curated set of Groq models spreads load, gives a same-provider fallback before paying the latency cost of Cloudflare, and removes the single-point-of-failure risk of one model id being retired.

## What Changes

- Replace the single hardcoded `DEFAULT_GROQ_MODEL` in `backend/app/llm/groq_provider.py` with a curated, explicit allow-list of Groq models suitable for structured-JSON Japanese correction output (general-purpose instruction-following chat models only — excludes moderation/guard, agentic/tool-use, and safety-tuned variants).
- Add model-selection logic that picks a model from the allow-list per request (see `design.md` for the random-vs-counter tradeoff given Vercel's stateless serverless invocations) instead of always using the same model.
- Preserve the `GROQ_MODEL` env var as an override that **disables rotation** and pins to a single model, for backward compatibility and debugging (unchanged existing behavior when set).
- Add bounded in-provider retry: on a retriable Groq failure (429/5xx/timeout), retry with one additional model from the rotation pool before falling back out to Cloudflare, to keep total worst-case latency bounded (see `design.md`/`specs` for the exact retry count and justification).
- Update `backend/app/llm/suggestions.py` only if the retry-before-fallback logic cannot live entirely inside `call_groq`/`groq_provider.py` (to be confirmed during design/implementation — proposal keeps this open, design.md makes the call).
- **BREAKING (internal/operational only, not a public API contract change)**: the specific Groq model used for a given request is no longer deterministic/fixed; this is invisible to API consumers (`POST /api/suggestions` response schema is unchanged) but relevant to anyone debugging via Groq dashboard per-model usage graphs.
- Update `AGENTS.md` "AI Suggestion Generation" section and `docs/SYSTEM-DESIGN.md` (if it documents the single-model behavior) to describe the new multi-model rotation layer.
- Add/extend tests in `backend/tests/test_groq_provider.py` (and `backend/tests/test_suggestions.py`-equivalent if one exists) for the allow-list, selection logic, `GROQ_MODEL` override behavior, and in-provider retry-then-fallback behavior.

## Capabilities

### New Capabilities

(None — this extends the existing Groq provider behavior rather than introducing a new capability domain.)

### Modified Capabilities

- `ai-suggestions`: The "Groq as primary provider" requirement (introduced in `add-groq-cloudflare-suggestions`, not yet archived/synced to `openspec/specs/`) changes from a single fixed Groq model to a curated multi-model rotation pool, with bounded in-provider retry across that pool before falling back to Cloudflare Workers AI. This proposal's delta spec is written against the same `specs/ai-suggestions/` capability path used by that predecessor change, since it has not yet been archived into `openspec/specs/`.

## Impact

- **Backend**: `backend/app/llm/groq_provider.py` (model allow-list constant, selection logic, `GROQ_MODEL` override handling, in-provider retry loop), `backend/app/llm/suggestions.py` (only if retry-across-models can't stay encapsulated in `groq_provider.py`).
- **Tests**: `backend/tests/test_groq_provider.py` (extend existing model-selection tests), possibly a new/extended suggestions-failover test file.
- **Docs**: `AGENTS.md` "AI Suggestion Generation" section (model table, rotation description), `docs/SYSTEM-DESIGN.md` if it duplicates that content.
- **Config**: No new environment variables required; `GROQ_MODEL` semantics are extended (now explicitly documented as "pin to one model, disable rotation") rather than changed.
- **Dependencies**: None new.
- **Out of scope**: No frontend changes (rotation is entirely a backend/Groq-provider implementation detail, invisible to the response schema); no changes to Cloudflare Workers AI or WebLLM fallback tiers.
