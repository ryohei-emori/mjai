## ADDED Requirements

### Requirement: TopAppBar Bell Shows Completed-Awaiting-HITL Count
The TopAppBar notification bell badge SHALL display the number of jobs in the current session's job queue whose status is `completed` (AI generation finished, awaiting human confirm/save). The badge MUST NOT count `queued`, `processing`, or `failed` jobs. When the completed count is zero, the badge SHALL be hidden.

#### Scenario: Badge counts completed jobs only
- **GIVEN** the current session job queue contains 2 `processing` jobs and 3 `completed` jobs
- **WHEN** the TopAppBar renders
- **THEN** the notification bell badge shows `3`

#### Scenario: Badge hidden when no completed jobs
- **GIVEN** the current session job queue has only `queued`/`processing` jobs, or is empty
- **WHEN** the TopAppBar renders
- **THEN** no numeric badge is shown on the notification bell

#### Scenario: Badge decreases after confirm and save
- **GIVEN** a completed job is awaiting review and the badge includes it
- **WHEN** the user confirms that job and successfully saves via "確定してコピー・保存" (removing it from the queue)
- **THEN** the badge count decreases by one (or hides if none remain)

### Requirement: Bell Opens Completed-Job Notification List
Clicking the TopAppBar notification bell SHALL open a panel (dropdown/popover) listing completed-but-unconfirmed jobs for the current session. Each item SHALL show a wall-clock time, a short snippet of the job's target text, and a completed status indicator. Clicking an item SHALL start the same HITL confirm flow as clicking that job in the Job Queue panel (load suggestions for review). When there are no completed-unconfirmed jobs, the panel SHALL show an empty state. The panel SHALL use existing MJAI MD3 / brutalist design tokens (no new purple/glow aesthetic).

#### Scenario: Open list of completed jobs
- **GIVEN** one or more completed jobs exist in the current session job queue
- **WHEN** the user clicks the notification bell
- **THEN** a panel opens listing those jobs with time, target-text snippet, and completed status

#### Scenario: Item click triggers HITL confirm
- **GIVEN** the notification panel is open with a completed job listed
- **WHEN** the user clicks that list item
- **THEN** the system loads that job for HITL review the same way as confirming it from the Job Queue
- **AND** the notification panel closes

#### Scenario: Empty state
- **GIVEN** there are no completed jobs in the current session job queue
- **WHEN** the user clicks the notification bell
- **THEN** the panel opens and shows an empty-state message (no job rows)

### Requirement: Bell Shake on New Completion
The notification bell SHALL play its existing short shake animation when a job transitions to `completed` (badge would increase / a new completed job arrives). The shake MUST NOT fire merely because a job was enqueued or entered `processing`. Animation duration remains brief (existing ~0.6s class); no continuous or looping shake.

#### Scenario: Shake when a job completes
- **GIVEN** a job is processing
- **WHEN** that job finishes successfully and becomes `completed`
- **THEN** the notification bell plays a single short shake animation

#### Scenario: No shake on enqueue alone
- **GIVEN** the user queues a new AI generation job
- **WHEN** the job enters `queued` or `processing` without completing
- **THEN** the notification bell does not shake solely for that enqueue/start event
