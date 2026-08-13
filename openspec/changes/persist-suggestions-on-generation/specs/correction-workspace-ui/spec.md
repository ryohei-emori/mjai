## ADDED Requirements

### Requirement: Persist Suggestions When Generation Completes
After a Job Queue item successfully produces suggestions (cloud API, or WebLLM only when オフラインモード is ON), the UI SHALL persist a pending correction history and the full suggestion set to the backend before or as the job is shown as completed in the right pane. Persistence failures SHALL surface a non-blocking error (toast) but SHALL NOT clear the in-memory completed job. The UI SHALL NOT auto-start WebLLM on cloud failure.

#### Scenario: Cloud generation success writes pending history
- **WHEN** a cloud suggestion job completes successfully
- **THEN** the UI creates a pending history for the session with original/target text, overall comment, provider indicating cloud, and the job id
- **AND** creates one AI proposal per suggestion
- **AND** stores the returned `historyId` on the completed job for later confirm

#### Scenario: Offline WebLLM success also persists
- **WHEN** オフラインモード is ON and WebLLM generation completes successfully
- **THEN** the UI persists the same pending history + proposals shape with provider indicating local/WebLLM

#### Scenario: Persist failure keeps local job
- **WHEN** the pending history or proposal create API fails after a successful generation
- **THEN** the job remains completed in local Job Queue with suggestions visible
- **AND** the UI shows an error toast that DB sync failed

### Requirement: Hydrate Pending Generations Across Clients
On session select and during the existing shared-DB poll (~10s), the UI SHALL load pending histories (and their proposals) from the backend and merge them into the Job Queue / review surface so another browser or environment on the same DB can open and confirm them. Confirmed histories continue to populate the History list only.

#### Scenario: Other environment sees pending suggestions
- **GIVEN** environment A completed a generation that was persisted as pending
- **WHEN** environment B selects the same session (or the poll runs while that session is open)
- **THEN** B's Job Queue or review UI shows a completed/unconfirmed job with those suggestions and overall comment
- **AND** B can enter confirm flow without regenerating

#### Scenario: Confirmed rows stay in History
- **WHEN** a history has `status` = `confirmed`
- **THEN** it appears in the right-pane History list as today
- **AND** it is not re-added as a pending Job Queue item

### Requirement: Confirm Promotes Pending Without Duplicate History
When the user runs 「確定してコピー・保存」 for a job that already has a pending `historyId`, the UI SHALL update that history to confirmed, update proposal selection metadata, and refresh History — SHALL NOT create a second history row for the same generation.

#### Scenario: Confirm updates existing pending history
- **WHEN** the user confirms with at least 3 selected suggestions and the active job has a pending `historyId`
- **THEN** the UI updates that history to `confirmed` with the finalized combined comment
- **AND** updates proposal selection/edit flags
- **AND** appends/refreshes a single History entry for that generation

#### Scenario: Confirm without prior persist still creates history
- **WHEN** the user confirms a local-only completed job that never obtained a `historyId` (persist failed earlier)
- **THEN** the UI falls back to creating history + proposals as in the existing confirm/save flow
