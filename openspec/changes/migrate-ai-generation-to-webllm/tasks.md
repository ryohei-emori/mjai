## 1. Frontend dependency and environment setup

- [x] 1.1 Add `@mlc-ai/web-llm` to `frontend/package.json` dependencies and install it
- [x] 1.2 Set the default WebLLM model id to `Phi-3.5-mini-instruct-q4f16_1-MLC` (per `design.md` Decision 1) as a single named constant, kept swappable for a future upgrade to `Llama-3.1-8B-Instruct-q4f16_1-MLC` or a Qwen2.5 variant
- [x] 1.3 Add a WebGPU feature-detection utility (e.g. `navigator.gpu` check) usable before attempting any model load

## 2. Client-side model loading

- [x] 2.1 Implement a model-loading module/hook that initializes the WebLLM engine on first suggestion request (not on page load), gated on the user having an authenticated session
- [x] 2.2 Wire WebLLM's progress callback to a UI progress indicator (e.g. percentage/status text) shown while the model downloads/initializes
- [x] 2.3 Cache the initialized engine instance in memory/module scope so subsequent generations in the same page session reuse it instead of reloading
- [x] 2.4 Verify WebLLM's own weight caching (e.g. Cache API/IndexedDB) avoids re-downloading model weights across sessions on the same browser

## 3. Client-side prompt construction and inference

- [x] 3.1 Port the intent of `SYSTEM_PROMPT`/`FEW_SHOT_EXAMPLES` (backend/app/main.py) into a client-side prompt/message template for the WebLLM chat-completion API
- [x] 3.2 Implement prompt construction from `originalText`, `targetText`, and the optional instruction (e.g. the existing "CCTalkからの添削指示" instruction currently passed from `page.tsx`)
- [x] 3.3 Run in-browser inference via the WebLLM engine and capture the model's raw text output
- [x] 3.4 Implement output parsing that extracts the structured critique from the model's response and maps it into the existing `{ id, original, reason }[]` suggestions array plus `overallComment`, matching the shape `SuggestionResponse` used to provide
- [x] 3.5 Handle malformed/unparsable model output gracefully (equivalent to the old Gemini malformed-response handling) without crashing the generation flow

## 4. Frontend integration

- [x] 4.1 Replace the `suggestionsAPI.generateSuggestions` network call in `frontend/src/app/page.tsx`'s `generateAISuggestions` with the new client-side model-loading + inference flow
- [x] 4.2 Remove or repurpose `suggestionsAPI` in `frontend/src/app/api.ts` now that suggestion generation no longer calls a backend endpoint
- [x] 4.3 Preserve existing selection-state restoration and custom-correction merging logic in `generateAISuggestions` so it works unchanged against the new suggestion source
- [x] 4.4 Add UI states for: model loading/progress, generation in progress, and generation success — reusing existing toast/loading patterns where possible

## 5. Unsupported browser/device fallback UX

- [x] 5.1 On WebGPU-unsupported browsers/devices, skip model loading entirely and show a clear, non-blocking message that in-browser AI suggestions are unavailable
- [x] 5.2 On model load or inference failure (WebGPU nominally supported but load/inference errors), show a non-blocking error state distinct from the "unsupported" message
- [x] 5.3 Ensure the manual custom-correction-proposal flow remains fully usable in both fallback cases above

## 6. Backend removal

- [x] 6.1 Remove `generate_gemini_suggestions` from `backend/app/main.py`
- [x] 6.2 Delete the entire `POST /suggestions` endpoint (`generate_suggestions`), including its mock-mode branch, `SuggestionRequest`/`SuggestionResponse`/`CorrectionSuggestion` models, and the `session_memories` dict, per `design.md` Decision 5's recommendation to remove rather than keep as a pass-through
- [x] 6.3 Remove the `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_API_URL` module-level configuration from `backend/app/main.py`
- [x] 6.4 Remove `GEMINI_API_KEY`/`GEMINI_MODEL` entries from `conf/.env.example`
- [x] 6.5 Search the backend and its docs (e.g. `AGENTS.md`, `docs/github-secrets.md`) for other Gemini-specific references tied to this capability and update/remove them for consistency

## 7. Testing and validation

- [x] 7.1 Add/update frontend tests covering: WebGPU-unsupported fallback UX, model-load progress UI, and suggestion-generation output parsing (using a mocked WebLLM engine)
- [ ] 7.2 Manually verify end-to-end suggestion generation in a WebGPU-capable browser (e.g. current Chrome/Edge) against representative original/target text pairs
- [ ] 7.3 Manually verify the unsupported-browser fallback path (e.g. via a browser/flag without WebGPU, or by simulating `navigator.gpu` absence)
- [ ] 7.4 Verify selected/edited suggestions still persist correctly via `POST /proposals` end-to-end after the generation-source change
- [x] 7.5 Verify `backend/app/main.py` no longer references `GEMINI_API_KEY`/`GEMINI_MODEL` and the backend starts/runs correctly without them set

## 8. Documentation reconciliation

- [x] 8.1 Note in this change (or a follow-up) that `openspec/changes/baseline-ai-suggestion-generation` should be treated as superseded once this change is applied, per `proposal.md`
- [x] 8.2 Update `README.md`/`AGENTS.md` references to Gemini-based suggestion generation to describe the new client-side WebLLM flow, once implementation lands
