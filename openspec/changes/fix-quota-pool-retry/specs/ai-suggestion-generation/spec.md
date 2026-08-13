## ADDED Requirements

### Requirement: Model-scoped Groq credential cooldown
When a Groq credential returns HTTP 401/403/429, the system SHALL cool that credential down only for the **model id** used in that attempt. A credential cooled for model A SHALL remain eligible for a different model B in the same process during in-provider model rotation, unless model B has also cooled it. Cloudflare credential cooldown MAY remain credential-wide (no model rotation).

#### Scenario: Second Groq model retries keys cooled on first model 429
- **WHEN** rotation is enabled and the first selected Groq model returns HTTP 429 for every key in the pool
- **AND** a second distinct model is selected for in-provider retry
- **THEN** the second model attempt SHALL be allowed to try those keys again (they are not blocked by the first model’s cooldown alone)
- **AND** if a key returns 429 again for the second model, that key is cooled for the second model

#### Scenario: Same model still skips a cooled key
- **WHEN** a Groq credential was cooled for model M after HTTP 429
- **AND** another request (or retry) targets the same model M before the cooldown expires
- **AND** another credential is eligible
- **THEN** the system selects a different credential for model M

### Requirement: Pool size diagnostics on quota / rate-limit failures
When `POST /suggestions` fails because cloud providers are rate-limited or quota-exhausted, the error response SHALL include non-secret diagnostic fields for how many Groq and Cloudflare credentials were loaded for the process (`groq_pool_size`, `cf_pool_size` or equivalent). Values MUST NOT include API keys, tokens, or raw secret material. Server logs for suggestion attempts SHOULD record the same pool sizes.

#### Scenario: Quota exhausted response includes pool sizes
- **WHEN** every configured provider fails with rate-limit / cooldown / quota exhaustion for a suggestion request
- **THEN** the 503 (or equivalent) JSON body includes numeric Groq and Cloudflare pool sizes
- **AND** the body does not contain full API keys or tokens
