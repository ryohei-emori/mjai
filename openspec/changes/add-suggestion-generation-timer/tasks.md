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
