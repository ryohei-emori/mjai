## 1. Credential pool

- [x] 1.1 Extend `backend/app/llm/key_pool.py` with Gemini credential load/acquire/is_configured (`GEMINI_API_KEYS` plural wins, `GEMINI_API_KEY` singular back-compat, dedupe, redaction)
- [x] 1.2 Add/extend unit tests in `backend/tests/test_key_pool.py` for Gemini plural/singular/empty and cooldown selection

## 2. Gemini provider

- [x] 2.1 Add `backend/app/llm/gemini_provider.py`: `generateContent` v1beta client, message mapping, JSON mime config, timeouts, model allow-list (`gemini-3.7-flash`, `gemini-3.6-flash`) + `GEMINI_MODEL` pin + in-provider model retry, key-pool cooldown on 401/403/429
- [x] 2.2 Add unit tests for Gemini provider (mocked httpx): success path, rate-limit next-key, model pin, empty/error handling

## 3. Suggestions failover

- [x] 3.1 Integrate Gemini into `suggestions.py` after Cloudflare (network + same-pass content salvage); update `are_providers_configured`, `SuggestionsError` with `gemini_pool_size`, logging
- [x] 3.2 Expose `gemini_pool_size` on HTTP 503 JSON in `main.py` (alongside existing pool fields)
- [x] 3.3 Extend `backend/tests/test_llm_suggestions.py` for Groq/CF fail → Gemini success, salvage, and only-Gemini configured

## 4. Docs and env templates

- [x] 4.1 Update `conf/.env.example` with `GEMINI_API_KEYS` / `GEMINI_API_KEY` / `GEMINI_MODEL` placeholders only
- [x] 4.2 Update `AGENTS.md` AI provider tables/failover text: document Gemini pool; remove obsolete “do not configure GEMINI_*”
- [x] 4.3 Update `docs/SYSTEM-DESIGN.md` for Groq → Cloudflare → Gemini and Gemini ops

## 5. Ops config, verify, ship

- [x] 5.1 Configure gitignored `conf/.env` with two-key `GEMINI_API_KEYS` (never commit)
- [x] 5.2 Configure Vercel production (+ preview if AI keys already mirrored) via `printf | vercel env add … --sensitive` stdin
- [x] 5.3 Run focused pytest for key_pool / gemini_provider / llm_suggestions
- [x] 5.4 Commit and push code changes only (no secrets; leave unrelated OpenSpec planning alone)
