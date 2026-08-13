## Context

See proposal.md — Why. Today `saveCorrections()` in `frontend/src/app/page.tsx` awaits `historyAPI.createHistory`, then a sequential loop of `proposalAPI.createProposal`, and only then copies to the clipboard and commits local UI (clear form, append History, remove confirmed job). The confirm button swaps the icon glyph to `progress_activity` while `isSaving` but omits `animate-spin`, unlike other loading sites in the same file (job `processing`, LATEST timer).

Backend APIs and persistence shape are unchanged. Parallel LLM/prompt changes must not be touched.

## Goals / Non-Goals

**Goals:**

- Make the user-visible confirm path feel instant for clipboard copy + local workspace reset.
- Keep server persistence reliable and double-submit-safe.
- Make any still-mounted waiting state on the confirm button obviously animated (ぐるぐる).

**Non-Goals:**

- Batching proposal creates into one API, changing history/proposal schemas, or retries/queue UI for failed background saves.
- Changing HITL job-confirm (`confirmJob`) load behavior, selection rules, or toast copy for unrelated buttons.
- Prompt / WebLLM / Groq changes.

## Decisions

### Decision 1: Copy + local UI commit first; persist in background

**Choice**: After validation, snapshot the session fields needed for APIs, `setIsSaving(true)`, copy the combined comment, apply the same local success side-effects as today's three branches (`confirmingJobId` / `confirmingHistoryIndex` / new-save), then run history+proposal creates without blocking that local commit. Toast copy (with “saving…” wording) immediately; toast save success or “copy ok, save failed” when the background work finishes; `setIsSaving(false)` in `finally` after background work.

**Why**: Matches the preferred UX; clipboard and form reset do not depend on network latency. Snapshotting before clear keeps the async save correct after the form is wiped.

**Alternatives considered**:

- *Spinner-only (keep await-then-copy)* — Fixes the frozen look but leaves copy slow; rejected as insufficient given the preferred architecture.
- *Copy first, keep UI until save completes* — Safer recovery on save failure, but still leaves the workspace “stuck” during network; rejected in favor of immediate local commit.

### Decision 2: Optimistic `SavedData` then patch `historyId`

**Choice**: Append `SavedData` on local commit with `historyId` omitted (or undefined). When `createHistory` returns, patch that entry’s `historyId` via a functional `updateCurrentSession` / `setSessions` update (match the just-appended entry by timestamp + `combinedComment`, or track a client-side temp key if needed).

**Why**: Local History list and job-queue cleanup must not wait on the network; `historyId` is only needed for later server-tied operations and can land a moment later.

### Decision 3: Confirm-button spinner must use `animate-spin`

**Choice**: While `isSaving` and the button is mounted, leading icon is `progress_activity` with `animate-spin` (same pattern as job processing / LATEST live badge). Label may stay `保存中...`. Document this under Application-Specific Patterns in `docs/UI-DESIGN.md`.

**Why**: Minimum bar from the bug report; glyph without spin reads as frozen. After optimistic clear the suggestions card unmounts — spinner obligation applies only while the button is still rendered; background save progress is communicated via toasts.

### Decision 4: Toast separation (avoid false “saved” before persist)

**Choice**: Do not show the old single “保存完了 / 修正内容が保存され、クリップボードにコピーされました” toast before APIs finish. Flow:

1. After successful copy + local commit: success toast that copy finished and server save is in progress (Japanese body copy).
2. After background success: “保存完了” (save-only wording).
3. After background failure: destructive toast that copy succeeded but save failed.

Prefer writing clipboard inside `saveCorrections` (or a `silent` option on `copyToClipboard`) so the generic copy toast does not stack awkwardly with the flow toasts.

### Decision 5: Double-submit + job timing unchanged in meaning

**Choice**: Keep `if (isSaving) return` / disabled button for the whole copy+background-save window. Record job review timing and remove the confirmed job on **local** commit (same relative ordering as today: timing read before `setConfirmingJobId(null)`), not after network success.

**Why**: Timing measures review work ending at confirm click, not server RTT. Double-submit must not create two history rows — `isSaving` spans the background persist.

## Risks / Trade-offs

- **[Risk] Background save fails after UI cleared** → User has clipboard content; show clear destructive toast; no automatic restore in this change (acceptable per Non-Goals). Mitigation: snapshot only for API payload; do not clear until copy succeeds.
- **[Risk] Race if user starts another round while `isSaving`** → Button disabled / early return; after clear, `canSave` is false until new selections exist, but `isSaving` still blocks a second persist.
- **[Risk] `historyId` patch misses the entry** → Prefer appending then updating the last matching entry in the same session’s `savedData`; keep patch logic tight and local.
- **[Trade-off] Brief spinner flash** if copy+local commit are near-instant and the card unmounts → Acceptable; toast covers background wait.

## Migration Plan

- Frontend-only deploy via usual Vercel git path; no DB migration.
- Rollback: revert `page.tsx` + `UI-DESIGN.md` (and this change’s OpenSpec artifacts if desired).

## Open Questions

None — preferred async-save architecture is fixed by the user request; spinner-only is the documented fallback only if implementation discovers an unsafe interaction with existing API/state (none identified).
