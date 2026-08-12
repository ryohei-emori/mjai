## Context

`CorrectionSuggestion.original` is an excerpt from TARGET TEXT (despite its name) and is currently only shown in an isolated red box, never located within the actual textarea. The user wants (1) that excerpt highlighted in-place in the TARGET TEXT textarea, (2) the corresponding SOURCE TEXT excerpt highlighted too — which requires a new LLM-provided field since SOURCE and TARGET are different content and cannot be cross-referenced by substring matching alone — and (3) graceful omission when no SOURCE TEXT correspondence exists.

Both `originalText` (SOURCE TEXT) and `targetText` (TARGET TEXT) are Japanese in this app's actual usage (see `backend/app/llm/prompts.py` module docstring) — `originalText` acts as a "reference"/expected-correct text and `targetText` is the user's draft containing errors; suggestions flag issues in the draft. This is not a cross-language translation pair, which simplifies the new field's language rule (same rule as `original`: stays Japanese, never translated).

## Goals / Non-Goals

**Goals:**
- Add a new optional per-suggestion field carrying the SOURCE TEXT correspondence, extracted with the same robustness conventions as existing fields.
- Highlight matched spans in-place in both textareas without breaking native editing.
- Use an MD3-pattern design token for the highlight color, documented alongside existing tokens.
- Keep the change additive and reversible: no schema-breaking changes, no DB migration, no changes to unrelated fields' language rules.

