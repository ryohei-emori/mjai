## ADDED Requirements

### Requirement: Pending vs Confirmed Correction History Status
The system SHALL persist each successful AI suggestion generation as a `correction_histories` row with `status` of `pending` until the user confirms and saves, at which point the same row SHALL be updated to `status` of `confirmed`. Existing rows with no status SHALL be treated as `confirmed`. The system SHALL NOT require a second history insert solely for confirm/save when a pending history already exists for that generation.

#### Scenario: Create pending history on generation success
- **WHEN** a client creates a history for a completed suggestion generation with `status` omitted or set to `pending`
- **THEN** the system persists the row with `status` = `pending`
- **AND** stores `originalText`, `targetText`, `overallComment` (generation overall comment), optional `provider`, and optional `clientJobId`
- **AND** returns those fields in the create response

#### Scenario: Confirm promotes pending to confirmed
- **WHEN** a client updates an existing pending history with `status` = `confirmed` and the finalized `combinedComment` / selection metadata
- **THEN** the system updates that row in place
- **AND** does not create a duplicate history for the same generation

#### Scenario: List includes status and restore fields
- **WHEN** a client lists histories for a session
- **THEN** each history object includes `status`, `overallComment`, `provider`, and `clientJobId` (null/omitted when unset)
- **AND** both `pending` and `confirmed` non-archived rows are returned

### Requirement: Update Correction History
The system SHALL provide `PUT /histories/{historyId}` (or equivalent update endpoint) accepting a JSON body that may include `status`, `combinedComment`, `overallComment`, `selectedProposalIds`, `customProposals`, and related finalize fields, and SHALL update the matching non-archived row.

#### Scenario: Successful pending-to-confirmed update
- **WHEN** a client sends an update for an existing history with `status` = `confirmed` and a finalized `combinedComment`
- **THEN** the system returns HTTP 200 with the updated history
- **AND** subsequent list responses show `status` = `confirmed`

#### Scenario: Unknown history id
- **WHEN** a client updates a history id that does not exist
- **THEN** the system returns HTTP 404

## MODIFIED Requirements

### Requirement: Create a Correction History Record
The system SHALL provide `POST /histories`, accepting a JSON request body (parsed as an untyped object, not a strict schema) and persisting a new `CorrectionHistories` row associated with the given `sessionId`. The body MAY include `status` (`pending` or `confirmed`, default `confirmed` for backward compatibility with confirm-only clients), `overallComment`, `provider`, and `clientJobId`. Missing required fields SHALL yield a non-2xx error (not a 200 error-shaped body).

#### Scenario: Successful creation with all fields supplied
- GIVEN a request body containing `sessionId`, `originalText`, `targetText`, and optionally `instructionPrompt`, `combinedComment`, `overallComment`, `selectedProposalIds`, `customProposals`, `status`, `provider`, `clientJobId`, and/or `historyId`
- WHEN a client sends `POST /histories` with this body
- THEN the system generates a server-side timestamp (current time) for the record regardless of any timestamp supplied by the client
- AND the system persists a new row keyed by the supplied `historyId`, or a newly generated UUID if `historyId` is omitted
- AND the system returns HTTP 200 with the created history data including status and restore fields

#### Scenario: Required field is missing
- GIVEN a request body missing `sessionId`, `originalText`, and/or `targetText` (falsy or absent)
- WHEN a client sends `POST /histories` with this body
- THEN the system returns HTTP 400 with a clear error detail
- AND no row is inserted into `CorrectionHistories`

#### Scenario: Pending generation create uses overallComment
- GIVEN a request with `status` = `pending`, `overallComment` set to the model overall comment, and `combinedComment` omitted or equal to that overall comment
- WHEN the history is created
- THEN `overallComment` is stored for later right-pane restore
- AND selected-proposal metadata may be null until confirm
