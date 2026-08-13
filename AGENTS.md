# AGENTS.md

Agent-facing environment/operational constraints for MJAI (Japanese text-correction AI app: FastAPI backend + Next.js frontend + Supabase Postgres). See `README.md` for the human-facing setup guide and feature overview — this file only covers what an agent must know before running commands, changing config, or deploying.

## ⚠️ Reality check: docs vs. repo state

`README.md`'s older "Quick Start (Docker & ngrok)" text may still mention `conf/docker-compose.yml`, `conf/ngrok.yml`, `conf/start.sh`, and `conf/update-env.sh` — those paths under `conf/` are **not** present. Local compose lives at the **repo-root** `docker-compose.yml` (backend `:8000`, frontend `:3000`). There is still no ngrok tunnel-provisioning tooling in-repo; `*_NGROK_URL` vars remain optional CORS allow-list entries. **Production path: both backend and frontend on Vercel (monorepo deployment), app DB + Auth on Supabase.** AI suggestions use **cloud APIs (Groq primary, Cloudflare failover) with WebLLM as offline fallback** — do **not** configure `GEMINI_*`.

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

**AI Provider Keys (backend-only, never `NEXT_PUBLIC_*`):**
| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Primary AI provider for fast inference (~1-3s). Get from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | Optional. If set, disables per-request model rotation and pins every request to this exact model id (see `ALLOWED_GROQ_MODELS` rotation pool in `backend/app/llm/groq_provider.py`) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID for Workers AI fallback. Get from Cloudflare dashboard |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with Workers AI access |

WebLLM (client-side) requires no backend configuration — it runs in the browser using WebGPU.

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
- `TF_API_TOKEN` — Terraform削除済み（`terraform/`ディレクトリは削除されました）

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
- `GROQ_API_KEY` — Primary AI provider (recommended)
- `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` — Fallback AI provider (optional)

**Render and Terraform infrastructure has been removed**: The Render Web Service and `terraform/` directory have been deleted. All deployment is now via Vercel git integration.

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

AI correction suggestions use a **hybrid architecture**: cloud APIs for speed with client-side WebLLM as offline fallback.

### Architecture Overview

```
User Request → POST /api/suggestions (authenticated)
              ↓
         Groq API (primary, ~1-3s)
              ↓ 429/5xx/timeout
         Cloudflare Workers AI (fallback)
              ↓ both fail
         Frontend falls back to WebLLM (offline)
```

| Path | Provider | Latency | When Used |
|------|----------|---------|-----------|
| **Default** | Groq, model rotation pool (see below), overridable/pinnable via `GROQ_MODEL` | ~1-3s | API keys configured, Groq available |
| **Failover** | Cloudflare Workers AI | ~2-5s | Both attempted Groq models rate-limited/error/timeout |
| **Offline** | WebLLM (Mistral 7B) | ~10-30s | API unavailable OR user enables オフラインモード |

