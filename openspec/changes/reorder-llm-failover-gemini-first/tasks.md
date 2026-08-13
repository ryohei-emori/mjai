## 1. Failover reorder

- [x] 1.1 Reorder `_generate_suggestions_once` in `backend/app/llm/suggestions.py` to Gemini → Groq → Cloudflare; keep same-pass salvage, outer Chinese/JSON retries, and SuggestionsError pool diagnostics coherent
- [x] 1.2 Update llm package comments (`__init__.py`, `gemini_provider.py`, `main.py` route docstring) that still say Groq-primary / Gemini-tertiary

## 2. Tests

- [x] 2.1 Update `backend/tests/test_llm_suggestions.py` for Gemini-first success, salvage, and failover; fix assertions that assume Groq-first
- [x] 2.2 Run focused pytest for `test_llm_suggestions` (and related if needed) and fix regressions

## 3. Docs and env template

- [x] 3.1 Update `AGENTS.md` failover diagram/tables to Gemini → Groq → Cloudflare
- [x] 3.2 Update `docs/SYSTEM-DESIGN.md` failover text/diagrams and remove obsolete “Gemini-primary rejected” wording that contradicts the new order
- [x] 3.3 Update `conf/.env.example` comments that document provider order (placeholders only; no secrets)

## 4. Ship

- [x] 4.1 Commit and push the change (code, docs, OpenSpec artifacts; no secrets)
