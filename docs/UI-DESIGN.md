# MJAI — UI Design Document

| Field | Value |
|---|---|
| **Title** | MJAI visual identity (MD3-inspired design tokens) |
| **Authors** | MJAI maintainers |
| **Status** | Living document — extracted from codebase |
| **Last updated** | 2026-08-11 |
| **Audience** | UI/frontend contributors |

> **What this document is (and is not)**
>
> This is a **visual-identity / design-token** document describing the Material Design 3-inspired color palette, typography scale, spacing, border radii, and component patterns used in the MJAI frontend.
>
> **For engineering architecture** (system design, APIs, data model, deployment), see [`docs/SYSTEM-DESIGN.md`](./SYSTEM-DESIGN.md).
>
> **For the original pre-migration design tokens**, see [`docs/archive/UI-DESIGN-initial.md`](./archive/UI-DESIGN-initial.md).

---

## Component Library

| Setting | Value | Source |
|---|---|---|
| **Framework** | shadcn/ui (Radix primitives + Tailwind) | `components.json` |
| **Style variant** | `new-york` | `components.json` |
| **Base color** | `neutral` | `components.json` |
| **Icon library** | Material Symbols Outlined (Google Fonts CDN) | `layout.tsx` |
| **Typography** | Inter (Google Fonts) | `layout.tsx` |
| **CSS variables** | Enabled | `components.json` |
| **Dark mode** | Class-based (`darkMode: ["class"]`) | `tailwind.config.js` |

---

## Color Palette

All colors are defined as HSL values in CSS custom properties. Tailwind utilities reference these via `hsl(var(--token))`.

### Core Tokens (Light Mode `:root`)

| Token | HSL Value | Tailwind Class | Description |
|---|---|---|---|
| `--background` | `0 0% 100%` | `bg-background` | Page background |
| `--foreground` | `0 0% 3.9%` | `text-foreground` | Primary text |
| `--surface` | `0 0% 100%` | `bg-surface` | Surface background |
| `--surface-container` | `220 14% 96%` | `bg-surface-container` | Elevated container |
| `--surface-container-low` | `220 14% 97%` | `bg-surface-container-low` | Low-emphasis container |
| `--surface-container-lowest` | `0 0% 100%` | `bg-surface-container-lowest` | Lowest-emphasis surface |
| `--surface-container-high` | `220 14% 94%` | `bg-surface-container-high` | High-emphasis container |
| `--surface-container-highest` | `220 14% 92%` | `bg-surface-container-highest` | Highest-emphasis container |
| `--on-surface` | `220 9% 12%` | `text-on-surface` | Text on surface |
| `--on-surface-variant` | `220 9% 35%` | `text-on-surface-variant` | Secondary text on surface |
| `--outline` | `220 9% 75%` | `border-outline` | Border color |
| `--outline-variant` | `220 14% 88%` | `border-outline-variant` | Subtle border color |
| `--md3-primary` | `220 70% 50%` | `bg-md3-primary` | Primary action color |
| `--on-primary` | `0 0% 100%` | `text-on-primary` | Text on primary |
| `--primary-container` | `220 70% 95%` | `bg-primary-container` | Primary container |
| `--on-primary-container` | `220 70% 20%` | `text-on-primary-container` | Text on primary container |
| `--error` | `0 84% 60%` | `bg-error` | Error color |
| `--on-error` | `0 0% 100%` | `text-on-error` | Text on error |
| `--tertiary` | `280 50% 45%` | `bg-tertiary` | Tertiary accent |
| `--on-tertiary` | `0 0% 100%` | `text-on-tertiary` | Text on tertiary |

### Session Status Colors

| Token | Hex Value | Tailwind Class | Usage |
|---|---|---|---|
| `session-active` | `#2563EB` | `bg-session-active` | Active/processing sessions |
| `session-complete` | `#16A34A` | `bg-session-complete` | Completed items (green) |
| `session-empty` | `#64748B` | `bg-session-empty` | Draft/empty states (gray) |

### Legacy Tokens (shadcn/ui compatibility)

The following tokens are retained for backward compatibility with shadcn/ui components:

| Token | Description |
|---|---|
| `--card`, `--card-foreground` | Card surface/text |
| `--popover`, `--popover-foreground` | Popover surface/text |
| `--primary`, `--primary-foreground` | Primary button (dark gray) |
| `--secondary`, `--secondary-foreground` | Secondary surfaces |
| `--muted`, `--muted-foreground` | Muted backgrounds/text |
| `--accent`, `--accent-foreground` | Accent surfaces |
| `--destructive`, `--destructive-foreground` | Destructive actions |
| `--border`, `--input`, `--ring` | Border/input/focus ring |

---

## Typography

MJAI uses Inter font with a custom typography scale.

### Font Stack

