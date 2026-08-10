## MODIFIED Requirements

### Requirement: Persistence Backend Selection and Error Handling
The system SHALL persist all session operations exclusively to Supabase Postgres (identified by the `DATABASE_URL` environment variable). The `USE_POSTGRESQL` toggle and SQLite fallback path are removed.

#### Scenario: Default configuration uses Supabase Postgres
- GIVEN the `DATABASE_URL` environment variable points to a Supabase Postgres instance
- WHEN any session endpoint (`GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, `DELETE /sessions/{id}`) is called
- THEN the request is served via the Postgres helper functions in `backend/app/db_helper.py`, operating on the `sessions` table with snake_case columns
- AND there is no `USE_POSTGRESQL` environment variable or SQLite code path

#### Scenario: Postgres failure returns error
- GIVEN the Supabase Postgres connection is unavailable or the query raises an exception
- WHEN any session endpoint is called
- THEN the error is logged and propagated to the client as an HTTP 500 response
- AND there is no SQLite fallback path

## REMOVED Requirements

### Requirement: SQLite persistence path
**Reason**: SQLite dual-path code is removed as part of consolidating on Supabase Postgres.
**Migration**: All session data must be migrated to Supabase Postgres before this change is deployed. Local development requires a Postgres connection (local instance or Supabase).

### Requirement: USE_POSTGRESQL toggle
**Reason**: The `USE_POSTGRESQL` environment variable and per-request backend selection are removed.
**Migration**: Remove `USE_POSTGRESQL` from environment configuration. The application always uses Supabase Postgres via `DATABASE_URL`.
