## ADDED Requirements

### Requirement: Multi-key provider configuration is accepted
The suggestion-generation path SHALL treat a provider as configured when either the legacy single-key environment variables or the plural multi-key / parallel-list environment variables yield at least one usable credential for that provider. The HTTP contract for `POST /suggestions` (request/response shape) SHALL remain unchanged.

#### Scenario: Groq available via plural keys only
- **WHEN** `GROQ_API_KEY` is unset and `GROQ_API_KEYS` contains at least one non-empty key
- **AND** a client requests suggestion generation through the cloud API path
- **THEN** the system MAY attempt Groq using a key from that pool (same as if `GROQ_API_KEY` were set)

#### Scenario: Cloudflare available via parallel lists only
- **WHEN** `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` are unset
- **AND** `CLOUDFLARE_ACCOUNT_IDS` and `CLOUDFLARE_API_TOKENS` yield at least one valid pair
- **AND** Groq is unavailable or fails
- **THEN** the system MAY attempt Cloudflare using a credential from that pool

#### Scenario: Neither single nor plural credentials configured
- **WHEN** neither Groq nor Cloudflare has any usable credential from single or plural env vars
- **THEN** the system responds with provider-unavailable behavior consistent with today's unconfigured providers (e.g. HTTP 503) so the client can fall back to WebLLM
