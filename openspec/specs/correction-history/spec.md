# correction-history Specification

## Purpose

Correction histories record each original-text vs. target-text correction pass performed within a session, so a session's past corrections (and the proposals/comments tied to each pass) can be listed and replayed later.

## Requirements

### Requirement: List Correction Histories for a Session
The system SHALL provide `GET /sessions/{sessionId}/histories`, returning all `CorrectionHistories` rows for the given `sessionId`, ordered by `timestamp` descending (most recent first).

#### Scenario: Session has existing history records
- GIVEN a session identified by `sessionId` has one or more correction history records
- WHEN a client sends `GET /sessions/{sessionId}/histories`
- THEN the system returns HTTP 200 with a JSON array of history objects
- AND the array is ordered by `timestamp` descending

#### Scenario: Session has no history records or does not exist
- GIVEN a `sessionId` for which no `CorrectionHistories` rows exist (including a `sessionId` that does not correspond to any row in `Sessions`)
- WHEN a client sends `GET /sessions/{sessionId}/histories`
- THEN the system returns HTTP 200 with an empty JSON array
- AND no 404 error is raised for an unknown or non-existent `sessionId` (the endpoint does not verify the session exists)

#### Scenario: JSON-encoded fields are returned unparsed
- GIVEN a history record whose `selectedProposalIds` and/or `customProposals` values were stored as JSON-encoded text
- WHEN that record is included in the list response
- THEN `selectedProposalIds` and `customProposals` are returned as raw string values exactly as stored
- AND the server does not deserialize them back into arrays/objects before responding

### Requirement: Create a Correction History Record
The system SHALL provide `POST /histories`, accepting a JSON request body (parsed as an untyped object, not a strict schema) and persisting a new `CorrectionHistories` row associated with the given `sessionId`.

#### Scenario: Successful creation with all fields supplied
- GIVEN a request body containing `sessionId`, `originalText`, `targetText`, and optionally `instructionPrompt`, `combinedComment`, `selectedProposalIds`, `customProposals`, and/or `historyId`
- WHEN a client sends `POST /histories` with this body
- THEN the system generates a server-side timestamp (current time) for the record regardless of any timestamp supplied by the client
- AND the system persists a new row keyed by the supplied `historyId`, or a newly generated UUID if `historyId` is omitted
- AND the system returns HTTP 200 with the created history data

#### Scenario: Required field is missing
- GIVEN a request body missing `sessionId`, `originalText`, and/or `targetText` (falsy or absent)
- WHEN a client sends `POST /histories` with this body
- THEN the system returns HTTP 200 (not a 4xx status) with a JSON body of the form `{"error": "Missing required field in payload", "payload": <original payload>}`
- AND no row is inserted into `CorrectionHistories`

#### Scenario: sessionId does not reference an existing session
- GIVEN a request body whose `sessionId` does not correspond to any row in `Sessions`
- WHEN a client sends `POST /histories` with this body and `originalText`/`targetText` present
- THEN the system still inserts the `CorrectionHistories` row (no application-level or database-level foreign-key check is enforced against `Sessions`)
- AND the system returns HTTP 200 with the created history data as in the successful case

#### Scenario: selectedProposalIds and customProposals are stored double-JSON-encoded
- GIVEN the client supplies `selectedProposalIds` and/or `customProposals` as a JSON-stringified string (e.g. `"[\"1\",\"2\"]"`), which is the current frontend behavior
- WHEN the record is persisted via the SQLite-backed insert path
- THEN the system applies `json.dumps()` to that already-stringified value before storing it, resulting in a double-JSON-encoded string in the `selectedProposalIds`/`customProposals` columns
- AND if the client omits `selectedProposalIds`/`customProposals` entirely, the system stores `NULL` for that column instead of encoding it

#### Scenario: Unexpected error while building the record
- GIVEN processing the request body raises an exception before the database insert (e.g. an unexpected payload shape)
- WHEN `POST /histories` is called
- THEN the system returns HTTP 200 (not a 4xx/5xx status) with a JSON body of the form `{"error": "<exception message>", "payload": <original payload>}`

### Requirement: Correction History Storage Backend Selection
The system SHALL select between a PostgreSQL-backed and a SQLite-backed implementation of the correction-history list/create operations based on the `USE_POSTGRESQL` environment variable (default `"true"`), and SHALL apply different fallback and response behavior for each backend.

#### Scenario: PostgreSQL backend enabled (default) and reachable
- GIVEN `USE_POSTGRESQL` is unset or set to `"true"`
- WHEN `GET /sessions/{sessionId}/histories` or `POST /histories` is called and the PostgreSQL query succeeds
- THEN the system serves the request using the PostgreSQL-backed helper functions (querying/inserting into a `correction_histories` table with snake_case columns)
- AND on successful creation via `POST /histories`, the response body is `null`, because the PostgreSQL insert helper performs the insert but returns no value

#### Scenario: PostgreSQL backend enabled but the query fails
- GIVEN `USE_POSTGRESQL` is `"true"`
- WHEN the PostgreSQL-backed call raises an exception (e.g. connection failure)
- THEN the system re-raises the exception without falling back to SQLite, resulting in an unhandled-exception (HTTP 500) response

#### Scenario: SQLite backend explicitly selected
- GIVEN `USE_POSTGRESQL` is explicitly set to a value other than `"true"` (e.g. `"false"`)
- WHEN `GET /sessions/{sessionId}/histories` or `POST /histories` is called
- THEN the system serves the request using the SQLite-backed helper functions against `backend/db/app.db`
- AND on successful creation via `POST /histories`, the response body is the constructed history object, which contains both snake_case and camelCase copies of every field (e.g. both `session_id` and `sessionId`)

#### Scenario: SQLite backend selected but the query fails
- GIVEN `USE_POSTGRESQL` is not `"true"`
- WHEN the SQLite-backed call raises an exception
- THEN the system logs a warning and retries the operation against SQLite again as a fallback
- AND if that retry also fails for `GET`, the exception propagates (HTTP 500); for `POST`, the retry's result (or the constructed history object) is returned

### Requirement: Correction History Data Model
The system SHALL persist each correction history in the `CorrectionHistories` SQLite table with columns `historyId` (primary key), `sessionId` (references `Sessions.sessionId`), `timestamp`, `originalText`, `instructionPrompt`, `targetText`, `combinedComment`, `selectedProposalIds`, and `customProposals`.

#### Scenario: Required vs. optional columns per schema
- GIVEN the `CorrectionHistories` table schema
- WHEN a row is inserted
- THEN `historyId`, `sessionId`, `timestamp`, `originalText`, and `targetText` are declared `NOT NULL`
- AND `instructionPrompt`, `combinedComment`, `selectedProposalIds`, and `customProposals` are nullable

#### Scenario: Foreign key to Sessions is declared but not enforced
- GIVEN the `CorrectionHistories` table declares `FOREIGN KEY (sessionId) REFERENCES Sessions(sessionId)`
- WHEN a row is inserted through the SQLite connection used by this application
- THEN the foreign key constraint is not enforced at runtime, because the application never enables `PRAGMA foreign_keys = ON` on its SQLite connections
- AND rows referencing a non-existent `sessionId` can be inserted successfully
