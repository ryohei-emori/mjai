## ADDED Requirements

### Requirement: Critiques MUST prioritize essential competence gaps over cosmetic surface edits

Prompts for cloud and WebLLM paths MUST instruct the model that the purpose of each suggestion is to help the translator improve **future** translations by teaching underlying competence gaps. Models MUST prioritize essential problems — meaning drift, systematic grammar (e.g. recurring conjugation errors framed as a conjugation competence issue), spelling that reveals missing word knowledge, register/domain term misuse with teaching why, modality mismatches (e.g. 聞き漏らす vs 見落とす), and similar — over cosmetic surface edits that do not change competence. Using a trivial omission/simplification as the **main** point of a suggestion (e.g. recommending dropping a harmless phrase solely for “日语习惯 / simplify”) is non-compliant when deeper real issues exist or when that edit is not essential.

#### Scenario: Trivial surface edit is discouraged as main critique

- **WHEN** cloud or WebLLM suggestion prompts are built
- **THEN** they explicitly discourage treating trivial surface omissions/simplifications as the primary critique when essential translation problems should be addressed instead

#### Scenario: Essential problem classes are encouraged

- **WHEN** cloud or WebLLM suggestion prompts are built
- **THEN** they instruct the model to prefer meaning drift, systematic grammar, competence-revealing spelling, register/domain misuse with why, and modality mismatches over cosmetic rewrites

### Requirement: Critiques MUST NOT prescribe source-token swaps without pedagogy

Prompts MUST forbid recommending a Japanese form solely because it matches a Chinese SOURCE token or “sounds closer to the source” without explaining the translation/competence issue. A→B prescriptions justified only by “原文 says X” (or equivalent) without teaching why the current JP is inadequate are non-compliant. This does not forbid accurate SOURCE citations when explaining meaning mismatch; it forbids bare source-token replacement as 添削.

#### Scenario: Source-token swap without teaching is non-compliant

- **WHEN** a suggestion would replace TARGET wording mainly to mirror a SOURCE token
- **THEN** prompts require pedagogical explanation of the competence/meaning issue; bare “原文用了X所以改成Y” style reasons are non-compliant

### Requirement: Lexical recommendations MUST include contrastive nuance before preference

When a `reason` recommends a different Japanese wording for a lexical upgrade (not a clear hard error like a wrong conjugation), prompts MUST require stating the nuance of the **current** form and the **recommended** form in Simplified Chinese, then explaining why the recommendation fits this context. Recommending A→B with only a vague benefit (“更能体现…” / “更自然”) and no contrastive nuance is non-compliant.

#### Scenario: Contrastive nuance precedes preference

- **WHEN** prompts describe a fixable lexical upgrade in `reason`
- **THEN** they require contrastive explanation of current vs recommended Japanese nuances before stating necessity/preference

### Requirement: Reasons MUST explain why the error class matters for future translations

Prompts MUST reinforce that the accessible Chinese why (already required) SHOULD connect to lasting translator competence when applicable — e.g. flagging a spelling mistake because it shows missing basic word knowledge that will affect future translations — not only local polish. This extends, and MUST NOT weaken, existing accessibility / why-necessary rules from prior changes.

#### Scenario: Class-of-error teaching cue in prompts

- **WHEN** cloud or WebLLM suggestion prompts are built
- **THEN** they include guidance to explain why the class of error matters for future translations (competence), not only why the local sentence sounds better

### Requirement: Teaching-quality fixtures without live LLM in CI

The system SHALL maintain deterministic fixtures documenting teaching-quality anti-patterns and compliant contrastive/essential-problem critique shapes. CI MUST NOT require live LLM calls for these fixtures; tests MAY assert prompt wording and fixture content only. Existing Gemini quality-bar structural MUSTS (Chinese reasons, `現状 → 推奨`, strengths-then-gaps overallComment, quote-mark policy, no false particles, no auto WebLLM) remain in force and MUST NOT regress.

#### Scenario: Fixture documents anti-patterns and compliant shapes

- **WHEN** teaching-quality fixture modules are loaded in tests
- **THEN** they document at least one discouraged anti-pattern example and one compliant teaching-oriented critique shape, without invoking a live model in CI

#### Scenario: Prompt sync encodes teaching bar without regressing Gemini bar

- **WHEN** prompt unit tests run
- **THEN** backend and WebLLM prompts encode essential-problem priority, anti source-token-swap, and contrastive-nuance guidance, while still encoding Chinese `reason`/`overallComment`, `現状 → 推奨` + why, strengths-then-gaps overallComment, and the JP-cite 「」 / CN-meta `""`/`“”` quote policy
