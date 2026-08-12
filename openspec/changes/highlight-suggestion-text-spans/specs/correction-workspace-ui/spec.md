## ADDED Requirements

### Requirement: In-place highlighting of a suggestion's flagged span in TARGET TEXT

The system SHALL visually highlight, inside the actual TARGET TEXT `<textarea>`, the first occurrence of a suggestion's `original` excerpt as a substring of the current `targetText`, using the `--suggestion-highlight` MD3-pattern color token defined in `docs/UI-DESIGN.md`. The highlight SHALL be purely visual (non-interactive) and SHALL NOT alter the textarea's normal typing, caret placement, text selection, or `onChange`-driven state updates.

#### Scenario: Suggestion's flagged excerpt is found in TARGET TEXT

- **WHEN** a suggestion's `original` field is a substring of the current session's `targetText`
- **AND** that suggestion's highlight is active (see hover/selection trigger requirement below)
- **THEN** the first matching occurrence is visually highlighted within the TARGET TEXT textarea using the `--suggestion-highlight` token

#### Scenario: Suggestion's flagged excerpt is not found in TARGET TEXT

- **WHEN** a suggestion's `original` field is not a substring of the current `targetText` (e.g. the user has since edited the text)
- **THEN** no highlight is shown for that suggestion in TARGET TEXT
- **AND** no error is raised or surfaced to the user

#### Scenario: Highlighting does not interfere with editing

- **WHEN** one or more suggestion highlights are active in the TARGET TEXT textarea
- **THEN** the user can still type, move the caret, select text, and trigger `onChange` exactly as if no highlight were present

### Requirement: In-place highlighting of the corresponding span in SOURCE TEXT

The system SHALL visually highlight, inside the actual SOURCE TEXT `<textarea>`, the first occurrence of a suggestion's `sourceExcerpt` as a substring of the current `originalText`, using the same `--suggestion-highlight` token family as the TARGET TEXT highlight, when and only when `sourceExcerpt` is non-empty and found in `originalText`.

#### Scenario: sourceExcerpt is present and found in SOURCE TEXT

- **WHEN** a suggestion's `sourceExcerpt` is non-empty and is a substring of the current `originalText`
- **AND** that suggestion's highlight is active
- **THEN** the first matching occurrence is visually highlighted within the SOURCE TEXT textarea

#### Scenario: sourceExcerpt is empty

- **WHEN** a suggestion's `sourceExcerpt` field is empty or absent
- **THEN** no highlight is shown in SOURCE TEXT for that suggestion
- **AND** no error is raised or surfaced to the user

#### Scenario: sourceExcerpt is present but not found in SOURCE TEXT

- **WHEN** a suggestion's `sourceExcerpt` is non-empty but is not a substring of the current `originalText` (e.g. the user has since edited SOURCE TEXT, or the model's excerpt was not verbatim)
- **THEN** no highlight is shown in SOURCE TEXT for that suggestion
- **AND** the TARGET TEXT highlight for that same suggestion (if its `original` is still found) is unaffected

### Requirement: Highlight trigger — hover preview and selected persistence

The system SHALL show a suggestion's highlight(s) under two independent triggers: (1) while the user hovers over that suggestion's card in the AI Suggestions panel (a transient preview), and (2) while that suggestion is selected (a persistent highlight, independent of hover). The two trigger states SHALL be visually distinguishable from each other (e.g. different highlight opacity/emphasis), and multiple simultaneously-active highlights (e.g. several selected suggestions) SHALL render without visually breaking or corrupting the text layout.

#### Scenario: Hovering a suggestion card previews its highlight

- **WHEN** the user hovers over an unselected suggestion card with a resolvable TARGET TEXT (and, if applicable, SOURCE TEXT) match
- **THEN** the corresponding span(s) are highlighted in the hover-preview visual style
- **AND** the highlight is removed when the hover ends, unless that suggestion is also selected

#### Scenario: Selecting a suggestion persists its highlight

- **WHEN** the user selects a suggestion (via the existing selection controls)
- **THEN** its resolvable span(s) remain highlighted in the selected visual style regardless of hover state
- **AND** the highlight is removed when the suggestion is deselected (unless still hovered)

#### Scenario: Multiple selected suggestions highlight simultaneously without collision

- **WHEN** two or more suggestions are selected and each has a resolvable TARGET TEXT match
- **THEN** each match is highlighted in the selected style
- **AND** if any of their matched ranges overlap, the overlapping portion renders in a single deterministic style (hover style taking priority over selected style) rather than corrupting the rendered text

### Requirement: Highlight overlay preserves native textarea behavior

The highlighting mechanism SHALL be implemented as a non-interactive visual overlay layered with the native `<textarea>` element (not a replacement input), such that all native browser text-editing behavior (typing, IME composition, caret rendering, native text selection, scrolling) continues to function exactly as before this feature was added.

#### Scenario: Typing while a highlight is active

- **WHEN** a highlight is currently displayed in a textarea
- **AND** the user types additional characters anywhere in that textarea
- **THEN** the typed characters are inserted at the caret position exactly as in an unhighlighted textarea, and the `onChange` handler fires with the updated value

#### Scenario: Scrolling a long text keeps the highlight aligned

- **WHEN** the textarea's content exceeds its visible height and the user scrolls it
- **THEN** the highlight overlay's visible position scrolls in sync, remaining aligned with the underlying text
