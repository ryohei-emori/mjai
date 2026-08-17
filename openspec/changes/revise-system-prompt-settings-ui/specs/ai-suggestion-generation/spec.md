## ADDED Requirements

### Requirement: On-device generation honours the shared correction prompt

On-device (offline) suggestion generation MUST use the operator's stored shared correction prompt as its rules body when one is stored, so that turning offline mode on changes where inference runs and not what the application is asking for. When no prompt is stored, or the stored prompt cannot be retrieved, on-device generation MUST fall back to its built-in prompt, which is deliberately condensed for a small on-device model.

The response contract — the JSON-only instruction, the response schema, and the worked example — MUST continue to be supplied by code on the on-device path, appended after the rules body, exactly as on the cloud path.

This requirement governs which prompt the on-device path uses. It MUST NOT be read as licence to load or invoke the on-device model outside explicit offline mode; automatic fallback from a failed cloud call to on-device inference remains prohibited.

#### Scenario: Stored prompt reaches the on-device model

- **GIVEN** a custom shared prompt is stored
- **AND** offline mode is enabled
- **WHEN** suggestions are generated
- **THEN** the prompt sent to the on-device model contains the stored rules body, followed by the code-owned response contract and the worked example

#### Scenario: Unset prompt leaves the on-device prompt unchanged

- **GIVEN** no custom shared prompt is stored
- **AND** offline mode is enabled
- **WHEN** suggestions are generated
- **THEN** the prompt is byte-identical to the built-in offline prompt that was sent before the stored prompt could reach this path

#### Scenario: Settings unavailable while offline

- **GIVEN** offline mode is enabled and the stored prompt cannot be fetched
- **WHEN** suggestions are generated
- **THEN** generation completes using the built-in offline prompt, and the failure to read settings does not surface as a generation failure

#### Scenario: Cloud failure still does not start the on-device model

- **GIVEN** offline mode is disabled
- **WHEN** every cloud provider fails
- **THEN** the on-device model is not loaded or called, and the job fails with the cloud error
