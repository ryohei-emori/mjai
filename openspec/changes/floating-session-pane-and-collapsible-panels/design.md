## Context

See `proposal.md` for motivation.

Today `frontend/src/app/page.tsx` renders the workspace as `header` + a flex row containing three regions:

- a docked session column — `<aside className="hidden lg:flex lg:flex-col w-72 …">` — always mounted at `lg`+, never collapsible;
- a `Sheet` (Radix `Dialog` wrapper, `frontend/src/components/ui/sheet.tsx`) holding a **duplicate** copy of the same session list, opened only by a `lg:hidden` floating menu button at `bottom-4 left-4`;
- the center `main` (editor cards) and the right `aside` (Job Queue carousel, AI Suggestions, History), separated by a pointer-drag resize handle whose width persists under `mjai-right-pane-width`.

The `correction-workspace-ui` spec's "Responsive Sidebar Navigation" requirement already describes a desktop collapse/expand toggle that no longer exists in the code, so this change reconciles code and spec rather than inventing a new interaction.

`add-optional-exemplar-translation-input` adds a third editor card in the center pane between SOURCE TEXT and TARGET TEXT. Its `design.md` Decision 2 explicitly rejected a collapsible presentation as "unnecessary complexity"; the user has since asked for exactly that, so this change supersedes that sub-decision while keeping everything else about the field (naming, prompt threading, draft persistence) intact.

## Goals / Non-Goals

**Goals:**

- Let the user reclaim the 288px session column for the center + right panes, and put it back, from an obvious always-visible control.
- Keep the session list one click away when it is not docked, with correct overlay accessibility.
- Remember both the pane presentation and the exemplar disclosure across reloads.
- Reuse existing components (`Sheet`) and existing `docs/UI-DESIGN.md` tokens — no new colors, sizes, or animation primitives.
- Remove the current duplicated session-list JSX rather than adding a third copy.

**Non-Goals:**

- An icon-only "rail" variant of the docked pane (the spec's old wording allowed it; a rail still consumes width, which defeats the user's stated goal).
- Making the right pane collapsible, or collapsing SOURCE / TARGET cards.
- Drag-to-resize for the session pane, or a draggable/repositionable floating panel.
- Server-side persistence of UI preferences.
- Any change to job-queue behavior, HITL flow, polling, or the AI request payload.

## Decisions

### 1. Two states, not three: `docked` ⇄ `floating`

**Choice**: One piece of persisted state, `sessionPaneMode: 'docked' | 'floating'`, plus one piece of ephemeral state, `sidebarOpen` (already exists), which only matters while `mode === 'floating'`.

| `sessionPaneMode` | `sidebarOpen` | Rendering |
|---|---|---|
| `docked` (only reachable at `lg`+) | ignored | docked `aside` column; center + right share the remaining width; no overlay |
| `floating` | `false` | no session column at all; center + right span the full width |
| `floating` | `true` | same full-width layout, with the `Sheet` overlay + backdrop above it |

Transitions:

- Trigger click at `lg`+ while `docked` → `floating`, and immediately `sidebarOpen = false` (the point of the click is to gain space, not to see the list again).
- Trigger click while `floating` → `sidebarOpen = true` (open the overlay). It does **not** re-dock, because the same button is the mobile menu button and mobile has no docked state.
- Re-docking is a separate action: a **dock button** inside the floating panel header (`dock_to_left` icon, `lg`+ only) sets `floating → docked` and closes the overlay.
- Backdrop click / `Escape` / session selection → `sidebarOpen = false`, mode unchanged.

**Rationale**: A single 3-way cycling button (docked → floating-closed → floating-open → docked) is unpredictable and unlabelable. Separating "show me the list" (trigger) from "give the list a permanent home" (dock button, only where docking is possible) keeps each control's `aria-label` honest.

**Alternatives considered**:
- One tri-state button — rejected as above.
- Keeping the docked column mounted but `w-0`/`translate-x` hidden — rejected: the docked and floating presentations already need different chrome, and a zero-width mounted column still runs the full session list render.
- A resizable session pane instead of a collapsible one — does not reach zero width, so it does not satisfy "作業空間を広く使える".

