## Purpose

Generates AI-based correction suggestions for a Japanese-Chinese (or Chinese-Japanese) translation attempt by comparing an original text against a target (translated) text, either via the Gemini API or a deterministic mock, and returns a fixed-size list of pointed-out issues plus an overall comment.

## ADDED Requirements

### Requirement: Suggestion Generation Request and Response Contract
The system SHALL expose `POST /suggestions`, accepting a JSON body with required `originalText` and `targetText` string fields and optional `instructionPrompt`, `sessionId`, and `engine` string fields, and SHALL respond with a JSON object containing `suggestions` (an array of objects each with `id`, `original`, and `reason` string fields), `overallComment` (string), and `sessionId` (string).

#### Scenario: Well-formed request returns the expected response shape
- GIVEN a client sends `originalText` and `targetText`
- WHEN the client calls `POST /suggestions`
- THEN the response is HTTP 200 with a JSON body containing `suggestions`, `overallComment`, and `sessionId`
- AND each entry in `suggestions` contains `id`, `original`, and `reason`

### Requirement: Session Identifier Assignment
The system SHALL reuse the `sessionId` supplied in the request when present, and SHALL generate a new UUID-based `sessionId` when it is omitted or empty. The system SHALL record the session id in an in-memory, per-process session registry (not persisted to a database) on first use.

#### Scenario: sessionId omitted from the request
- GIVEN a request without a `sessionId` field
- WHEN `POST /suggestions` is called
- THEN the system generates a new UUID as the session id
- AND the generated id is returned in the response's `sessionId` field

#### Scenario: sessionId provided by the client
- GIVEN a request with an existing `sessionId` value
- WHEN `POST /suggestions` is called
- THEN the same `sessionId` value is echoed back in the response
- AND the session id is registered in the in-memory session registry if not already present

### Requirement: Generation Engine Selection
The system SHALL determine which suggestion-generation strategy to use from the request body's `engine` field, falling back to the `engine` query parameter if the body field is absent. WHEN `engine` resolves to `"gemini"`, the system SHALL use the Gemini-backed generator. Otherwise, the system SHALL use the `BACKEND_MODE` environment variable (default `"mock"`) to select a fallback strategy.

#### Scenario: engine explicitly set to gemini in the request body
- GIVEN a request with `"engine": "gemini"`
- WHEN `POST /suggestions` is called
- THEN the system invokes the Gemini-backed generation path

#### Scenario: engine passed only as a query parameter
- GIVEN a request with no `engine` field in the JSON body
- AND the request URL includes `?engine=gemini`
- WHEN `POST /suggestions` is called
- THEN the system invokes the Gemini-backed generation path

#### Scenario: no engine specified and BACKEND_MODE is not mock
- GIVEN a request with no `engine` field and no `engine` query parameter
- AND the `BACKEND_MODE` environment variable is set to a value other than `"mock"`
- WHEN `POST /suggestions` is called
- THEN the system does not return a valid `SuggestionResponse` body (no suggestion-generation branch is executed)

### Requirement: Mock Suggestion Fallback
WHEN the resolved `engine` is not `"gemini"` and `BACKEND_MODE` is `"mock"` (the default when unset), the system SHALL return a fixed set of exactly five hardcoded `CorrectionSuggestion` entries and a fixed `overallComment` string, regardless of the actual contents of `originalText` and `targetText`.

#### Scenario: Mock mode ignores request text content
- GIVEN `BACKEND_MODE` is unset or set to `"mock"`
- AND the request does not specify `engine=gemini`
- WHEN `POST /suggestions` is called with arbitrary `originalText`/`targetText` values
- THEN the response contains the same fixed five suggestions and fixed overall comment on every call
- AND the `sessionId` in the response still reflects the request/generated session id

### Requirement: Gemini Prompt Construction
WHEN the Gemini-backed generator is invoked, the system SHALL build a single prompt consisting of a fixed system instruction (in Chinese, requesting a JSON-formatted critique), a fixed few-shot example, and a "## 問題" section embedding the request's `originalText` and `targetText` verbatim. The `instructionPrompt` field, though accepted by the request contract, SHALL have no effect on the constructed prompt or the generated output.

