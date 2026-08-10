## ADDED Requirements

### Requirement: Single Persistence Backend
The system SHALL persist all session data exclusively through the Supabase Postgres backend, with no runtime-selectable alternative persistence path and no environment-variable-driven backend switch.

#### Scenario: All session endpoints use Postgres unconditionally
- **WHEN** any session endpoint (`GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, `DELETE /sessions/{id}`) is called
- **THEN** the request is served via the Postgres/Supabase-backed persistence functions operating on the `sessions` table with snake_case columns
- **AND** no SQLite-backed code path exists to select as an alternative, regardless of any environment variable value

#### Scenario: No backend-selection environment variable
- **WHEN** the backend process starts
- **THEN** no `USE_POSTGRESQL` (or equivalent) environment variable is read to decide how to serve session requests
- **AND** setting such a variable in the deployment environment has no effect on session persistence behavior

### Requirement: Consistent Field Naming Across the Persistence Boundary
The system SHALL translate between the camelCase field names used in session API request/response bodies and the snake_case column names used in the Supabase `sessions` table entirely within the persistence layer, such that no route handler needs to know the database's column naming convention.

#### Scenario: Create session with a name persists correctly
- **WHEN** a client sends `POST /sessions` with a JSON body containing `{"name": "My Session"}`
- **THEN** a new row is inserted into the Supabase `sessions` table with `session_id` (newly generated UUID), `created_at` and `updated_at` (current timestamp), `name` set to `"My Session"`, `correction_count` set to `0`, and `is_open` set to `true`
- **AND** the created session object is returned to the client using the same camelCase field names the API already uses (`sessionId`, `createdAt`, `updatedAt`, `correctionCount`, `isOpen`)

#### Scenario: Get single session returns the expected projection without key errors
- **WHEN** a client sends `GET /sessions/{session_id}` for an existing session
- **THEN** the response body contains `sessionId`, `name`, `createdAt`, and `correctionCount`, correctly read from the Supabase row's snake_case columns
- **AND** no key-lookup error occurs due to a camelCase/snake_case mismatch

#### Scenario: Update allow-listed fields using either naming convention accepted by the API
- **WHEN** a client sends `PUT /sessions/{session_id}` with a JSON body such as `{"name": "Renamed", "isOpen": false}`
- **THEN** the corresponding `name` and `is_open` columns of the matching Supabase `sessions` row are updated
- **AND** the response body echoes the update using the client's camelCase field names

### Requirement: Postgres Failure Handling
The system SHALL surface Supabase/Postgres failures on session operations as errors to the caller rather than silently retrying against an alternative backend, since no alternative backend exists.

#### Scenario: Supabase query failure propagates as an error
- **GIVEN** a Supabase/Postgres call inside any session endpoint raises an exception
- **WHEN** the exception occurs
- **THEN** the system logs the error and the endpoint returns an error response
- **AND** the system does not attempt to serve the request from SQLite or any other fallback store, since none exists
