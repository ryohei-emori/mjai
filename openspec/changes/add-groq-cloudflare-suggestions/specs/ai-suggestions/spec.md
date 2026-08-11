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

### Requirement: Suggestion count targets thoroughness over an artificial cap

The system SHALL prompt the model to identify and return **at least 5** suggestions per request, actively searching across word choice, register/politeness, punctuation, natural phrasing, and structure rather than stopping at the first few obvious issues. The system SHALL NOT pad, fabricate, or duplicate entries to force the count up to 5 (or any other number) — if the model genuinely finds fewer than 5 issues after a thorough pass, the response SHALL contain only that smaller number of suggestions (including zero, when the text has no issues).

This reverses the previous "up to 3, no padding" direction (see superseded scenarios below) per explicit user direction ("AIによる提案内容は５個以上にしてください" — 2026-08): the "up to 3" cap was found to under-deliver value for a correction-exercise use case where there is almost always more than 3 genuine points worth noting. The anti-fabrication rule from the "up to 3" era is preserved unchanged: quality/authenticity of each suggestion still takes priority over hitting any specific number.

#### Scenario: Model finds 5 or more genuine issues

- **WHEN** the model identifies 5 or more correction points in the input text
- **THEN** the prompt guides it to return all of them (no upper cap), or at minimum the 5 most impactful, rather than truncating early

#### Scenario: Model finds fewer than 5 genuine issues on a first pass

- **WHEN** the input text is short or superficially clean
- **THEN** the prompt directs the model to look harder across additional dimensions (word choice, register/politeness, punctuation, natural phrasing, structure) before concluding fewer than 5 issues exist

#### Scenario: Model genuinely finds fewer than 5 issues after a thorough pass

- **WHEN** the model, after being prompted to search thoroughly, still identifies fewer than 5 correction points (including zero)
- **THEN** the response contains only the genuinely-found suggestions
- **AND** the system does not add empty or fabricated placeholder entries to reach 5

#### Scenario (superseded, kept for history): "up to 3" era behavior

- Previously: the system prompted for **up to 3** suggestions, prioritizing the most important issues when more were found, with no padding to reach 3. This is no longer current behavior as of this revision — see "Model finds 5 or more genuine issues" above — but is kept here as a record of the requirement's evolution (Gemini-era "always exactly five, padded" → "up to 3, no padding" → "at least 5, no padding").

### Requirement: Consistent JSON response schema

The system SHALL return suggestions in the same JSON schema used by WebLLM: `{"suggestions": [{"id": string, "original": string, "reason": string}, ...], "overallComment": string}`.

#### Scenario: Response format matches WebLLM schema

- **WHEN** suggestion generation succeeds
- **THEN** response body contains `suggestions` array with `id`, `original`, `reason` fields and `overallComment` string

### Requirement: Bilingual field content — Chinese explanations, Japanese corrected text

The system's users are Chinese speakers correcting/learning Japanese text. The system SHALL prompt the model so that explanation-oriented fields (`reason` on each suggestion, and `overallComment`) are written in **Chinese (Simplified)**, while the `original` field (the excerpt of corrected/flagged Japanese text itself) remains in **Japanese**, matching the language of the input `originalText`/`targetText`. Field names and the JSON schema itself are unchanged — only the prompted content language differs per field.

This corrects a prior overcorrection: an earlier bug caused the *entire* response (including the corrected Japanese text) to come out as garbled mixed-language output, because the backend system prompt had been ported from the frontend's Chinese WebLLM prompt without adapting it to the backend's Japanese-only proofreading task. The fix at the time rewrote the entire backend prompt to Japanese, which also flipped the explanation fields to Japanese — overcorrecting, since the target audience (Chinese speakers) benefits from Chinese explanations. This requirement restores Chinese explanations while explicitly keeping the corrected-text field in Japanese, avoiding a repeat of the original garbled-output bug.

#### Scenario: Suggestion reason is in Chinese

- **WHEN** suggestion generation succeeds
- **THEN** each suggestion's `reason` field is written in Simplified Chinese

#### Scenario: Overall comment is in Chinese

- **WHEN** suggestion generation succeeds
- **THEN** the `overallComment` field is written in Simplified Chinese

#### Scenario: Corrected/flagged text stays in Japanese

- **WHEN** suggestion generation succeeds
- **THEN** each suggestion's `original` field remains in Japanese (the same language as the input text) and is NOT translated into Chinese

### Requirement: Automatic retry on JSON parse failure

The system SHALL automatically retry suggestion generation up to a bounded total number of attempts when a provider's response fails to parse as valid JSON (i.e. `extract_json`/`repair_truncated_json` both fail to produce parseable content), before giving up and returning the existing parse-failure placeholder response. This is a distinct retry axis from the existing network-level retry (Groq 429/5xx/timeout in-provider model rotation, and the Groq→Cloudflare provider failover): it exists to handle cases where a provider responds successfully at the HTTP level but the *content* is not valid/parseable JSON (e.g. a small/preview model emitting reasoning tokens, prose, or truncated output instead of clean JSON).

#### Scenario: Parse fails on early attempts, succeeds on a later attempt

- **WHEN** the first attempt's response fails to parse as JSON, and a retry is issued
- **AND** a subsequent attempt (within the bounded retry budget) returns a response that parses successfully
- **THEN** the system returns the successfully-parsed suggestions from that attempt, without surfacing the earlier parse failures to the caller

#### Scenario: All retry attempts fail to parse

- **WHEN** every attempt within the bounded retry budget fails to parse as JSON
- **THEN** the system gives up and returns the existing parse-failure placeholder response (empty `suggestions`, explanatory `overallComment`) rather than retrying indefinitely

#### Scenario: Retry axis is additive with, not a replacement for, network-level retry

- **WHEN** a provider request fails at the network/HTTP level (429/5xx/timeout)
- **THEN** it is handled by the existing network-level retry/failover logic (Groq model rotation, then Cloudflare), unaffected by the JSON-parse retry budget
- **AND** the JSON-parse retry budget only applies to responses that succeeded at the network level but failed to parse as content

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
