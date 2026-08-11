## MODIFIED Requirements

### Requirement: Responsive Sidebar Navigation
The system SHALL present navigation via a TopAppBar with horizontal tabs (Sessions/Dashboard/Archive) on all viewports, with the session list displayed in a dedicated left pane below the TopAppBar.

#### Scenario: TopAppBar displays navigation tabs
- **WHEN** the workspace UI is rendered
- **THEN** a TopAppBar SHALL be displayed at the top with:
  - MJAI logo/title on the left
  - Navigation tabs: Sessions (active by default), Dashboard, Archive
  - New Session button
  - Notification bell icon button and Settings icon button (Settings is UI-only, no functional settings screen)
  - User avatar (Google account profile picture) and logout area on the right

#### Scenario: User avatar displays Google profile picture
- **WHEN** a user is authenticated via Google OAuth
- **THEN** the TopAppBar user avatar SHALL display the user's Google account profile picture from `user_metadata.avatar_url` or `user_metadata.picture`
- AND if no avatar URL is available, a default account icon SHALL be displayed

#### Scenario: Notification bell shakes on job completion
- **WHEN** a job transitions to "completed" status
- **THEN** the notification bell icon in the TopAppBar SHALL play a brief shake/wiggle animation (CSS keyframe, ~0.5s duration)

#### Scenario: Dashboard and Archive tabs show placeholder
- **WHEN** the user clicks the Dashboard or Archive tab
- **THEN** a "Coming Soon" or disabled placeholder content SHALL be displayed
- AND the Sessions tab remains the only functional navigation target

#### Scenario: Settings icon is UI-only
- **WHEN** the user clicks the Settings icon in the TopAppBar
- **THEN** no action SHALL be taken (no modal, no settings screen)
- AND the Settings icon MAY show a tooltip indicating "Coming Soon" or be visually styled as inactive/disabled

#### Scenario: Session list is displayed in left pane
- **WHEN** the viewport is at or above the `lg` breakpoint
- **THEN** the session list SHALL be displayed in a fixed left pane (not a collapsible sidebar)
- AND a search input SHALL be displayed above the session list

#### Scenario: Mobile viewport shows responsive layout
- **WHEN** the viewport is below the `lg` breakpoint
- **THEN** the TopAppBar SHALL remain visible
- AND the session list MAY be accessible via a slide-out sheet or collapsed state

### Requirement: Session List Display
The system SHALL display session cards with status pills indicating completion status and visual distinction for the active session.

#### Scenario: Sessions load on initial mount
- **WHEN** the page finishes mounting
- **THEN** the UI calls the sessions API to fetch the session list
- AND each returned session is rendered as a card showing:
  - Session name
  - A status pill showing saved count (e.g., "5 Saved") or "Draft" for new sessions
  - Creation date in metadata style

#### Scenario: Active session is visually distinct
- **WHEN** a session is selected as active
- **THEN** the session card SHALL have a visually distinct style (e.g., different background, border, or highlight)

#### Scenario: Session search filters the list
- **WHEN** the user types in the search input above the session list
- **THEN** the displayed sessions SHALL be filtered to match the search query

### Requirement: Three-Pane Layout
The system SHALL display the workspace in a three-pane layout: session list (left), text editor (center), job queue and AI suggestions (right).

#### Scenario: Three-pane layout on desktop
- **WHEN** the viewport is at or above the `lg` breakpoint
- **THEN** the layout SHALL display three distinct panes:
  - Left: Session list with search
  - Center: Source text and target text editors stacked vertically
  - Right: Job queue panel and AI suggestions panel

#### Scenario: Editor pane displays source and target cards
- **WHEN** a session is active
- **THEN** the center pane SHALL display:
  - A "Source Text" card with the original text textarea
  - A "Target Text" card with the target text textarea
  - The "AI提案を生成" button positioned at the bottom-right of the target card

### Requirement: Job Queue Panel Display
The system SHALL display an "Active Jobs" badge and individual job items with progress indicators in the right pane.

#### Scenario: Job queue shows active count
- **WHEN** one or more jobs are processing or queued
- **THEN** the job queue panel header SHALL display an "N Active" badge

#### Scenario: Processing job shows progress
- **WHEN** a job is in "processing" status
- **THEN** the job item SHALL display a progress bar or spinner

#### Scenario: Completed job shows confirm action
- **WHEN** a job is in "completed" status
- **THEN** the job item SHALL be clickable to initiate the HITL confirmation flow
- AND a "確認" (confirm) action indicator SHALL be visible

### Requirement: AI Suggestion Cards with Hover Actions
The system SHALL display AI suggestions as labeled cards (e.g., "Option A", "Option B") with hover-revealed action icons for copy and confirm.

#### Scenario: Suggestion cards show option labels
- **WHEN** AI suggestions are displayed
- **THEN** each suggestion SHALL be displayed as a card with an option label (e.g., "Option A Formal", "Option B Concise")

#### Scenario: Hover reveals action icons
- **WHEN** the user hovers over a suggestion card
- **THEN** copy and confirm/check action icons SHALL become visible

#### Scenario: Clicking confirm selects the suggestion
- **WHEN** the user clicks the confirm/check icon on a suggestion card
- **THEN** that suggestion SHALL be toggled as selected (same as clicking the checkbox)

### Requirement: Icon System Migration
The system SHALL use Material Symbols Outlined icons throughout the UI instead of Lucide React icons.

#### Scenario: Material Symbols font is loaded
- **WHEN** the application loads
- **THEN** the Material Symbols Outlined font SHALL be available via Google Fonts

#### Scenario: Icons use Material Symbols classes
- **WHEN** an icon is displayed in the UI
- **THEN** it SHALL use the Material Symbols Outlined icon font with appropriate icon names

### Requirement: Offline Mode Toggle Preservation
The system SHALL preserve the offline mode (WebLLM) toggle in the new layout, positioned near the Generate button or in a clearly accessible location.

#### Scenario: Offline mode toggle is visible
- **WHEN** a session is active and the target text area is displayed
- **THEN** the オフラインモード checkbox toggle SHALL be visible near the "AI提案を生成" button

#### Scenario: Offline mode toggle functionality unchanged
- **WHEN** the user toggles offline mode
- **THEN** the AI generation SHALL use WebLLM instead of the cloud API
- AND the toggle state SHALL be reflected visually

### Requirement: Toast Notifications Position
The system SHALL continue to display toast notifications in the top-right area, overlaying the TopAppBar if necessary.

#### Scenario: Toast appears in top-right
- **WHEN** a toast notification is triggered (e.g., "処理開始", "完了")
- **THEN** the toast SHALL appear in the top-right corner of the viewport
