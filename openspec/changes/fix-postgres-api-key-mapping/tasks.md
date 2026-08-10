## 1. Database Migration

- [x] 1.1 Create migration file `backend/supabase/migrations/003_align_ai_proposals_schema.sql` to add missing columns (`type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`) to the PostgreSQL `ai_proposals` table

## 2. Fix Session Fetch (GET /sessions/{session_id})

- [x] 2.1 Update `fetch_session()` in `backend/app/db_helper.py` to use column aliases (matching `fetch_sessions()` pattern) so returned dict has camelCase keys: `sessionId`, `name`, `createdAt`, `updatedAt`, `correctionCount`

## 3. Fix Session Update (PUT /sessions/{session_id})

- [x] 3.1 Add camelCase-to-snake_case field mapping in `update_session()` in `backend/app/db_helper.py` so that client-sent keys like `correctionCount` and `isOpen` are mapped to `correction_count` and `is_open` before checking the allow-list

## 4. Fix Proposal Functions (POST /proposals, GET /histories/{id}/proposals)

- [x] 4.1 Update `insert_proposal()` in `backend/app/db_helper.py` to accept camelCase keys from `main.py` and map them to the new snake_case PostgreSQL columns (`proposal_id`, `history_id`, `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`)
- [x] 4.2 Update `fetch_proposals_by_history()` in `backend/app/db_helper.py` to use column aliases returning camelCase keys (`proposalId`, `historyId`, `type`, `originalAfterText`, etc.)

## 5. Backend Tests

- [x] 5.1 Add test for `GET /sessions/{session_id}` PostgreSQL path in `backend/tests/test_sessions.py` verifying camelCase response keys
- [x] 5.2 Add test for `PUT /sessions/{session_id}` PostgreSQL path verifying camelCase input fields are correctly mapped and persisted
- [x] 5.3 Create `backend/tests/test_proposals.py` with tests for `POST /proposals` and `GET /histories/{id}/proposals` on PostgreSQL path using mocked asyncpg

## 6. Verification

- [x] 6.1 Run all backend tests (`pytest backend/tests/`) and verify they pass
