## 1. Database Migration

- [x] 1.1 Create `backend/supabase/migrations/002_add_session_status.sql` with `ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active'`

## 2. Backend Changes

- [x] 2.1 Update `fetch_sessions()` in `backend/app/db_helper.py` to filter by `status = 'active' OR status IS NULL`
- [x] 2.2 Update `delete_session()` in `backend/app/db_helper.py` to set `status = 'archived'` instead of DELETE cascade
- [x] 2.3 Update `delete_session` endpoint in `backend/app/main.py` to return `"Session archived"` message

## 3. Frontend Changes

- [x] 3.1 Update toast message in `frontend/src/app/page.tsx` from "セッションの削除" to "セッションのアーカイブ" (or keep delete terminology per UX judgment) — **Decision: Keep "削除" terminology** since the trash icon visual remains; from user perspective the action is "remove from view"

## 4. Testing

- [x] 4.1 Add backend test: archiving a session hides it from `GET /sessions` list
- [x] 4.2 Add backend test: archived session's histories and proposals remain intact in database
- [x] 4.3 Run existing backend test suite to confirm no regressions — **Result: 2 archive tests PASSED.** Other tests have pre-existing TestClient compatibility errors (starlette/httpx version mismatch unrelated to this change)
