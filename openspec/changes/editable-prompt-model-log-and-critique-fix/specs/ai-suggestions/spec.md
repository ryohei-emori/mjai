## ADDED Requirements

### Requirement: Effective System Prompt Resolution Per Request

Cloud suggestion generation SHALL resolve its system prompt at request time: the stored shared prompt when one exists, otherwise the built-in default. A saved prompt SHALL therefore take effect on the next generation without a redeploy, process restart, or cache expiry wait. The stored-prompt lookup SHALL be bounded by a short timeout and SHALL be accounted for inside the existing generation wall-clock budget, so a slow prompt store cannot push a request past the platform function timeout.

#### Scenario: Custom prompt is used on the next generation

- **GIVEN** a user saves a custom prompt
- **WHEN** the next cloud generation runs
- **THEN** the request sent to the provider carries the custom prompt as its system instruction

#### Scenario: Default prompt is used when none is stored

- **GIVEN** no custom prompt is stored
- **WHEN** a cloud generation runs
- **THEN** the system instruction is the built-in default composition, with no placeholder or marker indicating that customization is available

#### Scenario: Slow prompt store does not extend the request budget

- **GIVEN** the prompt store is slow to respond
- **WHEN** a generation request runs
- **THEN** the lookup gives up within its own short timeout and the default prompt is used
- **AND** the remaining provider budget is the same wall-clock budget as before, so the request still returns an application-level response rather than a platform timeout

### Requirement: Output Contract And Supporting Prompt Parts Are Not Editable

The editable prompt SHALL cover the critique rules only. The system SHALL append, after the editable body, a code-owned output contract stating that the reply must be a single JSON object and giving the response schema; an edit SHALL NOT be able to remove, weaken, or reorder that contract. The few-shot exemplar, the per-request reminder message, the optional exemplar-translation reference rules, and the retry nudges SHALL likewise remain code-owned and outside the editable text.

#### Scenario: Custom prompt without JSON instructions still gets the contract

- **GIVEN** a stored custom prompt whose text says nothing about JSON or the response schema
- **WHEN** the request is assembled
- **THEN** the system instruction consists of the custom text followed by the code-owned output contract
- **AND** the response schema is present in the assembled prompt

#### Scenario: Supporting parts are unaffected by a custom prompt

- **GIVEN** a stored custom prompt
- **WHEN** the request is assembled
- **THEN** the code-owned few-shot exemplar and per-request reminder are still sent
- **AND** an exemplar translation, when supplied, still contributes its code-owned reference rules

### Requirement: Winning Provider And Model Are Reported

A successful suggestion-generation response SHALL identify the provider that produced it and the exact model identifier used. When a provider rotates models, retries on a second model, or rotates credentials, the reported model SHALL be the one that produced the returned content, not the first one attempted. The reported values SHALL be stable machine-readable identifiers suitable for storage and later comparison.

#### Scenario: Primary provider wins

- **WHEN** the primary provider returns usable content
- **THEN** the response reports that provider and the model identifier it used

#### Scenario: Failover provider wins

- **GIVEN** the primary provider fails or returns unusable content and a later provider in the failover chain succeeds
- **WHEN** the response is returned
- **THEN** it reports the succeeding provider and that provider's model identifier

#### Scenario: In-provider model retry is reported accurately

- **GIVEN** a provider's first rotation model fails and its retry model succeeds
- **WHEN** the response is returned
- **THEN** the reported model is the retry model that produced the content

#### Scenario: Error responses are unchanged

- **GIVEN** every provider fails
- **WHEN** the error response is returned
- **THEN** it keeps its existing shape and diagnostics, and reports no winning provider or model

### Requirement: Recommended Forms Are Written In The Target Language

Every recommended replacement form inside a critique SHALL be written in the target language of the exercise (Japanese), not in the explanation language. A word or phrase in the explanation language SHALL NOT be presented as the corrected form. Explanations themselves SHALL remain in Simplified Chinese as already required; this requirement constrains only the recommended form.

#### Scenario: Recommended form is Japanese

- **WHEN** a critique proposes replacing a Japanese phrase
- **THEN** the proposed replacement is Japanese text

#### Scenario: Chinese phrase is not offered as the correction

- **WHEN** the source-language wording differs from the target-language wording
- **THEN** the critique does not instruct the learner to write the Chinese phrase into the Japanese text

### Requirement: Critique Scope Is The Target Text

Critiques SHALL address only the target text. Each item's flagged excerpt SHALL be a span of the target text, and no item SHALL propose editing, rewriting, or improving the source text. The source text may be cited to explain a divergence — including through the optional source-excerpt field — but is never the object of correction.

#### Scenario: Flagged excerpt comes from the target text

- **WHEN** a critique item is produced
- **THEN** its flagged excerpt is a span of the target text

#### Scenario: Source text is not corrected

