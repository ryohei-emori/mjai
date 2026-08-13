## ADDED Requirements

### Requirement: Optional exemplar translation on suggestions request

The system SHALL accept an optional `exemplarTranslation` string field on authenticated `POST /api/suggestions` (and the equivalent WebLLM client-side generation path). The field SHALL NOT be required: requests that omit it or send an empty/whitespace-only value MUST succeed under the same conditions as today when only `originalText` and `targetText` are provided. Non-empty values SHALL be treated as optional prompt context — a model/exemplar answer translation relative to SOURCE TEXT (`originalText`) — and SHALL NOT change the response schema (`suggestions` + `overallComment`, including any existing optional per-suggestion fields such as `sourceExcerpt`).

#### Scenario: Request without exemplarTranslation behaves as today

- **WHEN** an authenticated client sends `POST /api/suggestions` with valid `originalText` and `targetText` and no `exemplarTranslation` field (or an empty/whitespace-only value)
- **THEN** the system generates suggestions using the existing SOURCE/TARGET prompt construction
- **AND** the response shape is unchanged from the current contract

#### Scenario: Request with non-empty exemplarTranslation is accepted

- **WHEN** an authenticated client sends `POST /api/suggestions` with valid `originalText`, `targetText`, and a non-empty `exemplarTranslation`
- **THEN** the request is accepted (not rejected as unknown/invalid)
- **AND** the system returns the normal suggestions response shape on success

#### Scenario: WebLLM offline path accepts the same optional field

- **WHEN** the frontend generates suggestions via WebLLM (offline mode or cloud fallback) with a non-empty exemplar translation in session state
- **THEN** the WebLLM prompt assembly includes that exemplar as reference context
- **AND** when the exemplar is empty, WebLLM prompt assembly omits it and matches today's SOURCE/TARGET-only behavior

### Requirement: Exemplar translation included in prompt only when provided

WHEN `exemplarTranslation` is present and non-empty after trim, the system SHALL include it in the user/prompt payload for Groq, Cloudflare Workers AI, and WebLLM as a clearly labeled reference section (模範回答訳文 / exemplar answer translation) so the model can compare TARGET TEXT against a known-good translation of SOURCE TEXT. WHEN the field is absent or empty/whitespace-only, the system SHALL omit that section entirely and SHALL NOT send a placeholder empty block that could confuse the model.

#### Scenario: Non-empty exemplar appears in the prompt

- **WHEN** suggestion generation runs with a non-empty `exemplarTranslation`
- **THEN** the constructed prompt/messages include the exemplar text in a dedicated reference section
- **AND** SOURCE TEXT and TARGET TEXT continue to appear as today

#### Scenario: Empty exemplar is omitted from the prompt

- **WHEN** suggestion generation runs with no `exemplarTranslation` or only whitespace
- **THEN** the constructed prompt/messages contain no exemplar/模範回答 section
- **AND** generation proceeds with SOURCE TEXT and TARGET TEXT only
