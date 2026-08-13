## 1. Prompts (structure + domain + quotes)

- [x] 1.1 Update `backend/app/llm/prompts.py`: overallComment strengths→gaps; reason shape `現状 → 推奨` + accessible why; CN→JP literary/academic domain; 「」 only for JP TARGET cites, `""`/`“”` for Chinese meta; relax over-strict 1–2 sentence caps where they block density; keep anti-false-缺少 + Chinese-only + SOURCE fidelity + multi-paragraph coverage.
- [x] 1.2 Replace/expand `FEW_SHOT_EXAMPLE` with 1–2 short Gemini-shaped Chinese examples (`“”` for CN, 「」 for JP forms).
- [x] 1.3 Sync WebLLM `system.ts` / `fewShot.ts` (ultra-short); update `suggestions.py` reinforce line if it still absolute-forbids 「」.

## 2. Corner-quote heuristic

- [x] 2.1 Narrow `has_japanese_corner_quotes_in_critique` per design.md (misuse / Chinese prose in 「」, allow JP cites); keep wired to retry; update docstring.

## 3. Fixtures and tests

- [x] 3.1 Add `backend/tests/fixtures/gemini_quality_bar_cases.py` documenting desired critique shapes (+ epic SOURCE/TARGET pointer or short excerpts); optional note in `semantic_reason_cases.py`.
- [x] 3.2 Update `test_llm_prompts.py` + frontend Jest for new structure/domain/quote policy + few-shot shapes.
- [x] 3.3 Update parser tests: allow 「叙事詩」-style JP cites; still flag 「时态」 / Chinese-prose misuse.

## 4. Verify

- [x] 4.1 Run focused pytest (`test_llm_prompts`, `test_llm_parser`, related) and Jest prompt tests.
- [x] 4.2 Confirm fixtures note manual verify steps with provided SOURCE/TARGET (no live LLM in CI).
