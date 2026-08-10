## Why

The PostgreSQL backend path has three critical bugs that cause API failures and data loss when `USE_POSTGRESQL=true` (the default). These bugs were introduced when the codebase was migrated from SQLite-only to a dual-database model, where PostgreSQL uses snake_case columns while the application layer and SQLite use camelCase keys. The mismatches cause KeyError exceptions on session retrieval, silently ignored updates, and complete proposal creation failures.

## What Changes

- **Fix `GET /sessions/{session_id}`**: Map snake_case PostgreSQL columns (`session_id`, `created_at`, etc.) to camelCase keys in `fetch_session()`, matching the pattern already used in `fetch_sessions()`.
- **Fix `PUT /sessions/{session_id}`**: Accept both snake_case and camelCase field names in `update_session()` so that client-sent camelCase fields (`correctionCount`, `isOpen`) are mapped to the corresponding PostgreSQL columns.
- **Fix `POST /proposals`**: Migrate the PostgreSQL `ai_proposals` schema from the thin legacy model (`proposal_text`, `confidence_score`) to the full application model matching SQLite (`type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`). Update `insert_proposal()` and `fetch_proposals_by_history()` in `db_helper.py` to use consistent column mappings.
- **Add backend tests**: Cover the fixed PostgreSQL paths for GET session, PUT session, and POST proposals with mocked asyncpg to prevent regressions.

## Capabilities

### New Capabilities
<!-- None - this is a bug fix to existing capabilities -->

### Modified Capabilities
- `session-management`: Fix GET and PUT session endpoints to correctly handle snake_case/camelCase mapping on the PostgreSQL path, removing the known field-name mismatch bugs documented in the current spec.
- `ai-proposal-management`: Align PostgreSQL `ai_proposals` schema with the application's full proposal model (matching SQLite) and fix the `insert_proposal()` / `fetch_proposals_by_history()` functions to correctly persist and retrieve all proposal fields.

## Impact

- **Code**: `backend/app/db_helper.py` (fetch_session, update_session, insert_proposal, fetch_proposals_by_history), `backend/app/main.py` (no changes expected - already builds correct payloads)
- **Database**: New migration `backend/supabase/migrations/003_align_ai_proposals_schema.sql` to add missing columns to `ai_proposals` table
- **Tests**: New/updated tests in `backend/tests/` for PostgreSQL path coverage
- **Deployment**: Migration must be applied to Render Postgres before deploying the code changes (manual step for owner)
