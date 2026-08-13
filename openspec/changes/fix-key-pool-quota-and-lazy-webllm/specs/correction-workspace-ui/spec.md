## ADDED Requirements

### Requirement: WebLLM only when offline mode is explicitly enabled
The workspace SHALL import, initialize, download, or call the WebLLM engine **only** when the user has explicitly enabled オフラインモード（WebLLM）. WHEN オフラインモード is off, the workspace MUST NOT use WebLLM on cloud API success **or** on any cloud API failure (including HTTP 429 quota/rate-limit, 503, network errors, or parse failures). Lightweight WebGPU capability checks that do not load `@mlc-ai/web-llm` MAY still run. When WebLLM is used (offline mode on), the engine entrypoint SHALL be loaded via lazy dynamic import.

#### Scenario: Successful cloud generation leaves WebLLM unloaded
- **WHEN** オフラインモード is off
- **AND** `POST /suggestions` (cloud) returns successfully
- **THEN** the page does not initialize a WebLLM engine
- **AND** no WebLLM model download is started for that generation

#### Scenario: Offline mode uses lazy WebLLM
- **WHEN** the user enables オフラインモード and starts generation
- **THEN** the client loads the WebLLM engine via dynamic import
- **AND** generation proceeds with the local engine

#### Scenario: Cloud API failure never auto-falls back to WebLLM
- **WHEN** オフラインモード is off
- **AND** the cloud suggestions request fails for any reason (429, 503, network, etc.)
- **THEN** the client does not import or call WebLLM
- **AND** the job is marked failed (or equivalent error state)
- **AND** the user sees an error toast or right-pane error describing the failure

### Requirement: Rate-limit and quota failures are visible
WHEN the cloud suggestions API reports rate-limit or quota exhaustion (`rate_limited` or equivalent), the workspace SHALL mark the job failed, SHALL show a toast or right-pane error that communicates quota/rate-limit, and SHALL NOT complete the job via WebLLM.

#### Scenario: 429/quota does not look like success
- **WHEN** `POST /suggestions` fails with a rate-limit/quota signal
- **AND** オフラインモード is off
- **THEN** the user sees an error toast or failed job entry describing rate-limit/quota
- **AND** the job is not marked completed with WebLLM suggestions

### Requirement: Saved proposals from shared DB appear while session is open
WHILE an authenticated user has a session selected, the workspace SHALL periodically refresh that session’s persisted correction histories and `ai_proposals` from the backend and update the right-pane History (saved proposals) when new rows appear. Device-local Job Queue items that have not been confirmed/saved MUST NOT be required to sync across browsers.

#### Scenario: Other client’s save appears after poll
- **WHEN** client A and client B both have the same `sessionId` open
- **AND** client A confirms and persists proposals to the shared database
- **THEN** within one polling interval, client B’s right-pane History shows the new saved proposal round without requiring a full page reload
