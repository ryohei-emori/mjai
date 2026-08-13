## ADDED Requirements

### Requirement: Job Queue MUST NOT claim unconfirmed jobs are device-local

The Job Queue panel description SHALL describe only the current processing mode (sequential WebLLM vs. parallel cloud API with its concurrency limit). It MUST NOT state or imply that unconfirmed jobs exist only on the current device or that they reach the shared database only after the user confirms and saves, because suggestions are persisted as a `pending` history with proposals at generation time and are merged back into the Job Queue on other devices.

#### Scenario: Job Queue description omits the device-local note

- **WHEN** the Job Queue panel is rendered with at least one job
- **THEN** its description states the processing mode and does not claim unconfirmed jobs are limited to this device

#### Scenario: Genuine persistence failure is still communicated

- **WHEN** generation succeeds but persisting the pending history to the shared database fails
- **THEN** the user is still told that the suggestions are shown but the save failed and the job remains on this device
