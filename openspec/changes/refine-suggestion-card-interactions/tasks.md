## 1. Frontend: remove checkbox, add double-click-to-select

- [x] 1.1 Remove the `<Checkbox>` element from the suggestion-card `.map()` in `frontend/src/app/page.tsx` (~lines 2005-2009)
- [x] 1.2 Add `onDoubleClick={() => toggleSuggestionSelection(suggestion.id)}` to the card's outer wrapper `<div>` (~line 1995)
- [x] 1.3 Move the `selectedOrder` `<Badge>` (~lines 2010-2014) to render inline next to the "Option X" label (~lines 2018-2021) instead of under the removed checkbox
- [x] 1.4 Verify the hover-reveal check_circle/radio_button_unchecked icon button (~lines 2034-2045) is unchanged and its `e.stopPropagation()` still prevents a single click there from being consumed as part of a double-click on the card
- [x] 1.5 Verify clicking into the textarea to place a cursor/select text for editing (single click) does not interfere with the new double-click handler

## 2. Frontend: auto-resize the selected-state comment textarea

- [x] 2.1 Add a `ref` (e.g. a `Map<string, HTMLTextAreaElement>` keyed by suggestion id, or a per-item callback ref pattern) so each suggestion's textarea can be measured/resized independently
- [x] 2.2 Implement a resize helper that sets `el.style.height = 'auto'` then `el.style.height = el.scrollHeight + 'px'`
- [x] 2.3 Call the resize helper on mount/whenever the displayed value changes (selection, regeneration, restore-from-history) via `useEffect`, and inline within the `onChange` handler so it grows while typing
- [x] 2.4 Replace the fixed `min-h-[60px]` Tailwind class with a small floor (e.g. `min-h-[2.5rem]`) that cannot exceed/clip genuinely short content, and remove any class that would otherwise conflict with the inline `style.height`
- [x] 2.5 Manually verify (or via a short component-level check) that selecting a proposal with a long, multi-line comment renders a textarea at least as tall as the comment's pre-selection `<p>` height

## 3. Frontend: fix suggestions-panel scroll-on-every-selection bug

- [x] 3.1 Add `const lastScrolledJobIdRef = useRef<string | null>(null)` near the `confirmingJobId` state declaration in `frontend/src/app/page.tsx`
- [x] 3.2 Change the scroll `useEffect`'s dependency array from `[confirmingJobId, currentSession?.suggestions]` to `[confirmingJobId, currentSession?.suggestions?.length]`
- [x] 3.3 Inside the effect body, only proceed to scroll when `confirmingJobId && confirmingJobId !== lastScrolledJobIdRef.current && currentSession?.suggestions && currentSession.suggestions.length > 0`, and set `lastScrolledJobIdRef.current = confirmingJobId` before/at the point of scrolling
- [x] 3.4 Verify selecting/deselecting/editing any option (including a lower one like "Option E") after the initial scroll does not re-trigger `scrollIntoView`
- [x] 3.5 Verify confirming a *different* job afterward still scrolls once for that new job (the ref must not permanently latch)

## 4. Backend: Chinese-language validation + retry

- [x] 4.1 Add `has_non_chinese_reason(result: ParsedResponse) -> bool` to `backend/app/llm/parser.py`, checking each suggestion's `reason` and `result["overallComment"]` for any Hiragana (`\u3040-\u309F`) or Katakana (`\u30A0-\u30FF`) codepoint via a compiled regex; explicitly do NOT check `original`
- [x] 4.2 Export/import `has_non_chinese_reason` in `backend/app/llm/suggestions.py`
- [x] 4.3 Extend `generate_suggestions()`'s retry loop condition from `is_json_extraction_failure(result)` to `is_json_extraction_failure(result) or has_non_chinese_reason(result)`, keeping `MAX_PARSE_RETRY_ATTEMPTS`, `last_result` tracking, and the no-raise-on-exhaustion fallback unchanged
- [x] 4.4 Update the module docstrings in `parser.py`/`suggestions.py` to describe the new composed retry condition

## 5. Backend: filter blank suggestion items

- [x] 5.1 In `parse_model_output()`'s suggestion loop (`backend/app/llm/parser.py`, ~lines 246-272), skip appending an item when both `original.strip()` and `reason.strip()` are empty
- [x] 5.2 Re-sequence `id` using a separate counter (`len(suggestions) + 1`) incremented only for appended items, so ids stay contiguous after filtering
- [x] 5.3 Verify the diagnostic logging (`logger.warning` for "items found but no valid suggestions extracted") still makes sense given the new filtering behavior

## 6. Backend tests

- [x] 6.1 Add tests in `backend/tests/test_llm_parser.py` for `has_non_chinese_reason()`: detects Hiragana in a `reason`, detects Katakana in `overallComment`, returns `False` for pure-Chinese content, ignores Hiragana/Katakana present only in `original`
- [x] 6.2 Add tests in `backend/tests/test_llm_parser.py` for blank-item filtering in `parse_model_output()`: a fully-blank item (both fields empty/whitespace) is dropped; ids remain contiguous (`"1"`, `"2"`) when a blank item occurred between two valid items; an item with only one blank field is still retained
- [x] 6.3 Add tests in `backend/tests/test_llm_suggestions.py` mirroring the existing `TestGenerateSuggestionsParseFailureRetry` class: a non-Chinese `reason` on early attempts followed by a valid Chinese response succeeding within the retry budget; giving up after `MAX_PARSE_RETRY_ATTEMPTS` attempts all failing the language check, returning the last result without raising
- [x] 6.4 Run `cd backend && python3 -m pytest` and confirm all tests pass, noting any pre-existing unrelated failures separately (see notes: local run required a throwaway venv since no venv/pytest was pre-installed in this environment; also updated two pre-existing tests, `test_handles_missing_fields`/`test_missing_content_fields`, and the shared `VALID_LLM_RESPONSE` fixture, whose old expectations directly contradicted this change's new blank-filtering/Chinese-language behavior — see proposal/design for rationale)

## 7. Frontend verification

- [x] 7.1 Run `npm run lint` in `frontend/` and confirm no new errors introduced (note any pre-existing ones separately) — only pre-existing `layout.tsx` custom-font warning remains; added one `eslint-disable-next-line react-hooks/exhaustive-deps` for the intentional scroll-effect dependency deviation (Task 3)
- [x] 7.2 Run `npm run build` in `frontend/` and confirm no new errors introduced (note any pre-existing ones separately) — build succeeds with the same pre-existing warning only

## 8. Planning artifacts

- [x] 8.1 Mark all tasks above complete as implemented
- [x] 8.2 Run `openspec validate --strict` (or repo-equivalent) on this change and fix any reported issues

## 9. Post-merge note (2026-08-13): investigated as a possible cause of the "custom card disappears" bug, ruled out

- [x] 9.1 A later bug report ("user-added custom suggestion card disappears") was investigated against this change's double-click-select/blank-filtering/Chinese-validation work as a possible regression source, since it touched the same suggestion-card render path. Ruled out: none of this change's diffs mutate or filter `currentSession.suggestions` in a way that would drop an `isCustom` entry. The actual root cause (`confirmJob()` in `frontend/src/app/page.tsx` wholesale-replacing `currentSession.suggestions` with a job's AI-only suggestion list) predates this change and was unrelated to it. See `openspec/changes/highlight-suggestion-text-spans/design.md`'s "Post-merge Follow-up" section (Bug 2) and `tasks.md` task 10.2 for the actual root cause and fix, documented there since that's where the sibling bugs from the same user report (highlight overlay layout bug, TARGET-selection feature) were also written up.
