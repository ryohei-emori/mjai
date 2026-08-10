## Why

Every endpoint in `backend/app/main.py` (`/sessions`, `/histories`, `/proposals`, `/suggestions`, `/health`) is currently open to any caller, and the frontend (`frontend/src/app/page.tsx`) has no login screen — anyone who reaches the deployed URL can read and write correction data. The app is being deployed publicly (see the sibling Vercel/Render deployment changes), so it now needs a real access-control boundary. The intended user base is a single person, so the simplest secure design is Google OAuth login restricted to one allow-listed email address, rather than building general multi-user account management.

## What Changes

- Add a login screen in the frontend that unauthenticated users are redirected to; users sign in with their Google account via Supabase Auth (`@supabase/supabase-js`).
- **BREAKING**: The backend's `/sessions`, `/histories`, and `/proposals` routes start requiring a valid Supabase-issued JWT (via `Authorization: Bearer <token>`); requests without one are rejected with `401`.
- Enforce a single-allow-listed-email restriction server-side: after verifying the JWT, the backend checks the token's email claim against an `ALLOWED_USER_EMAIL` env var and rejects (`403`) any other Google account, even if it successfully authenticated with Google/Supabase.
- Add a logout flow and persist the logged-in session across page reloads until the token expires or the user logs out, with silent token refresh handled by the Supabase client.
- Add new auth-related env vars (Supabase URL/anon key, allow-listed email) to `conf/.env.example`.
- Note (not part of this change): `/suggestions` is being replaced by client-side WebLLM generation in a sibling change. That flow also requires a logged-in user, so this authentication capability must land before or alongside the WebLLM change.

## Capabilities

### New Capabilities
- `authentication`: Google OAuth sign-in via Supabase Auth, login-gated frontend, JWT-verified and single-email-restricted backend routes, session persistence, and logout.

### Modified Capabilities
(none — the session/history/proposal management capabilities themselves are unchanged; only their access control changes, which is fully described by the new `authentication` capability rather than by editing those baselines)

## Impact

- **Frontend**: `frontend/src/app/page.tsx` (auth gate/redirect), new login screen component, `frontend/src/app/api.ts` (attach `Authorization` header to all requests), `frontend/package.json` (new `@supabase/supabase-js` dependency), new Supabase client/session-context module.
- **Backend**: `backend/app/main.py` (JWT verification dependency applied to `/sessions`, `/histories`, `/proposals` routes; allow-listed-email check), `backend/requirements.txt` (JWT/Supabase verification dependency), `conf/.env.example` (new env vars).
- **Config/Secrets**: New Supabase project Auth settings (Google provider client ID/secret), new env vars for Supabase URL, anon key, and `ALLOWED_USER_EMAIL`.
- **Dependencies**: Assumes the sibling Supabase database migration change lands (or is landing in parallel) so a Supabase project already exists to host Auth; does not redesign persistence.
