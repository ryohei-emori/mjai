## 1. Shared label helper

- [x] 1.1 Create `frontend/src/lib/correctionLabel.ts` exporting `EMPTY_CORRECTION_LABEL`, the structural `CorrectionTextSource` type, the `CorrectionLabel` result type, and `deriveCorrectionLabel` implementing the title-line / excerpt / blank rules from design Decisions 2–3 and 6
- [x] 1.2 Add `frontend/src/lib/__tests__/correctionLabel.test.ts` covering: title-like first line used verbatim, single-paragraph short text (no ellipsis), long prose truncated with `…`, multi-line prose collapsed to one line, short first line ending in `。` treated as excerpt not title, blank/whitespace-only fallback to 「(空のテキスト)」, blank target text falling back to source text, mixed Japanese/Chinese text, and surrogate-pair-safe truncation

## 2. History card heading

- [x] 2.1 In `frontend/src/app/page.tsx`, replace the History card's `添削データ #{index + 1}` heading with the derived label, keeping `font-semibold text-body-sm text-on-surface` and adding `truncate`
- [x] 2.2 Move the sequence number into the card's metadata line as `#{index + 1} · {timestamp}` in `text-metadata text-on-surface-variant`
- [x] 2.3 Apply the flex fix from design Decision 5 (`min-w-0 flex-1` text column, `shrink-0` badge and action group, `gap-2` row) so a long label cannot displace the confirm/archive buttons

## 3. Share the rule with the existing preview surfaces

- [x] 3.1 Replace the Job Queue card's inlined `job.targetText.slice(0, 40)` preview with `deriveCorrectionLabel`
- [x] 3.2 Replace the TopAppBar bell entry's inlined snippet (including its `|| '(空のテキスト)'` fallback) with `deriveCorrectionLabel`

## 4. Documentation

- [x] 4.1 Document the correction-label pattern in `docs/UI-DESIGN.md` (title-line vs excerpt rule, 30-character budget, `…` ellipsis, blank placeholder, where the History sequence number lives, which three surfaces share it)

## 5. Verification

- [x] 5.1 Run `cd frontend && npm test` and `npm run lint`; fix anything the change introduced
- [x] 5.2 Run `cd frontend && npm run build`
- [x] 5.3 Start the app and visually confirm the History cards show identifiable headings, that badges/timestamps/confirm/archive still work, and that a long label truncates cleanly
- [x] 5.4 Commit only the files this change touches (explicit `git add`, no `-A` / `-a`) and push
