## MODIFIED Requirements

### Requirement: Correction Input Form
The system SHALL provide editable original-text and target-text fields for the active session, kept in local component state as the user types, AND SHALL persist both fields per-session to browser `localStorage` (debounced) so that neither field is lost across a page reload, a background session-list re-fetch, or an authentication-session object change (e.g. a token refresh), and SHALL restore any persisted text for a session when that session becomes active.

#### Scenario: User edits the original text
- GIVEN a session is active
- WHEN the user types or pastes into the "原文テキスト" textarea
- THEN the active session's original text is updated immediately in the UI state (no explicit save action)
- AND the updated text is persisted to `localStorage` for that session id within a short debounce window

#### Scenario: User edits the target (correction) text
- GIVEN a session is active
- WHEN the user types or pastes into the "添削対象テキスト" textarea
- THEN the active session's target text is updated immediately in the UI state
- AND the "AI提案を生成" (generate AI suggestions) button becomes enabled only when the target text is non-blank
- AND the updated text is persisted to `localStorage` for that session id within a short debounce window

#### Scenario: Session list re-fetch does not erase in-progress or persisted text
- GIVEN a session has non-blank original and/or target text, either currently held in UI state or previously persisted to `localStorage`
- WHEN the session list is re-fetched from the backend and the frontend `Session[]` array is rebuilt (e.g. on mount, or because the authentication session object changed identity such as a token refresh)
- THEN the rebuilt session entry's original text and target text are populated from the existing in-memory state or the persisted `localStorage` draft, in that order of preference
- AND only a session with neither in-memory text nor a persisted draft is initialized with empty strings

#### Scenario: Switching to another session and back preserves each session's own text
- GIVEN two sessions A and B each have distinct, non-blank original/target text
- WHEN the user switches the active session from A to B and then back to A
- THEN session A's original and target text are shown exactly as they were before switching away, with no bleed from session B's text

#### Scenario: Reloading the page restores the last-typed text per session
- GIVEN a session has non-blank original and/or target text that has been persisted to `localStorage` (past the debounce window)
- WHEN the browser page is fully reloaded and the user reopens that session
- THEN the original and target text fields are restored to their last-persisted values

#### Scenario: Confirmed save clears the persisted draft
- GIVEN a session has persisted original/target text in `localStorage`
- WHEN the user successfully completes "確定してコピー・保存" (`saveCorrections()`) for that session
- THEN the persisted original/target text draft for that session is cleared from `localStorage`
- AND merely navigating away from or reloading the session without saving does NOT clear the persisted draft

#### Scenario: Target text is intentionally cleared after queuing a generation job (not a bug)
- GIVEN a session has non-blank target text
- WHEN the user clicks "AI提案を生成" and the text is successfully added to the job queue
- THEN the target-text field is cleared immediately afterward so the user can type the next target text for the same fixed source text
- AND this clearing only happens after the job has been added to the queue, so the submitted text is never lost without first being queued
- AND the original (SOURCE) text is left untouched by this action
