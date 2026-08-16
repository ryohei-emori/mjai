# AGENTS.md

Agent-facing environment/operational constraints for MJAI (Japanese text-correction AI app: FastAPI backend + Next.js frontend + Supabase Postgres). See `README.md` for the human-facing setup guide and feature overview — this file only covers what an agent must know before running commands, changing config, or deploying.

## ⚠️ Reality check: docs vs. repo state

`README.md`'s older "Quick Start (Docker & ngrok)" text may still mention `conf/docker-compose.yml`, `conf/ngrok.yml`, `conf/start.sh`, and `conf/update-env.sh` — those paths under `conf/` are **not** present. Local compose lives at the **repo-root** `docker-compose.yml` (backend `:8000`, frontend `:3000`). Ngrok tunnel vars/`NGROK_*` are **not** part of the active env templates (`conf/.env.example`); do not reintroduce them. **Production path: both backend and frontend on Vercel (monorepo deployment), app DB + Auth on Supabase.** AI suggestions use **cloud APIs (Gemini → Groq → Cloudflare); WebLLM only when オフラインモード is ON**. Configure backend `GEMINI_API_KEYS` (or singular `GEMINI_API_KEY`) for the primary Gemini pool — never as `NEXT_PUBLIC_*`.

## Multi-Environment Architecture: Shared DB, Environment-Aware Auth

MJAI uses a **single Supabase project** for both local development and production. This provides:

| Aspect | Implementation |
|--------|---------------|
| **DB共有 (Shared DB)** | Same `DATABASE_URL` for local and production; all app data in one Postgres instance |
| **認証分け (Environment-Aware Auth)** | Same Supabase Auth project, but frontend uses `window.location.origin` to dynamically set OAuth redirect URLs |

### Environment Matrix

| Setting | Local Development | Production (Vercel) |
|---------|-------------------|---------------------|
| Frontend URL | `http://localhost:3000` | `https://mjai-nine.vercel.app` |
| API URL | `http://localhost:8000` | `/api` (same-origin) |
| `DATABASE_URL` | Same Supabase Postgres | Same Supabase Postgres |
| `NEXT_PUBLIC_SUPABASE_URL` | Same | Same |
| `SUPABASE_JWT_SECRET` | Same | Same |
| OAuth `redirectTo` | `http://localhost:3000` (auto via `window.location.origin`) | `https://mjai-nine.vercel.app` (auto) |
| `ALLOWED_USER_EMAIL` | Same | Same |

### What "認証分け" means in this architecture

- **Same user pool**: The allow-listed user can log in from either environment (auth.users is shared)
- **Environment-specific redirects**: OAuth flow redirects to the correct domain based on where sign-in was initiated
- **Same Google OAuth client**: One client ID with multiple authorized origins/redirect URIs

This is the simplest architecture for a single-user app. True auth separation (separate user pools) would require two Supabase projects, breaking DB sharing unless using an external Postgres.

### External configuration required (manual setup)

**Google Cloud Console** (Credentials → OAuth 2.0 Client):
1. Authorized JavaScript origins: `http://localhost:3000`, `https://mjai-nine.vercel.app`
2. Authorized redirect URIs: `https://[supabase-project-ref].supabase.co/auth/v1/callback`

**Supabase Dashboard** (Authentication → URL Configuration):
1. Site URL: `https://mjai-nine.vercel.app` (production)
2. Redirect URLs: `http://localhost:3000/**`, `http://127.0.0.1:3000/**`, `https://mjai-nine.vercel.app/**`

**Supabase Dashboard** (Authentication → Providers → Google):
1. Client ID and Client Secret from the Google OAuth client above

See `backend/supabase/config.toml` for local Supabase CLI config (`site_url`, `additional_redirect_urls`).

## Required environment variables / secrets