#### Scenario: instructionPrompt is accepted but does not alter the prompt
- GIVEN a request with `engine=gemini` and a non-empty `instructionPrompt`
- WHEN the system builds the Gemini prompt
- THEN the constructed prompt contains only the fixed system instruction, the fixed few-shot example, and the `originalText`/`targetText` values
- AND the `instructionPrompt` text does not appear anywhere in the constructed prompt

### Requirement: Gemini API Invocation
WHEN `GEMINI_API_KEY` is configured and the Gemini-backed generator is invoked, the system SHALL send an HTTP POST to the Gemini `generateContent` REST endpoint for the model named by `GEMINI_MODEL` (default `"gemini-2.5-pro"`), authenticating via an `X-goog-api-key` header, with a 30-second request timeout.

#### Scenario: Successful call to the configured Gemini model
- GIVEN `GEMINI_API_KEY` is set and `GEMINI_MODEL` is unset (defaulting to `gemini-2.5-pro`)
- WHEN the Gemini-backed generator runs
- THEN the system issues a POST request to the `gemini-2.5-pro` `generateContent` endpoint with the API key in the `X-goog-api-key` header and a 30-second timeout

### Requirement: Missing Gemini API Key Fallback
WHEN `engine=gemini` is requested but `GEMINI_API_KEY` is not configured, the system SHALL skip the network call entirely and return an empty `suggestions` list with the overall comment `"Gemini APIキーが設定されていません"`.

#### Scenario: Gemini requested without an API key configured
- GIVEN `GEMINI_API_KEY` is unset or empty
- AND the request specifies `engine=gemini`
- WHEN `POST /suggestions` is called
- THEN no HTTP request is made to the Gemini API
- AND the response contains an empty `suggestions` array and the overall comment `"Gemini APIキーが設定されていません"`
- AND the response is still HTTP 200 with the correct `sessionId`

### Requirement: Gemini Successful Response Parsing and Normalization
WHEN the Gemini API returns a successful response containing a JSON object with a `指摘` (points) array and a `全体講評` (overall comment) string embedded in the model's text output, the system SHALL parse that embedded JSON, map each `指摘` entry's `箇所` and `コメント` fields to a suggestion's `original` and `reason` fields respectively (with sequential string `id`s starting at `"1"`), and use `全体講評` as the response's `overallComment`. The system SHALL always return exactly five suggestion entries: padding with empty placeholder entries (empty `original`/`reason`) if fewer than five points were returned, and truncating to the first five if more were returned.

#### Scenario: Gemini returns fewer than five points
- GIVEN the Gemini response's embedded JSON contains three `指摘` entries
- WHEN the response is parsed
- THEN the resulting `suggestions` array has exactly five entries
- AND the first three contain the parsed `original`/`reason` values with ids `"1"`-`"3"`
- AND the remaining two entries have empty `original` and `reason` values

#### Scenario: Gemini returns more than five points
- GIVEN the Gemini response's embedded JSON contains more than five `指摘` entries
- WHEN the response is parsed
- THEN the resulting `suggestions` array is truncated to exactly the first five entries

### Requirement: Gemini Malformed or Failed Response Handling
WHEN the Gemini API call fails (HTTP error status), the response is missing expected fields (`candidates`, `content`, or `parts`), or the model's text output does not contain a JSON object matching the expected `指摘` pattern, the system SHALL NOT raise an error to the caller. Instead it SHALL return exactly five empty placeholder suggestions and a descriptive fallback `overallComment`, and the endpoint SHALL still respond with HTTP 200.

#### Scenario: Gemini HTTP request fails
- GIVEN the Gemini API returns a non-2xx HTTP status or the request raises a network exception
- WHEN the Gemini-backed generator runs
- THEN the system returns five empty placeholder suggestions
- AND the `overallComment` starts with `"Gemini APIエラー: "` followed by the error detail
- AND `POST /suggestions` still responds with HTTP 200

#### Scenario: Gemini response text contains no parsable JSON
- GIVEN the Gemini API call succeeds but the returned text does not contain a JSON object matching the `指摘` pattern
- WHEN the response is parsed
- THEN the system returns five empty placeholder suggestions
- AND the `overallComment` is `"Gemini返答にJSONが見つかりませんでした"`

#### Scenario: Gemini response is missing expected structural fields
- GIVEN the Gemini API response JSON is missing `candidates`, `content`, or `parts`
- WHEN the response is parsed
- THEN the system treats this the same as a failed call, returning five empty placeholder suggestions and a `"Gemini APIエラー: "`-prefixed `overallComment`
