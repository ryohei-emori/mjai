# AGENTS.md

Agent-facing environment/operational constraints for MJAI (Japanese text-correction AI app: FastAPI backend + Next.js frontend + Supabase Postgres). See `README.md` for the human-facing setup guide and feature overview — this file only covers what an agent must know before running commands, changing config, or deploying.

## ⚠️ Reality check: docs vs. repo state

`README.md`'s older "Quick Start (Docker & ngrok)" text may still mention `conf/docker-compose.yml`, `conf/ngrok.yml`, `conf/start.sh`, and `conf/update-env.sh` — those paths under `conf/` are **not** present. Local compose lives at the **repo-root** `docker-compose.yml` (backend `:8000`, frontend `:3000`). There is still no ngrok tunnel-provisioning tooling in-repo; `*_NGROK_URL` vars remain optional CORS allow-list entries. **Production path: both backend and frontend on Vercel (monorepo deployment), app DB + Auth on Supabase.** AI suggestions are client-side WebLLM — do **not** configure `GEMINI_*`.

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
| `NGROK_AUTHTOKEN` | Optional ngrok tunnel auth (see reality-check note above) |
| `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_BACKEND_NGROK_URL`, `NEXT_PUBLIC_FRONTEND_NGROK_URL` | Frontend API base URLs — **build-time** vars (see below). Local docker examples: `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `BACKEND_NGROK_URL`, `FRONTEND_NGROK_URL` | Optional; read by backend for CORS allow-list |
| `FRONTEND_URL` | Backend CORS allow-list origin (local docker: `http://localhost:3000`; prod: Vercel URL) |
| `ENVIRONMENT` | `development`/`production` switch, affects CORS logic in `backend/app/main.py` |
| `PYTHONPATH`, `APP_ROOT`, `PROJECT_ROOT` | Path plumbing for local/container runs |
| `SUPABASE_JWT_SECRET` | Backend-only secret used by `backend/app/auth.py` to verify Supabase-issued JWTs (Supabase project settings → API → JWT Secret). Never exposed as `NEXT_PUBLIC_*` |
| `ALLOWED_USER_EMAIL` | Google-auth allow-list checked by `backend/app/auth.py`; case-insensitive, supports comma-separated multiple addresses (also read as `ALLOWED_USER_EMAILS`) |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser-side Supabase client config used by `frontend/src/lib/supabaseClient.ts` for Google sign-in — **build-time** vars, safe to expose |

Optional/legacy: `SUPABASE_SERVICE_ROLE_KEY` may appear in `conf/.env` (commented placeholder in `.env.example`) — not referenced by current backend/frontend code. Google OAuth client secrets belong in the Supabase Auth provider (local `conf/client_secret*.json` is gitignored; never commit). `GEMINI_API_KEY` / `GEMINI_MODEL` are obsolete and must not be set.

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
- Tables use snake_case columns (`sessions`, `correction_histories`, `ai_proposals`); `backend/app/db_helper.py` maps to camelCase for API responses.
- Supabase is used for both **Auth** (Google OAuth, JWT) and **app data persistence** — a unified platform.
- RLS is enabled on all tables with permissive `USING (true)` policies. Tightening to per-user scope is deferred to a future change.
- **Historical files**: `backend/db/app.db` and `backend/db/schema.sql` are retained for reference but are no longer used by the application. Local development requires a Postgres connection (local Docker or Supabase).
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
| `backend/.github/workflows/migrate-database.yml` | manual only | ⚠️ ライブDBマイグレーション（要確認） |

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
- `DATABASE_URL` — Supabase Postgres接続文字列（`migrate-database.yml`用、Vercel envは別途設定）
- `SUPABASE_ACCESS_TOKEN`, `SUPABASE_ORG_ID` — Supabase管理用（将来のインフラ自動化用）

**不要（削除可能）:**
- `RENDER_API_KEY`, `RENDER_OWNER_ID` — Render廃止済み
- `GEMINI_API_KEY`, `GEMINI_MODEL` — AI生成はクライアントサイドWebLLMに移行済み
- `TF_API_TOKEN` — Terraform使用停止（terraform/は参照用に保持）

これらの古いシークレットはGitHub Settings → Secrets and variablesから手動で削除可能。

### CI Workflow詳細

`.github/workflows/ci.yml`は3つのジョブを並列実行:
1. **backend-test**: Python 3.12 + pytest（`backend/tests/`）
2. **frontend-test**: Node 20 + jest（`frontend/`）
3. **lint**: ESLint + ruff（`continue-on-error: true`、警告のみ）

PRがmainにマージされるにはCIテストのパスが必要（GitHub Branch Protection Rulesで設定推奨）。

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

**Render infrastructure is retired**: The Render Web Service `mjai` and `render_static_site.frontend` resource are no longer used. The `terraform/` directory may contain obsolete Render provider configuration.

Running any `terraform` command against this directory affects **real cloud resources**. `terraform.tfstate`/`terraform.tfvars` are git-ignored; `terraform/tfplan` is currently committed to git — be aware a saved plan file may be present in history.

## Documentation habits

- **`docs/SYSTEM-DESIGN.md`** is the Google-style **engineering** design document (as-built system: goals, components, APIs, data model, trade-offs). Update it when architecture changes, alongside this file.
- **`docs/UI-DESIGN.md`** is the visual-identity / design-token document (colors, typography, spacing, component library config) extracted from the frontend codebase. Update it when frontend design tokens change.
- **When creating or updating `README.md`, read this file (`AGENTS.md`) first** and keep README consistent with operational reality here — or explicitly note intentional portfolio/product-framing differences (e.g. WebLLM as architecture direction while Gemini still runs in code). Do not invent runnable setup paths or claim features are live when they are planning-only.

