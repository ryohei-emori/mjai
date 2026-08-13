## ADDED Requirements

### Requirement: Job Queue Horizontal Slide Presentation
The Job Queue panel SHALL present its job cards as a single horizontally sliding track instead of a vertically growing stack. The panel's height SHALL stay constant regardless of how many jobs are in the queue, so the panels below it (AI Suggestions, History) do not get pushed off-screen as the queue grows. Horizontal movement SHALL support native input — trackpad/wheel horizontal scroll and touch swipe — and SHALL settle with one card aligned to the start of the visible area rather than resting mid-card.

#### Scenario: Many jobs do not grow the panel vertically
- **GIVEN** the current session's job queue contains 20 jobs
- **WHEN** the Job Queue panel renders
- **THEN** the job cards are laid out in one horizontal row inside a horizontally scrollable track
- **AND** the panel occupies the same vertical height as it does with a single job
- **AND** the panel does not introduce a vertical scrollbar for the job list

#### Scenario: Swipe and wheel move the track
- **GIVEN** the job queue has more cards than fit in the visible track
- **WHEN** the user swipes horizontally on a touch device or scrolls horizontally with a trackpad/wheel over the track
- **THEN** the track scrolls horizontally to reveal further job cards
- **AND** when scrolling settles, a card edge is aligned to the start of the visible area

#### Scenario: Single job needs no sliding
- **GIVEN** the job queue contains exactly one job
- **WHEN** the Job Queue panel renders
- **THEN** the job card is shown and no slide navigation controls or position indicator are offered

### Requirement: Job Queue Relevance Ordering
The Job Queue SHALL order cards by present relevance rather than insertion order, so the first (leftmost) card is the job the user most likely needs. The order SHALL be: `processing` jobs first, then `queued` jobs, then finished jobs — `completed` before `failed`. Within each group, jobs SHALL be ordered newest-first by their most recent timestamp (completion time when present, otherwise enqueue time). The TopAppBar bell's completed-job list SHALL use the same newest-first rule for completed jobs so the two surfaces never disagree about which completed job is newest.

#### Scenario: Processing job leads the track
- **GIVEN** the job queue contains a `completed` job, a `queued` job, and a `processing` job in that insertion order
- **WHEN** the Job Queue panel renders
- **THEN** the `processing` job is the first card, followed by the `queued` job, followed by the `completed` job

#### Scenario: Newest finished job comes first among finished jobs
- **GIVEN** the job queue contains three `completed` jobs with different completion times and no in-flight jobs
- **WHEN** the Job Queue panel renders
- **THEN** the most recently completed job is the first card and the oldest is last

#### Scenario: Failed jobs trail completed jobs
- **GIVEN** the job queue contains a `failed` job that finished after a `completed` job
- **WHEN** the Job Queue panel renders
- **THEN** the `completed` job appears before the `failed` job

#### Scenario: Bell list agrees with queue ordering for completed jobs
- **GIVEN** the job queue contains several `completed` jobs
- **WHEN** the user opens the TopAppBar notification bell panel
- **THEN** the completed jobs are listed newest-first in the same relative order they appear among completed cards in the Job Queue track

### Requirement: Job Queue Slide Affordances
The Job Queue SHALL make it visually obvious that more cards exist off-screen and that the track slides horizontally. When the content overflows the visible track, the panel SHALL provide: previous/next navigation controls that move the track by roughly one visible page; a position indicator showing which page of cards is currently visible; and an edge treatment (fade/partial next-card peek) at each side where more content exists. Navigation controls SHALL be disabled (and communicate that state) when the track is already at that end, and the edge treatment at a given side SHALL be absent when there is nothing more to reveal on that side.

#### Scenario: Overflow shows navigation and indicator
- **GIVEN** the job queue has more cards than fit in the visible track
- **WHEN** the panel renders at the start of the track
- **THEN** a next control is enabled, a previous control is present but disabled, a position indicator is shown, and a fade/peek is visible only on the trailing edge

#### Scenario: Next control advances roughly one page
- **GIVEN** the track is at the start and overflowing
- **WHEN** the user activates the next control
- **THEN** the track scrolls forward by approximately one visible width and settles card-aligned
- **AND** the position indicator updates to the newly visible page

#### Scenario: End of track disables the next control
- **GIVEN** the track is scrolled to its far end
- **WHEN** the panel re-evaluates the scroll position
- **THEN** the next control is disabled, the previous control is enabled, and the trailing fade/peek is no longer shown

### Requirement: Job Queue Slide Keyboard and Assistive Access
The Job Queue slide track SHALL be operable without a pointer and describable to assistive technology. The track SHALL be reachable by keyboard and, while focus is within it, `ArrowLeft`/`ArrowRight` SHALL move the track backward/forward. Navigation controls and the track region SHALL carry accessible labels, and focused interactive elements SHALL show a visible focus indicator. Job cards that can start the HITL confirm flow SHALL remain keyboard-activatable exactly as before (focusable, `Enter`/`Space` confirm).

#### Scenario: Arrow keys slide the track
- **GIVEN** keyboard focus is inside the Job Queue slide track and the track is overflowing
- **WHEN** the user presses `ArrowRight`
- **THEN** the track scrolls forward
- **AND** pressing `ArrowLeft` scrolls it backward

#### Scenario: Controls and region are labelled
- **GIVEN** the Job Queue panel is rendered with an overflowing track
- **WHEN** assistive technology inspects the panel
- **THEN** the previous and next controls expose accessible labels describing their action
- **AND** the scrollable track exposes an accessible label identifying it as the job queue list

#### Scenario: Confirm from keyboard still works
- **GIVEN** a `completed` job card with suggestions is focused via keyboard inside the track
- **WHEN** the user presses `Enter` or `Space`
- **THEN** the same HITL confirm flow starts as when clicking the card

### Requirement: Job Queue Responsive Cards Per View
The number of job cards visible at once SHALL adapt to the available width of the right pane, which the user can resize. Narrow widths SHALL show one card at a time; wider widths SHALL show more cards per view. Card widths SHALL be derived from the visible track width so that a partial next card peeks in when content overflows, and the navigation step SHALL match the number of cards currently visible.

#### Scenario: Narrow pane shows one card
- **GIVEN** the right pane is at or near its minimum width
- **WHEN** the Job Queue panel renders with several jobs
- **THEN** one job card fills the visible track width (with a partial peek of the next card)
- **AND** activating the next control advances by one card

#### Scenario: Wide pane shows multiple cards
- **GIVEN** the user drags the right pane toward its maximum width
- **WHEN** the Job Queue panel re-renders
- **THEN** more than one job card is visible at once
- **AND** the navigation step and position indicator reflect the larger page size
