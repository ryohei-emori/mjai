## Why

A generation takes seconds to a minute, and the user does something else while it runs — often in another tab or another window. The only signal that a round is ready for HITL review is the in-app bell: a badge and a shake animation that are invisible unless the MJAI tab is already on screen. So the user either watches a tab that has nothing to show yet, or comes back late.

The browser can deliver that signal outside the tab. Nothing in the app asks it to.

## What Changes

- Show a browser notification when a generation completes and is waiting for review, titled and worded in English.
- Ask for notification permission only from a deliberate user action — a toggle in the notifications panel — never on page load.
- Suppress the notification while the MJAI tab is the visible one; the bell already covers that case.
- Clicking a notification focuses the tab and opens that job's HITL review, the same flow as clicking the job in the queue or the bell.
- Persist the on/off preference in `localStorage` under `mjai-browser-notifications`, matching the existing flat `mjai-…` keys.
- Degrade cleanly: a browser without the Notification API, or with permission denied, leaves the in-app bell — count, ordering, shake — working exactly as before, and the toggle says why it is unavailable.

## Capabilities

### New Capabilities

None — this is a second delivery channel for a signal the workspace already produces.

### Modified Capabilities

- `correction-workspace-ui`: completion of a generation becomes notifiable outside the tab, under an explicit, revocable user preference.

## Impact

- New `frontend/src/lib/browserNotifications.ts` — permission reading/requesting, the suppression decision, and notification construction, kept pure enough to unit test
- `frontend/src/lib/uiPreferences.ts` — load/save for the new preference key
- `frontend/src/app/page.tsx` — the toggle in the notifications panel, the fire-on-completion call, and routing a notification click into the existing confirm flow
- New tests for the granted / denied / unsupported paths
- `docs/UI-DESIGN.md` — the toggle's placement and states
- No backend, API, schema or prompt changes