## Never do

- Never commit `conf/.env`, `backend/.env`, `frontend/.env`, or `terraform/terraform.tfvars` — all are git-ignored; only `conf/.env.example` and `terraform/terraform.tfvars.example` should carry (placeholder) values.
- Never assume changing a `NEXT_PUBLIC_*` var takes effect without rebuilding the frontend (`docker-compose build frontend` / `npm run build`).
- Never run `terraform apply`/`destroy` casually — both act on live external services/data.
- Never treat the README's docker-compose/ngrok Quick Start as verified-working without first confirming the referenced files exist.
- Never make an infrastructure or architecture change (new deployment target, database/persistence backend swap, new or removed external service dependency, etc.) without reviewing and updating this file **and** `docs/SYSTEM-DESIGN.md` to match — that's exactly how README's old Quick Start section, documented in the Reality check above, went stale in the first place.
## AI Suggestion Generation

AI correction suggestions are now generated **entirely client-side** using WebLLM (`@mlc-ai/web-llm`). The frontend loads and runs a quantized LLM in the user's browser via WebGPU. Key facts:

### Model Details
- **Model ID:** `SmolLM2-1.7B-Instruct-q4f16_1-MLC`
- **Approximate download size:** ~0.9 GB (quantized weights, tokenizer, model config)
- **VRAM required:** ~1.8 GB
- **Context window:** 8192 tokens (8K)
- **Quantization:** 4-bit (q4f16_1) for reduced memory footprint
- **Implementation:** See `frontend/src/lib/webllm/` for model loading, prompt construction, inference, and parsing logic

### Inference Parameters (SmolLM2-optimized)
- **max_tokens:** 512 (sufficient for 5 corrections + overall comment in JSON)
- **temperature:** 0.2 (low for consistent JSON structure output)
- **Typical prompt size:** ~500 tokens (system + few-shot + user input)
- **Inference timeout:** 2 minutes (should complete in <30s with optimized prompts)

These parameters were tuned to prevent unbounded generation (80s+ timeouts observed with max_tokens=2048, temperature=0.7).

#### Model Selection History
- **2026-08-11:** Switched from Phi-3.5-mini (~3.7GB) to SmolLM2-1.7B (~0.9GB) for faster inference
- **2026-08-11:** Optimized prompts and inference params for SmolLM2 (max_tokens 2048→512, temperature 0.7→0.2)
- **Liquid AI LFM2.5 (blocked):** User requested LFM2.5 ("LFG2.5") but it's not available in WebLLM's prebuilt catalog. LFM2.5 models exist only in native/GGUF/MLX/ONNX formats, not MLC format. Custom compilation would be required.

### Runtime Requirements
- **WebGPU required:** Users need a WebGPU-capable browser (modern Chrome/Edge/Safari). Unsupported browsers see a graceful fallback message but can still add manual custom corrections
- **No server-side AI:** The backend no longer has a `POST /suggestions` endpoint or any Gemini-related code. `GEMINI_API_KEY`/`GEMINI_MODEL` env vars are not needed

### Caching Behavior
- **Cache mechanism:** `@mlc-ai/web-llm` uses the browser's **Cache API** (via MLC's tvmjs runtime) to store model weights
- **Cache location:** Browser's Cache Storage (visible in DevTools → Application → Cache Storage)
- **Persistence:** Model cache persists across:
  - Page reloads
  - Browser tab closes/reopens
  - Browser session restarts
  - **User logout** (MJAI logout clears only Supabase auth state, not model cache)
- **First visit:** Downloads full ~0.9GB model with progress indicator
- **Subsequent visits:** Loads from cache (fast, no network download)
- **Cache eviction:** Browser may evict cache under storage pressure (standard browser behavior, no MJAI control)

### Logout Behavior
- Logout clears Supabase auth localStorage keys (`sb-*`) only
- Logout does **NOT** clear Cache API or IndexedDB entries used by WebLLM
- After logout and re-login, model loads from cache without re-downloading

### Diagnostics
- UI shows current phase (Japanese labels), elapsed time, and download progress during AI inference
- Console logs prefixed `[webllm]` with phase transitions and timing for debugging
- Access `window.__webllmDiagnostics.getState()` or `.getLastRunSummary()` in DevTools
- Timeout errors indicate which phase timed out (e.g., "モデルダウンロード中" vs "AI推論中")

### Prompt Management

AI correction prompts are stored in `frontend/src/lib/webllm/prompts/` for easy management and optimization:

```
frontend/src/lib/webllm/prompts/
├── index.ts      # Re-exports all prompts (import from here)
├── system.ts     # System prompt (core AI instructions, Chinese)
├── fewShot.ts    # Minimal few-shot example showing JSON structure
└── templates.ts  # Section headers used in prompt construction
```

**Editing prompts:**
- Edit the `.ts` files directly — they export string constants
- `system.ts`: Modify AI behavior, tone, output format requirements
- `fewShot.ts`: Change the example to guide AI output structure
- `templates.ts`: Adjust section headers (e.g., for localization)

**SmolLM2 prompt optimization guidelines:**
- Keep prompts **concise** — small models work better with shorter, direct instructions
- Explicitly state **JSON-only output** requirement (禁止任何其他文字)
- Use **minimal few-shot examples** — show structure, not lengthy sample texts
- System prompt is in **Chinese** for consistency with output language requirement
- Total prompt tokens should stay under ~500 to leave room for user input within 8K context

**No backend deploy needed:** Prompt changes only require a frontend rebuild (`npm run build` or Vercel auto-deploy on push). The backend has no AI-related code.
