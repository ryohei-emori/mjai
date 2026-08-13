## 1. Measure the real cause

- [x] 1.1 Add `backend/scripts/live_gemini_coverage.py` reporting suggestion count, `finishReason`, `usageMetadata`, elapsed vs `GEMINI_TIMEOUT`, and each pooled model's advertised token limits, with `maxOutputTokens` / `thinkingConfig` sweep knobs and no key output
- [x] 1.2 Probe default thinking on both pooled models against the epic fixture and record latency, finish reason, token usage, suggestion count — 20.7–21.0s, `STOP`, 952–1067 candidate + 2920–3798 thought tokens, 7 suggestions, **2 of 4 calls timed out at 22s**
- [x] 1.3 Probe `thinkingLevel: low` and `thinkingBudget: 0` on both pooled models and record which fields each model accepts — `thinkingLevel` accepted by both; `thinkingBudget: 0` returns HTTP 400 INVALID_ARGUMENT on `gemini-3.6-flash`
- [x] 1.4 Confirm from the shared DB which real run produced only 3 proposals and which provider served it — 2026-08-13 23:07, `provider=api`, 704-char / 3-paragraph TARGET, 3 proposals, mean reason 113 chars

## 2. Constrain Gemini thinking

- [x] 2.1 Add `thinkingConfig.thinkingLevel` to `generationConfig` in `gemini_provider.py`, defaulting to `low`
- [x] 2.2 Support `GEMINI_THINKING_LEVEL` override, where the opt-out value omits `thinkingConfig` entirely
- [x] 2.3 Raise `maxOutputTokens` 8192 → 16384, documenting the 65536 model cap in a comment

## 3. Make token usage observable

- [x] 3.1 Log `usageMetadata` prompt / candidate / thoughts / total counts alongside `finishReason`
- [x] 3.2 Ensure a response without `usageMetadata` still extracts text without raising

## 4. Tests

- [x] 4.1 Unit-test the default payload: `thinkingLevel: low` present, `maxOutputTokens` 16384, inside the model cap
- [x] 4.2 Unit-test `GEMINI_THINKING_LEVEL` override and its opt-out behavior
- [x] 4.3 Unit-test usage-metadata logging and the missing-`usageMetadata` path
- [x] 4.4 Parser regression: truncated multi-item JSON retains every complete item with contiguous ids
- [x] 4.5 Run backend pytest and frontend jest; confirm no regressions — 270 passed (1 live `integration` test deselected; it is skipped in CI and fails locally only from free-tier 429 exhaustion across all three providers), jest 192 passed
- [x] 4.6 Re-probe through the real provider path after the fix — 4/4 success, 7.2–13.8s, `STOP`, 1379–1964 candidate tokens, 0 thought tokens, 10–20 suggestions

## 5. Documentation

- [x] 5.1 Update `AGENTS.md` Gemini rows with the thinking level, new token budget, measured latency, and `GEMINI_THINKING_LEVEL`
- [x] 5.2 Update `docs/SYSTEM-DESIGN.md` with the same numbers and the timeout trade-off rationale
