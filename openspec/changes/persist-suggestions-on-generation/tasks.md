## 1. Database migration

- [x] 1.1 Add `backend/supabase/migrations/005_pending_suggestion_histories.sql` with `status` (default `'confirmed'`), `overall_comment`, `provider`, `client_job_id` on `correction_histories`
- [x] 1.2 Document applying the migration to shared Supabase in a short comment or AGENTS note when docs are updated

## 2. Backend history API

- [x] 2.1 Extend `insert_history` / `fetch_histories_by_session` in `db_helper.py` for the new columns (camelCase in API responses)
- [x] 2.2 Extend `POST /histories` in `main.py` to accept `status`, `overallComment`, `provider`, `clientJobId` (default status `confirmed`)
- [x] 2.3 Add `update_history` helper + `PUT /histories/{history_id}` for promote/finalize fields
- [x] 2.4 Add backend tests for pending create, list fields, and PUT promote (mocked asyncpg)

## 3. Backend proposal update API

- [x] 3.1 Add `update_proposal` in `db_helper.py` for selection/edit fields
- [x] 3.2 Add `PUT /proposals/{proposal_id}` in `main.py`
- [x] 3.3 Add/extend tests for proposal update path

## 4. Frontend API + persist on generation

- [x] 4.1 Extend `frontend/src/app/api.ts` history/proposal types and add `updateHistory` / `updateProposal` helpers
- [x] 4.2 On successful `processJobAsync` (cloud or offline WebLLM), create pending history + proposals and attach `historyId` to the job; toast on persist failure without clearing local job
- [x] 4.3 Extend `QueuedJob` (and storage restore) with optional `historyId` / proposal id mapping as needed

## 5. Frontend hydrate + confirm

- [x] 5.1 Update `loadSessionDetails` to split pending vs confirmed: confirmed → History; pending → merge into Job Queue (dedupe by historyId/clientJobId); avoid clobbering active confirming job edits
- [x] 5.2 Update `saveCorrections` to PUT history + update proposals when `historyId` exists; keep legacy create path as fallback; no duplicate History junk
- [x] 5.3 Adjust frontend tests covering persist-on-success and/or hydrate/confirm paths where practical

## 6. Docs

- [x] 6.1 Update `AGENTS.md` briefly: suggestions persist to DB on generation (pending) then confirm promotes
- [x] 6.2 Update `docs/SYSTEM-DESIGN.md` data model / API notes for pending histories and new endpoints
