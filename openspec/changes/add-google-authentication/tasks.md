## 1. Supabase project setup (manual, one-time)

- [x] 1.1 In the Supabase project's Auth settings, enable the Google OAuth provider and configure the Google Cloud OAuth client ID/secret and authorized redirect URI. Done via Management API (`PATCH /v1/projects/{ref}/config/auth`) for project `fqyhrubqkpuyliqojbai`; Google Cloud Console redirect URI / JS origin already confirmed by the project owner. Project was restored from `INACTIVE` before config could be applied.
- [x] 1.2 Record the project's `SUPABASE_JWT_SECRET` (from Supabase project API settings) for backend JWT verification, and confirm `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` (already present in `conf/.env`) are correct for this project. JWT secret fetched via Management API `GET /v1/projects/{ref}/postgrest` (`jwt_secret`); anon key refreshed via `projects api-keys` / `GET .../api-keys`. Presence-only check: all three keys are non-empty in local `conf/.env`.
- [x] 1.3 Decide and record the allow-listed Google account email(s) to use as `ALLOWED_USER_EMAIL`. Owner provided three addresses (flat allow-list, no RBAC); written to both `ALLOWED_USER_EMAIL` and `ALLOWED_USER_EMAILS` in `conf/.env`.

## 2. Backend: JWT verification and allow-list dependency

- [x] 2.1 Add a JWT-verification library (e.g. `PyJWT`) to `backend/requirements.txt`.
- [x] 2.2 Create `backend/app/auth.py` with a `get_current_user` FastAPI dependency that: reads the `Authorization: Bearer <token>` header, verifies the JWT signature/expiry against `SUPABASE_JWT_SECRET`, and returns the decoded claims (raise `401` for missing/malformed/invalid/expired tokens).
- [x] 2.3 In `get_current_user` (or a second dependency composed after it), extract the token's `email` claim and compare case-insensitively against `ALLOWED_USER_EMAIL` (read from env, support a future comma-separated list without requiring code changes); raise `403` if it doesn't match.
- [x] 2.4 Apply `dependencies=[Depends(get_current_user)]` to the existing `router = APIRouter()` in `backend/app/main.py` so all `/sessions*`, `/histories*`, `/proposals*` routes require a valid, allow-listed token.
- [x] 2.5 Move or annotate the `/suggestions` endpoint (currently a bare `@app.post`) so it also requires `get_current_user`.
- [x] 2.6 Leave `/health` unauthenticated on the bare `app` so deploy-time health checks (`.github/workflows/deploy.yml`) keep working.
- [x] 2.7 Add `ALLOWED_USER_EMAIL` and `SUPABASE_JWT_SECRET` to `conf/.env.example` (placeholder values) and to local `conf/.env`. Placeholders were already in `.env.example`; real local values are now in `conf/.env` (gitignored).
- [x] 2.8 Add/update backend tests covering: request with no token → `401`; request with invalid/expired token → `401`; request with valid token but non-allow-listed email → `403`; request with valid token and allow-listed email → success.

## 3. Frontend: Supabase client and auth context

- [x] 3.1 Add `@supabase/supabase-js` to `frontend/package.json`.
- [x] 3.2 Create a Supabase browser client module (e.g. `frontend/src/lib/supabaseClient.ts`) initialized from `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- [x] 3.3 Create an `AuthProvider` React context (e.g. `frontend/src/app/auth-provider.tsx`) exposing `session`, `user`, `signInWithGoogle()`, `signOut()`, and a way to force sign-out on a 401; restore session via `supabase.auth.getSession()` on mount and subscribe to `supabase.auth.onAuthStateChange`.
- [x] 3.4 Wrap `children` in `<AuthProvider>` inside `frontend/src/app/layout.tsx`.

## 4. Frontend: login screen and route guard

- [x] 4.1 Build a `LoginScreen` component with a "Googleでログイン" button calling `signInWithGoogle()`.
- [x] 4.2 In `frontend/src/app/page.tsx`, add an early guard: while auth state is loading, show a loading state; if no session, render `LoginScreen` instead of the correction workspace; only fetch sessions/render the workspace once authenticated.
- [x] 4.3 Add a visible logout control (e.g. in the sidebar header) that calls `signOut()` and returns the user to the login screen.

## 5. Frontend: attach auth token to API calls

- [x] 5.1 In `frontend/src/app/api.ts`, update `apiFetch` to read the current Supabase session/access token and add an `Authorization: Bearer <token>` header to every request when a session exists.
- [x] 5.2 In `apiFetch`, on a `401` response, trigger the `AuthProvider`'s sign-out/unauthenticated state so the app redirects to the login screen instead of surfacing a generic API error.
- [x] 5.3 Verify all existing API modules (`sessionAPI`, `historyAPI`, `proposalAPI`, `suggestionsAPI`) pick up the header automatically via `apiFetch` (no per-call-site changes expected). Confirmed: all four modules call `apiFetch` exclusively; no per-call-site changes were needed.

## 6. Config and docs

- [x] 6.1 Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `ALLOWED_USER_EMAIL`, `SUPABASE_JWT_SECRET` to `conf/.env.example` with placeholder values and short comments.
- [ ] 6.2 Add the new env vars to the deployed backend (Render) and frontend (Vercel/Render static) environment variable settings. **Blocked**: requires the project owner's Render/Vercel dashboard access.
- [x] 6.3 Update `docs/github-secrets.md` if any of the new values need to be stored as CI/CD secrets (e.g. if tests need `SUPABASE_JWT_SECRET`). Decision: not needed — the new backend tests (`backend/tests/test_auth.py`) set `SUPABASE_JWT_SECRET`/`ALLOWED_USER_EMAIL` via test fixtures (`monkeypatch`), so no real secret needs to be added to CI. No doc changes made.

## 7. Verification

Local Auth plumbing is ready: Google provider enabled, redirect allow-list includes `http://localhost:3000/**`, `conf/.env` has JWT secret + allow-list, frontend/backend return HTTP 200 after compose restart. Automated unit coverage remains in `backend/tests/test_auth.py` and `frontend/src/app/__tests__/authGuard.test.tsx`. Remaining items below need a real browser Google sign-in (and/or deployed envs for 7.1 against production).

- [ ] 7.1 Manually verify: visiting the deployed frontend with no session shows the login screen and makes no calls to protected endpoints. (Local: frontend at `http://localhost:3000` loads HTTP 200 and should show login when unauthenticated — confirm in browser.)
- [ ] 7.2 Manually verify: signing in with an allow-listed Google account grants access and the workspace loads sessions successfully.
- [ ] 7.3 Manually verify: signing in with a different (non-allow-listed) Google account is denied access (no data shown, backend returns `403` for that account's token).
- [ ] 7.4 Manually verify: calling a protected endpoint directly (e.g. via curl) with no `Authorization` header returns `401`; with a garbage token returns `401`.
- [ ] 7.5 Manually verify: logging out returns to the login screen, and a subsequent reload does not restore access without signing in again.
- [ ] 7.6 Manually verify: reloading the page while logged in as an allow-listed user keeps the session (no forced re-login).
