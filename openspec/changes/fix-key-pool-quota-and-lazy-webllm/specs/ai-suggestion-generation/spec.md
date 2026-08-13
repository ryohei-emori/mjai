## ADDED Requirements

### Requirement: Fair credential failover without double-counting env keys
The cloud suggestion path SHALL load each provider’s credentials such that when plural multi-key environment variables are non-empty after parse, singular back-compat variables for that provider are ignored (no duplicate entries from setting both). Duplicate identical keys within a plural list SHALL be treated as a single credential. On HTTP 401/403/429 for a selected credential, the system SHALL cool that credential down and try another eligible credential in the same provider pool before failing that provider.

#### Scenario: Plural overrides singular without merging
- **WHEN** `GROQ_API_KEYS` contains two distinct keys and `GROQ_API_KEY` is also set to a third value
- **THEN** outbound Groq calls use only the two plural keys
- **AND** the singular key is not selected

#### Scenario: Rate-limited key is skipped for next attempt
- **WHEN** the first selected credential for a provider returns HTTP 429
- **AND** another credential in that provider pool is eligible
- **THEN** the system retries with a different credential before failing the provider
- **AND** the rate-limited credential is not selected again until its cooldown expires

### Requirement: Clear rate-limit / quota failure signal to the client
WHEN every configured cloud provider fails because all of its credentials are rate-limited, in cooldown, or exhausted for the request, `POST /suggestions` SHALL return an error response that indicates rate-limit or quota exhaustion (HTTP 503 is acceptable) and includes a human-readable message that names the failing provider family without exposing API key or token values. The response MAY include redacted/diagnostic fields such as which provider failed, but MUST NOT include full secrets.

#### Scenario: All Groq and Cloudflare credentials rate-limited
- **WHEN** every Groq credential returns HTTP 429 (or is already cooled) and every Cloudflare credential likewise fails with 401/403/429 or is cooled
- **THEN** the client receives a non-success response for suggestion generation
- **AND** the error payload indicates rate-limit or quota exhaustion in a message safe for operators
- **AND** the payload does not contain full API keys or tokens
