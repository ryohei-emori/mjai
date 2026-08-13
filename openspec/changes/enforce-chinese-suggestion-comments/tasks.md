## 1. Backend prompts

- [x] 1.1 Update `backend/app/llm/prompts.py` SYSTEM_PROMPT to lead with the primary correction brief 「意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。」 and keep JSON schema / ≥5 / sourceExcerpt rules
- [x] 1.2 Strengthen field-level language rules so `reason`/`overallComment` MUST be Simplified Chinese (unmistakable; forbid Japanese), while `original`/`sourceExcerpt` stay Japanese; refresh FEW_SHOT_EXAMPLE to demonstrate the split under the new framing

## 2. Backend language detection + retry

- [x] 2.1 Tighten `has_non_chinese_reason()` in `backend/app/llm/parser.py`: Hiragana/Katakana + halfwidth Katakana + careful Japanese particle/function-word patterns; do not reject pure Simplified Chinese; keep `original`/`sourceExcerpt` exempt
- [x] 2.2 Confirm `backend/app/llm/suggestions.py` still retries on `has_non_chinese_reason()` within `MAX_PARSE_RETRY_ATTEMPTS` (3) and returns last result without raising on exhaustion (adjust only if detector API/docs need updating)

## 3. WebLLM prompt + minimal client mirror

- [x] 3.1 Update `frontend/src/lib/webllm/prompts/system.ts` and `fewShot.ts` to match the new task framing and stronger Chinese rules (keep ultra-concise style where possible)
- [x] 3.2 Add minimal `hasNonChineseReason()` in `frontend/src/lib/webllm/parser.ts` mirroring backend heuristics; wire only if a small call-site fits, otherwise export for tests

## 4. Tests

- [x] 4.1 Extend `backend/tests/test_llm_parser.py` for new detection cases (halfwidth kana, JP function patterns, pure Chinese still passes, original/sourceExcerpt exempt)
- [x] 4.2 Add/adjust `backend/tests/` coverage for prompt framing/language phrases and confirm Chinese-language retry tests in `test_llm_suggestions.py` still pass with the stricter detector
- [x] 4.3 Add a 15-iteration verification test (loop/parametrize) under `backend/tests/` that repeatedly exercises detector + enforcement/retry with mocked Japanese→Chinese responses; keep CI deterministic (optional live smoke marked integration / skip-without-key)
- [x] 4.4 Add a light frontend unit test for `hasNonChineseReason` if exported
- [x] 4.5 Run backend pytest (docker or local) and fix regressions introduced by this change

## 5. Verification

- [x] 5.1 `openspec validate enforce-chinese-suggestion-comments --strict` (or equivalent) passes
- [ ] 5.2 Commit and push to main (no secrets)
