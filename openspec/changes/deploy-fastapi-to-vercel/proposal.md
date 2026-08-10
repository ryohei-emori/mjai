## Why

The Render Web Service hosting the FastAPI backend (`mjai.onrender.com`) is currently Suspended. The architecture goal is to consolidate hosting on Vercel (where the frontend already lives) + Supabase (Auth + DB), eliminating Render entirely. MJAI's backend is a thin CRUD+auth API without long-running workers — it fits Vercel's serverless model well.

## What Changes

- **Restructure backend for Vercel Python runtime**: Adapt the FastAPI entrypoint to Vercel's expected layout (`api/index.py` or `app/main.py` with `app` export).
- **Add `vercel.json` or `pyproject.toml` Vercel config**: Configure the Python function entrypoint, maxDuration, and any routing needed for the API.
- **Update CORS allow-list**: Add the Vercel frontend origin and remove stale Render references.
- **Update `NEXT_PUBLIC_API_URL`**: Frontend must point to the new Vercel API URL pattern (e.g., `/api` for same-domain or `https://<project>.vercel.app/api` for cross-domain).
- **Document Vercel env vars**: `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOWED_USER_EMAIL`, `FRONTEND_URL` must be set in Vercel Project Settings.
- **Retire Render backend reference**: Mark the Render Web Service for manual suspension/deletion. **BREAKING** for any external clients using the old `mjai.onrender.com` URL.

## Capabilities

### New Capabilities

- `api-deployment`: Defines where and how the FastAPI backend is deployed (Vercel Python runtime, serverless function config, env var requirements, cold start considerations).

### Modified Capabilities

_None — existing API behavior (sessions, histories, proposals endpoints) is unchanged; only the hosting platform changes._

## Impact

- **Backend code**: Minor restructure of entrypoint layout to match Vercel's detection pattern; main.py logic unchanged.
- **Frontend**: `NEXT_PUBLIC_API_URL` env var must be updated to new Vercel API URL in Vercel Project Settings.
- **Infra**: Render Web Service `mjai` (srv-d2f031buibrs738hhe40) is retired; Terraform `render` provider references may become fully obsolete.
- **CORS**: `backend/app/main.py` CORS allow-list needs Vercel origin added, Render origins removed.
- **Docs**: `AGENTS.md`, `docs/DESIGN.md`, `conf/.env.example`, `docs/github-secrets.md` need updates.
- **Operational**: Vercel serverless has different cold start characteristics vs. always-on Render service; acceptable for this thin API but noted.
