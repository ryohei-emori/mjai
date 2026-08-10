## MODIFIED Requirements

### Requirement: Correction History Storage Backend Selection
The system SHALL persist all correction history operations exclusively to Supabase Postgres (identified by the `DATABASE_URL` environment variable). The `USE_POSTGRESQL` toggle and SQLite fallback path are removed.

#### Scenario: Supabase Postgres backend is the only path
- GIVEN the `DATABASE_URL` environment variable points to a Supabase Postgres instance
- WHEN `GET /sessions/{sessionId}/histories` or `POST /histories` is called
- THEN the system serves the request using the Postgres-backed helper functions (querying/inserting into a `correction_histories` table with snake_case columns)
- AND there is no `USE_POSTGRESQL` environment variable or SQLite code path

#### Scenario: Postgres backend failure returns error
- GIVEN the Supabase Postgres connection is unavailable or the query raises an exception
- WHEN `GET /sessions/{sessionId}/histories` or `POST /histories` is called
- THEN the system logs the error and returns an HTTP 500 response
- AND there is no SQLite fallback path

#### Scenario: POST returns created history object
- GIVEN a successful `POST /histories` request
- WHEN the Postgres insert completes
- THEN the response body contains the created history object with camelCase field names
- AND the Postgres helper function returns the created record (not `null`)

## REMOVED Requirements

### Requirement: SQLite persistence path for correction histories
**Reason**: SQLite dual-path code is removed as part of consolidating on Supabase Postgres.
**Migration**: All correction history data must be migrated to Supabase Postgres before this change is deployed.

### Requirement: Double-JSON encoding for selectedProposalIds/customProposals
**Reason**: The SQLite insert path that applied `json.dumps()` to already-stringified values is removed. Postgres stores JSON natively.
**Migration**: Existing double-encoded data should be cleaned up during migration or handled at read-time if legacy data exists.
