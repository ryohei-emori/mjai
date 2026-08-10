## Context

See `proposal.md` - Why, for the full motivation. Summary of the current state this design must resolve:

- `backend/app/db_helper.py` has two independent implementations per entity (sessions, correction histories, AI proposals): an `asyncpg`-based Postgres path using snake_case columns (`sessions`, `correction_histories`, `ai_proposals`), and a `sqlite3`-based path using camelCase columns (`Sessions`, `CorrectionHistories`, `AIProposals`, backed by the checked-in file `backend/db/app.db`, schema in `backend/db/schema.sql`).
- `backend/app/main.py` branches on `os.environ.get("USE_POSTGRESQL", "true")` in every route to pick which helper functions to call, and wraps each call in a try/except that claims to "fall back to SQLite on Postgres failure" but, per the confirmed gotcha in `AGENTS.md`, only actually retries SQLite when `USE_POSTGRESQL` is explicitly `"false"` - under the default (`true`), failures are re-raised.
- The two schemas have already drifted apart in an unreconcilable way for one table: `backend/supabase/migrations/001_initial_schema.sql`'s `ai_proposals` table (`proposal_id`, `history_id`, `proposal_text`, `confidence_score`, `created_at`) does not have the columns the product's proposal UI actually needs, which only exist on the SQLite `AIProposals` table (`type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, `selectedOrder`). Under the default configuration, `POST /proposals` and `GET /histories/{id}/proposals` against Postgres are non-functional today (`KeyError` on insert; the fetch's `ORDER BY selectedOrder` is SQLite-only syntax that isn't even in the Postgres helper, which instead does `ORDER BY created_at DESC` - a different, currently-silent behavior mismatch).
- `sessions` and `correction_histories` tables are already reconcilable: their Postgres column shapes in `001_initial_schema.sql` already cover what the app needs (module bugs are in `main.py`'s route bodies building camelCase dicts, not in the target schema itself).
- Migration tooling: `backend/db/migrate_local.py` exists and migrates SQLite → a local Postgres instance, but only carries `proposal_text`/`confidence_score` for proposals (it derives a fabricated `confidence_score` from `isSelected`/`selectedOrder` and drops `type`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isModified`, `isCustom` entirely). `backend/db/migrate_to_supabase.py` is referenced by `AGENTS.md`, `docs/migration-plan.md`, and `.github/workflows/migrate-database.yml` (`python db/migrate_to_supabase.py`) but does not exist in the repository today - the CI workflow is currently broken/unrunnable.

## Goals / Non-Goals

**Goals:**
- Define the single canonical Postgres/Supabase schema (column names, types) for `sessions`, `correction_histories`, and `ai_proposals` that the app will use going forward, including the corrected `ai_proposals` shape.
- Decide the fate of `USE_POSTGRESQL`, `backend/db/schema.sql`, and `backend/db/app.db`.
- Define the naming-convention boundary between the DB layer (snake_case) and the API request/response layer (camelCase, unchanged for the frontend) and where the translation happens.
- Define the one-time data migration approach for existing rows in `backend/db/app.db`, including how the currently-missing `migrate_to_supabase.py` gets created/fixed.

**Non-Goals:**
- Does not change the frontend API contract (request/response field names, HTTP routes, status codes) - this is a persistence-layer-only change from the frontend's point of view.
- Does not add authentication, per-user row scoping, or Supabase Row Level Security policy changes beyond what already exists in `001_initial_schema.sql` (permissive `USING (true)` policies are left as-is; tightening RLS is a follow-on concern for the auth change).
- Does not redesign the Session -> CorrectionHistory -> AIProposal data model's relationships or add new entities.
- Does not touch AI-generation logic (Gemini/WebLLM), frontend deployment, or CI/CD infrastructure beyond the migration workflow's script reference.

## Decisions

### 1. Canonical column naming: snake_case in Postgres, camelCase stays at the API boundary

**Decision**: Postgres/Supabase columns remain snake_case (already the convention in `001_initial_schema.sql` and the `asyncpg` path). `backend/app/db_helper.py` becomes the single translation layer: its public functions accept/return the camelCase shape the routes and frontend already use, and internally map to/from snake_case columns.

