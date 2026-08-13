## 1. Model-scoped Groq cooldown

- [x] 1.1 Extend `key_pool` cooldown acquire/mark APIs with optional `scope` (model id); keep CF unscoped
- [x] 1.2 Wire `call_groq` to pass `resolved_model` as cooldown scope on acquire + 401/403/429 mark
- [x] 1.3 Add tests: next-key on 429 for same model; second model retries keys cooled on first model

## 2. Pool-size diagnostics

- [x] 2.1 Log groq/cf pool sizes in suggestions generate path; attach sizes on `SuggestionsError`
- [x] 2.2 Include `groq_pool_size` / `cf_pool_size` on `POST /suggestions` 503 JSON (no secrets)
- [x] 2.3 Short AGENTS.md note: model-scoped cooldown vs per-account RPD; how to read pool_size in errors/logs

## 3. Verification

- [x] 3.1 Run backend key-pool / related pytest
- [x] 3.2 Commit + push (LLM pool path only; no secrets)
