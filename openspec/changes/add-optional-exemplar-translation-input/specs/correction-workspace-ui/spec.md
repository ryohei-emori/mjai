## ADDED Requirements

### Requirement: Optional exemplar translation input

The system SHALL provide an optional editable exemplar-translation field (模範回答訳文) for the active session, kept in local component state as the user types, and SHALL present it with an MD3 card and bilingual English-primary header consistent with the SOURCE TEXT / TARGET TEXT pattern in `docs/UI-DESIGN.md` (e.g. `EXEMPLAR TEXT (模範回答訳文)` — exact wording may be refined at implement time without changing this requirement). The field SHALL NOT be required for AI suggestion generation: the "AI提案を生成" control SHALL remain governed solely by non-blank TARGET TEXT (and existing in-progress guards), regardless of whether the exemplar field is empty or filled.

#### Scenario: User edits the exemplar translation

- **GIVEN** a session is active
- **WHEN** the user types or pastes into the exemplar-translation textarea
- **THEN** the active session's exemplar translation is updated immediately in the UI state (no explicit save action)

#### Scenario: Generate remains available when exemplar is empty

- **GIVEN** a session is active with non-blank TARGET TEXT and an empty exemplar-translation field
- **WHEN** the user clicks "AI提案を生成"
- **THEN** generation proceeds normally (cloud API and/or WebLLM path) without requiring the exemplar field
- **AND** no validation error is shown for the empty exemplar field

#### Scenario: Exemplar field does not enable generate by itself

- **GIVEN** a session is active with blank TARGET TEXT and a non-blank exemplar-translation field
- **WHEN** the generate control is evaluated
- **THEN** "AI提案を生成" remains disabled (same rule as today: TARGET TEXT must be non-blank)

#### Scenario: Exemplar text is not cleared after queuing a generation job

- **GIVEN** a session has non-blank SOURCE TEXT and non-blank exemplar translation
- **WHEN** the user clicks "AI提案を生成" and the TARGET TEXT is successfully queued
- **THEN** the TARGET TEXT field is cleared as today
- **AND** the SOURCE TEXT and exemplar-translation fields are left untouched

### Requirement: Exemplar translation draft persistence

The system SHALL persist the exemplar-translation field per-session to browser `localStorage` (debounced) together with the existing SOURCE/TARGET draft persistence, restore it when the session becomes active or the page reloads, and clear it on confirmed save alongside the other draft text fields.

#### Scenario: Reloading restores exemplar translation

- **GIVEN** a session has a non-blank exemplar translation that has been persisted to `localStorage` (past the debounce window)
- **WHEN** the browser page is fully reloaded and the user reopens that session
- **THEN** the exemplar-translation field is restored to its last-persisted value

#### Scenario: Session switch preserves per-session exemplar text

- **GIVEN** two sessions A and B each have distinct, non-blank exemplar translations
- **WHEN** the user switches the active session from A to B and then back to A
- **THEN** session A's exemplar translation is shown exactly as it was before switching away

#### Scenario: Confirmed save clears persisted exemplar draft

- **GIVEN** a session has a persisted exemplar translation in `localStorage`
- **WHEN** the user successfully completes "確定してコピー・保存" for that session
- **THEN** the persisted exemplar-translation draft for that session is cleared from `localStorage` together with the other draft text fields