Defined in `conf/.env` (git-ignored; copy from `conf/.env.example`, never commit the real file):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase Postgres connection string (format: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`). Supabase is used for both Auth and app data persistence. |
| `USE_POSTGRESQL` | Keep `true` (Postgres/Supabase is the only app DB path; SQLite dual-path removed). |
| `SOURCE_DATABASE_URL` / `TARGET_DATABASE_URL` | Migration-only vars (commented in `.env.example`); safe to omit after one-time data migration |
| `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_URL` | Frontend API base URLs — **build-time** vars (see below). Local docker examples: `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `FRONTEND_URL` | Backend CORS allow-list origin (local docker: `http://localhost:3000`; prod: Vercel URL) |
| `ENVIRONMENT` | `development`/`production` switch, affects CORS logic in `backend/app/main.py` |
| `PYTHONPATH`, `APP_ROOT`, `PROJECT_ROOT` | Path plumbing for local/container runs |
| `SUPABASE_JWT_SECRET` | Backend-only secret used by `backend/app/auth.py` to verify Supabase-issued JWTs (Supabase project settings → API → JWT Secret). Never exposed as `NEXT_PUBLIC_*` |
| `ALLOWED_USER_EMAIL` | Google-auth allow-list checked by `backend/app/auth.py`; case-insensitive, supports comma-separated multiple addresses (also read as `ALLOWED_USER_EMAILS`) |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser-side Supabase client config used by `frontend/src/lib/supabaseClient.ts` for Google sign-in — **build-time** vars, safe to expose |

**AI Provider Keys (backend-only, never `NEXT_PUBLIC_*`):**
| Variable | Purpose |
|---|---|
| `GROQ_API_KEYS` | Optional comma-separated Groq keys for the credential pool (`backend/app/llm/key_pool.py`). When non-empty after parse, overrides `GROQ_API_KEY`. |
| `GROQ_API_KEY` | Singular back-compat. Primary AI provider for fast inference (~1-3s). Used when `GROQ_API_KEYS` is unset/empty. Get from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | Optional. If set, disables per-request model rotation and pins every request to this exact model id (see `ALLOWED_GROQ_MODELS` rotation pool in `backend/app/llm/groq_provider.py`) |
| `CLOUDFLARE_ACCOUNT_IDS` + `CLOUDFLARE_API_TOKENS` | Optional parallel comma-separated lists (same length) for multi-account Cloudflare Workers AI. When either plural var is set, both must match in length or the CF pool is empty. Overrides singular pair when non-empty. |
| `CLOUDFLARE_ACCOUNT_ID` | Singular back-compat. Cloudflare account ID for Workers AI fallback. Get from Cloudflare dashboard |
| `CLOUDFLARE_API_TOKEN` | Singular back-compat. Cloudflare API token with Workers AI access |
| `GEMINI_API_KEYS` | Optional comma-separated Gemini API keys for the primary provider pool. When non-empty after parse, overrides `GEMINI_API_KEY`. Get from [Google AI Studio](https://aistudio.google.com/apikey) |
| `GEMINI_API_KEY` | Singular back-compat. Used when `GEMINI_API_KEYS` is unset/empty |
| `GEMINI_MODEL` | Optional. If set, disables Gemini Flash rotation and pins every request to this exact model id (see `ALLOWED_GEMINI_MODELS` in `backend/app/llm/gemini_provider.py`) |
| `GEMINI_THINKING_LEVEL` | Optional. Overrides the `thinkingConfig.thinkingLevel` sent to Gemini (default `low`). `none` omits `thinkingConfig` entirely, restoring provider-default thinking |

**Key pool behavior:** each outbound Groq/Cloudflare/Gemini call selects a credential via round-robin among non-cooled-down entries; on HTTP 401/403/429 the failing credential is cooled down (~60s) and the next key/pair is tried before the provider fails over. **Groq and Gemini cooldown is model-scoped** (a 429 on one model does not block the same key for a sibling rotation model); Cloudflare cooldown remains credential-wide. Single-key Vercel setups need no change. Plural vars override singular (they are not merged — no double-counting). Duplicate identical keys in a plural list collapse to one entry. Cooldown is process-local (best-effort on Vercel warm instances; not shared across concurrent serverless isolates).

**Quota vs pool:** the pool spreads load and fails over across accounts/keys; it does **not** raise each account’s hard RPD/TPM/quota. Gemini free-tier limits are often **per Google Cloud project** (not per API key), so two keys from the same project may share one quota. “Quota exceeded” with `pool_size≥2` usually means **every loaded credential** hit provider limits (or later failover also failed) — not that the pool skipped a healthy key. `POST /suggestions` 503 JSON includes `groq_pool_size` / `cf_pool_size` / `gemini_pool_size` (counts only, no secrets); logs emit the same. Check Groq/Cloudflare/Gemini dashboards **per key/account/project** when limits trip.

WebLLM (client-side) requires no backend configuration — it runs in the browser using WebGPU.

Optional/legacy: `SUPABASE_SERVICE_ROLE_KEY` may appear in `conf/.env` (commented placeholder in `.env.example`) — not referenced by current backend/frontend code. Google OAuth client secrets belong in the Supabase Auth provider (local `conf/client_secret*.json` is gitignored; never commit).

`backend/.env` and `frontend/.env` both exist as empty (0-byte) files and are git-ignored — they are placeholders, not active config sources.

## Local dev / Docker constraints

- Backend: Python 3.12 (Vercel Python runtime), deps in `backend/requirements.txt` and root `requirements.txt` (FastAPI, uvicorn, asyncpg, pytest, python-dotenv). Runs via `uvicorn app.main:app` locally, listens on `${PORT:-8000}`, has a `/health` endpoint. On Vercel, served as a serverless function at `/api/*`.
- Frontend: Next.js 15 / React 19. No Dockerfile — frontend is deployed via Vercel (see Deployment section).
- **Build-time vs runtime**: all `NEXT_PUBLIC_*` vars are baked into the frontend at `npm run build` time. On Vercel, configure these in Project Settings → Environment Variables. Locally, set them in `conf/.env` before running `npm run build`.
- `frontend/next.config.js` uses Vercel's native Next.js build (no explicit `output` mode). The former `output: 'export'` and `frontend/Dockerfile` have been removed.
- Backend `.env` file discovery order (`backend/app/main.py`): `${APP_ROOT}/../conf/.env`, then `${APP_ROOT}/.env`, then `/conf/.env`. `APP_ROOT` defaults to `/app` (container path).
- **Vercel entrypoint**: `api/index.py` at repo root imports `app` from `backend.app.main` for Vercel's Python runtime detection.

## Database constraints

- **Single Supabase Postgres backend**: All app data (sessions, correction histories, AI proposals) is persisted to Supabase Postgres via `asyncpg`. The SQLite dual-path code has been removed.
- Tables use snake_case columns (`sessions`, `correction_histories`, `ai_proposals`, `app_settings`); `backend/app/db_helper.py` maps to camelCase for API responses.
- **`app_settings`** (`006_app_settings.sql`): global key/value settings shared by every allow-listed user — not per user, not per browser. Only key today is `correction_system_prompt`, the editable rules body of the AI correction prompt. **Absence of a row means "built-in default in effect"**, not a copy of the default text, so improving the default in code still reaches anyone who has not customized it; reset therefore deletes the row rather than writing the default back.
- **LLM provenance columns** (`007_history_llm_provenance.sql`): `correction_histories.llm_provider` (`gemini` / `groq` / `cloudflare` / `webllm`) and `llm_model` (exact model id). Kept separate from the existing `provider` column, which records the transport (`api` / `webllm`) and drives the クラウドAPI / ローカルAI badge. Rows written before the migration read back `NULL`, and the UI shows no model caption for those.
- **Deploy order is not load-bearing for these two migrations.** Because migrations are applied to the shared project by hand, a deploy can land first, so the code probes for both additions instead of assuming them: `db_helper._has_provenance_columns()` checks `information_schema` once per process and drops `llm_provider` / `llm_model` from every history read and write when they are absent (otherwise a missing column would 500 the whole workspace, not just the model caption), and a missing `app_settings` table makes `GET /settings/prompt` serve the built-in default while `PUT` returns a 503 naming `006_app_settings.sql`. **Still apply both migrations** — this is a safety net for the window between deploy and migration, not a reason to skip them: until 007 runs, no provenance is recorded at all.
- **Suggestion persistence**: Successful AI generation writes a `correction_histories` row with `status=pending` plus full `ai_proposals` immediately (not only after 「確定してコピー・保存」). Confirm/save promotes the same history to `status=confirmed` via `PUT /histories/{id}` and updates proposal selection flags. Apply `backend/supabase/migrations/005_pending_suggestion_histories.sql` to the shared Supabase project before relying on this path in production.
- Supabase is used for both **Auth** (Google OAuth, JWT) and **app data persistence** — a unified platform.
- RLS is enabled on all tables with permissive `USING (true)` policies. Tightening to per-user scope is deferred to a future change.
- **Historical files**: `backend/db/app.db` is retained as historical data reference but is no longer used by the application. SQLite scripts and schema have been removed. Local development requires a Postgres connection (Supabase).
- **Free tier note**: Supabase free-tier projects may pause after ~7 days of inactivity; first request after pause incurs a cold-start delay. An automated keep-alive workflow prevents this (see below).

## Supabase Keep-alive

Supabase無料プランはアクティビティがないとプロジェクトが一時停止する。これを防ぐため、GitHub Actionsのcronワークフローが3日ごとに本番APIをpingする。

- **Workflow**: `.github/workflows/supabase-keepalive.yml`
- **Schedule**: `0 0 */3 * *` (3日ごと UTC 00:00)
- **Endpoint**: `GET /api/keepalive` — DBに `SELECT 1` を発行、認証不要
- **Target URL**: GitHub変数 `KEEPALIVE_URL` で設定可能（デフォルト: `https://mjai-nine.vercel.app/api/keepalive`）
- **Manual trigger**: GitHub Actions UIから `workflow_dispatch` で手動実行可能
- **Failure handling**: 1回リトライ後、失敗時はワークフロー失敗（GitHub通知）

カスタムURLを設定する場合: GitHub repo → Settings → Variables → Repository variables → `KEEPALIVE_URL` を追加。

## CI/CD & GitHub Actions

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `.github/workflows/ci.yml` | push to main, PRs to main | Run backend pytest + frontend jest + lint (optional) |
| `.github/workflows/supabase-keepalive.yml` | cron (3日ごと), manual | Supabase無料プラン一時停止防止 |
| `.github/workflows/apply-migrations.yml` | manual only | ⚠️ Supabase CLIで共有Postgresにマイグレーション適用（下記参照） |
| `backend/.github/workflows/migrate-database.yml` | manual only | ⚠️ ライブDBマイグレーション（要確認。`backend/.github/` 配下なのでGitHubからは実行されない） |

### Deployment (Vercel Git Integration)

デプロイはGitHub Actionsではなく、**Vercel Git統合**が処理する:

| ブランチ/イベント | Vercel環境 | URL |
|------------------|------------|-----|
| push to `main` | Production | `https://mjai-nine.vercel.app` |
| PR作成/更新 | Preview | PR固有の一時URL |
| `staging`ブランチ (未使用) | Staging | 将来用に予約 |

### GitHub Environments

GitHub repoには3つのEnvironmentが存在:
- **production**: Vercel Productionデプロイに対応
- **Preview**: Vercel Previewデプロイに対応（PRごと）
- **staging**: 現在未使用、将来のstaging環境用に保持

### GitHub Secrets

**必須（現在使用中）:**
- `DATABASE_URL` — Supabase Postgres接続文字列（`apply-migrations.yml`と`migrate-database.yml`用、Vercel envは別途設定）。環境スコープの場合は`apply-migrations.yml`の`environment` inputで対応する環境を選ぶこと
- `SUPABASE_ACCESS_TOKEN`, `SUPABASE_ORG_ID` — Supabase管理用（将来のインフラ自動化用）

**不要（削除可能）:**
- `RENDER_API_KEY`, `RENDER_OWNER_ID` — Render廃止済み
- `TF_API_TOKEN` — Terraform削除済み（`terraform/`ディレクトリは削除されました）
- Note: `GEMINI_API_KEY(S)` / `GEMINI_MODEL` are **active** as the primary cloud provider (Vercel env / `conf/.env`); do **not** put them in GitHub Secrets unless a workflow reads them.

これらの古いシークレットはGitHub Settings → Secrets and variablesから手動で削除可能。

### CI Workflow詳細

`.github/workflows/ci.yml`は3つのジョブを並列実行:
1. **backend-test**: Python 3.12 + pytest（`backend/tests/`）
2. **frontend-test**: Node 20 + jest（`frontend/`）
3. **lint**: ESLint + ruff（`continue-on-error: true`、警告のみ）

PRがmainにマージされるにはCIテストのパスが必要（GitHub Branch Protection Rulesで設定推奨）。

### apply-migrations.yml（Supabase CLIでのマイグレーション適用）

手動実行のみ。inputs は `environment`（`DATABASE_URL`シークレットのスコープ選択と監査用）、`mode`（`list` / `dry-run` / `push`）、`repair_versions`。**`mode=list`で現状を見てから`push`する**。

- **`db push`をそのまま叩くと001で落ちる。** 001-005はSQL Editorから手で当てられたため`supabase_migrations.schema_migrations`が空になり得る。CLIは履歴に無い版を全部適用しようとするが、`001_initial_schema.sql`は素の`CREATE TABLE`、`002`は素の`ADD COLUMN`で冪等ではないので`relation "sessions" already exists`で失敗する。→ `mode=list`のremote列が空なら`repair_versions="001 002 003 004 005"`を渡す（repairはSQLを再実行せず履歴に記録するだけ）。003以降は`IF NOT EXISTS`ガード付き。
- 接続文字列: poolerの6543（transaction mode）はDDLを流せないため、ワークフローが同ホストの5432（session mode）へ読み替える。アプリ側は6543のまま。
- マイグレーションは`backend/supabase/migrations/`にあるので、CLIには**`--workdir backend`が必須**。リポジトリ直下の`supabase/.temp/linked-project.json`（ref `fqyhrubqkpuyliqojbai`）は`supabase link`の残骸で、`--db-url`経路では参照されない。
- ローカルから同じことをする場合（`conf/.env`に`DATABASE_URL`がある前提）:

```bash
supabase migration list --workdir backend --db-url "$DATABASE_URL"
# ↑のremote列が空のときだけ（既に当たっている版を履歴に記録する。SQLは再実行されない）
supabase migration repair --status applied 001 002 003 004 005 --workdir backend --db-url "$DATABASE_URL"
supabase db push --workdir backend --db-url "$DATABASE_URL"
```

- 検証済み（2026-08）: 上記手順をローカルPostgres 16（001-005のみ手で適用した状態）で実行し、006/007だけが適用されて`app_settings`と`llm_provider`/`llm_model`が作られ、履歴に001-007が記録され、再pushが`Remote database is up to date.`になることを確認した。

### migrate-database.yml

⚠️ **手動実行のみ**。ライブデータ移行を実行するため、以下を確認してから実行:
1. `TARGET_DATABASE_URL`シークレットが正しいSupabaseプロジェクトを指していること
2. バックアップがあること
3. 可能ならstagingで先にテスト

**Render infrastructure is retired**: The Render Web Service `mjai` (srv-d2f031buibrs738hhe40) is suspended/deleted; `RENDER_API_KEY` and `RENDER_OWNER_ID` secrets are no longer required.

## Vercel deployment (frontend + backend)

**Both frontend and backend are deployed via Vercel as a monorepo:**

- **Root directory**: `.` (repo root) — default when linking/deploying from repo root; not required in `vercel.json`
- **Framework / Build / Output**: encoded in repo-root `vercel.json` (`framework`, `buildCommand`, `outputDirectory`) so CLI/git deploys do not need dashboard Build settings
- **Python backend**: `api/index.py` serves FastAPI at `/api/*` as a Vercel serverless function

**CLI vs dashboard**: After `vercel login` + `vercel link`, use `vercel env add` / `vercel env pull` for secrets. Build/Output/framework live in `vercel.json` (git). Dashboard is still useful for Git integration, domains, and one-time project creation if the project does not exist yet.

**Env layout**: `conf/.env` is the local source of truth (docker + secrets). Do not commit it. Optional root `.env` symlink to `conf/.env` for tools that expect WD `.env` (gitignored). Never blindly sync local `ENVIRONMENT` / `NEXT_PUBLIC_API_URL` / `FRONTEND_URL` to Production — set Production overrides via CLI/dashboard.

**Environment variables** (set via `vercel env add … production` or Project Settings → Environment Variables):
- `DATABASE_URL` — Supabase Postgres connection string
- `SUPABASE_JWT_SECRET` — Backend JWT verification secret
- `ALLOWED_USER_EMAIL` — Google-auth allow-list
- `FRONTEND_URL` — Production Vercel URL (for CORS, though same-origin for monorepo)
- `ENVIRONMENT` — `production` or `development`
- `NEXT_PUBLIC_API_URL` — empty or `/api` for same-origin monorepo deployment
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase browser client config
- AI keys — see **AI provider keys on Vercel** below (`GROQ_API_KEYS`, CF plural pairs, `GEMINI_API_KEYS`, singular back-compat)

**Render and Terraform infrastructure has been removed**: The Render Web Service and `terraform/` directory have been deleted. All deployment is now via Vercel git integration.

### AI provider keys on Vercel (ops)

**Local vs Production:** `conf/.env` is **local only** (gitignored). Production AI credentials live in **Vercel Environment Variables**. They do **not** auto-sync from `conf/.env` or from GitHub Secrets. Changing local `.env` never updates Production.

**Key pool variable names** (`backend/app/llm/key_pool.py`; plural wins when non-empty after parse):

| Variable | Role |
|---|---|
| `GROQ_API_KEYS` | Preferred. Comma-separated Groq keys |
| `GROQ_API_KEY` | Singular back-compat (used when plural unset/empty) |
| `CLOUDFLARE_ACCOUNT_IDS` + `CLOUDFLARE_API_TOKENS` | Preferred. Same-length comma-separated lists, paired by index |
| `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | Singular back-compat |
| `GEMINI_API_KEYS` | Preferred. Comma-separated Gemini API keys (primary failover) |
| `GEMINI_API_KEY` | Singular back-compat (used when plural unset/empty) |
| `GEMINI_MODEL` | Optional pin (disables Flash rotation) |
| `GEMINI_THINKING_LEVEL` | Optional thinking-level override (`low` default; `none` = provider default) |

**How to set (CLI or Dashboard):**

```bash
# From repo root (after vercel login + vercel link). Values via stdin — never paste secrets into shell history casually.
printf '%s' "$GROQ_API_KEYS" | vercel env add GROQ_API_KEYS production --sensitive -y
printf '%s' "$CLOUDFLARE_ACCOUNT_IDS" | vercel env add CLOUDFLARE_ACCOUNT_IDS production --sensitive -y
printf '%s' "$CLOUDFLARE_API_TOKENS" | vercel env add CLOUDFLARE_API_TOKENS production --sensitive -y
printf '%s' "$GEMINI_API_KEYS" | vercel env add GEMINI_API_KEYS production --sensitive -y
# Mirror to preview when AI keys are already used on Preview deployments:
printf '%s' "$GROQ_API_KEYS" | vercel env add GROQ_API_KEYS preview --sensitive -y
printf '%s' "$GEMINI_API_KEYS" | vercel env add GEMINI_API_KEYS preview --sensitive -y
# …
```

- Or: Vercel Dashboard → Project Settings → Environment Variables.
- Keep/update singular vars if they already exist (back-compat / single-key fallback).
- **Redeploy required** after env changes for serverless functions to pick up new values (`vercel --prod` or trigger a Production redeploy from the dashboard / empty commit on `main`). Runtime env on existing deployments is snapshotted at build/deploy time.
- **Do not** put Groq/Cloudflare keys in GitHub Secrets unless a workflow actually reads them. `/api/suggestions` runs on Vercel, not GitHub Actions — GH Secrets are unused for AI inference today.

## Documentation habits

- **`docs/SYSTEM-DESIGN.md`** is the Google-style **engineering** design document (as-built system: goals, components, APIs, data model, trade-offs). Update it when architecture changes, alongside this file.
- **`docs/UI-DESIGN.md`** is the visual-identity / design-token document (colors, typography, spacing, component library config) extracted from the frontend codebase. Update it when frontend design tokens change.
- **When creating or updating `README.md`, read this file (`AGENTS.md`) first** and keep README consistent with operational reality here — or explicitly note intentional portfolio/product-framing differences (e.g. WebLLM as architecture direction while Gemini still runs in code). Do not invent runnable setup paths or claim features are live when they are planning-only.

## Never do

- Never commit `conf/.env`, `backend/.env`, or `frontend/.env` — all are git-ignored; only `conf/.env.example` carries placeholder values.
- Never assume changing a `NEXT_PUBLIC_*` var takes effect without rebuilding the frontend (`docker-compose build frontend` / `npm run build`).
- Never treat the README's docker-compose Quick Start as verified-working without first confirming the referenced files exist.
- Never make an infrastructure or architecture change (new deployment target, database/persistence backend swap, new or removed external service dependency, etc.) without reviewing and updating this file **and** `docs/SYSTEM-DESIGN.md` to match — that's exactly how README's old Quick Start section, documented in the Reality check above, went stale in the first place.
## AI Suggestion Generation

AI correction suggestions use a **hybrid architecture**: cloud APIs by default, with client-side WebLLM only when the user explicitly enables オフラインモード (no automatic client fallback).

### Architecture Overview

```
User Request → POST /api/suggestions (authenticated)
 ↓
 Gemini API (primary, free-tier Flash pool, ~7-16s measured w/ thinkingLevel=low; 22s HTTP timeout)
 ↓ 429/5xx/timeout / unusable content
 Groq API (secondary, ~1-3s; 25s timeout)
 ↓ fail / unusable content
 Cloudflare Workers AI (tertiary; 20s timeout)
 ↓ all fail / wall-clock budget (~55s) exhausted
 Frontend shows error (toast + failed job) — does NOT auto-start WebLLM
```

| Path | Provider | Latency | When Used |
|------|----------|---------|-----------|
| **Default** | Gemini (`gemini-3.7-flash` / `gemini-3.6-flash` rotation; pin via `GEMINI_MODEL`) | ~7-16s | Gemini keys configured and available |
| **Secondary** | Groq, model rotation pool (see below), overridable/pinnable via `GROQ_MODEL` | ~1-3s | Gemini rate-limited/error/timeout or unusable content |
| **Tertiary** | Cloudflare Workers AI | ~2-5s | Gemini and Groq failed or returned unusable content |
| **Offline** | WebLLM (Mistral 7B) | ~10-30s | **Only** when user enables オフラインモード |

**Vercel timeout ops:** `vercel.json` sets `api/index.py` `maxDuration` to **60s**. Provider HTTP timeouts (Gemini ~22s, Groq 25s, CF 20s) plus `suggestions.py` wall-clock budget (`SUGGESTIONS_WALL_CLOCK_S` ≈ 55s) MUST stay under that limit so a slow/failing failover chain returns app **503** with `gemini_pool_size` / `groq_pool_size` / `cf_pool_size` instead of opaque platform **504 FUNCTION_INVOCATION_TIMEOUT**. Empty Gemini pool skips Gemini immediately (no hang). After changing `GEMINI_API_KEYS` on Vercel, **redeploy** so serverless snapshots pick up the env.

**Gemini thinking level is the latency/coverage lever (`fix-gemini-thinking-coverage-budget`, 2026-08):** Gemini 3.x Flash thinks by default, and live probes on the 5-paragraph epic fixture measured ~2.9k–3.8k `thoughtsTokenCount` per call, ~20.7–21.0s latency (**2 of 4 calls hit the 22s timeout and silently demoted to Groq**), and only 7 suggestions. `gemini_provider.py` therefore sends `generationConfig.thinkingConfig.thinkingLevel = "low"` (override `GEMINI_THINKING_LEVEL`; `none` = provider default), which measured 7.2–13.8s with 0 timeouts and 10–20 suggestions on the same prompt. Use `thinkingLevel`, **not** `thinkingBudget` — `gemini-3.6-flash` rejects `thinkingBudget` with HTTP 400 while `gemini-3.7-flash` accepts it, and the pool rotates randomly. **Do not raise `GEMINI_TIMEOUT` as an alternative fix**: 22+25+20 = 67s of provider timeouts already over-commit the 55s wall clock, so a larger Gemini share means a slow primary eats the budget and returns 503 without Groq/CF being tried. Reproduce with `backend/scripts/live_gemini_coverage.py`.

**Groq model rotation (added 2026-08 ahead of `llama-3.3-70b-versatile`'s 2026-08-16 deprecation):** rather than pinning to a single hardcoded model, `backend/app/llm/groq_provider.py` selects a model per request from a curated allow-list (`ALLOWED_GROQ_MODELS`):

| Model ID | Role |
|---|---|
| `openai/gpt-oss-120b` | Rotation pool — Production tier, quality-focused |
| `openai/gpt-oss-20b` | Rotation pool — Production tier, speed/cost-focused |

- **Selection**: `random.choice`-style (`random.sample`) per request, not a stateful round-robin — Vercel serverless functions are stateless per-invocation, so an in-memory counter would not reliably rotate in production.
- **In-provider retry**: on a retriable Groq failure (429/5xx/timeout), the provider retries once against a second, different model from the pool (`call_groq_with_rotation()`) before the `suggestions.py` failover chain falls over to Cloudflare — bounding the Groq phase to at most 2 attempts to keep total request latency predictable.
- **`GROQ_MODEL` override**: if set to a non-empty value, rotation is fully disabled and every request pins to that exact model id, with no in-provider retry — unchanged from prior behavior, useful for debugging or pinning to a specific model.
- **JSON mode**: Groq requests send `response_format: {"type": "json_object"}` plus `max_tokens: 4096` so long epic corpora do not truncate mid-JSON or drift into prose.
- **Content salvage**: if Gemini returns HTTP-OK but unparseable or non-Chinese `reason`/`overallComment`, `suggestions.py` still tries Groq, then Cloudflare, in the same pass before the outer language/parse retry loop.

**Gemini model rotation (primary, free-tier Flash):** `backend/app/llm/gemini_provider.py` uses `ALLOWED_GEMINI_MODELS` (`gemini-3.7-flash`, `gemini-3.6-flash`) selected via `random.sample` with one in-provider retry on retriable failure — same pattern as Groq. Live probes (2026-08) confirmed these IDs on free-tier keys; `gemini-2.5-flash`/`gemini-2.5-pro` 404'd on the same keys. Prefer stable IDs over floating `gemini-flash-latest` (still pin-able via `GEMINI_MODEL`). Calls use Generative Language `generateContent` (v1beta) with `responseMimeType: application/json`, `maxOutputTokens: 16384`, and `thinkingConfig.thinkingLevel: low`. HTTP timeout is ~22s so primary + failover fit Vercel `maxDuration` (60s) with a soft wall-clock abort (~55s). Both pooled models advertise `outputTokenLimit` 65536, so the 16384 ceiling is headroom (dense multi-paragraph critiques consume ~1.4k–2.1k completion tokens) and cannot trip the "above model limit ⇒ HTTP 400" failure mode.
- **Excluded from the pool** (and why): `qwen/qwen3.6-27b` (live Chinese-enforcement smoke on CN-source/JP-target corpora frequently returned Japanese explanations or empty bodies despite `reasoning_effort: "none"`; still pin-able via `GROQ_MODEL`), `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` (Groq shutdown date 2026-08-16), `qwen/qwen3-32b` (already deprecated/404s), `openai/gpt-oss-safeguard-20b` (safety/policy-classification tuned), `groq/compound`/`compound-mini` (agentic/tool-use, low RPD), `meta-llama/llama-prompt-guard-2-*` (classifier models), `allam-2-7b` (Arabic-focused, not evaluated for Japanese quality).
- **Maintenance note**: `ALLOWED_GROQ_MODELS` is a static, manually-reviewed constant — there is no runtime catalog-refresh mechanism. If Groq announces further deprecations, update this list (and this table) as a small follow-up change; do not wait for production errors to surface it.

### Backend Providers (`backend/app/llm/`)

| Module | Purpose |
|--------|---------|
| `prompts.py` | Shared prompt (ported from frontend WebLLM prompts), split into the editable `SYSTEM_PROMPT_BODY` and the code-owned `OUTPUT_CONTRACT` |
| `parser.py` | Hardened JSON parser (trailing commas, truncated JSON, markdown fences) + `has_non_japanese_recommendation` guard |
| `provider_output.py` | `ProviderOutput(text, model)` — how rotation wrappers report which model actually answered |
| `key_pool.py` | Multi-credential load/select/cooldown for Groq + Cloudflare + Gemini (env-driven) |
| `groq_provider.py` | Groq API client, 25s timeout, JSON-object mode, model rotation pool (`ALLOWED_GROQ_MODELS`) + key-pool retry + in-provider model retry |
| `cloudflare_provider.py` | Cloudflare Workers AI client (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`, 20s timeout) with response-shape normalize + key-pool retry |
| `gemini_provider.py` | Gemini `generateContent` (v1beta), ~22s timeout, JSON mime type, `maxOutputTokens` 16384, `thinkingLevel` low, Flash rotation pool (`ALLOWED_GEMINI_MODELS`) + key-pool retry + in-provider model retry; logs `finishReason` + `usageMetadata` token counts |
| `suggestions.py` | Failover chain logic (Gemini → Groq → Cloudflare) + wall-clock budget before platform 504 |

### Environment Variables (Vercel Production)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` or `GEMINI_API_KEYS` | Recommended | Primary provider (singular or comma-separated pool). Get from [Google AI Studio](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | Optional | Pins Gemini to a single model id, disabling rotation across `ALLOWED_GEMINI_MODELS` |
| `GEMINI_THINKING_LEVEL` | Optional | Overrides `thinkingConfig.thinkingLevel` (default `low`); `none` omits `thinkingConfig` and restores provider-default thinking |
| `GROQ_API_KEY` or `GROQ_API_KEYS` | Recommended | Secondary provider (singular or comma-separated pool). Get from [console.groq.com](https://console.groq.com) → API Keys |
| `GROQ_MODEL` | Optional | Pins Groq to a single model id, disabling rotation across `ALLOWED_GROQ_MODELS`, without a code change |
| `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` or parallel `CLOUDFLARE_ACCOUNT_IDS` + `CLOUDFLARE_API_TOKENS` | Optional | Tertiary provider (singular pair or equal-length parallel lists). Account ID from Cloudflare dashboard → Overview |

If none of Groq / Cloudflare / Gemini is configured, `/api/suggestions` returns 503. Frontend does **not** auto-start WebLLM — enable オフラインモード explicitly.

### Frontend UX

- **Default behavior**: Calls `/api/suggestions` first for fast response
- **No auto-fallback**: If the cloud API fails (429/quota, 503, network, etc.), the job fails and the UI shows the error — WebLLM is **not** started unless オフラインモード is already ON
- **オフラインモード toggle**: Explicit WebLLM-only mode (checkbox near generate button); required to use local AI
- **Visual indicator**: Badge shows "クラウドAPI" or "ローカルAI" after generation
- **DB sync on generation**: When a job completes with suggestions, the UI persists `pending` history + proposals to shared Postgres so another browser/environment on the same DB can see them via session load / ~10s poll (Job Queue). Confirm promotes to `confirmed` History without a second history insert when `historyId` is already known.

### WebLLM (Offline Fallback)

WebLLM remains fully functional for offline use and future evolution:

- **Model ID:** `Mistral-7B-Instruct-v0.3-q4f16_1-MLC`
- **Approximate download size:** ~4-5 GB (cached in browser Cache API)
- **VRAM required:** ~4.5 GB
- **WebGPU required:** Modern Chrome/Edge/Safari
- **Implementation:** `frontend/src/lib/webllm/`

WebLLM is retained for:
1. Offline usage when cloud APIs are unavailable
2. Users who prefer local inference (privacy, no API dependencies)
3. Future client-side AI evolution

### Editable shared prompt (`editable-prompt-model-log-and-critique-fix`, 2026-08)

The correction prompt's **rules body** is operator-editable from the top-bar gear (`frontend/src/components/ui/prompt-settings-dialog.tsx`) and stored as one global `app_settings.correction_system_prompt` row — shared by every allow-listed user, persisted across logins, no per-browser copy.

| Endpoint (authenticated `router`, so also served at `/api/...`) | Behavior |
|---|---|
| `GET /settings/prompt` | `{ systemPrompt, defaultSystemPrompt, isCustomized, updatedAt, updatedBy }`; attribution is null when the default is in effect |
| `PUT /settings/prompt` | Body `{ systemPrompt }`. Trim-empty → 400; >20,000 chars → 400 stating the limit. `updated_by` comes from the JWT email |
| `DELETE /settings/prompt` | Reset: deletes the row (idempotent), so the built-in default applies again |

- **The output contract is code-owned and not editable.** `prompts.py` composes `(stored body or SYSTEM_PROMPT_BODY) [+ EXEMPLAR_REFERENCE_RULES when an exemplar was pasted] + OUTPUT_CONTRACT`, and `OUTPUT_CONTRACT` (JSON-only instruction + `格式：` schema line) is always appended last. A bad edit can lower critique quality; it cannot break parsing. With no override and no exemplar, the composition is byte-identical to `SYSTEM_PROMPT`.
- **Read path**: `backend/app/prompt_settings.resolve_system_prompt_override()` is called by the `/suggestions` handler *after* the wall-clock deadline is set, with a short timeout, no cache, and never raises — any failure logs a warning and uses the built-in default. A settings outage degrades quality at worst, never availability.
- **Not versioned**: history rows do not record the prompt in force at generation time. Only the model is attributable (see below).
- **Offline WebLLM keeps its own built-in prompt** (`frontend/src/lib/webllm/prompts/`), which the dialog states explicitly. Mirror new rules there in condensed form; do not port the full backend rules into the 7B instruction budget.
- Editing the default in code still reaches everyone who has not customized it, because customization is a row's presence rather than a copy of the default.

### Prompts (Shared)

Same prompt is used across all providers (backend and WebLLM):

```
frontend/src/lib/webllm/prompts/
├── system.ts     # System prompt (Chinese, ultra-concise for small models)
├── fewShot.ts    # Minimal few-shot example
└── templates.ts  # Section headers

backend/app/llm/prompts.py  # Python port of above
```

### Request Schema

`POST /api/suggestions` body:

```json
{
  "originalText": "原文",
  "targetText": "添削対象",
  "exemplarTranslation": "模範回答訳文（任意・省略可）"
}
```

`exemplarTranslation` (added 2026-08, `add-optional-exemplar-translation-input` change) is optional: a known-good translation of `originalText` that the user may paste into the EXEMPLAR TEXT (模範回答訳文) card. **Omitted / empty / whitespace-only produces byte-identical prompts to before the field existed** — the exemplar block and its rules section are both withheld, never sent as an empty placeholder. When non-empty it is used as *reference calibration only*: `EXEMPLAR_REFERENCE_RULES` is appended to the system prompt to forbid citing the exemplar as a correction reason and to forbid treating "differs from the exemplar" as a defect. Same optional field threads into the WebLLM offline prompt (`PromptInput.exemplarTranslation`). Not persisted server-side (no DB column, not sent to `POST /histories` or `POST /proposals`); the frontend keeps it in the per-session localStorage draft.

A live A/B probe (`backend/scripts/live_exemplar_compare.py`) is why the guard rules exist rather than pasting the exemplar bare: on the multi-paragraph epic fixture with `gemini-3.7-flash`, baseline returned 13/13 suggestions across two runs, guarded returned 11/12 while additionally catching modality faults baseline missed, and an unguarded exemplar dropped to 9 — a coverage regression. Prompt tokens rose ~21% (3089 → 3723) for a three-paragraph exemplar with latency unchanged (~10-13s), comfortably inside the Gemini 22s timeout and 55s wall-clock budget.

### Response Schema

All providers return the same JSON structure:

```json
{
  "suggestions": [
    {"id": "1", "original": "指摘箇所", "reason": "修正理由", "sourceExcerpt": "原文中の対応箇所（該当する場合のみ、省略/空文字可）"}
  ],
  "overallComment": "全体講評",
  "llmProvider": "gemini",
  "llmModel": "gemini-3.7-flash"
}
```

`llmProvider` / `llmModel` (added 2026-08, `editable-prompt-model-log-and-critique-fix`) report which inference actually answered — `gemini` / `groq` / `cloudflare` plus the exact model id — because Gemini and Groq pick a model per request and may retry against a sibling. `call_gemini_with_rotation()` / `call_groq_with_rotation()` return `ProviderOutput(text, model)` for this; Cloudflare's plain string is paired with `CF_MODEL`. Reported on the salvage and retry paths too, logged on success, and the 503 error shape is unchanged (pool sizes only). The frontend passes both onto the pending-history create so a round stays attributable, and renders `{model} used` as a caption in the AI Suggestions header (omitted when unknown, e.g. rounds saved before the columns existed).

`sourceExcerpt` (added 2026-08, `highlight-suggestion-text-spans` change) is optional: an excerpt from SOURCE TEXT (原文) corresponding to the flagged TARGET TEXT snippet in `original`, used by the frontend to highlight the matching span in the SOURCE TEXT textarea. Omitted/empty when the model finds no clear correspondence — never fabricated. Not persisted through `POST /proposals`.

`reason` / `overallComment` are Simplified Chinese. Each `reason` should convey problem → recommended JP form (when clear) → accessible why in **natural prose** — do not force spoken machine labels `现状：` / `推荐：` / `現状：` / `推奨：`. Multi-paragraph TARGET should get systematic real-issue coverage (target ≥~5 when that many exist; no padding). Gemini `maxOutputTokens` is 16384 so dense multi-suggestion JSON does not truncate mid-array — but the token ceiling was never the coverage constraint (measured `finishReason` is `STOP`, not `MAX_TOKENS`, at ~1.4k–2.1k completion tokens); the thinking level is. See **Gemini thinking level is the latency/coverage lever** above.

**Prompt maintenance rule (`refine-prompt-instruction-coherence`, 2026-08):** when editing prompt rules, edit the few-shot exemplar to match. Models imitate the example's item count and issue categories more reliably than they obey a numeric target, so the example MUST demonstrate the stated density (≥5 in the backend prompt), cover the categories the rules call highest priority (meaning shift / modality, systematic grammar — not lexical and register items only), keep every item distinct (a restated correction is padding), and include one item that omits `sourceExcerpt` so an always-filled excerpt does not bias the model into inventing one. Exemplar `reason` text is learner-facing critique only — anti-pattern directives belong in the rule sections. Avoid hedges whose side effect is fewer items (a standalone "quality over count" line, or a global brevity cue instead of a per-item length bound). There is no suggestion-count cap in prompts, providers, or the parser; keep it that way.

**Target-language critique rules (`editable-prompt-model-log-and-critique-fix`, 2026-08).** A reported live session returned Chinese words *as the correction* for a Japanese TARGET (改为"对比睡眠数据" / 改为"理论上"), critiqued the Chinese SOURCE (「原文の"完成"を"实现"に」), offered interchangeable synonyms as faults (比較⇄対比, 研究者⇄学者), and proposed a form that does not hold in Japanese (「睡眠が需要だ」) — while missing real faults such as the numeral carryover 「９点５時間」. The rules now state, and the exemplar demonstrates:

- **Recommended forms MUST be written in Japanese.** Chinese is for explanation only, never the corrected form. A learner cannot paste a Chinese word into a Japanese sentence.
- **Only 添削対象 may be corrected.** The 原文 is the reference for judging meaning, never the object of correction — no item may propose rewriting the source into different Chinese.
- **Interchangeable near-synonyms are not faults.** A wording item must name a concrete defect (meaning shift, register, collocation, domain term), not a preference.
- **Any proposed form must be substituted back into the sentence and checked** for grammar and collocation before it is offered.
- **Explain by meaning transfer**: what a Japanese reader would misunderstand or lose, not which word maps to which.

Mechanical backstop: `parser.has_non_japanese_recommendation()` flags a `reason` only when a recommendation verb is followed by a quoted span that has **no kana** *and* contains a Simplified-only character, so kanji-only Japanese citations (「叙事詩」「学者」) do not trip it. Wired into `_content_usable()` with its own retry nudge, sharing `MAX_PARSE_RETRY_ATTEMPTS` so the attempt ceiling is unchanged. It is script-level only: a script-legal but semantically wrong recommendation (需要 for 必要) is out of its reach by design and is handled by the rules plus the live probe. Reproduce/measure with `backend/scripts/live_critique_quality.py` (fixture: `backend/tests/fixtures/primate_sleep_source_target.py`), which scores Chinese recommended forms, items whose excerpt is not a TARGET span, synonym-only items, and whether 「９点５時間」 is caught. Mirror these rules into the WebLLM prompt in condensed form.

### How to Get API Keys

**Gemini (primary, free tier available):**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Set as `GEMINI_API_KEYS` (or `GEMINI_API_KEY`) in Vercel

**Groq (secondary, free tier available):**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in
3. Navigate to API Keys → Create API Key
4. Copy key and set as `GROQ_API_KEY` in Vercel

**Cloudflare Workers AI (tertiary fallback):**
1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Copy Account ID from Overview page → set as `CLOUDFLARE_ACCOUNT_ID`
3. Go to My Profile → API Tokens → Create Token
4. Use "Workers AI" template or custom with Workers AI Read permission
5. Copy token and set as `CLOUDFLARE_API_TOKEN` in Vercel
