## Why

Users are currently asked to log in every time they visit the app, even though they have already successfully authenticated via Google. Additionally, the WebLLM model (~3.7GB for Phi-3.5-mini-instruct-q4f16_1-MLC) re-downloads on every session despite `@mlc-ai/web-llm` supporting browser-level caching via Cache API. Logout should not clear the model cache, and leaving/reopening the page should reuse cached weights.

## What Changes

- **Auth session restoration**: Ensure `supabase.auth.getSession()` is called on app boot and Supabase client is configured with `persistSession: true`, `autoRefreshToken: true`, `detectSessionInUrl: true`, so returning users remain signed in across page reloads and browser sessions. Frontend must not clear session state unnecessarily on mount or navigation.
- **Logout does not wipe WebLLM cache**: The sign-out flow must only clear auth state (localStorage/sessionStorage keys used by Supabase) and must NOT clear the browser's Cache API or IndexedDB entries used by `@mlc-ai/web-llm` to store model weights.
- **WebLLM persistent caching**: Verify and document that `@mlc-ai/web-llm` already uses the browser's Cache API for model weights and that this cache persists across page navigations, reloads, and browser sessions. Engine re-initialization should detect cached weights and skip the full download, showing progress only when actually fetching.
- **Document WebLLM model**: Add explicit documentation (AGENTS.md, code comments, this change's artifacts) stating the model ID (`Phi-3.5-mini-instruct-q4f16_1-MLC`), approximate size (~3.7GB), and caching behavior.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `authentication`: Strengthen session persistence requirement to clarify that the frontend must restore existing sessions on page load and not require re-login unless the session is truly expired or invalid.

## Impact

- **Frontend code**: `frontend/src/lib/supabaseClient.ts`, `frontend/src/app/auth-provider.tsx`, `frontend/src/app/page.tsx`. Minor verification/hardening of existing logic.
- **Logout flow**: Confirm `signOut()` only clears Supabase auth state, not Cache API.
- **Documentation**: `AGENTS.md` AI Suggestion Generation section, code comments in `frontend/src/lib/webllm/config.ts` and `engine.ts`.
- **No backend changes required**.
- **No database schema changes**.
