## Why

Operators see “Quota Exceeded” / rate-limit 503s and assume the multi-key pool still has unused quota. Investigation showed next-key retry on 429 already works within a single model call, but **Groq model rotation cools keys globally for ~60s after the first model’s 429**, so the second model never retries those keys even when limits are per-model. Separately, hard RPD is per account (pool does not raise it), and removing WebLLM auto-fallback made real cloud failures visible. We need correct per-model cooldown scoping plus pool-size diagnostics on the error path.

## What Changes

- Scope Groq credential cooldown by **model id** so a 429 on model A does not block the same key for model B in `call_groq_with_rotation`.
- Keep Cloudflare cooldown credential-scoped (no model rotation).
- Log and return non-secret pool sizes (`groq_pool_size`, `cf_pool_size`) on suggestion failures / 503 payloads.
- Add regression tests for model-scoped cooldown + rotation retry.
- Brief AGENTS.md note on model-scoped cooldown vs account RPD.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestion-generation`: Groq 429 cooldown must be model-scoped so in-provider model rotation can still use the key pool; quota/rate-limit 503 responses include pool sizes without secrets.

## Impact

- Backend: `key_pool.py`, `groq_provider.py`, `suggestions.py`, `main.py`, `test_key_pool.py`
- Docs: `AGENTS.md` (short note)
- Frontend: optional read of new diagnostic fields only if already parsing 503 JSON (no required UI change; avoid `page.tsx` large edits)
- No env var renames; Production already has `GROQ_API_KEYS` / CF plural vars
