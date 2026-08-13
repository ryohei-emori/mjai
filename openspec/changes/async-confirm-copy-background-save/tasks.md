## 1. Confirm button loading polish

- [x] 1.1 On the "確定してコピー・保存" button in `frontend/src/app/page.tsx`, apply `animate-spin` to the leading `progress_activity` icon whenever `isSaving` is true (match job-processing / LATEST spinner pattern)
- [x] 1.2 Briefly document the confirm-button loading pattern (`progress_activity` + `animate-spin`, disabled while in flight) in `docs/UI-DESIGN.md` under Application-Specific Patterns

## 2. Restructure `saveCorrections` for copy-first + background save

- [x] 2.1 Snapshot session fields / selected suggestions / confirming job|history indices before any clear; validate selection/text emptiness as today; set `isSaving` true
- [x] 2.2 Copy combined comment to clipboard first (avoid stacking a redundant generic copy toast if needed); on copy failure, keep UI uncleared and show the existing destructive copy-failure toast
- [x] 2.3 Apply local UI commit immediately after successful copy (append `SavedData` without waiting for `historyId`, clear target/suggestions/overallComment, hide custom form, reset selection counter, job-queue/history confirm side-effects including review timing + draft clear) and toast that copy succeeded / save is in progress
- [x] 2.4 Run `historyAPI.createHistory` + proposal creates using the snapshot; patch `historyId` onto the appended `SavedData` on success; toast save success or destructive “copy ok, save failed”; clear `isSaving` in `finally` after background work

## 3. Verify

- [x] 3.1 Manually sanity-check: with 3+ selections, click confirm — clipboard updates quickly, form clears, spinner shows while button mounted, save success toast follows; force a save failure path if feasible and confirm destructive toast without undoing copy
