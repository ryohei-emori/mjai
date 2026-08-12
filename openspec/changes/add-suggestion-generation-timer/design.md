## Context

See `proposal.md` for motivation. Relevant existing code in `frontend/src/app/page.tsx` (re-verified fresh at time of writing; two concurrent changes — `refine-suggestion-card-interactions` [done] and `highlight-suggestion-text-spans` — have also touched this file, so line numbers below are a snapshot, not a stable reference):

- `type QueuedJob` (~lines 68-78): has `queuedAt: Date` (set in `addJobAndProcess`, i.e. exactly when "Generate AI Suggestions" is clicked) and `completedAt?: Date` (set when AI generation finishes/fails, NOT when the user confirms+saves).
- `type PersistedQueuedJob` (~lines 132-135) plus `loadJobQueueFromStorage`/`saveJobQueueToStorage` (~lines 189-228): round-trip `queuedAt`/`completedAt` between `Date` and ISO string for `localStorage`.
- `addJobAndProcess(targetText)` (~lines 573-623): creates the `QueuedJob` with `queuedAt: new Date()` — this is the "start" event for timing.
- `confirmJob(job)` (~lines 879-940): loads a completed job's suggestions into `currentSession` and sets `confirmingJobId`; the job stays in `jobQueue` (status `'completed'`) at this point.
- `saveCorrections()` (~lines 1155-1329): has three success branches after `historyAPI.createHistory()` succeeds:
  1. `confirmingJobId !== null` (~1236-1267): job-queue confirm flow — `setJobQueue(prev => prev.filter(j => j.id !== confirmingJobId))` then `setConfirmingJobId(null)`, "確認完了" toast. **This is the literal "Generate AI Suggestions → 確定してコピー・保存" round-trip** the user described.
  2. `confirmingHistoryIndex !== null` (~1268-1286): history-retry confirm flow — marks an existing `savedData` entry `confirmed: true`. Not a `QueuedJob`-based flow at all; there is no `queuedAt` to measure from that corresponds to "clicking Generate AI Suggestions" for this data (it originates from `restoreFromHistory`, itself triggered from either a previously-saved-but-unconfirmed round or an old history entry, not a fresh generate click).
  3. Neither confirming variable set (~1287-1314): "new save flow" — also not gated on a `QueuedJob`.
- Session Header JSX (~lines 1732-1741): a `flex items-center justify-between` row with the session name/date on the left and a conditional `Saved: N` `Badge` on the right — this is the natural anchor point for "right edge of the center session pane" since it is already the topmost, full-width row of the center pane's content and already uses a left/right flex split.
- Existing timestamp formatting precedent: `job.queuedAt.toLocaleTimeString()` / `job.completedAt.toLocaleTimeString()` in the Job Queue panel (~line 1969) for wall-clock timestamps, and `formatElapsedTime()` (from `@/lib/webllm`, used in `AIDiagnosticsPanel` ~lines 299-303) for elapsed *durations* — e.g. `現在フェーズ: {formatElapsedTime(...)}`. `formatElapsedTime` operates on milliseconds and is the closest existing "duration formatting" convention in this codebase.

## Goals / Non-Goals

**Goals:**
- Live-tick a "latest job" duration display, in the center pane's header area, from the moment "Generate AI Suggestions" is clicked until that same job is confirmed+saved.
- Once a job completes that round-trip, freeze its final duration as "latest", and fold it into a running, session-lifetime average shown alongside it.
- Use only `docs/UI-DESIGN.md` MD3 tokens (typography, spacing, badge/metadata visual language) for the new UI.
- Keep the implementation additive and narrowly scoped: no changes to `QueuedJob`'s shape, no changes to existing persistence helpers, no backend changes.

**Non-Goals:**
- Persisting timer/average history across page reloads (`localStorage`) — deliberately out of scope, see Decision 2 below.
- Counting `confirmingHistoryIndex` (history-retry) or the plain "new save" confirmation path toward this timing feature — only the `confirmingJobId` (job-queue confirm) path counts, see Decision 1.
- Any backend change, API contract change, or database schema change — this is a pure frontend, client-state UX feature.
- General job-analytics/reporting (e.g. per-job history list, min/max, export) — only "latest" + "average" as explicitly requested.
- Adding new design tokens to `docs/UI-DESIGN.md`/`tailwind.config.js` — every visual element reuses an existing token (see Decision 4).

