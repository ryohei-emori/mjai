## Why

On desktop the session list occupies a permanent 288px column (`w-72`), so the two panes where the actual work happens — the center editor and the right Job Queue / AI Suggestions pane — are permanently squeezed. The `correction-workspace-ui` spec already promises a desktop "collapsible fixed sidebar" with a collapse/expand toggle, but the current implementation has no such toggle: the column is always mounted at `lg` and above. At the same time the optional 模範回答訳文 (exemplar translation) card added by `add-optional-exemplar-translation-input` keeps a full textarea permanently visible in the center pane even though its content is fixed per exercise and rarely needs to be read, pushing TARGET TEXT and the generate button further down.

## What Changes

- **Restore a docked ⇄ floating toggle for the desktop session pane.** At `lg` and above the session list can be either docked as today's fixed column or dismissed so the center and right panes reclaim its full width. When dismissed, the same session list is reachable as a floating overlay panel (the existing left `Sheet`), so session switching is never more than one click away.
- **Always-visible trigger.** A menu/sidebar icon button in the TopAppBar toggles the pane at every breakpoint, so the session list can never become unreachable. The existing mobile-only floating menu button is superseded by it.
- **Persist the docked/dismissed preference** in `localStorage` under a dedicated key, so a reload keeps the workspace as the user left it. First-ever visit defaults by viewport: docked at `lg`+, floating below `lg`.
- **Overlay accessibility**: backdrop click and `Escape` close the floating panel, focus is trapped inside it while open and returns to the trigger on close, and the trigger exposes `aria-expanded` / `aria-label`.
- **Make the exemplar-translation card collapsible**, collapsed by default, with a header disclosure control that shows a 「入力あり」 indicator when the field is non-empty so collapsed content is never silently forgotten. The open/closed state persists in `localStorage`.
- **No change** to session switching, history display, HITL confirm/save, bell notifications, the ~10s polling, the resizable right pane, or the job-queue carousel — this change only affects which chrome occupies horizontal/vertical space.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `correction-workspace-ui`: the "Responsive Sidebar Navigation" requirement is replaced by an explicit docked ⇄ floating session-pane requirement (persisted preference, always-visible trigger, overlay dismissal/focus behavior, viewport-based default), and the exemplar-translation input requirement gains collapsed-by-default disclosure behavior with a non-empty indicator and persisted open state.

## Impact

- **Frontend UI**: `frontend/src/app/page.tsx` — session-pane rendering (docked `aside` becomes conditional), TopAppBar toggle button, `Sheet` reused as the floating panel at all breakpoints, exemplar card wrapped in a disclosure.
- **Frontend styles**: `frontend/src/app/globals.css` only if a disclosure/collapse transition helper is needed; no new color or spacing tokens.
- **Frontend persistence**: two new `localStorage` keys alongside the existing `mjai-right-pane-width` / `mjai:draft:` keys. No server state, no API change, no DB migration.
- **Docs**: `docs/UI-DESIGN.md` — Three-Pane Layout section gains the docked/floating states and the toggle; Mobile Responsive Behavior updated to reflect that the sheet is no longer mobile-only.
- **Interaction with concurrent work**: depends on `add-optional-exemplar-translation-input` having landed for requirement B; the job-queue carousel from `slide-job-queue-carousel` already measures its own track width with a `ResizeObserver`, so it adapts to the wider right/center panes without change.
- **Out of scope**: an icon-only rail variant of the docked pane, making the right pane collapsible, collapsing SOURCE/TARGET cards, and any server-side UI-preference persistence.
