## 1. Preconditions

- [x] 1.1 Confirm the concurrent frontend changes (`slide-job-queue-carousel`, exemplar-translation input) are committed and `frontend/src` is clean, then re-read `frontend/src/app/page.tsx` immediately before editing
- [x] 1.2 Confirm whether the exemplar-translation card exists in `page.tsx`; if it does not, mark task group 4 as out of scope

## 2. Session pane: docked ⇄ floating state

- [x] 2.1 Add `SESSION_PANE_STORAGE_KEY = 'mjai-session-pane-mode'` and a `SessionPaneMode` type near the existing right-pane constants
- [x] 2.2 Add `sessionPaneMode` state (SSR-safe initial value `'floating'`) and hydrate it from `localStorage` inside the existing mount effect that loads the right-pane width and `isLgScreen`, falling back to the viewport default (`docked` at ≥1024px) for missing or malformed values
- [x] 2.3 Derive `isSessionPaneDocked = sessionPaneMode === 'docked' && isLgScreen` and add `try/catch`-wrapped persistence helpers for the mode
- [x] 2.4 Add handlers: trigger click (docked → floating + close overlay; floating → open overlay) and dock click (floating → docked + close overlay)

## 3. Session pane: rendering and accessibility

- [x] 3.1 Extract the duplicated session-list body (search field + session cards + empty state) into a single render helper used by both presentations
- [x] 3.2 Render the docked `aside` only when `isSessionPaneDocked`, so the center and right panes reclaim the `w-72` column otherwise
- [x] 3.3 Remove the `lg:hidden` restriction from the session `Sheet` so it serves as the floating panel at all breakpoints, and delete the `fixed bottom-4 left-4` mobile FAB trigger
- [x] 3.4 Add the TopAppBar trigger button (leftmost, existing icon-button classes, `menu` / `menu_open`, state-specific `aria-label`, `aria-expanded`, `focus-visible` ring)
- [x] 3.5 Add the `lg`+-only dock button in the floating panel header (`dock_to_left`, `aria-label`) and verify session selection from the floating panel still switches sessions and closes the panel

## 4. Exemplar translation card disclosure

- [x] 4.1 Add `EXEMPLAR_CARD_STORAGE_KEY = 'mjai-exemplar-card-open'` plus `isExemplarCardOpen` state defaulting to collapsed, hydrated in the same mount effect with the same `try/catch` fallback
- [x] 4.2 Turn the exemplar card header into a `button` with `aria-expanded` / `aria-controls` and an `expand_more` / `expand_less` icon, keeping the existing copy button (if any) outside the disclosure button so it stays independently clickable
- [x] 4.3 Conditionally render the exemplar textarea on `isExemplarCardOpen`, and show a 「入力あり」 badge with a character count in the header when collapsed and non-blank
- [x] 4.4 Persist the disclosure state on toggle and verify collapsing does not clear the value, its draft persistence, or its inclusion in generation

## 5. Tests

- [x] 5.1 Add tests covering the session-pane mode default/hydration/fallback logic and the docked ⇄ floating transitions
- [x] 5.2 Add tests covering the exemplar disclosure: collapsed by default, toggle, persisted state, value retained while collapsed
- [x] 5.3 Run `npm run lint`, `npm test`, and `npm run build` in `frontend/` and fix any regressions

## 6. Docs and delivery

- [x] 6.1 Update `docs/UI-DESIGN.md`: Three-Pane Layout docked/floating states + TopAppBar trigger + persistence keys, Mobile Responsive Behavior no longer mobile-only sheet, exemplar card disclosure
- [x] 6.2 Manually verify docked, floating-closed, floating-open, and exemplar open/closed presentations in a running dev server, capturing screenshots
- [x] 6.3 Mark tasks complete, stage only this change's files, then commit and push
