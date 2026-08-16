## ADDED Requirements

### Requirement: Prompt Settings Entry Point

The workspace top bar SHALL provide an enabled settings control in its top-right control group that opens the AI prompt settings surface. The control SHALL be reachable and operable by keyboard, SHALL carry an accessible name describing that it opens settings, and SHALL replace the current non-functional placeholder. Opening or closing it SHALL NOT alter the active session, draft text, queued jobs, or displayed suggestions.

#### Scenario: Settings control opens the prompt settings

- **WHEN** the user activates the settings control in the top bar
- **THEN** the prompt settings surface opens

#### Scenario: Settings control is keyboard operable

- **WHEN** the user moves focus to the settings control and activates it with the keyboard
- **THEN** the prompt settings surface opens and receives focus

#### Scenario: Workspace state is untouched

- **GIVEN** the workspace holds draft text and generated suggestions
- **WHEN** the user opens and then closes the prompt settings without saving
- **THEN** the draft text, suggestions, and queued jobs are unchanged

### Requirement: Prompt Settings Surface Behaviour

The prompt settings surface SHALL present the effective AI correction prompt in an editable multi-line field large enough for a long rule document, and SHALL show whether the effective prompt is the built-in default or a customized one — including, when customized, who last saved it and when. It SHALL offer saving the edited text, resetting to the built-in default, and dismissing without saving. Saving SHALL be unavailable while the text is unchanged or fails validation, validation and save failures SHALL be shown in the surface next to the field rather than only as a transient notification, and a successful save SHALL confirm that the shared prompt was updated. Dismissing SHALL discard local edits without writing them.

Because the prompt applies to cloud generation only, the surface SHALL state that offline mode uses its own built-in prompt.

#### Scenario: Surface loads the effective prompt

- **WHEN** the prompt settings surface opens
- **THEN** the editable field is pre-filled with the effective prompt
- **AND** the surface indicates whether that text is the built-in default or a customized prompt

#### Scenario: Customized prompt shows attribution

- **GIVEN** a custom prompt was saved by an account
- **WHEN** the surface opens
- **THEN** it shows that account and the time of the last save

#### Scenario: Save is gated on a valid change

- **WHEN** the text is unchanged from what is stored, or is empty or over the length limit
- **THEN** the save action is unavailable or rejected with the reason shown beside the field

#### Scenario: Save failure keeps the user's text

- **GIVEN** the user edited the prompt and saving fails
- **WHEN** the failure is reported
- **THEN** the message appears in the surface and the edited text is still present for a retry

#### Scenario: Reset restores the default text

- **WHEN** the user resets to the built-in default and confirms
- **THEN** the field shows the built-in default text
- **AND** the surface reports that no custom prompt is stored

#### Scenario: Dismiss discards edits

- **GIVEN** the user typed changes into the field
- **WHEN** the user dismisses the surface without saving
- **THEN** reopening it shows the stored prompt, not the discarded edits

#### Scenario: Offline scope is stated

- **WHEN** the prompt settings surface is shown
- **THEN** it states that the prompt applies to cloud generation and that offline mode uses its own built-in prompt

### Requirement: Generating Model Is Shown As Metadata

When a suggestion set is displayed, the workspace SHALL show which model produced it as an unobtrusive metadata label reading in the form `<model> used`. The label SHALL use metadata-level typography and muted colour, SHALL sit outside the suggestion cards' content area so it neither overlaps nor displaces suggestion text or controls, and SHALL be omitted entirely when the generating model is unknown rather than showing a placeholder. For an offline generation the label SHALL name the local model.

The existing cloud-versus-local indicator SHALL reflect the source of the most recent generation instead of remaining permanently absent.

#### Scenario: Cloud generation shows its model

- **WHEN** a cloud generation completes and its suggestions are displayed
- **THEN** a metadata label naming the model that produced them is shown near the results

#### Scenario: Offline generation shows the local model

- **WHEN** an offline generation completes and its suggestions are displayed
- **THEN** the metadata label names the local model

#### Scenario: Unknown model shows no label

- **GIVEN** a displayed suggestion set with no recorded model
- **WHEN** the results render
- **THEN** no model label is shown and the layout is unchanged

#### Scenario: Label does not disturb the suggestions

- **GIVEN** suggestions are displayed with a model label
- **WHEN** the panel renders at a narrow width
- **THEN** the suggestion cards keep their existing position and controls, with the label wrapping or truncating instead of pushing them

#### Scenario: Source indicator matches the last generation

- **WHEN** a generation completes
- **THEN** the cloud-versus-local indicator shows the source actually used for that generation

### Requirement: Restored History Round Shows Its Recorded Model

WHEN a saved correction round is restored into the workspace, the workspace SHALL show the model recorded for that round using the same metadata label, and SHALL show no label for rounds saved before provenance was recorded.

#### Scenario: Restored round with recorded provenance

- **GIVEN** a saved round whose stored record names the generating model
- **WHEN** the user restores it
- **THEN** the metadata label names that model

#### Scenario: Restored legacy round

- **GIVEN** a saved round stored before provenance was recorded
- **WHEN** the user restores it
- **THEN** no model label is shown
