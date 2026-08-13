## ADDED Requirements

### Requirement: Reasons MUST use natural Chinese prose without mandatory spoken label prefixes

Prompts for cloud and WebLLM paths MUST require each `reason` to convey, in natural Simplified Chinese prose: (1) what is wrong or inadequate in the current TARGET form, (2) a concrete recommended replacement or rewrite direction when a clear fix exists, and (3) an accessible why. Prompts MUST NOT mandate machine-spoken colon labels such as `现状：`, `推荐：`, `現状：`, or `推奨：` as the spoken shape of `reason`. Contrastive forms like `旧形 → 「新形」` inside flowing prose remain allowed. Pedagogical content requirements from teaching-quality / Gemini quality-bar changes (essential gaps, contrastive nuance, accessible why) remain in force.

#### Scenario: Prompts forbid rigid spoken label templates

- **WHEN** cloud or WebLLM suggestion prompts are built
- **THEN** they explicitly discourage forcing `现状：` / `推荐：` / `現状：` / `推奨：` as required spoken prefixes while still requiring problem → fix → why content in natural Chinese

#### Scenario: Few-shots demonstrate natural prose

- **WHEN** few-shot examples used by cloud or WebLLM prompts are inspected
- **THEN** example `reason` strings demonstrate natural Chinese critique prose (optionally with `A → 「B」` contrast) and do not train colon-labeled `现状：…推荐：…` templates as the required shape

### Requirement: Multi-paragraph TARGET MUST get broader real-issue coverage without artificial low caps

Prompts MUST instruct models that for multi-paragraph TARGET text, they MUST scan paragraphs systematically for genuine issues and return a reasonable suggestion density (target at least about five when that many real issues exist). Stopping after only one or two suggestions when more real issues remain across paragraphs is non-compliant. Models MUST NOT fabricate or pad to hit a count; quality and truthfulness still beat padding. The system MUST NOT artificially cap suggestion count at two in prompts, provider config, or parsing.

#### Scenario: Coverage guidance present in synced prompts

- **WHEN** backend and WebLLM system/user prompts are built
- **THEN** they include multi-paragraph systematic coverage guidance and a non-trivial density target (at least ~5 when real issues exist), without instructing the model to emit only ~2 items

### Requirement: Gemini generation MUST allow enough output tokens for dense multi-suggestion JSON

The Gemini cloud provider MUST request a `maxOutputTokens` budget sufficient for a multi-suggestion pedagogical JSON payload on homework-length corpora (higher than a short-reply default). When a response is truncated (`finishReason` indicating max tokens), the provider SHOULD surface that condition in logs so operators can distinguish truncation from intentionally short critiques. Failover order Gemini → Groq → Cloudflare MUST NOT change.

#### Scenario: Gemini payload requests elevated maxOutputTokens

- **WHEN** the Gemini provider builds a `generateContent` request
- **THEN** `generationConfig.maxOutputTokens` is set high enough for multi-suggestion JSON (at least 8192)

#### Scenario: Truncation is observable in logs

- **WHEN** Gemini returns a candidate whose `finishReason` indicates token-limit truncation
- **THEN** the provider logs that finish reason (without logging secrets or full prompt bodies)

### Requirement: Format and coverage fixtures without live LLM in CI

The system SHALL maintain deterministic prompt/fixture assertions that (a) do not require spoken `现状：`/`推荐：` labels and (b) encode coverage guidance. CI MUST NOT require live LLM calls for these checks.

#### Scenario: Prompt unit tests encode natural prose and coverage

- **WHEN** backend and WebLLM prompt unit tests run
- **THEN** they assert natural problem→fix→why guidance without requiring colon-labeled `现状：`/`推荐：` prefixes, and assert multi-paragraph / density coverage guidance remains present
