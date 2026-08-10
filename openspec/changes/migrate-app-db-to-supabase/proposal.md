## Why

The project currently maintains Auth on Supabase but app data (sessions, correction histories, AI proposals) on Render Postgres, creating a split-brain architecture that doubles operational costs and complicates free-tier deployment. Unifying Auth **and** app data on Supabase simplifies the stack, enables future RLS-based authorization, and positions the project for a serverless/free-tier profile where Render can be retired.

**Decision reversal context:** An earlier `migrate-database-to-supabase` change was cancelled in favor of keeping Render Postgres. This decision is now reversed based on a free-tier architecture recommendation: consolidate on Supabase for both Auth and persistence, retire Render database dependency, and prepare for future direct-from-frontend CRUD via Supabase SDK (phase 2).

## What Changes

- **Migrate `DATABASE_URL`** from Render Postgres to the existing Supabase project (`fqyhrubqkpuyliqojbai`) already used for Auth.
- **Apply schema migrations** to Supabase Postgres: ensure `sessions`, `correction_histories`, and `ai_proposals` tables match the application's expectations (including `status` column for soft-archive, and the full `ai_proposals` field set the app requires).
- **Point FastAPI at Supabase** as the single persistence backend (`DATABASE_URL` in `conf/.env`). The FastAPI backend continues to run on Render in phase 1, but only for compute; database traffic moves to Supabase.
- **Remove SQLite dual-path code** from `backend/app/db_helper.py` and `backend/app/main.py` (the `USE_POSTGRESQL` branching and `*_sqlite` functions). Supabase Postgres becomes the only persistence path.
- **Update configuration/documentation**: `conf/.env.example`, `AGENTS.md`, `docs/DESIGN.md` to reflect Supabase as both Auth and app DB; remove references to Render Postgres for data storage and the obsolete SQLite fallback.
- **RLS enablement path** (documented, not fully implemented in phase 1): Supabase tables already have RLS enabled with permissive policies; tightening to `authenticated` or per-user scope is documented as phase 2 once client-direct CRUD is in scope.
- **BREAKING**: The SQLite persistence path is removed; local development requires a Postgres connection (local or Supabase).
- **Out of scope (phase 2/future)**: Client-direct Supabase SDK CRUD from frontend; moving FastAPI compute from Render to Vercel API routes; full RLS policy tightening.

## Capabilities

### New Capabilities

(None — this change modifies persistence behavior of existing capabilities only)

### Modified Capabilities

- `session-management`: Session data SHALL be persisted exclusively in Supabase Postgres; the `USE_POSTGRESQL` backend-selection requirement and its SQLite/fallback scenarios are superseded by a single-backend requirement targeting Supabase.
- `correction-history`: Correction history data SHALL be persisted exclusively in Supabase Postgres; the dual-path storage-backend-selection requirement is superseded by a single-backend requirement.
- `ai-proposal-management`: AI proposal data SHALL be persisted exclusively in Supabase Postgres, with the `ai_proposals` schema carrying the full field set (`type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`) needed to serve `GET /histories/{history_id}/proposals` and `POST /proposals` correctly.

## Impact

- **Code**: `backend/app/db_helper.py` (remove all `*_sqlite` functions and `get_sqlite_db`), `backend/app/main.py` (remove all `USE_POSTGRESQL` branching, simplify routes to single Postgres path).
- **Database**: Supabase Postgres at `fqyhrubqkpuyliqojbai.supabase.co` becomes the production database; Render Postgres can be decommissioned after data migration.
- **Config**: `conf/.env.example` — update `DATABASE_URL` comment to reference Supabase; remove `USE_POSTGRESQL`; keep `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL` during migration window.
- **Docs**: `AGENTS.md`, `docs/DESIGN.md` — update to reflect Supabase as both Auth + app DB; remove dual-path gotchas; document RLS path.
- **Data migration**: One-time copy from Render Postgres to Supabase Postgres (schema migrations are additive; data copy requires `SOURCE_DATABASE_URL` → `TARGET_DATABASE_URL` tooling or manual `pg_dump`/`pg_restore`).
- **Dependencies**: No new external dependency — `asyncpg` is already a backend dependency; `sqlite3` (stdlib) usage is removed from the request path.
- **Not affected**: AI-generation logic (WebLLM), frontend deployment target (Vercel is a separate change), authentication flow (Supabase Auth already in place).
