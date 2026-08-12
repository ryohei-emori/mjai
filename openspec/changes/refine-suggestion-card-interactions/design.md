## Context

See `proposal.md` for motivation. Relevant existing code:

- `frontend/src/app/page.tsx` suggestion-card `.map()` (~lines 1994-2069): each card wraps a `<Checkbox>` (~2005-2009) plus a `selectedOrder` badge (~2010-2014) in a left column, an "Option X" label (~2018-2021), a hover-reveal copy/select icon pair (~2023-2046), a red "指摘箇所" block, and a "修正コメント" block that renders either a read-only `<p>` or, when selected, a `<Textarea className="... min-h-[60px] ...">` (~2056-2064).
- `toggleSuggestionSelection(suggestionId)` (~lines 1017-1053): the existing selection-toggle logic (assigns/reclaims `selectedOrder`, updates the selection counter). Already wired to both the checkbox's `onCheckedChange` and the hover icon button's `onClick`.
- `updateSuggestionReason(suggestionId, newReason)` (~lines 1055-1062): updates `userModifiedReason` on change.
- The suggestions-scroll `useEffect` (~lines 793-806): keyed on `[confirmingJobId, currentSession?.suggestions]`, scrolls `[data-suggestions-card]` into view via a 50ms-delayed `scrollIntoView` whenever either dependency's reference changes. Since `currentSession.suggestions` gets a new array reference from every `toggleSuggestionSelection`/`updateSuggestionReason` call (both go through `updateCurrentSession`), this effect re-fires and re-scrolls on every selection/edit, not just on initial suggestion load.
- `backend/app/llm/parser.py`'s `parse_model_output()` (~lines 194-283): loops over the raw `shiteki_list`, appending a `CorrectionSuggestion` with `id: str(i+1)` for every dict item regardless of whether `original`/`reason` are both empty.
- `backend/app/llm/suggestions.py`'s `generate_suggestions()` (~lines 148-194): a `for attempt in range(1, MAX_PARSE_RETRY_ATTEMPTS + 1)` loop that retries `_generate_suggestions_once()` while `is_json_extraction_failure(result)` is true, returning the last result if every attempt still fails.

## Goals / Non-Goals

**Goals:**
- Replace checkbox-driven selection with double-click-the-card selection while keeping the hover icon button as an equally valid, non-removed alternative.
- Make the selected-state comment textarea's rendered height content-driven (auto-resize), never shorter than the unselected `<p>`'s natural height for the same text.
- Make the suggestions-panel auto-scroll fire at most once per confirmation session (per distinct `confirmingJobId`), not on every suggestions-array mutation.
- Add a Chinese-language content check for `reason`/`overallComment` and wire it into the existing bounded retry loop, without changing the loop's overall attempt budget or its "degrade gracefully, don't raise" behavior on exhaustion.
- Drop blank suggestion items and keep `id` sequencing contiguous.

**Non-Goals:**
- Changing the `original`-field language behavior (it stays Japanese, unchecked by the new validation) — explicit constraint from the task.
- Removing the hover check_circle/radio_button_unchecked icon button — explicit constraint.
- Changing the overall `MAX_PARSE_RETRY_ATTEMPTS` value or the network-level (Groq rotation/Cloudflare failover) retry axis — the new language check only adds a second condition to the existing loop's retry predicate.
- Building a general-purpose CJK script classifier (e.g. distinguishing Traditional vs Simplified Chinese, or catching more subtle mixed-language cases). Hiragana/Katakana presence is a narrow, cheap, high-precision signal sufficient for this task; deeper NLP-based language detection is out of scope.
- Changing the "at least 5 suggestions" prompt guidance or any other prompt-content decision unrelated to the two issues above.

## Decisions

### 1. Double-click target: the whole card wrapper `<div>`, not a separate handler on the comment text

**Choice**: Attach a single `onDoubleClick={() => toggleSuggestionSelection(suggestion.id)}` to the card's outer wrapper `<div>` (~line 1995), rather than adding a second, narrower double-click handler scoped only to the "修正コメント" `<p>`/`<Textarea>`. Since the reason text is already contained within the card, a card-level handler satisfies both requirement 1 (double-click the card) and requirement 2 (double-click the comment) with one implementation — double-clicking the comment is a double-click on the card, by DOM nesting.

**Alternative considered**: Two separate `onDoubleClick` handlers (one on the card, a redundant one on the comment element). Rejected: functionally identical outcome, adds duplicate logic and a stopPropagation edge case to maintain for no behavioral benefit.

**Interaction with existing click handlers**: The hover icon button's `onClick` already calls `e.stopPropagation()` (~line 2026 for copy, 2036 for select) — this is preserved so a *single* click on either hover icon does not also register as part of a double-click sequence on the card. The `<Textarea>`'s own `onChange`/typing/click-to-focus interactions are unaffected since `onDoubleClick` only fires on an actual double-click gesture, not on ordinary single clicks used to focus the textarea for editing. The selected-state `<Textarea>` additionally gets its own `onDoubleClick={(e) => e.stopPropagation()}`: double-clicking inside an already-selected textarea is the standard browser gesture for selecting a word to edit, not an intent to deselect the card — without stopping propagation there, that word-select double-click would also bubble up and toggle the card back to unselected mid-edit, which would be surprising and would discard the in-progress editing view.

