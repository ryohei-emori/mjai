## MODIFIED Requirements

### Requirement: Clipboard Copy Feedback
The system SHALL notify the user via toast whether a clipboard copy operation succeeded or failed, and the success toast's description SHALL accurately reflect the kind of content that was actually copied rather than always claiming corrected content was copied.

#### Scenario: Clipboard copy succeeds
- GIVEN text is copied to the clipboard (e.g. as part of saving a correction)
- WHEN the copy operation resolves successfully
- THEN a success toast is shown with title "コピー完了"

#### Scenario: Clipboard copy fails
- GIVEN a clipboard copy is attempted
- WHEN the browser's clipboard API rejects the write
- THEN a destructive toast is shown with title "コピー失敗" and description "クリップボードへのコピーに失敗しました"

#### Scenario: Copying the SOURCE text shows an accurate description
- GIVEN the user clicks the copy button in the SOURCE TEXT card
- WHEN the copy operation resolves successfully
- THEN the success toast's description is "原文がクリップボードにコピーされました"
- AND the description does NOT claim "修正内容" (corrected content) was copied

#### Scenario: Copying the TARGET text shows an accurate description
- GIVEN the user clicks the copy button in the TARGET TEXT card
- WHEN the copy operation resolves successfully
- THEN the success toast's description is "添削対象テキストがクリップボードにコピーされました"

#### Scenario: Copying an AI suggestion's excerpt and reason shows an accurate description
- GIVEN the user clicks a proposal card's copy icon
- WHEN the copy operation resolves successfully
- THEN the success toast's description is "提案内容がクリップボードにコピーされました"

#### Scenario: Copying the finalized combined comment during save keeps the corrected-content wording
- GIVEN `saveCorrections()` copies the combined comment of selected proposals plus the overall comment to the clipboard
- WHEN the copy operation resolves successfully
- THEN the success toast's description is "修正内容がクリップボードにコピーされました", since this is the one call site that genuinely copies finalized corrected content

### Requirement: Correction Input Form
The system SHALL provide editable original-text and target-text fields for the active session, kept in local component state as the user types, and SHALL provide a one-click copy-to-clipboard button in each of the SOURCE TEXT and TARGET TEXT card headers.

#### Scenario: User edits the original text
- GIVEN a session is active
- WHEN the user types or pastes into the "原文テキスト" textarea
- THEN the active session's original text is updated immediately in the UI state (no explicit save action)

#### Scenario: User edits the target (correction) text
- GIVEN a session is active
- WHEN the user types or pastes into the "添削対象テキスト" textarea
- THEN the active session's target text is updated immediately in the UI state
- AND the "AI提案を生成" (generate AI suggestions) button becomes enabled only when the target text is non-blank

#### Scenario: User copies the SOURCE text via the card header button
- GIVEN the active session has non-blank original text
- WHEN the user clicks the copy icon button in the SOURCE TEXT card header
- THEN the original text is copied to the clipboard with an accurate toast description (see "Clipboard Copy Feedback")

#### Scenario: User copies the TARGET text via the card header button
- GIVEN the active session has non-blank target text
- WHEN the user clicks the copy icon button in the TARGET TEXT card header
- THEN the target text is copied to the clipboard with an accurate toast description (see "Clipboard Copy Feedback")
- AND clicking the button while the target text is blank does not attempt a copy, mirroring the SOURCE TEXT card's empty-text guard

#### Scenario: TARGET TEXT card header no longer shows decorative formatting icons
- GIVEN the TARGET TEXT card header renders
- WHEN the user inspects the header's action area
- THEN it shows exactly one functional copy button (no non-interactive `format_bold`/`format_italic` icons)
