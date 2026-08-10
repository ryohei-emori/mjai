## MODIFIED Requirements

### Requirement: List Proposals for a Correction History
The system SHALL expose `GET /histories/{history_id}/proposals` to retrieve all `ai_proposals` rows from Supabase Postgres associated with the given `history_id`, returning the full proposal field set.

#### Scenario: Proposals exist for the history
- GIVEN one or more `ai_proposals` rows have `history_id` equal to the requested `history_id`
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with a JSON array of proposal objects containing `proposalId`, `historyId`, `type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, and `selectedOrder`
- AND the array is ordered by `selected_order` ascending, with rows whose `selected_order` is NULL sorted first
- AND the response uses camelCase field names (mapped from snake_case columns)

#### Scenario: History has no proposals or does not exist
- GIVEN no `ai_proposals` row has the requested `history_id`
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with an empty JSON array

#### Scenario: Postgres failure returns error
- GIVEN the Supabase Postgres query raises an exception
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system logs the error and returns an HTTP 500 response
- AND there is no SQLite fallback path

### Requirement: Create a Proposal Record
The system SHALL expose `POST /proposals` to persist a single AI-generated or custom proposal to Supabase Postgres, using the full proposal field set (`type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`).

#### Scenario: Successful creation
- GIVEN a valid JSON body containing at least `historyId`, `type`, and `originalAfterText`
- WHEN a client sends `POST /proposals`
- THEN the system inserts a row into the `ai_proposals` table with snake_case columns
- AND defaults `is_selected`, `is_modified`, and `is_custom` to `false` and `selected_order` to `null` when not provided
- AND the system returns HTTP 200 with a JSON object echoing the persisted proposal in camelCase field names

#### Scenario: Missing required field
- GIVEN the JSON request body omits `historyId`, `type`, or `originalAfterText`
- WHEN a client sends `POST /proposals`
- THEN the system returns HTTP 400 with an error message indicating the missing field

## REMOVED Requirements

### Requirement: SQLite persistence path for proposals
**Reason**: SQLite dual-path code is removed as part of consolidating on Supabase Postgres.
**Migration**: All AI proposal data must be migrated to Supabase Postgres before this change is deployed.

### Requirement: Legacy ai_proposals schema (proposal_text/confidence_score)
**Reason**: The Postgres `ai_proposals` table is updated to use the full field set (`type`, `original_after_text`, `original_reason`, etc.) matching the application's data model.
**Migration**: Apply migration `003_align_ai_proposals_schema.sql` to add the required columns to the Supabase `ai_proposals` table.
