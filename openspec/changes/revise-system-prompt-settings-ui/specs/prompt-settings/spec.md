## ADDED Requirements

### Requirement: Stored Prompt Governs Every Generation Path

The stored shared prompt SHALL be the rules body for every generation path the application offers, including the on-device offline path, so that "the prompt this app critiques with" has one answer rather than one per transport. Where a path has a built-in prompt of its own, that built-in prompt SHALL be used only as the fallback for the case where no custom prompt is stored.

The machine-interface parts of the prompt — the JSON-only instruction, the response schema, and the built-in worked example — SHALL remain owned by code on every path and SHALL be supplied automatically. A stored prompt SHALL therefore be able to lower critique quality but SHALL NOT be able to remove the response contract.

#### Scenario: Offline generation uses the stored prompt

- **GIVEN** a custom prompt is stored
- **WHEN** a suggestion is generated with offline mode enabled
- **THEN** the stored text is the rules body of the prompt sent to the on-device model
- **AND** the response contract and the worked example are still present

#### Scenario: Offline generation with no custom prompt stored

- **GIVEN** no custom prompt is stored
- **WHEN** a suggestion is generated with offline mode enabled
- **THEN** the built-in offline prompt is used, byte-for-byte as it was before the stored prompt could reach this path

#### Scenario: The stored prompt cannot be read

- **GIVEN** the stored prompt cannot be retrieved (offline network, settings outage)
- **WHEN** a suggestion is generated with offline mode enabled
- **THEN** generation proceeds with the built-in offline prompt rather than failing

#### Scenario: Enabling offline mode is still an explicit choice

- **GIVEN** a custom prompt is stored
- **WHEN** a cloud generation fails
- **THEN** the on-device model is neither loaded nor called, because this requirement governs which prompt that path uses and not when that path runs

### Requirement: The Editor Discloses Where Supplied Text Is Inserted

The prompt editor SHALL disclose, in the editor itself, the order in which the complete prompt is assembled: the operator's edited body, the exemplar reference rules, the code-owned output contract, the built-in worked example, and the supplied SOURCE, EXEMPLAR and TARGET text. It SHALL state which of those pieces are conditional — the exemplar rules and the exemplar text appear only when the operator actually pasted an exemplar — so that an operator writing a rule about the exemplar can tell whether the exemplar is in context at all.

The disclosed order SHALL be derived from a single description that the prompt builders are verified against, so the disclosure cannot drift from what is actually sent.

#### Scenario: Assembly order is visible without leaving the editor

- **WHEN** the operator opens the prompt editor
- **THEN** the assembly order is shown, with the operator's own prompt identified as the first piece and the supplied text identified as following it

#### Scenario: Conditional pieces are marked as conditional

- **WHEN** the operator reads the disclosed assembly order
- **THEN** the exemplar rules and the exemplar text are marked as present only when an exemplar was supplied

#### Scenario: Disclosure matches what is sent

- **WHEN** the prompt builders assemble a prompt with an exemplar supplied
- **THEN** the pieces appear in the order the editor discloses
- **AND** when no exemplar is supplied, neither exemplar piece appears

### Requirement: The Editor Is Sized For The Document It Edits

The prompt editor SHALL use a dialog width intended for long-form editing rather than the default prose-dialog width, and its input SHALL offer a substantially taller editing surface on viewports with the room for one. Both sizes SHALL come from named sizes recorded in the design documentation rather than from values chosen at the one call site, so a second long-form editor is sized consistently.

Sizing SHALL NOT regress the existing small-viewport guarantee: the footer buttons SHALL remain reachable when the on-screen keyboard is open.

#### Scenario: Wide editor on a desktop viewport

- **WHEN** the prompt editor is opened on a wide viewport
- **THEN** the dialog uses the long-form editing width, not the default prose width

#### Scenario: Footer stays reachable on a phone

- **WHEN** the prompt editor is opened on a narrow viewport with the on-screen keyboard open
- **THEN** the input yields height and the footer buttons remain reachable

### Requirement: The Editor's Copy Is English

Every string the prompt editor presents SHALL be in English: its title, its explanation, the customized/default indicator, the attribution line, the character counter, validation messages, request-failure messages, the footer buttons, and the confirmation the operator receives after saving or resetting. The explanation SHALL state that the prompt is shared across all users and sessions and that the JSON output format is appended automatically, so the operator does not write it.

#### Scenario: Opening the editor

- **WHEN** the operator opens the prompt editor
- **THEN** the title, explanation, indicator, counter and buttons are English

#### Scenario: Rejecting an invalid prompt

- **WHEN** the operator empties the prompt or exceeds the length limit
- **THEN** the reason is stated in English
