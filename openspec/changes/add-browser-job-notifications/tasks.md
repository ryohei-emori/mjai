# Tasks — add-browser-job-notifications

## 1. Notification module

- [x] 1.1 Add `frontend/src/lib/browserNotifications.ts` with `getNotificationPermission()`, `requestNotificationPermission()`, the pure `shouldShowBrowserNotification()` policy, and `showJobCompletedNotification()`
- [x] 1.2 Collapse "no Notification API" into the `'unsupported'` enum member so no caller branches on `typeof window`
- [x] 1.3 Tag each notification with its job id, and reuse `deriveCorrectionLabel` for the body text

## 2. Preference storage

- [x] 2.1 Add `BROWSER_NOTIFICATIONS_STORAGE_KEY = 'mjai-browser-notifications'` plus load/save helpers to `frontend/src/lib/uiPreferences.ts`, defaulting to off on unreadable storage

## 3. Wiring in the workspace

- [x] 3.1 Read the preference in the existing mount effect in `page.tsx`
- [x] 3.2 Add the toggle to the notifications panel: request permission from its change handler only, and render the unavailable/blocked states
- [x] 3.3 Fire the notification from `processJobAsync` on completion, gated by `shouldShowBrowserNotification`
- [x] 3.4 Route a notification click through `notificationJobId` state into an effect placed after `confirmJob`, tolerating a job that is no longer in the queue

## 4. Tests

- [x] 4.1 Unit-test `shouldShowBrowserNotification` across granted / denied / unsupported and visible / hidden
- [x] 4.2 Unit-test `getNotificationPermission` and `requestNotificationPermission` with the global absent, granted and denied
- [x] 4.3 Unit-test the preference load/save, including unreadable storage

## 5. Docs and verification

- [x] 5.1 Document the toggle, its states and the suppression rule in `docs/UI-DESIGN.md`
- [x] 5.2 `npm run lint`, `npm test`, `npm run build` in `frontend/`
