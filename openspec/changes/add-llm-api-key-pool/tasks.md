## 1. Key pool module

- [x] 1.1 Add `backend/app/llm/key_pool.py` with credential parsing for `GROQ_API_KEYS` / `GROQ_API_KEY` and `CLOUDFLARE_ACCOUNT_IDS`+`CLOUDFLARE_API_TOKENS` / singular pair, round-robin `acquire`, cooldown on mark, redacted labels, and test-friendly pool reset
- [x] 1.2 Reject mismatched Cloudflare parallel-list lengths (empty pool) and ignore empty CSV entries

## 2. Provider wiring

- [x] 2.1 Update `groq_provider.py` so `get_groq_api_key` / outbound calls use the Groq pool and retry with the next key on 401/403/429 (bounded by pool size)
- [x] 2.2 Update `cloudflare_provider.py` similarly for account_id+token pairs; surface rate-limit/auth status for cooldown marking
- [x] 2.3 Update `suggestions.py` (and any `is_*_configured` helpers) to treat non-empty pools as configured

## 3. Config and docs

- [x] 3.1 Update `conf/.env.example` with plural vars (placeholders only) and keep singular aliases documented
- [x] 3.2 Merge real keys into gitignored `conf/.env` using the new format (omit or leave blank the second CF account id if unknown)
- [x] 3.3 Briefly document the multi-key convention and back-compat in `AGENTS.md`

## 4. Tests

- [x] 4.1 Add `backend/tests/test_key_pool.py` covering selection, cooldown, next-key fallback, singular back-compat, and mismatched CF lists
- [x] 4.2 Adjust existing Groq/Cloudflare/suggestions unit tests if they break under pool-based reads; keep them green

## 5. Verify and ship

- [x] 5.1 Run key-pool unit tests plus relevant `backend/tests/test_groq_provider.py` / `test_llm_suggestions.py` (and CF tests if present)
- [x] 5.2 Optional smoke: one Groq call via key A and one via key B without logging secrets
- [x] 5.3 Commit and push code + openspec + `.env.example` + `AGENTS.md` only (never `conf/.env`)
