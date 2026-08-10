## Context

See proposal.md for motivation. The current `DELETE /sessions/{session_id}` endpoint performs a hard deletion with cascade-deletes to `correction_histories` and `ai_proposals`. The backend uses PostgreSQL as the primary persistence (via `asyncpg`) with a deprecated SQLite fallback path. Per `AGENTS.md`, the Postgres path is the priority; SQLite changes are out of scope unless leaving it broken would be worse.

Current codebase state:
- Backend delete logic in `backend/app/db_helper.py::delete_session()` explicitly deletes proposals, then histories, then the session
- Frontend calls `DELETE /sessions/{session_id}` via `frontend/src/app/api.ts::sessionAPI.deleteSession()`
- Existing migration pattern: `backend/supabase/migrations/001_initial_schema.sql`

## Goals / Non-Goals

**Goals:**
- Preserve session data when user clicks "delete" (soft-delete via status flag)
- Hide archived sessions from the default session list
- Minimal code changes; no new endpoints

**Non-Goals:**
- Providing UI to view/restore archived sessions (future work)
- Updating the SQLite schema or SQLite code path (deprecated per AGENTS.md)
- Query parameter to optionally include archived sessions in list (future work)

## Decisions

### Decision 1: Reuse DELETE endpoint for archive semantics

**Choice**: Keep `DELETE /sessions/{session_id}` endpoint but change its behavior from hard-delete to soft-delete (update `status = 'archived'`).

**Rationale**: Minimal frontend changes required - the frontend already calls DELETE for this action. REST purists might prefer a new `PATCH /sessions/{session_id}/archive` or using PUT with `{status: 'archived'}`, but that would require frontend changes for no real user-visible benefit. The DELETE verb can reasonably mean "remove from active view" rather than "destroy data" when soft-delete is the semantic.

**Alternatives considered**:
- `PATCH /sessions/{session_id}/archive`: More explicit but requires frontend change
- `PUT /sessions/{session_id}` with `{status: 'archived'}`: Already exists for updates but mixing archive semantics into generic update is unclear

### Decision 2: Add `status` column with default `'active'`

**Choice**: Add `status TEXT DEFAULT 'active'` column. Use string values `'active'` and `'archived'` rather than boolean `is_archived`.

**Rationale**: String enum allows future status values (e.g., `'deleted'` for eventual hard-delete after retention period) without schema change. Existing rows automatically get `'active'` status via DEFAULT.

**Migration file**: `backend/supabase/migrations/002_add_session_status.sql`

### Decision 3: Filter in SQL query, not application layer

**Choice**: Modify `fetch_sessions()` query to include `WHERE status = 'active'` (or `WHERE status IS NULL OR status = 'active'` for safety during rollout).

**Rationale**: Filtering at the database level is more efficient and ensures consistency. The `WHERE status = 'active' OR status IS NULL` pattern handles any edge case where the column exists but isn't populated.

### Decision 4: Update response message from "deleted" to "archived"

**Choice**: Change response from `{"message": "Session deleted", ...}` to `{"message": "Session archived", ...}`.

**Rationale**: Reflects actual behavior. Frontend currently doesn't parse this message text, just checks for success, so this is non-breaking but semantically correct.

## Risks / Trade-offs

**[Risk] Orphaned data accumulation**: Archived sessions and their histories/proposals remain indefinitely.  
→ **Mitigation**: Acceptable for MVP; future work can add retention policy or admin cleanup tools.

**[Risk] SQLite path becomes inconsistent**: Not updating SQLite schema means `USE_POSTGRESQL=false` path won't have status column.  
→ **Mitigation**: Per AGENTS.md, SQLite is deprecated and Postgres is the live path. SQLite code will continue to hard-delete until it's fully removed. Document this in release notes.

**[Risk] Frontend shows "deleted" toast but session is archived**: If frontend toast message says "セッションを削除しました" (session deleted), it may confuse users.  
→ **Mitigation**: Update toast message to "セッションをアーカイブしました" or similar. This is a minor frontend text change.

## Migration Plan

1. **Deploy migration**: Run `002_add_session_status.sql` against production Postgres via Supabase SQL Editor or migration tool
2. **Deploy backend**: Updated `db_helper.py` and `main.py` with archive semantics
3. **Deploy frontend**: If toast message change is included
4. **Rollback strategy**: 
   - Backend can be rolled back independently (old code would just ignore status column and continue hard-deleting)
   - Migration is additive (new column with default), so rollback is safe - the column can remain unused

## Open Questions

- Should we log/audit archive operations? (Deferrable - no current audit logging pattern exists)
