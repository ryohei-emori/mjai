## Context

See `proposal.md` — Why for motivation. Summary of current state this design resolves:

- `backend/app/db_helper.py` has two independent persistence implementations: an `asyncpg`-based Postgres path (snake_case columns) and a `sqlite3`-based path (camelCase columns, file at `backend/db/app.db`).
- `backend/app/main.py` branches on `USE_POSTGRESQL` (default `"true"`) per-request to select which helper functions to call.
- The `ai_proposals` Postgres schema (`001_initial_schema.sql`) is incomplete: it has `proposal_text`/`confidence_score` but lacks the full field set the application needs (`type`, `original_after_text`, `original_reason`, etc.).
- Supabase is already used for Auth (project `fqyhrubqkpuyliqojbai`); this change consolidates app data onto the same project.
- Render Postgres is currently the app data target in `.env.example`; this change retires that dependency.

## Goals / Non-Goals

**Goals:**
- Migrate `DATABASE_URL` from Render Postgres to Supabase Postgres (same project as Auth)
- Align `ai_proposals` schema with the full application data model
- Remove SQLite dual-path code from `db_helper.py` and `main.py`
- Remove `USE_POSTGRESQL` environment variable and branching
- Update documentation (`AGENTS.md`, `docs/DESIGN.md`) to reflect single Supabase backend
- Document RLS enablement path for future work

**Non-Goals:**
- Client-side Supabase SDK direct CRUD (phase 2)
- Moving FastAPI compute from Render to Vercel (phase 2)
- Full RLS policy tightening beyond permissive policies (phase 2)
- Data migration automation — migration is a manual one-time step

## Decisions

### 1. Use Supabase Postgres as the single persistence backend

**Decision**: Point `DATABASE_URL` at the existing Supabase project (`fqyhrubqkpuyliqojbai.supabase.co`) already used for Auth. FastAPI continues to connect via `asyncpg` using a standard Postgres connection string.

**Why**: Unifies Auth + data on one platform, simplifies free-tier deployment, enables future RLS. Supabase Postgres is fully compatible with the existing `asyncpg` code path.

**Alternatives considered**:
- *Keep Render Postgres* — rejected per user decision to consolidate on Supabase
- *Use Supabase SDK from backend* — rejected as unnecessary complexity; standard Postgres connection is simpler and already working

### 2. Align `ai_proposals` schema via additive migration

**Decision**: Create `backend/supabase/migrations/003_align_ai_proposals_schema.sql` that adds the missing columns (`type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`) to the existing `ai_proposals` table. The legacy `proposal_text`/`confidence_score` columns are retained for backward compatibility but not used.

**Why**: Additive migration is non-destructive and can be applied to a table that already has data. Dropping legacy columns can be done in a follow-up cleanup.

**Alternatives considered**:
- *Drop and recreate `ai_proposals`* — rejected as destructive if the table has existing data
- *Create a new table `ai_proposals_v2`* — rejected as unnecessary complexity

### 3. Remove SQLite code path entirely

**Decision**: Remove all `*_sqlite` functions from `db_helper.py`, remove `USE_POSTGRESQL` branching from `main.py`, and remove `get_sqlite_db` / `DB_PATH` references. The application has exactly one persistence path.

**Why**: Dual-path code doubles maintenance and has already drifted (different column names, different behavior on delete). A single path is simpler and less error-prone.

**Alternatives considered**:
- *Keep SQLite for local dev* — rejected; local dev can use a local Postgres (Docker) or connect to Supabase. The checked-in `app.db` is historical data, not a live dev dependency.

### 4. camelCase/snake_case mapping stays in `db_helper.py`

**Decision**: Postgres columns remain snake_case. `db_helper.py` functions accept/return camelCase dicts (matching frontend expectations) and translate internally. This is already the pattern for `fetch_sessions()`.

**Why**: Consistent with Postgres/Supabase conventions. Frontend already expects camelCase. Single mapping layer avoids bugs.

### 5. RLS remains permissive (phase 1)

**Decision**: Existing RLS policies (`USING (true)`) are retained. The application connects with service-role credentials (or a dedicated Postgres user), not anon key. RLS tightening to `authenticated` or per-user scope is documented as phase 2.

**Why**: Phase 1 goal is to unify the database, not redesign authorization. Current app is single-user (email allow-list) so RLS isn't security-critical yet.

### 6. Data migration is manual

**Decision**: Data migration from Render Postgres (or SQLite `app.db`) to Supabase is a manual one-time step. Provide migration script guidance but do not automate destructive operations.

**Why**: Safe migration requires verification. Automating could destroy production data if misconfigured.

## Risks / Trade-offs

- **[Risk] Live data on Render Postgres must be migrated before cutover.** → Mitigation: Document migration steps; user must manually run `pg_dump`/`pg_restore` or use `migrate_to_supabase.py` tooling after verifying target.
- **[Risk] `ai_proposals` may have existing rows in Supabase that need backfilling.** → Mitigation: Migration 003 is additive; existing rows get NULL for new columns. Backfill can be done via SQL if needed.
- **[Risk] Local dev without Postgres is no longer supported.** → Mitigation: Document how to run local Postgres (Docker) or connect to Supabase dev project. This is a one-time developer setup change.
- **[Trade-off] SQLite file `backend/db/app.db` becomes unused.** → Accepted; file is kept as historical backup until explicitly removed in a cleanup change.
- **[Trade-off] Supabase free tier may pause after inactivity.** → Accepted as a free-tier constraint; user is aware.

## Migration Plan

1. **Apply schema migrations to Supabase**: `002_add_session_status.sql` (if not already applied) and `003_align_ai_proposals_schema.sql`.
2. **Migrate data**: If Render Postgres has production data, export via `pg_dump` and import to Supabase via `psql` or Supabase SQL Editor.
3. **Update `conf/.env`**: Point `DATABASE_URL` at Supabase (format: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`).
4. **Deploy backend code**: Remove SQLite code path, update `db_helper.py` / `main.py`.
5. **Verify**: Confirm `GET /sessions`, `POST /sessions`, etc. work against Supabase.
6. **Decommission Render Postgres**: Once verified, delete the Render database (manual dashboard action).

**Rollback strategy**: If issues arise post-deploy, revert code changes (git revert) and point `DATABASE_URL` back at Render Postgres. Data should still be present on both until Render is explicitly decommissioned.

## Open Questions

- Exact timing of Render Postgres decommission — defer to user confirmation after successful Supabase verification.
- Whether to drop legacy `proposal_text`/`confidence_score` columns from `ai_proposals` — defer to cleanup change after this migration is stable.