### 2. Selection-order badge's new location

**Choice**: Move the `{suggestion.selected && suggestion.selectedOrder && <Badge>...}` block (~2010-2014) to sit inline next to the "Option X" label (~2018-2021), e.g. `<span>Option {letter}</span> <Badge>{order}</Badge>`. This keeps the selection-order signal visible in the same header row users already look at for the option letter, rather than inventing a new location.

**Alternative considered**: Show the order number as a corner overlay badge on the card itself (absolute-positioned). Rejected: more layout complexity for no clear UX benefit over the simple inline placement next to the label, and inconsistent with the existing `text-label-caps` header row pattern.

### 3. Textarea auto-resize approach: ref + `scrollHeight` on mount and on change, no new dependency

**Choice**: Add a `ref` to the `<Textarea>`, and a small resize function (`el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'`) called both in a `useEffect` keyed on the visible value (so it re-sizes when a suggestion is selected, when suggestions are regenerated, or when a saved history entry is restored) and inline in the `onChange` handler (so it grows as the user types, before the next render/effect cycle). Remove the fixed `min-h-[60px]` Tailwind class so nothing overrides the computed height, keeping a small `min-h` (e.g. `min-h-[2.5rem]`, roughly one line) only as a floor for genuinely short comments, not as a value that can exceed and clip longer content.

**Alternative considered**: Use a third-party auto-resize textarea library (e.g. `react-textarea-autosize`). Rejected: this is a single, isolated textarea instance in one component; adding a new frontend dependency for one auto-resize behavior is disproportionate when the standard `scrollHeight` pattern is a well-known ~4-line solution requiring no new dependency, consistent with `AGENTS.md`'s general preference for minimal footprint changes.

### 4. Scroll-once-per-job via a ref, not a dependency-array change alone

**Choice**: Introduce `const lastScrolledJobIdRef = useRef<string | null>(null)`. Change the effect's dependency array from `[confirmingJobId, currentSession?.suggestions]` to `[confirmingJobId, currentSession?.suggestions?.length]`* guarded by an explicit check inside the body: only scroll when `confirmingJobId !== lastScrolledJobIdRef.current`, then immediately set `lastScrolledJobIdRef.current = confirmingJobId` before scrolling. Also reset/allow re-arming: when `confirmingJobId` becomes `null` (confirmation session ends), the ref naturally stops matching future non-null job ids, so the next confirmation is treated as new.