### 2. Reuse `Sheet` for the floating panel at every breakpoint; drop the duplicate list JSX

**Choice**: Extract the session-list body into one internal `SessionListPanel` render helper used by both the docked `aside` and the `Sheet`, and remove the `lg:hidden` restriction from the `Sheet`.

**Rationale**: `Sheet` wraps Radix `Dialog`, which already gives modal focus trapping, focus restore to the trigger, `Escape`, backdrop dismissal, `aria-modal`, and scroll locking — all of requirement A's accessibility bullets, with no hand-rolled focus management. The current duplicated list JSX (~65 lines twice) is exactly the kind of drift risk that motivated the shared `jobQueue/ordering.ts` helper in `slide-job-queue-carousel`.

**Trade-off**: The floating panel is modal, so the workspace behind it is inert while open. Accepted: the panel is short-lived (opened to switch sessions, then closed), and modality is what makes `Escape`/backdrop/focus-trap behavior free and predictable.

### 3. Trigger lives in the TopAppBar, replacing the floating mobile FAB

**Choice**: An icon button as the **first** item in the `header`, left of the `MJAI` wordmark, using the existing TopAppBar icon-button pattern (`p-2 rounded-full hover:bg-surface-container transition-colors`, `material-symbols-outlined md-24 text-on-surface-variant`) — the same pattern as the bell and logout buttons. Icon: `menu` when the list is hidden/closed, `menu_open` when the floating panel is open. `aria-label` is state-specific (「セッション一覧を開く」/「閉じる」/「セッション一覧をたたむ」), `aria-expanded` reflects "is the list currently visible" (docked, or floating-and-open). `focus-visible:ring-2 focus-visible:ring-md3-primary` per the carousel's precedent.

The existing `fixed bottom-4 left-4 z-50 lg:hidden` FAB is removed: with a TopAppBar trigger at all widths it is redundant, and it overlapped the mobile content.

**Rationale**: Top-left is the conventional home for a navigation-drawer toggle and it is always visible, satisfying "迷子にならない".

### 4. Persistence keys and hydration order

**Choice**: Two new keys, following the flat `mjai-…` naming of `mjai-right-pane-width` (the per-session `mjai:draft:` / `mjai:jobQueue:` prefixes are for session-scoped data; these preferences are global):

| Key | Values | Default |
|---|---|---|
| `mjai-session-pane-mode` | `"docked"` \| `"floating"` | viewport-based: `docked` at `innerWidth >= 1024`, else `floating` |
| `mjai-exemplar-card-open` | `"1"` \| `"0"` | `"0"` (collapsed) |

Both are read in a mount-time `useEffect` — reusing the existing effect that already loads `mjai-right-pane-width` and sets `isLgScreen` — never during `useState` initialization, so server and first client render agree and Next.js does not hydration-mismatch. Initial state is therefore the SSR-safe value (`floating` for the pane, since `isLgScreen` starts `false`; `false` for the disclosure), corrected within the same commit-then-effect tick. Writes happen in the click handlers, wrapped in `try/catch` like the existing helpers, so Safari private mode / disabled storage degrades to in-memory-only.

**Note on the default**: an unknown/garbage stored value is treated as "nothing stored" and falls back to the viewport default, per the spec's fallback scenario.

The load/save helpers live in `frontend/src/lib/uiPreferences.ts` rather than inside `page.tsx`, following the `lib/jobQueue/ordering.ts` precedent, so the default/fallback logic is unit-testable without rendering the 3000-line workspace component. `resolveSessionPaneMode(stored, viewportWidth)` is exported as a pure function for exactly that reason.

### 5. `docked` is clamped to `lg`+ rather than persisted per breakpoint

**Choice**: A single stored mode. The effective presentation is `mode === 'docked' && isLgScreen ? 'docked' : 'floating'`. Narrowing the window past `lg` therefore floats the pane without overwriting the stored `docked` preference, and widening it back restores docking.

**Rationale**: `isLgScreen` is already tracked by a `resize` listener for the right pane, so this is free. Storing separate per-breakpoint preferences would surprise users who resize a desktop window.

