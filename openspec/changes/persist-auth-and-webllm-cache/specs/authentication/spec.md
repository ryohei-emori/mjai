## MODIFIED Requirements

### Requirement: Session Persistence Across Reloads
The system SHALL keep an authenticated user logged in across page reloads, browser tab closures, and browser session restarts until the user explicitly logs out or the underlying session/token expires. The frontend SHALL restore existing valid sessions on page load by checking for persisted auth state before showing any login screen.

#### Scenario: Reloading the page while logged in
- **WHEN** an authenticated, allow-listed user reloads the page before their session expires
- **THEN** the frontend restores the authenticated state from persisted storage without requiring the user to sign in again
- **AND** the user sees the main application interface, not the login screen

#### Scenario: Closing and reopening browser tab
- **WHEN** an authenticated user closes the browser tab, then reopens the application URL in a new tab before their session expires
- **THEN** the frontend restores the authenticated state from persisted storage without requiring the user to sign in again

#### Scenario: Closing and reopening browser entirely
- **WHEN** an authenticated user closes the browser entirely, then reopens the browser and navigates to the application URL before their session expires
- **THEN** the frontend restores the authenticated state from localStorage without requiring the user to sign in again

#### Scenario: Session check happens before UI rendering
- **WHEN** the application loads
- **THEN** the frontend SHALL check for an existing valid session before rendering either the login screen or the main application
- **AND** the frontend SHALL show a loading state while the session check is in progress

#### Scenario: Logout clears only auth state
- **WHEN** an authenticated user clicks the logout button
- **THEN** the frontend clears Supabase auth state (localStorage keys related to authentication)
- **AND** the frontend does NOT clear the browser's Cache API entries or IndexedDB entries used by WebLLM for model weights
- **AND** the user is redirected to the login screen

## ADDED Requirements

### Requirement: WebLLM Model Cache Independence from Auth
The system SHALL NOT clear WebLLM model cache (stored in browser Cache API / IndexedDB by `@mlc-ai/web-llm`) when the user logs out or when auth state is cleared. Model weights SHALL persist independently of authentication state.

#### Scenario: Logout preserves model cache
- **WHEN** an authenticated user who has previously loaded the WebLLM model clicks the logout button
- **THEN** the WebLLM model weights remain in the browser's Cache API
- **AND** a subsequent login by the same or different user can reuse the cached model without re-downloading

#### Scenario: Auth token refresh preserves model cache
- **WHEN** the Supabase client automatically refreshes an expiring access token
- **THEN** the WebLLM model weights and engine state remain unaffected

### Requirement: WebLLM Cache Reuse Across Sessions
The system SHALL reuse cached WebLLM model weights across page navigations, reloads, and browser sessions, downloading only on cache miss.

#### Scenario: Page reload reuses cached model
- **WHEN** a user who has previously loaded the WebLLM model reloads the page
- **THEN** the WebLLM engine initialization detects the cached weights
- **AND** the model loading progress indicator shows rapid completion (loading from cache) rather than a full download

#### Scenario: First visit downloads model
- **WHEN** a user visits the application for the first time or after clearing browser cache
- **THEN** the WebLLM engine downloads the full model weights
- **AND** the model loading progress indicator shows download progress

#### Scenario: Cache API persists across browser sessions
- **WHEN** a user closes the browser entirely and reopens it
- **THEN** the WebLLM model weights remain in the Cache API (browser default behavior, not cleared by MJAI)
- **AND** the next model initialization reuses the cached weights
