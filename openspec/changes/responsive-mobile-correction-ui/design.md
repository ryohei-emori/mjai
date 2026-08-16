## Context

See proposal.md — Why for the failures being fixed. The constraints that shape the approach:

- `page.tsx` is one ~3,100-line client component. Its authenticated tree is `header` → optional session `aside` → a `flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden` container holding `main` (editor) and `aside` (job queue + suggestions + history). Restructuring that tree is the main risk in this change, so the design avoids moving JSX.
- `lg` (1024px) is already the only layout breakpoint, and `LG_BREAKPOINT_PX` in `lib/uiPreferences.ts` mirrors it for the JS that sizes the right pane. Introducing a second layout breakpoint would mean two sources of truth for the same split.
- `globals.css` clips horizontal overflow on `html, body`. That is what turns a too-wide top bar from an ugly scroll into unreachable controls, and it is worth keeping (a workspace that scrolls sideways by accident is worse), so the top bar has to fit rather than overflow.
- Tailwind is 3.4.17: `dvh` utilities exist, and `addVariant` plugins are available. `tailwindcss-animate` is the only plugin today.
- `layout.tsx` is a Server Component with no `viewport` export, so Next injects the default `width=device-width, initial-scale=1`.
- `next.config.js` sets `output: 'export'`, so anything added must be static-render safe.
- Jest is jsdom with no `matchMedia` and no configured viewport. jsdom does not evaluate media queries or lay anything out, which bounds what these tests can honestly assert.

## Goals / Non-Goals

**Goals:**

- Make every control reachable and every core action performable with a finger, at 320px.
- Give the review step the full screen when it is the step the user is on.
- Leave the desktop layout, density and hover behavior byte-for-byte as they are.
- Keep the change surgical: class and attribute edits plus one new piece of state, not a re-layout of `page.tsx`.

**Non-Goals:**

- Splitting `page.tsx` into components. It needs doing, but bundling it with a behavior change would make both unreviewable.
- A mobile-first rewrite of the 58 files that carry no responsive styling. Most are primitives that inherit their width; this change touches only the ones that actually misbehave.
- Bottom tab bars, gesture navigation, pull-to-refresh, or any other app-shell convention beyond what the two panes need.
- Side-by-side 原文 / 添削対象 on tablets. They are stacked at every width today, and stacking is right for the long CJK lines this app handles.

## Decisions

### 1. Pointer capability, not viewport width, decides touch affordances

Two Tailwind variants added via `addVariant`:

- `can-hover` → `@media (hover: hover) and (pointer: fine)`
- `touch` → `@media (hover: none)`

A hover-revealed action becomes `can-hover:opacity-0 can-hover:group-hover:opacity-100` instead of `opacity-0 group-hover:opacity-100`. The default (no variant) is "visible", so anything that cannot hover sees the action; a mouse still gets the quiet card. Tap targets become `touch:min-h-11 touch:min-w-11`, which leaves desktop sizes untouched.

Alternatives: gate on `lg:` — rejected, because it makes a narrow desktop window lose hover reveal it can use, and a 1280px-wide tablet keep affordances it cannot. Detect touch in JS and branch — rejected, because it needs a mount-time effect and re-render for something CSS answers directly, and `output: 'export'` means the first paint is static.

### 2. The double-click selection route stays, and stops being the only route

`onDoubleClick` on the suggestion card is kept for desktop, where it is a genuinely fast way to work through a list. What changes is that the always-visible-on-touch select button from Decision 1 is now a real single-activation route, which is what the spec requires. This is why Decision 1 comes first: it is the mechanism, and single-tap selection is a consequence of it rather than a second implementation.

Alternative: replace double-click with single-click on the card body. Rejected — the card contains a textarea, badges and a copy button, so a body-wide click target fights its own contents, and the existing `stopPropagation` dance would have to grow.

### 3. Below `lg`, one pane at a time — by visibility, not by moving JSX

