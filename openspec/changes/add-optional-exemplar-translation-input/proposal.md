## Why

Users always have a model/exemplar answer translation relative to the SOURCE TEXT (原文), but the workspace today only accepts SOURCE TEXT and TARGET TEXT (the learner's attempt). Without a place to paste that exemplar, the AI cannot ground corrections against a known-good reference, so suggestions are less precise than the workflow allows. An optional 「模範回答訳文」 field closes that gap without blocking generation when the user has none.

## What Changes

- **Add an optional 「模範回答訳文」 / model-exemplar translation input** in the correction workspace, styled like the existing SOURCE TEXT / TARGET TEXT cards (MD3, bilingual English-primary headers per `docs/UI-DESIGN.md`).
- **Keep Generate AI Suggestions working when the field is empty** — the field is never required for enabling the generate button or for a successful API/WebLLM call.
- **When non-empty, pass the exemplar into suggestion generation** as optional prompt context for both cloud (`POST /api/suggestions`) and WebLLM offline paths, so the model can compare the TARGET TEXT against a known-good translation of the SOURCE TEXT.
- **When empty, omit the field** from the request/prompt and behave exactly as today (SOURCE + TARGET only).
- **Persist the field per session in localStorage** alongside existing SOURCE/TARGET draft persistence (same draft object / debounce pattern), so reload and session switch restore it.
- **Separate Spec / OpenSpec change** from any Chinese-language enforcement work — this change does not fold into or depend on that effort.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: gains a requirement for an optional exemplar-translation textarea (模範回答訳文) next to SOURCE/TARGET, persisted like other draft text fields, not required for "AI提案を生成".
- `ai-suggestions`: gains a requirement that `POST /api/suggestions` (and the shared prompt builders used by Groq/Cloudflare/WebLLM) accept an optional exemplar-translation string; when present and non-empty it is included as reference context in the prompt; when absent/empty it is omitted and generation proceeds as today.

## Impact

- **Frontend UI**: `frontend/src/app/page.tsx` (new session field + card in the center pane), possibly `HighlightedTextarea` reuse or a plain textarea for the exemplar (no suggestion-span highlighting required for the exemplar itself).
- **Frontend draft persistence**: extend `PersistedDraft` / session state with the new field; merge/restore/clear alongside `originalText`/`targetText`.
- **Frontend API client**: `frontend/src/app/api.ts` — optional field on the suggestions request body.
- **Frontend WebLLM**: `frontend/src/lib/webllm/prompts/` (templates / prompt assembly) — optional section when exemplar is provided.
- **Backend**: `backend/app/main.py` (accept optional field), `backend/app/llm/prompts.py` + provider call sites — include exemplar in prompt only when non-empty. No DB schema changes; exemplar is not persisted server-side in this change.
- **Docs**: brief note in `docs/UI-DESIGN.md` bilingual label table / layout sketch if the third card is added; `docs/SYSTEM-DESIGN.md` only if the `/api/suggestions` request contract section is updated.
- **No breaking API change**: field is additive and optional; existing clients omitting it keep working.
- **Out of scope**: Chinese-comment enforcement Spec; saving exemplar into correction histories / proposals tables; requiring the field for generation.
