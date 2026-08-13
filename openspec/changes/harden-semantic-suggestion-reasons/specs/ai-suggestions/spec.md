## ADDED Requirements

### Requirement: Critique reason MUST include why the correction is needed

Every suggestion's `reason` field（指摘コメント）MUST explain **why the correction is necessary**, in addition to stating what is wrong and/or where. This is a hard content-quality requirement for all critique types (grammar, particles, fluency, meaning mismatch, spelling, etc.)—not optional guidance and not limited to particle additions. A `reason` that only names a missing form or location (e.g. 「缺少「は」在「誰でも」前」) without communicative or grammatical necessity (为什么必须改) MUST be treated as non-compliant with prompt quality rules. Prompts for cloud and WebLLM paths MUST encode this requirement in Simplified Chinese for `reason` fields, consistent with existing Chinese-enforcement constraints.

#### Scenario: Compliant reason states what/where and why

- **WHEN** a suggestion is generated successfully
- **THEN** each suggestion's `reason` includes both the problem identification (what/where) and an explanation of why the correction is needed

#### Scenario: Location-only missing-particle reason is non-compliant

- **WHEN** a `reason` matches a location-only pattern such as 「缺少「X」在…」 (or equivalent) without stating why the particle/form is required
- **THEN** that `reason` fails the documented quality expectation for critique comments (prompt rules forbid it; automated heuristics/fixtures MAY flag it for regression)

#### Scenario: Applies beyond particle additions

- **WHEN** the model flags any issue type (tense, adjective conjugation, fluency, meaning mismatch, etc.)
- **THEN** the corresponding `reason` still MUST include why the change is necessary, not only the surface error label

### Requirement: Avoid false particle inventing and prefer real issues

The system SHALL prompt models to prioritize true meaning mismatches, grammar errors, fluency problems, and spelling mistakes, and MUST instruct models **not** to invent missing particles or other 「缺少」 claims when the Japanese TARGET TEXT is already acceptable. Prompts MUST forbid inventing particles that incorrectly change meaning or are not needed. Existing Chinese-language rules for `reason`/`overallComment` and Japanese rules for `original`/`sourceExcerpt` remain in force.

#### Scenario: Acceptable Japanese must not get fabricated 「缺少」 particle critiques

- **WHEN** TARGET TEXT is already grammatically/communicatively acceptable for a given span (as illustrated by Case A fixture corpora)
- **THEN** prompts instruct the model not to invent false 「缺少「X」」 particle fixes for that span; regression fixtures document the non-issue corpus and unacceptable false-positive reason patterns

#### Scenario: Genuine issues remain in scope

- **WHEN** real meaning, grammar, fluency, or spelling issues exist
- **THEN** the model is still expected to flag them, with each `reason` including why the correction is needed

### Requirement: Semantic quality fixtures and deterministic checks

The system SHALL maintain deterministic test fixtures covering Case A–style false 「缺少」 particle inventing and Case B–style weak reasons that omit 为什么, plus prompt-content assertions that the mandatory why-in-reason and anti-false-「缺少」 rules are present in backend and WebLLM prompts. If a lightweight post-parse heuristic for weak location-only 「缺少」 reasons is adopted, tests SHALL cover pass/fail examples; a hard retry-loop validator MUST NOT be required if design documents it as too noisy.

#### Scenario: Case A fixture documents false-positive pattern

- **WHEN** the Case A fixture (acceptable Japanese + bad 「缺少「が」…」 style reason) is loaded in tests
- **THEN** tests assert the documented quality expectation that such a false critique is unacceptable (via fixture metadata and/or heuristic)

#### Scenario: Case B fixture documents why-missing reason

- **WHEN** the Case B fixture (weak location-only 「缺少「は」…」 reason without 为什么) is loaded in tests
- **THEN** tests assert that reason fails the why-required quality check / heuristic (or prompt regression if heuristic is not wired)

#### Scenario: Prompt sync assertions

- **WHEN** prompt unit tests run
- **THEN** backend `prompts.py` and WebLLM prompt modules both contain wording requiring why-in-`reason` and forbidding false particle inventing