New state `mobilePane: 'editor' | 'review'`, and `main` / `aside` each get a conditional `hidden lg:…` class. Nothing moves in the tree, so the desktop render path is provably unchanged and the diff stays reviewable. The switch itself is a two-button segmented control rendered `lg:hidden` directly under the header.

This also repairs the height fight described in proposal.md: with only one pane visible below `lg`, `flex-1` has a single claimant, so each pane gets the whole area and one scroll region instead of two competing ones. `aside` gains `flex-1 lg:flex-none` for that reason.

Alternatives: let the whole document scroll below `lg` (drop the inner scroll containers) — simpler and needs no new state, but leaves a single scroll of roughly editor + queue + 10–20 suggestion cards + history, which is the complaint, not the fix. An accordion of collapsible sections — more taps for the same information and it does not give the review list a full screen.

### 4. The pane switch reuses the existing "take the user to the suggestions" intent

`page.tsx` already has an effect that scrolls `[data-suggestions-card]` into view when `confirmingJobId` changes and suggestions have loaded, deliberately keyed on `suggestions.length` so selection edits do not re-trigger it. Below `lg` that element is now inside a hidden pane, where `scrollIntoView` is a silent no-op. Rather than add a second trigger, the same effect sets `mobilePane = 'review'`. One place decides "the user is now reviewing this job", and it keeps working for the job queue and the notification list without either of them knowing about panes.

The switch does not fire on generation *start*. A job takes 10–20 seconds during which the user may keep editing, and yanking the pane out from under them would be worse than the count badge that tells them something is waiting.

### 5. Section tabs move into the drawer below `md`, and only below `md`

The tabs (`Sessions` / `Dashboard` / `Archive`, the latter two currently placeholders) are the widest discardable thing in the top bar. Below `md` they render in the session drawer, which is already the "where am I" surface. `md` rather than `lg` because the tabs *do* fit a 768px tablet top bar, and the drawer copy is rendered `md:hidden` so the two never both exist.

Moving the tabs alone does not reach 320px. Measured, the remainder still wants ~385px: menu 44, wordmark ~65, new-session 36, and a four-icon cluster (bell, settings, avatar, sign-out) at ~188 including gaps. Identity and sign-out therefore follow below `sm`, to the foot of the same drawer — which is where a phone's account controls usually live — leaving the menu trigger, the wordmark and the three things a correction session needs at hand: new session, notifications, settings. With `px-3`/`gap-2` at that size the row fits 320px with roughly 35px to spare.

Both moves are a single `NAV_ITEMS` array rendered in two places rather than two hand-maintained copies, since three buttons duplicated by hand is what drifts.

Alternative: an overflow "…" menu for the icon cluster. Rejected: it hides settings behind an extra tap, and the drawer is a better home than a second disclosure for controls that are not part of the correction loop.

### 6. Viewport height from `dvh`, with a fallback that is not decoration

Two utilities in `globals.css` rather than Tailwind's `h-dvh`:

```css
.h-viewport { height: 100vh; height: 100dvh; }
```

Tailwind can emit both `h-screen` and `h-dvh`, but which one wins depends on utility ordering in the generated sheet, which is not something to rely on for the shell's height. The declaration pair is deterministic. The `vh` line matters: without any height the shell is a flex column of auto-height panes, which collapses rather than degrading.

### 7. The keyboard gets to resize the layout viewport

`layout.tsx` gains `export const viewport = { width: 'device-width', initialScale: 1, interactiveWidget: 'resizes-content' }`.

By default only the visual viewport shrinks when the on-screen keyboard opens, so `dvh` keeps reporting the full height and the field being typed into can sit behind the keyboard. `resizes-content` shrinks the layout viewport too, so `dvh` follows the keyboard and Decision 6 does the rest. Supported in Chrome 108+ and Firefox 132+; elsewhere it is ignored and behavior is today's.

`maximumScale` and `userScalable` are deliberately absent — suppressing zoom is the standard collateral damage of a mobile pass, and the spec forbids it.