**Non-Goals:**
- Fuzzy/approximate substring matching (e.g. Levenshtein-distance matching for near-verbatim excerpts). First-occurrence exact substring match only; if the model's excerpt isn't verbatim enough to match, no highlight for that side (acceptable degradation per requirement 3's "graceful, no error" mandate).
- Persisting `sourceExcerpt` through the save/proposals flow (see Decision 4).
- Multi-occurrence highlighting (highlighting every occurrence of a repeated snippet) — only the first occurrence is highlighted, consistent with how `original`-in-target matching would already be ambiguous for repeated snippets, and keeping the range-resolution logic simple.

## Decisions

### Decision 1: New field name — `sourceExcerpt`

**Choice:** Add `sourceExcerpt: string` (optional/omittable, empty-string default) to the suggestion schema.

**Rationale:** Matches the existing naming convention (`original`, `reason`) — a plain, descriptive noun in the field's own semantic terms rather than a q generic name like `sourceMatch` or `sourceRef`. "Excerpt" mirrors how `original` is documented ("該当箇所の抜粋" / "excerpt of the relevant part") applied to the SOURCE side instead of TARGET. Chosen over alternatives like `sourceOriginal` (confusing double use of "original") or `correspondingSource` (verbose).

### Decision 2: Highlight trigger — hover preview + selected persistence (both, differentiated)

**Choice:** Support both triggers simultaneously: hovering a suggestion card shows a transient, lighter-toned preview highlight; a selected suggestion shows a persistent, stronger-toned highlight independent of hover. When a suggestion is both hovered and selected, hover styling wins (it's the more "active" intent signal).

**Rationale:** This matches the existing card affordances already in the codebase — the suggestion card already has `hover:bg-surface-container` (unselected) and `bg-primary-container` (selected, persistent) states, so extending the same "hover = transient preview, selected = persistent" mental model to the textarea highlight keeps the two surfaces (card list and textarea) conceptually consistent. A hover-only design would lose the ability to compare multiple selected suggestions' locations at once (a core review-tool use case per the user's framing); a selected-only design would remove the low-commitment "let me check where this is" preview interaction. Supporting both, with a clear visual precedence rule for the overlap case, is more useful without meaningfully increasing implementation risk (both are just entries in the same highlight-ranges array passed to the overlay).

**Alternatives considered:**
- Hover-only: simpler, but loses persistent multi-suggestion comparison.
- Selected-only: loses the cheap "preview without committing to a selection" interaction; also suggestions need at least one selected to see anything, which doesn't help while still deciding what to select.

### Decision 3: Color token — new `--suggestion-highlight` (not reusing `--error`)

**Choice:** Add a new MD3-pattern token, `--suggestion-highlight` (HSL, amber/warning-toned: `38 92% 50%`), to `globals.css`, wired through `tailwind.config.js` as `bg-suggestion-highlight` / `border-suggestion-highlight`, and documented in `docs/UI-DESIGN.md`. Applied at two opacities via Tailwind's opacity modifier (already used elsewhere in this codebase, e.g. `bg-primary-container/50`): `bg-suggestion-highlight/25` for hover-preview, `bg-suggestion-highlight/45` with a `border-b-2 border-suggestion-highlight` underline for selected-persistent.

**Rationale:** `--error` (red, `0 84% 60%`) is already used elsewhere for destructive actions, failed-job retry buttons, and (as a plain Tailwind `red-*` shade, not the token) the existing "指摘箇所" box — reusing it for an in-text highlight risks visually conflating "this text is an error/failure state" with "this text is being reviewed," and the user's own request flagged this ambiguity. `--md3-primary` (blue) is already the "selected card" background and would visually clash/blend with the card's own selected state when also used for the textarea highlight. `--tertiary` (purple) had no established semantic tie-in. An amber/warning tone is a distinct, conventionally "flag for attention" hue (common in editor "found match" / "review" highlighting, e.g. find-in-page browser highlights) that doesn't collide with any existing semantic token's meaning in this app.

**Alternatives considered:**
- Reuse `--error`: rejected per above (semantic collision with destructive/failure meaning).
- Reuse `--md3-primary`/`--primary-container`: rejected — already means "selected card," would be visually redundant/confusing when the card is selected AND the text is highlighted with the same hue.
- Two separate tokens for hover vs. selected: unnecessary — a single hue with two opacity levels (matching the existing `bg-primary-container/50` opacity-modifier pattern already used in this file) is simpler and still visually distinguishable.

### Decision 4: No persistence of `sourceExcerpt`

**Choice:** `sourceExcerpt` is not added to `POST /proposals`'s payload, `backend/app/db_helper.py`'s `insert_proposal`, or the `ai_proposals` table schema.

**Rationale:** Per the user's own stated default and scope framing: it is a transient generation-time highlighting aid, not saved correction data. The saved proposal record's purpose is to capture the user's final selected/edited correction (`originalAfterText`, `modifiedAfterText`/`modifiedReason`), not the ephemeral cross-referencing data used to render a highlight during review. Adding a column would require a migration for a field with no read path after the review session ends (once saved, the user is looking at history/proposals, not re-highlighting live textareas). If a future need arises (e.g. showing the same highlight when reviewing saved history), it can be added then with a clear consumer in hand.

### Decision 5: Highlight overlay implementation — `HighlightedTextarea` (backdrop-div pattern)

**Choice:** New component `frontend/src/components/ui/highlighted-textarea.tsx` implementing the standard "highlighted textarea" technique:
- A wrapper `<div className="relative">` contains two stacked children of identical box size (via `absolute inset-0` on the overlay, matching the textarea's normal-flow size).
- The real `<textarea>` sits on top (`relative z-10`), with `bg-transparent`, `text-transparent`, and an explicit `caret-[hsl(var(--on-surface))]` so the caret stays visible. It receives all pointer/keyboard events normally — nothing about focus, typing, IME composition, native selection, or `onChange` changes.
- The overlay `<div aria-hidden>` sits behind (`absolute inset-0 z-0`), sharing the *exact same* className list (font size/weight, line-height, padding, border, `whitespace-pre-wrap break-words`) as the textarea so glyph positions line up, but rendering the real visible text (`text-on-surface` for plain runs) plus `<mark>`-wrapped highlighted runs. It owns the visible background/border (`bg-surface-container border-outline-variant`) that the textarea's own background no longer shows.
- Scroll sync: the textarea's `onScroll` handler imperatively sets `overlayRef.current.scrollTop/scrollLeft` to match (no React state round-trip needed) — the overlay uses `overflow-auto` plus a `no-scrollbar` utility class (new, minimal addition to `globals.css`) so it can be scrolled programmatically without showing its own scrollbar or intercepting user scroll input (it also has `pointer-events-none`, so user-initiated wheel/touch scroll passes through to... actually lands on the textarea underneath, which is the interactive layer; the overlay is kept in sync purely via the mirrored `scrollTop`/`scrollLeft` assignment triggered by the textarea's own scroll event).
- Because the overlay is `position: absolute; inset: 0` inside a `position: relative` wrapper whose height is determined by the in-flow textarea, manual textarea resizing (if enabled) or content-driven height changes are automatically picked up by the browser's layout engine with no `ResizeObserver` needed.

**Rationale:** This is the standard, widely-used technique for highlighting substrings inside a native `<textarea>` (native textareas cannot style inline substrings) — used by tools like `react-simple-code-editor` and various "highlight-within-textarea" implementations. It fully preserves native editing behavior (the real `<textarea>` is untouched functionally, only its own text/background paint is made transparent) while keeping implementation cost low (no virtual caret/selection reimplementation, no keystroke interception).

**Trade-off accepted:** The overlay must duplicate the full text content (not just highlighted spans) so that normal (non-highlighted) text remains visible at all times — this is inherent to the technique, not optional. This roughly doubles the DOM text nodes for these two textareas, which is a negligible cost for typical correction-exercise-length text.

**Range resolution for overlaps:** highlight ranges are computed as `{start, end, variant: "hover" | "selected"}` per matched suggestion, sorted, and reduced to a per-character variant array (hover overwrites selected on overlap, per Decision 2) before being grouped back into contiguous rendered segments. This keeps rendering robust (no broken nesting) regardless of how many suggestions are simultaneously active.

### Decision 6: WebLLM parser parity (`frontend/src/lib/webllm/parser.ts`)

**Choice:** In addition to the explicitly-requested prompt mirroring (`system.ts`, `fewShot.ts`), also extend `frontend/src/lib/webllm/parser.ts`'s extraction logic to read `sourceExcerpt` (mirroring the backend parser's key-fallback approach), so the field flows end-to-end for offline/WebLLM-generated suggestions too, not just cloud-API ones.

