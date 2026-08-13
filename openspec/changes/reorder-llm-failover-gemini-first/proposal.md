## Why

After `add-gemini-api-key-pool`, cloud suggestions fail over Groq → Cloudflare → Gemini. Operators now prefer quality-first ordering: try Gemini free-tier Flash first, then Groq, then Cloudflare, so salvage/failover still covers rate limits while the happy path uses the stronger critique model.

## What Changes

- Reorder the suggestions failover / same-pass content-salvage chain to **Gemini → Groq → Cloudflare** (was Groq → Cloudflare → Gemini).
- Keep existing key pools, in-provider model rotation, Chinese/JSON outer retries, 503 pool-size diagnostics, and toggle-only WebLLM unchanged.
- Update as-built docs (`AGENTS.md`, `docs/SYSTEM-DESIGN.md`) and `conf/.env.example` comments that document provider order.
- Adjust unit tests that assert Groq-first ordering.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `ai-suggestion-generation`: Cloud suggestion failover order SHALL be Gemini → Groq → Cloudflare; same-pass salvage SHALL follow that order.
- `architecture-documentation`: As-built docs SHALL describe Gemini-primary failover (not Groq-primary / Gemini-tertiary).

## Impact

- **Code**: `backend/app/llm/suggestions.py` (and module comments in related llm package files); tests in `backend/tests/test_llm_suggestions.py`.
- **Docs/ops**: `AGENTS.md`, `docs/SYSTEM-DESIGN.md`, `conf/.env.example` comments only (no secret changes).
- **API**: no request/response contract change; latency of the happy path may increase when Gemini is slower than Groq.
- **Security**: no key exposure; env vars unchanged.
