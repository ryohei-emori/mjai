## 1. Backend LLM Module

- [x] 1.1 Create `backend/app/llm/__init__.py` module structure
- [x] 1.2 Port prompt from `frontend/src/lib/webllm/prompts/` to `backend/app/llm/prompts.py`
- [x] 1.3 Port parser logic from `frontend/src/lib/webllm/parser.ts` to `backend/app/llm/parser.py`
- [x] 1.4 Implement Groq provider in `backend/app/llm/groq_provider.py` with httpx async client
- [x] 1.5 Implement Cloudflare Workers AI provider in `backend/app/llm/cloudflare_provider.py`
- [x] 1.6 Implement failover chain logic in `backend/app/llm/suggestions.py`

## 2. Backend API Endpoint

- [x] 2.1 Add `POST /suggestions` route to `backend/app/main.py` with auth dependency
- [x] 2.2 Add httpx to `backend/requirements.txt`
- [x] 2.3 Implement request validation (originalText, targetText required)
- [x] 2.4 Return consistent JSON schema matching WebLLM format

## 3. Backend Tests

- [x] 3.1 Add parser unit tests in `backend/tests/test_parser.py`
- [x] 3.2 Add mock-based tests for Groq success path
- [x] 3.3 Add mock-based tests for Groq fail → Cloudflare fallback
- [x] 3.4 Add mock-based tests for both providers fail → 503

## 4. Frontend API Integration

- [x] 4.1 Add `suggestionsAPI.generate()` to `frontend/src/app/api.ts`
- [x] 4.2 Update suggestion generation logic to try API first, then WebLLM fallback
- [x] 4.3 Add error handling with toast notification for fallback scenario
- [x] 4.4 Add "オフラインモード" toggle state (session-only, no persistence)

## 5. Frontend UI

- [x] 5.1 Add offline mode toggle near generate button or in settings
- [x] 5.2 Show visual indicator when using WebLLM vs API
- [x] 5.3 Preserve WebLLM diagnostics and progress UI for offline mode

## 6. Configuration & Documentation

- [x] 6.1 Add `GROQ_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` to `conf/.env.example`
- [x] 6.2 Update `AGENTS.md` with new env vars and hybrid AI architecture
- [x] 6.3 Update `docs/SYSTEM-DESIGN.md` to document API-first suggestion flow
- [x] 6.4 Verify WebLLM tests still pass

## 7. Deployment

- [ ] 7.1 Commit and push changes to main
- [ ] 7.2 Add env vars to Vercel production environment (manual step via Vercel dashboard)
