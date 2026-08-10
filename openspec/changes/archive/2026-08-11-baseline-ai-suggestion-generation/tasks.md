## 1. Baseline Accuracy Verification

- [x] 1.1 Verify the request/response contract in `specs/ai-suggestion-generation/spec.md` matches `SuggestionRequest`, `SuggestionResponse`, and `CorrectionSuggestion` in `backend/app/main.py`.
- [x] 1.2 Verify the engine-selection and mock-fallback requirements match the `generate_suggestions` endpoint logic (`BACKEND_MODE`, `engine` body/query param resolution).
- [x] 1.3 Verify the Gemini prompt-construction requirement (including the no-op `instructionPrompt`) matches `generate_gemini_suggestions`'s prompt-building code.
- [x] 1.4 Verify the Gemini success-path parsing/normalization requirement (5-item padding/truncation, `指摘`/`全体講評` field mapping) matches the current implementation.
- [x] 1.5 Verify the missing-API-key and error/malformed-response fallback requirements match the corresponding `except`/guard branches.

## 2. Documentation Only — No Implementation Work

- [x] 2.1 Confirm no code changes are required: this change documents existing, already-implemented behavior as a baseline spec.
- [x] 2.2 Confirm `openspec/specs/ai-suggestion-generation/` did not previously exist, so this change is additive-only (`## ADDED Requirements`), not a modification of prior documented behavior.
- [x] 2.3 Flag any discrepancy found during verification (steps 1.1-1.5) as a follow-up item for a future change, rather than silently editing behavior or spec to match.
