## ADDED Requirements

### Requirement: Suggestion Provenance Is Persisted With The History

A correction history record SHALL be able to carry the provenance of the suggestion set it was created from: the LLM provider identifier and the exact model identifier that generated the suggestions. Both fields SHALL be optional on create — a record submitted without them SHALL be accepted and stored with those fields empty — and SHALL be returned when the record is read, so provenance is available to any client and to later analysis of critique quality without reading server logs.

These fields are additive: existing clients that omit them SHALL keep working, and records written before this change SHALL read back with empty provenance rather than failing.

#### Scenario: History created with provenance

- **WHEN** a correction history is created with a provider identifier and a model identifier
- **THEN** both values are stored on that record
- **AND** reading the session's histories returns both values for it

#### Scenario: History created without provenance

- **WHEN** a correction history is created without provenance fields
- **THEN** the record is created successfully
- **AND** reading it returns empty provenance rather than an error

#### Scenario: Records predating provenance are readable

- **GIVEN** history records stored before provenance existed
- **WHEN** they are read
- **THEN** they are returned with empty provenance and all their other fields intact

### Requirement: Provenance Survives Confirmation Of A Pending History

WHEN a history that was persisted at generation time is later promoted from pending to confirmed, its recorded provider and model SHALL be preserved. An update that does not mention provenance SHALL NOT clear it.

#### Scenario: Confirming a pending history keeps its model

- **GIVEN** a pending history stored with a provider and model at generation time
- **WHEN** the user confirms and saves that round
- **THEN** the confirmed record still reports the same provider and model

#### Scenario: Unrelated update does not clear provenance

- **WHEN** a history is updated with fields that do not include provenance
- **THEN** the stored provider and model are unchanged

### Requirement: Provenance Distinguishes Transport From Model

The existing coarse provider field that records whether a round came from the cloud API or the offline local engine SHALL be retained unchanged, and the new provenance fields SHALL be stored separately rather than overloading it. For an offline round, provenance SHALL name the local engine and its model identifier.

#### Scenario: Cloud round records both transport and model

- **WHEN** a cloud-generated round is stored
- **THEN** the coarse field still records that it came from the API
- **AND** the provenance fields record the cloud provider and its model identifier

#### Scenario: Offline round records the local model

- **WHEN** an offline-generated round is stored
- **THEN** the coarse field still records the offline engine
- **AND** the provenance fields record the local engine and its model identifier
