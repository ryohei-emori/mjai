## 1. Backend prompt exemplars and hedges

- [x] 1.1 Rebuild `FEW_SHOT_EXAMPLE` in `backend/app/llm/prompts.py` to five distinct genuine items on the existing corpus, covering domain term, register, collocation, subject–predicate grammar (omitting `sourceExcerpt`), and lost 推量 modality.
- [x] 1.2 Remove the model-facing directive text from inside few-shot `reason` strings, and drop the anti-label reminder from the few-shot preamble (it stays in the system prompt and the reminder block).
- [x] 1.3 Add a note stating the example's item count reflects its short input and is not a cap.
- [x] 1.4 Replace `质量优先于条数` with an explicit statement that anti-fabrication is not a reason to omit genuine issues; replace the global brevity cue with a per-item length bound that still requires fix + why.
- [x] 1.5 Reorganise `SYSTEM_PROMPT` into labelled sections with coverage/count as its own final block, preserving all existing rule content.
- [x] 1.6 Trim the duplicated clauses in `build_user_prompt`'s reminder block while keeping every rule it is the last line of defence for.

## 2. WebLLM prompt sync (kept small for Mistral 7B)

- [x] 2.1 Replace the duplicate-point third item in `fewShot.ts` with a distinct semantic/grammar issue, keep an item without `sourceExcerpt`, and add the count note.
- [x] 2.2 Merge the duplicated coverage/anti-padding clauses in `system.ts` and apply the same hedge replacements, keeping total length at or below the current size.
- [x] 2.3 Update the doc comments in both files to record this change.

## 3. Retry nudge

- [x] 3.1 De-duplicate `LANGUAGE_RETRY_NUDGE` in `backend/app/llm/suggestions.py` so it reinforces coverage and language without restating the full rule set.

## 4. Tests and fixtures

- [x] 4.1 Extend `backend/tests/test_llm_prompts.py`: few-shot has ≥5 items, at least one omits `sourceExcerpt`, no item repeats another's correction, no model-facing directive text, count-note present, no count-trading hedge.
- [x] 4.2 Extend `frontend/src/lib/webllm/__tests__/prompts.test.ts` with the equivalent assertions for the WebLLM prompt and few-shot.
- [x] 4.3 Add a regression assertion that no fixed-length slice caps the parsed suggestion array.
- [x] 4.4 Update `backend/tests/fixtures/gemini_quality_bar_cases.py` / `teaching_quality_cases.py` manual-verify notes for the exemplar requirements.
- [x] 4.5 Run backend pytest and frontend jest; fix regressions.

## 5. Live sanity probe (best effort)

- [x] 5.1 Run a few iterations of `backend/scripts/live_chinese_15x.py` on the epic corpus before and after, comparing `n_suggestions`; record the result. Skip or shorten if quota-limited, and say so. Never log key values.

## 6. Docs

- [x] 6.1 If `AGENTS.md` describes the prompt's coverage expectations, note that few-shot exemplars must demonstrate the density and priority categories. Failover order unchanged.
