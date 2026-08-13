## Why

The TopAppBar notification bell already shakes when a job completes, but its badge still counts **active** (`queued`/`processing`) jobs and the bell itself is not clickable. Users need a clear signal for **completed jobs awaiting HITL review**, plus a one-click path into the same confirm flow as the Job Queue panel.

## What Changes

- **Badge semantics**: Count `status === 'completed'` jobs in the current session's job queue (awaiting confirm/save), not active queue depth.
- **Bell click → notification list**: Open a lightweight panel/dropdown listing those completed-but-unconfirmed jobs (time, target-text snippet, status). Empty state when none. Item click calls existing `confirmJob` / HITL flow and closes the panel.
- **Shake motion**: Keep the existing completion-triggered shake (already wired on job complete). Do not shake on enqueue/active-count changes. No over-animation.
- **Docs**: Briefly update `docs/UI-DESIGN.md` so badge/bell behavior matches the new semantics.
- No backend/API changes. No change to Job Queue panel behavior beyond reuse of `confirmJob`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `correction-workspace-ui`: TopAppBar notification bell badge meaning, click-to-list of completed-unconfirmed jobs, and shake trigger semantics (completion events only).

## Impact

- `frontend/src/app/page.tsx` — badge count, bell click handler, notification panel UI, reuse of `confirmJob`
- `frontend/src/app/globals.css` — shake CSS already exists; no change expected unless wiring needs a class tweak
- `docs/UI-DESIGN.md` — document badge = completed-awaiting-HITL; clarify shake on completion
- Unrelated planning-only change `add-optional-exemplar-translation-input` is left untouched
