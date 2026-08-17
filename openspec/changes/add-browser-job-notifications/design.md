# Design — add-browser-job-notifications

## Context

The workspace already has a completion event with everything a notification needs: `processJobAsync` marks a job `completed`, triggers the bell shake, and knows the job id and its target text. What is missing is a second delivery channel and a policy for when firing it is welcome rather than obnoxious.

Browser notifications are the classic example of a feature that is trivial to call and easy to get wrong: prompt on load and the user blocks the origin forever; fire while they are looking at the tab and the notification is noise; fire without a click handler and it is a dead end.

## Decision 1 — Permission is requested from the toggle, never from load or completion

A permission prompt the user did not ask for is the fastest way to a permanently denied origin, and denial is not recoverable from within the page. So:

- **Never** call `Notification.requestPermission()` in an effect, on session load, or when a job completes.
- The only call site is the toggle's change handler in the notifications panel — a real user gesture, in the one place in the UI that is already about notifications, where the user's intent is unambiguous.
- If the user turns the toggle on and then refuses the prompt, the preference does not flip on. A stored "on" that can never fire would be a lie, and it would keep the toggle looking correct while nothing arrived.

The toggle lives inside the bell dropdown rather than in the (prompt-owned) settings dialog: the dropdown is what the user opens when thinking about notifications, and it means the control is discovered next to the thing it changes.

## Decision 2 — Keep the policy in a pure module, keep `Notification` at one call site

`frontend/src/lib/browserNotifications.ts` holds the whole feature, following the shape of `lib/uiPreferences.ts` (pure decision functions, storage access wrapped in `try`/`catch`):

| Export | Responsibility |
|---|---|
| `getNotificationPermission()` | `'granted' \| 'denied' \| 'default' \| 'unsupported'` — collapses "no API" into the same enum so callers never branch on `typeof window` |
| `requestNotificationPermission()` | Resolves to the same enum; returns `'unsupported'` instead of throwing |
| `shouldShowBrowserNotification({ enabled, permission, documentVisibility })` | The whole policy as one pure boolean, unit-testable without a DOM |
| `showJobCompletedNotification({ label, jobId, onActivate })` | The single place that constructs a `Notification`; returns `null` when it cannot |

`shouldShowBrowserNotification` being pure is the point: the three interesting paths (granted / denied / unsupported) and the visibility suppression are decided by a function that takes plain values, so the tests do not need a fake `Notification` constructor to cover them. Only the last export needs a stub.

`'unsupported'` as an enum member rather than a separate `isSupported()` predicate keeps every caller on one exhaustive switch, and makes the "no API" path structurally identical to "denied" — which is how it must behave.

## Decision 3 — Suppress while the tab is visible

`document.visibilityState === 'visible'` means the bell shake and badge are already on screen, and a second signal for the same event is noise. Visibility is read at fire time, not tracked in state: the app already keeps an `isTabVisible` state for the review timer, but that exists to pause a stopwatch and reading it here would couple two unrelated policies through a state variable that could lag a tick.

Note the deliberate asymmetry: hidden means "hidden or in a background tab or minimised", which is exactly the set of situations where the user cannot see the bell.

## Decision 4 — A click routes through the existing confirm flow, via state rather than a captured callback

The notification must open the same HITL review that clicking the job does. `confirmJob` is defined well after `processJobAsync` in `page.tsx` and closes over the current session, so capturing it inside the notification's `onclick` would either be a forward reference or a stale closure.

Instead the click sets `notificationJobId`, and an effect placed after `confirmJob` consumes it:

```
onclick → window.focus(); setNotificationJobId(id)
effect([notificationJobId, jobQueue, confirmJob])
  → find the job, still completed, in the current queue
  → clear the state, call confirmJob(job)
```

This reads the job from the live queue rather than from a snapshot taken when the notification was created, so a job whose proposals were persisted (and whose ids were rewritten) in the meantime is confirmed with its current data. If the job is gone — session switched, queue cleared — the effect simply finds nothing and the tab is left as it was, which is the behaviour the spec asks for.

`window.focus()` is best-effort: browsers vary in whether a notification click can raise a window. The important half is that the app is in the right state once the user gets there.

## Decision 5 — `tag` per job, so a queue of 30 does not become 30 stacked notifications

Each notification is tagged with its job id. Re-firing for the same job replaces rather than stacks, and distinct jobs still each get one — the app allows up to 30 concurrent API generations, and collapsing them all under one tag would hide everything but the last. `requireInteraction` is left off: the notification is a nudge, not a modal.

The body text reuses `deriveCorrectionLabel`, the same helper the job card and bell row use, so the three surfaces name a round identically.

## Decision 6 — Preference storage matches the existing keys

`mjai-browser-notifications`, `'1'` / `'0'`, in `lib/uiPreferences.ts` beside `mjai-session-pane-mode` and `mjai-exemplar-card-open`. Default off, and anything unreadable reads as off — for this preference "off" is also the privacy-preserving default, and an unreadable value cannot imply consent.

Read in a mount effect, never during render, so SSR and the first client render agree — the constraint already documented for the other preferences.

## Risks / Trade-offs

- **Permission cannot be re-requested after denial.** Inherent to the platform. The toggle therefore reports "blocked in browser settings" rather than pretending a retry will help.
- **Cooldown/permission state is per browser profile.** Nothing is synced; a user with two browsers enables it twice. Acceptable for a single-user app.
- **jsdom has no `Notification`.** Which is why the policy is a pure function: the unsupported path is the default test environment, and the granted/denied paths are covered by stubbing the global for those cases only.
