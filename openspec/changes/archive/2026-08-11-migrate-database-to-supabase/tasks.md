> **CANCELLED (2026-08-11):** All tasks below are cancelled. Project decision: keep Render Postgres for app data; Supabase Auth-only. No implementation was applied. See `CANCELLED.md`.

## 1. Schema Preparation (Supabase)

- [ ] 1.1 Author a new migration file (e.g. `backend/supabase/migrations/002_align_ai_proposals_schema.sql`) that redefines `ai_proposals` with columns `proposal_id`, `history_id`, `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order` (do not edit the already-applied `001_initial_schema.sql` in place) — **CANCELLED**
- [ ] 1.2 Add indexes matching current access patterns (e.g. `idx_proposals_history_id_selected_order` for the `ORDER BY selected_order ASC` query) to the new migration — **CANCELLED**
- [ ] 1.3 Apply the migration to a non-production Supabase project/schema first for dry-run verification — **CANCELLED**
- [ ] 1.4 Confirm `sessions`/`correction_histories` Postgres schemas (already snake_case, per current `db_helper.py` usage) need no further column changes beyond what's used today — **CANCELLED**

## 2. Data Migration Script

- [ ] 2.1 Back up `backend/db/app.db` (e.g. copy to a separate, non-repo location) before any migration run — **CANCELLED**
- [ ] 2.2 Extend `backend/db/migrate_local.py` (or add `backend/db/migrate_to_supabase.py`) so the `ai_proposals` insert maps every SQLite `AIProposals` column (`type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`) to the corresponding snake_case column from task 1.1, with no lossy derivation (remove the `confidence_score`-synthesis logic) — **CANCELLED**
- [ ] 2.3 Point the script at the target Supabase `DATABASE_URL` (via `asyncpg`), reusing the existing UUID-validation/remapping and timestamp-parsing helpers already present in `migrate_local.py` — **CANCELLED**
- [ ] 2.4 Run the corrected script against a copy of `backend/db/app.db` targeting the non-production Supabase project/schema from task 1.3 — **CANCELLED**
- [ ] 2.5 Verify row counts match per table (`sessions`, `correction_histories`, `ai_proposals`) between SQLite source and Supabase target — **CANCELLED**
- [ ] 2.6 Spot-check migrated records, including at least one proposal each with `isSelected`/`isModified`/`isCustom` true and false, and one with a non-null `selectedOrder` — **CANCELLED**
- [ ] 2.7 Apply the schema migration (task 1.1) to the real production Supabase project — **CANCELLED**
- [ ] 2.8 Run the corrected script against the real `backend/db/app.db` targeting the real production `DATABASE_URL` — **CANCELLED**
- [ ] 2.9 Re-verify row counts and spot-checks against the production Supabase target — **CANCELLED**

## 3. Backend Code: Remove Dual-Path Branching

