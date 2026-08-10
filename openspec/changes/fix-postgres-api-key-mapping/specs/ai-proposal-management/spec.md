## MODIFIED Requirements

### Requirement: List Proposals for a Correction History
The system SHALL expose `GET /histories/{history_id}/proposals` to retrieve all `ai_proposals` rows associated with the given `history_id`, without validating that the parent CorrectionHistory exists. The response SHALL include the full proposal model fields with consistent camelCase key names across both backends.

#### Scenario: Proposals exist for the history
- GIVEN one or more proposal rows have `history_id` (PostgreSQL) or `historyId` (SQLite) equal to the requested `history_id`
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with a JSON array of proposal objects containing `proposalId`, `historyId`, `type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, and `selectedOrder`
- AND on the SQLite-backed path the array is ordered by `selectedOrder` ascending, with rows whose `selectedOrder` is NULL sorted first
- AND on the PostgreSQL-backed path the array is ordered by `selected_order` ascending (with NULLs first) or by `created_at` descending, with snake_case columns mapped to camelCase keys in the response

#### Scenario: History has no proposals or does not exist
- GIVEN no proposal row has the requested `historyId`, including when `history_id` does not correspond to any existing CorrectionHistory
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with an empty JSON array
- AND no 404 is returned, since the endpoint never checks for the existence of the parent CorrectionHistory before querying proposals

#### Scenario: Default backend query failure is not recovered
- GIVEN the `USE_POSTGRESQL` environment variable is unset or set to any value other than `"false"` (the default configuration)
- WHEN a client sends `GET /histories/{history_id}/proposals` and the underlying PostgreSQL/Supabase query raises an exception
- THEN the system logs the error and re-raises it, resulting in an unhandled exception and an HTTP 500 response
- AND no automatic fallback to the local SQLite `AIProposals` table occurs in this case

### Requirement: Create a Proposal Record
The system SHALL expose `POST /proposals`, accepting an untyped JSON request body (not a strict Pydantic model), to persist a single AI-generated or custom proposal, applying default values for optional fields and generating a `proposalId` when one is not supplied. The endpoint SHALL work correctly on both PostgreSQL and SQLite backends, mapping camelCase request keys to the appropriate database column names.

#### Scenario: Successful creation with SQLite backend
- GIVEN `USE_POSTGRESQL` is explicitly set to `"false"`
- WHEN a client sends `POST /proposals` with a JSON body containing at least `historyId`, `type`, and `originalAfterText`
- THEN the system inserts a row into the `AIProposals` table, defaulting `isSelected`, `isModified`, and `isCustom` to `0` and `selectedOrder` to `null` when they are not present in the request
- AND the system returns HTTP 200 with a JSON object echoing the persisted proposal, including a server-generated UUID `proposalId` when none was supplied in the request

#### Scenario: Missing required field
- GIVEN the JSON request body omits `historyId`, `type`, or `originalAfterText`
- WHEN a client sends `POST /proposals`
- THEN the system raises a `KeyError` while constructing the proposal record before any database call is made
- AND this exception is unhandled, resulting in an HTTP 500 response

#### Scenario: Default PostgreSQL backend is non-functional for proposal creation
- GIVEN `USE_POSTGRESQL` is unset or set to any value other than `"false"` (the default configuration) and the PostgreSQL `ai_proposals` schema has been migrated to include the full proposal model columns
- WHEN a client sends `POST /proposals` with a valid payload containing `historyId`, `type`, and `originalAfterText`
- THEN the `insert_proposal()` helper maps camelCase keys to snake_case PostgreSQL columns (`proposal_id`, `history_id`, `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`)
- AND the system successfully inserts a row into the `ai_proposals` table
- AND the system returns HTTP 200 with a JSON object echoing the persisted proposal in camelCase format

#### Scenario: No foreign key or enum validation on write
- GIVEN a request body whose `historyId` does not correspond to any existing CorrectionHistory, or whose `type` value is neither `"AI"` nor `"Custom"`
- WHEN a client sends `POST /proposals`
- THEN the system persists the row without error, since neither the `historyId` relationship nor the `type` value is validated at the application level

## ADDED Requirements

### Requirement: PostgreSQL Schema Alignment
The system SHALL maintain a PostgreSQL `ai_proposals` table schema that matches the application's full proposal model, including all fields used by the SQLite `AIProposals` table.

#### Scenario: PostgreSQL ai_proposals table has all required columns
- GIVEN the PostgreSQL database has had migration `003_align_ai_proposals_schema.sql` applied
- WHEN the `ai_proposals` table schema is inspected
- THEN the table contains columns: `proposal_id` (UUID PK), `history_id` (UUID FK), `type` (TEXT), `original_after_text` (TEXT), `original_reason` (TEXT), `modified_after_text` (TEXT), `modified_reason` (TEXT), `is_selected` (INTEGER), `is_modified` (INTEGER), `is_custom` (INTEGER), `selected_order` (INTEGER), `created_at` (TIMESTAMP)
- AND the legacy columns `proposal_text` and `confidence_score` MAY be retained for backward compatibility or dropped