- **GIVEN** the source text contains wording the model considers improvable
- **WHEN** critiques are produced
- **THEN** no item proposes a rewrite of the source text

### Requirement: Only Substantive Faults Are Reported

Critiques SHALL report faults, not stylistic preferences. Substituting a near-synonym that leaves meaning, grammaticality, and register-appropriateness intact SHALL NOT be reported as an issue. When a lexical or wording item is reported, its explanation SHALL identify a concrete defect — a shift in meaning, a collocation or usage error, a register or domain-convention mismatch, or a systematic grammatical fault — rather than asserting that the alternative is merely more accurate, more natural, more formal, or more concise.

#### Scenario: Interchangeable synonym is not reported

- **GIVEN** the target text uses a word that is interchangeable with an alternative in this context
- **WHEN** critiques are produced
- **THEN** no item is spent on swapping one for the other

#### Scenario: Reported wording item names its defect

- **WHEN** a critique reports a wording issue
- **THEN** its explanation identifies which concrete defect applies, rather than resting on a bare claim of greater naturalness or formality

### Requirement: Recommended Forms Must Be Valid In Their Sentence

A recommended form SHALL be checked against the sentence it would appear in: the resulting target-language sentence SHALL be grammatical and collocationally natural. A collocation valid in the source language SHALL NOT be transplanted into the target language on the strength of shared characters or a dictionary gloss.

#### Scenario: Recommendation is rejected when the result is unnatural

- **GIVEN** substituting a proposed word would produce an ungrammatical or unnatural target-language sentence
- **WHEN** critiques are produced
- **THEN** that substitution is not proposed

#### Scenario: Source-language collocation is not transplanted

- **GIVEN** a word pairing that is idiomatic in the source language but not in the target language
- **WHEN** critiques are produced
- **THEN** the pairing is not recommended for the target text

### Requirement: Critiques Are Framed As Meaning Transfer

Critique explanations SHALL be framed as translation critique: what the source conveys, what a reader of the target text would understand instead, and what the reader loses or misreads if the text is left as written. Framing an item purely as lexical bookkeeping — that one word is the standard equivalent of another — SHALL NOT satisfy this requirement on its own.

#### Scenario: Explanation states the reader-facing consequence

- **WHEN** a critique reports a meaning-related issue
- **THEN** the explanation says what a target-language reader would understand or miss as written, not only which word maps to which

#### Scenario: Equivalence claim alone is insufficient

- **WHEN** the only justification available for a change is that the source uses a corresponding word
- **THEN** no critique item is produced from it

### Requirement: Chinese Recommended Forms Trigger Regeneration

A response that presents a recommended form in the explanation language rather than the target language SHALL be treated as unusable content, in the same way non-Chinese explanation prose already is, and SHALL trigger a further generation attempt within the existing shared attempt budget — adding no new attempts and therefore no additional worst-case latency. The check SHALL NOT fire on legitimate target-language citations, including forms written only in kanji. When the shared budget is exhausted, the system SHALL return the last obtained result rather than failing the request.

#### Scenario: Chinese recommendation triggers a retry

- **GIVEN** a provider returns a critique instructing the learner to use a Chinese phrase as the corrected Japanese form
- **WHEN** the response is evaluated
- **THEN** it is treated as unusable and another attempt is made within the existing attempt budget

#### Scenario: Kanji-only Japanese citation does not trigger a retry

- **GIVEN** a critique recommends a Japanese form written only in kanji
- **WHEN** the response is evaluated
- **THEN** it is accepted as usable

#### Scenario: Budget exhaustion still returns content

- **GIVEN** every attempt in the budget produces a Chinese recommended form
- **WHEN** the budget is exhausted
- **THEN** the last result is returned rather than an error

### Requirement: Few-Shot Exemplar Demonstrates The Critique Rules

The code-owned few-shot exemplar SHALL demonstrate the rules above, because the exemplar anchors model behaviour more strongly than rule prose does. Every recommended form in the exemplar SHALL be target-language text; no exemplar item SHALL be a bare near-synonym preference; at least one item SHALL show a meaning-transfer or modality fault explained by its reader-facing consequence; and the exemplar SHALL continue to satisfy the existing density, category-coverage, distinctness, and omitted-source-excerpt requirements.

#### Scenario: Exemplar recommendations are all target-language

- **WHEN** the few-shot exemplar is inspected
- **THEN** every recommended form it contains is Japanese

#### Scenario: Exemplar contains no preference-only item

- **WHEN** the few-shot exemplar is inspected
- **THEN** no item's justification is limited to one word being more natural, more formal, or more accurate than an interchangeable alternative

#### Scenario: Exemplar keeps its existing structural properties

- **WHEN** the few-shot exemplar is inspected
- **THEN** it still shows at least five distinct items, covers meaning or modality and grammatical categories alongside lexical ones, and still includes at least one item with no source excerpt
