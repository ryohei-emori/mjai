## Context

See `proposal.md` - Why for motivation. Relevant current-state facts that shape this design:

- Today, `backend/app/main.py`'s `generate_gemini_suggestions` builds a single fixed-template prompt (system instruction + one hardcoded few-shot example + the request's `originalText`/`targetText`), calls the Gemini `generateContent` REST endpoint directly via `requests` (no SDK), and regex-extracts an embedded `指摘`/`全体講評` JSON blob from the model's free-text response, normalizing it to exactly 5 suggestion entries. `instructionPrompt` is accepted by the request contract but never used.
- `POST /suggestions` is a synchronous FastAPI endpoint with a `mode="mock"` fallback (`BACKEND_MODE` env var) used when `engine != "gemini"`.
- The frontend (`frontend/src/app/page.tsx`, `generateAISuggestions`) currently calls `suggestionsAPI.generateSuggestions(...)` (`frontend/src/app/api.ts`) with `engine: "gemini"` and maps the response into the same `CorrectionSuggestion[]` + `overallComment` shape used for mock data — this shape is a UI-internal contract, not tied to Gemini, so it can be preserved.
- Persistence is independent of generation: `POST /histories` and `POST /proposals` already accept arbitrary `original`/`reason` text regardless of where it came from, so no backend/API changes are needed there.
- `@mlc-ai/web-llm` runs entirely client-side, requires WebGPU, and exposes an OpenAI-Chat-Completions-compatible `CreateMLCEngine(modelId, { initProgressCallback })` API plus `engine.chat.completions.create(...)`.
- The parallel `add-google-authentication` change is assumed to exist and gate the app behind a login; this change only needs to assume "an authenticated session exists" as a precondition, not implement or verify it.

## Goals / Non-Goals

**Goals:**
- Replace the `engine=gemini` code path with client-side WebLLM inference, producing output compatible with the existing `CorrectionSuggestion`/`overallComment` UI shape, so `page.tsx`'s selection/editing/saving logic downstream of `generateAISuggestions` does not need to change.
- Give the user clear, non-blocking feedback for model download progress and for WebGPU/model-load failure, given first-load downloads can be multiple gigabytes.
- Fully remove Gemini-specific backend code, config, and env vars so there is no dangling dead code or leaked capability to call an external LLM from the server.

**Non-Goals:**
- Redesigning `AIProposals`/`CorrectionHistories` persistence, their endpoints, or their DB schema — unaffected, per the confirmed product decision.
- Implementing or specifying the `add-google-authentication` login flow itself — treated as an external precondition.
- Supporting non-WebGPU inference fallback (e.g., WASM-only CPU inference, a hosted-model fallback, or server-side proxying) — out of scope; unsupported environments get a fallback UX, not an alternate inference path.
- Multi-model selection UI (letting the end user pick between several WebLLM models) — a single fixed default model is used initially (see Decisions).

## Decisions

### 1. WebLLM model choice: `Mistral-7B-Instruct-v0.3-q4f16_1-MLC` as the default

This is a bilingual (Japanese ⇄ Chinese) proofreading task requiring: (a) reasonable instruction-following and JSON-shaped output, (b) acceptable multilingual (esp. CJK) quality, and (c) practical inference performance. User testing with SmolLM2-1.7B indicated that larger models produce more usable correction output.

| Candidate | Approx. download (q4f16) | VRAM Required | Context window | Trade-off |
|---|---|---|---|---|
| `SmolLM2-1.7B-Instruct-q4f16_1-MLC` | ~0.9 GB | ~1.8 GB | 8192 tokens | Smallest/fastest; struggled with consistent JSON output and meaningful corrections in testing |
| `Phi-3.5-mini-instruct-q4f16_1-MLC` | ~3.7 GB | ~4 GB | 4096 tokens | Good instruction-following; weaker multilingual/CJK nuance |
| `Mistral-7B-Instruct-v0.3-q4f16_1-MLC` | ~4-5 GB | ~4.5 GB | 4096 tokens | Strong instruction-following, good multilingual quality, well-supported in WebLLM ecosystem |
| `Llama-3.1-8B-Instruct-q4f16_1-MLC` | ~5.0 GB | ~5 GB | 4096 tokens | Better multilingual/instruction-following quality; heavier VRAM footprint |
| `Qwen2.5-7B-Instruct` family | ~4.5 GB | ~4.5 GB | 4096-32k | Strong native Chinese-language performance; alternative for Chinese-heavy tasks |

**Decision**: ship `Mistral-7B-Instruct-v0.3-q4f16_1-MLC` as the default. Mistral 7B offers a good balance of output quality and resource requirements — larger and more capable than SmolLM2/Phi-3.5-mini, with better instruction-following for structured JSON output, while staying within practical VRAM limits (~4.5 GB) for consumer GPUs with WebGPU support. The model ID is stored as a single named constant in the frontend config (`frontend/src/lib/webllm/config.ts`) so switching models remains a one-line change plus re-validation.

