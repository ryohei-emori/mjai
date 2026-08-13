## 1. Prompts (MUST why + anti-false-缺少)

- [x] 1.1 Update `backend/app/llm/prompts.py`: add rules that (a) every `reason` MUST include why the correction is needed (what/where + 为什么), for all critique types; (b) prefer real meaning/grammar/fluency/spelling; (c) do not invent false 「缺少」 particles when Japanese is acceptable. Keep Chinese-enforcement intact. Adjust few-shot so each reason includes 为什么.
- [x] 1.2 Sync the same rules into `frontend/src/lib/webllm/prompts/system.ts` (and `fewShot.ts` if needed) so WebLLM matches backend intent without large token bloat.

## 2. Weak-reason heuristic (test-facing)

- [x] 2.1 Add a lightweight `has_weak_critique_reason()` (or equivalent) in `backend/app/llm/parser.py` for location-only 「缺少「X」在…」 without necessity markers; do **not** wire into `generate_suggestions()` retry in this change (per design).
- [x] 2.2 Export for tests; document in module docstring that Spec MUST why-in-reason is primarily prompt-enforced; heuristic is regression aid.

## 3. Fixtures and tests

- [x] 3.1 Add `backend/tests/fixtures/semantic_reason_cases.py` with Case A (false 「缺少「が」」) and Case B (weak 「缺少「は」」 without 为什么) plus a compliant why-including reason example.
- [x] 3.2 Extend `backend/tests/test_llm_prompts.py` to assert MUST why-in-reason and anti-false-「缺少」 wording in backend prompts.
- [x] 3.3 Add parser/heuristic tests (new or in `test_llm_parser.py`) covering Case B weak fail, compliant pass, and Case A bad-pattern documentation assert.
- [x] 3.4 Add a small frontend prompt assertion if an existing Jest pattern already covers WebLLM prompts; otherwise rely on backend sync + manual note.

## 4. Verify

- [x] 4.1 Run relevant pytest (`test_llm_prompts`, `test_llm_parser`, and any new tests).
- [x] 4.2 Note manual verify steps for the two example sentences in a short comment in the fixture module or tasks completion notes.
