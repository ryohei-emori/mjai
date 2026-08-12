## 1. Root-cause verification

- [x] 1.1 Confirm `loadSessions()` unconditionally re-initializes `originalText`/`targetText`/`suggestions`/`overallComment`/`savedData` to empty on every run, and confirm its triggering `useEffect` is keyed on the `session` object from `useAuth()`
- [x] 1.2 Confirm `handleGenerateClick` never touches `originalText` and never calls `loadSessions()` directly (rules out a direct causal link for the "disappears on Generate click" report)
- [x] 1.3 Confirm the `session`-identity-churn trigger path(s): `auth-provider.tsx`'s `onAuthStateChange` (including routine `TOKEN_REFRESHED`) and `api.ts`'s 401-driven `handleUnauthenticated()` → `setSession(...)`, both of which replace the `session` object reference and would re-trigger `loadSessions()`
- [x] 1.4 Verify the TARGET-text clear ordering in `handleGenerateClick`/`addJobAndProcess` (queue-then-clear, same tick, no `await` between) so clearing never discards a not-yet-queued submission

## 2. Fix `loadSessions()` to merge instead of clobber

- [x] 2.1 Change `loadSessions()`'s `setSessions(convertedSessions)` to a `setSessions((prev) => ...)` updater
- [x] 2.2 For each converted session, resolve `originalText`/`targetText`/`suggestions`/`overallComment` by checking the matching entry in `prev` first, then `loadDraftFromStorage(sessionId)`, then falling back to the empty defaults only if neither exists
- [x] 2.3 Preserve `savedData` from `prev` when present (avoid discarding already-fetched history details from `loadSessionDetails()` on a `loadSessions()` re-run)
- [x] 2.4 Ensure per-session isolation: verify the merge is keyed strictly by session id with no cross-session fallback

## 3. Confirmed-save clears the persisted draft

- [x] 3.1 Verify `saveCorrections()`'s existing `clearDraftFromStorage(currentSession.id)` call sites (already present, ~3 locations) correctly clear the SOURCE/TARGET text draft as part of the same draft object, since `PersistedDraft` already contains both fields — no separate clear call needed if the shape is unchanged
- [x] 3.2 If SOURCE/TARGET text is split into its own storage key instead of reusing `PersistedDraft` (see Task 4 decision), add the equivalent clear call at the same call sites

## 4. Implementation in `frontend/src/app/page.tsx`

- [x] 4.1 Decide storage shape: reuse the existing `PersistedDraft`/`DRAFT_STORAGE_PREFIX` object (already includes `originalText`/`targetText`) rather than introducing a new key — confirms with design.md Decision 1
- [x] 4.2 Implement the `loadSessions()` merge fix (Task 2)
- [x] 4.3 Add a short code comment at the `handleGenerateClick` TARGET-text clear site noting it is intentional (multi-target-per-source workflow), not a bug, referencing this change
- [x] 4.4 Re-verify `createNewSession()` still correctly initializes a brand-new session's text to `""` (expected, unaffected by this fix — no draft can exist yet for a session id that didn't exist before this call)
- [x] 4.5 Re-verify `deleteSession()`'s existing `clearDraftFromStorage`/`clearJobQueueFromStorage` calls remain correct (unaffected, but confirm no regression)

## 5. Verification

- [x] 5.1 Run `npm run lint` in `frontend/` and confirm no new errors introduced
- [x] 5.2 Run `npm run build` in `frontend/` and confirm no new errors introduced
- [x] 5.3 Note any pre-existing unrelated lint/build failures separately from this change's results

## 6. Planning artifacts

- [x] 6.1 Mark all tasks above complete as implemented
- [x] 6.2 Confirm `docs/UI-DESIGN.md` does not need updating (no existing precedent for documenting draft-persistence behavior there; design.md carries the note instead)
