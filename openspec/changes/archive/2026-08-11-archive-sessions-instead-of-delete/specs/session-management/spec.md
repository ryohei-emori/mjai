## MODIFIED Requirements

### Requirement: List Sessions
The system SHALL provide a `GET /sessions` endpoint that returns all **active** (non-archived) sessions ordered by `updatedAt` descending, with each session annotated with a `correctionCount` computed as the number of associated correction-history rows.

#### Scenario: Active sessions exist
- **WHEN** one or more rows exist in the `sessions` table with `status = 'active'`
- **THEN** the response is a JSON array containing only those active session objects, each containing at least `sessionId`, `name`, `createdAt`, `updatedAt`, and `correctionCount`
- **AND** the array is ordered by `updatedAt` in descending order (most recently updated first)

#### Scenario: Archived sessions are excluded
- **WHEN** sessions exist with `status = 'archived'`
- **THEN** those sessions SHALL NOT appear in the response from `GET /sessions`

#### Scenario: No active sessions exist
- **WHEN** the `sessions` table is empty or all sessions are archived
- **THEN** the response is an empty JSON array

### Requirement: Delete Session
The system SHALL provide a `DELETE /sessions/{session_id}` endpoint that **archives** the session by setting its `status` to `'archived'`, without removing the session row or any associated correction-history or AI-proposal data.

#### Scenario: Archive an existing session
- **WHEN** a session exists with `status = 'active'`
- **AND** a client sends `DELETE /sessions/{session_id}`
- **THEN** the session's `status` column is updated to `'archived'`
- **AND** all `CorrectionHistories` rows for the session remain intact
- **AND** all `AIProposals` rows linked to those histories remain intact
- **AND** the response body is `{"message": "Session archived", "sessionId": "<session_id>"}`

#### Scenario: Archive a nonexistent session
- **WHEN** no session with the given `sessionId` exists
- **AND** a client sends `DELETE /sessions/{session_id}`
- **THEN** the update statement matches zero rows without raising an error
- **AND** the response still reports success (`{"message": "Session archived", "sessionId": "<session_id>"}`)

#### Scenario: Archive an already-archived session
- **WHEN** a session exists with `status = 'archived'`
- **AND** a client sends `DELETE /sessions/{session_id}`
- **THEN** the session's `status` remains `'archived'` (idempotent)
- **AND** the response is `{"message": "Session archived", "sessionId": "<session_id>"}`

## ADDED Requirements

### Requirement: Session Status Field
The system SHALL maintain a `status` column on each session record with valid values `'active'` (default for new sessions) and `'archived'`.

#### Scenario: New session has active status
- **WHEN** a client sends `POST /sessions` to create a new session
- **THEN** the new session is created with `status = 'active'`

#### Scenario: Status field in response
- **WHEN** a client retrieves a session via `GET /sessions/{session_id}`
- **THEN** the response MAY include the `status` field (implementation may choose to include or omit it)
