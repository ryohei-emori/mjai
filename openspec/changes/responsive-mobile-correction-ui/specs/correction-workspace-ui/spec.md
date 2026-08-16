## ADDED Requirements

### Requirement: Workspace Fits the Visible Viewport
The workspace shell SHALL be sized to the viewport that is actually visible, not to the largest viewport the browser could present, so that no part of the application is left behind browser chrome or an on-screen keyboard. While a text field has focus, that field SHALL remain visible.

#### Scenario: Mobile browser chrome is showing
- **WHEN** the workspace is opened in a mobile browser whose address bar and toolbar occupy part of the screen
- **THEN** the shell's height matches the space left between them
- **AND** every control at the bottom of the shell is reachable without the page being taller than the visible area

#### Scenario: On-screen keyboard opens over a text field
- **GIVEN** the workspace is open on a touch device
- **WHEN** the user focuses the 添削対象 text field and the on-screen keyboard appears
- **THEN** the workspace is laid out within the space the keyboard leaves
- **AND** the focused field remains visible rather than being covered by the keyboard

#### Scenario: Browser does not support dynamic viewport units
- **GIVEN** a browser that does not understand dynamic viewport units
- **WHEN** the workspace renders
- **THEN** the shell still receives a full-viewport height from a static fallback
- **AND** the panes are laid out normally rather than collapsing to zero height

### Requirement: Top Bar Remains Fully Operable on Narrow Viewports
Every top-bar control SHALL remain reachable at viewport widths down to 320px. Because horizontal document overflow is clipped rather than scrollable, a control that does not fit MUST be relocated to a reachable place rather than allowed to overflow.

#### Scenario: Narrow viewport keeps every action reachable
- **GIVEN** a viewport 320px wide
- **WHEN** the workspace renders
- **THEN** the session-list trigger, the new-session action, notifications, settings and sign-out are all present and operable
- **AND** no top-bar control is positioned outside the visible width

#### Scenario: Section navigation moves into the session drawer
- **GIVEN** a viewport below the `md` breakpoint, where the section tabs would not fit the top bar
- **WHEN** the user opens the session drawer
- **THEN** the drawer offers the same section choices the top bar shows on wider viewports
- **AND** choosing one switches sections and closes the drawer

#### Scenario: Wide viewport is unchanged
- **GIVEN** a viewport at or above the `md` breakpoint
- **WHEN** the workspace renders
- **THEN** the section tabs appear in the top bar as before
- **AND** they are not duplicated inside the drawer

### Requirement: One Workspace Pane at a Time Below Large Viewports
Below the `lg` breakpoint the system SHALL present the editing pane and the review pane one at a time, each occupying the full height available to the workspace, rather than dividing that height between them. At or above `lg` both panes SHALL remain visible side by side.

#### Scenario: Narrow viewport shows the editor by default
- **GIVEN** a viewport below the `lg` breakpoint with an active session
- **WHEN** the workspace renders
- **THEN** the 原文 / 模範回答訳文 / 添削対象 cards are shown
- **AND** the review pane's job queue, suggestions and history are not shown
- **AND** a control is offered for switching to the review pane

#### Scenario: User switches to the review pane
- **GIVEN** a viewport below the `lg` breakpoint showing the editing pane
- **WHEN** the user activates the review switch
- **THEN** the review pane is shown using the full workspace height with a single scroll region
- **AND** the editing pane is not shown

#### Scenario: Pending review work is discoverable from the editing pane
- **GIVEN** a viewport below the `lg` breakpoint showing the editing pane
- **WHEN** the active session has suggestions awaiting review, or a generation job is queued or running
- **THEN** the review switch indicates that there is something to review without the user leaving the editing pane

#### Scenario: Reviewing a job brings the review pane forward
- **GIVEN** a viewport below the `lg` breakpoint showing the editing pane
- **WHEN** the user opens a completed job for review from the job queue or the notification list
- **THEN** the review pane is brought forward so the suggestions are visible
- **AND** the user does not have to find the switch themselves

