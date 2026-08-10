> **CANCELLED (2026-08-11):** Rejected — keep Render Postgres for app data; Supabase Auth-only. Implementation was not applied. See `CANCELLED.md`. Delta specs were not synced to main specs.

## Why

The backend currently maintains two parallel, incompatible persistence paths — an `asyncpg`/Postgres path (snake_case columns, tables `sessions`/`correction_histories`/`ai_proposals`) and a `sqlite3` path (camelCase columns, tables `Sessions`/`CorrectionHistories`/`AIProposals`) — selected per-request by the `USE_POSTGRESQL` env var (default `"true"`). This dual-path design is already broken in practice: several Postgres-path routes build camelCase dicts and pass them into snake_case-keyed `asyncpg` helpers (e.g. `POST /sessions`, `GET /sessions/{id}`, `POST /proposals`), causing `KeyError`s under the default configuration, and the code's "fallback to SQLite on Postgres failure" comments are misleading — when `USE_POSTGRESQL=true` every route re-raises the exception instead of falling back. The project owner has confirmed the product direction: consolidate exclusively on Supabase (Postgres) as the single persistence backend. This removes a confirmed source of production bugs and the ongoing cost of maintaining two schemas that have already drifted apart (the `ai_proposals` table in `backend/supabase/migrations/001_initial_schema.sql`/`db_helper.py` stores only `proposal_text`/`confidence_score`, while the SQLite `AIProposals` table — the schema the app's proposal UI actually depends on — stores `type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`).

## What Changes

- **BREAKING**: Remove the SQLite persistence path (`sqlite3`-based functions in `backend/app/db_helper.py`, `backend/db/schema.sql`, `backend/db/app.db` as a live data source) from the request-serving code path.
- **BREAKING**: Remove the `USE_POSTGRESQL` environment variable and all per-route `if os.environ.get("USE_POSTGRESQL"...)` branching in `backend/app/main.py`. Supabase Postgres becomes the only backend; there is no runtime backend switch.
- **BREAKING**: Remove the misleading "fallback to SQLite on Postgres failure" logic and comments (the fallback does not actually run today when `USE_POSTGRESQL=true`, so removing it changes no observed production behavior, but removes dead/misleading code and the `except`-retry-then-swallow-into-200 behavior on the SQLite-only paths).
- Reconcile the `ai_proposals` table schema so it actually holds every field the product depends on (`type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`), replacing the narrower legacy `proposal_text`/`confidence_score` shape currently in `backend/supabase/migrations/001_initial_schema.sql`.
- Standardize the column-naming convention across the stack (DB columns snake_case, API request/response bodies remain camelCase as the frontend already expects, translated by an explicit mapping layer in `backend/app/db_helper.py`) — see `design.md` for the chosen convention and rejected alternatives.
- Migrate any existing data in `backend/db/app.db` to Supabase Postgres using a corrected version of the existing one-way migration scripts (`backend/db/migrate_local.py` / the referenced-but-currently-absent `migrate_to_supabase.py`), extended to carry the full `AIProposals` field set losslessly.
- Update `conf/.env.example` to drop `USE_POSTGRESQL` and `SOURCE_DATABASE_URL`/`TARGET_DATABASE_URL` (migration-only) once migration is complete, and clarify `DATABASE_URL` always points at Supabase.
- Out of scope (explicitly not designed here, only noted as future considerations): AI-generation provider changes (WebLLM), frontend deployment target (Vercel), and authentication (Google/Supabase Auth) — these are sibling changes owned by others. Supabase Auth may later provide a `user_id` to scope rows per-user; this change does not add user scoping but the schema decisions here should not preclude adding a nullable `user_id` column later.

## Capabilities

### New Capabilities

(none — this change modifies persistence behavior of existing capabilities only)

### Modified Capabilities

- `session-management`: Session data SHALL be persisted exclusively in Supabase Postgres; the `USE_POSTGRESQL` backend-selection requirement and its SQLite/fallback scenarios are superseded by a single-backend requirement.
- `correction-history`: Correction history data SHALL be persisted exclusively in Supabase Postgres; the dual-path storage-backend-selection requirement is superseded by a single-backend requirement, and the double-JSON-encoding behavior tied to the SQLite insert path no longer applies to the persisted path.
- `ai-proposal-management`: AI proposal data SHALL be persisted exclusively in Supabase Postgres, with the `ai_proposals` schema carrying the full field set (`type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`) needed to serve `GET /histories/{history_id}/proposals` and `POST /proposals` correctly; the "default PostgreSQL backend is non-functional" bug scenario is resolved by construction.

Note: these three delta spec files describe **target** (post-migration) persistence behavior only — they do not restate the baselines' non-persistence requirements (request validation, response shape, ordering, etc.), which are unaffected. Each delta should eventually be reconciled with (and supersede the persistence-related requirements of) the corresponding `openspec/changes/baseline-*` change once those baselines are synced into `openspec/specs/`.

## Impact

- **Code**: `backend/app/db_helper.py` (remove all `*_sqlite` functions and `get_sqlite_db`), `backend/app/main.py` (remove all `USE_POSTGRESQL` branching, retry/fallback `except` blocks, and the now-single-path route bodies), `backend/db/schema.sql` (remove or explicitly mark dev-only/deprecated), `backend/supabase/migrations/001_initial_schema.sql` (superseded by a corrected migration that matches the real `AIProposals` field set).
- **Data**: One-time migration of `backend/db/app.db` (checked into the repo, several MB, real persisted data per `AGENTS.md`) into Supabase Postgres using a corrected migration script; existing `backend/db/migrate_local.py` must be extended, not run as-is, because it currently drops most `AIProposals` fields.
- **Config**: `conf/.env.example` — drop `USE_POSTGRESQL`; keep `DATABASE_URL` pointed at Supabase; drop migration-only vars after the one-time migration.
- **Docs**: `docs/github-secrets.md` / CI workflows reviewed for any Supabase-specific secrets needed post-consolidation (no code change to CI itself is designed here beyond what's listed in `tasks.md`).
- **Dependencies**: No new external dependency — `asyncpg` is already a backend dependency; `sqlite3` (stdlib) usage is removed from the request path.
- **Not affected**: AI-generation logic (Gemini/WebLLM), frontend deployment, authentication — see "Out of scope" above.
