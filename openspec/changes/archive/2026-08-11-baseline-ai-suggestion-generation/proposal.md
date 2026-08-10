## Why

MJAI recently adopted OpenSpec, but no capability specs exist yet under `openspec/specs/`. The AI-suggestion-generation behavior (Gemini-backed correction suggestions via `POST /suggestions`) is already implemented and running in production, but its behavior is undocumented outside of source code. This change establishes an accurate baseline spec of the existing, already-implemented behavior so that future changes to this capability can be proposed and reviewed against a known contract. This is a documentation-only change; no functional behavior is modified.

## What Changes

- Document the current `POST /suggestions` endpoint contract (`SuggestionRequest` / `SuggestionResponse` shapes) as-is.
- Document the Gemini-backed generation path (`generate_gemini_suggestions`): prompt construction, fixed 5-suggestion normalization, response parsing, and fallback/error behavior when the Gemini API key is missing, the HTTP call fails, or the response is malformed.
- Document the mock generation path used when no Gemini engine is requested (`BACKEND_MODE=mock`, the default), which returns a fixed, hardcoded set of suggestions regardless of input text.
- Document the session-id handling (`sessionId` echoed or generated) and the in-memory `session_memories` bookkeeping tied to this endpoint.
- No code, API, or configuration changes are made as part of this change.

## Capabilities

### New Capabilities
- `ai-suggestion-generation`: Generation of AI-based Japanese/Chinese translation-correction suggestions from an original/target text pair, via the Gemini API or a mock fallback, exposed through the `POST /suggestions` endpoint.

### Modified Capabilities
- None.

## Impact

- **Affected code (read-only, documentation baseline)**: `backend/app/main.py` (`SuggestionRequest`, `SuggestionResponse`, `CorrectionSuggestion` models; `SYSTEM_PROMPT`/`FEW_SHOT_EXAMPLES`; `generate_gemini_suggestions`; `generate_suggestions` endpoint; `GEMINI_API_KEY`/`GEMINI_MODEL`/`GEMINI_API_URL` configuration).
- **Dependencies**: `requests` (plain HTTP calls to the Gemini `generateContent` REST endpoint — no dedicated Gemini SDK is used); `GEMINI_API_KEY` and optional `GEMINI_MODEL` environment variables.
- **Related but out of scope**: Persistence of generated suggestions as `AIProposal` records (separate `POST /proposals` endpoint and `Session`/`CorrectionHistory`/`AIProposal` CRUD), owned by a sibling baseline-documentation change. This spec only references that relationship where the `sessionId` field is concerned.
- **No runtime/behavioral impact**: this is a planning-only, documentation baseline change.
