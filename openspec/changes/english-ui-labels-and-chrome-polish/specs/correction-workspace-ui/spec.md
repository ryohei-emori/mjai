## ADDED Requirements

### Requirement: Workspace Chrome Is Presented in English
Every label the application itself supplies in the correction workspace — pane and panel titles, buttons, badges, checkboxes, placeholders, empty states, accessible names, tooltips and transient notifications — SHALL be in English. Text that originates outside the application SHALL be presented as authored: AI-generated critique (Simplified Chinese), text the user typed or pasted (Japanese), model identifiers, and provider error text.

#### Scenario: Session screen carries no application-supplied Japanese
- **GIVEN** an active session with a completed generation awaiting review
- **WHEN** the workspace renders
- **THEN** the pane switch, notifications panel, job cards, suggestion panel, history cards and session header all read in English
- **AND** the AI's Chinese correction reasons and overall comment are unchanged
- **AND** the source, exemplar and target text the user entered is unchanged

#### Scenario: Narrow-viewport pane switch
- **GIVEN** a viewport below the `lg` breakpoint with an active session
- **WHEN** the pane switch renders
- **THEN** its two controls read `TEXT` and `SUGGESTIONS`
- **AND** the `SUGGESTIONS` control still carries the count of work waiting in the pane that is off screen

#### Scenario: Accessible names match the visible language
- **WHEN** a screen reader reads the workspace controls
- **THEN** each control's accessible name is the English name, not a Japanese one that disagrees with the visible label

#### Scenario: Values sent to the server are unaffected
- **GIVEN** the user confirms and saves a correction round
- **WHEN** the history and proposals are persisted
- **THEN** the stored instruction prompt and other server-side field values are byte-identical to before this change

### Requirement: Scroll Regions Follow the Design Tokens
Scrollbars in the workspace SHALL be drawn from the design tokens in `docs/UI-DESIGN.md` — an `--outline-variant` thumb that darkens to `--outline` on hover — and SHALL NOT inherit the operating system's dark-mode scrollbar rendering. The application presents a single light theme, so the declared colour scheme SHALL be light regardless of the OS preference.

#### Scenario: Operating system is set to dark mode
- **GIVEN** an OS and browser configured to prefer a dark colour scheme
- **WHEN** the user scrolls the editor pane, the review pane or a text field
- **THEN** the scrollbar is drawn in the light theme's outline colours
- **AND** no part of the workspace switches to dark surfaces or dark text

#### Scenario: Job Queue carousel keeps its always-visible rail
- **GIVEN** a job queue with more jobs than fit the track
- **WHEN** the panel renders
- **THEN** the horizontal scrollbar under the cards is visible before the user scrolls, as before
- **AND** its thumb uses the same outline tokens as the other scroll regions

### Requirement: Non-Interactive Readouts Do Not Signal Interaction
Elements that only display a value — timing readouts, counters, status and provider badges — SHALL NOT change appearance on hover and SHALL NOT show a pointer cursor. Elements that respond to activation SHALL keep their hover feedback.

#### Scenario: Cursor rests on a timing readout
- **GIVEN** a session showing the `LATEST` and `AVG` review-time readouts
- **WHEN** the pointer moves over either readout, the `Saved` count or the selection counter
- **THEN** its background and text colour do not change
- **AND** the cursor remains the default cursor

#### Scenario: Interactive surfaces keep their hover feedback
- **WHEN** the pointer moves over a completed job card, a suggestion card, a session list entry or a notification row
- **THEN** that element still shows its hover background

### Requirement: New Session Action Reads as a Primary Action
The New Session control in the top bar SHALL be typeset from the documented typography scale at a size and weight that make it the most prominent text action in the bar.

#### Scenario: Top bar renders on a wide viewport
- **WHEN** the top bar renders at or above the `sm` breakpoint
- **THEN** the New Session button's label is set at the `body-base` size with semibold weight
- **AND** no new typography value outside the documented scale is introduced

### Requirement: Provider Reporting Is Not Duplicated
Which provider produced a round of proposals SHALL be reported on the job card that produced it, and the model that wrote them on the suggestion panel's provenance caption. It SHALL NOT additionally be reported beside the offline-mode control, where it duplicated both.

#### Scenario: A generation completes through the cloud API
- **GIVEN** offline mode is off
- **WHEN** a queued generation completes
- **THEN** the job card for that generation shows an `API` provider badge
- **AND** loading it for review shows the model identifier in the suggestion panel's provenance caption
- **AND** no provider badge is shown beside the offline-mode checkbox

#### Scenario: A generation completes through the local model
- **GIVEN** offline mode is on
- **WHEN** a queued generation completes
- **THEN** the job card for that generation shows a `WebLLM` provider badge
- **AND** no provider badge is shown beside the offline-mode checkbox