## Decisions

### 1. Only the `confirmingJobId` (job-queue confirm) path counts toward timing

**Choice**: Elapsed time is recorded only inside `saveCorrections()`'s first success branch (`confirmingJobId !== null`), computed as `(Date.now() - job.queuedAt.getTime()) / 1000` where `job = jobQueue.find(j => j.id === confirmingJobId)`, read *before* the existing `setJobQueue(prev => prev.filter(j => j.id !== confirmingJobId))` line removes it. The `confirmingHistoryIndex` branch and the "neither" (new-save) branch are left untouched — no timing is recorded for them.

**Rationale**: The user's request is specifically "Suggestionsを押したら時間計測を開始し...保存をおすまでの時間" — the literal button-press-to-save round trip. Only the job-queue flow has a `queuedAt` timestamp that corresponds to an actual "Generate AI Suggestions" click for the data being saved. The history-retry flow re-opens older, already-generated (and possibly previously-saved-but-unconfirmed) data via `restoreFromHistory`, which has no "just clicked Generate" starting point — attributing a duration to it would be measuring "how long the user took to click restore-then-confirm", a fundamentally different and less meaningful number. The "new save" branch (neither confirming variable set) is reachable when the user manually builds up `suggestions` via `addCustomCorrection` without ever going through a `QueuedJob` at all (no `queuedAt` exists to measure from in the general case).

**Alternative considered**: Also time the `confirmingHistoryIndex` path by using that `SavedData`'s own `timestamp` field as a proxy start time. Rejected: `SavedData.timestamp` is set at save time, not generation time, so this would measure "0 seconds" or a nonsensical past-vs-past delta, not a real duration — there is no reliable start event for this path today.

### 2. Timing history state: session-lifetime `useState`, not `localStorage`-persisted

**Choice**: A small piece of state, scoped per session like the existing `jobQueue`/drafts (i.e. cleared/reset — or more precisely, not loaded — whenever the user switches sessions, since duration history is a live productivity indicator, not saved data), holding:

```ts
type JobTimingRecord = { jobId: string; elapsedSeconds: number; completedAt: Date }

const [jobTimingHistory, setJobTimingHistory] = useState<JobTimingRecord[]>([])
```

capped to the most recent 50 entries (simple array push + slice, no need for a ring buffer at this scale) to bound memory for a long-running tab session. "Latest" is derived as `jobTimingHistory[jobTimingHistory.length - 1]`; "average" is derived as `jobTimingHistory.reduce((sum, r) => sum + r.elapsedSeconds, 0) / jobTimingHistory.length`. Both are simple derived reads, not additional stored fields — no separate running-average accumulator is needed at this scale (≤50 numbers to sum is trivial cost per render).

**Not persisted to `localStorage`**: unlike `PersistedDraft`/`PersistedQueuedJob`, this state is not written to or restored from `localStorage`, and no `PersistedJobTimingRecord` ISO-string variant is introduced.

**Rationale**: This is explicitly a "nice-to-have live indicator" per the task, not data with any downstream consumer (it is never sent to the backend, never shown in `History`/`SavedData`). The existing persistence patterns (`PersistedDraft`, `PersistedQueuedJob`) exist because losing unsaved *work* (draft text, in-flight jobs) on an accidental reload is a real cost to the user; losing a stopwatch reading on reload is not — the user simply keeps generating and the average rebuilds. Adding persistence would also require solving "which session does a `JobTimingRecord` belong to" and a `Persisted...`/round-trip pair purely for a display-only convenience metric, which is disproportionate complexity for the value delivered.

**Alternative considered**: Persist to `localStorage` per session, mirroring `JOB_QUEUE_STORAGE_PREFIX`. Rejected per the task's own recommendation and the reasoning above; revisit only if user feedback specifically asks for cross-session history/reporting, at which point this would likely deserve a proper backend-persisted analytics feature rather than a `localStorage` shim.

