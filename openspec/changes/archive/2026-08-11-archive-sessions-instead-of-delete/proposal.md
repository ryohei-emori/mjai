## Why

The current session "delete" operation performs a hard deletion, permanently removing the session row and cascading deletion to all associated correction histories and AI proposals. This contradicts the existing "full auditability" principle documented in the README. Users may want to recover accidentally deleted sessions or access historical data for audit purposes. Changing to a soft-delete (archive) model preserves data integrity while still allowing users to "remove" sessions from their active view.

## What Changes

- **Session delete becomes archive**: The delete button in the left pane will archive the session (set `status = 'archived'`) instead of permanently removing it from the database.
- **Add status column to sessions table**: A new `status` column (values: `active`, `archived`) will be added to the `sessions` table via a Postgres migration.
- **Filter archived sessions from default list**: The `GET /sessions` endpoint will return only active sessions by default, hiding archived sessions from the UI.
- **Preserve all related data**: Archived sessions retain all their correction histories and AI proposals intact in the database.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `session-management`: The "Delete Session" requirement changes from hard deletion to soft-delete (archive), and the "List Sessions" requirement adds default filtering to exclude archived sessions.

## Impact

- **Backend**:
  - `backend/supabase/migrations/`: New migration file to add `status` column
  - `backend/app/db_helper.py`: Modify `delete_session` to set status instead of DELETE; modify `fetch_sessions` to filter by status
  - `backend/app/main.py`: Update delete endpoint semantics; no cascade-delete of related data
- **Frontend**:
  - `frontend/src/app/api.ts`: Consider renaming `deleteSession` to `archiveSession` for clarity (optional)
  - `frontend/src/app/page.tsx`: Update delete handler and potentially button label (use judgment on UX)
- **Database**: Existing sessions need a default `status = 'active'` value in migration
