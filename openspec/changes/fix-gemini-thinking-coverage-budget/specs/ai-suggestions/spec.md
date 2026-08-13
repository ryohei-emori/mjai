## ADDED Requirements

### Requirement: Gemini requests MUST constrain internal thinking so critiques finish inside the provider timeout

The Gemini cloud provider MUST send an explicit thinking constraint in `generationConfig` that reduces internal deliberation, so a homework-length multi-paragraph critique completes well inside `GEMINI_TIMEOUT` rather than finishing near the timeout boundary. The constraint MUST be expressed with a field the whole `ALLOWED_GEMINI_MODELS` pool accepts. Operators MUST be able to override the level (including restoring provider-default thinking) through an environment variable without a code change. Failover order Gemini → Groq → Cloudflare MUST NOT change, and `GEMINI_TIMEOUT` MUST remain inside the suggestions wall-clock budget.

#### Scenario: Payload carries a thinking constraint by default

- **WHEN** the Gemini provider builds a `generateContent` request with no thinking-level override configured
- **THEN** `generationConfig.thinkingConfig` requests a reduced thinking level

#### Scenario: Thinking level is operator-overridable

- **WHEN** the thinking-level environment override is set to a non-empty level
- **THEN** the request carries that level instead of the default

#### Scenario: Provider-default thinking can be restored

- **WHEN** the thinking-level environment override is set to the opt-out value
- **THEN** the request omits `thinkingConfig` entirely, restoring provider-default thinking behavior

#### Scenario: Thinking constraint works across the whole model pool

- **WHEN** the thinking constraint is applied
- **THEN** it uses a field accepted by every model in `ALLOWED_GEMINI_MODELS`, so no pooled model rejects the request with HTTP 400

### Requirement: Gemini output-token budget MUST exceed dense multi-suggestion needs without exceeding the model cap

The Gemini provider MUST request a `maxOutputTokens` budget that comfortably exceeds the completion tokens a dense multi-suggestion pedagogical JSON payload consumes on homework-length corpora, while staying at or below the model's advertised `outputTokenLimit` so the request cannot be rejected with HTTP 400.

#### Scenario: Budget has headroom over observed usage

- **WHEN** the Gemini provider builds a `generateContent` request
- **THEN** `generationConfig.maxOutputTokens` is at least 16384, several times the completion tokens a dense multi-paragraph critique consumes

#### Scenario: Budget stays inside the model cap

- **WHEN** the configured `maxOutputTokens` is compared to the advertised `outputTokenLimit` of every model in `ALLOWED_GEMINI_MODELS`
- **THEN** the configured value does not exceed that limit

### Requirement: Gemini token usage MUST be observable in logs

The Gemini provider MUST log the response's `usageMetadata` token counts — prompt, candidate/completion, thinking, and total — alongside the existing `finishReason` line, so operators can distinguish an intentionally short critique from a budget-truncated one and can see thinking cost, without logging secrets or full prompt bodies.

#### Scenario: Usage metadata logged on a successful response

- **WHEN** Gemini returns a `generateContent` response containing `usageMetadata`
- **THEN** the provider logs the prompt, candidate, thinking, and total token counts

#### Scenario: Missing usage metadata does not break extraction

- **WHEN** a Gemini response omits `usageMetadata`
- **THEN** text extraction still succeeds and no exception is raised

### Requirement: Truncated suggestion JSON MUST retain every complete item

When a model response is cut off mid-JSON, the parser MUST recover every suggestion item that is structurally complete before the cutoff, not just the leading one or two. Only the incomplete trailing item may be dropped or blanked.

#### Scenario: Multi-item truncated array keeps all complete items

- **WHEN** a response containing several complete suggestion objects is truncated part-way through a later object
- **THEN** parsing returns all the complete items with contiguous ids

### Requirement: Live Gemini coverage probe MUST be reproducible without exposing secrets

The repository SHALL provide a live probe script that reports, per call, the suggestion count, `finishReason`, `usageMetadata` token counts, elapsed time against `GEMINI_TIMEOUT`, and each pooled model's advertised token limits, and that can sweep `maxOutputTokens` and thinking settings. The script MUST NOT print API keys or key-derived material, and CI MUST NOT depend on it.

#### Scenario: Probe reports coverage and token evidence

- **WHEN** the live Gemini coverage probe runs against the multi-paragraph fixture
- **THEN** it emits, per call, suggestion count, finish reason, token usage, and elapsed time, and never prints key material
