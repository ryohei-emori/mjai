## Purpose

The correction-workspace UI is the single-page Next.js/React frontend that lets a user manage correction sessions, submit Japanese text for AI-assisted correction, review and curate AI-generated correction proposals, and save the finalized result as a session history entry.

## ADDED Requirements

### Requirement: Session List Display
The system SHALL load the list of sessions from the backend when the workspace first mounts and display each session's name, creation date, and saved-correction count in the sidebar.

#### Scenario: Sessions load on initial mount
- GIVEN the workspace UI is opened
- WHEN the page finishes mounting
- THEN the UI calls the sessions API to fetch the session list
- AND each returned session is rendered in the sidebar showing its name, formatted creation date, and a "保存済み: N件" badge with its correction count

#### Scenario: No sessions exist
- GIVEN the session list returned from the API is empty
- WHEN the sidebar renders
- THEN an empty-state message ("セッションがありません") with an icon is shown instead of a session list

### Requirement: Session Selection and On-Demand Detail Loading
The system SHALL let the user select a session from the sidebar as the active session, and SHALL lazily load that session's saved correction-history details only when the session is selected.

#### Scenario: User selects a session from the sidebar
- GIVEN one or more sessions are listed in the sidebar
- WHEN the user clicks a session entry
- THEN that session becomes the active session shown in the main content area
- AND the mobile sidebar sheet (if open) closes
- AND the UI fetches that session's histories and, for each history, its proposals, then populates the session's saved-data list with the results

#### Scenario: No session selected
- GIVEN no session has been selected (e.g. on first load with no prior selection)
- WHEN the main content area renders
- THEN a "セッションを開始" (start a session) card is shown instead of the workspace form, with a button to create a new session

### Requirement: Session Creation
The system SHALL allow the user to create a new session via the backend API and SHALL immediately make it the active session.

#### Scenario: User creates a new session
- GIVEN the user is viewing the sidebar or the empty-state "start a session" card
- WHEN the user clicks a "新しいセッション" / "新しいセッション作成" button
- THEN the UI calls the sessions-create API with an auto-generated default name
- AND the newly created session is prepended to the session list
- AND the new session becomes the active session
- AND the mobile sidebar sheet closes and the selection counter resets to 0

#### Scenario: Session creation fails
- GIVEN the user triggers session creation
- WHEN the create-session API call throws an error
- THEN the error is logged to the console
- AND a destructive toast is shown with title "エラー" and description "セッションの作成に失敗しました"

### Requirement: Session Deletion
The system SHALL allow the user to delete a session via the backend API and SHALL update the active session appropriately if the deleted session was active.

#### Scenario: User deletes a non-active session
- GIVEN a session other than the currently active one exists in the sidebar
- WHEN the user clicks that session's delete (trash) button
- THEN the UI calls the delete-session API for that session
- AND the session is removed from the sidebar list
- AND the currently active session remains unchanged

#### Scenario: User deletes the currently active session
- GIVEN the currently active session is deleted
- WHEN the delete completes
- THEN the active session becomes the first remaining session in the list, or no session if none remain

#### Scenario: Session deletion fails
- GIVEN the user triggers session deletion
- WHEN the delete-session API call throws an error
- THEN the error is logged to the console
- AND a destructive toast is shown with title "エラー" and description "セッションの削除に失敗しました"

### Requirement: Correction Input Form
The system SHALL provide editable original-text and target-text fields for the active session, kept in local component state as the user types.

#### Scenario: User edits the original text
- GIVEN a session is active
- WHEN the user types or pastes into the "原文テキスト" textarea
- THEN the active session's original text is updated immediately in the UI state (no explicit save action)

#### Scenario: User edits the target (correction) text
- GIVEN a session is active
- WHEN the user types or pastes into the "添削対象テキスト" textarea
- THEN the active session's target text is updated immediately in the UI state
- AND the "AI提案を生成" (generate AI suggestions) button becomes enabled only when the target text is non-blank

### Requirement: AI Suggestion Generation
The system SHALL let the user trigger AI correction-suggestion generation for the active session's target text, preserving any existing proposal selections, edited comments, and custom proposals across regeneration.

#### Scenario: User generates AI suggestions successfully
- GIVEN the active session has non-blank target text and no generation is already in progress
- WHEN the user clicks "AI提案を生成"
- THEN the button shows a loading spinner and "AI分析中..." while the request is in flight, and is disabled
- AND the UI calls the suggestions-generation API with the session's original text, target text, a fixed instruction prompt ("CCTalkからの添削指示"), the session id, and engine "gemini"
- AND on success, the returned suggestions and overall comment replace the session's suggestion list and overall comment
- AND the custom-correction add form becomes visible

