## Context

The right pane stacks three panels: Job Queue (horizontal carousel), AI Suggestions, and History. Job Queue cards and the TopAppBar bell entries each preview a round with an inlined `job.targetText.slice(0, 40)` plus a manual `'...'` suffix — the same expression written twice. History cards have no preview at all; their heading is `添削データ #{index + 1}`.

The user's report is specifically about the History panel: the font weight is fine, but `添削データ #1` / `#2` gives no way to tell which round is which, while the queue cards do. So the fix is not "add a preview to History" in isolation — it is "make History use the queue's flavour of preview", which first requires the queue's flavour to exist somewhere both can call.

There is a precedent in this repo for exactly that move: `slide-job-queue-carousel` pulled the queue's ordering out of `page.tsx` into the pure module `frontend/src/lib/jobQueue/ordering.ts` so the bell list could not drift from the queue. This change applies the same pattern to labelling.

Constraints:
- `page.tsx` is a ~3000-line `"use client"` component that pulls in WebLLM and Supabase; anything unit-testable has to live outside it.
- No new design tokens (`docs/UI-DESIGN.md` is the authority).
- The History card layout must not fight the concurrently-landed floating session pane / collapsible panels work: the change stays inside the History card's own flex row.

## Goals / Non-Goals

Goals:
- A History card heading that identifies its round from its content.
- One derivation rule, unit-tested, shared by History cards, Job Queue cards, and bell entries.
- Handle a title-like leading line, long prose, multi-line text, blank text, and mixed JP/CN scripts without layout damage.

Non-Goals:
- No change to what gets persisted (`SavedData` gains no field; nothing new is sent to the API).
- No change to ordering, restore, confirm, archive, retry, or job execution.
- No search/filter over History (a different feature; identifiable headings are the prerequisite, not the substitute).
- No font-weight change anywhere — the user explicitly approved the current weight.

## Decisions

### Decision 1: Derive the label in a pure module, not in `page.tsx`

`frontend/src/lib/correctionLabel.ts` exports `deriveCorrectionLabel(source)` and the `EMPTY_CORRECTION_LABEL` placeholder. Like `jobQueue/ordering.ts`, it takes a **structural** input type rather than importing `QueuedJob` / `SavedData` (neither is exported, and both belong to the client page). `QueuedJob` and `SavedData` both already carry `targetText` and `originalText`, so both satisfy the structural type with no adapter at the call sites.

The function returns `{ text, kind }` rather than a bare string. `kind` (`'title' | 'excerpt' | 'empty'`) makes the tests assert *why* a label came out the way it did — a test that only checks `text` cannot distinguish "the title-line branch fired" from "the excerpt branch happened to cut at the same place" — and leaves the door open for a future surface that wants to style a real title differently. Callers that do not care read `.text`.

**Alternative rejected:** putting the helper under `frontend/src/lib/jobQueue/`. Labelling is no longer queue-specific once History uses it, and importing from a `jobQueue/` path inside the History panel would misdescribe ownership.

### Decision 2: Prefer a title-like first line, else excerpt the collapsed text

```
lines    = text split on newlines, blanks dropped
first    = lines[0] with internal whitespace collapsed
title-like  ⇔  lines.length > 1
               ∧ charCount(first) ≤ 30
               ∧ first does not end in 。．.!！?？…、，,;；:：
```

If title-like → `{ text: first, kind: 'title' }`, no ellipsis. Otherwise → excerpt of *all* lines joined by single spaces, truncated to 30 characters with `…` appended only when characters were actually dropped.

Rationale for each clause:
- **`lines.length > 1`**: a single short paragraph is the entire content, not a heading for something. Treating it as a title would be a distinction without a difference, and it would wrongly suppress the ellipsis logic for a text that might grow.
- **`≤ 30 characters`**: a CJK heading is short (the reported example 「英雄史詩ーいかが宿命に直面」 is 13). 30 is generous enough for a subtitle and still far below the point where a "title" is really a first sentence. It reuses the excerpt budget rather than inventing a second number.
- **Punctuation guard**: a line ending in `。` or `、` is a sentence or a clause that continues, not a heading. This is what stops a short opening sentence from being mistaken for a title.
- **Excerpt spans all lines**, not just the first: when the leading line is a long prose line the excerpt never reaches line 2 anyway, but when it is short-but-sentence-terminated (「以下、訳文です。」) an excerpt limited to that line would waste the budget on boilerplate.