**Per-session scoping detail**: Since `jobTimingHistory` is not persisted or keyed by session id, switching sessions via `handleSessionSwitch` naturally leaves stale numbers from a previous session visible until the next generate/save cycle. This is judged acceptable (the indicator is explicitly documented as a live, transient aid, not scoped data), but for a cleaner experience the `handleSessionSwitch` callback also resets `jobTimingHistory` to `[]` when switching to a *different* session id (mirroring how it already resets `jobQueue` on the "active jobs" confirmation path) — this keeps the display's numbers meaningfully tied to "this session's" generation activity without adding persistence.

### 3. Live "ticking" via a single shared `now` tick state, reusing the existing tick-while-active pattern

**Choice**: Add one `const [nowTick, setNowTick] = useState(() => Date.now())` plus a `useEffect` that starts a `setInterval(() => setNowTick(Date.now()), 1000)` whenever there is at least one job in `jobQueue` with status `'queued'` or `'processing'` that was started via the counted (`addJobAndProcess`) path, and clears the interval otherwise:

```ts
useEffect(() => {
  const hasActiveJob = jobQueue.some(j => j.status === 'queued' || j.status === 'processing')
  if (!hasActiveJob) return
  const intervalId = setInterval(() => setNowTick(Date.now()), 1000)
  return () => clearInterval(intervalId)
}, [jobQueue])
```

The "latest job, in progress" display then computes `elapsedSeconds = (nowTick - latestActiveJob.queuedAt.getTime()) / 1000` on every render while ticking, where `latestActiveJob` is the most-recently-queued job still in `'queued'`/`'processing'` state (`jobQueue` sorted by `queuedAt` descending, first match) — falling back to the last completed `JobTimingRecord` when no job is active.

**Rationale**: This directly mirrors the existing "Periodic timer updates during WebLLM processing" `useEffect` (~lines 440-459 in `page.tsx`), which already starts/stops a `setInterval` keyed on active-state and re-reads a timestamp-derived value every tick — same pattern, new trigger condition (`jobQueue` activity instead of `webllmStatus.state`), same 1-second-appropriate cadence for a human-readable stopwatch (the WebLLM panel ticks every 100ms because it's tracking sub-second phase transitions during generation; this is a coarser, seconds-resolution UX indicator per the task's explicit "1秒ごとに更新" style example, so 1000ms is used instead of reusing the 100ms constant).

**Alternative considered**: Compute elapsed time via `Date.now()` directly inside the render body without a `nowTick` state, relying on some other frequently-re-rendering state to drive updates. Rejected: there is no guarantee some other state changes every second while a job is in flight (e.g. a long API call has no intermediate re-renders), so the display would appear frozen without an explicit ticking mechanism.

### 4. Placement: new flex item in the Session Header row, not an absolutely-positioned overlay

**Choice**: Add the timer/average display as a new sibling inside the existing Session Header `<div className="flex items-center justify-between">` (~lines 1732-1741), to the right of the existing conditional `Saved: N` badge, inside a small `flex items-center gap-3` wrapper alongside it — i.e. it becomes part of the same right-aligned flex group as the Saved badge, not a new top-level row or an `absolute`-positioned corner element.

```
[Session Name / created date]  ...................  [最新: 12.3秒] [平均: 9.8秒] [Saved: N]
```

This satisfies "センターのセッションの右端側" (right edge of the center session pane) precisely: the Session Header is the full-width top row of the center pane's content (`<main>`), and `justify-between` already pushes its second child to the pane's right edge — extending that existing right-side flex group is the natural, layout-consistent choice already established by the `Saved: N` badge, versus inventing a new absolutely-positioned overlay that would need its own z-index/scroll-behavior handling and could visually collide with the resizable pane divider immediately to its right.

**Alternative considered**: A fixed/sticky overlay pinned to the top-right of the center `<main>` element (`position: absolute` or `sticky`). Rejected: `<main>` is `overflow-y-auto` (scrolls independently), so a `sticky` element would need extra top-offset/z-index tuning to avoid overlapping the Source/Target Text cards as the user scrolls, and an `absolute` element would need to escape the `space-y-6` flow container. The header-row flex item avoids all of this by using normal document flow that already renders once, at the top, and never scrolls out of the initial viewport in the common case (the header is the first element in the pane).

