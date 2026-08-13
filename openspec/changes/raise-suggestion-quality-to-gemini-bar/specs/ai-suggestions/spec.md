## ADDED Requirements

### Requirement: overallComment MUST open with constructive strengths then gaps

Prompts for cloud and WebLLM paths MUST instruct the model to write `overallComment` in Simplified Chinese with a constructive framing: first acknowledge what already works in the TARGET (concepts, register strengths, successful conveyance of SOURCE ideas when present), then summarize remaining issue categories or gaps. Empty praise-only or issue-only overall comments without this strengths-then-gaps skeleton are non-compliant with the quality bar.

#### Scenario: Strengths then gaps in overallComment

- **WHEN** suggestions are generated successfully for a non-empty TARGET
- **THEN** prompts require `overallComment` to mention at least one strength / what already works before summarizing remaining issues or categories

### Requirement: Each reason MUST use problem → recommended fix → accessible why

Every suggestion `reason` MUST follow a Gemini-style critique shape in Simplified Chinese: (1) state the problem or current form, (2) give a concrete recommended replacement when a clear fix exists (format like `現状 → 推奨` with optional reading aids for Japanese forms), and (3) explain why in plain Chinese understandable without JP↔CN translation craft. Because the API schema remains `original` + `reason` + optional `sourceExcerpt` (no separate suggested-text field), the recommended fix MUST appear inside `reason` when applicable. Label-only critiques without a recommended direction or accessible why remain non-compliant.

#### Scenario: Compliant reason includes replacement and why

- **WHEN** a suggestion flags a fixable wording/term/grammar issue
- **THEN** prompts require the `reason` to include a concrete recommended form (or clear rewrite direction) plus an accessible Chinese why

#### Scenario: No separate suggested field required

- **WHEN** the model proposes a replacement
- **THEN** that replacement is encoded inside `reason` (schema does not gain a new field for this change)

### Requirement: CN→JP literary and academic translation critique domain

Prompts MUST frame the task as critique of Chinese→Japanese literary/academic essay translation (including epic / oral-literature terminology, register, calque→natural JP, sense modality, voice, and standard academic renderings), not generic monolingual composition only. Models MUST still prefer real issues and MUST NOT invent false problems for coverage.

#### Scenario: Domain-aware prompt framing

- **WHEN** cloud or WebLLM suggestion prompts are built
- **THEN** they include CN→JP literary/academic translation-critique framing (term norms, register, calque, etc.) alongside existing meaning/grammar/fluency/spelling priorities

### Requirement: Corner brackets allowed only for Japanese TARGET citations

In `reason` and `overallComment`, Chinese meta-prose MUST use ASCII or Chinese double quotes (`""` / `“”`) when quoting Chinese words or meta labels. Japanese corner brackets 「」 MUST be used **only** to cite Japanese TARGET words or phrases (and MAY include readings). Using 「」 to wrap Chinese explanatory prose is non-compliant. This revises the prior absolute forbid of 「」 in Chinese critique fields from `harden-semantic-suggestion-reasons`.

#### Scenario: Japanese cite may use corner brackets

- **WHEN** a Chinese `reason` cites a Japanese TARGET form such as a recommended academic rendering
- **THEN** prompts allow wrapping that Japanese form in 「」, while Chinese meta quotes use `""` / `“”`

#### Scenario: Chinese prose inside corner brackets is non-compliant

- **WHEN** `reason` or `overallComment` wraps Chinese explanatory prose in 「」 (e.g. 「时态」)
- **THEN** that output fails the quote-mark quality rule; a narrowed post-parse heuristic MAY retry

### Requirement: Gemini quality-bar fixtures without live LLM in CI

The system SHALL maintain deterministic fixtures documenting desired Gemini-style critique shapes (overallComment skeleton and/or `現状 → 推奨` + why examples) against representative CN SOURCE / JP TARGET pairs. CI MUST NOT require live LLM calls for these fixtures; tests MAY assert prompt wording and heuristic behavior only.

#### Scenario: Fixture documents quality-bar shape

- **WHEN** quality-bar fixture modules are loaded in tests
- **THEN** they document example compliant critique shapes and/or corpora for manual verify, without invoking a live model in CI

#### Scenario: Prompt sync for quality bar

- **WHEN** prompt unit tests run
- **THEN** backend and WebLLM prompts both encode overallComment strengths-then-gaps, per-reason `現状 → 推奨` + accessible why, CN→JP literary/academic framing, and the revised quote-mark policy
