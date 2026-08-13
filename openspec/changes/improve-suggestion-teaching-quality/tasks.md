## 1. Prompts (teaching bar)

- [x] 1.1 Update `backend/app/llm/prompts.py`: essential-problem priority; anti trivial-surface / anti source-token-swap / contrastive-nuance-before-preference; class-of-error why for future translations; reinforce (do not regress) Chinese reason, `現状 → 推奨`, strengths-then-gaps overallComment, quote policy, anti-false-particles.
- [x] 1.2 Adjust `FEW_SHOT_EXAMPLE` so at least one reason shows contrastive nuance (current vs recommended) and none models the three anti-patterns as “good.”
- [x] 1.3 Sync WebLLM `system.ts` / `fewShot.ts` (ultra-short Chinese bullets for teaching rules).

## 2. Fixtures and tests

- [x] 2.1 Add `backend/tests/fixtures/teaching_quality_cases.py` with documented bad (trivial omit, bare source-swap, preference-without-contrast) and good (contrastive / class-of-error) reason shapes; cross-link from `gemini_quality_bar_cases.py`.
- [x] 2.2 Update `test_llm_prompts.py` + frontend Jest prompt tests for teaching-bar cues without dropping Gemini-bar assertions.

## 3. Verify

- [x] 3.1 Run focused pytest (`test_llm_prompts` + fixture import sanity) and Jest prompt tests.
- [x] 3.2 Confirm fixtures note manual verify tips; do not edit gemini_provider / GEMINI env / exemplar-translation / frontend/out.
