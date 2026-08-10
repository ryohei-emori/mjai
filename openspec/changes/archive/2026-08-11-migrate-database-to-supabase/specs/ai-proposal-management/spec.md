## ADDED Requirements

### Requirement: Single Persistence Backend
The system SHALL persist all AI-proposal data exclusively through the Supabase Postgres backend, with no runtime-selectable alternative persistence path and no environment-variable-driven backend switch.

#### Scenario: Proposal list and create endpoints use Postgres unconditionally
- **WHEN** `GET /histories/{history_id}/proposals` or `POST /proposals` is called
- **THEN** the request is served via the Postgres/Supabase-backed helper functions, querying/inserting into the `ai_proposals` table
- **AND** no SQLite-backed code path exists to select as an alternative, regardless of any environment variable value

#### Scenario: No backend-selection environment variable
- **WHEN** the backend process starts
- **THEN** no `USE_POSTGRESQL` (or equivalent) environment variable is read to decide how to serve proposal requests

### Requirement: AI Proposal Data Model Carries the Full Field Set
The system SHALL persist each proposal in the Supabase `ai_proposals` table with columns covering `proposal_id` (primary key), `history_id` (references `correction_histories.history_id`), `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`, and `created_at` - the same information the product's proposal UI depends on, correctly represented in Postgres rather than the narrower legacy `proposal_text`/`confidence_score` shape.

#### Scenario: Creating a proposal persists all fields, not a subset
- **WHEN** a client sends `POST /proposals` with a body containing `historyId`, `type`, `originalAfterText`, and optionally `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, and `selectedOrder`
- **THEN** the system inserts a row into the Supabase `ai_proposals` table with every supplied field persisted (mapped to snake_case columns), not only a `proposal_text`/`confidence_score` approximation
- **AND** the system returns HTTP 200 with the persisted proposal, including a server-generated `proposalId` when none was supplied

#### Scenario: Flags default when omitted
- **GIVEN** a `POST /proposals` request omits `isSelected`, `isModified`, and/or `isCustom`
- **WHEN** the proposal is persisted
- **THEN** the system defaults each omitted flag to a falsy value
- **AND** defaults `selectedOrder` to null when omitted

#### Scenario: Listing proposals returns them ordered by selection order
- **WHEN** a client sends `GET /histories/{history_id}/proposals` for a history with existing proposals
- **THEN** the system returns HTTP 200 with a JSON array of proposal objects containing `proposalId`, `historyId`, `type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, and `selectedOrder`
- **AND** the array is ordered by `selectedOrder` ascending, with proposals whose `selectedOrder` is null sorted first

#### Scenario: History with no proposals returns an empty list, not an error
- **GIVEN** no `ai_proposals` row has the requested `history_id`
- **WHEN** a client sends `GET /histories/{history_id}/proposals`
- **THEN** the system returns HTTP 200 with an empty JSON array

### Requirement: Postgres Failure Handling
The system SHALL surface Supabase/Postgres failures on proposal operations as errors to the caller rather than silently retrying against an alternative backend or raising a schema-mismatch error under normal operation, since the schema now matches what the application writes and reads.

#### Scenario: Supabase query failure propagates as an error
- **GIVEN** a Supabase/Postgres call inside `GET /histories/{history_id}/proposals` or `POST /proposals` raises an exception
- **WHEN** the exception occurs
- **THEN** the system logs the error and the endpoint returns an error response
- **AND** the system does not attempt to serve the request from SQLite or any other fallback store, since none exists

#### Scenario: Creating a proposal with a valid payload no longer fails due to schema mismatch
- **GIVEN** a `POST /proposals` request includes all required fields (`historyId`, `type`, `originalAfterText`)
- **WHEN** the request is processed against the Supabase `ai_proposals` table
- **THEN** the insert succeeds without a key-lookup or column-mismatch error, correcting the previously non-functional default-backend behavior
