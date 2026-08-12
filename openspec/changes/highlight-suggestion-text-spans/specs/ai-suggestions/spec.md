## ADDED Requirements

### Requirement: Optional source-text correspondence excerpt per suggestion

The system SHALL support an optional `sourceExcerpt` field on each generated suggestion, holding a verbatim-or-close excerpt from SOURCE TEXT (原文, the input `originalText`) corresponding to the flagged TARGET TEXT snippet described by that suggestion's `original` field. The system SHALL prompt the model to write this field in the same language as SOURCE TEXT (Japanese, matching `original`'s language rule), and SHALL instruct the model to omit the field or return an empty string when no clear SOURCE TEXT correspondence exists for that suggestion, rather than fabricating one. The parser SHALL extract this field using the same multi-key-fallback convention used for `original`/`reason`, defaulting to an empty string when absent under any recognized key.

#### Scenario: Suggestion has a clear source-text correspondence

- **WHEN** a flagged TARGET TEXT snippet corresponds to an identifiable excerpt in SOURCE TEXT (e.g. the correct usage the target text should have followed)
- **THEN** the suggestion's `sourceExcerpt` field contains that excerpt, written in the same language as SOURCE TEXT

#### Scenario: Suggestion has no source-text correspondence

- **WHEN** a flagged TARGET TEXT snippet is a local grammar/style/register issue with no direct counterpart in SOURCE TEXT (e.g. an adjective conjugation error)
- **THEN** the suggestion's `sourceExcerpt` field is omitted or an empty string
- **AND** the system does not fabricate or force a value to fill the field

#### Scenario: Parser extracts sourceExcerpt under alternate key names

- **WHEN** a provider's raw response uses an alternate key for this concept instead of the canonical `sourceExcerpt` key
- **THEN** the parser still extracts the value via its documented key-fallback order

#### Scenario: Parser defaults to empty string when the field is absent

- **WHEN** a suggestion item in the raw response contains no recognized source-excerpt key at all
- **THEN** the parsed suggestion's `sourceExcerpt` is an empty string, not `null` or a missing key

#### Scenario: sourceExcerpt is not subject to the Chinese-language content check

- **WHEN** a suggestion's `sourceExcerpt` contains Hiragana or Katakana (as expected, since it must stay in SOURCE TEXT's language)
- **THEN** this does not count as a language-check failure and does not trigger the existing non-Chinese-content retry (`has_non_chinese_reason`), consistent with the existing exemption for `original`

### Requirement: sourceExcerpt is not persisted as saved correction data

The system SHALL treat `sourceExcerpt` as a transient, generation-time-only field. It SHALL NOT be persisted through `POST /proposals` or stored in the `ai_proposals` table in this iteration.

#### Scenario: Confirming/saving corrections does not require sourceExcerpt

- **WHEN** a user selects suggestions and saves corrections via the existing confirm/save flow
- **THEN** the saved proposal record is unaffected by whether any selected suggestion had a `sourceExcerpt` value
