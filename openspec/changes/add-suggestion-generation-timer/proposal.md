## Why

Users have no visibility into how long an AI-suggestion generation round actually takes end-to-end — from clicking "Generate AI Suggestions" to finishing the review and clicking "確定してコピー・保存". This round-trip time is a useful signal for judging whether the cloud API, the WebLLM fallback, or the user's own review pace is the bottleneck. The user explicitly requested a live, always-visible timer for the most recent job plus a running average, placed at the right edge of the center editor pane, styled with the existing MD3 design tokens.

## What Changes

- Add a live-updating "most recent job" stopwatch display, in the center editor pane's header area (top-right of the Session Header row), that starts ticking the moment `handleGenerateClick`/`addJobAndProcess()` creates a new `QueuedJob` (using its existing `queuedAt` timestamp) and keeps ticking (updating once per second) until the user confirms and saves that same job via `saveCorrections()`'s `confirmingJobId` success path.
- Once a job is confirmed+saved via the `confirmingJobId` path, freeze that job's elapsed time as the "最新" (latest) completed-job duration, and roll it into a running average of all such recorded completions for the session (in-memory, capped history).
- Add an average-duration display (average across saved/confirmed jobs so far, this session) next to the latest-job display, using the same visual treatment.
- Both displays follow `docs/UI-DESIGN.md`'s existing MD3 tokens (typography, spacing, badge/metadata patterns) — no new colors or ad hoc styling are introduced.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: gains a new requirement describing the live per-job generation-to-save timer and running average displayed in the center pane's header, including what starts/stops the clock and what is (and is not) counted toward the average.

## Impact

- **Frontend code only**: `frontend/src/app/page.tsx` — a new small piece of client state for recorded job-completion durations, a `now`-tick `useEffect` for live updates while a job is in flight, a read at the exact point inside `saveCorrections()`'s `confirmingJobId` success branch (before the job is filtered out of `jobQueue`), and new JSX in the Session Header area.
- **No backend changes.**
- **No API contract changes.**
- **No database schema changes.**
- **No persistence changes**: this feature's state is intentionally session-lifetime only (not written to `localStorage`), unlike the existing Draft/JobQueue persistence patterns — see `design.md` for rationale.
