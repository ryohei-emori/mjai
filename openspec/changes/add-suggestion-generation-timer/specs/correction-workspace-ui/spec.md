## ADDED Requirements

### Requirement: Suggestion Generation-to-Save Timer and Running Average
The system SHALL display, at the right edge of the center session pane's header, a live "latest job" duration indicator and a running average duration, both measured from the moment the user clicks "Generate AI Suggestions" for a job to the moment that same job is confirmed and saved via "確定してコピー・保存". The latest-job indicator SHALL tick upward at least once per second while that job is still in progress (queued or processing), and SHALL freeze to the job's final elapsed duration once it is confirmed and saved. The running average SHALL be computed across all jobs timed this way during the current browser session (not persisted across page reloads), and SHALL update whenever a new job's duration is recorded.

Only the job-queue confirmation flow (confirming a completed job from the Job Queue panel, then saving) SHALL count toward this timer and average. Confirmations originating from restoring a prior execution-history entry, or saving without confirming a queued job, SHALL NOT be timed by this feature, since there is no corresponding "Generate AI Suggestions" click to measure from.

#### Scenario: Timer starts when a job is queued
- GIVEN the user has entered target text and clicks "Generate AI Suggestions"
- WHEN the resulting job is added to the job queue
- THEN the center pane's header begins showing a live, ticking duration for that job, updating at least once per second, starting from zero and counting up

#### Scenario: Timer keeps ticking through generation
- GIVEN a job's live duration is being shown in the center pane's header
- WHEN the job is still queued or processing (not yet completed and saved)
- THEN the displayed duration continues to increase in real time, reflecting elapsed time since that job was queued

#### Scenario: Timer freezes and average updates on confirm+save
- GIVEN a completed job from the Job Queue panel has been confirmed (loaded for review) and its live duration is ticking
- WHEN the user selects at least 3 proposals and clicks "確定してコピー・保存", and the save succeeds
- THEN the center pane's header shows that job's final elapsed duration as the latest completed duration, no longer ticking
- AND the running average duration shown alongside it is recalculated to include this job's duration

#### Scenario: History-retry confirmation does not affect the timer
- GIVEN the user restores a prior execution-history entry (not a job-queue job) and clicks "確定してコピー・保存"
- WHEN the save succeeds
- THEN neither the latest-job duration nor the running average is updated as a result of this save

#### Scenario: No jobs timed yet
- GIVEN the current session has not yet had any job confirmed and saved via the job-queue flow, and no job is currently queued or processing
- WHEN the center pane renders
- THEN the latest-job and average duration indicators show a neutral empty/placeholder state rather than a stale or zero duration

#### Scenario: Multiple concurrent jobs show the most recently started job's duration
- GIVEN two or more jobs are queued or processing concurrently
- WHEN the center pane's header renders the live "latest job" duration
- THEN it reflects the job that was most recently added to the queue (most recent "Generate AI Suggestions" click), not an older still-in-progress job

#### Scenario: Visual styling follows existing design tokens
- GIVEN the timer and average indicators are rendered
- WHEN inspecting their styling
- THEN they use only typography, spacing, color, and badge tokens already documented in `docs/UI-DESIGN.md` (e.g. `text-label-caps`, `text-metadata`, `bg-surface-container`, `bg-session-complete`), introducing no new ad hoc colors or styles