(*Per the task's explicit guidance, `currentSession?.suggestions` — the array reference — must not remain a re-trigger; using `.length` instead of the full array reference as a secondary dependency is a minor pragmatic addition so the effect still re-evaluates once suggestions initially populate for a job id that was already the `confirmingJobId` value at mount, without reintroducing a re-trigger on every subsequent in-place edit that doesn't change the array's length. The ref-based `lastScrolledJobIdRef` check is the actual gate that prevents re-scrolling, not the dependency array by itself.)

**Alternative considered**: Depend on `[confirmingJobs]` alone (no `.length`) and rely solely on the ref check. Rejected: if suggestions arrive asynchronously *after* `confirmingJobId` is already set (the common case — confirming a job triggers a fetch, and suggestions populate a moment later), an effect with only `[confirmingJobId]` as its dependency would have already run (and found `suggestions.length === 0`) before the data arrives, and would need the array-length change to re-run and pick up the newly-loaded suggestions. Depending on `.length` (which only changes when suggestions actually populate/change count, not on every selection toggle which doesn't change array length) preserves the "wait for suggestions to load" behavior without reintroducing the per-selection re-scroll bug, since toggling `selected`/editing `userModifiedReason` mutates existing array elements in place (via `.map()`) without changing `suggestions.length`.

### 5. Chinese-language detection: Hiragana/Katakana Unicode range check, not a full script classifier

**Choice**: `has_non_chinese_reason(result: ParsedResponse) -> bool` scans each suggestion's `reason` and the top-level `overallComment` for any codepoint in `U+3040–U+309F` (Hiragana) or `U+30A0–U+30FF` (Katakana), using a compiled regex (e.g. `re.search(r'[\u3040-\u30FF]', text)`). Returns `True` (meaning: retry) if any of these fields contains such a codepoint.

**Rationale**: Chinese (Simplified or Traditional) text never contains Hiragana or Katakana — these are Japanese-only syllabaries. Japanese text, by contrast, is almost never written using Hanzi/Kanji alone in natural, connective prose (particles, verb conjugations, etc. require Hiragana) — so the presence of Hiragana/Katakana in a `reason`/`overallComment` string is a highly reliable, cheap signal that the model wrote that field in Japanese rather than the required Chinese, without needing a language-detection library or model call.

**Alternative considered**: A statistical/library-based language detector (e.g. `langdetect`, `fasttext` language ID). Rejected: adds a new backend dependency and non-trivial latency/accuracy overhead (short strings are exactly langdetect's known weak case) to solve a problem that has a deterministic, zero-dependency answer for this specific Japanese-vs-Chinese distinction. If future requirements need finer-grained script classification (e.g. Simplified vs Traditional Chinese), that would warrant revisiting this choice.

**Alternative considered**: Check for the *absence* of Chinese-specific Hanzi variants instead of presence of Hiragana/Katakana. Rejected: many Hanzi are shared identically between Chinese and Japanese (Kanji), so "not exclusively Chinese-looking Hanzi" is a much noisier, higher-false-positive signal than the clean Hiragana/Katakana presence check.

### 6. Retry composition: extend the existing loop's predicate, not a second loop

**Choice**: In `generate_suggestions()`, change the loop's continue-retrying condition from `is_json_extraction_failure(result)` to `is_json_extraction_failure(result) or has_non_chinese_reason(result)`, keeping everything else (the `for attempt in range(1, MAX_PARSE_RETRY_ATTEMPTS + 1)` loop, `last_result` tracking, and the final "return last result, don't raise" fallback) unchanged. This means a language-check failure and a JSON-parse failure draw from the exact same shared attempt budget, exactly as `proposal.md`/spec requires ("composing with, not replacing").

**Alternative considered**: A separate, independent retry loop specifically for the language check, nested inside or after the existing parse-failure loop (e.g. up to `MAX_PARSE_RETRY_ATTEMPTS` parse-retries, each of which could itself retry up to `MAX_PARSE_RETRY_ATTEMPTS` more times for language). Rejected: multiplies worst-case latency (already documented in `suggestions.py`'s module docstring as up to 9 LLM calls for the existing single axis) without a clear benefit, and contradicts the task's explicit instruction to compose with, not add a second independent budget alongside, the existing retry count.

### 7. Blank-item filtering: skip when *both* fields are blank, not *either*

**Choice**: Skip an item only when both `original.strip()` and `reason.strip()` are empty. An item with a non-empty `original` but empty `reason` (or vice versa) is still likely a genuine (if incomplete) suggestion the model intended, not a spurious blank filler — the observed bug (per the task description) is specifically "one extra item that ends up blank" (both fields empty), not partially-filled items.

**Alternative considered**: Skip when *either* field is blank. Rejected: this is stricter than what the observed bug requires and risks dropping legitimate suggestions where, e.g., the model provides `original` but a still-being-generated `reason` gets cut off empty by a parse edge case elsewhere — better handled by the existing truncation-repair logic in `extract_json`/`repair_truncated_json`, not by this filter silently discarding otherwise-valid data.

## Risks / Trade-offs

**[Risk] Double-click may be less discoverable than a visible checkbox for some users** → Mitigation: the hover-reveal check_circle/radio_button_unchecked icon button remains as an explicit, visually-discoverable single-click alternative; double-click is an additive convenience, not the only path to selection.

**[Risk] `scrollHeight`-based auto-resize can misbehave inside certain flex/grid layouts or when the textarea is initially hidden (`display: none`) at mount** → Mitigation: the textarea only exists in the DOM when `suggestion.selected` is true (conditional render, not CSS-hidden), so `scrollHeight` is always measured against a visible, laid-out element when the resize effect runs.

**[Risk] Using `.length` as a secondary effect dependency could theoretically still miss a case where suggestions are replaced with a same-length-but-different-content array for the same `confirmingJobId` (e.g. regeneration while still confirming)** → Mitigation: regeneration while a job-queue confirmation is in progress is not a supported/expected flow in the current UI (confirmation is a terminal review step, not a re-generation trigger); if this changes in the future, the ref-based guard can be revisited alongside that new flow.

**[Risk] The Hiragana/Katakana check could produce a false positive if a `reason` legitimately quotes a Japanese word/phrase inside otherwise-Chinese explanatory text (e.g. `「である」という表現は…`)** → Accepted trade-off: per the task's explicit heuristic, this is treated as "reason is not clean Chinese" and triggers a retry; this errs toward stricter Chinese-only enforcement, consistent with the underlying prompt rule ("重合コメント" must be Chinese), and a retry is cheap relative to serving a genuinely mixed-language response. If this proves too aggressive in practice (e.g. quoting Japanese terms is common and desirable), a follow-up could scope the check to "primarily Hiragana/Katakana" via a density threshold rather than any-occurrence — deferred since no evidence of this false-positive pattern exists yet.

## Migration Plan

No data migration. Both the frontend and backend changes are behavior-only fixes to an existing feature; no schema, API contract, or environment-variable changes. Ships as a normal deploy. No feature flag needed.
