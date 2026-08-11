## Purpose

Provides fast cloud-based AI text correction suggestions via a backend API endpoint, with automatic provider failover and WebLLM as offline fallback.

## ADDED Requirements

### Requirement: Backend suggestions endpoint

The system SHALL expose an authenticated `POST /api/suggestions` endpoint that accepts Japanese text and returns correction suggestions in a structured JSON format.

#### Scenario: Successful suggestion generation

- **WHEN** authenticated user sends POST /api/suggestions with valid `originalText` and `targetText`
- **THEN** system returns JSON with `suggestions` array and `overallComment` string within 5 seconds

#### Scenario: Unauthenticated request rejected

- **WHEN** request is sent without valid Bearer token
- **THEN** system returns 401 Unauthorized

### Requirement: Groq as primary provider

The system SHALL use Groq's OpenAI-compatible API as the primary inference provider with model `llama-3.1-8b-instant` for fast response times (~1-3 seconds).

#### Scenario: Groq success path

- **WHEN** `GROQ_API_KEY` is configured and Groq API is available
- **THEN** system sends inference request to Groq and returns parsed response

#### Scenario: Groq API key missing

- **WHEN** `GROQ_API_KEY` environment variable is not set
- **THEN** system immediately falls back to Cloudflare Workers AI

### Requirement: Cloudflare Workers AI failover

The system SHALL automatically failover to Cloudflare Workers AI when Groq returns 429 (rate limit), 5xx (server error), or request times out (>10 seconds).

#### Scenario: Groq rate limited triggers fallback

- **WHEN** Groq returns HTTP 429
- **THEN** system retries with Cloudflare Workers AI and returns suggestions

#### Scenario: Groq server error triggers fallback

- **WHEN** Groq returns HTTP 5xx
- **THEN** system retries with Cloudflare Workers AI and returns suggestions

#### Scenario: Groq timeout triggers fallback

- **WHEN** Groq request exceeds 10 seconds without response
- **THEN** system cancels request and retries with Cloudflare Workers AI

#### Scenario: Both providers fail

- **WHEN** both Groq and Cloudflare Workers AI fail or are unavailable
- **THEN** system returns HTTP 503 with error message indicating service unavailable

### Requirement: Suggestion count targets quality over a fixed quantity

The system SHALL prompt the model to identify and return **up to 3** suggestions per request, prioritizing the most important issues when more are found. The system SHALL NOT pad, fabricate, or duplicate entries to force the count up to 3 (or any other number) — if the model genuinely finds fewer than 3 issues, the response SHALL contain only that smaller number of suggestions (including zero, when the text has no issues).

This intentionally supersedes the older (Gemini-era, now-removed) `ai-suggestion-generation` spec's "always exactly five, padded with empty placeholders" behavior: padding with empty/fake entries produces low-quality, misleading output and is explicitly disallowed. "3" is a target/max guideline for prompt engineering (per user direction: "AIの提案は3件でOK"), not a mandatory exact count enforced by application logic.

#### Scenario: Model finds 3 or more genuine issues

- **WHEN** the model identifies 3 or more correction points in the input text
- **THEN** the prompt guides it to return at most 3, focused on the most important/impactful issues

#### Scenario: Model finds fewer than 3 genuine issues

- **WHEN** the model identifies fewer than 3 correction points (including zero)
- **THEN** the response contains only the genuinely-found suggestions
- **AND** the system does not add empty or fabricated placeholder entries to reach 3

### Requirement: Consistent JSON response schema

The system SHALL return suggestions in the same JSON schema used by WebLLM: `{"suggestions": [{"id": string, "original": string, "reason": string}, ...], "overallComment": string}`.

#### Scenario: Response format matches WebLLM schema

- **WHEN** suggestion generation succeeds
- **THEN** response body contains `suggestions` array with `id`, `original`, `reason` fields and `overallComment` string

### Requirement: WebLLM remains as offline fallback

The system SHALL retain WebLLM client-side inference as a fallback when backend API is unavailable or returns errors.

#### Scenario: API unavailable triggers WebLLM fallback

- **WHEN** backend `/api/suggestions` returns network error or 5xx
- **THEN** frontend falls back to WebLLM for suggestion generation

#### Scenario: API keys not configured uses WebLLM

- **WHEN** neither `GROQ_API_KEY` nor Cloudflare credentials are configured
- **THEN** backend returns 503, frontend uses WebLLM

### Requirement: Environment variable configuration

The system SHALL read provider credentials from backend-only environment variables (never exposed to frontend).

#### Scenario: Required environment variables

- **WHEN** deploying to production
- **THEN** system requires `GROQ_API_KEY` and optionally `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` for full failover support

### Requirement: User can explicitly choose offline mode

The system SHALL provide a UI option (e.g., "オフライン生成" toggle or secondary button) allowing users to explicitly use WebLLM instead of the API.

#### Scenario: User selects offline mode

- **WHEN** user enables offline/WebLLM mode in UI
- **THEN** system bypasses API and uses WebLLM directly for that session
