## 1. Prompts (accessibility + quotes + SOURCE + coverage)

- [x] 1.1 Update `backend/app/llm/prompts.py`: (a) accessible why MUST for every reason; (b) Chinese critique uses `""`/`“”`, never 「」; (c) accurate SOURCE citation / no invent-misquote / no drift rewrites; (d) multi-paragraph coverage guidance; (e) keep anti-false-缺少 + Chinese-only. Rewrite few-shot citations to `""`.
- [x] 1.2 Sync the same rules into `frontend/src/lib/webllm/prompts/system.ts` and `fewShot.ts` (ultra-short; no large token bloat). Update `suggestions.py` language reinforce line if it still teaches 「」.

## 2. Parser heuristics

- [x] 2.1 Extend quote stripping in `has_non_chinese_reason` path to include `""` / `“”` (keep 「」 strip for legacy). Extend weak-缺少 pattern to `""` form; keep test-only (no retry).
- [x] 2.2 Add `has_japanese_corner_quotes_in_critique()` for 「/」 in reason/overallComment; wire into `generate_suggestions()` retry with Chinese check (low-noise). Export + docstring.

## 3. Fixtures and tests

- [x] 3.1 Extend `backend/tests/fixtures/semantic_reason_cases.py` with Case C (meaning/wording drift) and update A/B examples toward `""` style; note meaning-misquote / accessibility manual checks.
- [x] 3.2 Extend `backend/tests/test_llm_prompts.py` for accessibility, quote marks, SOURCE fidelity, paragraph coverage wording.
- [x] 3.3 Extend parser tests: weak-reason with `""`; corner-quote heuristic pass/fail; Chinese detect with `""` cites.
- [x] 3.4 Extend frontend Jest prompt assertions for quote marks + accessibility (+ coverage/SOURCE if short).

## 4. Verify

- [x] 4.1 Run focused pytest (`test_llm_prompts`, `test_llm_parser`, related) and Jest prompt tests.
- [x] 4.2 Confirm tasks/fixtures note the five user feedback points for manual UI smoke if needed.
