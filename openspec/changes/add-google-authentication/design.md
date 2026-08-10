## Context

See `proposal.md` for motivation. Relevant current state:

- **Frontend** (`frontend/src/app/page.tsx`, `layout.tsx`): a single client component rendered unconditionally by `RootLayout`. No auth wrapper, no route guard, no concept of a logged-in user today. All API calls go through `frontend/src/app/api.ts`'s `apiFetch` helper, which sends plain `fetch` requests with only a `Content-Type` header — no `Authorization` header exists anywhere in the frontend.
- **Backend** (`backend/app/main.py`): a single `FastAPI()` app with one `APIRouter` mounted at the root. Every route (`/sessions*`, `/histories*`, `/proposals*`, `/suggestions`, `/health`) is a plain path operation with no `Depends(...)` for auth — there is no auth concept in the backend at all today.
- **Deployment target**: Render (backend) + Vercel/Render static (frontend), per `deploy-frontend-to-vercel` and the Render backend already live at `https://mjai.onrender.com`. Both are public URLs reachable by anyone.
- **Parallel changes**: `migrate-database-to-supabase` is standing up a Supabase project as the Postgres host; this change assumes that Supabase project already exists (or is landing in parallel) so Supabase Auth is available on it. `migrate-ai-generation-to-webllm` assumes an authenticated browser session exists before it lets WebLLM run client-side — this change is what creates that authenticated session, but this change does **not** modify the WebLLM flow itself.
- Expected user count: **exactly one** real user. This shapes the design toward the simplest mechanism that is still genuinely secure (a single allow-listed email checked server-side), not a general multi-tenant user/roles system.

## Goals / Non-Goals

**Goals:**
- Gate the entire frontend app behind a Google sign-in screen.
- Verify Supabase-issued JWTs on every protected backend route, independent of the frontend (so hitting the API directly with curl and no/garbage token is rejected).
- Enforce the single-allow-listed-email restriction on the server, so passing Google/Supabase auth is necessary but not sufficient for access.
- Keep the mechanism simple enough for a one-user app: no roles, no user table, no invite flow, no admin UI.
- Define the exact integration point (frontend Supabase client + backend JWT verification) precisely enough that `tasks.md` is a straightforward checklist.

**Non-Goals:**
- Multi-user support, roles/permissions, or an admin UI for managing the allow-list (a single env var is sufficient for one user; a comma-separated list is noted as a future extension, not built now).
- Redesigning `/suggestions` or the WebLLM migration flow — this change only guarantees an authenticated session exists for that flow to depend on.
- Building Supabase's Google OAuth provider configuration via Terraform/IaC — this is a manual one-time step in the Supabase dashboard (documented in `tasks.md`), consistent with how other manual provider setup is already handled in this repo (e.g. Gemini API key).
- Rate limiting, brute-force protection, or audit logging beyond what Supabase Auth provides out of the box.

## Decisions

### 1. Use Supabase Auth's hosted Google OAuth flow (not a custom OAuth implementation)
Supabase Auth already implements the OAuth redirect/callback dance, PKCE, token issuance, and refresh-token rotation. Implementing Google OAuth by hand in FastAPI would duplicate this for no benefit, and the DB migration change is already introducing Supabase as a dependency — reusing its Auth product avoids adding a second unrelated auth provider. Alternative considered: NextAuth.js in the frontend with its own Google provider — rejected because it would need a separate backend-side verification story and a separate user store, whereas Supabase Auth's JWTs can be verified directly by the backend against the same project.

