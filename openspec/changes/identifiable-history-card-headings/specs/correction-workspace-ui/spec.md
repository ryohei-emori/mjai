## ADDED Requirements

### Requirement: Correction Text Short Label
The workspace SHALL derive a short, single-line label that identifies a correction round from its text, and SHALL use one and the same derivation rule everywhere such a label is shown (History card heading, Job Queue card preview, notification-bell entry) so the surfaces cannot disagree about how a round is named.

The label SHALL be derived from the round's target text, falling back to its source text when the target text is blank. The rule SHALL be:

- When the text's first non-blank line is **title-like** — short, followed by at least one further non-blank line, and not ending in sentence-terminating or list-continuing punctuation — the label SHALL be that line verbatim, with no ellipsis.
- Otherwise the label SHALL be an excerpt taken from the start of the text with runs of whitespace (including line breaks) collapsed to single spaces, truncated at a fixed character budget and marked with a trailing ellipsis only when truncation actually removed content.
- When both texts are absent, empty, or whitespace-only, the label SHALL be the placeholder 「(空のテキスト)」.

Truncation SHALL count and cut whole characters, so a label never ends in a broken surrogate pair, and SHALL apply the same budget regardless of script, so mixed Japanese/Chinese text is handled identically to single-script text.

#### Scenario: Title-like first line becomes the label verbatim
- **GIVEN** a correction round whose target text starts with a short heading line followed by one or more body paragraphs
- **WHEN** a surface renders that round's short label
- **THEN** the label is exactly that heading line
- **AND** no ellipsis is appended

#### Scenario: Body text is excerpted with an ellipsis
- **GIVEN** a correction round whose target text is a long prose paragraph with no heading line
- **WHEN** a surface renders that round's short label
- **THEN** the label shows the beginning of the text up to the label character budget
- **AND** a trailing ellipsis indicates the text continues

#### Scenario: Short body text is shown in full
- **GIVEN** a correction round whose target text is shorter than the label character budget and is a single paragraph
- **WHEN** a surface renders that round's short label
- **THEN** the whole text is shown as the label with no ellipsis

#### Scenario: Multi-line text without a heading collapses to one line
- **GIVEN** a correction round whose target text spans several paragraphs, the first of which is long prose
- **WHEN** a surface renders that round's short label
- **THEN** the label is a single line with line breaks and repeated whitespace rendered as single spaces

#### Scenario: Blank text falls back to a placeholder
- **GIVEN** a correction round whose target text and source text are both empty or whitespace-only
- **WHEN** a surface renders that round's short label
- **THEN** the label is 「(空のテキスト)」 rather than an empty heading

#### Scenario: Blank target text falls back to the source text
- **GIVEN** a correction round whose target text is blank but whose source text has content
- **WHEN** a surface renders that round's short label
- **THEN** the label is derived from the source text by the same rule

### Requirement: History Cards Identify Their Content
Each card in the History panel SHALL lead with the correction round's short label so the user can tell rounds apart without opening them. The round's sequence number SHALL remain visible but SHALL be presented as secondary metadata alongside the save timestamp, not as the card's heading. The heading SHALL be constrained to a single line and SHALL be visually truncated when the label is wider than the card, without pushing the card's badge or action buttons out of place.

The card's existing behaviour SHALL be preserved: the saved/unconfirmed badge, the save timestamp, restore-on-click (and keyboard activation), the confirm action, and the archive action all behave exactly as before, and the heading's font weight is unchanged.

#### Scenario: Two rounds are distinguishable at a glance
- **GIVEN** the active session has two saved rounds with different target texts
- **WHEN** the History panel renders
- **THEN** each card's heading shows that round's own short label
- **AND** the two headings differ whenever the underlying texts differ

#### Scenario: Sequence number is demoted, not removed
- **GIVEN** the History panel lists saved rounds
- **WHEN** a card renders
- **THEN** the card still shows its 1-based position
- **AND** that position appears with the timestamp in the card's metadata line rather than as the heading

#### Scenario: Long label does not break the card layout
- **GIVEN** a saved round whose short label is wider than the History card
- **WHEN** the card renders
- **THEN** the heading is clipped to one line with a truncation indicator
- **AND** the saved/unconfirmed badge and the confirm/archive buttons remain fully visible in their existing positions

#### Scenario: Existing card actions are unaffected
- **GIVEN** a History card with the new heading
- **WHEN** the user clicks the card, activates it with `Enter`/`Space`, clicks the confirm action, or clicks the archive action
- **THEN** the same restore, confirm, and archive behaviour occurs as before the heading change

## MODIFIED Requirements

### Requirement: Saved History Restore
The system SHALL let the user restore a previously saved correction-history entry from the active session's saved-data list back into the active editing form. Each listed entry SHALL be identified by the correction round's short label, with its 1-based position and save timestamp shown as secondary metadata.

#### Scenario: User restores a saved history entry
- GIVEN the active session has one or more saved-data entries listed under "保存履歴", each showing the round's short label plus its position and save timestamp
- WHEN the user clicks that entry's "復元" button
- THEN the active session's original text, target text, suggestion list, and overall comment are replaced with the values from that saved entry
- AND the selection counter is recalculated from the restored suggestions' selected state
- AND the custom-correction form is shown
- AND a toast is shown with title "履歴を復元しました"

#### Scenario: User clicks delete on a saved history entry
- GIVEN a saved-data entry is listed with a "削除" button
- WHEN the user clicks that button
- THEN the action currently only logs "削除機能未実装" (deletion not implemented) to the console and has no other observable effect
