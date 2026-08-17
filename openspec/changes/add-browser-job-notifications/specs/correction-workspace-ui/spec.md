## ADDED Requirements

### Requirement: Browser Notification for Completed Generations
When a generation completes and is waiting for HITL review, the system SHALL deliver a browser notification, provided the user has enabled the preference and the browser has granted permission. The notification's text SHALL be in English and SHALL identify which correction round completed.

#### Scenario: Generation completes while the user is in another tab
- **GIVEN** browser notifications are enabled and permission is granted
- **AND** the MJAI tab is not the visible tab
- **WHEN** a queued generation completes
- **THEN** a browser notification is shown naming the completed round
- **AND** the in-app bell badge and shake behave exactly as before

#### Scenario: Generation completes while the user is looking at the app
- **GIVEN** browser notifications are enabled and permission is granted
- **AND** the MJAI tab is the visible tab
- **WHEN** a queued generation completes
- **THEN** no browser notification is shown
- **AND** the in-app bell still announces the completion

#### Scenario: Preference is off
- **GIVEN** the user has not enabled browser notifications
- **WHEN** a queued generation completes in a hidden tab
- **THEN** no browser notification is shown and no permission prompt appears

#### Scenario: Generation fails
- **WHEN** a queued generation fails instead of completing
- **THEN** no completion notification is shown, since there is nothing to review

### Requirement: Notification Permission Is Requested From a User Action
The system SHALL NOT request notification permission as a consequence of page load, session selection, or generation. Permission SHALL be requested only when the user activates the browser-notification preference. The preference SHALL be persisted across reloads.

#### Scenario: First visit
- **GIVEN** a browser that has never been asked for notification permission on this origin
- **WHEN** the workspace loads and the user generates and reviews corrections
- **THEN** no permission prompt appears

#### Scenario: User enables the preference
- **GIVEN** permission has not yet been decided
- **WHEN** the user turns the browser-notification preference on
- **THEN** the browser's permission prompt is shown
- **AND** if permission is granted the preference reads as on and survives a reload
- **AND** if permission is refused the preference does not read as on

#### Scenario: User turns the preference off
- **GIVEN** the preference is on with permission granted
- **WHEN** the user turns it off
- **THEN** subsequent completions produce no browser notification
- **AND** the choice survives a reload

### Requirement: Notification Click Opens the Completed Round
Activating a completion notification SHALL bring the MJAI tab forward and open that generation's HITL review — the same result as activating the job in the Job Queue or in the bell list.

#### Scenario: User clicks the notification
- **GIVEN** a completion notification for a specific generation is showing
- **WHEN** the user activates it
- **THEN** the MJAI tab is focused
- **AND** that generation's proposals are loaded for review
- **AND** the notification is dismissed

#### Scenario: The round is no longer available
- **GIVEN** a completion notification whose generation has since been removed from the queue
- **WHEN** the user activates it
- **THEN** the tab is focused and the workspace is left as it was, without an error state

### Requirement: Notifications Degrade Without Breaking the Bell
Where browser notifications are unavailable — no Notification API, or permission denied — the workspace SHALL remain fully functional through the in-app bell, and the preference control SHALL state why it cannot be used.

#### Scenario: Browser has no Notification API
- **GIVEN** a browser that does not implement the Notification API
- **WHEN** the notifications panel is opened
- **THEN** the browser-notification preference is shown as unavailable with an explanation
- **AND** no error is raised and the bell list, count and ordering are unaffected

#### Scenario: Permission was denied at the browser level
- **GIVEN** the user has blocked notifications for this origin in browser settings
- **WHEN** the notifications panel is opened
- **THEN** the preference is shown as blocked, directing the user to their browser settings
- **AND** activating it does not raise a repeated permission prompt
- **AND** completions continue to appear in the bell list
