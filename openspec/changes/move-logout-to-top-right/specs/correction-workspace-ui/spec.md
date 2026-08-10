## ADDED Requirements

### Requirement: Global Logout Button Placement
The system SHALL display a logout button in the top-right corner of the main application area, visible to authenticated users regardless of sidebar state or viewport size.

#### Scenario: Logout button visible on desktop with sidebar open
- **WHEN** the user is authenticated and the desktop sidebar is expanded
- **THEN** a logout button is visible in the top-right area of the main content
- **AND** the sidebar does NOT contain a logout button

#### Scenario: Logout button visible on desktop with sidebar collapsed
- **WHEN** the user is authenticated and the desktop sidebar is collapsed
- **THEN** a logout button is visible in the top-right area of the main content

#### Scenario: Logout button visible on mobile viewport
- **WHEN** the user is authenticated on a mobile viewport (below `lg` breakpoint)
- **THEN** a logout button is visible in the top-right area of the main content
- **AND** the mobile sidebar sheet does NOT contain a logout button

#### Scenario: Logout triggers sign out
- **WHEN** the user clicks the global logout button
- **THEN** the `signOut()` function from the auth context is called
- **AND** the user is signed out and redirected to the login screen

## MODIFIED Requirements

### Requirement: Responsive Sidebar Navigation
The system SHALL present the session sidebar as a slide-out sheet on small (mobile/`lg`-breakpoint-below) viewports and as a collapsible fixed sidebar on large viewports. The sidebar SHALL contain only session management controls (session list, create new session, collapse/expand toggle) and SHALL NOT contain a logout button.

#### Scenario: Mobile viewport shows a sheet-based sidebar
- **GIVEN** the viewport is below the `lg` breakpoint
- **WHEN** the user taps the floating menu button
- **THEN** a slide-out sheet opens from the left showing the session list and "新しいセッション" action
- **AND** the sheet does NOT contain a logout button

#### Scenario: Desktop viewport shows a collapsible fixed sidebar
- **GIVEN** the viewport is at or above the `lg` breakpoint
- **WHEN** the user clicks the sidebar's collapse/expand toggle
- **THEN** the fixed left sidebar collapses to an icon-only rail or expands to show full session details, without affecting the main content's session state
- **AND** the sidebar does NOT contain a logout button
