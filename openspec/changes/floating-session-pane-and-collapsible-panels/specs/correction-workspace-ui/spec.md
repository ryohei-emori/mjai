## MODIFIED Requirements

### Requirement: Responsive Sidebar Navigation
The system SHALL present the session list in one of two mutually exclusive presentations — **docked** (a fixed column inside the workspace layout) or **floating** (an overlay panel above the workspace) — SHALL let the user switch between them at any viewport width from an always-visible trigger, SHALL remember the chosen presentation across reloads, and SHALL reclaim the docked column's horizontal space for the center and right panes whenever the presentation is floating. Below the `lg` breakpoint only the floating presentation is offered.

#### Scenario: Desktop viewport shows a collapsible fixed sidebar
- GIVEN the viewport is at or above the `lg` breakpoint and the session pane presentation is docked
- WHEN the workspace renders
- THEN the session list is rendered as a fixed-width column to the left of the center pane
- AND no overlay or backdrop is shown
- AND a trigger is available to collapse that column away from the layout

#### Scenario: Switching to floating widens the work area
- GIVEN the viewport is at or above the `lg` breakpoint and the session pane presentation is docked
- WHEN the user activates the session-pane trigger
- THEN the docked session column is removed from the layout
- AND the center pane and the right pane together occupy the full width previously shared with that column
- AND the session list is available as a floating overlay panel

#### Scenario: Trigger is always reachable
- GIVEN any viewport width and any session-pane presentation
- WHEN the workspace renders
- THEN a labelled session-pane trigger control is visible in the top app bar
- AND the trigger reports its current state via `aria-expanded`

#### Scenario: Mobile viewport shows a sheet-based sidebar
- GIVEN the viewport is below the `lg` breakpoint
- WHEN the user activates the session-pane trigger
- THEN the floating overlay panel opens from the left showing the session list and its search field
- AND no docked session column is rendered at that viewport width

#### Scenario: Session switching from the floating panel
- GIVEN the floating session panel is open
- WHEN the user selects a session from it
- THEN that session becomes the active session exactly as selecting it from the docked column would
- AND the floating panel closes

#### Scenario: Dismissing the floating panel
- GIVEN the floating session panel is open
- WHEN the user clicks the backdrop outside the panel, or presses `Escape`
- THEN the panel closes without changing the active session
- AND keyboard focus returns to the session-pane trigger

#### Scenario: Focus stays inside the open floating panel
- GIVEN the floating session panel is open
- WHEN the user cycles focus forward past the panel's last focusable control
- THEN focus wraps to the panel's first focusable control rather than reaching the workspace behind the overlay

### Requirement: Session Pane Presentation Persistence
The system SHALL persist the user's docked/floating session-pane choice in browser local storage and SHALL restore it on the next visit. When no choice has been persisted, the system SHALL default to docked at or above the `lg` breakpoint and to floating below it. A corrupt or unreadable stored value SHALL fall back to that viewport-based default without breaking the workspace.

#### Scenario: Choice survives a reload
- GIVEN the user has switched the session pane to floating at a desktop viewport
- WHEN the page is fully reloaded
- THEN the session pane is still floating and the center/right panes still occupy the full width

#### Scenario: First visit defaults by viewport
- GIVEN no session-pane presentation has ever been persisted
- WHEN the workspace first renders at or above the `lg` breakpoint
- THEN the session pane is docked
- AND when it first renders below the `lg` breakpoint the session pane is floating

#### Scenario: Unreadable stored preference is ignored
- GIVEN the persisted session-pane preference is missing, malformed, or local storage is unavailable
- WHEN the workspace renders
- THEN the viewport-based default presentation is used
- AND the workspace renders without error

## ADDED Requirements

### Requirement: Collapsible Exemplar Translation Card
The system SHALL present the optional exemplar-translation field (模範回答訳文) inside a collapsible card that is collapsed by default, SHALL expose a labelled disclosure control in the card header reporting its state via `aria-expanded`, and SHALL keep the field's value unchanged when it is collapsed or expanded. When the field is non-blank while collapsed, the header SHALL show an indicator so the entered text is not silently hidden.

#### Scenario: Exemplar card starts collapsed
- GIVEN a session is active and no exemplar-card disclosure state has been persisted
- WHEN the center pane renders
- THEN the exemplar-translation card header is visible
- AND its textarea is not shown
- AND the vertical space the textarea would occupy is available to the TARGET TEXT card and the generate control

#### Scenario: User expands and collapses the card
- GIVEN the exemplar-translation card is collapsed
- WHEN the user activates its disclosure control
- THEN the exemplar textarea becomes visible and editable
- AND activating the control again collapses it

#### Scenario: Collapsing does not discard entered text
- GIVEN the user has typed a non-blank exemplar translation with the card expanded
- WHEN the user collapses the card
- THEN the exemplar translation value is retained in state and in its persisted draft
- AND expanding the card again shows the same text

#### Scenario: Non-blank collapsed field is indicated
- GIVEN the exemplar-translation field is non-blank
- WHEN the card is collapsed
- THEN the card header shows an indicator that content has been entered

#### Scenario: Collapsed exemplar still reaches generation
- GIVEN the exemplar-translation field is non-blank and its card is collapsed
- WHEN the user clicks "AI提案を生成"
- THEN the exemplar translation is passed to suggestion generation exactly as it would be when the card is expanded

### Requirement: Exemplar Card Disclosure Persistence
The system SHALL persist the exemplar-card expanded/collapsed state in browser local storage and SHALL restore it on the next visit, defaulting to collapsed when nothing is persisted or the stored value cannot be read.

#### Scenario: Expanded state survives a reload
- GIVEN the user has expanded the exemplar-translation card
- WHEN the page is fully reloaded
- THEN the exemplar-translation card is still expanded

#### Scenario: Unreadable stored disclosure state falls back to collapsed
- GIVEN the persisted exemplar-card disclosure state is missing, malformed, or local storage is unavailable
- WHEN the center pane renders
- THEN the exemplar-translation card is collapsed
- AND the workspace renders without error
