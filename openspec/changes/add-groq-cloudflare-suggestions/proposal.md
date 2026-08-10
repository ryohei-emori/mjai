## Why

WebLLM currently requires ~0.9GB model download and 30-90 seconds initial load time, causing slow first-use experience. Users need **fast AI suggestions (~3 seconds)** for a smooth correction workflow. Adding cloud-based LLM providers (Groq as primary, Cloudflare Workers AI as failover) will dramatically improve response time while retaining WebLLM as an offline fallback for future client-side evolution.

## What Changes

- **Add backend `POST /api/suggestions` endpoint**: Authenticated endpoint that generates Japanese text correction suggestions using cloud LLM providers
- **Groq as primary provider**: OpenAI-compatible chat completions API with fast model (`llama-3.1-8b-instant`); ~1-3s inference
- **Cloudflare Workers AI failover**: Automatic fallback on Groq 429/5xx/timeout errors; uses Workers AI REST API with similar fast model
- **Reuse existing JSON schema**: Same `{"指摘": [...], "全体講評": "..."}` structure; share/port hardened parser logic from `frontend/src/lib/webllm/parser.ts`
- **Frontend API-first UX**: Call backend API by default for speed; WebLLM remains as optional offline fallback when APIs fail or keys are missing
- **Environment variables**: `GROQ_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` (backend-only, never `NEXT_PUBLIC_*`)
- **Documentation updates**: AGENTS.md, SYSTEM-DESIGN.md, conf/.env.example to reflect hybrid architecture
- **Tests**: Mock-based tests for Groq success, Groq fail → CF fallback, both fail → clear error

## Capabilities

### New Capabilities

- `ai-suggestions`: Cloud-based AI suggestion generation with Groq primary + Cloudflare Workers AI failover, keeping WebLLM as offline fallback

### Modified Capabilities

(None - this is a new capability addition; WebLLM code remains unchanged)

## Impact

- **Backend**: `backend/app/main.py` (new `/suggestions` route), new `backend/app/llm/` module for provider abstraction
- **Frontend**: `frontend/src/app/api.ts` (add `suggestionsAPI`), components to prefer API over WebLLM
- **Config**: `conf/.env.example` (new env vars), Vercel environment variables
- **Docs**: `AGENTS.md`, `docs/SYSTEM-DESIGN.md` (hybrid AI architecture)
- **Tests**: New backend tests in `backend/tests/`, verify existing WebLLM tests remain passing
- **Dependencies**: `httpx` or `aiohttp` for async HTTP calls to Groq/CF APIs
