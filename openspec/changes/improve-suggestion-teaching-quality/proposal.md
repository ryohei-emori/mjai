## Why

After `raise-suggestion-quality-to-gemini-bar`, critiques already use Chinese, `現状 → 推奨`, and strengths-then-gaps — but models still often ship **cosmetic** or **source-token-swap** “fixes” that do not teach the translator. Users need 添削 that builds **future translation competence** (essential gaps + contrastive nuance), not “A→B because B sounds better / closer to SOURCE wording.”

## What Changes

- Tighten prompt teaching bar (backend + WebLLM sync): prefer essential problems (meaning drift, systematic grammar, spelling that reveals missing word knowledge, register/domain misuse with why, modality, etc.).
- Explicit **anti-patterns** in prompts + few-shot / fixtures: (1) trivial surface omission as the main point; (2) swap-to-SOURCE-token without pedagogy; (3) recommend a JP form without contrastive nuance of current vs recommended.
- Require **contrastive explanation before preference** for lexical upgrades; reinforce **why this class of error matters** for future translations (keep existing accessibility MUST).
- Keep / reinforce existing MUST: Chinese `reason`/`overallComment`, why-necessary, `現状 → 推奨` shape, `""`/`“”` for CN / 「」 for JP cites, no false particles, no auto WebLLM, strengths-first `overallComment`.
- Extend fixtures/tests (extend `gemini_quality_bar_cases` and/or add `teaching_quality_cases.py` + prompt assertions). OpenSpec `ai-suggestions` delta.
- **Out of scope:** Gemini key pool / `gemini_provider` / `GEMINI_*` env; exemplar-translation input change; `frontend/out`; provider failover logic.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `ai-suggestions`: Teaching-oriented critique quality — anti-cosmetic / anti-source-swap / contrastive-nuance rules; essential-problem priority; reinforce (do not regress) Gemini-bar structural MUSTS.

## Impact

- `backend/app/llm/prompts.py` — teaching anti-patterns + desired patterns; few-shot contrast examples
- `frontend/src/lib/webllm/prompts/{system,fewShot}.ts` — sync (ultra-short where needed)
- `backend/tests/fixtures/` — teaching-quality anti/compliant examples (+ optional epic pointer notes)
- `backend/tests/test_llm_prompts.py` + frontend Jest prompt tests
- `openspec/changes/improve-suggestion-teaching-quality/specs/ai-suggestions/spec.md` — delta requirements
- No provider modules, no API/DB schema change, no Gemini pool collision
