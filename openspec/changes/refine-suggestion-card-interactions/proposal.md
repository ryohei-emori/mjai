## Why

The AI-suggestion "Option A/B/C..." cards in `frontend/src/app/page.tsx` have accumulated several rough edges reported directly by the user: the per-card checkbox is redundant now that a hover-reveal select toggle already exists and adds visual clutter; the selected-state comment textarea visually *shrinks* relative to its own unselected `<p>` height for long comments because it uses a fixed `min-h-[60px]`; selecting a lower-listed option (e.g. Option E) triggers an unwanted scroll-to-top of the AI SUGGESTIONS card; and on the backend, `backend/app/llm/parser.py`/`suggestions.py` occasionally emit a `reason`/`overallComment` in Japanese instead of the required Simplified Chinese (per `backend/app/llm/prompts.py`'s language-split rule), and occasionally emit one extra blank suggestion item that renders as an empty "Option" card. None of these are new features — they are targeted interaction, layout, and generation-quality fixes to an existing, working feature.

## What Changes

- **Remove the per-card `<Checkbox>`** from each suggestion card (`frontend/src/app/page.tsx`, inside the suggestion `.map()`). Double-clicking anywhere on the card (including the "修正コメント" text) now toggles that option's selected state, via a single `onDoubleClick` handler on the card's outer wrapper `<div>`. The existing hover-reveal check_circle/radio_button_unchecked icon button remains as the single-click alternative selection control — it is not removed.
- **Relocate the `selectedOrder` badge** that used to sit under the checkbox to next to the "Option X" label, since the checkbox column that hosted it is going away.
- **Fix the selected-state comment textarea's height** so it auto-sizes to its content (`scrollHeight`-driven, on mount and on every edit) instead of using a fixed `min-h-[60px]`, so it never renders shorter than the pre-selection `<p>`'s natural height for the same text.
- **Stop the AI SUGGESTIONS card from auto-scrolling on every selection change.** The scroll-into-view effect currently re-fires on every `currentSession.suggestions` array mutation (which happens on every select/deselect/edit); it will instead scroll at most once per confirmation session, exactly when suggestions for a given `confirmingJobId` first become available.
- **Add a Chinese-language validation+retry layer** for generated suggestions: a new `has_non_chinese_reason()` check in `backend/app/llm/parser.py` detects Hiragana/Katakana codepoints (a reliable "this is Japanese, not Chinese" signal) in any suggestion's `reason` or in `overallComment`, and `backend/app/llm/suggestions.py`'s existing bounded retry loop (`MAX_PARSE_RETRY_ATTEMPTS`) is extended to also retry on this condition, composing with (not replacing) the existing JSON-parse-failure retry. `original` stays unaffected and unchecked — it is required to remain Japanese.
- **Filter out blank suggestion items** in `parse_model_output()`: an item whose `original` and `reason` are both empty/whitespace-only after `.strip()` is dropped instead of appended, and remaining items are re-sequenced with contiguous `id`s (`"1"`, `"2"`, ...) so the frontend's index-derived `Option {A,B,C...}` lettering has no gap.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: "Proposal Selection and Ordering" changes from checkbox-driven selection to double-click-the-card (plus the existing hover icon button) selection, with the selection-order badge moving next to the option label; "Proposal Comment Editing" gains an explicit auto-resize requirement for the editable textarea so it never renders shorter than the read-only view; a new requirement covers the AI-suggestions panel scrolling into view at most once per confirmation session rather than on every selection change.
- `ai-suggestions`: gains a new requirement that generated suggestions are validated for Simplified-Chinese `reason`/`overallComment` content and retried (composing with the existing JSON-parse-failure retry, same attempt budget) when Japanese-only script is detected; and a new requirement that blank/empty suggestion items are filtered out of the parsed result rather than surfaced as empty cards.

## Impact

- **Frontend code**: `frontend/src/app/page.tsx` only — the suggestion-card `.map()` block (checkbox removal, double-click handler, badge relocation), the comment `<Textarea>` (auto-resize), and the suggestions-scroll `useEffect` (scroll-once-per-job fix via a new ref).
- **Backend code**: `backend/app/llm/parser.py` (new `has_non_chinese_reason()` function, blank-item filtering + id re-sequencing in `parse_model_output()`) and `backend/app/llm/suggestions.py` (retry loop extended to also check `has_non_chinese_reason()`).
- **No API contract changes**: `POST /suggestions`'s request/response shape is unchanged; only the content-quality of `reason`/`overallComment`/the suggestion list improves.
- **No database schema changes.**
- **Tests**: new unit tests in `backend/tests/test_llm_parser.py` (Hiragana/Katakana detection, pure-Chinese negative case, blank-item filtering + id re-sequencing) and `backend/tests/test_llm_suggestions.py` (retry-on-non-Chinese-reason behavior, composing with the existing parse-failure retry).
