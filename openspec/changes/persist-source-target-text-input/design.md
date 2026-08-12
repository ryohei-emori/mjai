## Context

See `proposal.md` for motivation. Relevant existing code in `frontend/src/app/page.tsx`:

- `DRAFT_STORAGE_PREFIX` / `JOB_QUEUE_STORAGE_PREFIX` and `loadDraftFromStorage`/`saveDraftToStorage`/`clearDraftFromStorage`/`loadJobQueueFromStorage`/`saveJobQueueToStorage`/`clearJobQueueFromStorage` (~lines 109-232): the established localStorage-draft pattern. `PersistedDraft` already includes `originalText`/`targetText` fields — the draft object shape does not need to change.
- `handleSessionSwitch` (~lines 716-779): on first switch-to per tab (guarded by `restoredDraftSessionIdsRef`), merges `loadDraftFromStorage(sessionId)` into the matching `sessions` entry. This is the *reload-recovery* path and already works correctly for text fields, in isolation.
- The debounced-persistence `useEffect` (~lines 800-824): writes `{ originalText, targetText, suggestions, overallComment, confirmingHistoryIndex, confirmingJobId }` to storage 500ms after `currentSession` changes. This already covers writing SOURCE/TARGET text; it does not need new write logic, only to remain correctly ordered relative to the fix below.
- `loadSessions()` (~lines 911-934): **the actual bug**. Runs inside a `useEffect` keyed on `[session, loadSessions]` (~lines 1354-1358), where `session` comes from `useAuth()`. It rebuilds the *entire* `sessions` array from the backend's session metadata and unconditionally sets `originalText: "", targetText: "", suggestions: [], overallComment: "", savedData: []` for every session — discarding whatever was already in `sessions` state (including anything a user is mid-typing) and whatever is sitting in `localStorage` for sessions not yet visited via `handleSessionSwitch` in this tab.
- `frontend/src/app/auth-provider.tsx`: `session` (a Supabase `Session` object) is replaced via `setSession(newSession)` on every `onAuthStateChange` event, including `TOKEN_REFRESHED` — which fires periodically in the background regardless of user activity, as a *new object reference* even when the underlying user/token content is functionally a routine refresh. Since React's dependency comparison is referential, this reference change alone re-triggers the `loadSessions()` effect.
- `frontend/src/app/api.ts`: `apiFetch()` also independently calls `supabase.auth.getSession()` per request and, on a 401, calls `notifyUnauthorized()` → `handleUnauthenticated()` → `setSession(null)` (and, once reconnected, another `setSession(newSession)`) — a second, rarer path that produces the same kind of `session`-identity churn, more likely to coincide with a long-running request such as AI suggestion generation.
- `handleGenerateClick` (~lines 657-663): calls `addJobAndProcess(currentSession.targetText)` and then `updateCurrentSession({ targetText: "" })`. Confirmed by reading: this function never touches `originalText` and never calls `loadSessions()` — so it is not itself the source of SOURCE-text loss. The correlation users noticed ("text disappears when I click Generate") is because Generate starts a multi-second network call (`suggestionsAPI.generate`, or ~10-30s for WebLLM), which widens the time window during which a `session`-identity-churn-triggered `loadSessions()` re-run (from either of the two paths above) can land and wipe SOURCE text out from under the user while they wait. It is a timing coincidence, not a causal link through the click handler itself.

## Goals / Non-Goals

**Goals:**
- Make `loadSessions()` (and any other point that rebuilds the `Session[]` array from backend metadata) merge existing text instead of blindly re-initializing it, closing the root cause for both reported symptoms.
- Keep using the existing `PersistedDraft`/`DRAFT_STORAGE_PREFIX` localStorage pattern — no new storage key, no new persisted shape.
- Preserve strict per-session isolation: switching sessions must never bleed one session's text into another's storage read/write.
- Clear the persisted draft text only on confirmed save (`saveCorrections()` success), matching the existing suggestions-draft clear behavior at the same call sites.
- Leave the intentional TARGET-text clear in `handleGenerateClick` behaviorally unchanged; only document it.

**Non-Goals:**
- Server-side persistence of `originalText`/`targetText`. Not needed: this is a pure client-state lifecycle bug, and localStorage already round-trips correctly once `loadSessions()` stops clobbering it. (Explicitly checked per task constraints — no backend change is being made.)
- Changing Supabase auth-refresh behavior or `apiFetch`'s 401-handling flow. Those are legitimate, necessary behaviors; the fix is to make `loadSessions()` robust to being re-run, not to stop it from being re-run.
- Changing the intentional-clear UX for TARGET text on Generate click (e.g. delaying the clear until job completion). No evidence found that the current ordering (`addJobAndProcess()` then clear) ever loses text without it having been queued first — see Decision 3.

## Decisions

### 1. Merge strategy in `loadSessions()`

