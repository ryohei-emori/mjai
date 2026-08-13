## MODIFIED Requirements

### Requirement: Saving a Correction History
The system SHALL, when the user confirms via "確定してコピー・保存", first copy the combined summary to the clipboard and commit the local UI success state (append saved-history, clear the active editing form, and for job-queue / history-restore confirm flows apply the same local confirm side-effects as today), then persist the finalized correction (history plus all proposals) to the backend asynchronously. The confirm button MUST show a spinning Material Symbols `progress_activity` icon for the entire time it is in a waiting/loading state. Concurrent confirm submissions MUST be rejected while a confirm/save is in flight.

#### Scenario: User saves a completed correction with 3 or more selections
- GIVEN at least 3 proposals are selected in the active session
- WHEN the user clicks "確定してコピー・保存"
- THEN the UI builds a combined comment consisting of the selected proposals numbered in selection order (each with its original or user-modified comment) followed by the overall comment, and copies it to the clipboard without waiting for backend persistence to finish
- AND the session's target text, suggestion list, and overall comment are cleared, and the combined result is appended to the session's saved-data history with a timestamp (local UI commit) without waiting for backend persistence to finish
- AND the custom-correction form is hidden, its inputs cleared, and the selection counter reset to 0
- AND a success toast is shown indicating the copy completed (and that server save may still be in progress, if applicable)
- AND the UI creates a history via the history API with the session id, original text, target text, a fixed instruction prompt, the overall comment, the JSON-encoded list of selected proposal ids, and the JSON-encoded list of custom proposals among the selection
- AND the UI then creates a proposal record via the proposal API for every suggestion in the session (selected and unselected), each carrying its selection state, custom flag, modification flag, and (if selected) its selection order
- AND when backend persistence succeeds, a success toast is shown indicating the save completed
- AND when backend persistence fails after a successful copy/local commit, a destructive toast is shown indicating that copy succeeded but save failed

#### Scenario: Confirm button shows spinner while waiting
- GIVEN the confirm/save flow has entered a waiting/loading state (`isSaving` / equivalent)
- WHEN the "確定してコピー・保存" button is still rendered
- THEN its leading icon is Material Symbols `progress_activity` with a continuous spin animation (`animate-spin`)
- AND the button remains disabled to prevent double-submit

#### Scenario: Saving fails before copy/local commit
- GIVEN the user attempts to save a correction history
- WHEN clipboard copy fails (or an error occurs before local UI commit)
- THEN the error is logged to the console
- AND the active editing form is NOT cleared
- AND a destructive toast is shown (copy failure uses the existing clipboard-failure copy; other pre-commit failures use an error toast)
- AND no backend history/proposal create is treated as successful for that attempt

#### Scenario: Background save fails after copy/local commit
- GIVEN clipboard copy and local UI commit already succeeded
- WHEN history-create or proposal-create fails
- THEN the error is logged to the console
- AND a destructive toast is shown indicating copy succeeded but server save failed
- AND the local UI remains in the committed (cleared) state

## ADDED Requirements

### Requirement: Confirm Button Loading Indicator
While "確定してコピー・保存" is disabled due to an in-flight confirm/save, the button MUST display a spinning `progress_activity` icon using the same Material Symbols + `animate-spin` pattern used elsewhere in the workspace (job processing, auth loading). A static (non-spinning) `progress_activity` glyph alone is NOT sufficient.

#### Scenario: Spinner visible during in-flight confirm
- GIVEN a confirm/save is in flight and the confirm button is still mounted
- WHEN the user looks at the button
- THEN they see a continuously rotating `progress_activity` icon next to the waiting label (e.g. "保存中...")
