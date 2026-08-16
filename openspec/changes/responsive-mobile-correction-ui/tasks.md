## 1. Viewport sizing

- [ ] 1.1 Add `h-viewport` / `min-h-viewport` utilities to `globals.css` with the `vh` → `dvh` declaration pair, and a comment saying why the fallback is load-bearing
- [ ] 1.2 Replace `h-screen` on the shell and `min-h-screen` on the auth-loading screen with them
- [ ] 1.3 Add the `viewport` export to `layout.tsx` with `interactiveWidget: 'resizes-content'`, and without `maximumScale` / `userScalable`
- [ ] 1.4 Set the document language to Japanese so CJK line-breaking and font selection are correct
- [ ] 1.5 Replace the two `calc(100vh - …)` guesses (drawer session list, empty-session state) with flex-derived heights

## 2. Pointer-capability variants

- [ ] 2.1 Add `can-hover` and `touch` variants to `tailwind.config.js` via `addVariant`
- [ ] 2.2 Convert every `opacity-0 group-hover:opacity-100` reveal (suggestion card actions, session list delete, toast close) to the `can-hover` form so the action is visible where the pointer cannot hover
- [ ] 2.3 Give every icon-only control a `touch:`-scoped 44px minimum: card copy/select, session delete, header cluster, carousel chevrons, history actions
- [ ] 2.4 Confirm the desktop rendering is unchanged — the variants must add rules under a media query, never alter the base class

## 3. Top bar

- [ ] 3.1 Hide the section tabs below `md` and render the same choices inside the session drawer, closing the drawer on selection
- [ ] 3.2 Verify the remaining controls fit 320px, and that the icon cluster cannot be pushed outside the clipped width
- [ ] 3.3 Let the session header and its LATEST / AVG / Saved badges wrap instead of colliding with the session name

## 4. One pane at a time below `lg`

- [ ] 4.1 Add `mobilePane` state, in memory only
- [ ] 4.2 Add the segmented 編集 / 添削案 switch, rendered only below `lg`, with tap targets sized for a finger
- [ ] 4.3 Show exactly one pane below `lg` by conditional visibility classes, without moving any JSX
- [ ] 4.4 Give the review pane `flex-1` below `lg` so the single visible pane owns the full height and one scroll region
- [ ] 4.5 Surface pending review work on the switch: suggestion count, and queued/running generations
- [ ] 4.6 Have the existing scroll-to-suggestions effect also bring the review pane forward, so job-queue and notification review both work below `lg`
- [ ] 4.7 Make the generate button a comfortable full-width target on narrow viewports

## 5. Narrow-viewport sizing of the rest

- [ ] 5.1 Make the session drawer fit 320px (it is fixed at `w-80` today) and scroll within its own height
- [ ] 5.2 Check the notification dropdown, prompt-settings dialog and job-queue cards at 320px for clipped or overflowing content

## 6. Tests

- [ ] 6.1 Add a `matchMedia` stub and a viewport-width helper to the jest setup, wired through `jest.config.js`
- [ ] 6.2 Below `lg`: the editor pane renders and the review pane does not, and the switch reverses that
- [ ] 6.3 Reviewing a job from the queue brings the review pane forward
- [ ] 6.4 The switch reports pending suggestions and running generations
- [ ] 6.5 At `lg` and above: both panes render and no switch is offered
- [ ] 6.6 A single activation of a proposal's selection control selects it, and again deselects it, with the order bookkeeping from the spec
- [ ] 6.7 Section tabs are reachable from the drawer, and are not duplicated when the top bar carries them
- [ ] 6.8 The viewport export enables keyboard-aware layout and does not disable zoom
- [ ] 6.9 Run frontend jest, `tsc`, and lint

## 7. Manual verification (real layout, which jsdom cannot answer)

- [ ] 7.1 At 320px, 375px and 768px: every top-bar control reachable, no horizontal clipping
- [ ] 7.2 Focus the 添削対象 field with an on-screen keyboard open and confirm the field stays visible
- [ ] 7.3 Walk one correction end to end on a phone-sized viewport: enter text, generate, switch to 添削案, select three suggestions by single tap, confirm and copy
- [ ] 7.4 Confirm the desktop layout at 1440px is visually unchanged from `main`

## 8. Docs

- [ ] 8.1 `docs/UI-DESIGN.md`: the two breakpoints in use and what each decides, the pointer-capability variants, and the 44px rule
- [ ] 8.2 `docs/SYSTEM-DESIGN.md`: the mobile pane switch as workspace presentation, and that it carries no persisted state
- [ ] 8.3 Correct the stale `next.config.js` description in `AGENTS.md` if it is still claiming no explicit output mode
