## ADDED Requirements

### Requirement: Critique reason MUST include why the correction is needed

Every suggestion's `reason` field（指摘コメント）MUST explain **why the correction is necessary**, in addition to stating what is wrong and/or where. This is a hard content-quality requirement for all critique types (grammar, particles, fluency, meaning mismatch, spelling, etc.)—not optional guidance and not limited to particle additions. A `reason` that only names a missing form or location (e.g. `缺少"は"在"誰でも"前`) without communicative or grammatical necessity (为什么必须改) MUST be treated as non-compliant with prompt quality rules. Prompts for cloud and WebLLM paths MUST encode this requirement in Simplified Chinese for `reason` fields, consistent with existing Chinese-enforcement constraints.

#### Scenario: Compliant reason states what/where and why

- **WHEN** a suggestion is generated successfully
- **THEN** each suggestion's `reason` includes both the problem identification (what/where) and an explanation of why the correction is needed

#### Scenario: Location-only missing-particle reason is non-compliant

- **WHEN** a `reason` matches a location-only pattern such as `缺少"X"在…` (or equivalent) without stating why the particle/form is required
- **THEN** that `reason` fails the documented quality expectation for critique comments (prompt rules forbid it; automated heuristics/fixtures MAY flag it for regression)

#### Scenario: Applies beyond particle additions

- **WHEN** the model flags any issue type (tense, adjective conjugation, fluency, meaning mismatch, etc.)
- **THEN** the corresponding `reason` still MUST include why the change is necessary, not only the surface error label

### Requirement: Critique reasons MUST be accessible without translation expertise

Every `reason` MUST be understandable in plain Simplified Chinese to a reader who does **not** know Japanese↔Chinese translation craft. The explanation MUST cover (a) what is wrong, (b) where if relevant, and (c) **why** it matters / why the correction is needed, without assuming Japanese linguistics jargon or that the reader can read Japanese. Merely labeling an expression as "contextually awkward" without explaining why is non-compliant.

#### Scenario: Non-specialist can follow the why

- **WHEN** a suggestion `reason` is shown to a Chinese-speaking user unfamiliar with JP↔CN translation technique
- **THEN** the `reason` still conveys what is wrong and why the fix is needed in plain Chinese (prompts encode this accessibility MUST)

#### Scenario: Label-only critique is non-compliant

- **WHEN** a `reason` only says an expression is contextually bad / awkward without explaining why
- **THEN** that `reason` fails the accessibility / why-required quality expectation

### Requirement: Chinese critique text MUST use double quotes, never Japanese corner brackets

In `reason` and `overallComment`, quotation marks MUST be ASCII or Chinese double quotes (`""` / `“”`). Japanese corner brackets 「」 MUST NOT appear inside those Chinese critique fields. Prompts MUST encode this rule; tests MUST assert prompt wording. A low-noise post-parse check for 「」 in Chinese critique fields MAY retry like existing Chinese-language enforcement when design deems it safe.

#### Scenario: Compliant Chinese reason uses double quotes

- **WHEN** a Chinese `reason` or `overallComment` cites a form or phrase
- **THEN** prompts instruct the model to wrap citations in `""` / `“”`, not 「」

#### Scenario: Corner brackets in Chinese critique fields are non-compliant

- **WHEN** `reason` or `overallComment` contains 「 or 」
- **THEN** that output fails the documented quote-mark quality rule (prompt forbid; optional retry heuristic MAY trigger)

### Requirement: Accurate SOURCE citation for meaning-mismatch critiques

When a critique claims meaning mismatch with SOURCE TEXT, prompts MUST instruct the model to compare carefully, quote SOURCE accurately without inventing or mis-paraphrasing, and explain the mismatch clearly. Critiques of awkward Japanese wording versus SOURCE meaning MUST explain the meaning problem accurately and MUST NOT propose rewrites that drift away from SOURCE meaning.

#### Scenario: Meaning mismatch cites SOURCE accurately

- **WHEN** the model flags a meaning mismatch between TARGET and SOURCE
- **THEN** prompts require accurate SOURCE quotation/paraphrase and a clear mismatch explanation (fixtures document unacceptable inventing/misquote patterns)

#### Scenario: Awkward wording critique must not drift from SOURCE

- **WHEN** the model critiques awkward Japanese wording relative to SOURCE meaning
- **THEN** prompts require an accurate meaning-problem explanation and forbid rewrite suggestions that change SOURCE intent

### Requirement: Prefer multi-paragraph issue coverage

When TARGET TEXT has multiple paragraphs, prompts MUST guide the model to aim for surfacing real issues across paragraphs rather than concentrating all critiques on a single paragraph while ignoring others. Quality over spam: do not invent false issues for coverage.

#### Scenario: Multi-paragraph TARGET encourages distributed critiques

- **WHEN** TARGET TEXT contains multiple paragraphs with real issues in more than one paragraph
- **THEN** prompts instruct the model to prefer pointing issues across paragraphs without fabricating critiques

### Requirement: Avoid false particle inventing and prefer real issues

The system SHALL prompt models to prioritize true meaning mismatches, grammar errors, fluency problems, and spelling mistakes, and MUST instruct models **not** to invent missing particles or other 「缺少」 claims when the Japanese TARGET TEXT is already acceptable. Prompts MUST forbid inventing particles that incorrectly change meaning or are not needed. Existing Chinese-language rules for `reason`/`overallComment` and Japanese rules for `original`/`sourceExcerpt` remain in force.

#### Scenario: Acceptable Japanese must not get fabricated 「缺少」 particle critiques

- **WHEN** TARGET TEXT is already grammatically/communicatively acceptable for a given span (as illustrated by Case A fixture corpora)
- **THEN** prompts instruct the model not to invent false `缺少"X"` particle fixes for that span; regression fixtures document the non-issue corpus and unacceptable false-positive reason patterns

#### Scenario: Genuine issues remain in scope

- **WHEN** real meaning, grammar, fluency, or spelling issues exist
- **THEN** the model is still expected to flag them, with each `reason` including why the correction is needed in accessible Chinese

### Requirement: Semantic quality fixtures and deterministic checks

The system SHALL maintain deterministic test fixtures covering Case A–style false particle inventing, Case B–style weak reasons that omit 为什么, Case C–style meaning/wording drift, quote-mark / accessibility prompt assertions, and prompt-content assertions for the rules above in backend and WebLLM prompts. If a lightweight post-parse heuristic for weak location-only 缺少 reasons or Japanese corner brackets in Chinese fields is adopted, tests SHALL cover pass/fail examples; a hard retry-loop validator for weak 缺少 MUST NOT be required if design documents it as too noisy; corner-bracket retry MAY be wired when low-noise.

#### Scenario: Case A fixture documents false-positive pattern

- **WHEN** the Case A fixture (acceptable Japanese + bad `缺少"が"…` style reason) is loaded in tests
- **THEN** tests assert the documented quality expectation that such a false critique is unacceptable (via fixture metadata and/or heuristic)

#### Scenario: Case B fixture documents why-missing reason

- **WHEN** the Case B fixture (weak location-only 缺少 reason without 为什么) is loaded in tests
- **THEN** tests assert that reason fails the why-required quality check / heuristic (or prompt regression if heuristic is not wired)

#### Scenario: Prompt sync assertions

- **WHEN** prompt unit tests run
- **THEN** backend `prompts.py` and WebLLM prompt modules both contain wording requiring accessible why-in-`reason`, forbidding false particle inventing, forbidding 「」 in Chinese critique fields, accurate SOURCE citation, and multi-paragraph coverage guidance
