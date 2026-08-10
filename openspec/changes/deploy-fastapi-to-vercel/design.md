## Context

See `proposal.md` — Why for the motivation. Relevant current state:

- **Backend location**: `backend/app/main.py` exports a `FastAPI` instance named `app` via `uvicorn app.main:app`. Currently hosted on Render Web Service `mjai` (srv-d2f031buibrs738hhe40, `https://mjai.onrender.com`), which is **Suspended**.
- **Backend dependencies**: `backend/requirements.txt` (FastAPI, uvicorn, asyncpg, PyJWT, python-dotenv, etc.). No `pyproject.toml` exists.
- **Env var loading**: `backend/app/main.py` searches for `.env` files via `dotenv` at startup, looking in `${APP_ROOT}/../conf/.env`, `${APP_ROOT}/.env`, `/conf/.env`.
- **Frontend**: Already on Vercel per `deploy-frontend-to-vercel` change; uses `NEXT_PUBLIC_API_URL` to call backend.
- **Terraform**: `terraform/main.tf` uses `render-oss/render` provider; backend service is **outside** Terraform management.

## Goals / Non-Goals

**Goals:**
- Define the Vercel entrypoint structure for the FastAPI backend.
- Specify `vercel.json` configuration for Python runtime and function settings.
- Update CORS to include Vercel frontend origin and remove stale Render references.
- Document which env vars must be configured in Vercel Project Settings.
- Update `AGENTS.md`, `docs/DESIGN.md`, and related docs to reflect the new deployment target.
- Provide clear manual steps for Render retirement (not automated destruction).

