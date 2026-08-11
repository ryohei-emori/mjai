## Context

MJAI currently generates AI correction suggestions entirely client-side via WebLLM (~0.9GB download, 30-90s initial load). See proposal.md - Why for motivation. The goal is sub-3-second suggestions via cloud APIs while preserving WebLLM for offline use and future evolution.

Current state:
- No `/suggestions` endpoint exists (removed during WebLLM migration)
- `frontend/src/lib/webllm/parser.ts` has hardened JSON parsing logic
- Auth via Supabase JWT is already in place (`backend/app/auth.py`)
- Vercel monorepo deployment serves backend at `/api/*`

## Goals / Non-Goals

**Goals:**
- Add `POST /api/suggestions` with Groq primary + Cloudflare failover
- Response time target: <3 seconds for most requests
- Reuse existing JSON schema and parsing logic
- Keep WebLLM fully functional as offline fallback
- Clear UX for when API vs WebLLM is used

**Non-Goals:**
- Multi-provider abstraction layer (simple if/else failover is sufficient)
- Persistent provider preference storage (session-only setting)
- Streaming responses (batch JSON response is sufficient for short outputs)
- Custom model fine-tuning or prompt optimization beyond current WebLLM prompts

## Decisions

### Decision 1: Provider architecture - Simple failover chain

**Choice:** Sequential try-catch pattern: Groq → Cloudflare → raise error

**Rationale:** Both providers use OpenAI-compatible chat completions format. A simple try-catch chain is easier to reason about than a registry/strategy pattern for just 2 providers.

**Alternatives considered:**
- Abstract provider interface with registry: Over-engineered for 2 providers; adds complexity without benefit
- Parallel requests to both (race): Wastes API credits; not cost-effective

### Decision 2: Prompt sharing - Port from frontend

**Choice:** Port the Chinese system prompt from `frontend/src/lib/webllm/prompts/system.ts` and few-shot example from `fewShot.ts` to backend Python.

**Rationale:** Same prompt produces consistent output format. Prompts are short (~500 tokens) and don't need separate file management.

**Alternatives considered:**
- Shared JSON prompt file: Added build complexity for minimal benefit
- Different backend prompt: Would require maintaining two prompts and potentially different parsing

### Decision 3: Parser reuse - Backend Python port

**Choice:** Port `frontend/src/lib/webllm/parser.ts` logic to Python in `backend/app/llm/parser.py`.

**Rationale:** The hardened parser handles trailing commas, truncated JSON, markdown fences - issues that occur with both WebLLM and cloud models. Same defensive logic needed on backend.

**Alternatives considered:**
- Strict JSON-only (reject malformed): Would cause unnecessary failures
- Shared npm package: Can't run JS in Python backend

### Decision 4: HTTP client - httpx with async

**Choice:** Use `httpx` (already common in FastAPI ecosystem) for async HTTP calls to provider APIs.

**Rationale:** Async-native, supports timeouts, connection pooling. FastAPI routes are already async.

**Alternatives considered:**
- `aiohttp`: Equally good but httpx has nicer API and is commonly paired with FastAPI
- `requests`: Sync-only, would block event loop

### Decision 5: Timeout configuration

**Choice:** 10-second timeout for Groq, 15-second timeout for Cloudflare (slightly higher as fallback).

**Rationale:** Groq targets <3s, but network variance can push to 5-7s. 10s gives headroom. Cloudflare gets extra time since it's already the fallback path.

### Decision 6: Frontend UX - API-first with explicit offline toggle

**Choice:** Default to API call; show "オフラインモード" toggle in settings or near the generate button. When API fails, auto-fallback to WebLLM with toast notification.

**Rationale:** Fast API is the default experience. Toggle lets power users or offline users explicitly choose WebLLM. Auto-fallback ensures resilience.

**Alternatives considered:**
- Separate "オフライン生成" button: Clutters UI with two buttons
- Settings-only toggle: Less discoverable
- Auto-detect offline (navigator.onLine): Unreliable; doesn't detect API key issues

### Decision 7: Error response format

**Choice:** Return `{"error": string, "fallback_available": boolean}` on failure, HTTP 503.

**Rationale:** Frontend can show error message and knows whether to attempt WebLLM fallback.

## Risks / Trade-offs

**[Risk] Groq rate limits on free tier** → Cloudflare failover automatically handles. Monitor 429 frequency in logs; upgrade plan if needed.

**[Risk] Cold start latency on Vercel serverless** → First request may add 1-2s. Acceptable given WebLLM's 30-90s alternative. Could add keep-warm if needed.

**[Risk] Cloudflare Workers AI model availability** → Use a stable model (e.g., `@cf/meta/llama-3.1-8b-instruct`). Document model ID in config for easy updates.

