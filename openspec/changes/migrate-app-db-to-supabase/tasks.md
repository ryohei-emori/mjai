## 1. Schema Preparation (Supabase)

- [x] 1.1 Create `backend/supabase/migrations/003_align_ai_proposals_schema.sql` that adds columns `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order` to the existing `ai_proposals` table
- [x] 1.2 Verify `002_add_session_status.sql` is compatible with Supabase (already applied or ready to apply)
- [ ] 1.3 Apply migrations to Supabase project via Supabase CLI (`supabase db push`) or SQL Editor — **Manual step: requires Supabase dashboard/CLI access**

## 2. Backend Code: Remove SQLite Path

- [x] 2.1 In `backend/app/db_helper.py`, remove `get_sqlite_db`, `DB_PATH`, and all `*_sqlite` functions (`fetch_sessions_sqlite`, `insert_session_sqlite`, `delete_session_sqlite`, `update_session_sqlite`, `fetch_session_sqlite`, `fetch_histories_by_session_sqlite`, `insert_history_sqlite`, `fetch_proposals_by_history_sqlite`, `insert_proposal_sqlite`)
- [x] 2.2 Remove `sqlite3` import from `db_helper.py`
- [x] 2.3 Update `fetch_session` to return a camelCase dict (map `session_id` → `sessionId`, etc.) matching the pattern in `fetch_sessions`
- [x] 2.4 Update `insert_proposal` to use the full field set (`type`, `original_after_text`, etc.) instead of `proposal_text`/`confidence_score`
- [x] 2.5 Update `fetch_proposals_by_history` to select and return the full field set with camelCase mapping, ordered by `selected_order ASC NULLS FIRST`
- [x] 2.6 Update `insert_history` to return the created history object (not `None`)

## 3. Backend Code: Remove USE_POSTGRESQL Branching

- [x] 3.1 In `backend/app/main.py`, remove all `if os.environ.get("USE_POSTGRESQL"...)` branching in `get_sessions`, `create_session`, `get_histories`, `create_history`, `get_proposals`, `create_proposal`, `delete_session`, `update_session`, `get_session`
- [x] 3.2 Remove paired `except Exception as e: ... fallback to SQLite ...` retry blocks in each route
- [x] 3.3 Remove the now-unused SQLite imports from `main.py`'s `from .db_helper import (...)` block
- [x] 3.4 Simplify route bodies to use only the Postgres helper functions

## 4. Configuration Updates

- [x] 4.1 Update `conf/.env.example`: change `DATABASE_URL` comment to reference Supabase format (`postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`)
- [x] 4.2 Remove `USE_POSTGRESQL` from `conf/.env.example`
- [x] 4.3 Add comment noting `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL` are migration-only and can be removed after migration

## 5. Documentation Updates

- [x] 5.1 Update `AGENTS.md` "Database constraints" section to reflect single Supabase Postgres backend (remove dual-path description, USE_POSTGRESQL gotcha, SQLite file references)
- [x] 5.2 Update `AGENTS.md` environment variables table: remove `USE_POSTGRESQL`, update `DATABASE_URL` description to reference Supabase
- [x] 5.3 Update `docs/DESIGN.md` section 5.2 (Data model/storage) to describe single Supabase Postgres backend
- [x] 5.4 Update `docs/DESIGN.md` section 8 (Future Work) to mark `migrate-app-db-to-supabase` as implemented
- [x] 5.5 Update `docs/DESIGN.md` diagram to show Supabase as both Auth and Database

## 6. Data Migration (Manual)

- [ ] 6.1 Export data from current Render Postgres using `pg_dump` (or from SQLite `app.db` if that's the source of truth) — **Manual step: requires DATABASE_URL credentials**
- [ ] 6.2 Import data to Supabase Postgres via `psql` or Supabase SQL Editor — **Manual step: requires Supabase dashboard access**
- [ ] 6.3 Verify row counts match between source and target for `sessions`, `correction_histories`, `ai_proposals`

## 7. Environment Switch

- [ ] 7.1 Update `conf/.env` to point `DATABASE_URL` at Supabase — **Manual step: local config file is git-ignored**
- [ ] 7.2 Update Render environment variables to point `DATABASE_URL` at Supabase — **Manual step: requires Render dashboard access**
- [ ] 7.3 Verify Vercel environment variables (if frontend makes API calls that depend on backend config) — **Manual step: requires Vercel dashboard access**

## 8. Verification

- [ ] 8.1 Run existing backend tests (`pytest backend/tests/`) to confirm no regressions
- [ ] 8.2 Manually test `GET /sessions`, `POST /sessions`, `GET /sessions/{id}`, `PUT /sessions/{id}`, `DELETE /sessions/{id}` against Supabase
- [ ] 8.3 Manually test `GET /sessions/{id}/histories`, `POST /histories` against Supabase
- [ ] 8.4 Manually test `GET /histories/{id}/proposals`, `POST /proposals` against Supabase
- [ ] 8.5 Confirm migrated data is visible through the frontend UI

## 9. Cleanup (Deferred)

- [ ] 9.1 Decommission Render Postgres database — **Manual step: defer until verification complete; requires Render dashboard**
- [ ] 9.2 Mark `backend/db/app.db` and `backend/db/schema.sql` as historical (or remove in follow-up change)
- [ ] 9.3 Remove `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL` from `.env.example` after migration workflow is no longer needed
