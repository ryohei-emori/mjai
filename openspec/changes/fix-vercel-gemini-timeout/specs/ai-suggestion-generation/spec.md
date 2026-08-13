## ADDED Requirements

### Requirement: Suggestions wall-clock budget under Vercel maxDuration
The system SHALL bound `generate_suggestions` wall-clock time so that, when the budget is exhausted before a usable result, the endpoint returns HTTP 503 with a `SuggestionsError` (including non-secret `gemini_pool_size` / `groq_pool_size` / `cf_pool_size` when available) rather than continuing until the Vercel platform emits `504 FUNCTION_INVOCATION_TIMEOUT`. The wall-clock budget SHALL be strictly less than the configured `api/index.py` `maxDuration`.

#### Scenario: Wall-clock budget exhausted mid-failover
- GIVEN providers are configured and a suggestions request is in progress
- AND elapsed time reaches the suggestions wall-clock budget before a usable parsed response
- WHEN the budget check runs
- THEN the system raises `SuggestionsError` (mapped to HTTP 503)
- AND the response is not left to the platform function-invocation timeout

### Requirement: Gemini HTTP timeout fits platform budget
The Gemini provider HTTP client timeout SHALL be low enough that a single Gemini attempt (and, with in-provider model rotation, a bounded second attempt) is compatible with the Vercel `maxDuration` and the suggestions wall-clock budget. Unconfigured Gemini (empty credential pool) SHALL be skipped without waiting on a Gemini HTTP call.

#### Scenario: Gemini not configured skips immediately
- GIVEN no Gemini credentials are loaded
- AND Groq (or Cloudflare) is configured
- WHEN `generate_suggestions` runs
- THEN the system does not perform a Gemini HTTP request
- AND proceeds to the next configured provider

#### Scenario: Gemini HTTP client uses a bounded timeout
- GIVEN Gemini credentials are configured
- WHEN the Gemini provider issues `generateContent`
- THEN the HTTP client timeout is at most 25 seconds
