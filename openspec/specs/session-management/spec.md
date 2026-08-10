# session-management Specification

## Purpose

The session-management capability lets a user create, list, retrieve, update, and delete "Sessions" — a Session represents one block of a user's correction work and acts as the parent container for that user's correction histories and AI proposals.

## Requirements

### Requirement: List Sessions
The system SHALL provide a `GET /sessions` endpoint that returns sessions ordered by `updatedAt` descending, with each session annotated with a `correctionCount` computed as the number of associated correction-history rows.

#### Scenario: Sessions exist (PostgreSQL path)
- GIVEN the backend is configured with `USE_POSTGRESQL=true` (default) and one or more rows exist in the `sessions` table with `status = 'active'` or `status IS NULL`
- WHEN a client sends `GET /sessions`
- THEN the response is a JSON array of session objects, each containing at least `sessionId`, `name`, `createdAt`, `updatedAt`, and `correctionCount` (column aliases applied in the query)
- AND archived sessions (`status = 'archived'`) are excluded
- AND the array is ordered by `updatedAt` in descending order (most recently updated first)

#### Scenario: Sessions exist (SQLite path)
- GIVEN the backend is configured with `USE_POSTGRESQL=false` and one or more rows exist in the `Sessions` table
- WHEN a client sends `GET /sessions`
- THEN the response is a JSON array of session objects, each containing at least `sessionId`, `name`, `createdAt`, `updatedAt`, `correctionCount`, and `isOpen`
- AND the array is ordered by `updatedAt` in descending order
- AND (assumption, per current code) SQLite has no `status` column, so no archive filtering is applied

#### Scenario: No sessions exist
- GIVEN no matching session rows exist for the active backend
- WHEN a client sends `GET /sessions`
- THEN the response is an empty JSON array

### Requirement: Create Session
The system SHALL provide a `POST /sessions` endpoint that accepts an arbitrary JSON object (no strict schema validation) and creates a new session with a server-generated identifier and timestamps.

#### Scenario: Create session with a name
- GIVEN a client sends `POST /sessions` with a JSON body containing `{"name": "My Session"}`
- WHEN the request is processed
- THEN a new session is created with a newly generated UUID as the session id, `createdAt`/`created_at` and `updatedAt`/`updated_at` both set to the current timestamp (ISO-8601, millisecond precision), `name` set to `"My Session"`, correction count `0`, and is-open `true`
- AND the created session object (containing both snake_case and camelCase key copies) is returned in the response

#### Scenario: Create session without a name
- GIVEN a client sends `POST /sessions` with a JSON body that omits the `name` field (or sends `{}`)
- WHEN the request is processed
- THEN the new session's `name` defaults to `"セッション"`
- AND all other fields are populated the same way as when a name is supplied

#### Scenario: Create session persisted via either backend
- GIVEN the backend uses PostgreSQL (`USE_POSTGRESQL=true`) or SQLite (`USE_POSTGRESQL=false`)
- WHEN a client sends `POST /sessions`
- THEN the endpoint builds a session dict with both snake_case keys (`session_id`, `created_at`, `updated_at`, `correction_count`, `is_open`) and camelCase keys (`sessionId`, `createdAt`, `updatedAt`, `correctionCount`, `isOpen`) plus `name`
- AND the PostgreSQL insert helper reads the snake_case keys while the SQLite insert helper reads the camelCase keys, so both backends can persist successfully

### Requirement: Get Single Session
The system SHALL provide a `GET /sessions/{session_id}` endpoint that returns a reduced projection of a single session's fields, or a not-found payload if no matching session exists.

#### Scenario: Session exists (SQLite path)
- GIVEN `USE_POSTGRESQL=false` and a session with a given `sessionId` exists
- WHEN a client sends `GET /sessions/{session_id}` with that ID
- THEN the response body contains exactly `sessionId`, `name`, `createdAt`, and `correctionCount` (defaulting `correctionCount` to `0` if not present on the stored record)
- AND the HTTP status code is 200

#### Scenario: Session does not exist
- GIVEN no session with the given `sessionId` exists (and the fetch succeeds without raising)
- WHEN a client sends `GET /sessions/{session_id}` with that ID
- THEN the response body is `{"error": "Session not found", "sessionId": "<session_id>"}`
- AND the HTTP status code is still 200 (the endpoint does not return a 404)

#### Scenario: Lookup under default PostgreSQL configuration (known field-name mismatch)
- GIVEN the backend is running with the default configuration (`USE_POSTGRESQL=true` or unset) and the session row exists
- WHEN a client sends `GET /sessions/{session_id}`
- THEN the PostgreSQL fetch helper runs `SELECT * FROM sessions`, returning a dict keyed by snake_case column names (e.g. `session_id`, `created_at`), but the endpoint reads it using camelCase keys (`session["sessionId"]`, etc.)
- AND (assumption, based on reading the current code) this mismatch causes a key-lookup error that is re-raised, surfacing to the client as an unhandled server error instead of the expected projection

### Requirement: Update Session
The system SHALL provide a `PUT /sessions/{session_id}` endpoint that partially updates an existing session, persisting only an allow-listed set of fields and silently ignoring any others, without first verifying that the session exists.

#### Scenario: Update an allowed field via SQLite
- GIVEN the backend is configured with `USE_POSTGRESQL=false` and a session with a given `sessionId` exists
- WHEN a client sends `PUT /sessions/{session_id}` with a JSON body such as `{"name": "Renamed", "isOpen": false}`
- THEN the `name` and `isOpen` columns of the matching `Sessions` row are updated
- AND the response body is `{"message": "Session updated", "sessionId": "<session_id>", "name": "Renamed", "isOpen": false}`

