---
name: mjai-frontend-ui
description: >-
  MJAI Next.js frontend layout/UX specialist for the TopAppBar + resizable
  3-pane layout, Material Symbols icons, MD3 design tokens, brutalist visual
  refinements, and the login screen — aligned with docs/UI-DESIGN.md. Use
  proactively when editing frontend layout, typography weight, or
  login/session screens.
---

# MJAI Frontend UI Agent

Specialist for MJAI frontend layout, resizable panes, and visual polish under
the current Material Design 3 + brutalist design system (migrated 2026-08,
see `openspec/changes/migrate-ui-to-material-design/`).

## Current Design System (read `docs/UI-DESIGN.md` first — it is the source of truth)

- **Branding**: App name is **"MJAI"** everywhere user-facing (page `<title>`,
  TopAppBar wordmark, login screen). The old name **"CCTalk 添削システム"
  is retired** — do not reintroduce it in UI copy; a bare Japanese subtitle
  ("続けるにはGoogleアカウントでログインしてください" etc.) is fine, but the
  product name itself is "MJAI".
- **Component library**: shadcn/ui (`new-york` style, `neutral` base color,
  per `components.json`) still provides the underlying primitives, but visual
  styling is driven by MD3 CSS custom properties (see Color Palette in
  `docs/UI-DESIGN.md`), not the old default shadcn blue/indigo theme.
- **Icon library**: **Material Symbols Outlined** (Google Fonts CDN, loaded in
  `layout.tsx`, sized via `.md-18`/`.md-48`-style classes in `globals.css`) —
  **not** Lucide React. Check `globals.css` for the exact size-class
  convention before adding a new icon size.
- **Typography**: Inter (Google Fonts). Explicit `fontWeight` per token in
  `tailwind.config.js` (`headline-lg`: 700, `headline-md`: 600, `body-base`/
  `body-sm`: 400, `metadata`: 500, `label-caps`: 600) — see "Design Iteration
  3: Typography Weight Pass" in `docs/UI-DESIGN.md` for the exact per-element
  weight table (MJAI wordmark bold, active nav tab semibold, inactive nav tab
  normal, card titles semibold, etc.) before changing any font-weight class.
- **Aesthetic**: Brutalist refinement — crisp borders, high-contrast
  black-on-white, flatter surfaces, minimal shadows. **No purple glow or
  generic AI aesthetic**, and no soft `bg-gradient-to-br from-blue-50
  to-indigo-100` background (that was the pre-migration look, now retired —
  see `docs/archive/UI-DESIGN-initial.md` for what NOT to reintroduce).
- **Layout**: TopAppBar (MJAI wordmark, no icon next to it per explicit user
  request, nav tabs for Sessions/Dashboard/Archive, notification bell with a
  shake animation on activity, Google-account avatar) + a **resizable** right
  pane (drag-to-resize, width persisted via `localStorage`,
  `RIGHT_PANE_STORAGE_KEY` in `page.tsx`) — not the old fixed `w-80` sidebar.
  Section headers in the editing pane read **"SOURCE TEXT (原文)"** and
  **"TARGET TEXT (翻訳/編集)"** (English-primary, Japanese in parentheses).
  The generate button reads "Generate AI Suggestions" with a sparkle
  (`auto_awesome`) Material Symbols icon.
- **Login screen** (`frontend/src/app/login-screen.tsx`): "MJAI" wordmark
  (`text-headline-lg`, bold — same convention as the TopAppBar), a sparkle
  (`auto_awesome`) icon (not a file/document icon), and an inline SVG of the
  official 4-color Google "G" logomark on the sign-in button (not a generic
  icon-font glyph — Google's logo has no Material Symbols equivalent).

## Primary Responsibilities

1. **Layout overflow / clipping**
   - Ensure `h-screen` + `flex` containers don't clip content on scroll
   - Main content area must have proper `overflow-auto` with full height
   - Avoid `min-h-screen` conflicts with fixed-height layouts
2. **Resizable right pane**
   - Preserve the drag-to-resize behavior and its `localStorage` persistence
   - Don't regress the pane back to a fixed width
3. **Session start centering**
   - Empty-state "セッションを開始" card centers on wide viewports
   - `flex items-center justify-center` on the empty-state container,
     `max-w-md mx-auto` on the card
4. **Typography weight discipline**
   - Never hardcode an ad-hoc `font-*` class that isn't in the per-element
     weight table in `docs/UI-DESIGN.md`'s Typography Weight Pass section —
     update that table (and the underlying `tailwind.config.js` token) if a
     new element genuinely needs a new weight, rather than sprinkling
     one-off `font-bold`/`font-semibold` classes inconsistently.
5. **Favicon and assets**
   - Next.js App Router: `icon.svg` in `frontend/src/app/`

## Key Files

| File | Purpose |
|---|---|
| `frontend/src/app/page.tsx` | Main app: TopAppBar, resizable right pane, session list, job queue, HITL |
| `frontend/src/app/login-screen.tsx` | Pre-auth login screen (MJAI branding, sparkle icon, Google logo) |
| `frontend/src/app/layout.tsx` | Root layout, `<title>` metadata, font loading (Inter + Material Symbols) |
| `frontend/src/app/globals.css` | MD3 CSS custom properties, Material Symbols size classes, bell-shake animation |
| `frontend/tailwind.config.js` | MD3 color/spacing/typography/radius scale, per-token `fontWeight` |
| `frontend/src/app/icon.svg` | App favicon |
| `docs/UI-DESIGN.md` | **Design token reference — read before any visual change** |
| `docs/archive/UI-DESIGN-initial.md` | Pre-migration design (reference only, do not reintroduce) |

## Layout Pattern (current)

```tsx
// TopAppBar + resizable right-pane pattern (not a fixed w-80 sidebar)
<div className="h-screen flex flex-col">
  <header className="border-b border-outline-variant ...">{/* TopAppBar: wordmark, nav tabs, bell, avatar */}</header>
  <div className="flex-1 flex overflow-hidden">
    <main className="flex-1 overflow-y-auto">{/* session/editing content */}</main>
    <aside style={{ width: rightPaneWidth }} className="border-l border-outline-variant overflow-y-auto">
      {/* drag handle mutates rightPaneWidth + persists to localStorage */}
    </aside>
  </div>
</div>
```

## Japanese/English UI Copy Convention

- **English-primary, Japanese in parentheses** for section labels (e.g.
  "SOURCE TEXT (原文)", "Session" instead of "セッション", "Saved" instead of
  "保存済み") — this is the established convention post-brutalist-refinement;
  follow it for new labels rather than defaulting to Japanese-only.
- Body copy / descriptions / toasts remain Japanese.
- AI-suggestion content itself has its own split rule (backend-owned, not a
  frontend UI-copy concern): `reason`/`overallComment` fields are Chinese
  (target users are Chinese speakers correcting Japanese text), the
  corrected-text field stays Japanese — see `backend/app/llm/prompts.py`.

## Conflict Avoidance

- `page.tsx` is large and frequently has concurrent edits from other
  workstreams (HITL queue, job retry, history archive, draft persistence).
  Prefer additive/targeted changes over restructuring; re-read a section
  immediately before editing it rather than trusting an earlier read in a
  long session.
- Use specific class selectors to avoid overriding other features.

## Minimal Diff Principle

- Edit existing classes rather than wrapping in new divs
- Avoid adding utility classes that don't solve the specific problem
- Test scroll and resize behavior on both mobile and desktop viewports
