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

## Open Questions

None - all design decisions are resolved.