#### Scenario: Regeneration preserves existing selections and custom proposals
- GIVEN the active session already has AI suggestions with some selected, some with an edited comment, and/or one or more custom proposals
- WHEN the user regenerates AI suggestions
- THEN any newly returned suggestion whose text matches a previously seen suggestion's text retains its prior selected state, selection order, and edited comment
- AND previously added custom proposals are preserved and appended to the new suggestion list
- AND the selection counter is recalculated from the resulting selected suggestions

#### Scenario: AI suggestion generation fails
- GIVEN the user triggers AI suggestion generation
- WHEN the suggestions-generation API call throws an error
- THEN a destructive toast is shown with title "APIエラー" and description "AI提案の取得に失敗しました"
- AND the loading state is cleared regardless of success or failure

#### Scenario: Mock mode bypasses the backend
- GIVEN the app is running with `NEXT_PUBLIC_FRONTEND_MODE` set to `mock`
- WHEN the user clicks "AI提案を生成"
- THEN the UI uses a fixed set of built-in mock suggestions and a mock overall comment instead of calling the suggestions API
- AND the same selection/custom-proposal preservation behavior applies as in the real API path

### Requirement: Proposal Review Display
The system SHALL display each AI-generated or custom proposal with its flagged original-text excerpt and its correction comment, and SHALL visually distinguish custom proposals.

#### Scenario: Proposal list is rendered after generation
- GIVEN the active session has one or more suggestions
- WHEN the suggestions panel renders
- THEN each suggestion shows its excerpt of flagged original text and its correction comment
- AND suggestions with `isCustom` set show a "カスタム修正" badge
- AND a running count "選択済み: X/5+" is shown, switching to a "保存可能" badge once at least 3 are selected

### Requirement: Proposal Selection and Ordering
The system SHALL let the user select or deselect each proposal via a checkbox, and SHALL track and display the order in which proposals were selected.

#### Scenario: User selects a proposal
- GIVEN a proposal is currently unselected
- WHEN the user checks its checkbox
- THEN the proposal becomes selected and is assigned the next sequential selection-order number
- AND the selection counter increments by 1
- AND a small badge showing its selection-order number appears next to the checkbox

#### Scenario: User deselects a proposal
- GIVEN a selected proposal with a selection-order number
- WHEN the user unchecks its checkbox
- THEN the proposal becomes unselected and loses its selection-order number
- AND every other selected proposal whose order number was greater than the deselected one has its order number decremented by 1
- AND the selection counter decrements by 1

### Requirement: Proposal Comment Editing
The system SHALL let the user edit the correction comment of a selected proposal, while showing the comment as read-only text when the proposal is not selected.

#### Scenario: User edits a selected proposal's comment
- GIVEN a proposal is selected
- WHEN the user types into its comment textarea
- THEN the edited text is stored as the proposal's modified reason, separate from the original AI-generated reason
- AND the displayed value in the textarea reflects the modified reason once set

#### Scenario: Unselected proposal comment is read-only
- GIVEN a proposal is not selected
- WHEN the proposal list renders
- THEN its comment is shown as plain (non-editable) text using its original reason

### Requirement: Custom Proposal Addition
The system SHALL let the user manually add a custom proposal with its own flagged text and comment, which is automatically selected.

#### Scenario: User adds a valid custom proposal
- GIVEN the custom-correction form is visible with both "修正前のテキスト" and "修正コメント" filled in
- WHEN the user clicks "修正内容を追加"
- THEN a new proposal is appended to the suggestion list, marked custom, automatically selected, and assigned the next selection-order number
- AND the selection counter increments accordingly
- AND the custom-correction input fields are cleared
- AND a success toast is shown with title "修正内容を追加しました"

#### Scenario: User attempts to add an incomplete custom proposal
- GIVEN the custom-correction form has the original-text or comment field left blank
- WHEN the user clicks "修正内容を追加"
- THEN no proposal is added
- AND a destructive toast is shown with title "入力エラー" and description "すべての項目を入力してください"

### Requirement: Overall Comment Editing
The system SHALL display an editable overall summary comment for the active session's suggestion set once one is present.

#### Scenario: User edits the overall comment
- GIVEN the active session has a non-empty overall comment (set by AI generation or mock mode)
- WHEN the user types into the "全体総括コメント" textarea
- THEN the session's overall comment is updated immediately in the UI state

