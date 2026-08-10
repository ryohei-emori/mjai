## 1. Verify and Harden Auth Session Persistence

- [x] 1.1 Verify `supabaseClient.ts` has correct auth config (`persistSession: true`, `autoRefreshToken: true`, `detectSessionInUrl: true`)
- [x] 1.2 Verify `auth-provider.tsx` correctly checks `getSession()` on mount before setting `isLoading` to false
- [x] 1.3 Verify `page.tsx` shows loading state during `isAuthLoading` and doesn't flash login screen
- [x] 1.4 Verify `signOut()` only clears Supabase auth state (no explicit cache clearing code)

## 2. Document WebLLM Model Details

- [x] 2.1 Add detailed model documentation comment to `frontend/src/lib/webllm/config.ts` (model ID, size, caching behavior)
- [x] 2.2 Update AGENTS.md AI Suggestion Generation section with model caching details

## 3. Verify WebLLM Cache Behavior

- [x] 3.1 Verify `@mlc-ai/web-llm` uses Cache API (check library docs/code or test empirically)
- [x] 3.2 Verify engine.ts `initializeEngine` properly reuses cached engine in-memory
- [x] 3.3 Add code comment in `engine.ts` documenting cache reuse behavior

## 4. Manual Testing Verification

> These tasks require user manual testing in a running application.

- [ ] 4.1 Test auth persistence: login → reload → should remain logged in
- [ ] 4.2 Test auth persistence: login → close/reopen tab → should remain logged in
- [ ] 4.3 Test WebLLM cache: generate suggestion → reload → should load from cache (fast)
- [ ] 4.4 Test logout cache isolation: generate suggestion → logout → login → generate → should load from cache