### 2. Frontend: `@supabase/supabase-js` client + a top-level auth guard in `layout.tsx`/a new `AuthProvider`
Add a Supabase client (browser-side, using `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`, both already present as unused env vars in `conf/.env`) and wrap the app in an `AuthProvider` (React context) that:
- On mount, calls `supabase.auth.getSession()` to restore any persisted session (Supabase's JS client persists the session in `localStorage` by default and handles silent refresh internally).
- Subscribes to `supabase.auth.onAuthStateChange` to react to sign-in/sign-out/token-refresh events.
- Exposes `session`, `user`, `signInWithGoogle()`, `signOut()` to the app.

`frontend/src/app/layout.tsx` wraps `children` in `<AuthProvider>`. Inside it (or in `page.tsx`), render a `<LoginScreen />` with a "Sign in with Google" button when there is no session, and only render the existing correction-workspace UI when a session exists. This is the natural insertion point identified in `page.tsx`/`layout.tsx`: `page.tsx` is currently a single unconditional component, so the guard becomes an early return at the top of the render (`if (!session) return <LoginScreen />`) rather than a rewrite of the existing workspace logic.

Alternative considered: per-route middleware/redirect (e.g. Next.js middleware.ts) — rejected because `next.config.js` currently targets a static export (`output: 'export'`, per `AGENTS.md`), where Next.js middleware does not run; a client-side guard works regardless of which of the two inconsistent build strategies documented in `AGENTS.md` ends up in effect.

### 3. Frontend → backend: attach the Supabase access token as a Bearer header in `api.ts`
`apiFetch` in `frontend/src/app/api.ts` is the single chokepoint all API modules (`sessionAPI`, `historyAPI`, `proposalAPI`, `suggestionsAPI`) already go through. Modify only this function to call `supabase.auth.getSession()` (cheap — reads from the client's in-memory/local-storage state, only hits the network if a refresh is due) and add `Authorization: Bearer <access_token>` to the request headers when a session exists. This means every existing API call gets the header automatically with a one-function change, instead of editing every call site.

On a `401` response, `apiFetch` triggers the same "unauthenticated" state used at startup (e.g. via a callback into `AuthProvider` that clears the session and shows the login screen), satisfying the "Session expires while app is open" scenario in the spec.

### 4. Backend: a single FastAPI dependency (`get_current_user`) applied to protected routers
Add `backend/app/auth.py` with a dependency that:
1. Reads the `Authorization: Bearer <token>` header (raises `401` if missing/malformed).
2. Verifies the JWT's signature and expiry using the Supabase project's JWT secret (`SUPABASE_JWT_SECRET`, a symmetric HS256 secret available in the Supabase project's API settings) via a standard JWT library (e.g. `PyJWT`, added to `backend/requirements.txt`). Verifying locally (no network call per request) is preferred over calling Supabase's `auth.getUser()` REST endpoint on every request, for latency and to avoid a hard runtime dependency on Supabase's API being reachable for every single data request.
3. Extracts the `email` claim and compares it (case-insensitively) against `ALLOWED_USER_EMAIL` from the environment; raises `403` if it doesn't match.
4. Returns the verified user info (at minimum, the email) for handlers that might want it; handlers otherwise ignore the return value since there's only one possible user.

Apply this dependency at the router level: `backend/app/main.py`'s existing `router = APIRouter()` (which already carries `/sessions*`, `/histories*`, `/proposals*`) gets `dependencies=[Depends(get_current_user)]` added, so every current and future route added to that router is protected by default — new routes don't need to remember to add the check individually. `/health` stays on the bare `app` (not the router) and remains unauthenticated, since it's used by the deploy workflow's post-deploy health check (`.github/workflows/deploy.yml`) and container health checks, which have no way to obtain a user token. `/suggestions` is currently a bare `@app.post` (not on `router`); it is moved onto the same protected router (or given the same `Depends(get_current_user)`) since it is a data-bearing endpoint per the spec's "protected endpoint" scenarios, even though it is slated for removal in the sibling WebLLM change.

Alternative considered: verifying via Supabase's REST `auth.getUser()` (network round-trip per request) — rejected as the default for latency/availability reasons, but noted as a fallback worth considering later if local JWKS/secret verification proves awkward (see Open Questions).

### 5. Allow-list as a single env var now, documented as extensible later
`ALLOWED_USER_EMAIL` holds exactly one address for now, matching the "exactly one user" requirement, added to `conf/.env.example` alongside the new Supabase Auth vars (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`). The comparison code is written against a small list (`{e.strip().lower() for e in os.environ.get("ALLOWED_USER_EMAILS", os.environ.get("ALLOWED_USER_EMAIL", "")).split(",") if e.strip()}`) so switching to multiple users later is a config-only change, not a code change — but only one value is configured/documented as part of this change.

### 6. 401 vs 403 semantics
- No token / malformed token / expired or invalid signature → `401 Unauthorized` (an authentication failure — the caller isn't proven to be anyone).
- Valid, verifiable token but email not on the allow-list → `403 Forbidden` (an authorization failure — the caller is proven to be someone, just not the allowed someone).

This distinction is what lets the frontend tell "please log in again" (401) apart from "your Google account isn't the allowed one, don't retry" (403) if it ever wants to show a different message, and matches the spec's separate scenarios for the two cases.

## Risks / Trade-offs

- **[Risk]** `SUPABASE_JWT_SECRET` is a powerful shared secret (anyone with it can forge valid tokens) → Mitigation: it's a backend-only env var (never `NEXT_PUBLIC_*`), stored the same way `GEMINI_API_KEY` already is (`conf/.env`, git-ignored, injected via Render env vars in production).
- **[Risk]** Local JWT verification means a user who is removed from the allow-list, or whose Supabase account is disabled, still has a technically-valid, unexpired JWT until it expires (Supabase default access-token lifetime is short, on the order of an hour) → Mitigation: acceptable for a single-owner app where the owner controls both the allow-list and their own logout; not a concern for external attackers since they'd need a valid Supabase session for the allowed account in the first place, which they don't have.
- **[Risk]** Static export / Next.js build mode inconsistency (noted in `AGENTS.md`) could affect where env vars are read from or whether a server-rendered guard is even possible → Mitigation: the design deliberately uses a client-side auth guard and client-side Supabase SDK, which works under both the static-export and standalone-server build paths described in `AGENTS.md`, avoiding a dependency on resolving that inconsistency.
- **[Trade-off]** Client-side-only route gating means the unauthenticated HTML/JS bundle itself is still served to anyone (no server-side page protection) → Accepted: this is standard for a client-rendered SPA-style app with no sensitive data in the bundle itself; all actual data lives behind the backend's server-verified JWT check, which is the real security boundary per the spec ("enforced server-side, not just hidden in the UI").
- **[Risk]** `/suggestions` moving under the auth dependency is technically a breaking API change for that endpoint → Mitigation: acceptable and intended (per proposal's `BREAKING` note); the endpoint is only used by the authenticated frontend today and is slated for replacement by the WebLLM change regardless.

## Migration Plan

1. Configure the Google OAuth provider in the Supabase project's Auth settings (Google Cloud OAuth client ID/secret) — manual, one-time, done in the Supabase dashboard, not in code.
2. Ship backend changes first (JWT-verification dependency + allow-list check on `router` and `/suggestions`), deployed behind a short window where the frontend doesn't yet send tokens — acceptable since this is a low-traffic, single-user app and a brief `401` on old frontend builds is not user-impacting for the app owner, who controls the deploy timing.
3. Ship frontend changes (Supabase client, login screen, guard, `api.ts` Bearer header) immediately after/alongside.
4. Add new env vars to `conf/.env` (local) and to the Render/Vercel dashboard env var settings for the deployed backend/frontend (consistent with how `GEMINI_API_KEY` etc. are already provisioned per `docs/github-secrets.md`).
5. **Rollback**: revert the backend `Depends(get_current_user)` addition (or temporarily unset/no-op the dependency) to restore the pre-change open-access behavior if something goes wrong; since this change adds a new capability rather than altering existing data/schema, rollback is a pure code revert with no data migration to undo.

## Open Questions

- Whether to verify tokens locally via `SUPABASE_JWT_SECRET` (HS256) or fetch Supabase's JWKS/call `auth.getUser()` remotely can be revisited later (e.g. if Supabase deprecates the shared JWT secret in favor of asymmetric per-project keys) without changing the spec, the allow-list behavior, or the task breakdown — it's an internal implementation detail of `get_current_user`.
- Exact Supabase JS session storage key/mechanism (localStorage vs cookie) is left to the library's default; can be revisited if a future requirement needs server-side rendering awareness, without affecting this change's requirements.
