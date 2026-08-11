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

## 7. Suggestion count tuning (post-launch)

- [x] 7.1 Update backend prompt (`backend/app/llm/prompts.py`) to target up to 3 suggestions instead of 5, without instructing fabrication/padding
- [x] 7.2 Update WebLLM prompts (`frontend/src/lib/webllm/prompts/system.ts`, `fewShot.ts`) to match the 3-suggestion target for consistency
- [x] 7.3 Verify no hardcoded 5-count truncation/padding logic exists in `backend/app/llm/parser.py` / `suggestions.py` (none found — count is prompt-guided only)
- [x] 7.4 Verify `backend/ pytest` passes with no test hardcoding the old 5-count expectation

## 8. Deployment

- [x] 8.1 Commit and push changes to main
- [x] 8.2 Add env vars to Vercel production environment — **GROQ_API_KEY** + **CLOUDFLARE_API_TOKEN** set (Production + Preview via CLI); **CLOUDFLARE_ACCOUNT_ID** still required for Workers AI fallback (paste from Cloudflare dashboard Overview)

## 9. Suggestion count reversal + bilingual content + parse-failure retry (2026-08 `/opsx-apply`)

- [x] 9.1 Reverse suggestion-count guidance in `backend/app/llm/prompts.py` from "up to 3, no padding" back to "at least 5, no padding" — bias the model to search word choice/register/punctuation/phrasing/structure before concluding fewer than 5 issues exist
- [x] 9.2 Apply the same "at least 5" reversal to `frontend/src/lib/webllm/prompts/system.ts` and `fewShot.ts` for cloud/offline consistency
- [x] 9.3 Split field-level language in `backend/app/llm/prompts.py`: `reason` + `overallComment` → Simplified Chinese; `original` → stays Japanese. Update the few-shot example to demonstrate this exact split
- [x] 9.4 Verify/fix `frontend/src/lib/webllm/prompts/system.ts` + `fewShot.ts` explicitly distinguish Japanese `original` vs Chinese `reason`/`overallComment` (WebLLM prompt was already Chinese-only; add the explicit split instruction)
- [x] 9.5 Update `backend/app/llm/parser.py` docstring to reflect the current field-level language expectations (no parsing logic changes needed — parser is language-agnostic)
- [x] 9.6 Bump WebLLM `max_tokens` (512 → 1024) in `frontend/src/lib/webllm/engine.ts` and update `config.ts` docstring, since 5+ suggestions need more output budget than the old "up to 3" target
- [x] 9.7 Implement bounded JSON-parse-failure retry (up to 3 total passes) in `backend/app/llm/suggestions.py`, additive with existing network-level retry/failover (see design.md Decision 8)
- [x] 9.8 Add tests in `backend/tests/test_llm_suggestions.py` covering: parse failure on attempts 1–2 then success on attempt 3; giving up after 3 failed parse attempts
- [x] 9.9 Update `specs/ai-suggestions/spec.md` (count, bilingual content, retry requirements) and `design.md` (Decisions 8–10) to reflect all of the above
- [x] 9.10 Run `backend pytest` to confirm no regressions from the retry loop or prompt changes
