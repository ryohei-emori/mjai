## Why

MJAI currently generates AI correction suggestions server-side by calling the Google Gemini API from `backend/app/main.py` (`generate_gemini_suggestions`, invoked via `POST /suggestions`). This requires the backend to hold and protect a `GEMINI_API_KEY`, incurs a per-request hosted-model API cost, and ties suggestion quality/availability to a third-party API's uptime and pricing. The product direction has now shifted to running AI inference entirely client-side using WebLLM (`@mlc-ai/web-llm`), so that correction suggestions are generated in the user's browser (via WebGPU/WASM) once they are authenticated, with no server-side model call, no API key to manage, and no per-request inference cost to the backend. This change replaces the Gemini-backed generation path with client-side WebLLM inference.

## What Changes

- **BREAKING**: Remove the server-side Gemini suggestion-generation path entirely — `generate_gemini_suggestions`, the `GEMINI_API_KEY`/`GEMINI_MODEL`/`GEMINI_API_URL` configuration, and the `engine=gemini` branch of `POST /suggestions` are deleted from `backend/app/main.py`. No server-side fallback to Gemini (or any other hosted LLM) is kept.
- **BREAKING**: Remove `GEMINI_API_KEY`/`GEMINI_MODEL` from `conf/.env.example` and any other Gemini-specific configuration/documentation for this capability.
- Add `@mlc-ai/web-llm` as a frontend dependency and implement client-side suggestion generation in the browser: model loading/initialization (with progress feedback), prompt construction from `originalText`/`targetText`/optional instruction, in-browser inference, and parsing of the model output into the existing `suggestions` (`id`/`original`/`reason`) + `overallComment` shape the UI already expects.
- Add graceful degradation for browsers/devices that do not support WebGPU (or otherwise fail to load the WebLLM model): a clear, non-blocking UX state indicating in-browser AI suggestions are unavailable, without crashing the correction workflow.
- Preserve the existing persistence flow unchanged: suggestions the user selects/edits are still submitted via the existing `POST /proposals` endpoint exactly as today; this change affects only how suggestions are generated, not how they are stored.
- Precondition (owned by a sibling change, not designed here): the client-side generation flow assumes the user is already authenticated via Google auth before a model load/generation is attempted.
- Supersedes the not-yet-archived `baseline-ai-suggestion-generation` change: once this change is applied, that baseline capability documentation describes a Gemini-backed flow that no longer exists and must be reconciled (superseded/replaced, not merged) rather than treated as the current contract for `ai-suggestion-generation`.

## Capabilities

### New Capabilities
- `ai-suggestion-generation`: Client-side (in-browser, WebLLM-based) generation of AI correction suggestions from an original/target text pair, including model loading, in-browser inference, unsupported-environment fallback, and unchanged downstream persistence via `POST /proposals`. (`openspec/specs/ai-suggestion-generation/` does not exist yet since the prior baseline change documenting the Gemini-based version of this capability has not been archived/synced; this change's delta is therefore expressed as `ADDED Requirements` and, once applied, should be treated as replacing — not merging with — the pending `baseline-ai-suggestion-generation` proposal.)

### Modified Capabilities
- None (no other synced capability specs exist yet under `openspec/specs/`).

## Impact

- **Affected code (backend)**: `backend/app/main.py` — delete `generate_gemini_suggestions`, the `engine=gemini` branch of `generate_suggestions`/`POST /suggestions`, and the `GEMINI_API_KEY`/`GEMINI_MODEL`/`GEMINI_API_URL` module-level configuration. `backend/requirements.txt` is unaffected (no dedicated Gemini SDK was ever added; `requests` may still be used elsewhere).
- **Affected code (frontend)**: `frontend/package.json` (new `@mlc-ai/web-llm` dependency), `frontend/src/app/api.ts` (`suggestionsAPI` no longer calls a backend endpoint for generation), `frontend/src/app/page.tsx` (`generateAISuggestions` flow reimplemented to run model loading + inference in-browser), plus new UI for model-load progress and unsupported-browser fallback.
- **Configuration**: `conf/.env.example` — remove `GEMINI_API_KEY`/`GEMINI_MODEL`. No new secrets are introduced (WebLLM runs client-side with publicly hosted model weights).
- **Dependencies removed**: server-side dependency on the Gemini `generateContent` REST API.
- **Dependencies added**: `@mlc-ai/web-llm` (browser-side, WebGPU/WASM-based inference).
- **Out of scope (owned by sibling changes)**: Google authentication (assumed as a precondition), Supabase/database persistence migration (persistence via `POST /proposals` is referenced as unchanged, not redesigned), Vercel frontend deployment.