**Rationale:** Without this, a user in オフラインモード would have the WebLLM prompt asking the model for `sourceExcerpt`, but the value would be silently dropped by the parser — a confusing, easy-to-miss half-implementation. The change is a small, low-risk mirror of the existing `original`/`reason` extraction pattern, keeping the two code paths' capabilities in sync as the repo's established convention already dictates for prompts.

## Risks / Trade-offs

**[Risk] Model-provided `sourceExcerpt` is not a verbatim substring of `originalText`** → No highlight shown for that suggestion's SOURCE side (graceful no-op, per requirement 3's explicit "don't force it" framing); the TARGET TEXT highlight for the same suggestion is unaffected since matching is independent per side.

**[Risk] First-occurrence-only matching picks the "wrong" occurrence for a repeated snippet** → Accepted as a known limitation (Non-Goal); consistent with how the existing "指摘箇所" box already can't disambiguate repeated snippets either.

**[Trade-off] Overlay duplicates full textarea text in the DOM** → Negligible for this app's text lengths (short correction exercises, not long documents); revisit only if a future use case introduces much longer texts.

## Migration Plan

1. Backend: extend prompt + parser + tests (independently testable, no frontend dependency).
2. WebLLM: mirror prompt + parser for offline parity.
3. Frontend types: thread `sourceExcerpt` through `SuggestionsResponse` and `CorrectionSuggestion` (mostly automatic via existing `{...s, selected: false}` spreads).
4. Design tokens: add `--suggestion-highlight` to `globals.css` + `tailwind.config.js`, document in `docs/UI-DESIGN.md`.
5. Build `HighlightedTextarea` component in isolation.
6. Wire into SOURCE/TARGET `<Card>`s in `page.tsx`, add hover-state tracking for suggestion cards, compute highlight range arrays via `useMemo`.
7. Verify: backend pytest, frontend lint + build.

**Rollback:** All changes are additive (new optional field, new component, new token). Reverting is a straightforward revert of the diff with no data migration to undo.

## Open Questions

None — all decisions above are resolved for this iteration.
