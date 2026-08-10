## MODIFIED Requirements

### Requirement: Get Single Session
The system SHALL provide a `GET /sessions/{session_id}` endpoint that returns a reduced projection of a single session's fields, or a not-found payload if no matching session exists. The endpoint SHALL correctly map snake_case PostgreSQL columns to camelCase response keys on the PostgreSQL path.

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
- THEN the `fetch_session()` helper applies column aliases in the SQL query, returning a dict with camelCase keys (`sessionId`, `name`, `createdAt`, `correctionCount`)
- AND the endpoint successfully returns these fields in the response body with HTTP status 200

### Requirement: Update Session
The system SHALL provide a `PUT /sessions/{session_id}` endpoint that partially updates an existing session, persisting only an allow-listed set of fields and silently ignoring any others, without first verifying that the session exists. The endpoint SHALL accept both camelCase (client-style) and snake_case (PostgreSQL-style) field names and map them correctly to the database column names.

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
- THEN the `update_session()` helper maps camelCase keys to their snake_case equivalents (`correctionCount` → `correction_count`, `isOpen` → `is_open`)
- AND the mapped fields are checked against the PostgreSQL allow-list and persisted if valid
- AND the endpoint returns a 200 success response
- AND both `name` and the mapped camelCase fields update successfully on the PostgreSQL backend when supplied
