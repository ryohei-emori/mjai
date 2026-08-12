## Why

Each AI correction suggestion (`CorrectionSuggestion`) carries an `original` field that is an excerpt from the TARGET TEXT (the flagged/erroneous Japanese snippet), despite its misleading field name. Today this excerpt is only shown in a small isolated "指摘箇所" box in the AI Suggestions panel — the user has no visual way to locate that snippet *inside* the actual TARGET TEXT textarea, and no way at all to see where the corresponding correct usage appears in SOURCE TEXT. For a text-correction workflow, seeing the flagged span in-place (and its SOURCE TEXT counterpart, when one exists) is core reviewing UX that the current isolated-box presentation doesn't provide.

## What Changes

- **New optional suggestion field `sourceExcerpt`**: the backend LLM schema (`backend/app/llm/prompts.py`, `backend/app/llm/parser.py`) and the WebLLM offline schema (`frontend/src/lib/webllm/prompts/system.ts`, `fewShot.ts`, `frontend/src/lib/webllm/parser.ts`) gain a new per-suggestion field holding a verbatim-or-close excerpt from SOURCE TEXT (原文) corresponding to the flagged TARGET TEXT snippet. The model is instructed to omit it or leave it as `""` when no clear SOURCE TEXT correspondence exists (e.g. a purely local grammar/style issue) — it is never fabricated to force a value.
- **In-place textarea highlighting**: a new reusable `HighlightedTextarea` component renders a highlight overlay behind the native SOURCE TEXT and TARGET TEXT `<textarea>` elements, showing the matched substring for `suggestion.original` (in TARGET TEXT) and `suggestion.sourceExcerpt` (in SOURCE TEXT, only when present and found) using a new `--suggestion-highlight` MD3-pattern color token. The overlay is purely visual (`pointer-events: none`) and does not alter existing typing/caret/selection/onChange behavior.
- **Highlight trigger**: hovering an AI Suggestion card previews its highlight (lighter tone); a selected suggestion's highlight persists (stronger tone) independent of hover. Both can be active simultaneously across multiple suggestions without visually colliding (overlapping ranges resolve deterministically, hover taking priority).
- **Graceful no-match handling**: if `suggestion.original` isn't found in `targetText`, or `sourceExcerpt` is empty/not found in `originalText`, that side simply shows no highlight — never an error.
- **Design docs updated**: `docs/UI-DESIGN.md` gains the new `--suggestion-highlight` token (and its two opacity variants for hover vs. selected) in the color token table and the AI Suggestion Card pattern section; `frontend/tailwind.config.js` and `frontend/src/app/globals.css` add the corresponding CSS variable/Tailwind class, following the existing `session-active`/`session-complete` token-extension precedent.
- **No persistence**: `sourceExcerpt` is a transient generation-time aid, not persisted through `POST /proposals` / `ai_proposals` table — see design.md for rationale.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `ai-suggestions`: gains a new requirement that generated suggestions may include an optional `sourceExcerpt` field (excerpt from SOURCE TEXT corresponding to the flagged TARGET TEXT snippet), omitted/empty when no clear correspondence exists, extracted by the parser with the same multi-key-fallback pattern used for `original`/`reason`.
- `correction-workspace-ui`: gains new requirements that (1) the TARGET TEXT textarea highlights the on-hover/selected suggestion's flagged excerpt in place, (2) the SOURCE TEXT textarea highlights the corresponding `sourceExcerpt` in place when present and found, and (3) highlighting degrades gracefully (no highlight, no error) when a match can't be found or the field is absent.

## Impact

- **Backend**: `backend/app/llm/prompts.py` (SYSTEM_PROMPT + few-shot example), `backend/app/llm/parser.py` (`CorrectionSuggestion` TypedDict + extraction), `backend/tests/test_llm_parser.py` (new field-extraction tests). No changes to `backend/app/main.py`, `backend/app/db_helper.py`, or any DB migration (explicitly out of scope this iteration).
- **Frontend types**: `frontend/src/app/api.ts` (`SuggestionsResponse`), `frontend/src/app/page.tsx` (`CorrectionSuggestion` type), `frontend/src/lib/webllm/parser.ts` (`CorrectionSuggestion` type + extraction), `frontend/src/lib/webllm/prompts/system.ts` + `fewShot.ts`.
- **Frontend UI**: new `frontend/src/components/ui/highlighted-textarea.tsx` component; `frontend/src/app/page.tsx` wires it into the SOURCE TEXT and TARGET TEXT `<Card>`s and adds hover-state tracking for suggestion cards.
- **Design system**: `frontend/src/app/globals.css`, `frontend/tailwind.config.js`, `docs/UI-DESIGN.md` (new `--suggestion-highlight` token).
- **No API contract breakage**: `sourceExcerpt` is additive/optional on the existing `POST /suggestions` response shape; existing consumers ignoring the field are unaffected.
- **No database schema changes.**
