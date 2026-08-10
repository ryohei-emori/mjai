## 1. Spec Accuracy Verification

- [x] 1.1 Verify `### Requirement: List Proposals for a Correction History` and its scenarios match `GET /histories/{history_id}/proposals` in `backend/app/main.py`
- [x] 1.2 Verify `### Requirement: Create a Proposal Record` and its scenarios match `POST /proposals` in `backend/app/main.py`
- [x] 1.3 Verify `### Requirement: Proposal Selection, Modification, and Ordering Metadata` matches the `AIProposals` table in `backend/db/schema.sql` and the SQLite helper functions in `backend/app/db_helper.py`
- [x] 1.4 Confirm the documented `USE_POSTGRESQL` fallback/error behavior matches the current code exactly (no fallback on the default PostgreSQL path; `KeyError` on the default POST path due to schema mismatch)

## 2. No Implementation Work

- [x] 2.1 No code changes required — this change documents already-implemented, already-deployed behavior only
- [x] 2.2 Do not modify `backend/app/main.py`, `backend/app/db_helper.py`, or `backend/db/schema.sql` as part of this change
- [x] 2.3 If a future change decides to fix the known default-backend defects noted in the spec (PostgreSQL key mismatch on proposal creation, unhandled 500s, missing `historyId`/`type` validation), open a separate OpenSpec change with `MODIFIED Requirements` against this baseline

## 3. Follow-up

- [x] 3.1 Once this baseline change is reviewed and accepted, archive it (`openspec archive`) so `openspec/specs/ai-proposal-management/spec.md` becomes the source of truth — out of scope for this change, left for the project owner
