## Why

Suggestion generation currently fails over Groq → Cloudflare only. When both are rate-limited or return unusable content, the cloud path hard-fails (WebLLM is toggle-only). Adding Gemini free-tier Flash as a third provider with a multi-key pool improves resilience and raises salvage quality for JP↔CN translation critique (structured JSON + Chinese reasons) without changing the frontend contract.

## What Changes

- Add a Gemini Generative Language API provider (`generateContent` / v1beta) with env-driven credential pooling (`GEMINI_API_KEYS` plural wins; optional `GEMINI_API_KEY` singular back-compat; optional `GEMINI_MODEL` pin), mirroring Groq/CF pool patterns (round-robin, cooldown on 401/403/429).
- Extend the suggestions failover / same-pass content-salvage chain to include Gemini after Cloudflare (default order: Groq → Cloudflare → Gemini).
- Curated free-tier Flash model allow-list / rotation (stable IDs, not floating `-latest`), documented with research rationale.
- Reuse existing `parser.py` JSON hardening and Chinese-enforcement / parse-retry loops so Gemini participates in salvage and outer retries.
- Update ops docs: `conf/.env.example` (placeholders only), `AGENTS.md`, and `docs/SYSTEM-DESIGN.md` — replace obsolete “do not configure GEMINI_*” guidance with current Gemini pool ops.
- Unit tests for Gemini credential load/select/cooldown, provider call shape, and failover inclusion.
- No frontend `NEXT_PUBLIC_*` Gemini keys; offline WebLLM remains explicit toggle-only.

## Capabilities

### New Capabilities
- `gemini-llm-provider`: Gemini API key pool, model selection, and `generateContent` provider used by suggestion generation.

### Modified Capabilities
- `ai-suggestions`: Cloud suggestion failover SHALL include Gemini after Groq and Cloudflare; 503 / pool-size reporting SHALL expose Gemini pool size when relevant; provider-configured checks SHALL treat Gemini as a valid cloud provider.
- `architecture-documentation`: As-built docs (`AGENTS.md`, `docs/SYSTEM-DESIGN.md`) SHALL describe the three-provider chain and Gemini env/ops conventions.

## Impact

- **Code**: new `backend/app/llm/gemini_provider.py`; extend `key_pool.py`, `suggestions.py`, and related tests; possibly 503 JSON fields in the suggestions route.
- **Config**: `GEMINI_API_KEYS` / `GEMINI_API_KEY` / `GEMINI_MODEL` in gitignored `conf/.env` and Vercel sensitive env (never committed).
- **External service**: Google Generative Language API (new dependency in the failover chain).
- **API**: no breaking change to `POST /suggestions` request/response shape; optional additive diagnostics (`gemini_pool_size`).
- **Security**: never commit real keys; redact in logs; no browser exposure of Gemini secrets.