**Groq model rotation (added 2026-08 ahead of `llama-3.3-70b-versatile`'s 2026-08-16 deprecation):** rather than pinning to a single hardcoded model, `backend/app/llm/groq_provider.py` selects a model per request from a curated allow-list (`ALLOWED_GROQ_MODELS`):

| Model ID | Role |
|---|---|
| `openai/gpt-oss-120b` | Rotation pool — Production tier, quality-focused |
| `openai/gpt-oss-20b` | Rotation pool — Production tier, speed/cost-focused |

- **Selection**: `random.choice`-style (`random.sample`) per request, not a stateful round-robin — Vercel serverless functions are stateless per-invocation, so an in-memory counter would not reliably rotate in production.
- **In-provider retry**: on a retriable Groq failure (429/5xx/timeout), the provider retries once against a second, different model from the pool (`call_groq_with_rotation()`) before the `suggestions.py` failover chain falls over to Cloudflare — bounding the Groq phase to at most 2 attempts to keep total request latency predictable.
- **`GROQ_MODEL` override**: if set to a non-empty value, rotation is fully disabled and every request pins to that exact model id, with no in-provider retry — unchanged from prior behavior, useful for debugging or pinning to a specific model.
- **JSON mode**: Groq requests send `response_format: {"type": "json_object"}` plus `max_tokens: 4096` so long epic corpora do not truncate mid-JSON or drift into prose.
- **Content salvage**: if Groq returns HTTP-OK but unparseable or non-Chinese `reason`/`overallComment`, `suggestions.py` still tries Cloudflare in the same pass before the outer language/parse retry loop.
- **Excluded from the pool** (and why): `qwen/qwen3.6-27b` (live Chinese-enforcement smoke on CN-source/JP-target corpora frequently returned Japanese explanations or empty bodies despite `reasoning_effort: "none"`; still pin-able via `GROQ_MODEL`), `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` (Groq shutdown date 2026-08-16), `qwen/qwen3-32b` (already deprecated/404s), `openai/gpt-oss-safeguard-20b` (safety/policy-classification tuned), `groq/compound`/`compound-mini` (agentic/tool-use, low RPD), `meta-llama/llama-prompt-guard-2-*` (classifier models), `allam-2-7b` (Arabic-focused, not evaluated for Japanese quality).
- **Maintenance note**: `ALLOWED_GROQ_MODELS` is a static, manually-reviewed constant — there is no runtime catalog-refresh mechanism. If Groq announces further deprecations, update this list (and this table) as a small follow-up change; do not wait for production errors to surface it.

### Backend Providers (`backend/app/llm/`)

| Module | Purpose |
|--------|---------|
| `prompts.py` | Shared prompt (ported from frontend WebLLM prompts) |
| `parser.py` | Hardened JSON parser (trailing commas, truncated JSON, markdown fences) |
| `groq_provider.py` | Groq API client, 25s timeout, JSON-object mode, model rotation pool (`ALLOWED_GROQ_MODELS`) + in-provider retry |
| `cloudflare_provider.py` | Cloudflare Workers AI client (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`, 45s timeout) with response-shape normalize |
| `suggestions.py` | Failover chain logic |

### Environment Variables (Vercel Production)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Recommended | Primary provider. Get from [console.groq.com](https://console.groq.com) → API Keys |
| `GROQ_MODEL` | Optional | Pins Groq to a single model id, disabling rotation across `ALLOWED_GROQ_MODELS`, without a code change |
| `CLOUDFLARE_ACCOUNT_ID` | Optional | Fallback provider. Get from Cloudflare dashboard → Overview |
| `CLOUDFLARE_API_TOKEN` | Optional | Fallback provider. Create token with Workers AI read access |

If neither is configured, `/api/suggestions` returns 503 and frontend auto-falls back to WebLLM.

### Frontend UX

- **Default behavior**: Calls `/api/suggestions` first for fast response
- **Auto-fallback**: If API fails, automatically switches to WebLLM with toast notification
- **オフラインモード toggle**: User can explicitly enable WebLLM-only mode (checkbox near generate button)
- **Visual indicator**: Badge shows "クラウドAPI" or "ローカルAI" after generation

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

### Prompts (Shared)

Same prompt is used across all providers (backend and WebLLM):

```
frontend/src/lib/webllm/prompts/
├── system.ts     # System prompt (Chinese, ultra-concise for small models)
├── fewShot.ts    # Minimal few-shot example
└── templates.ts  # Section headers

backend/app/llm/prompts.py  # Python port of above
```

### Response Schema

All providers return the same JSON structure:

```json
{
  "suggestions": [
    {"id": "1", "original": "指摘箇所", "reason": "修正理由", "sourceExcerpt": "原文中の対応箇所（該当する場合のみ、省略/空文字可）"}
  ],
  "overallComment": "全体講評"
}
```

`sourceExcerpt` (added 2026-08, `highlight-suggestion-text-spans` change) is optional: an excerpt from SOURCE TEXT (原文) corresponding to the flagged TARGET TEXT snippet in `original`, used by the frontend to highlight the matching span in the SOURCE TEXT textarea. Omitted/empty when the model finds no clear correspondence — never fabricated. Not persisted through `POST /proposals`.

### How to Get API Keys

**Groq (primary, free tier available):**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in
3. Navigate to API Keys → Create API Key
4. Copy key and set as `GROQ_API_KEY` in Vercel

**Cloudflare Workers AI (fallback):**
1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Copy Account ID from Overview page → set as `CLOUDFLARE_ACCOUNT_ID`
3. Go to My Profile → API Tokens → Create Token
4. Use "Workers AI" template or custom with Workers AI Read permission
5. Copy token and set as `CLOUDFLARE_API_TOKEN` in Vercel
