## ADDED Requirements

### Requirement: Gemini-primary cloud failover order
The system SHALL attempt cloud suggestion providers in this default order when configured: Gemini (primary), then Groq (secondary), then Cloudflare Workers AI (tertiary). Gemini SHALL participate in same-pass content salvage first: WHEN Gemini returns network success but unusable content (empty, unparseable JSON, or failing Chinese critique-field checks), the system SHALL still try Groq, then Cloudflare, in that pass before returning the best available soft-failed body to the outer parse/language retry loop. WebLLM MUST NOT start automatically when all cloud providers fail.

#### Scenario: Gemini succeeds as primary
- **WHEN** Gemini credentials are configured and Gemini returns usable parsed suggestions
- **THEN** `POST /suggestions` returns those suggestions
- **AND** Groq and Cloudflare are not required for success

#### Scenario: Gemini fails, Groq succeeds
- **WHEN** Gemini fails or is unconfigured or returns unusable content
- **AND** Groq credentials are configured and Groq returns usable parsed suggestions
- **THEN** `POST /suggestions` returns the Groq suggestions successfully

#### Scenario: Gemini and Groq fail, Cloudflare succeeds
- **WHEN** Gemini and Groq fail, are unconfigured, or return unusable content
- **AND** Cloudflare credentials are configured and Cloudflare returns usable suggestions
- **THEN** `POST /suggestions` returns the Cloudflare suggestions successfully

#### Scenario: Same-pass salvage follows Gemini → Groq → Cloudflare
- **WHEN** Gemini returns HTTP-OK but unusable content
- **AND** Groq returns HTTP-OK but unusable content
- **AND** Cloudflare returns usable Chinese JSON suggestions
- **THEN** the system returns the Cloudflare-parsed result without requiring a separate user action

#### Scenario: All three cloud providers fail
- **WHEN** Gemini, Groq, and Cloudflare all fail at the network level or are unconfigured
- **THEN** the system raises a provider-failure error suitable for HTTP 503
- **AND** the frontend does not auto-start WebLLM