**[Trade-off] Two providers double the API surface to maintain** → Mitigation: Both use OpenAI-compatible format; actual code delta is minimal.

**[Trade-off] API keys required for fast path** → Users without keys still have WebLLM. Document clearly in AGENTS.md.

## Migration Plan

1. Add backend endpoint + LLM module (no frontend changes yet)
2. Add frontend `suggestionsAPI.generate()` calling new endpoint
3. Update UI to call API first, fall back to WebLLM
4. Add "オフラインモード" toggle
5. Update AGENTS.md, SYSTEM-DESIGN.md, conf/.env.example
6. Deploy to Vercel with new env vars
7. Test both paths (API success, API fail → WebLLM)

**Rollback:** Remove env vars from Vercel → endpoint returns 503 → frontend auto-falls back to WebLLM (existing behavior).

### Decision 8: JSON-parse-failure retry — retry the whole failover-chain pass, not a single provider call

**Choice:** When a generate+parse pass produces unparseable content, retry the *entire* `generate_suggestions` pass (Groq → Cloudflare failover chain, same as a fresh top-level call) up to `MAX_PARSE_RETRY_ATTEMPTS = 3` total passes, rather than (a) retrying only the same single provider call in a tight loop, or (b) immediately jumping to Cloudflare on the first parse failure.

**Rationale:**
- This retry axis is orthogonal to the existing network-level retry (Groq in-provider model rotation on 429/5xx/timeout, then Cloudflare fallback on a non-retriable/exhausted Groq failure). Composing them by retrying the *whole pass* keeps the two axes independent and easy to reason about — no special-casing needed inside `groq_provider.py` or `cloudflare_provider.py`.
- Groq is the primary/fastest path and already has model rotation (`select_groq_models`), so re-entering the Groq branch on a retry pass has a good chance of landing on a different model than the failed attempt, without prematurely spending the Cloudflare fallback slot on what may just be Groq-model-specific noise (e.g. a Preview-tier model's occasional malformed output).
- If Groq is not configured, each retry pass naturally goes straight to Cloudflare (unaffected — the pass structure is unchanged, only repeated).
- A genuine network-level failure (`SuggestionsError`, both providers failed at the HTTP layer even after their own retries) is NOT retried by this axis — it propagates immediately, since retrying a fully-down network path would not help and would only add latency.

**Bounded worst case:** `MAX_PARSE_RETRY_ATTEMPTS (3) × (Groq's own up-to-2-model rotation + 1 Cloudflare attempt if Groq raises)` — in practice, most passes succeed at parsing on attempt 1 (parse failures are rare), so this worst case is a deliberate, documented trade-off favoring eventual success over strict latency bounds for the rare parse-failure case. See `backend/app/llm/suggestions.py` module docstring for the precise accounting.

**Alternatives considered:**
- Retry only the same provider call directly (bypass the failover chain): simpler, but loses the "fall through to Cloudflare on repeated Groq parse failure" safety net entirely if Groq is configured, since a plain retry loop around `call_groq_with_rotation` alone would never try Cloudflare for a parse failure.
- Jump straight to Cloudflare after the first Groq parse failure: gives up on Groq's model rotation diversity too early; Cloudflare's single fixed model (`@cf/meta/llama-3.1-8b-instruct`) has no internal retry diversity of its own.

### Decision 9: Suggestion count reversed to "at least 5" (2026-08)

**Choice:** Revert the prior "up to 3, no padding" prompt guidance (Decision documented in tasks.md §7) back to "at least 5 genuine suggestions, no padding/fabrication," per explicit user direction. The anti-fabrication guardrail from the "up to 3" era is kept unchanged — only the target count and the instruction to search more dimensions (word choice, register, punctuation, phrasing, structure) before concluding there are fewer than 5 issues.

**Rationale:** For a correction-exercise product, under-reporting issues (capping at 3) was judged lower-value than thoroughness; almost any non-trivial piece of text has 5+ legitimate points worth flagging across grammar/register/naturalness/structure.

### Decision 10: Chinese explanations, Japanese corrected text (2026-08)

**Choice:** Explicitly split field-level language in the backend prompt (`backend/app/llm/prompts.py`): `reason` and `overallComment` → Simplified Chinese; `original` (the flagged/corrected Japanese excerpt) → stays Japanese. Both the system prompt's explicit field-level rules and the few-shot example are updated to demonstrate this exact mixed-language pattern.

**Rationale:** Restores the intended UX (Chinese-speaking users get explanations in their native language) without reintroducing the earlier garbled-mixed-language bug in the *corrected text itself* — the original bug was in over-applying Chinese to the whole response including the Japanese content field, not in having Chinese explanations per se. Field-level (not whole-prompt-level) language instructions avoid repeating that mistake.

## Open Questions

None - all design decisions are resolved.