- [ ] 3.1 In `backend/app/db_helper.py`, remove `get_sqlite_db`, `DB_PATH`, and every `*_sqlite` function (`fetch_sessions_sqlite`, `insert_session_sqlite`, `delete_session_sqlite`, `update_session_sqlite`, `fetch_session_sqlite`, `fetch_histories_by_session_sqlite`, `insert_history_sqlite`, `fetch_proposals_by_history_sqlite`, `insert_proposal_sqlite`) — **CANCELLED**
- [ ] 3.2 Extend every remaining Postgres-facing function in `backend/app/db_helper.py` to accept/return camelCase dicts and perform the snake_case column translation internally (following the existing `fetch_sessions` pattern), so `main.py` never touches snake_case — **CANCELLED**
- [ ] 3.3 Fix `insert_session` to correctly map the camelCase session dict fields to snake_case columns (fixes the confirmed `KeyError` bug) — **CANCELLED**
- [ ] 3.4 Fix `fetch_session` to return a camelCase dict so `main.py`'s `session["sessionId"]`-style access works (fixes the confirmed `KeyError` bug) — **CANCELLED**
- [ ] 3.5 Update `insert_proposal` to use the corrected `ai_proposals` schema (task 1.1) and accept the full camelCase proposal field set from `main.py` (fixes the confirmed non-functional-proposal-creation bug) — **CANCELLED**
- [ ] 3.6 Update `fetch_proposals_by_history` to order by `selected_order ASC` (nulls first) to match the product-required ordering, and return camelCase fields — **CANCELLED**
- [ ] 3.7 In `backend/app/main.py`, remove the `USE_POSTGRESQL` import/usage and every `if os.environ.get("USE_POSTGRESQL", "true")... else: ...` branch in `get_sessions`, `create_session`, `get_histories`, `create_history`, `get_proposals`, `create_proposal`, `delete_session`, `update_session`, `get_session` — **CANCELLED**
- [ ] 3.8 Remove the paired `except Exception as e: ... fallback to SQLite ...` retry blocks in each of the routes above, replacing with a single straightforward try/except that logs and re-raises (or returns an error response consistent with the spec deltas) — **CANCELLED**
- [ ] 3.9 Remove the now-unused SQLite imports from `backend/app/main.py`'s `from .db_helper import (...)` block — **CANCELLED**
- [ ] 3.10 Update `create_history`/`create_proposal` request-dict construction in `main.py` to build a single camelCase dict (remove the duplicated snake_case+camelCase key construction that existed only to satisfy both old paths) — **CANCELLED**

## 4. Deprecate SQLite Artifacts

- [ ] 4.1 Mark `backend/db/schema.sql` as historical/reference-only with a header comment explaining it is no longer a live code path (used only as the source schema for the completed migration) — **CANCELLED**
- [ ] 4.2 Remove or gate any startup/bootstrap code path that calls `backend/db/init_db.py` or otherwise initializes the SQLite database at app startup — **CANCELLED**
- [ ] 4.3 Leave `backend/db/app.db` in place (do not delete) as a historical backup until a separate, later change decides its final disposition — **CANCELLED**

## 5. Configuration Updates

- [ ] 5.1 Remove `USE_POSTGRESQL` from `conf/.env.example` — **CANCELLED**
- [ ] 5.2 Update the `DATABASE_URL` comment/example in `conf/.env.example` to state it always points at Supabase Postgres (not a generic Postgres host) — **CANCELLED**
- [ ] 5.3 Remove `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL` from `conf/.env.example` once the one-time migration (section 2) is confirmed complete in production — **CANCELLED**
- [ ] 5.4 Update `AGENTS.md`'s "Database constraints" section to reflect the removal of the dual-path/fallback behavior once this change is implemented (tracked here since it's the source of the documented gotcha this change fixes) — **CANCELLED**

## 6. CI/Docs Review

- [ ] 6.1 Review `docs/github-secrets.md` and any GitHub Actions workflow referencing `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL`/`USE_POSTGRESQL` (e.g. `backend/.github/workflows/migrate-database.yml`) and update or remove references made obsolete by this change — **CANCELLED**
- [ ] 6.2 Confirm `.github/workflows/deploy.yml`'s post-deploy `/health` check still passes with the single-backend backend (no code change expected, verification only) — **CANCELLED**

## 7. Verification

- [ ] 7.1 Manually or via automated test, exercise `GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, `DELETE /sessions/{id}` against Supabase and confirm no `KeyError`/500s from naming mismatches — **CANCELLED**
- [ ] 7.2 Exercise `GET /sessions/{id}/histories` and `POST /histories` against Supabase and confirm the create response now returns the persisted record (not `null`) — **CANCELLED**
- [ ] 7.3 Exercise `GET /histories/{id}/proposals` and `POST /proposals` against Supabase with a full field payload (including `isSelected`, `isModified`, `isCustom`, `selectedOrder`) and confirm all fields round-trip correctly — **CANCELLED**
- [ ] 7.4 Confirm the migrated production data (task 2.8) is visible and correct through the above endpoints — **CANCELLED**
