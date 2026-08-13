## Purpose

Provides an environment-driven pool of Groq and Cloudflare API credentials so suggestion generation can rotate and fall back across multiple accounts for rate-limit resilience without code changes when new keys are added.

## ADDED Requirements

### Requirement: Multi-credential loading from environment
The system SHALL load zero or more Groq API keys and zero or more Cloudflare credential pairs from environment variables. When plural multi-key variables are unset or empty, the system SHALL fall back to the existing single-key variables (`GROQ_API_KEY`, and `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`) so a one-key deployment continues to work unchanged. Empty entries after splitting SHALL be ignored. The system MUST NOT log full credential values.

#### Scenario: Plural Groq keys configured
- **WHEN** `GROQ_API_KEYS` contains two or more comma-separated non-empty keys
- **THEN** the Groq pool contains each of those keys as selectable credentials

#### Scenario: Single Groq key back-compat
- **WHEN** `GROQ_API_KEYS` is unset or empty and `GROQ_API_KEY` is set
- **THEN** the Groq pool contains exactly that one key

#### Scenario: Cloudflare parallel lists of equal length
- **WHEN** `CLOUDFLARE_ACCOUNT_IDS` and `CLOUDFLARE_API_TOKENS` are both set with the same number of comma-separated non-empty entries
- **THEN** the Cloudflare pool contains one credential per aligned account-id/token pair

#### Scenario: Cloudflare single-pair back-compat
- **WHEN** the plural Cloudflare lists are unset or empty and both `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` are set
- **THEN** the Cloudflare pool contains exactly that one credential pair

#### Scenario: Mismatched Cloudflare list lengths
- **WHEN** `CLOUDFLARE_ACCOUNT_IDS` and `CLOUDFLARE_API_TOKENS` are both set but have different numbers of non-empty entries after split
- **THEN** the system treats Cloudflare as not configured for pooling (empty pool) rather than pairing misaligned entries

### Requirement: Per-request credential selection
For each outbound call to a provider that has at least one non-cooled-down credential, the system SHALL select a credential from that provider's pool using a deterministic round-robin or random strategy among eligible credentials.

#### Scenario: Selection when multiple credentials are available
- **WHEN** a provider pool has two or more credentials that are not in cooldown
- **THEN** an outbound call uses one of those eligible credentials
- **AND** repeated calls eventually use more than one distinct credential when the pool size is greater than one

#### Scenario: No credentials configured
- **WHEN** a provider pool is empty
- **THEN** the provider reports as not configured (same observable outcome as missing single-key env today)

### Requirement: Cooldown and next-credential retry on auth or rate-limit errors
WHEN an outbound provider call fails with HTTP 401, 403, or 429 attributable to the selected credential, the system SHALL mark that credential unavailable for a short cooldown period and SHALL retry the same logical call with a different eligible credential from the same provider pool when one exists, before failing that provider. Non-auth/rate-limit failures MAY leave the credential eligible.

#### Scenario: Rate-limited key falls over to next key
- **WHEN** the first selected Groq (or Cloudflare) credential returns HTTP 429
- **AND** at least one other credential in that provider's pool is eligible
- **THEN** the system retries with a different credential from the same pool
- **AND** the failing credential is not selected again until its cooldown expires

#### Scenario: All credentials exhausted
- **WHEN** every credential in a provider pool is either in cooldown or has already failed the current call with 401/403/429
- **THEN** the provider call fails with an error that allows the existing suggestions failover chain to continue (e.g. Groq → Cloudflare → client WebLLM)

### Requirement: Secrets hygiene
The system SHALL never write full API keys or tokens to application logs, OpenSpec artifacts, or committed configuration examples. Committed examples MUST use empty or clearly fake placeholders only.

#### Scenario: Error logging redacts secrets
- **WHEN** a provider error message is logged after a failed call
- **THEN** the log content does not include the full credential string