**Ellipsis:** `…` (U+2026), one character wide, replacing the current hand-rolled `'...'`. It costs no layout width in a 30-character budget and reads as typographic elision rather than as part of the text.

**Character budget vs. the current 40:** the queue's `slice(0, 40)` was chosen for a card that is `text-metadata` (12px) and full-panel-width. The History heading is `text-body-sm` (14px) and shares its row with a badge, so 40 characters would always truncate under CSS anyway and the extra 10 would only ever be invisible. 30 is one budget that fits all three surfaces; the queue preview loses at most 10 characters it could not reliably show either.

**Alternative rejected:** a heuristic that also detects markdown-ish decoration (`# `, `【】`, `■`). The corpora here are plain pasted translation text; that machinery would be speculative and would need its own stripping rules.

### Decision 3: Count characters with `Array.from`, not `String.length`

`slice(0, n)` on UTF-16 code units can cut a surrogate pair in half and emit a replacement glyph. Rare CJK extension characters and emoji are both plausible in pasted corpora, so truncation iterates `Array.from(text)` and joins the first *n* code points. This also makes the budget mean the same thing for Japanese, Chinese, and Latin text, which is what the mixed-script requirement asks for.

### Decision 4: Keep the sequence number, move it to the metadata line

The heading becomes the label; `#{index + 1}` joins the timestamp line as `#1 · 2026/8/13 21:44:01` in `text-metadata text-on-surface-variant`. Dropping the number entirely was tempting, but it is the only stable handle the user has for referring to a round out loud or in notes ("the second one"), and two rounds pasted from the same corpus can legitimately produce identical labels — in that case the number is what disambiguates them. Demoting rather than deleting satisfies "preview is primary, number is secondary" without losing that.

The separator is a middle dot with spaces rather than a second `<p>`, so the card gains no vertical height — relevant because the History panel sits below Job Queue and AI Suggestions in a pane the user may have collapsed panels in.

### Decision 5: Truncate with `min-w-0` on the heading column, `shrink-0` on the actions

The card's outer row is `flex justify-between items-start`. A flex child does not shrink below its content's intrinsic width by default, so `truncate` on the `<h4>` alone would let a long label push the confirm/archive buttons out of the card. The fix is the standard pair: `min-w-0 flex-1` on the text column, `shrink-0` on the badge and on the action-button group, `gap-2` between them. That is entirely inside the existing card markup and touches no panel-level layout, so it cannot collide with the floating-session-pane work.

### Decision 6: Reuse 「(空のテキスト)」 as the blank fallback

The bell list already renders `snippet || '(空のテキスト)'`. Promoting that literal into the shared module's `EMPTY_CORRECTION_LABEL` means the blank case reads identically in all three surfaces and the string exists once. A blank heading in History would otherwise render as a zero-height row with an orphan badge.

## Risks / Trade-offs

- **Two rounds can produce the same label.** Same corpus corrected twice → identical headings. Mitigated by Decision 4: the sequence number and the timestamp both remain on the card, so the pair is still distinguishable.
- **The title heuristic can misfire.** A short, un-punctuated first line that is really the opening of a sentence will be shown as a title. The failure mode is benign — the user sees real text from the round either way, just without an ellipsis — and the punctuation guard covers the common Japanese case.
- **Queue previews shorten from 40 to 30 characters.** Accepted per Decision 2; the extra characters were already clipped by `truncate` at those widths.
- **`SavedData.targetText` is the round's target text at save time**, and `saveCorrections` clears the live editor afterwards — so History labels reflect the saved round, not the current editor. That is the intended reading of a history entry.

## Migration Plan

None required. Presentation-only plus a new pure module; no schema, no persisted field, no API contract. Reverting is a single-commit revert.

## Open Questions

None.