**Why**: Postgres/Supabase tooling (RLS policies, `information_schema`, Supabase Studio) all assume snake_case by convention; fighting that would be unusual and non-idiomatic. The frontend already sends/expects camelCase (`sessionId`, `originalText`, etc.) and changing that would touch `frontend/src` for no product benefit. Keeping the translation inside `db_helper.py` (rather than spread across `main.py` route bodies, which is what causes today's `KeyError` bugs) is the actual bug fix: one mapping, in one place, per entity.

**Alternatives considered**:
- *camelCase columns in Postgres* (mirroring current SQLite convention) - rejected: non-idiomatic for Postgres/Supabase, and `001_initial_schema.sql` already ships snake_case in what is meant to be the production schema; changing it would mean redoing a migration that's already been run against a real Supabase project (per `docs/github-secrets.md` / CI secrets referencing an existing `DATABASE_URL`).
- *camelCase end-to-end incl. frontend* - rejected: forces an unrelated frontend change outside this proposal's scope.

### 2. `ai_proposals` schema is corrected, not left as-is

**Decision**: Replace `001_initial_schema.sql`'s `ai_proposals` table (`proposal_text`, `confidence_score`) with a corrected shape carrying the full field set the SQLite `AIProposals` table has today: `proposal_id`, `history_id`, `type`, `original_after_text`, `original_reason`, `modified_after_text`, `modified_reason`, `is_selected`, `is_modified`, `is_custom`, `selected_order`, `created_at`. This ships as a new, additive Supabase migration file (`002_correct_ai_proposals_schema.sql` or similar; exact filename decided during implementation) rather than editing `001_initial_schema.sql` in place, since `001` may already be applied to the live Supabase project.

**Why**: Per the baseline `ai-proposal-management` spec, `POST /proposals` and `GET /histories/{id}/proposals` are the routes that actually exercise this table, and every field they read/write is already in the SQLite shape - the Postgres shape was simply never kept in sync. There is no working code path today that uses `proposal_text`/`confidence_score` for anything a client depends on, so nothing is lost by replacing it, and doing so in-place (edit `001`) vs. as a new migration is safer for a schema that may already be live.

**Alternatives considered**:
- *Keep `proposal_text`/`confidence_score` and adapt the app to use them* - rejected: would require redesigning the proposal UI/data model (AI vs. custom proposals, selection order, modification tracking), which is out of scope and would be a product regression, not a migration.
- *Drop and recreate `ai_proposals` in place* - rejected as the default path since it's destructive to any already-migrated Supabase data; only acceptable if the team confirms the current Supabase `ai_proposals` table is empty/unused (flagged as an assumption below).

**Assumption**: This design assumes the live Supabase `ai_proposals` table (if `001_initial_schema.sql` has already been applied there) holds no rows worth preserving in its current shape, since the app has never successfully written to it in production (per the "Default PostgreSQL backend is non-functional for proposal creation" baseline scenario). If that assumption is wrong, `tasks.md` includes a verification step before any destructive schema change.

### 3. `USE_POSTGRESQL` is removed entirely, not kept as a dead flag

**Decision**: Remove the `USE_POSTGRESQL` environment variable and all branching on it from `backend/app/main.py` and `backend/app/db_helper.py`. There is exactly one persistence path after this change; a flag with only one live value adds cognitive overhead with no transition benefit.

**Why**: Keeping it "for a transition period" was considered, but there is no phased-rollout need here - Supabase is already the confirmed target and the SQLite path is already effectively broken for one of three entities. A no-op flag that always evaluates to the same branch is exactly the kind of dead-but-plausible-looking code that caused the original "fallback" confusion this proposal fixes. Removing it outright is also what the proposal.md's "What Changes" already commits to.

**Alternatives considered**: Keep `USE_POSTGRESQL` as a deprecated, ignored env var (log a warning if set to `"false"`) for one release to avoid surprising anyone with lingering config - rejected as unnecessary ceremony for an internal-only flag with no external consumers documented anywhere (`conf/.env.example` is the only place it's declared, and this change updates that file in the same commit).

### 4. `backend/db/schema.sql` is retired in place; `backend/db/app.db` is kept as a one-release safety net, not immediately deleted

**Decision**: `backend/db/schema.sql` is marked historical/reference-only (header comment noting it no longer backs any live code path) rather than deleted immediately, since it remains useful as the documented source schema for the migration in Decision 5. Any startup/bootstrap code that initializes SQLite via `backend/db/init_db.py` is removed from the app's request-serving path. `backend/db/app.db` itself is **not** deleted as part of this change - it is kept as a verified-migrated backup until a separate, later cleanup change confirms production has run stably on Supabase and decides its final disposition (delete, or move to `backend/db/legacy/`).

**Why**: This is the safer default: the migration script and workflow (`migrate_to_supabase.py`, `migrate-database.yml`) are new/unverified against a real Supabase target (see Risks), so keeping the multi-MB source-of-truth file around for one release after cutover costs little and provides a fast recovery path if the migration needs re-running or spot-checking, without relying solely on git history. Deleting it outright the moment code stops reading it is not necessary to achieve this change's goal (removing the dual-path *code*), and is better decided once there's real confidence in the migrated data.

**Alternatives considered**: Delete `schema.sql` and `app.db` immediately once the code path is removed - rejected as unnecessarily aggressive given the migration tooling is being created/fixed in the same change and hasn't been exercised against production yet; relying purely on git history for recovery during that initial risk window is less convenient than keeping the file present but clearly inert.

### 5. Migration approach: fix `migrate_local.py`'s proposal mapping, create the missing `migrate_to_supabase.py`, run once as a manual, verified step

**Decision**:
1. `backend/db/migrate_to_supabase.py` does not exist despite being referenced by `AGENTS.md`, `docs/migration-plan.md`, and `.github/workflows/migrate-database.yml`. It must be created before this change can be applied - built as a copy of `migrate_local.py`'s structure (UUID coercion, timestamp parsing, session/history ID re-mapping) but (a) targeting `DATABASE_URL`/`TARGET_DATABASE_URL` (a real Supabase/Render Postgres instance) instead of the hardcoded `LOCAL_DATABASE_URL`, and (b) carrying the full corrected `ai_proposals` field set from Decision 2 instead of the lossy `proposal_text`/`confidence_score` mapping `migrate_local.py` currently does.
2. The migration is run once, manually, via the existing `workflow_dispatch`-only GitHub Actions workflow (`backend/.github/workflows/migrate-database.yml`), against a `staging` target first, then `production`, per that workflow's existing environment input - consistent with `AGENTS.md`'s "never trigger this without confirming the target environment first."
3. After migration, a verification step (row-count comparison between SQLite and Postgres per table, matching the existing script's count-based logging) gates deleting `backend/db/app.db` (Decision 4).

**Why**: Reusing `migrate_local.py`'s already-tested ID/timestamp-normalization logic is lower-risk than writing a migration script from scratch. Fixing the `ai_proposals` mapping is required regardless, since the target schema is changing (Decision 2). Running through the existing CI workflow (rather than ad hoc, by hand) keeps the migration auditable and consistent with how `AGENTS.md` already documents this process should work.

**Alternatives considered**: Write application-level "backfill on read" logic instead of a batch migration - rejected as unnecessary complexity for a bounded, one-time dataset (`backend/db/app.db` is a single file, not a live multi-writer system).

## Risks / Trade-offs

- **[Risk] The corrected `ai_proposals` schema change is destructive if the live Supabase table already has rows in the old shape.** → Mitigation: `tasks.md` includes an explicit "check row count in live `ai_proposals`" verification step before applying the corrective migration; if non-empty, the new migration adds columns alongside the old ones instead of dropping, and a follow-up decides removal.
- **[Risk] `migrate_to_supabase.py` has never existed and has never been run against a real Supabase instance; the CI workflow that references it (`migrate-database.yml`) has therefore never successfully executed.** → Mitigation: dry-run the new script against a disposable local Postgres (following `migrate_local.py`'s existing pattern) before pointing it at `TARGET_DATABASE_URL`; verify with row-count checks and a manual spot-check of a few migrated `AIProposals` rows for round-trip fidelity.
- **[Risk] Removing `USE_POSTGRESQL` and the SQLite path is a breaking change for anyone currently relying on `USE_POSTGRESQL=false` for local development without a Postgres instance.** → Mitigation: `tasks.md` includes updating local-dev docs/README to describe running against a local or hosted Postgres/Supabase instance instead; this is a one-time developer-workflow adjustment, not a runtime risk.
- **[Trade-off] Deleting `backend/db/app.db` and `schema.sql` loses the ability to quickly spin up a zero-dependency SQLite-backed dev environment.** → Accepted per the confirmed product decision; git history retains the files if ever needed again.

## Migration Plan

1. Land the corrected Postgres schema as a new, additive Supabase migration file (Decision 2) - apply it to staging first.
2. Implement/fix the mapping layer in `backend/app/db_helper.py` (Decision 1) and remove `USE_POSTGRESQL` branching in `backend/app/main.py` (Decision 3) - deploy behind the existing single `DATABASE_URL` config, no feature flag needed since staging/production Supabase already exist.
3. Create/fix `backend/db/migrate_to_supabase.py` (Decision 5) and dry-run it locally.
4. Run the migration workflow against staging, verify row counts and spot-check data, then run against production.
5. Once verified, mark `backend/db/schema.sql` as historical, remove the `backend/db/init_db.py` startup path (Decision 4), and update `conf/.env.example` (drop `USE_POSTGRESQL`, `SOURCE_DATABASE_URL`, `TARGET_DATABASE_URL`). Leave `backend/db/app.db` in place as a verified backup; its deletion/archival is deferred to a later cleanup change.

**Rollback strategy**: Because the SQLite path is being removed from the code (not just deprioritized), rollback after step 2 ships means reverting the `db_helper.py`/`main.py` commit (git revert) rather than re-enabling a flag. Because `backend/db/app.db` is deliberately kept in place (Decision 4), the original SQLite data remains available for recovery or re-migration at any point after this change ships, without needing to reach into git history.

## Open Questions

- Should the corrected `ai_proposals` migration ship as a brand-new migration file or edit `001_initial_schema.sql` in place? Decision 2 defaults to a new file for safety; this can be revisited during implementation once it's confirmed whether `001_initial_schema.sql` has actually been applied to the live Supabase project yet (not verifiable from the repo alone).
- Exact target filename/location for the archived `backend/db/app.db`/`schema.sql` (delete vs. move to `backend/db/legacy/`) - left as an implementation-time choice in `tasks.md`, doesn't affect the specs or overall approach.
