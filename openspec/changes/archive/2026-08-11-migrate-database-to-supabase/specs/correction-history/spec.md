## ADDED Requirements

### Requirement: Single Persistence Backend
The system SHALL persist all correction-history data exclusively through the Supabase Postgres backend, with no runtime-selectable alternative persistence path and no environment-variable-driven backend switch.

#### Scenario: History list and create endpoints use Postgres unconditionally
- **WHEN** `GET /sessions/{sessionId}/histories` or `POST /histories` is called
- **THEN** the request is served via the Postgres/Supabase-backed helper functions, querying/inserting into the `correction_histories` table with snake_case columns
- **AND** no SQLite-backed code path exists to select as an alternative, regardless of any environment variable value

#### Scenario: No backend-selection environment variable
- **WHEN** the backend process starts
- **THEN** no `USE_POSTGRESQL` (or equivalent) environment variable is read to decide how to serve correction-history requests

### Requirement: Correction History Data Model
The system SHALL persist each correction history in the Supabase `correction_histories` table with columns `history_id` (primary key), `session_id` (references `sessions.session_id`), `timestamp`, `original_text`, `instruction_prompt`, `target_text`, `combined_comment`, `selected_proposal_ids`, and `custom_proposals`, and SHALL translate to/from the API's existing camelCase field names entirely within the persistence layer.

#### Scenario: Successful creation returns the created record
- **WHEN** a client sends `POST /histories` with a body containing `sessionId`, `originalText`, and `targetText`
- **THEN** the system persists a new `correction_histories` row keyed by the supplied `historyId` (or a newly generated UUID if omitted), with a server-side timestamp
- **AND** the system returns HTTP 200 with the created history data using the API's existing camelCase field names, not an empty/`null` body

#### Scenario: List histories for a session is ordered and returns snake_case data correctly mapped
- **WHEN** a client sends `GET /sessions/{sessionId}/histories` for a session with existing history records
- **THEN** the system returns HTTP 200 with a JSON array of history objects ordered by `timestamp` descending
- **AND** each object's fields are correctly mapped from the Supabase row's snake_case columns to the API's camelCase field names

#### Scenario: JSON-encoded fields are not double-encoded
- **GIVEN** the client supplies `selectedProposalIds` and/or `customProposals` as a JSON-stringified string
- **WHEN** the record is persisted to Supabase
- **THEN** the system stores the value as supplied by the client without applying an additional layer of JSON encoding on top of it

### Requirement: Postgres Failure Handling
The system SHALL surface Supabase/Postgres failures on correction-history operations as errors to the caller rather than silently retrying against an alternative backend, since no alternative backend exists.

#### Scenario: Supabase query failure propagates as an error
- **GIVEN** a Supabase/Postgres call inside `GET /sessions/{sessionId}/histories` or `POST /histories` raises an exception
- **WHEN** the exception occurs
- **THEN** the system logs the error and the endpoint returns an error response
- **AND** the system does not attempt to serve the request from SQLite or any other fallback store, since none exists