**Non-Goals:**
- Changing the FastAPI API contract (routes, request/response formats unchanged).
- Multi-region or edge function deployment (single region is sufficient).
- Terraform management of Vercel resources (use Vercel's native git integration).
- Automated deletion of the Render service (manual retirement only).

## Decisions

### Decision 1: Use `api/index.py` entrypoint pattern with symlink/import

**Chosen approach**: Create `api/index.py` at the repo root that imports and re-exports the `app` from `backend/app/main.py`. This matches Vercel's standard Python function detection pattern (`api/*.py`) while preserving the existing backend code structure.

```
mjai/
├── api/
│   └── index.py          # from backend.app.main import app
├── backend/
│   ├── app/
│   │   ├── main.py       # existing FastAPI app
│   │   ├── auth.py
│   │   └── db_helper.py
│   └── requirements.txt
├── vercel.json
└── ...
```

**Alternatives considered**:
- *Move `backend/app/main.py` to `api/index.py` directly*: Would break the existing backend directory structure and Docker development workflow. Rejected to minimize disruption.
- *Use `pyproject.toml` `[tool.vercel].entrypoint`*: Requires creating a new `pyproject.toml` and migrating from `requirements.txt`. More churn than needed; Vercel auto-detects from `requirements.txt`. Revisit if pyproject migration is desired for other reasons.
- *Use `app/main.py` or `src/main.py` as entrypoint*: These are also detected by Vercel, but `api/` is the canonical pattern for serverless functions and communicates intent clearly.

### Decision 2: Configure `vercel.json` for Python function settings

**Chosen approach**: Add `vercel.json` at repo root with:
- Function configuration for `api/index.py` (maxDuration, memory if needed)
- Rewrites to route all `/api/*` requests to the function
- Python runtime version pin (3.12, matching Vercel's default and our codebase)

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/index.py": {
      "maxDuration": 30
    }
  },
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/index.py" }
  ]
}
```

Note: `maxDuration: 30` is appropriate for thin CRUD operations; Vercel Pro/Enterprise can extend to 60+ seconds if needed. Hobby tier default is 10 seconds; 30 requires Pro tier.

**Alternatives considered**:
- *No `vercel.json`*: Vercel auto-detects FastAPI, but explicit config documents intent and allows tuning. Minimal overhead to add.
- *`pyproject.toml` `[tool.vercel]` instead*: Would require creating pyproject.toml. Vercel.json is simpler and more widely documented.

### Decision 3: Same-project deployment (monorepo) vs. separate Vercel projects

**Chosen approach**: Deploy both frontend and backend from the **same** Vercel project as a monorepo. Frontend lives at root `/` routes, backend at `/api/*` routes. This eliminates CORS complexity (same-origin requests) and simplifies env var management.

Vercel monorepo structure:
- Frontend: `frontend/` as root directory for the Next.js framework preset
- Backend: `api/index.py` at repo root as Python serverless function

Configure in Vercel dashboard:
- Root Directory: `.` (repo root, not `frontend/`)
- Framework: Next.js (auto-detected from `frontend/`)
- Build Command: `cd frontend && npm install && npm run build`
- Output Directory: `frontend/.next`

**Alternatives considered**:
- *Two separate Vercel projects* (one for frontend, one for API): Adds CORS complexity, two sets of env vars, two deployment URLs. Rejected as unnecessary for this use case.
- *Next.js API routes instead of FastAPI*: Would require rewriting the entire backend in TypeScript. Rejected — FastAPI is working and well-tested.

### Decision 4: Environment variable configuration in Vercel

**Chosen approach**: Configure these environment variables in Vercel Project Settings → Environment Variables:

| Variable | Scope | Value |
|---|---|---|
| `DATABASE_URL` | Production, Preview | Supabase Postgres connection string |
| `SUPABASE_JWT_SECRET` | Production, Preview | Supabase JWT secret (for auth verification) |
| `ALLOWED_USER_EMAIL` | Production, Preview | Allowed Google email(s) |
| `FRONTEND_URL` | Production | Production Vercel URL (e.g., `https://mjai.vercel.app`) |
| `FRONTEND_URL` | Preview | (can omit; same-origin for monorepo) |
| `ENVIRONMENT` | Production | `production` |
| `ENVIRONMENT` | Preview | `development` |
| `PYTHONPATH` | Production, Preview | `/var/task/backend` (if needed for imports) |

Since this is a monorepo (same-origin), `FRONTEND_URL` and CORS complexity are minimized — the frontend calls `/api/*` without cross-origin concerns.

### Decision 5: Update CORS configuration

**Chosen approach**: Modify `backend/app/main.py` CORS allow-list:
- Keep localhost/LAN origins for local development
- Add Vercel production URL pattern (`https://*.vercel.app`)
- Remove Render-specific origins (`https://mjai-app-frontend.onrender.com`, `https://mjai.onrender.com`)
- Keep ngrok patterns for tunnel-based development

For monorepo same-origin deployment, CORS is effectively moot for production (same origin), but the allow-list remains for local dev and any future cross-origin scenarios.

### Decision 6: Frontend `NEXT_PUBLIC_API_URL` update

**Chosen approach**: For a monorepo deployment, set `NEXT_PUBLIC_API_URL` to a relative path or empty string:
- **Production**: `NEXT_PUBLIC_API_URL=` (empty or `/api` — frontend calls `/api/sessions`, etc. same-origin)
- **Local dev**: `NEXT_PUBLIC_API_URL=http://localhost:8000` (or backend dev server URL)

This leverages same-origin to avoid hardcoding a full URL.

**Alternatives considered**:
- *Full absolute URL* (`https://mjai.vercel.app/api`): Works but unnecessary for same-origin; adds a hardcoded domain to maintain.

## Risks / Trade-offs

- **[Risk]** Vercel serverless cold starts may be slower than Render's always-on service. → **Mitigation**: MJAI's thin CRUD API should cold-start quickly; Vercel Fluid compute keeps functions warm under moderate traffic. Monitor latency post-deploy.
- **[Risk]** Vercel Hobby tier has 10-second function timeout by default. → **Mitigation**: For a CRUD API this is sufficient; if needed, upgrade to Pro for 60+ second limits. Document tier requirements.
- **[Risk]** Python import paths may differ between local (`python backend/app/main.py`) and Vercel (`api/index.py` importing `backend.app.main`). → **Mitigation**: Test import structure during implementation; set `PYTHONPATH` if needed.
- **[Risk]** Render Web Service remains billable until manually suspended/deleted. → **Mitigation**: Clear manual steps in tasks.md; do not automate destruction.
- **[Trade-off]** Monorepo deployment couples frontend and backend versioning. → Accepted; this is a single-developer project where coupled deploys are simpler.

## Migration Plan

1. **Create `api/index.py`** at repo root that imports `app` from `backend.app.main`.
2. **Add `vercel.json`** with function config and rewrites.
3. **Add `requirements.txt`** at repo root (or symlink to `backend/requirements.txt`) so Vercel detects Python deps.
4. **Configure Vercel Project Settings**: Import repo, set root directory, configure env vars.
5. **Deploy preview**: Create a PR to trigger preview deployment; verify `/api/health` and a few API calls.
6. **Update frontend env var**: Set `NEXT_PUBLIC_API_URL` to empty/relative for production.
7. **Deploy production**: Merge to main; verify end-to-end.
8. **Update docs**: `AGENTS.md`, `docs/DESIGN.md`, `conf/.env.example`, `docs/github-secrets.md`.
9. **Retire Render** (manual): Suspend or delete the Render Web Service `mjai` from the Render dashboard.

**Rollback strategy**: If Vercel deployment fails:
1. Do not retire Render until Vercel is verified.
2. Revert the `NEXT_PUBLIC_API_URL` change to point back at Render.
3. The backend code changes (`api/index.py`, `vercel.json`) are additive and don't break local/Render deployment.

## Open Questions

- **Custom domain**: Whether to configure a custom domain for the Vercel deployment (e.g., `api.mjai.app`) — deferred as not required for functional parity.
- **Vercel tier**: Whether Hobby tier limits (10s timeout, 100GB bandwidth) are sufficient long-term — monitor usage post-deploy.
