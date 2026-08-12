## 1. Backend schema + prompt + parser

- [x] 1.1 Update `backend/app/llm/prompts.py` SYSTEM_PROMPT: add `sourceExcerpt` to the output-format example, add its language rule (stays in SOURCE TEXT's language, i.e. Japanese, same as `original`), and instruct the model to omit/empty it when no clear correspondence exists
- [x] 1.2 Update `backend/app/llm/prompts.py` FEW_SHOT_EXAMPLE: add `sourceExcerpt` to at least one suggestion that has a clear correspondence, and demonstrate omission/empty-string for at least one that doesn't
- [x] 1.3 Update `backend/app/llm/parser.py`: add `sourceExcerpt` to `CorrectionSuggestion` TypedDict, extract it in `parse_model_output()` with a multi-key fallback (mirroring `original`/`reason`), defaulting to `""`
- [x] 1.4 Update `backend/app/llm/parser.py` module/function docstrings to document the new field and its fallback keys

## 2. Backend tests

- [x] 2.1 Add test: `sourceExcerpt` extracted when present under the canonical key
- [x] 2.2 Add test: `sourceExcerpt` defaults to `""` when absent from the item
- [x] 2.3 Add test: `sourceExcerpt` extracted via an alternate/fallback key name
- [x] 2.4 Add test: `sourceExcerpt` containing Hiragana/Katakana does NOT trigger `has_non_chinese_reason()` (exempt, same as `original`)
- [x] 2.5 Run `backend pytest` (inside the running `mjai-backend-1` container) to confirm no regressions — 102 passed (was 92 before this change's tests), 28 skipped

## 3. WebLLM offline parity

- [x] 3.1 Update `frontend/src/lib/webllm/prompts/system.ts` to add `sourceExcerpt` to the output format + language rule
- [x] 3.2 Update `frontend/src/lib/webllm/prompts/fewShot.ts` to demonstrate `sourceExcerpt` present and absent cases
- [x] 3.3 Update `frontend/src/lib/webllm/parser.ts`: add `sourceExcerpt` to `CorrectionSuggestion` type and extract it in `parseModelOutput()` with fallback keys, mirroring the backend parser (plus matching jest tests in `parser.test.ts`)

## 4. Frontend types

- [x] 4.1 Add `sourceExcerpt?: string` to `SuggestionsResponse` in `frontend/src/app/api.ts`
- [x] 4.2 Add `sourceExcerpt?: string` to `CorrectionSuggestion` type in `frontend/src/app/page.tsx`

## 5. Design tokens

- [x] 5.1 Add `--suggestion-highlight` HSL CSS variable to `frontend/src/app/globals.css` `:root`
- [x] 5.2 Add `suggestion-highlight` Tailwind color mapping to `frontend/tailwind.config.js`
- [x] 5.3 Add a `.no-scrollbar` utility class to `frontend/src/app/globals.css` for the highlight overlay's programmatically-scrolled backdrop
- [x] 5.4 Document the new token (value, usage, opacity variants for hover vs. selected) in `docs/UI-DESIGN.md`'s color token table and AI Suggestion Card pattern section (plus `AGENTS.md`'s Response Schema section for the new field)

## 6. HighlightedTextarea component

- [x] 6.1 Create `frontend/src/components/ui/highlighted-textarea.tsx`: wrapper div, transparent-text/transparent-background textarea on top, backdrop div with duplicated text + `<mark>`-wrapped highlight spans behind
- [x] 6.2 Implement range computation: given `value` and a `highlights: {text, variant}[]` prop, find first-occurrence substring matches, resolve overlaps (hover takes priority over selected), and produce contiguous render segments
- [x] 6.3 Implement scroll sync (mirror `scrollTop`/`scrollLeft` from textarea to backdrop on the textarea's `onScroll`)
- [x] 6.4 Forward `ref`, and pass through all other native `<textarea>` props (`value`, `onChange`, `placeholder`, `className`, etc.) unchanged

## 7. Wire highlighting into the workspace UI

- [x] 7.1 Add `hoveredSuggestionId` state in `frontend/src/app/page.tsx`; wire `onMouseEnter`/`onMouseLeave` on each suggestion card
- [x] 7.2 Compute `targetHighlights` (from `suggestion.original`, for hovered/selected suggestions) and `sourceHighlights` (from `suggestion.sourceExcerpt`, filtered to non-empty, for hovered/selected suggestions) via `useMemo`
- [x] 7.3 Replace the SOURCE TEXT `<Textarea>` with `<HighlightedTextarea>` passing `sourceHighlights`
- [x] 7.4 Replace the TARGET TEXT `<Textarea>` with `<HighlightedTextarea>` passing `targetHighlights`
- [x] 7.5 Verify existing typing/caret/selection/onChange behavior is unaffected for both textareas (native `<textarea>` untouched functionally; only paint layer changed)

## 8. Verification

- [x] 8.1 Run backend pytest suite (full) — 102 passed, 28 skipped, no regressions
- [x] 8.2 Run `npm run lint` in `frontend/` — no new errors (one pre-existing unrelated warning in `layout.tsx`)
- [x] 8.3 Run `npm run build` in `frontend/` — build succeeds
- [x] 8.4 Local docker containers were running (`mjai-backend-1`, `mjai-frontend-1`); ran pytest/lint/build/jest directly inside them; also ran the full frontend jest suite (130 tests, 129 passed — the 1 failure is a pre-existing, unrelated stale-label assertion in `apiError.test.tsx`, verified via `git stash` to fail identically without this change's diff applied)

## 9. Finalize planning artifacts

- [x] 9.1 Mark all tasks above complete
- [x] 9.2 Run `openspec validate highlight-suggestion-text-spans --strict` and fix any reported issues