**Generation parameters** (aligned with prior optimization work):
- `max_tokens`: 512 (sufficient for JSON output with 5 suggestions + overall comment)
- `temperature`: 0.2 (low temperature for consistent structured output)
- Input truncation: Limit SOURCE+TARGET to ~3000 tokens combined, leaving headroom for system prompt and generation within the 4096 context window

Alternative considered and rejected: keep SmolLM2-1.7B for faster inference and smaller download. Rejected based on user feedback that output quality was insufficient — Mistral 7B's larger capacity produces more actionable correction suggestions.

### 2. Client-side prompt construction

Reuse the existing Chinese-language system instruction and few-shot example currently embedded in `backend/app/main.py` (`SYSTEM_PROMPT`, `FEW_SHOT_EXAMPLES`) as a starting point, ported verbatim into a frontend prompt-building module (e.g. `frontend/src/lib/webllm/prompt.ts`), since that prompt content already encodes the desired output format (JSON `指摘`/`全体講評`) and tone, and preserving it minimizes behavior drift for end users used to the current suggestion style.

Unlike the backend version, the `instructionPrompt` field (previously a no-op, per the baseline spec's "Gemini Prompt Construction" requirement) is instead genuinely appended to the constructed prompt as an optional final instruction block, since there is no longer a reason to accept-but-ignore it — this is a deliberate, minor behavioral improvement bundled into the migration, called out explicitly here as it was a documented no-op in the baseline behavior it wholly replaces.

Prompt assembly, sent as a single user message to `engine.chat.completions.create({ messages: [...] })`:
1. Fixed system instruction (ported `SYSTEM_PROMPT`).
2. Fixed few-shot example (ported `FEW_SHOT_EXAMPLES`).
3. A `## 問題` section embedding the current `originalText` and `targetText` verbatim.
4. If `instructionPrompt` is non-empty, an additional instruction block appended after `## 問題`.

### 3. Response parsing and mapping to the existing suggestion shape

Reuse the same parsing strategy as the current backend (`generate_gemini_suggestions`): regex-extract a `\{\s*"指摘".*\}` JSON blob from the model's text output, parse it, map each `指摘[].箇所`/`コメント` to a suggestion's `original`/`reason` with sequential string ids, and use `全体講評` as `overallComment`. This is ported into a shared frontend parsing utility rather than re-derived, since the prompt still asks the model to produce that exact shape and the parsing logic is a well-tested unit of behavior worth carrying over as-is. Unlike the backend's fixed 5-item padding/truncation (an artifact of the old hardcoded mock-parity contract), the client-side version returns however many `指摘` entries the model actually produced (no forced padding to 5), since there is no longer a mock-mode contract requiring exactly 5 — this is called out as an intentional, minor behavior change, matched by an equivalent spec requirement.

If no JSON blob matches, or parsing fails, the module returns an empty `suggestions` array plus an `overallComment` describing the parse failure — mirroring today's malformed-response handling, but as a user-visible in-UI error state rather than a silent HTTP-200-with-placeholder response, since there's no HTTP boundary to preserve compatibility with anymore.

The mapped `{ suggestions, overallComment }` result is handed directly to the existing `updateCurrentSession({ suggestions, overallComment })` call in `page.tsx`, unchanged from how the Gemini-backed HTTP response was consumed before — this is the seam that keeps everything downstream of generation (selection, editing, `saveCorrections`, `POST /proposals`) untouched.

### 4. WebGPU / model-load failure handling

Before attempting any model load, feature-detect WebGPU via `navigator.gpu` (WebLLM's own `hasModelInCache`/engine creation will also fail fast if unsupported, but detecting it up front lets the UI skip straight to the fallback state instead of surfacing a load-attempt spinner first). On unsupported/failed environments, the "AI提案を生成" button flow surfaces a non-blocking inline message ("このブラウザでは AI 提案機能を利用できません" or similar) instead of the suggestion list, while the rest of the correction workspace (manual/custom correction entry, save flow) remains fully usable — this preserves the existing "3+ selections required to save" flow using only custom corrections when AI generation is unavailable.

### 5. Backend `/suggestions` endpoint: remove entirely (not kept as a pass-through)

**Recommendation: delete `POST /suggestions` and its models (`SuggestionRequest`, `SuggestionResponse`, `CorrectionSuggestion`) entirely from `backend/app/main.py`, rather than keeping it as a thin pass-through.**

Rationale:
- There is no remaining server-side responsibility for suggestion generation once the Gemini call and the mock-mode branch are both gone — a pass-through with "no AI logic" would have nothing left to pass through to (the frontend already has everything it needs client-side: `originalText`, `targetText`, `instructionPrompt`).
- Keeping a dead/near-dead endpoint around is exactly the kind of inconsistency this codebase already suffers from (per `AGENTS.md`'s "reality check" section on stale docs/config) and would need its own justification to exist (e.g., analytics logging), which was not requested.
- The in-memory `session_memories: Dict[str, List[str]]` bookkeeping tied to this endpoint is also unused elsewhere and SHALL be removed with it — it was only ever populated by `/suggestions`.
- If a future need arises (e.g., server-side telemetry on generation events), that should be its own explicit, separately-specified capability rather than a vestigial endpoint kept "just in case."

Alternative considered: keep `/suggestions` as a no-op/pass-through endpoint that simply echoes back an empty response, to minimize the diff and avoid a hard 404 for any stale client. Rejected because there are no other known clients of this endpoint (it's internal to this same frontend, which is being updated in lockstep), and a silently-empty-but-200 endpoint is more confusing to future maintainers than a clean 404/removal.

## Risks / Trade-offs

- **[Risk] Heavy initial download** (multi-GB model fetch on first use) could cause users to abandon the flow or perceive the app as broken. → **Mitigation**: mandatory, prominent progress UI during `initProgressCallback` events; browser-cache the model (WebLLM caches compiled weights via the Cache API by default) so only the very first generation per browser incurs the full download; default to the smallest viable instruct model (Phi-3.5-mini) per Decision 1.
- **[Risk] WebGPU support gaps** on older browsers/devices (older Firefox, some Android WebViews, corporate-locked-down Chrome/Edge builds) mean a nonzero share of users get no AI suggestions at all, with no server-side fallback by design. → **Mitigation**: explicit, friendly fallback UX (Decision 4) that keeps manual/custom correction entry fully functional; this is an accepted trade-off per the confirmed product decision to go "fully client-side," not something this design can fully close.
- **[Risk] Client-side inference quality/consistency regression** versus Gemini (a much larger hosted model) — smaller local models may produce lower-quality or less consistent critique JSON. → **Mitigation**: reuse the existing, already-tuned system prompt/few-shot example (Decision 2) to carry over as much prompt-engineering value as possible; keep the model id swappable (Decision 1) so it can be upgraded post-launch based on observed quality without a design change.
- **[Trade-off] Removing the 5-item padding/truncation contract** (Decision 3) is a visible behavior change from the documented baseline — the UI must already tolerate a variable-length `suggestions` array (it does, since `page.tsx` maps over `suggestions` without assuming a fixed length), but this is called out explicitly since it changes an implicit contract from `baseline-ai-suggestion-generation`.
- **[Risk] Browser compute cost shifted to the user's device** — inference that previously cost the backend a Gemini API call now costs the end user's CPU/GPU/battery and bandwidth every session (until cached). → **Mitigation**: this is the explicit intent of the product decision (eliminate server-side API cost); no further mitigation is in scope here beyond the caching and progress-UX already covered above.

## Migration Plan

1. Land the frontend WebLLM integration (dependency, model-loading module, prompt/parsing module, UI progress/fallback states) behind the existing `generateAISuggestions` call site in `page.tsx`, replacing the `suggestionsAPI.generateSuggestions({ engine: "gemini", ... })` call with the new client-side path. `FRONTEND_MODE=mock` behavior in `page.tsx` can remain as a local-dev/test convenience independent of this change (it does not call the backend or WebLLM either).
2. Remove `suggestionsAPI.generateSuggestions` from `frontend/src/app/api.ts` once nothing calls it.
3. Remove `generate_gemini_suggestions`, `POST /suggestions`, `SuggestionRequest`/`SuggestionResponse`/`CorrectionSuggestion` models, `SYSTEM_PROMPT`/`FEW_SHOT_EXAMPLES`, `GEMINI_API_KEY`/`GEMINI_MODEL`/`GEMINI_API_URL`, and `session_memories` from `backend/app/main.py`.
4. Remove `GEMINI_API_KEY`/`GEMINI_MODEL` from `conf/.env.example` and any references in `README.md`/`docs/github-secrets.md`/CI secrets documentation (leave the actual GitHub Actions secret removal, if any, as an infra/ops follow-up outside this repo's code changes).
5. Deploy frontend and backend together (or backend first) since the backend change is a pure removal with no new required input from the frontend — there is no wire-format coupling between the two beyond `/proposals`, which is unaffected.
6. **Rollback**: if client-side generation proves unacceptably slow/low-quality in practice, rollback is a revert of this change's commits (restoring `/suggestions` + `GEMINI_API_KEY`) rather than a feature flag, since the product decision to fully remove Gemini was explicit and not intended to be run in parallel with the old path.

## Open Questions

- Exact end-user copy/wording for the WebGPU-unavailable and model-load-failure messages is left to implementation/UI polish — does not affect the chosen approach or task breakdown.
- Whether to eventually add a lightweight client-side telemetry/logging signal for model-load failures (to gauge how many real users hit the WebGPU-unsupported fallback) is deferred to a future change; it does not change this design or its specs.