### Requirement: Minimum Selection Save Gate
The system SHALL require at least 3 selected proposals before the user can save a correction history.

#### Scenario: Fewer than 3 proposals selected
- GIVEN fewer than 3 proposals are currently selected
- WHEN the suggestions panel renders
- THEN the "確定してコピー・保存" (save) button is disabled and shows the current selected count out of the minimum (e.g. "(1/3)")

#### Scenario: User attempts to save with fewer than 3 selections
- GIVEN somehow the save action is invoked with fewer than 3 selected proposals
- WHEN the save handler runs
- THEN no history is created
- AND a destructive toast is shown with title "選択不足" and description "3つ以上の修正内容を選択してください"

### Requirement: Saving a Correction History
The system SHALL persist the active session's finalized correction (history plus all proposals) to the backend, copy a combined summary to the clipboard, and reset the active editing form while appending the result to the session's saved-history list.

#### Scenario: User saves a completed correction with 3 or more selections
- GIVEN at least 3 proposals are selected in the active session
- WHEN the user clicks "確定してコピー・保存"
- THEN the UI creates a history via the history API with the session id, original text, target text, a fixed instruction prompt, the overall comment, the JSON-encoded list of selected proposal ids, and the JSON-encoded list of custom proposals among the selection
- AND the UI then creates a proposal record via the proposal API for every suggestion in the session (selected and unselected), each carrying its selection state, custom flag, modification flag, and (if selected) its selection order
- AND the UI builds a combined comment consisting of the selected proposals numbered in selection order (each with its original or user-modified comment) followed by the overall comment, and copies it to the clipboard
- AND the session's target text, suggestion list, and overall comment are cleared, and the combined result is appended to the session's saved-data history with a timestamp
- AND the custom-correction form is hidden, its inputs cleared, and the selection counter reset to 0
- AND a success toast is shown with title "保存完了" and description "修正内容が保存され、クリップボードにコピーされました"

#### Scenario: Saving fails
- GIVEN the user attempts to save a correction history
- WHEN any of the history-create, proposal-create, or clipboard-copy calls throws an error
- THEN the error is logged to the console
- AND a destructive toast is shown with title "エラー" and description "修正内容の保存に失敗しました"

### Requirement: Clipboard Copy Feedback
The system SHALL notify the user via toast whether a clipboard copy operation succeeded or failed.

#### Scenario: Clipboard copy succeeds
- GIVEN text is copied to the clipboard (e.g. as part of saving a correction)
- WHEN the copy operation resolves successfully
- THEN a success toast is shown with title "コピー完了" and description "修正内容がクリップボードにコピーされました"

#### Scenario: Clipboard copy fails
- GIVEN a clipboard copy is attempted
- WHEN the browser's clipboard API rejects the write
- THEN a destructive toast is shown with title "コピー失敗" and description "クリップボードへのコピーに失敗しました"

### Requirement: Saved History Restore
The system SHALL let the user restore a previously saved correction-history entry from the active session's saved-data list back into the active editing form.

#### Scenario: User restores a saved history entry
- GIVEN the active session has one or more saved-data entries listed under "保存履歴", each showing an index label and save timestamp
- WHEN the user clicks that entry's "復元" button
- THEN the active session's original text, target text, suggestion list, and overall comment are replaced with the values from that saved entry
- AND the selection counter is recalculated from the restored suggestions' selected state
- AND the custom-correction form is shown
- AND a toast is shown with title "履歴を復元しました"

#### Scenario: User clicks delete on a saved history entry
- GIVEN a saved-data entry is listed with a "削除" button
- WHEN the user clicks that button
- THEN the action currently only logs "削除機能未実装" (deletion not implemented) to the console and has no other observable effect

### Requirement: Responsive Sidebar Navigation
The system SHALL present the session sidebar as a slide-out sheet on small (mobile/`lg`-breakpoint-below) viewports and as a collapsible fixed sidebar on large viewports.

#### Scenario: Mobile viewport shows a sheet-based sidebar
- GIVEN the viewport is below the `lg` breakpoint
- WHEN the user taps the floating menu button
- THEN a slide-out sheet opens from the left showing the session list and "新しいセッション" action

#### Scenario: Desktop viewport shows a collapsible fixed sidebar
- GIVEN the viewport is at or above the `lg` breakpoint
- WHEN the user clicks the sidebar's collapse/expand toggle
- THEN the fixed left sidebar collapses to an icon-only rail or expands to show full session details, without affecting the main content's session state
