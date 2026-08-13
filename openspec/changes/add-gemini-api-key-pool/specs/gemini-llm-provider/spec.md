## Purpose

Provides Gemini Generative Language API inference for suggestion generation via an environment-driven API key pool, stable free-tier Flash model selection, and `generateContent` calls that return text suitable for the shared JSON suggestion parser.

## ADDED Requirements

### Requirement: Multi-key Gemini credential loading
The system SHALL load zero or more Gemini API keys from environment variables. WHEN `GEMINI_API_KEYS` is non-empty after comma-split, the system SHALL use those keys as the Gemini pool and MUST NOT merge in `GEMINI_API_KEY`. WHEN `GEMINI_API_KEYS` is unset or empty and `GEMINI_API_KEY` is set, the system SHALL use that single key. Duplicate identical keys in a plural list SHALL collapse to one entry. Empty split entries SHALL be ignored. The system MUST NOT log full Gemini API key values.

#### Scenario: Plural Gemini keys configured
- **WHEN** `GEMINI_API_KEYS` contains two comma-separated non-empty keys
- **THEN** the Gemini pool contains two selectable credentials

#### Scenario: Singular Gemini key back-compat
- **WHEN** `GEMINI_API_KEYS` is unset or empty and `GEMINI_API_KEY` is set
- **THEN** the Gemini pool contains exactly that one key

#### Scenario: No Gemini keys
- **WHEN** both `GEMINI_API_KEYS` and `GEMINI_API_KEY` are unset or empty
- **THEN** Gemini is treated as not configured

### Requirement: Per-request Gemini key selection with cooldown
For each outbound Gemini call when the pool is non-empty, the system SHALL select a credential via round-robin among keys that are not in cooldown. WHEN a call fails with HTTP 401, 403, or 429 attributable to the selected key, the system SHALL cool that key down for a short period and SHALL retry with a different eligible key from the Gemini pool when one exists, before failing the Gemini provider.

#### Scenario: Rate-limited Gemini key falls over to next key
- **WHEN** the first selected Gemini key returns HTTP 429
- **AND** at least one other Gemini key is eligible
- **THEN** the system retries with a different Gemini key
- **AND** the failing key is not selected again until its cooldown expires

#### Scenario: All Gemini keys exhausted
- **WHEN** every Gemini key is in cooldown or has already failed the current call with 401/403/429
- **THEN** the Gemini provider call fails so the suggestions chain can surface an all-providers-failed error (or return a prior soft-failed body from earlier providers)

### Requirement: Gemini generateContent invocation
WHEN Gemini is invoked for suggestion generation, the system SHALL send an HTTP POST to the Google Generative Language `generateContent` endpoint (v1beta) for the selected model id, authenticate with the selected API key (query `key` and/or `x-goog-api-key` header), and request JSON-oriented text output suitable for the shared suggestion parser. The request MUST use a bounded timeout. Secrets MUST NOT appear in application logs.

#### Scenario: Successful Gemini call returns model text
- **WHEN** Gemini credentials are configured and the API returns a successful candidate with text parts
- **THEN** the provider returns that concatenated text to the suggestions layer for parsing

#### Scenario: Gemini model pin via env
- **WHEN** `GEMINI_MODEL` is set to a non-empty model id
- **THEN** every Gemini request uses that exact model id (rotation disabled)

#### Scenario: Default free-tier Flash rotation when unpinned
- **WHEN** `GEMINI_MODEL` is unset or empty
- **THEN** the system selects a model from a curated allow-list of stable free-tier Flash model ids (not floating `*-latest` aliases as the default pool)

### Requirement: Gemini secrets hygiene
Committed configuration examples SHALL document `GEMINI_API_KEYS`, optional `GEMINI_API_KEY`, and optional `GEMINI_MODEL` with placeholders only. Real keys MUST remain in gitignored local env and/or Vercel sensitive environment variables, never in OpenSpec artifacts, commits, or frontend `NEXT_PUBLIC_*` variables.

#### Scenario: Example env uses placeholders
- **WHEN** a contributor opens `conf/.env.example`
- **THEN** Gemini-related entries are empty or clearly fake placeholders
- **AND** no real Gemini API key string is present
