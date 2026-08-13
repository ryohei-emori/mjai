## ADDED Requirements

### Requirement: Few-shot exemplars MUST demonstrate the stated coverage density

Few-shot examples embedded in cloud and WebLLM suggestion prompts MUST demonstrate a suggestion count consistent with the density target the same prompt states (at least about five for the backend/cloud example), rather than a smaller count that anchors the model to a low cardinality. Where an example's item count is constrained by a deliberately short example input, the prompt MUST state explicitly that the example's count is not an upper bound and that longer multi-paragraph input should yield more items.

#### Scenario: Backend few-shot demonstrates the density target

- **WHEN** the backend suggestion prompt's few-shot example is inspected
- **THEN** it contains at least five suggestion objects, and prompt text states that the example's item count reflects its short input and is not a cap

#### Scenario: WebLLM few-shot does not anchor a low count

- **WHEN** the WebLLM few-shot example is inspected
- **THEN** it carries an explicit note that longer input should produce more items than the example shows

### Requirement: Few-shot exemplars MUST cover the declared priority issue categories

Few-shot examples MUST illustrate the issue categories the prompt declares highest priority — meaning divergence from SOURCE, lost or altered modality, systematic grammatical faults, and domain/register misuse — and MUST NOT consist only of lexical-substitution and register items. Every demonstrated item MUST address a distinct issue; restating an earlier item's point as an additional item is non-compliant because it models the padding-by-repetition the same prompt forbids.

#### Scenario: Semantic and grammatical categories are demonstrated

- **WHEN** the backend or WebLLM few-shot example is inspected
- **THEN** at least one item addresses divergence from SOURCE meaning or lost modality, and at least one addresses a grammatical fault, in addition to lexical/register items

#### Scenario: No item duplicates another item's point

- **WHEN** the items of any few-shot example are compared
- **THEN** no item restates a correction already made by another item in the same example

### Requirement: Few-shot critique text MUST contain only user-facing critique prose

Few-shot `reason` and `overallComment` strings MUST read as critique addressed to the learner. They MUST NOT embed instructions aimed at the model (for example, telling the model which critique types to avoid); such constraints belong in the instruction sections of the prompt, not inside exemplar output.

#### Scenario: No model-facing directives inside exemplar reasons

- **WHEN** few-shot `reason` strings are inspected
- **THEN** none of them contains directive text addressed to the model rather than explanation addressed to the learner

### Requirement: Few-shot exemplars MUST demonstrate omitting sourceExcerpt

Because `sourceExcerpt` is optional and MUST NOT be fabricated, few-shot examples MUST include at least one item that omits it, representing a fault with no clear SOURCE counterpart (such as a target-language-internal grammatical error). An example in which every item carries a `sourceExcerpt` is non-compliant, as it biases the model toward always producing one.

#### Scenario: At least one exemplar item omits the excerpt

- **WHEN** the backend and WebLLM few-shot examples are inspected
- **THEN** each contains at least one suggestion item with no `sourceExcerpt` field

### Requirement: Prompt text MUST NOT hedge in ways that license under-reporting

Prompt instruction text MUST express its anti-fabrication rules without also granting permission to return fewer suggestions than the real issues warrant. Standalone hedges that trade coverage against count (such as declaring quality preferable to number of items) MUST NOT accompany the coverage requirement. Length control MUST be expressed as a per-item bound rather than a global instruction to be brief, so that limiting verbosity does not also limit item count.

#### Scenario: Coverage requirement carries no count-trading hedge

- **WHEN** the coverage and density instructions are inspected
- **THEN** they forbid fabricating or padding items while explicitly stating that anti-fabrication is not a reason to omit genuine issues, and they contain no standalone instruction preferring fewer items

#### Scenario: Brevity is bounded per item

- **WHEN** length guidance for critique text is inspected
- **THEN** it bounds the length of an individual `reason` rather than instructing overall brevity, and still requires the recommended fix and the why

### Requirement: Each prompt rule SHALL be stated once at the appropriate layer

To limit dilution and token waste, a given constraint SHALL be stated in the system prompt and, where reinforcement is warranted, in the per-request reminder or retry nudge — but SHALL NOT additionally be repeated in few-shot preamble text when the example itself already demonstrates compliance. The WebLLM prompt SHALL state each coverage rule once rather than duplicating it across lines, given its small-model token and instruction-following budget.

#### Scenario: Anti-label rule is not repeated in few-shot preamble

- **WHEN** the few-shot examples are inspected
- **THEN** they demonstrate compliant natural prose without restating the prohibition on spoken colon labels, which remains in the system prompt and reminder text

#### Scenario: WebLLM coverage guidance appears once

- **WHEN** the WebLLM system prompt is inspected
- **THEN** the multi-paragraph coverage rule and the density target are stated without duplicated anti-padding or early-stop clauses

### Requirement: Suggestion count SHALL NOT be capped downstream

The system SHALL NOT truncate, cap, or otherwise limit the number of parsed suggestions in provider clients, response parsing, or persistence, so that the prompt-level density target is the only thing governing item count.

#### Scenario: No downstream truncation of the suggestion array

- **WHEN** a provider returns a JSON payload containing many suggestions
- **THEN** all parsed suggestions are returned to the caller with no fixed-length slice applied
