## 1. Badge semantics

- [x] 1.1 In `frontend/src/app/page.tsx`, replace `activeJobCount` (filter `processing`/`queued`) with `completedJobCount` (filter `status === 'completed'`)
- [x] 1.2 Wire the TopAppBar bell badge to render only when `completedJobCount > 0`, showing that count

## 2. Notification panel

- [x] 2.1 Add `bellPanelOpen` state (and a ref on the bell/panel wrapper for click-outside)
- [x] 2.2 Make the bell button toggle the panel; add Escape / outside-click to close
- [x] 2.3 Render an absolute panel under the bell listing `jobQueue` jobs with `status === 'completed'` (newest-first by `completedAt`/`queuedAt`): time, target-text snippet (~40 chars), completed status (`check_circle` + 「完了」), using MD3 tokens (`bg-surface`, `border-outline-variant`, etc.)
- [x] 2.4 Empty state copy when no completed jobs (Japanese body copy is fine)
- [x] 2.5 On list item click: call existing `confirmJob(job)`, then close the panel

## 3. Shake motion

- [x] 3.1 Confirm existing completion-path `setBellShake(true)` remains; do not add shake on enqueue/processing
- [x] 3.2 Leave `globals.css` `.bell-shake` as-is unless a restart edge-case needs a tiny tweak

## 4. Docs

- [x] 4.1 Update `docs/UI-DESIGN.md` TopAppBar / Bell Shake notes: badge = completed awaiting HITL; bell opens list; shake on completion (not active queue). Adjust the typography table `"N Active"` wording if it refers to this badge

## 5. Verify

- [x] 5.1 Sanity-check TypeScript/lint on touched files; manually trace generate → complete → badge/shake → bell list → confirmJob → save → badge decreases
