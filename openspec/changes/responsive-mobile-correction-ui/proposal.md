## Why

On a phone the correction workspace is not merely cramped — parts of it cannot be operated at all. The top bar is a single non-wrapping row of a menu button, the wordmark, three nav tabs and five icon actions, which overflows below roughly 640px; because `globals.css` sets `overflow-x: hidden` on `html, body`, the overflow is clipped rather than scrollable, so 設定 and ログアウト become physically unreachable. Selecting a suggestion — the one action the whole review step is made of — is bound to `onDoubleClick` plus a `group-hover`-revealed icon, and a touch screen has neither: a double-tap is a zoom gesture and there is no hover to reveal anything. The shell is sized with `100vh`, which on iOS Safari means the largest viewport, so the bottom of the app sits behind the browser toolbar, and the on-screen keyboard covers the very textarea being typed into.

Underneath those is a structural problem. Below `lg` the editor and the review pane stack inside a `min-h-0 overflow-hidden` container while both declare `overflow-y-auto`, so the fixed viewport height is split between two competing scroll areas: the user gets a squeezed editor above a squeezed suggestion list, and after tapping 生成 the results are thousands of pixels away from the text they describe.

## What Changes

- **The shell tracks the real viewport.** Height comes from `dvh` (with a `vh` fallback, because a shell with no height collapses rather than degrades), and the layout viewport is made to follow the on-screen keyboard so the focused field stays visible while typing.
- **The top bar stops clipping.** Below `md` the nav tabs move into the session drawer, which is where the session list already lives; the remaining controls fit one row at 320px. Pinch-zoom is left enabled.
- **One pane at a time below `lg`.** A 編集 / 添削案 switch under the header shows either the text cards or the review column, each getting the full available height and a single scroll. Above `lg` the side-by-side layout with its resizable right pane is unchanged. The existing "jump to the suggestions card when reviewing a job" behavior switches the pane on mobile, where scrolling to a hidden element does nothing.
- **Touch gets first-class affordances.** Actions previously revealed on hover stay visible where the pointer cannot hover, a single tap selects a suggestion, and tap targets reach 44px on coarse pointers. Desktop density and hover behavior are unchanged, because the switch is on pointer capability rather than screen width.
- **Long rows wrap instead of colliding**: the session header and its timer badges, the suggestion card header, and the generate button's hit area.

Not included: any change to what the AI is asked or what it returns, to persistence, or to the desktop layout. No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `correction-workspace-ui`: adds requirements for viewport-accurate sizing, a non-clipping adaptive top bar, one-pane-at-a-time workspace presentation below `lg`, and pointer-capability-based touch affordances (including a single-tap route to selecting a proposal, which today is double-click only).

## Impact

- `frontend/src/app/page.tsx` — shell height, top bar, the mobile pane switch, session header wrapping, suggestion card affordances.
- `frontend/src/app/layout.tsx` — `viewport` export (keyboard behavior), document language.
- `frontend/src/app/globals.css` — viewport-height utilities.
- `frontend/tailwind.config.js` — pointer-capability variants.
- `frontend/src/components/ui/sheet.tsx`, `job-queue-carousel.tsx` — drawer sizing at 320px, carousel tap targets.
- `frontend/jest.config.js` / test setup — a viewport + `matchMedia` harness, which does not exist today (58 of 66 source files have no responsive styling and there are no layout tests).

No backend, API, schema, or environment change. Nothing to migrate or redeploy beyond the normal frontend build.