#### Scenario: Large viewport keeps both panes
- **GIVEN** a viewport at or above the `lg` breakpoint
- **WHEN** the workspace renders
- **THEN** the editing pane and the review pane are both visible side by side
- **AND** the review pane keeps its user-adjustable width
- **AND** no pane switch is offered

### Requirement: Touch Affordances Follow Pointer Capability
Controls SHALL be operable with a coarse pointer. An action MUST NOT depend on hovering to become visible, or on a double activation to take effect, when the pointer cannot hover. Whether these accommodations apply SHALL be decided by the pointer's capability, not by viewport width, so that a small window on a mouse-driven machine keeps its hover behavior and a large touch screen still gets touch affordances.

#### Scenario: Card actions are visible without hover
- **GIVEN** a device whose pointer cannot hover
- **WHEN** a suggestion card or a session list entry renders
- **THEN** its actions are visible without any pointer interaction

#### Scenario: A single tap selects a proposal
- **GIVEN** a device whose pointer cannot hover
- **WHEN** the user taps a proposal's selection control once
- **THEN** the proposal's selection state changes
- **AND** no double activation is required

#### Scenario: Tap targets are large enough for a finger
- **GIVEN** a device whose pointer cannot hover
- **WHEN** any icon-only control renders
- **THEN** its activation area is at least 44px in each dimension

#### Scenario: Hover-capable pointers keep the existing behavior
- **GIVEN** a device with a hover-capable, fine pointer
- **WHEN** a suggestion card renders
- **THEN** its actions stay hidden until the card is hovered, as before
- **AND** the control sizes are unchanged

### Requirement: Page Zoom Remains Available
The system SHALL NOT suppress the user's ability to zoom the page.

#### Scenario: Pinch zoom on a touch device
- **GIVEN** the workspace is open on a touch device
- **WHEN** the user pinches to zoom
- **THEN** the page scales
- **AND** neither a maximum scale nor a scalability restriction prevents it

## MODIFIED Requirements

### Requirement: Proposal Selection and Ordering
The system SHALL let the user select or deselect each proposal through a control that is operable with a single activation and without hovering, and SHALL track and display the order in which proposals were selected.

#### Scenario: User selects a proposal
- GIVEN a proposal is currently unselected
- WHEN the user activates its selection control
- THEN the proposal becomes selected and is assigned the next sequential selection-order number
- AND the selection counter increments by 1
- AND a small badge showing its selection-order number appears next to the selection control

#### Scenario: User deselects a proposal
- GIVEN a selected proposal with a selection-order number
- WHEN the user activates its selection control
- THEN the proposal becomes unselected and loses its selection-order number
- AND every other selected proposal whose order number was greater than the deselected one has its order number decremented by 1
- AND the selection counter decrements by 1

#### Scenario: Editing a proposal's comment does not change its selection
- GIVEN a selected proposal whose comment is being edited
- WHEN the user interacts with the comment field
- THEN the proposal's selection state is unaffected

### Requirement: Responsive Sidebar Navigation
The system SHALL present the session sidebar as a slide-out sheet on small (mobile/`lg`-breakpoint-below) viewports and as a collapsible fixed sidebar on large viewports. On viewports too narrow for the top bar to carry the section tabs, the sheet SHALL also carry them.

#### Scenario: Mobile viewport shows a sheet-based sidebar
- GIVEN the viewport is below the `lg` breakpoint
- WHEN the user taps the floating menu button
- THEN a slide-out sheet opens from the left showing the session list and "新しいセッション" action

#### Scenario: Desktop viewport shows a collapsible fixed sidebar
- GIVEN the viewport is at or above the `lg` breakpoint
- WHEN the user clicks the sidebar's collapse/expand toggle
- THEN the fixed left sidebar collapses to an icon-only rail or expands to show full session details, without affecting the main content's session state

#### Scenario: Sheet fits a narrow viewport
- GIVEN a viewport 320px wide
- WHEN the sheet opens
- THEN the sheet and its contents fit within the viewport width
- AND the session list scrolls within the sheet's own height rather than being cut off by browser chrome
