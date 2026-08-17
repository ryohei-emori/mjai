# Tasks — english-ui-labels-and-chrome-polish

## 1. Scroll regions

- [x] 1.1 Replace the `prefers-color-scheme: dark` block in `frontend/src/app/globals.css` with an unconditional `color-scheme: light` on `html`, noting why (light-only app, `.dark` never applied)
- [x] 1.2 Add a `.token-scrollbar` utility beside `.job-carousel-track`, using only `::-webkit-scrollbar*` with an `--outline-variant` thumb and `--outline` on hover; leave the carousel block untouched
- [x] 1.3 Apply `.token-scrollbar` to the editor pane, the review pane and the notifications list in `frontend/src/app/page.tsx`
- [x] 1.4 Move the Radix `ScrollArea` thumb from `bg-border` to `bg-outline-variant` with `hover:bg-outline`

## 2. Non-interactive readouts

- [x] 2.1 Remove `hover:bg-primary/80`, `hover:bg-secondary/80` and `hover:bg-destructive/80` from `badgeVariants` in `frontend/src/components/ui/badge.tsx`
- [x] 2.2 Confirm no `Badge` call site relies on that hover (none takes an `onClick`), and that interactive surfaces — job cards, suggestion cards, session entries, notification rows — keep theirs

## 3. Provider badge removal

- [x] 3.1 Delete the `クラウドAPI` / `ローカルAI` `Badge` from the offline-mode row in `page.tsx`, keeping `lastSuggestionSource` state (still used for the saved `llmProvider`)

## 4. English chrome

- [x] 4.1 Pane switch → `TEXT` / `SUGGESTIONS`, with its group `aria-label`
- [x] 4.2 Session header `作成日:` → `Created:`
- [x] 4.3 Offline-mode checkbox label → `Offline Mode (WebLLM)`, and the WebGPU-unavailable notice
- [x] 4.4 Notifications panel subtitle, empty state, job `完了` badge, bell `title` / `aria-label`
- [x] 4.5 Job Queue: mode description, status badges (`Processing` / `Completed` / `Failed` / `Queued`), `確認` affordance, `再試行` button, carousel hint and arrow labels
- [x] 4.6 Suggestion panel: `選択済み: N/3+` → `Selected: N/3+`, `保存可能`, `指摘箇所` / `修正コメント` labels, custom-correction form, overall-comment label, confirm/save button
- [x] 4.7 History cards: `未確認` badge, action `title`s
- [x] 4.8 Session list and drawer: search placeholder, empty state, delete `aria-label`, drawer title, dock button, `セッションを開始` card
- [x] 4.9 Exemplar card: `EXEMPLAR TEXT (reference translation)` + `optional`, `入力あり` badge, character count, placeholder, copy `aria-label`
- [x] 4.10 Copy buttons, resize handle, settings/sign-out `title`s, diagnostics panel phase text, `（初回DL）`
- [x] 4.11 Toast titles and descriptions for queueing, completion, failure, restore, copy, save and archive
- [x] 4.12 `formatJobDuration` → `12.3s`
- [x] 4.13 Leave `instructionPrompt`, the `抽出できませんでした` parser sentinel, AI critique text and user input untouched

## 5. New Session weight

- [x] 5.1 Add `text-body-base` to the wide-viewport New Session button, keeping `font-semibold`

## 6. Docs and verification

- [x] 6.1 Record in `docs/UI-DESIGN.md`: `color-scheme: light` + `.token-scrollbar`, `Badge` as non-interactive, the New Session pairing, and English-only chrome
- [x] 6.2 Update tests that name renamed labels (`apiError.test.tsx`, `exemplar-text-card.test.tsx`, `job-queue-carousel.test.tsx`)
- [x] 6.3 `npm run lint`, `npm test`, `npm run build` in `frontend/`

## 7. Custom scale tokens survive class merging

- [x] 7.1 Teach `cn` in `frontend/src/lib/utils.ts` the project's custom `fontSize` and `spacing` scales via `extendTailwindMerge`, so `text-body-base` is classified as a size and no longer displaces `text-on-primary` on the New Session button
- [x] 7.2 Cover the New Session composition and a spacing token with a unit test on `cn`
- [x] 7.3 Record the rule in `docs/UI-DESIGN.md` beside the typography scale: a custom scale value must be registered with `tailwind-merge` or it is merged as a colour
- [x] 7.4 Re-run `npm run lint`, `npm test`, `npm run build` in `frontend/`