#### Scenario: Update with no recognized fields
- GIVEN a client sends `PUT /sessions/{session_id}` with a JSON body containing only fields outside the allow-list (e.g. `{"foo": "bar"}`)
- WHEN the request is processed
- THEN no columns are modified in the database (the update is silently skipped)
- AND the response still reports success: `{"message": "Session updated", "sessionId": "<session_id>", "foo": "bar"}`

#### Scenario: Update a nonexistent session
- GIVEN no session with the given `sessionId` exists
- WHEN a client sends `PUT /sessions/{session_id}` with a valid payload
- THEN the SQL `UPDATE` statement matches zero rows without raising an error
- AND the response still reports success (`{"message": "Session updated", ...}`), giving no indication that nothing was actually changed

#### Scenario: Allow-listed field names differ by backend
- GIVEN the backend is running with the default configuration (`USE_POSTGRESQL=true` or unset)
- WHEN a client sends `PUT /sessions/{session_id}` with camelCase field names such as `{"correctionCount": 5, "isOpen": false}`
- THEN (assumption, based on reading the current code) none of these keys match the PostgreSQL path's snake_case allow-list (`name`, `correction_count`, `is_open`, `updated_at`), so no fields are persisted
- AND the endpoint still returns a 200 success response echoing the submitted payload
- AND `name` (identical in both naming styles) is the primary field that updates successfully on either backend when supplied

### Requirement: Delete Session
The system SHALL provide a `DELETE /sessions/{session_id}` endpoint whose persistence behavior depends on the active backend: PostgreSQL archives the session; SQLite hard-deletes the session and cascades to dependents. The endpoint does not first verify that the session exists.

#### Scenario: Archive via PostgreSQL (default)
- GIVEN `USE_POSTGRESQL=true` (default) and a session exists
- WHEN a client sends `DELETE /sessions/{session_id}`
- THEN the session's `status` is set to `'archived'` and associated correction-history / AI-proposal rows are retained
- AND the response body is `{"message": "Session archived", "sessionId": "<session_id>"}`

#### Scenario: Hard-delete via SQLite
- GIVEN `USE_POSTGRESQL=false` and a session exists with associated correction-history rows (each of which may have associated AI-proposal rows)
- WHEN a client sends `DELETE /sessions/{session_id}`
- THEN all `AIProposals` rows linked to the session's `CorrectionHistories` are deleted first, then the `CorrectionHistories` rows for the session are deleted, then the `Sessions` row itself is deleted
- AND the response body is `{"message": "Session deleted", "sessionId": "<session_id>"}`

#### Scenario: Delete/archive a nonexistent session
- GIVEN no session with the given `sessionId` exists
- WHEN a client sends `DELETE /sessions/{session_id}`
- THEN the update/delete statements match zero rows without raising an error
- AND the response still reports success (`Session archived` on PostgreSQL, `Session deleted` on SQLite)

#### Scenario: Archive an already-archived session
- GIVEN `USE_POSTGRESQL=true` and a session exists with `status = 'archived'`
- WHEN a client sends `DELETE /sessions/{session_id}`
- THEN the session's `status` remains `'archived'` (idempotent)
- AND the response is `{"message": "Session archived", "sessionId": "<session_id>"}`

### Requirement: Session Status Field
The system SHALL maintain a `status` column on each session record (PostgreSQL path) with valid values `'active'` (default for new sessions) and `'archived'`.

#### Scenario: New session has active status
- WHEN a client sends `POST /sessions` to create a new session on the PostgreSQL path
- THEN the new session is created with `status = 'active'`

#### Scenario: Status field in response
- WHEN a client retrieves a session via `GET /sessions/{session_id}`
- THEN the response MAY include the `status` field (implementation may choose to include or omit it)

### Requirement: Persistence Backend Selection and Error Handling
The system SHALL select between a PostgreSQL/Supabase persistence path and a local SQLite persistence path for all session operations based on the `USE_POSTGRESQL` environment variable (default: `true` when unset), and SHALL handle backend failures differently across endpoints as currently implemented.

#### Scenario: Default configuration uses PostgreSQL
- GIVEN the `USE_POSTGRESQL` environment variable is unset or set to `"true"`
- WHEN any session endpoint (`GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, `DELETE /sessions/{id}`) is called
- THEN the request is served via the PostgreSQL/Supabase helper functions in `backend/app/db_helper.py`, operating on the `sessions` table with snake_case columns

#### Scenario: Explicit SQLite configuration
- GIVEN the `USE_POSTGRESQL` environment variable is set to `"false"`
- WHEN any session endpoint is called
- THEN the request is served via the SQLite helper functions, operating on the `Sessions` table defined in `backend/db/schema.sql` (file at `backend/db/app.db`)

#### Scenario: PostgreSQL failure does not fall back to SQLite
- GIVEN `USE_POSTGRESQL` is `"true"` (default) and the PostgreSQL call raises an exception for any reason
- WHEN the exception occurs inside `GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, or `DELETE /sessions/{id}`
- THEN the error is logged and re-raised rather than retried against SQLite
- AND (assumption, based on reading the current code) the client receives an unhandled server error despite the code containing comments describing a "fallback" design

#### Scenario: SQLite failure handling differs by endpoint
- GIVEN `USE_POSTGRESQL` is `"false"` and the (only) SQLite call inside a session endpoint raises an exception
- WHEN the exception is caught
- THEN for `GET /sessions` and `POST /sessions`, the code retries the identical SQLite call a second time inside the `except` block, and if that second attempt also fails, the exception propagates unhandled
- AND for `GET /sessions/{id}`, `PUT /sessions/{id}`, and `DELETE /sessions/{id}`, the code retries the identical SQLite call a second time inside the `except` block, but if that second attempt also fails, it is caught and converted into a 200 response with an `{"error": "..."}` body instead of propagating
