## ADDED Requirements

### Requirement: Optional Codex async transport failures MUST fall back to the cloud provider chain
The system SHALL treat the Codex CLI asynchronous transport as an optional first provider path. If async task submission, response validation, polling, or completion fails for a recoverable transport or server reason, the same user request MUST continue through the established synchronous Gemini → Groq → Cloudflare chain. A Codex failure MUST NOT prevent a configured cloud provider from answering.

#### Scenario: Codex gateway is not configured
- **WHEN** async task submission reports that the Codex gateway is not configured
- **THEN** the request continues through the synchronous cloud provider chain

#### Scenario: Codex task submission fails
- **WHEN** the configured Codex gateway returns a server error or cannot be reached during task submission
- **THEN** the request continues through the synchronous cloud provider chain
- **AND** the Codex error is not presented as the final result if a cloud provider succeeds

#### Scenario: Codex task polling fails
- **WHEN** an accepted Codex task later returns a recoverable server, missing-task, malformed-response, network, or polling-timeout failure
- **THEN** the original request continues through the synchronous cloud provider chain

#### Scenario: Codex async generation succeeds
- **WHEN** Codex task submission and polling produce a valid completed suggestion response
- **THEN** that response is returned
- **AND** no synchronous cloud-provider request is started

#### Scenario: Fallback providers also fail
- **WHEN** the Codex async path fails recoverably
- **AND** Gemini, Groq, and Cloudflare cannot produce a usable answer
- **THEN** the final error reflects the synchronous provider-chain diagnostics and fallback availability

### Requirement: Terminal request and authentication errors MUST remain terminal
The system MUST NOT use provider fallback to hide a request that is unauthenticated, unauthorized, or invalid before provider selection. Client and authentication failures SHALL be returned to the caller without starting another generation path.

#### Scenario: Authentication fails on async submission
- **WHEN** async task submission returns an authentication or authorization failure
- **THEN** the failure is returned to the caller
- **AND** the synchronous provider chain is not started

#### Scenario: Suggestion input is invalid
- **WHEN** the server rejects the suggestion request as invalid input
- **THEN** the validation failure is returned to the caller
- **AND** provider fallback does not retry the invalid request

### Requirement: Production API requests MUST use a normalized same-origin base
The deployed frontend SHALL remove surrounding whitespace and redundant trailing slashes from the configured API base URL. When no non-whitespace production API base is configured, requests MUST use the same-origin `/api` path and MUST NOT target localhost.

#### Scenario: Production API base contains trailing whitespace
- **WHEN** the production API base contains a valid path followed by whitespace
- **THEN** browser requests use the normalized path without whitespace

#### Scenario: Production API base is empty
- **WHEN** the production API base is unset, empty, or whitespace-only
- **THEN** browser requests use `/api`
- **AND** no request targets `localhost:8000`

#### Scenario: Local development API base is empty
- **WHEN** the API base is unset during local development
- **THEN** browser requests use `http://localhost:8000`

### Requirement: Async failover behavior MUST have contract-level regression coverage
Automated tests SHALL cover the observable async response states and SHALL fail if a recoverable Codex error once again prevents the cloud chain from running.

#### Scenario: Frontend transport contract is tested
- **WHEN** the frontend test suite runs
- **THEN** it verifies unconfigured, submission-failed, polling-failed, malformed-success, timed-out, and successful Codex async responses
- **AND** it verifies whether the synchronous endpoint is called exactly when required

#### Scenario: Backend async endpoint contract is tested
- **WHEN** the backend test suite runs
- **THEN** it distinguishes an unconfigured gateway from a configured gateway whose submission fails
- **AND** it verifies the async endpoint's status and JSON response shapes

#### Scenario: Existing request body options remain covered
- **WHEN** optional exemplar input tests run through either the async-success or cloud-fallback path
- **THEN** they verify that omitted, whitespace-only, and trimmed exemplar values retain their documented request shape
