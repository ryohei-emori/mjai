## Why

Groq and Cloudflare free-tier rate limits and per-account quotas make a single API key a fragility point for suggestion generation. Supporting multiple credentials per provider (rotated with cooldown on 401/403/429) improves stability now and leaves a clear path to add more accounts later without code changes.

## What Changes

- Add an abstracted **API key pool** module that loads multiple credentials per LLM provider from environment variables and selects one per outbound request.
- On auth/rate-limit failures (401/403/429), mark the failing credential for a short cooldown and retry with the next available credential before failing the provider.
- Env convention for multi-key config with full **backward compatibility** for existing single-key vars (`GROQ_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`) so current Vercel/production setup keeps working unchanged.
- Wire the pool into Groq and Cloudflare providers (and thus the suggestions failover chain) so every outbound call goes through credential selection.
- Unit tests for selection, cooldown, next-key fallback, and single-key back-compat.
- Document the convention in `AGENTS.md` and `conf/.env.example` (placeholders only; real secrets stay in gitignored `conf/.env`).

## Capabilities

### New Capabilities
- `llm-api-key-pool`: Multi-credential loading, selection, cooldown, and retry for Groq and Cloudflare LLM API keys driven by environment variables.

### Modified Capabilities
- `ai-suggestion-generation`: Suggestion generation SHALL treat multi-key env configuration as a valid provider configuration (in addition to the existing single-key vars), without changing the HTTP API contract for `POST /suggestions`.

## Impact

- **Code**: new `backend/app/llm/key_pool.py` (or equivalent); updates to `groq_provider.py`, `cloudflare_provider.py`, possibly `suggestions.py` availability checks; new unit tests under `backend/tests/`.
- **Config**: `conf/.env.example`, local `conf/.env` (gitignored), `AGENTS.md` env tables.
- **Runtime**: Vercel/production may keep using single keys; adding comma-separated / parallel multi-key vars is optional. No public API shape change.
- **Security**: never commit real keys; redact in logs and docs.