### 5. Display format: `X.X秒` (one decimal place) while ticking, same format once frozen

**Choice**: Format both the live "latest (in progress)" value and the frozen "latest completed" / "average" values as `${elapsedSeconds.toFixed(1)}秒` (e.g. `12.3秒`, `9.8秒`). Average is computed in seconds and formatted the same way.

**Rationale**: `docs/UI-DESIGN.md` does not document a duration-formatting convention (only wall-clock `toLocaleTimeString()` for timestamps, e.g. Job Queue's `job.queuedAt.toLocaleTimeString()`). The closest *duration* precedent, `formatElapsedTime()` (`frontend/src/lib/webllm`), formats milliseconds for sub-second-resolution diagnostic display (e.g. `"1.2s"` / `"850ms"`-style output tuned for very short WebLLM phase timings) — not a natural fit for round-trip durations that will typically span single-digit-to-low-double-digit seconds or occasionally minutes. Given the task's own suggested example (`X.X秒`) and that most round-trips will be seconds-to-tens-of-seconds (well within Groq/Cloudflare/WebLLM's documented latency ranges in `AGENTS.md`), a simple one-decimal seconds format is the clearest, most consistent choice; no MM:SS is introduced since durations are not expected to routinely exceed ~99.9 seconds, and MM:SS would be harder to skim at a glance for short jobs than `N.N秒`.

**Alternative considered**: Reuse `formatElapsedTime()` from `@/lib/webllm` directly (already imported in `page.tsx`) by passing `elapsedSeconds * 1000`. Rejected: that helper's output format is tuned for the AI Diagnostics Panel's sub-second/phase-timing display, not for a simple stopwatch/average badge; introducing a second call site with different expectations (whole round-trip duration vs. phase duration) risks inconsistent-looking output (e.g. unexpected `ms` suffixes for the common case) for no benefit over a direct one-line `toFixed(1)` format. If a future change wants full duration-formatting consistency across the app, unifying these would be a reasonable follow-up, but is not required here.

### 6. Visual styling: reuse `Badge`/`text-metadata`/`text-label-caps` tokens, no new colors

**Choice**: Render each of the two values (latest, average) as a small labeled pair using existing tokens only:
- A `text-label-caps text-on-surface-variant` micro-label ("LATEST" / "AVG", English-primary per the "brutalist legibility" bilingual convention already used for SOURCE/TARGET TEXT headers) followed by
- The formatted duration in a `Badge` using `bg-surface-container text-on-surface-variant` (neutral, matching the existing "Job Queue" queued-status badge look — see `bg-surface-container border-outline-variant` job cards) while a job is in progress, switching to `bg-session-complete text-white` (the existing "saved/complete" session-status color, already used for the `Saved: N` badge and completed-job cards) once the latest value reflects a *completed* (saved) job rather than a live in-progress tick.
- A small `progress_activity` Material Symbol with `animate-spin` (reusing the existing spinner icon/pattern from `AIDiagnosticsPanel`/Job Queue processing rows) next to the "latest" value specifically while it is live-ticking, to visually distinguish "still running" from "frozen/final" without needing a new color.

No new CSS custom properties, Tailwind theme extensions, or one-off hex/HSL values are introduced — every class used already exists in `tailwind.config.js`/`globals.css` per `docs/UI-DESIGN.md`.

**Alternative considered**: Introduce a dedicated new "timer" accent color (e.g. distinct from `session-active`/`session-complete`) to make the stopwatch visually unique. Rejected: `docs/UI-DESIGN.md`'s existing `session-active`/`session-complete`/`session-empty` triad already covers "in progress" vs "done" semantics app-wide (job queue cards, session badges); reusing them keeps the new UI visually consistent with, rather than competing against, that established vocabulary, per the task's explicit instruction to reuse existing tokens rather than hardcode arbitrary styling.

### 7. Revision (2026-08): measure review-work time only, not raw generate-to-save wall-clock time

**Context**: After shipping Decisions 1-6 above, user feedback (verbatim, Japanese): "あ、あと計測時間は、うまいこと実際にユーザーがそのセッションのそのジョブで作業をしている時間についてのみ計測するようにしてください" — "please cleverly make sure the measured time only counts the time the user is actually working on that job in that session." The original Decision 1 formula, `(Date.now() - job.queuedAt.getTime()) / 1000`, measures the *entire* span from "Generate AI Suggestions" click to "確定してコピー・保存" click, which — given `MAX_CONCURRENT_API_JOBS = 30` (parallel job processing is a deliberate throughput feature so users are not meant to wait idly) — mostly measures AI-processing time and background queue-wait time while the user is doing something else (reviewing a different job, editing another session, or away from the tab entirely), not actual review work. This revision changes what is measured without changing the overall UX contract established by Decisions 1-6 (still `confirmingJobId`-gated, still session-lifetime `useState`, still a header-row live badge, still `X.X秒` format, still reused MD3 tokens).

**Choice**: Track "review segments" per job — a segment is open only while the user is plausibly looking at that job's HITL review UI — and sum segment durations instead of using raw `queuedAt`-to-save elapsed time.

A review segment for `job` is open exactly when all three hold:
1. `confirmingJobId === job.id` (the user has clicked "確認" on this job and its suggestions are loaded for review — unchanged gating condition from Decision 1).
2. `job.sessionId === currentSessionId` (see sub-decision "Session-switch reachability" below).
3. `document.visibilityState === 'visible'` (Page Visibility API; the tab is the active, foreground tab).

Implementation:
- **`QueuedJob` gains a `sessionId: string` field**, set from `currentSession.id` at `addJobAndProcess()` time. `loadJobQueueFromStorage()` backfills `sessionId: job.sessionId || sessionId` (the storage key's own session id) for records persisted before this field existed, so existing `localStorage` job queues don't break.
- **`activeReviewJobId`** is a derived value (recomputed every render, not stored state): `confirmingJobId` if the three conditions above hold, else `null`.
- **Two refs**, not state (so mutating them never itself triggers a re-render — only paired `setState` calls, described below, do):
  - `reviewAccumulatedMsRef: Map<jobId, number>` — total milliseconds from all *closed* segments for that job.
  - `reviewSegmentStartRef: Map<jobId, number>` — `Date.now()` epoch ms at which the *currently open* segment for that job started (absent if no segment is open for that job).
- **One `useEffect(() => {...}, [activeReviewJobId])`** opens a segment (`reviewSegmentStartRef.set(jobId, Date.now())`) when `activeReviewJobId` becomes a given job id, and its cleanup — which fires when `activeReviewJobId` changes away from that id (tab hidden, `confirmingJobId` moved to another job/`null`, or session switched away) or on unmount — closes it by folding the elapsed ms into `reviewAccumulatedMsRef` and deleting the `reviewSegmentStartRef` entry. This is the same "start/stop keyed on a dependency-array value" shape as the pre-existing WebLLM diagnostics timer (`page.tsx`'s `activeStates`-gated `setInterval` effect) and Decision 3's original ticking effect, just retargeted from `jobQueue` activity to `activeReviewJobId`. The cleanup also calls `setNowTick(Date.now())` once, purely so the display re-renders with the freshly closed, exact total immediately (ref mutations alone don't trigger renders).
- **A second `useEffect(() => {...}, [activeReviewJobId])`** runs the visible 1-second `setInterval(() => setNowTick(...), 1000)` ticker only while a segment is open — replacing Decision 3's `jobQueue`-activity-gated interval (which ticked during AI processing, no longer meaningful here) with one gated on active *review*.
- **`getReviewElapsedSeconds(jobId)`** (a `useCallback` keyed on `[nowTick]`) returns `(closed accumulated ms + live open-segment ms, if any) / 1000` — the single source of truth used both for the live "LATEST" display and for the final value recorded into `jobTimingHistory` at save time.
- **At save time** (`saveCorrections()`'s `confirmingJobId !== null` branch), `elapsedSeconds = getReviewElapsedSeconds(timedJob.id)` replaces the old `(Date.now() - timedJob.queuedAt.getTime()) / 1000`, read *before* `setConfirmingJobId(null)` (so the still-open segment, if any — the save button is clicked from within the open review UI, so a segment is open in the overwhelmingly common case — is included). The two ref map entries for that job are then deleted (bounds memory; a saved job's timing is now fully captured in `jobTimingHistory`).

**Rationale for Page Visibility over a heuristic (e.g. `requestIdleCallback`, mouse/keyboard activity)**: The task explicitly calls out `document.visibilityState`/`visibilitychange` as the mechanism, and it precisely captures the one unambiguous "definitely not working on this" signal (backgrounded tab) without the false-positive risk of activity-based idle detection (a user reading a long suggestion list without touching the mouse for 30s is still working, but naive idle detection could wrongly pause the timer).

**Sub-decision: reachability of "switch sessions without `confirmingJobId` changing"** — Investigated whether the UI can leave `confirmingJobId` pointing at a job while `currentSessionId` changes. Confirmed **yes, reachable**: `handleSessionSwitch()` never resets `confirmingJobId` on a plain switch (only `saveCorrections()` does, on successful save) — it is only synced from a per-session persisted Draft's `confirmingJobId` field the *first* time a given session is opened in a browser tab (`restoredDraftSessionIdsRef`). Since the AI Suggestions review panel itself renders `currentSession.suggestions` (a per-`Session` field, not global), switching sessions while `confirmingJobId` is non-null typically makes the review panel disappear from view entirely (the newly-active session's own, usually-empty `suggestions`) even though `confirmingJobId` is still technically set to the old job's id — exactly the "user has navigated away without an explicit close" case the task asked to handle. Adding `job.sessionId` (rather than a separately-tracked "which session was I reviewing in" piece of state) makes this self-correcting: if the user switches back to the original session later, `job.sessionId === currentSessionId` becomes true again automatically and the segment resumes — correctly treating this as one more pause/resume cycle rather than requiring separate bookkeeping that could drift out of sync with `confirmingJobId`.

**Alternative considered (rejected): clearing `reviewAccumulatedMsRef`/`reviewSegmentStartRef` on every session switch, mirroring `jobTimingHistory`'s reset (Decision 2)**. Tried first, then reverted: `handleSessionSwitch()` runs synchronously and would clear the maps *before* the `activeReviewJobId`-keyed effect's cleanup gets a chance to run (effects run after the render commit that reacts to the state change), so the in-progress open segment's elapsed time would be silently discarded instead of properly folded into the accumulated total — a data-loss bug, not a deliberate trade-off. Leaving the two ref maps alone on session switch is both simpler and strictly more correct: the segment-lifecycle effect always closes out an open segment properly on its own, and preserving the accumulated total across a temporary session excursion is exactly the "multiple pause/resume cycles" robustness the task asked for. (`jobTimingHistory` itself, a `useState`, is unaffected by this and still resets per Decision 2 — that is a distinct, deliberate "this is a session-scoped display metric" choice, not a mechanism for cleaning up in-flight segment bookkeeping.)

**Redefinition of "LATEST"**: Previously the live elapsed time of the most-recently-`queuedAt` `queued`/`processing` job (a proxy that no longer makes sense once queue/processing time isn't counted). Now: while `confirmingJobId` is set, LATEST live-displays `getReviewElapsedSeconds(confirmingJobId)` — ticking only while `activeReviewJobId === confirmingJobId` (tab visible, matching session), otherwise frozen at its last value with a paused visual state (see below); once `confirmingJobId` returns to `null` (job saved, or no job ever reviewed yet this session), LATEST shows the most recent entry in `jobTimingHistory` (the frozen, final review time of the last *saved* job), same as before.

**New visual state: "paused"**: A job can now be "under review but not currently accumulating time" (tab hidden, or the user switched to a different session while this job's review was still open) — a third state beyond the pre-existing "live/ticking" and "frozen/complete". Reusing `bg-session-complete` (green, meaning "saved") for this would misleadingly imply the job had been saved when it has not. Instead, paused state keeps the neutral `bg-surface-container` badge background (same as live) but swaps the `progress_activity` spin icon for a static `pause_circle` Material Symbol — communicating "still in progress, temporarily not counting" without introducing a new color token (`docs/UI-DESIGN.md` token-reuse constraint from Decision 6 still holds — `pause_circle` is a Material Symbols Outlined glyph, and the codebase already relies on that same icon font, so no new asset is added).

**AVG unchanged**: Still the simple average of `jobTimingHistory.elapsedSeconds` (Decision 2's formula). The values it averages now represent pure review-work time instead of generate-to-save wall-clock time, but the aggregation itself needed no change — averaging is agnostic to what each individual "elapsedSeconds" represents.

**Explicitly not handled** (documented, not oversights):
- **Multiple tabs/windows open to the same session simultaneously**: `document.visibilityState` is per-tab; if a user has two tabs open to the same session, one visible and one hidden, review-time bookkeeping (the two ref `Map`s, `confirmingJobId`, `jobQueue`) is independent in-memory state per tab (`jobQueue`/drafts are persisted to `localStorage` but read once per session-visit, not live-synced across tabs), so the two tabs' timers do not coordinate. This is consistent with the rest of the app's existing single-tab-authoritative assumptions (e.g. `restoredDraftSessionIdsRef`, debounced `localStorage` writes) and is out of scope for this revision.
- **System sleep / laptop lid close while tab is visible and foregrounded**: `visibilitychange` does not reliably fire for this on all platforms/browsers; the open segment would keep "running" across the sleep gap, minutely overcounting. Judged low-impact/rare enough (and consistent with the existing 1-second/one-decimal precision bar set in Decision 5) not to add a `requestAnimationFrame`-drift-detection or `navigator.wakeLock` heuristic for.
- **Rapid open/close/re-open cycles (e.g. double-clicking 確認 on two different jobs in quick succession)**: handled correctly by construction — each `activeReviewJobId` transition deterministically closes exactly one segment (if any was open) and opens exactly one new one via the same effect's dependency-array-triggered cleanup/setup pair; React may batch multiple synchronous state updates into a single commit (skipping intermediate `activeReviewJobId` values entirely without ever running an effect for them), which only avoids spurious near-zero-length segments rather than causing any double-counting.

## Risks / Trade-offs

**[Risk] `jobTimingHistory` is not persisted, so a page reload mid-session loses the average** → Accepted trade-off, per Decision 2 — this is a documented, deliberate scope boundary, not an oversight.

**[Risk] The 1-second tick interval adds one more `setInterval` to a component that already runs one for WebLLM diagnostics** → Mitigation: the new interval is gated identically (only runs while a review segment is open, i.e. `activeReviewJobId` is non-null — updated in the Decision 7 revision from the original "`jobQueue` has an active entry" gate) and is cleared via the same `useEffect` cleanup pattern already proven correct for the existing WebLLM timer; the two intervals are independent and do not interact.

**[Risk] (Superseded by Decision 7) Multiple concurrent API jobs (`MAX_CONCURRENT_API_JOBS = 30`) mean "the most recently queued active job" is not necessarily "the job the user is about to confirm next"** → No longer applicable: LATEST no longer tracks queue/processing activity at all post-Decision-7, only the job actually open for HITL review (`confirmingJobId`), so there is no ambiguity about which of many concurrently-processing jobs is being displayed.

**[Risk] Switching sessions resets `jobTimingHistory`, so a user bouncing between two sessions loses the "average" context for the one they're not currently on** → Accepted trade-off, consistent with Decision 2's "session-lifetime, not cross-session analytics" scope; the numbers are meant to reflect "how is this session's generation loop going right now", not lifetime stats. (Note: per Decision 7, this reset intentionally does *not* extend to the in-flight review-segment ref maps — see Decision 7's "alternative considered" for why clearing those on switch would be a correctness bug rather than a consistent extension of this trade-off.)

**[Risk] (New, Decision 7) `visibilitychange` does not fire for system sleep/lid-close, so a segment left open across a sleep gap overcounts by the sleep duration** → Accepted trade-off, see Decision 7's "explicitly not handled" list; judged rare and low-impact relative to the feature's existing seconds-resolution precision bar.

## Migration Plan

No data migration. Purely additive frontend client state and JSX; no schema, API contract, or environment-variable changes. Ships as a normal deploy. No feature flag needed — the new display simply shows nothing (or a neutral "—") until the first job in the current session is queued/completed.