### 8. Drop `vh` arithmetic where flex already knows the answer

`h-[calc(100vh-12rem)]` on the drawer's session list and `min-h-[calc(100vh-8rem)]` on the empty-session state encode a guess about how much chrome is above them. Both become flex-derived (`flex-1` inside a column, `min-h-full`), which is correct at every viewport and cannot drift when the header changes height.

The prompt dialog had the same shape of problem in `vh` form: a `45vh`/`55vh` textarea that ignored the header, footer and counters around it, so with the keyboard open the save button left the dialog. It becomes `flex-1` with a floor, inside a dialog bounded by `max-h-[90%]` — a percentage, because the dialog is `fixed` and so resolves against the initial containing block, which is the visible viewport — with `overflow-y-auto` as the backstop for when a flexible child has already shrunk to its floor.

### 10. Rows that cannot fit wrap, with the sacrifice chosen per row

Four rows are laid out as one line whose contents need more than 320px: the session heading beside its timing readouts, the offline-mode label beside its provider badge, the diagnostics phase beside the model name, and the exemplar heading beside its "input present" badges. Each gets `flex-wrap`, and what yields is decided per row rather than uniformly.

The session name shrinks and truncates but is given a basis (`basis-48`) it will fight for, so the short fixed readouts wrap to their own line rather than the name being cut to a few characters — the name is what identifies the work. The exemplar heading truncates for the mirror-image reason: it is fixed text the user can predict, where the badges beside it describe their own input.

### 9. Test what jsdom can actually answer

jsdom evaluates no media queries and lays nothing out, so a test cannot assert that a control is visible at 375px. What it can assert is the part that is not CSS: the switch's own state, that opening a job for review moves it, that it reports the count waiting in the pane the user cannot see, and that it is absent before a session exists. Anything that depends on real layout is verified by hand in a device-sized browser and recorded, not asserted in jsdom — a passing test that cannot fail is worse than no test.

No `matchMedia` stub or viewport helper turned out to be needed, because Decision 3 leaves the breakpoint entirely to CSS: nothing in the pane switch reads a viewport width. Asserting on the `hidden` / `lg:block` class strings was also dropped — it would restate the implementation without being able to detect the failure that matters, which is CSS not resolving the way the class names imply.

## Risks / Trade-offs

- **The pane switch is a new concept for existing (desktop) users** → It renders only below `lg`, where the alternative today is a broken split. Desktop sees nothing new.
- **Auto-switching panes on job review could surprise someone mid-edit** → It fires only when the user opened a job for review, which is an explicit request to look at suggestions; it does not fire on generation start.
- **`can-hover` / `touch` variants could be applied inconsistently as the UI grows** → They are named for the capability they test, and the two are mutually exclusive, so a reviewer can see at a glance which branch a class belongs to. Documented in `docs/UI-DESIGN.md`.
- **`interactiveWidget` is unsupported on Safari** → Its absence is exactly today's behavior, and Decision 6 still keeps the shell inside the visible viewport; only the keyboard case is left unimproved there.
- **jsdom tests cannot prove the layout works** → Stated plainly above; the real check is manual on a device-sized viewport, and it is a task, not an afterthought.
- **`page.tsx` grows again** → About 40 lines for the switch and its state. The file needs splitting, but not in the same change as a behavior fix (Non-Goals).

## Migration Plan

Frontend-only, no schema or environment change. `NEXT_PUBLIC_*` values are untouched, so no rebuild beyond the normal Vercel build on merge. Rollback is a revert of the commit range: nothing persists new state (`mobilePane` is in-memory, deliberately not in localStorage — a stored pane would reopen the app on the review tab of a session the user has since left).

## Open Questions

None that change the specs or the task breakdown. Whether the pane switch should also appear on tablet-width landscape (where 1024px is met but the right pane is cramped) is worth revisiting after the manual pass, and would be a follow-up adjustment of one breakpoint.