**Choice**: When mapping `SessionAPIResponse[]` to `Session[]`, for each session id, resolve `originalText`/`targetText` (and, for consistency, `suggestions`/`overallComment` — already-in-memory state should never regress either) by checking, in order:
1. The existing entry for that id in the current `sessions` state (covers "user is actively editing right now, in this tab, this render").
2. `loadDraftFromStorage(sessionId)` (covers "not yet visited this tab session, but a draft exists from a prior tab/reload").
3. Fall back to `""` / `[]` only if neither exists (a genuinely brand-new session with no draft).

Implemented via a `setSessions((prev) => ...)` updater (not a plain `setSessions(convertedSessions)`) so the merge can see the latest `prev` state without adding `sessions` to `loadSessions`'s dependency array (which would create a stale-closure/extra-rerender risk analogous to why `updateCurrentSession` already uses the updater form).

**Alternative considered**: Skip re-running `loadSessions()` entirely unless the session list is empty (e.g. `if (sessions.length === 0) loadSessions()`). Rejected: this would also suppress legitimate backend-driven changes (new `correctionCount`, sessions created/renamed in another tab), and does not fix the underlying fragility — any other future caller of `loadSessions()` or similar rebuild logic would reintroduce the same class of bug. Fixing the merge itself is more robust.

### 2. Where restoration from `localStorage` happens now

**Choice**: Keep `handleSessionSwitch`'s existing one-time-per-tab restoration (`restoredDraftSessionIdsRef`) as the primary reload-recovery path for a session the user actively opens, and have the `loadSessions()` merge (Decision 1) be the safety net for the general clobbering case. These two are complementary, not competing: `loadSessions()`'s merge protects against `sessions` state being blown away regardless of which sessions have been visited in the tab; `handleSessionSwitch`'s explicit restore-with-toast handles the intentional "hey, we found your unsaved draft" UX moment specifically at switch-in time. No change is needed to `handleSessionSwitch` itself.

**Alternative considered**: Move all restoration into `loadSessions()` and remove the switch-time restore/toast. Rejected: the switch-time toast ("Draftを復元しました") is a deliberate UX signal that users have relied on since the prior change; removing it changes UX unrelated to this bug's scope.

### 3. TARGET-text clear-after-queue ordering (Generate click)

**Verified**: `handleGenerateClick` calls `addJobAndProcess(currentSession.targetText)` synchronously, and `addJobAndProcess` synchronously calls `setJobQueue(prev => [...prev, newJob])` (the job, with its `targetText`, is committed to React state) *before* returning `true`; only then does `handleGenerateClick` call `updateCurrentSession({ targetText: "" })`. Both are synchronous state-setter calls in the same tick (no `await` between them), so there is no window in which the debounced localStorage-persistence effect (which fires ~500ms later, off the *settled* state) can observe or persist an intermediate "job not yet queued, text already cleared" state. The just-submitted text is safely captured in `jobQueue` (itself independently persisted via `JOB_QUEUE_STORAGE_PREFIX`) before the visible field is ever cleared.

**Decision**: No change to this ordering or timing. Add a one-line comment at the clear site plus the spec/proposal notes already written, so this is understood as intentional design, not a latent bug, the next time someone investigates a "target text disappeared" report.

**Alternative considered**: Defer the clear until the job reaches `completed` status (i.e. only clear on success). Rejected as out of scope per the task's explicit instruction — no evidence of actual data loss was found (the text is queued before being cleared), only a UX-perception issue, and changing this is a larger, separate UX decision.

## Risks / Trade-offs

**[Risk] Merge logic in `loadSessions()` could resurrect stale text for a session whose text was intentionally cleared elsewhere** → Mitigation: the merge order (in-memory `prev` state first, then localStorage) means an intentional clear that already updated `prev` state and/or called `clearDraftFromStorage` will not be resurrected; only genuinely absent state falls through to the old empty-string default.

**[Risk] Merging on every `loadSessions()` call adds a small amount of `Session[]`-rebuild work** → Mitigation: negligible; session lists are small (single-user app, per `ALLOWED_USER_EMAIL` allow-list design) and this only runs when the auth session's object identity changes, not on every render.

**[Trade-off] This still does not persist text server-side** → Accepted per Non-Goals: no cross-device/cross-browser sync for in-progress (unsaved) text. Once a round is confirmed via "確定してコピー・保存", it is already durably saved server-side as a `correction_histories` row; only the *unsaved draft* is browser-local, consistent with the existing suggestions/job-queue draft behavior this change extends.

## Migration Plan

No data migration. Purely a frontend logic fix; ships as a normal frontend deploy. No feature flag needed — this only removes an unintended data-loss window, it does not change any externally-visible API or persisted-storage schema (the `PersistedDraft` shape is unchanged, since `originalText`/`targetText` were already fields on it).

## Open Questions

None — both reported symptoms trace to the same confirmed root cause, and the TARGET-text clear-on-Generate behavior is confirmed safe as currently ordered.
