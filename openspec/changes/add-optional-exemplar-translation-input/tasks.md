## 1. Backend request + prompt

- [x] 1.1 Accept optional `exemplarTranslation` on `POST /api/suggestions` in `backend/app/main.py` (trim; treat missing/empty as absent; do not require it)
- [x] 1.2 Extend `backend/app/llm/prompts.py` `build_user_prompt` / `build_messages` to take optional exemplar text; when non-empty after trim, insert a `模範回答訳文：...` block between 原文 and 添削対象; when empty, omit the block entirely
- [x] 1.3 Add a short SYSTEM_PROMPT note that 模範回答訳文 is an optional known-good reference for calibrating corrections (not text to copy blindly into suggestions) — implemented as `EXEMPLAR_REFERENCE_RULES` + `build_system_prompt()`, appended only when the exemplar is non-empty (see design Decision 4 resolution and 4b)
- [x] 1.4 Thread the optional field through `backend/app/llm/suggestions.py` (and any provider call sites) into `build_messages`

## 2. Backend tests

- [x] 2.1 Add/adjust tests: request without `exemplarTranslation` (or empty) still succeeds and builds a SOURCE/TARGET-only user prompt (`TestOptionalExemplarTranslation`, plus byte-identical assertions for the system message)
- [x] 2.2 Add test: non-empty `exemplarTranslation` appears in the constructed user prompt under the exemplar section (also asserted at the `generate_suggestions` layer via the messages sent to the provider)
- [x] 2.3 Run backend pytest and confirm no regressions — 270 passed, 1 deselected (`-m "not integration"`)

## 3. WebLLM offline parity

- [x] 3.1 Update `frontend/src/lib/webllm/prompts/` (templates / assembly) so a non-empty exemplar is included as a labeled reference section; empty omits it (`SECTION_EXEMPLAR`, `EXEMPLAR_REFERENCE_RULES`, `buildPrompt`)
- [x] 3.2 Pass exemplar into the WebLLM generate path from session state when offline mode runs (`PromptInput.exemplarTranslation`, threaded from `processJobAsync`)
- [x] 3.3 Add or update jest coverage for prompt assembly with/without exemplar (`prompt.test.ts`, `prompts.test.ts`)

## 4. Frontend API + session state

- [x] 4.1 Add optional `exemplarTranslation?: string` to `suggestionsAPI.generate` in `frontend/src/app/api.ts`; key omitted unless trimmed non-empty (covered by `suggestionsExemplar.test.ts`)
- [x] 4.2 Add `exemplarTranslation` to session state types in `frontend/src/app/page.tsx` (default `""`)
- [x] 4.3 Extend `PersistedDraft` + load/save/clear helpers and the debounced persistence effect to include `exemplarTranslation`
- [x] 4.4 Ensure `loadSessions()` / session-switch restore merges exemplar from in-memory state or localStorage (same preference order as SOURCE/TARGET)
- [x] 4.5 Clear persisted exemplar on confirmed save with other draft fields (via existing `clearDraftFromStorage`); exemplar is not cleared when TARGET is cleared after generate

## 5. Workspace UI

- [x] 5.1 Add EXEMPLAR TEXT (模範回答訳文) MD3 card between SOURCE TEXT and TARGET TEXT — extracted as `frontend/src/components/ui/exemplar-text-card.tsx` so the planned collapsible treatment wraps a self-contained component
- [x] 5.2 Wire `onChange` to `updateCurrentSession({ exemplarTranslation })`; generate button enablement remains SOURCE/TARGET-only
- [x] 5.3 Pass `exemplarTranslation` into cloud `suggestionsAPI.generate` and WebLLM job processing when non-empty
- [x] 5.4 Update `docs/UI-DESIGN.md` layout sketch + bilingual label table for the third card; `docs/SYSTEM-DESIGN.md` request-body note; `AGENTS.md` Request Schema section

## 6. Verification

- [x] 6.1 Generate with empty exemplar → succeeds, same as today (live `scripts/live_exemplar_e2e.py`, plus byte-identical prompt assertions in both test suites)
- [x] 6.2 Generate with filled exemplar → prompt includes exemplar; suggestions still return, and no critique names the exemplar (live e2e + `scripts/live_exemplar_compare.py` A/B)
- [~] 6.3 Reload / session switch restores exemplar; generate clears TARGET only — implemented on the exact `PersistedDraft` path SOURCE/TARGET already use (same key, same debounce, same merge precedence) and type-checked, but browser-level manual QA is still outstanding
- [x] 6.4 Run frontend lint/build and jest with no new failures — 192 jest tests passed; `npm run lint` clean apart from the pre-existing `no-page-custom-font` warning in `layout.tsx`
- [x] 6.5 Run `openspec validate add-optional-exemplar-translation-input --strict` — valid

## 7. Follow-ups (not in this change)

- [ ] 7.1 Manual browser QA for 6.3 (reload + session switch round-trip of the exemplar field)
- [ ] 7.2 Manual WebLLM (Mistral-7B) QA with a filled exemplar — the guard is a two-line condensation and was not live-probed on a 7B model; the empty-exemplar offline path is provably unchanged
