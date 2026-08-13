## ADDED Requirements

### Requirement: Gemini as tertiary cloud failover after Cloudflare
The system SHALL extend the cloud suggestion failover chain so that after Groq (primary) and Cloudflare Workers AI (secondary), Gemini is attempted when configured. Default order SHALL be Groq → Cloudflare → Gemini. Gemini SHALL participate in same-pass content salvage: WHEN Groq and/or Cloudflare return network success but unusable content (empty, unparseable JSON, or failing Chinese critique-field checks), the system SHALL still try Gemini in that pass before returning the best available soft-failed body to the outer parse/language retry loop. WebLLM MUST NOT start automatically when Gemini (or earlier providers) fail.

#### Scenario: Groq and Cloudflare fail, Gemini succeeds
- **WHEN** Groq fails or is unconfigured
- **AND** Cloudflare fails or is unconfigured
- **AND** Gemini credentials are configured and Gemini returns usable parsed suggestions
- **THEN** `POST /suggestions` returns those suggestions successfully

#### Scenario: Same-pass salvage reaches Gemini after unusable Groq and CF bodies
- **WHEN** Groq returns HTTP-OK but unusable content
- **AND** Cloudflare returns HTTP-OK but unusable content
- **AND** Gemini returns usable Chinese JSON suggestions
- **THEN** the system returns the Gemini-parsed result without requiring a separate user action

#### Scenario: All three cloud providers fail
- **WHEN** Groq, Cloudflare, and Gemini all fail at the network level or are unconfigured
- **THEN** the system raises a provider-failure error suitable for HTTP 503
- **AND** the frontend does not auto-start WebLLM

### Requirement: Gemini counts toward configured cloud providers
The system SHALL treat a non-empty Gemini credential pool as a configured cloud provider for suggestion generation. WHEN at least one of Groq, Cloudflare, or Gemini is configured, the system SHALL NOT report “no providers configured.”

#### Scenario: Only Gemini configured
- **WHEN** Gemini keys are set and Groq/Cloudflare credentials are unset
- **THEN** suggestion generation proceeds using Gemini without requiring Groq or Cloudflare

### Requirement: Gemini pool size in failure diagnostics
WHEN suggestion generation fails after exhausting configured cloud providers, the error payload / logs SHALL include Gemini pool size counts (integer size only, no secrets), alongside existing Groq and Cloudflare pool size fields when those are already reported.

#### Scenario: 503 includes gemini_pool_size
- **WHEN** all configured providers fail
- **AND** two Gemini keys are loaded in the pool
- **THEN** the failure response or structured error includes `gemini_pool_size` equal to 2
- **AND** no Gemini API key material appears in the response