```css
font-family: var(--font-inter), system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### Typography Scale

| Token | Size | Weight | Line Height | Letter Spacing | Tailwind Class |
|---|---|---|---|---|---|
| `headline-lg` | 1.5rem (24px) | 700 (bold) | 2rem (32px) | 0 | `text-headline-lg` |
| `headline-md` | 1.25rem (20px) | 600 (semibold) | 1.75rem (28px) | 0.0125em | `text-headline-md` |
| `body-base` | 1rem (16px) | 400 (normal) | 1.5rem (24px) | 0.03125em | `text-body-base` |
| `body-sm` | 0.875rem (14px) | 400 (normal) | 1.25rem (20px) | 0.025em | `text-body-sm` |
| `metadata` | 0.75rem (12px) | 500 (medium) | 1rem (16px) | 0.03125em | `text-metadata` |
| `label-caps` | 0.625rem (10px) | 600 (semibold) | 1rem (16px) | 0.1em | `text-label-caps` |

> **Note**: All typography tokens include explicit `fontWeight` values in `tailwind.config.js`. The typography classes apply both size and weight automatically.

### Font Rendering

```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

---

## Spacing & Radii

### Named Spacing Tokens

| Token | Value | Tailwind Class | Usage |
|---|---|---|---|
| `container-margin` | 1.5rem (24px) | `p-container-margin` | Outer container margins |
| `card-gap` | 1.25rem (20px) | `gap-card-gap` | Gap between cards |
| `gutter` | 1rem (16px) | `p-gutter` | Inner padding |
| `section` | 2rem (32px) | `p-section` | Section padding |
| `topappbar` | 4rem (64px) | `pt-topappbar` | TopAppBar height offset |

### Border Radius Scale

| Token | Value | Tailwind Class |
|---|---|---|
| `DEFAULT` | 0.25rem (4px) | `rounded` |
| `lg` | 0.5rem (8px) | `rounded-lg` |
| `xl` | 0.75rem (12px) | `rounded-xl` |
| `full` | 9999px | `rounded-full` |

---

## Icon System

MJAI uses Material Symbols Outlined icons loaded from Google Fonts CDN.

### Icon Font Link

```html
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet" />
```

### Icon Usage

```jsx
<span className="material-symbols-outlined md-24">icon_name</span>
```

### Size Classes

| Class | Size |
|---|---|
| `md-18` | 18px |
| `md-20` | 20px |
| `md-24` | 24px (default) |
| `md-36` | 36px |
| `md-40` | 40px |
| `md-48` | 48px |

### Common Icons Used

| Purpose | Icon Name |
|---|---|
| Logo/Edit | `edit_note` |
| Add/New | `add` |
| Session/Document | `description` |
| Calendar | `calendar_today` |
| Delete | `delete` |
| AI/Bot | `smart_toy` |
| Copy | `content_copy` |
| Checkmark | `check_circle` |
| Progress/Loading | `progress_activity` |
| Queue | `queue` |
| History | `history` |
| Chat/Comment | `chat` |
| Notifications | `notifications` |
| Settings | `settings` |
| Logout | `logout` |
| Account | `account_circle` |
| Error | `error` |
| Schedule | `schedule` |
| Construction | `construction` |
| Article | `article` |
| Edit Document | `edit_document` |
| Menu | `menu` |

---

## Application-Specific Patterns

### TopAppBar

Fixed header with navigation tabs and user controls.

```
┌─────────────────────────────────────────────────────────────┐
│ MJAI  │ Sessions │ Dashboard │ Archive │  [+ New]  🔔 ⚙ 👤 🚪 │
└─────────────────────────────────────────────────────────────┘
```

- Height: 64px (`h-16`)
- Background: `bg-surface`
- Border: `border-b border-outline-variant`
- Logo: "MJAI" text wordmark only (no icon)
- Nav tabs: `Sessions` (active), `Dashboard`, `Archive` (Coming Soon)
- Right side: New Session button, notification bell, settings (disabled), avatar, logout

### Three-Pane Layout

Desktop layout below TopAppBar. Right pane is user-resizable.

```
┌───────────────┬─────────────────────────┼─────────────────┐
│  Left Pane    │     Center Pane         │   Right Pane    │
│  (Sessions)   │     (Editor)            │  (Queue + AI)   │
│               │                         │ ← resizable →   │
│  [Search]     │  ┌─────────────────┐    │  ┌───────────┐  │
│               │  │ SOURCE TEXT     │    │  │ Job Queue │  │
│  Session 1 ✓  │  │ (原文)          │    │  └───────────┘  │
│  Session 2    │  └─────────────────┘    │                 │
│  Session 3    │                         │  ┌───────────┐  │
│               │  ┌─────────────────┐    │  │ AI Sugg.  │  │
│               │  │ TARGET TEXT     │    │  │ Option A  │  │
│               │  │ (翻訳/編集)     │    │  │ Option B  │  │
│               │  │                 │    │  └───────────┘  │
│               │  │ [Generate AI]   │    │                 │
│               │  └─────────────────┘    │  ┌───────────┐  │
│               │                         │  │ History   │  │
└───────────────┴─────────────────────────┴─────────────────┘
```

- Left pane: `w-72` (288px) fixed width, session list with search
- Center pane: `flex-1`, SOURCE TEXT + TARGET TEXT cards (English-primary bilingual headers)
- Right pane: Default `448px`, resizable (drag handle between center and right panes, persisted to localStorage)
- Section headers: `text-label-caps` uppercase style, English primary with Japanese in parentheses

