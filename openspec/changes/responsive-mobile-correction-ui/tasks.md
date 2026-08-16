## 1. Viewport sizing

- [x] 1.1 Add `h-viewport` / `min-h-viewport` utilities to `globals.css` with the `vh` → `dvh` declaration pair, and a comment saying why the fallback is load-bearing
- [x] 1.2 Replace `h-screen` on the shell and `min-h-screen` on the auth-loading screen with them
- [x] 1.3 Add the `viewport` export to `layout.tsx` with `interactiveWidget: 'resizes-content'`, and without `maximumScale` / `userScalable`
- [x] 1.4 Set the document language to Japanese so CJK line-breaking and font selection are correct
- [x] 1.5 Replace the two `calc(100vh - …)` guesses (drawer session list, empty-session state) with flex-derived heights — three in the end; the prompt dialog's `45vh`/`55vh` textarea was the same mistake in another unit

## 2. Pointer-capability variants

- [x] 2.1 Add a `can-hover` variant to `tailwind.config.js` via `addVariant`. No `touch` variant: 2.3 needs a whole rule under `hover: none`, not a variant of one utility, so it is a class in `globals.css` instead
- [x] 2.2 Convert every `opacity-0 group-hover:opacity-100` reveal (suggestion card actions, session list delete, toast close) to the `can-hover` form so the action is visible where the pointer cannot hover
- [x] 2.3 Give every icon-only control a 44px minimum under `hover: none`: card copy/select, session delete, header cluster, carousel chevrons, history actions, dialog and sheet dismiss
- [x] 2.4 Confirm the desktop rendering is unchanged — verified in the generated stylesheet (the rules sit inside `@media (hover: hover) and (pointer: fine)` / `@media (hover: none)`, never on the base class) and in the browser at 1280px

## 3. Top bar

- [x] 3.1 Hide the section tabs below `md` and render the same choices inside the session drawer, closing the drawer on selection
- [x] 3.2 Verify the remaining controls fit 320px — they did not with the tabs alone removed, so identity and sign-out move to the drawer below `sm` as well (design.md Decision 5)
- [x] 3.3 Let the session header and its LATEST / AVG / Saved badges wrap instead of colliding with the session name

## 4. One pane at a time below `lg`

- [x] 4.1 Add `mobilePane` state, in memory only
- [x] 4.2 Add the segmented 編集 / 添削案 switch, rendered only below `lg`, with tap targets sized for a finger
- [x] 4.3 Show exactly one pane below `lg` by conditional visibility classes, without moving any JSX
- [x] 4.4 Give the review pane `flex-1` below `lg` so the single visible pane owns the full height and one scroll region
- [x] 4.5 Surface pending review work on the switch: suggestion count, falling back to queued/running generations when there is nothing to review yet
- [x] 4.6 Have the existing scroll-to-suggestions effect also bring the review pane forward, so job-queue and notification review both work below `lg`
- [x] 4.7 Make the generate button a comfortable full-width target on narrow viewports

## 5. Narrow-viewport sizing of the rest

- [x] 5.1 Make the session drawer fit 320px (it was fixed at `w-80`) and scroll within its own height
- [x] 5.2 Check the notification dropdown, prompt-settings dialog and job-queue cards at 320px. The dropdown was already capped at `calc(100vw-2rem)` and the carousel derives card widths from the measured track, so both were fine; the dialog needed the height work in 1.5 and was then confirmed in the browser

## 6. Tests

- [x] 6.1 No `matchMedia` stub or viewport helper was needed — the pane switch reads no viewport width (design.md Decision 9). One test does narrow `window.innerWidth`, but only because the *pre-existing* docked-pane logic reads it
- [x] 6.2 The switch reports the editor as showing on a fresh session, and reverses on activation. Which pane is *painted* is CSS, so it is checked in 7.1 rather than asserted here
- [x] 6.3 Reviewing a job from the queue brings the review pane forward
- [x] 6.4 The switch reports pending suggestions and running generations
- [x] 6.5 Dropped as untestable in jsdom: "no switch at lg" is a media query, and asserting the class string would restate the implementation without being able to fail when CSS does not resolve as the names imply. Covered by 7.4
- [x] 6.6 A single activation of a proposal's selection control selects it, and again deselects it, with the order bookkeeping from the spec
- [x] 6.7 Section tabs are reachable from the drawer and switch section, closing the drawer. Note both copies are always in the DOM — `hidden` decides which is exposed — so the test addresses the drawer's copy through the drawer
- [x] 6.8 The viewport export enables keyboard-aware layout and does not disable zoom
- [x] 6.9 Run frontend jest, `tsc`, and lint — 25 suites / 285 tests pass; lint clean apart from a pre-existing custom-font warning

## 7. Manual verification (real layout, which jsdom cannot answer)

- [x] 7.1 At 320px, 390px and 768px: every top-bar control reachable, no horizontal clipping, no horizontal page scroll. Also checked the drawer (tabs, search, session list and the account row all visible without clipping) and the prompt dialog (all three footer buttons reachable at 390px without scrolling)
- [ ] 7.2 Focus the 添削対象 field with an on-screen keyboard open and confirm the field stays visible — **not verifiable here**: the verification browser is desktop Chrome with no on-screen keyboard, and DevTools device emulation does not raise one. `interactiveWidget` is asserted in 6.8; its effect needs a real touch device
- [~] 7.3 Walk one correction end to end on a phone-sized viewport — done as far as this environment allows (create session, enter both texts, switch panes both ways, open and dismiss the settings dialog). Generation itself was not run: no AI provider keys exist in this environment
- [x] 7.4 Confirm the desktop layout at 1280px is unchanged from `main`: tabs, avatar and sign-out in the bar, both panes side by side with the resize handle, and no pane switch

## 8. Docs

- [x] 8.1 `docs/UI-DESIGN.md`: the breakpoints in use and what each decides, the pointer-capability variants, and the 44px rule
- [x] 8.2 `docs/SYSTEM-DESIGN.md`: the mobile pane switch as workspace presentation, and that it carries no persisted state
- [x] 8.3 Correct the stale `next.config.js` description in `AGENTS.md` — it was still claiming the explicit output mode had been removed
