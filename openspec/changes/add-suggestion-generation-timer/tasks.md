## 1. Frontend: timing state and recording

- [x] 1.1 Add `type JobTimingRecord = { jobId: string; elapsedSeconds: number; completedAt: Date }` and `const [jobTimingHistory, setJobTimingHistory] = useState<JobTimingRecord[]>([])` near the other job-queue-related state in `frontend/src/app/page.tsx`
- [x] 1.2 In `saveCorrections()`'s `confirmingJobId !== null` success branch, before `setJobQueue(prev => prev.filter(j => j.id !== confirmingJobId))` runs, look up `jobQueue.find(j => j.id === confirmingJobId)`, compute `elapsedSeconds = (Date.now() - job.queuedAt.getTime()) / 1000`, and append a new `JobTimingRecord` to `jobTimingHistory` (capped to the most recent 50 entries)
- [x] 1.3 Verify the `confirmingHistoryIndex` branch and the "neither" (new-save) branch in `saveCorrections()` are left untouched (no timing recorded)
- [x] 1.4 In `handleSessionSwitch`, reset `jobTimingHistory` to `[]` when switching to a different session id (mirroring the existing `jobQueue` reset behavior on that path)

## 2. Frontend: live ticking

- [x] 2.1 Add `const [nowTick, setNowTick] = useState(() => Date.now())` near `jobTimingHistory`
- [x] 2.2 Add a `useEffect` keyed on `[jobQueue]` that starts a `setInterval(() => setNowTick(Date.now()), 1000)` when `jobQueue.some(j => j.status === 'queued' || j.status === 'processing')` is true, and clears it (returns a cleanup) otherwise/on unmount
- [x] 2.3 Derive the "latest active job" as the most-recently-queued job still `'queued'`/`'processing'` (max `queuedAt`), and compute its live `elapsedSeconds` from `nowTick` when present; otherwise fall back to the last entry in `jobTimingHistory`

## 3. Frontend: display formatting and UI placement

- [x] 3.1 Add a small formatting helper (e.g. `formatJobDuration(seconds: number) => \`${seconds.toFixed(1)}秒\``) local to `page.tsx`
- [x] 3.2 Compute the running average from `jobTimingHistory` (`reduce`/`length`) as a derived value, not extra stored state
- [x] 3.3 In the Session Header `<div className="flex items-center justify-between">` block, add a new flex group to the right of (or wrapping) the existing conditional `Saved: N` `Badge`, containing: a "LATEST" `text-label-caps` micro-label + duration `Badge` (with `animate-spin` `progress_activity` icon while live-ticking, `bg-surface-container text-on-surface-variant` while live, `bg-session-complete text-white` once frozen/completed), and an "AVG" micro-label + duration `Badge` (`bg-surface-container text-on-surface-variant`)
- [x] 3.4 Render a neutral placeholder (e.g. em dash `—`) for both values when `jobTimingHistory` is empty and no job is currently active
- [x] 3.5 Verify the new UI only uses existing Tailwind classes/tokens already present elsewhere in `page.tsx` (no new colors, no arbitrary values)

## 4. Verification

- [x] 4.1 Run `npm run lint` in `frontend/` and confirm no new errors introduced (note any pre-existing ones separately) — only pre-existing `layout.tsx` custom-font warning remains
- [x] 4.2 Run `npm run build` in `frontend/` and confirm no new errors introduced (note any pre-existing ones separately) — build succeeds with the same pre-existing warning only
- [x] 4.3 Manually trace through the code path (generate → confirm → save) to confirm the timer starts at job creation, keeps ticking, freezes at save, and the average updates — since this is a live-UI feature without existing automated frontend tests for `page.tsx`'s job queue flows, no new test file is added (consistent with the untested state of the surrounding job-queue code)

## 5. Planning artifacts

- [x] 5.1 Mark all tasks above complete as implemented
- [x] 5.2 Run `openspec validate --strict` (or repo-equivalent) on this change and fix any reported issues

## 6. Revision (2026-08): measure review-work time only (design.md Decision 7)

- [x] 6.1 Add `sessionId: string` to `QueuedJob`, set from `currentSession.id` in `addJobAndProcess`; backfill `sessionId: job.sessionId || sessionId` in `loadJobQueueFromStorage` for pre-existing persisted queues
- [x] 6.2 Add `isTabVisible` state + `visibilitychange` listener effect (Page Visibility API)
- [x] 6.3 Add `reviewAccumulatedMsRef` (`Map<jobId, ms>`) and `reviewSegmentStartRef` (`Map<jobId, ms>`) refs
- [x] 6.4 Derive `activeReviewJobId` (`confirmingJobId` gated on matching `job.sessionId === currentSessionId` and `isTabVisible`)
- [x] 6.5 Add segment open/close `useEffect` keyed on `[activeReviewJobId]` that folds elapsed ms into `reviewAccumulatedMsRef` on close and force-refreshes `nowTick` once so the display settles on the exact frozen total
- [x] 6.6 Retarget the 1s ticking `useEffect` from `jobQueue` activity to `activeReviewJobId`
- [x] 6.7 Add `getReviewElapsedSeconds(jobId)` helper (closed + live open segment, in seconds)
- [x] 6.8 Replace `saveCorrections()`'s `(Date.now() - queuedAt) / 1000` with `getReviewElapsedSeconds(timedJob.id)`, read before `setConfirmingJobId(null)`; delete both ref map entries for that job afterward
- [x] 6.9 Redefine `latestJobDurationSeconds`/`isLatestJobLive` derived values around `activeReviewJobId`/`getReviewElapsedSeconds` instead of `jobQueue` processing state; add `isReviewPaused` derived value
- [x] 6.10 Add a "paused" visual state to the LATEST badge (`pause_circle` icon, neutral background — distinct from both live-ticking and saved/complete) for when a job is under review but not currently accumulating time
- [x] 6.11 Verify `handleSessionSwitch`'s existing `jobTimingHistory` reset (Decision 2) is left as-is, and confirm the review-segment ref maps are deliberately *not* cleared there (see design.md Decision 7 "alternative considered" for why clearing them would lose in-progress segment data)
- [x] 6.12 Update `design.md` with Decision 7 and refreshed Risks section
- [x] 6.13 Run `npm run lint` and `npm run build` in `frontend/`, confirm no new errors
- [x] 6.14 Checked `frontend/src/lib/webllm/__tests__/` (WebLLM-internal unit tests only) and `frontend/src/app/__tests__/` (`apiError.test.tsx`, `authGuard.test.tsx` — both render `TextCorrectionApp` end-to-end but only cover WebGPU-unavailable/auth-guard rendering, not the job-queue/HITL confirm/save flow or timing); no existing test targets the job-timing logic specifically, so consistent with task 4.3's original note, no new test file is added for this revision either