### Session Card

```
┌────────────────────────────────────────┐
│ 📄 Session Name                    🗑  │
│    📅 2024-01-15                       │
│    [5 Saved] or [Draft]                │
└────────────────────────────────────────┘
```

- Active: `bg-primary-container border-md3-primary`
- Inactive: `border-outline-variant hover:bg-surface-container`
- Status pill: `bg-session-complete` (saved) / `bg-session-empty` (draft)

### AI Suggestion Card

```
┌────────────────────────────────────────┐
│ ☐ OPTION A                       📋 ✓ │
│ ┌──────────────────────────────────┐   │
│ │ 指摘箇所: "修正前テキスト"         │   │
│ └──────────────────────────────────┘   │
│ ┌──────────────────────────────────┐   │
│ │ 修正コメント: "修正理由..."        │   │
│ └──────────────────────────────────┘   │
└────────────────────────────────────────┘
```

- Label: `text-label-caps` with Option A/B/C...
- Selected: `bg-primary-container border-md3-primary`
- Hover: reveals copy/confirm icons

### Bell Shake Animation

CSS animation triggered on job completion.

```css
@keyframes bell-shake {
  0%, 100% { transform: rotate(0deg); }
  10% { transform: rotate(-15deg); }
  20% { transform: rotate(15deg); }
  /* ... */
}

.bell-shake {
  animation: bell-shake 0.6s ease-in-out;
}
```

---

## Mobile Responsive Behavior

At breakpoints below `lg` (1024px):

- TopAppBar remains visible
- Left pane (session list) becomes a slide-out Sheet (triggered by menu button)
- Center and right panes stack vertically
- New Session button becomes icon-only

---

## Source Files

| File | Purpose |
|---|---|
| `frontend/src/app/globals.css` | CSS custom properties (design tokens) |
| `frontend/tailwind.config.js` | Tailwind theme extensions |
| `frontend/src/app/layout.tsx` | Font loading (Inter, Material Symbols) |
| `frontend/components.json` | shadcn/ui component library config |

When updating design tokens, modify these source files first, then update this document to match.

---

## Design Iteration 2: Brutalist Refinement (2026-08-11)

This section documents visual refinements applied after the initial MD3 migration, based on user feedback to align with the original mockup's "brutalist legibility" aesthetic.

### Changes Applied

| Element | Before | After |
|---------|--------|-------|
| MJAI logo | `edit_note` icon + "MJAI" text | "MJAI" text wordmark only |
| Source card header | 原文テキスト | SOURCE TEXT (原文) |
| Target card header | 添削対象テキスト | TARGET TEXT (翻訳/編集) |
| Generate button | `smart_toy` + "AI提案を生成" | `auto_awesome` + "Generate AI Suggestions" |
| Right pane width | `w-96` (384px) fixed | 448px default, resizable (280-600px range) |
| Card borders | Soft shadows | Crisp 1px `border-outline-variant`, `shadow-none` |
| Header style | `text-headline-md` with icons | `text-label-caps` uppercase, no icons |

### Visual Direction

- **Brutalist legibility**: High contrast black-on-white text, minimal shadows, crisp borders
- **English-primary bilingual**: English labels with Japanese in parentheses
- **Functional density**: Compact headers with uppercase label style
- **User control**: Resizable right pane for personalized workspace layout

---

## Design Iteration 3: Typography Weight Pass (2026-08-11)

Refinement focused specifically on font-weight to match the reference mockup more precisely.

### Changes Applied

| Element | Before | After | Rationale |
|---------|--------|-------|-----------|
| MJAI wordmark | `text-headline-md font-semibold` (20px/600) | `text-headline-lg` (24px/700) | Mockup shows bold, heavy wordmark |
| Nav tabs (active) | `font-medium` (500) | `font-semibold` (600) | Active tab needs visual emphasis |
| Nav tabs (inactive) | `font-medium` (500) | `font-normal` (400) | Lighter weight for inactive state |
| Session header | `text-headline-lg font-semibold` | `text-headline-lg` | Redundant weight removed (built-in 700) |
| Session card title | `font-medium` (500) | `font-semibold` (600) | Mockup shows semibold titles |
| Status badges | (no weight) | `font-medium` (500) | Consistent badge weight |
| "N Active" badge | `font-medium` | `font-semibold` | Stronger emphasis for active count |
| History card title | `font-medium` | `font-semibold` | Consistent with session cards |

### Typography Token Weights (Updated)

All typography tokens in `tailwind.config.js` now include explicit `fontWeight`:

| Token | Weight |
|-------|--------|
| `headline-lg` | 700 (bold) |
| `headline-md` | 600 (semibold) |
| `body-base` | 400 (normal) |
| `body-sm` | 400 (normal) |
| `metadata` | 500 (medium) |
| `label-caps` | 600 (semibold) |

> **Note on `label-caps`**: The original DESIGN.md specified 700, but the reference mockup's section labels ("SOURCE TEXT", etc.) appear lighter. We use 600 as a compromise for functional legibility without excessive boldness.
