## Purpose

Lets the people who judge critique quality edit the AI correction prompt themselves, storing it as one shared record in the application database so a change takes effect for everyone on the next generation and never has to be re-entered after signing out or switching browsers.

## ADDED Requirements

### Requirement: Shared Prompt Record

The system SHALL store the editable AI correction prompt as a single global record in the application database, shared by every authenticated user rather than scoped per user, per device, or per browser session. The record SHALL survive sign-out, sign-in from another browser or machine, and application redeploy. Client-side storage (for example browser local storage) SHALL NOT be the system of record for this prompt.

#### Scenario: Saved prompt is visible to another session

- **GIVEN** a user has saved a custom prompt
- **WHEN** any other allow-listed user opens the prompt settings from a different browser or after signing out and in again
- **THEN** the same custom prompt text is shown, without re-entry

#### Scenario: Saved prompt survives redeploy

- **GIVEN** a custom prompt is stored
- **WHEN** the application is redeployed
- **THEN** the stored prompt is still the effective prompt, because it is read from the database rather than from application code or client storage

#### Scenario: No custom prompt stored yet

- **GIVEN** no custom prompt has ever been saved
- **WHEN** the prompt settings are read
- **THEN** the built-in default prompt text is returned as the effective prompt
- **AND** the response indicates that the prompt is not customized

### Requirement: Prompt Read Contract

The system SHALL expose an authenticated read that returns, in one response: the effective prompt text, the built-in default prompt text, whether a custom prompt is stored, and — when one is stored — when it was last updated and the identity (email) of the account that saved it. Returning the default text alongside the effective text is required so a client can offer "reset to default" and show a difference without hardcoding a copy of the prompt.

#### Scenario: Read returns effective and default text

- **GIVEN** a custom prompt is stored
- **WHEN** a client reads the prompt settings
- **THEN** the response contains the stored text as the effective prompt, the built-in default text as a separate field, a customized flag that is true, the last-updated timestamp, and the editor's email

#### Scenario: Read reports attribution only when customized

- **GIVEN** no custom prompt is stored
- **WHEN** a client reads the prompt settings
- **THEN** the customized flag is false
- **AND** no last-updated timestamp or editor identity is reported

### Requirement: Prompt Update Contract

The system SHALL expose an authenticated update that replaces the shared prompt with submitted text, and SHALL record the update time and the submitting account's email. The update SHALL reject text that is empty or whitespace-only, and SHALL reject text longer than a documented maximum length, in both cases with a client error whose message states the reason and, for the length case, the limit — leaving the previously stored prompt unchanged. On success the response SHALL report the newly stored state in the same shape as the read contract, so the client never has to guess what was persisted.

Concurrent edits SHALL resolve as last-write-wins without locking or version conflicts; the recorded timestamp and editor identity make the winning edit attributable.

#### Scenario: Valid prompt is stored and attributed

- **WHEN** an allow-listed user submits non-empty prompt text within the length limit
- **THEN** the text becomes the effective prompt
- **AND** the response reports it as customized with the submitting user's email and the update time

#### Scenario: Empty prompt is rejected

- **WHEN** a user submits empty or whitespace-only prompt text
- **THEN** the request fails with a client error explaining that the prompt cannot be empty
- **AND** the previously effective prompt is unchanged

#### Scenario: Oversized prompt is rejected

- **WHEN** a user submits prompt text longer than the maximum allowed length
- **THEN** the request fails with a client error stating the maximum length
- **AND** the previously effective prompt is unchanged

#### Scenario: Second edit wins without a conflict error

- **GIVEN** two users read the same prompt and both submit edits
- **WHEN** the second update is processed
- **THEN** it succeeds and its text becomes effective
- **AND** the recorded editor identity and timestamp are those of the second update

### Requirement: Reset To Built-In Default

The system SHALL expose an authenticated reset that discards the stored custom prompt so the built-in default becomes effective again. Reset SHALL be idempotent: resetting when no custom prompt is stored SHALL succeed and report the default as effective rather than failing. Reset exists as the recovery path for an edit that degrades generation quality, so it SHALL NOT depend on the stored prompt being readable, parseable, or valid.

#### Scenario: Reset restores the default

- **GIVEN** a custom prompt is stored
- **WHEN** an allow-listed user resets the prompt
- **THEN** subsequent reads report the built-in default as effective and the customized flag as false
- **AND** subsequent generations use the built-in default

#### Scenario: Reset with no custom prompt stored

- **GIVEN** no custom prompt is stored
- **WHEN** a user resets the prompt
- **THEN** the request succeeds and reports the built-in default as effective

### Requirement: Prompt Settings Authorization

Reading, updating, and resetting the prompt SHALL require the same authentication and allow-list authorization as the rest of the application's data API. Unauthenticated requests SHALL be rejected without disclosing prompt content, and authenticated-but-not-allow-listed requests SHALL be refused.

#### Scenario: Unauthenticated read is refused

- **WHEN** a client reads the prompt settings without valid credentials
- **THEN** the request is rejected as unauthenticated
- **AND** no prompt text is returned

#### Scenario: Non-allow-listed account cannot edit

- **GIVEN** a request carrying valid credentials for an account outside the allow-list
- **WHEN** it attempts to update or reset the prompt
- **THEN** the request is refused as forbidden
- **AND** the stored prompt is unchanged

### Requirement: Prompt Store Failures Do Not Block Generation

A failure to read the stored prompt SHALL NOT fail suggestion generation: the system SHALL fall back to the built-in default prompt, generate as usual, and record the failure in server logs. By contrast, a failure to read or write the prompt from the settings surface SHALL be reported to the user rather than silently ignored, so an edit is never believed to be saved when it was not.

#### Scenario: Prompt store unavailable during generation

- **GIVEN** the prompt store cannot be read (unavailable or timing out)
- **WHEN** a user generates suggestions
- **THEN** generation proceeds using the built-in default prompt
- **AND** the failure is logged server-side

#### Scenario: Save failure is surfaced

- **GIVEN** the prompt store rejects or fails an update
- **WHEN** the user attempts to save an edited prompt
- **THEN** the user is shown that the save failed
- **AND** the editor still holds the user's text so the edit is not lost
