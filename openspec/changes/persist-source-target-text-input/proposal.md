## Why

SOURCE text (原文, `currentSession.originalText`) and TARGET text (添削対象/翻訳, `currentSession.targetText`) live only in ephemeral client-side React state. `loadSessions()` unconditionally re-initializes both fields to `""` for every session every time it runs — and it re-runs any time the `session` object from `useAuth()` changes identity, which happens on every Supabase `onAuthStateChange` event (including routine background `TOKEN_REFRESHED` events with no user-visible auth change). This silently wipes text a user is actively typing or has not yet saved, with no relation to any user action. A second, related report says text disappears specifically when clicking "AI提案を生成" (Generate AI Suggestions); investigation confirms `handleGenerateClick` never touches `originalText` and never calls `loadSessions()`, so the SOURCE-text loss there is the same underlying bug — the Generate click merely starts a multi-second network request, widening the window in which a coincidental token-refresh-driven `loadSessions()` re-run can wipe the SOURCE text out from under the user. TARGET text, on the other hand, is intentionally cleared right after `handleGenerateClick` queues a job — that part is by design (repeated-target-per-fixed-source workflow) but reads as data loss to users and deserves an explicit note so it isn't "fixed" as a false regression later.

## What Changes

- **Persist SOURCE/TARGET text per session in `localStorage`**, mirroring the existing `DRAFT_STORAGE_PREFIX` draft-persistence pattern already used for AI suggestions/job queue (`loadDraftFromStorage`/`saveDraftToStorage`/`clearDraftFromStorage`, 500ms-debounced writes). `originalText`/`targetText` already flow through that exact draft object today — the missing piece is that `loadSessions()` and initial session hydration overwrite them with `""` instead of merging in whatever is already persisted.
- **Fix `loadSessions()` to merge, not clobber**: when (re-)building the `Session[]` list from the backend's session metadata (`SessionAPIResponse`, which carries no text fields), read any existing in-memory session state for that id plus any persisted draft, and only fall back to `""` when neither exists. This is the root-cause fix for both the general disappearance report and the "disappears on Generate click" report, since both trace back to the same `loadSessions()` re-run path being triggered by auth-session object churn.
- **Verify and, if needed, harden** the `session`-identity-change trigger in `frontend/src/app/page.tsx` (the `useEffect` calling `loadSessions()` keyed on `[session, loadSessions]`) so a `TOKEN_REFRESHED`-style same-user event does not blow away already-hydrated session text.
- **Keep session-switch restoration intact**: `handleSessionSwitch`'s existing one-time-per-tab draft restoration (gated by `restoredDraftSessionIdsRef`) continues to be the point where a *reload* recovers previously-typed text into a freshly-mounted session entry; this change makes sure nothing downstream re-blanks it afterward.
- **Clear persisted SOURCE/TARGET text on confirmed save**: extend the existing `clearDraftFromStorage()` call sites inside `saveCorrections()` (already present for the suggestions draft) to also be the point where the persisted text draft is dropped — consistent with "don't clear on every navigation, only on confirmed save."
- **Document, do not change, the intentional TARGET-text clear on Generate click**: `handleGenerateClick` clearing `targetText` immediately after `addJobAndProcess()` succeeds is kept as-is (ordering already guarantees the text is queued into a job before being cleared, so there is no window where it is lost without being queued). This proposal adds an explicit note in `design.md` and this file so future readers do not mistake it for a bug.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: The "Correction Input Form" requirement is strengthened from "kept in local component state" to "kept in local component state AND persisted per-session to `localStorage`, surviving page reloads, session-list re-fetches, and auth-session object churn, restored on session switch, and cleared only on confirmed save."

## Impact

- **Frontend code**: `frontend/src/app/page.tsx` only — `loadSessions()` (session-hydration merge fix), the SOURCE/TARGET localStorage helpers (new, alongside the existing `DRAFT_STORAGE_PREFIX` helpers), the debounced persistence `useEffect`, and the `saveCorrections()` clear-on-save call sites.
- **No backend changes**: confirmed not required — this is purely a client-side state-lifecycle bug; the backend never carried `originalText`/`targetText` and is not expected to.
- **No database schema changes.**
- **Documentation**: `docs/UI-DESIGN.md` is not expected to need a change (it does not currently describe draft-persistence behavior for the prior job-queue/suggestions change either — confirmed by inspection); this proposal's `design.md` carries the persistence-behavior note instead, following that same precedent.
