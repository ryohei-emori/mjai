## ADDED Requirements

### Requirement: Primary correction task framing

The system SHALL frame suggestion generation around the primary correction brief focusing on meaning mismatch, grammar, fluency, and spelling errors (Japanese source wording: 「意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。」), as the core task instruction in the prompt structure — not merely as an optional comment. The JSON response schema SHALL remain `{ "suggestions": [ { "id", "original", "reason", "sourceExcerpt"? } ], "overallComment" }` with a target of at least five genuine suggestions when issues exist.

#### Scenario: Prompt includes the primary correction brief

- **WHEN** the backend (or WebLLM mirror) builds messages/prompts for suggestion generation
- **THEN** the constructed prompt includes the primary correction brief as core task framing, alongside the JSON schema and field-level language rules

#### Scenario: Schema and suggestion-count expectations are unchanged

- **WHEN** a model responds successfully to a generation request
- **THEN** the expected response shape remains suggestions + overallComment (with optional sourceExcerpt), and the prompt still targets at least five genuine suggestions without fabricating filler

### Requirement: Stricter Japanese detection for explanation fields

The system SHALL treat a parsed suggestion response as failing the Chinese-language content check when any suggestion's `reason` or the top-level `overallComment` contains Japanese-script signals: Hiragana (U+3040–U+309F), Katakana (U+30A0–U+30FF), halfwidth Katakana (U+FF66–U+FF9D), or carefully chosen Japanese-only particle/function-word patterns that indicate Japanese prose. The check MUST NOT reject legitimate Simplified Chinese text that shares Han characters with Japanese. The `original` and `sourceExcerpt` fields remain exempt. On failure, the system SHALL retry within the existing shared `MAX_PARSE_RETRY_ATTEMPTS` budget and return the last result without raising when exhausted.

#### Scenario: Hiragana or Katakana in reason still fails the check

- **WHEN** a suggestion's `reason` contains Hiragana or Katakana
- **THEN** the language check fails and generation is retried if attempts remain

#### Scenario: Japanese particle/function patterns without relying only on dense kana prose

- **WHEN** a `reason` or `overallComment` matches Japanese-only particle/function-word patterns used by the detector (even in otherwise sparse mixed text)
- **THEN** the language check fails and generation is retried if attempts remain

#### Scenario: Pure Simplified Chinese explanations pass

- **WHEN** every `reason` and `overallComment` are Simplified Chinese with no Japanese kana or Japanese-only particle/function patterns
- **THEN** the language check passes even if Han characters are shared with Japanese kanji

#### Scenario: original and sourceExcerpt remain exempt

- **WHEN** only `original` and/or `sourceExcerpt` contain Japanese script
- **THEN** the language check does not fail for that reason alone

#### Scenario: Fifteen-iteration enforcement verification

- **WHEN** the automated verification harness runs the detector / enforcement path fifteen times with controlled (mocked) payloads
- **THEN** each iteration confirms Chinese `reason`/`overallComment` pass the check and Japanese explanation fields fail (and trigger retry when exercised through the generation loop)

## MODIFIED Requirements

### Requirement: Bilingual field content — Chinese explanations, Japanese corrected text

The system's users are Chinese speakers correcting/learning Japanese text. The system SHALL prompt the model so that explanation-oriented fields (`reason` on each suggestion, and `overallComment`) are written in **Simplified Chinese**, while the `original` field (the excerpt of corrected/flagged Japanese TARGET TEXT) remains in **Japanese**, and `sourceExcerpt` (when present) remains in the SOURCE TEXT language (Japanese). Field names and the JSON schema itself are unchanged — only the prompted content language differs per field.

Prompt wording SHALL make the Chinese requirement for `reason`/`overallComment` unmistakable (hard to violate), including explicit prohibitions against Japanese in those fields. WebLLM prompts SHALL carry the same field-level language split.

#### Scenario: Suggestion reason is in Chinese

- **WHEN** a suggestion is generated successfully
- **THEN** each suggestion's `reason` field is written in Simplified Chinese

#### Scenario: Overall comment is in Chinese

- **WHEN** a suggestion response is generated successfully
- **THEN** the `overallComment` field is written in Simplified Chinese

#### Scenario: Corrected-text excerpt stays Japanese

- **WHEN** a suggestion is generated successfully
- **THEN** each suggestion's `original` field remains in Japanese (the same language as the input TARGET TEXT) and is NOT translated into Chinese

#### Scenario: sourceExcerpt stays Japanese when present

- **WHEN** a suggestion includes a non-empty `sourceExcerpt`
- **THEN** that field remains in Japanese (SOURCE TEXT language) and is NOT translated into Chinese