### 6. Exemplar card: header-button disclosure, conditional body, no height animation

**Choice**: The card's `CardHeader` becomes a `<button type="button">` row carrying `aria-expanded` and `aria-controls`, with a trailing `expand_more` / `expand_less` Material Symbol. The `CardContent` (textarea) is **conditionally rendered** rather than hidden with CSS.

**Rationale**: The codebase's existing show/hide patterns (`showCustomForm`, `bellPanelOpen`, the carousel's overflow cues) are all conditional-render with, at most, `transition-colors`; there is no height/grid-rows collapse animation anywhere, and `docs/UI-DESIGN.md` defines no such token. Adding a bespoke max-height transition would be inventing a pattern the doc does not sanction — "開閉アニメーションは既存の流儀に合わせる" resolves to "instant, with the icon rotating via the existing `transition-transform`". Not rendering the textarea also keeps the exemplar out of the tab order while collapsed.

**Indicator when collapsed and non-blank**: a `Badge` reading 「入力あり」 using the existing `bg-session-complete text-white` pair already used for "N Saved" / saved-state badges, plus a character count in `text-metadata text-on-surface-variant`. No new token.

**Value ownership unchanged**: the disclosure only gates rendering. `exemplarTranslation` stays in session state with its existing debounced draft persistence, so a collapsed card's text is still persisted and still threaded into generation.

### 7. Center/right panes absorb the freed width automatically

**Choice**: No width arithmetic. The center `main` is `flex-1` and the right `aside` has an explicit pixel width; removing the docked `aside` hands the entire 288px (`w-72`) to `main`.

**Interaction with the carousel**: the right pane's width is unchanged by this toggle, so `slide-job-queue-carousel`'s `ResizeObserver`-measured cards-per-view does not shift when the session pane toggles — the carousel simply keeps working. On mobile, where the right pane is full-width, the observer already handles the width change. No cap or clamp needed.

### 8. Docs update scope

**Choice**: Update `docs/UI-DESIGN.md`'s "Three-Pane Layout" section with the docked/floating states, the TopAppBar trigger, and the persistence keys; update "Mobile Responsive Behavior" to say the sheet is the floating presentation at all widths (no longer mobile-only); add the exemplar disclosure to the layout description. No new entries in the color / typography / spacing tables, because no new tokens are introduced.

## Risks / Trade-offs

- **[Risk] Users lose track of the session list after floating it** → Mitigation: the TopAppBar trigger is always visible with a state-specific label; the floating panel carries a dock button to restore the column.
- **[Risk] Modal overlay blocks the workspace, e.g. during an active HITL review** → Mitigation: the panel closes on `Escape`, backdrop click, and session selection; no long-lived state lives inside it. Job processing and the ~10s poll are unaffected by overlay state.
- **[Risk] Hydration mismatch from reading `localStorage`/`innerWidth` too early** → Mitigation: preferences are only applied in a mount effect (Decision 4), matching the existing `mjai-right-pane-width` pattern.
- **[Risk] Merge conflicts with concurrent frontend work in `page.tsx`** → Mitigation: implement only after the exemplar change lands, re-read the file immediately before editing, and stage only this change's files.
- **[Trade-off] Collapsed-by-default exemplar hides a field some users fill every time** → Accepted per the user's request; the 「入力あり」 badge plus persisted open state means a user who always uses it expands once and keeps it open.
- **[Trade-off] No collapse animation** → Accepted; consistent with every other disclosure in this codebase and avoids inventing an unsanctioned motion token.

## Migration Plan

1. Frontend-only, additive, no API or DB change; ship in a normal Vercel deploy.
2. No feature flag. Existing users see the pane docked at desktop widths on first load (unchanged from today) until they choose otherwise.
3. Rollback: revert the commit. Leftover `mjai-session-pane-mode` / `mjai-exemplar-card-open` keys are simply unread by the reverted code.

## Open Questions

None blocking. If the exemplar change does not land, requirement B has no target component and is dropped from this change's scope; requirement A is fully independent of it.
