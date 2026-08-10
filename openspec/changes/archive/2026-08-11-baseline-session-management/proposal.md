## Why

The `session-management` capability (Session CRUD: list, create, get, update, delete) is already fully implemented in `backend/app/main.py` and `backend/app/db_helper.py`, but the repository has just adopted OpenSpec and has no specs yet under `openspec/specs/`. Before planning any future changes to sessions, the team needs an accurate, spec-formatted baseline of the behavior that actually exists today — including quirks and edge cases — so future proposals can diff against ground truth instead of guesswork.

## What Changes

- Document the existing `/sessions` REST endpoints (list, create, get one, update, delete) as OpenSpec requirements, reflecting current behavior exactly (including known inconsistencies).
- No functional, API, or schema changes. No code in `backend/` or `frontend/` is modified.
- Capture the dual-persistence behavior: sessions are read/written through either a Supabase/PostgreSQL path or a SQLite path (`backend/db/schema.sql`, `Sessions` table), selected by the `USE_POSTGRESQL` environment variable (default `true`), with SQLite used as an explicit fallback only when `USE_POSTGRESQL=false`.
- Note observed data-shape mismatches between the PostgreSQL helper functions (snake_case columns) and the endpoint code (which builds/reads camelCase session dicts matching the SQLite schema) as documented, current behavior — not something this change fixes.

## Capabilities

### New Capabilities
- `session-management`: CRUD lifecycle for a user's correction work session (create, list, retrieve, update, delete), backed by the `Sessions` table, including request/response shapes, status codes, ordering, and cascading delete of dependent correction history/proposal rows.

### Modified Capabilities
(none — this is the first spec for this capability)

## Impact

- **Affected code (read-only, for documentation purposes)**: `backend/app/main.py` (`get_sessions`, `create_session`, `get_session`, `update_session`, `delete_session`, router prefix `/sessions`), `backend/app/db_helper.py` (`fetch_sessions`/`fetch_sessions_sqlite`, `insert_session`/`insert_session_sqlite`, `fetch_session`/`fetch_session_sqlite`, `update_session`/`update_session_sqlite`, `delete_session`/`delete_session_sqlite`), `backend/db/schema.sql` (`Sessions` table).
- **Out of scope**: `CorrectionHistories` and `AIProposals` tables/endpoints are only referenced minimally where session endpoints cascade into them (e.g., delete). They are documented separately by sibling capability write-ups.
- **No runtime impact**: this is a planning/documentation-only OpenSpec change; no source files outside `openspec/changes/baseline-session-management/` are touched.
