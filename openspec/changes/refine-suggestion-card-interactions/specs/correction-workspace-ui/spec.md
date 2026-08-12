## MODIFIED Requirements

### Requirement: Proposal Selection and Ordering
The system SHALL let the user select or deselect each proposal by double-clicking anywhere on its card (including its comment text) or by clicking the card's hover-reveal select icon button, and SHALL track and display the order in which proposals were selected next to the proposal's "Option X" label. The system SHALL NOT present a separate checkbox control for selection.

#### Scenario: User selects a proposal
- GIVEN a proposal card is currently unselected
- WHEN the user double-clicks anywhere on the card, including on its "修正コメント" text
- THEN the proposal becomes selected and is assigned the next sequential selection-order number
- AND the selection counter increments by 1
- AND a small badge showing its selection-order number appears next to the "Option X" label

#### Scenario: User deselects a proposal
- GIVEN a selected proposal card with a selection-order number
- WHEN the user double-clicks anywhere on the card
- THEN the proposal becomes unselected and loses its selection-order number
- AND every other selected proposal whose order number was greater than the deselected one has its order number decremented by 1
- AND the selection counter decrements by 1

#### Scenario: User selects or deselects a proposal via the hover icon button
- GIVEN a proposal card is hovered, revealing its check_circle/radio_button_unchecked icon button
- WHEN the user clicks that icon button
- THEN the proposal's selected state toggles exactly as it would from a double-click on the card
- AND clicking the icon button does not also trigger the card-level double-click handler

### Requirement: Proposal Comment Editing
The system SHALL let the user edit the correction comment of a selected proposal in a textarea that visually auto-resizes to fit its full content, while showing the comment as read-only text when the proposal is not selected. The selected-state textarea's rendered height SHALL never be shorter than the height needed to display the comment's full text without internal scrolling, matching or exceeding the height the same text would occupy in the unselected read-only view.

#### Scenario: User edits a selected proposal's comment
- GIVEN a proposal is selected
- WHEN the user types into its comment textarea
- THEN the edited text is stored as the proposal's modified reason, separate from the original AI-generated reason
- AND the displayed value in the textarea reflects the modified reason once set

#### Scenario: Selecting a proposal with a long comment does not shrink it
- GIVEN a proposal is unselected and its comment `<p>` is rendered at a height that fits its full (possibly long) text
- WHEN the user selects that proposal, switching the comment to an editable textarea
- THEN the textarea's height is at least as tall as the comment text requires, and is not clipped to a fixed minimum height shorter than the pre-selection view

#### Scenario: Textarea grows as the user types more text
- GIVEN a proposal is selected and its comment textarea is displayed
- WHEN the user types additional lines into the textarea, growing the content beyond the textarea's current height
- THEN the textarea's height increases to fit the new content without requiring internal scrolling

#### Scenario: Unselected proposal comment is read-only
- GIVEN a proposal is not selected
- WHEN the proposal list renders
- THEN its comment is shown as plain (non-editable) text using its original reason

## ADDED Requirements

### Requirement: AI Suggestions Panel Scrolls Into View At Most Once Per Confirmation Session
When the user confirms a job from the job queue, the system SHALL scroll the AI SUGGESTIONS panel into view exactly once for that confirmation session, at the point the confirmed job's suggestions first become available. The system SHALL NOT re-trigger this scroll on subsequent suggestion-list mutations (such as selecting, deselecting, or editing a proposal) within the same confirmation session.

#### Scenario: Confirming a job scrolls the suggestions panel into view once
- GIVEN the user confirms a job from the job queue and its suggestions are not yet loaded
- WHEN that job's suggestions become available
- THEN the AI SUGGESTIONS panel scrolls into view

#### Scenario: Selecting a lower-listed option does not re-scroll
- GIVEN the AI SUGGESTIONS panel has already scrolled into view for the current confirmation session
- WHEN the user selects, deselects, or edits any proposal (e.g. selecting "Option E")
- THEN the panel does not scroll again, regardless of how the suggestions array reference changes as a result

#### Scenario: Confirming a different job re-arms the one-time scroll
- GIVEN a confirmation session has already scrolled its suggestions panel into view once
- WHEN the user confirms a different job from the job queue and its suggestions become available
- THEN the panel scrolls into view again for that new confirmation session
