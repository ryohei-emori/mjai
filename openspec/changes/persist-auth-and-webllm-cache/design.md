## Context

See proposal.md for motivation. The current implementation already has most of the pieces in place:

- `frontend/src/lib/supabaseClient.ts` configures `persistSession: true`, `autoRefreshToken: true`, `detectSessionInUrl: true`
- `frontend/src/app/auth-provider.tsx` calls `supabase.auth.getSession()` on mount to restore sessions
- `frontend/src/lib/webllm/engine.ts` maintains a module-scoped `cachedEngine` for in-memory caching during a session

The issue may be subtle: if the frontend renders the login screen before the async `getSession()` call completes, users see a flash of login screen even though they're authenticated. Additionally, `signOut()` behavior regarding Cache API is undocumented.

## Goals / Non-Goals

**Goals:**
- Ensure authenticated users don't see a login screen on page reload
- Verify and document that `signOut()` does not clear WebLLM's Cache API storage
- Document the WebLLM model (ID, size, caching mechanism) in AGENTS.md and code

**Non-Goals:**
- Changing the WebLLM model selection (Phi-3.5-mini-instruct-q4f16_1-MLC is adequate)
- Implementing explicit model cache management UI (clear cache button, etc.)
- Multi-user model cache isolation (single-user app, no need)
- Server-side session tracking changes (Supabase handles this)

## Decisions

### Decision 1: Auth loading state must block UI rendering

**Choice:** The auth provider shows a loading spinner while `getSession()` is in progress, and only renders children (main app or login screen) after the session check completes.

**Rationale:** The current `auth-provider.tsx` already has `isLoading` state, and `page.tsx` already renders a loader during `isAuthLoading`. This should work correctly.

**Verification needed:** Confirm the loading state is actually shown during the async gap. If users see a flash of login screen, it means `isLoading` is being set to `false` prematurely or the initial state is wrong.

**Current code review:**
- `isLoading` starts as `true` ✓
- `setIsLoading(false)` is called in the `.then()` of `getSession()` ✓
- `onAuthStateChange` also calls `setIsLoading(false)` - this could race with `getSession()` ✓ (but harmless)

The existing implementation appears correct. We'll verify in testing.

### Decision 2: Supabase `signOut()` does not clear Cache API

**Choice:** Rely on Supabase's documented behavior - `signOut()` only clears Supabase's own localStorage keys (`sb-*`), not arbitrary browser storage like Cache API.

**Rationale:** 
- `@supabase/supabase-js` v2's `signOut()` clears: `localStorage` keys it created (session, user), and optionally `sessionStorage`
- It does NOT touch: Cache API, IndexedDB, other localStorage keys
- `@mlc-ai/web-llm` uses Cache API for model weights (standard browser Cache Storage API)

**Verification needed:** Confirm by testing that model cache persists after logout.

**Alternative considered:** Explicitly preserve and restore Cache API references around signOut. Rejected because Supabase doesn't touch Cache API.

### Decision 3: Document WebLLM model details

**Choice:** Add documentation in:
1. `AGENTS.md` - AI Suggestion Generation section (already exists, enhance with cache details)
2. `frontend/src/lib/webllm/config.ts` - code comment with model details
3. This change's design doc - model specification

**Model specification:**
- Model ID: `Phi-3.5-mini-instruct-q4f16_1-MLC`
- Approximate download size: ~3.7 GB (quantized weights, tokenizer, model config)
- Caching: `@mlc-ai/web-llm` uses browser Cache API via MLC's `tvmjs` runtime
- Cache location: Browser's Cache Storage (can be seen in DevTools → Application → Cache Storage)
- Cache key pattern: Model files are stored under origin-scoped cache names managed by the library

### Decision 4: No explicit cache management in code

**Choice:** Do not add code to manually manage WebLLM cache. Let the library handle caching transparently.

**Rationale:**
- `@mlc-ai/web-llm` already handles cache detection on `CreateMLCEngine()`
- The library's `InitProgressReport` shows "Loading from cache" vs "Downloading" appropriately
- Adding manual cache checks would duplicate library logic and risk breaking on library updates

**Alternative considered:** Check `caches.has()` before engine init to show different UI. Rejected because the library's progress callback already handles this.

## Risks / Trade-offs

**[Risk: Browser cache eviction]** → Browser may evict Cache API entries under storage pressure. Mitigation: Accept this as browser-managed behavior; users on low-storage devices may need to re-download. No action needed from our side.

**[Risk: WebLLM library changes caching strategy]** → Future library updates could change cache keys or location. Mitigation: Pin library version in package.json; document cache behavior so changes are noticed on upgrades.

**[Risk: Session flicker on slow getSession()]** → On slow networks, `getSession()` might take noticeable time. Mitigation: Current loading spinner already handles this; no additional work needed.

## Verification Plan

1. **Auth persistence test:**
   - Log in → reload page → should remain logged in, no login screen flash
   - Log in → close tab → reopen → should remain logged in
   - Log in → close browser → reopen → should remain logged in (if session not expired)

2. **WebLLM cache test:**
   - Generate AI suggestion (triggers model download) → note progress shows download
   - Reload page → generate again → progress should show "Loading from cache" or skip quickly
   - Log out → log back in → generate → should not re-download

3. **Cache isolation test:**
   - DevTools → Application → Cache Storage → verify model files present after generation
   - Log out → verify model cache entries still present
