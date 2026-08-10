## Purpose

Restricts access to the MJAI application to a single authorized person by requiring Google sign-in and verifying the signed-in identity against an allow-listed email address, both in the frontend and on every protected backend endpoint.

## ADDED Requirements

### Requirement: Unauthenticated Access Redirected to Login
The frontend SHALL redirect any unauthenticated user to a login screen instead of rendering the correction workspace (sessions, histories, proposals, suggestion generation).

#### Scenario: Visiting the app without a session
- **WHEN** a user with no active session loads the application
- **THEN** the frontend displays the login screen and does not render session data or fetch protected endpoints

#### Scenario: Session expires while app is open
- **WHEN** a logged-in user's session/token expires or becomes invalid during use
- **THEN** the frontend detects the resulting authentication failure and redirects the user to the login screen

### Requirement: Google Sign-In
The system SHALL let a user authenticate using their Google account via Supabase Auth's OAuth flow.

#### Scenario: User signs in with Google
- **WHEN** a user on the login screen chooses to sign in with Google and completes Google's consent flow
- **THEN** the system establishes an authenticated session for that user and grants access to the application if the account passes the allow-list check

### Requirement: Single Allow-Listed Email Enforcement
The system SHALL deny access to any authenticated Google account whose verified email address does not match the single allow-listed email, regardless of whether Google/Supabase authentication itself succeeded. This check SHALL be enforced on the server side, not only in frontend code.

#### Scenario: Allowed user signs in
- **WHEN** the authenticated user's verified email matches the configured allow-listed email
- **THEN** the system grants the user access to the application and its protected endpoints

#### Scenario: Disallowed user signs in
- **WHEN** a user successfully authenticates with Google/Supabase but their verified email does not match the configured allow-listed email
- **THEN** the system denies application access, signs the user out or refuses to establish an authorized session, and does not return any protected data

#### Scenario: Disallowed user calls a protected endpoint directly
- **WHEN** a request to a protected backend endpoint carries a valid, verifiable token whose email claim is not the allow-listed email
- **THEN** the backend rejects the request with an authorization error and performs no data access

### Requirement: Protected Backend Endpoints Require Valid Session
Backend endpoints that read or write session, history, or proposal data SHALL reject requests that do not carry a valid, verifiable authentication token.

#### Scenario: Request without a token
- **WHEN** a request to a protected endpoint (session, history, or proposal read/write) is made without an authentication token
- **THEN** the backend rejects the request with an authentication error and performs no data access

#### Scenario: Request with an invalid or expired token
- **WHEN** a request to a protected endpoint carries a token that fails verification or has expired
- **THEN** the backend rejects the request with an authentication error and performs no data access

#### Scenario: Request with a valid token for the allowed user
- **WHEN** a request to a protected endpoint carries a valid, unexpired token whose email claim matches the allow-listed email
- **THEN** the backend processes the request normally

### Requirement: Session Persistence Across Reloads
The system SHALL keep an authenticated user logged in across page reloads and new browser tabs until the user explicitly logs out or the underlying session/token expires.

#### Scenario: Reloading the page while logged in
- **WHEN** an authenticated, allow-listed user reloads the page or reopens the app in a new tab before their session expires
- **THEN** the frontend restores the authenticated state without requiring the user to sign in again

### Requirement: Logout
The system SHALL let an authenticated user explicitly log out, ending their session and returning them to the login screen.

#### Scenario: User logs out
- **WHEN** an authenticated user triggers logout
- **THEN** the system invalidates the local session, and subsequent loads of the application redirect the user to the login screen until they sign in again
