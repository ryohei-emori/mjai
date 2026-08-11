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

| Token | Size | Line Height | Letter Spacing | Tailwind Class |
|---|---|---|---|---|
| `headline-lg` | 1.5rem (24px) | 2rem (32px) | 0 | `text-headline-lg` |
| `headline-md` | 1.25rem (20px) | 1.75rem (28px) | 0.0125em | `text-headline-md` |
| `body-base` | 1rem (16px) | 1.5rem (24px) | 0.03125em | `text-body-base` |
| `body-sm` | 0.875rem (14px) | 1.25rem (20px) | 0.025em | `text-body-sm` |
| `metadata` | 0.75rem (12px) | 1rem (16px) | 0.03125em | `text-metadata` |
| `label-caps` | 0.625rem (10px) | 1rem (16px) | 0.1em, 500 weight | `text-label-caps` |

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
│ 🖊 MJAI  │ Sessions │ Dashboard │ Archive │  [+ New]  🔔 ⚙ 👤 🚪 │
└─────────────────────────────────────────────────────────────┘
```

- Height: 64px (`h-16`)
- Background: `bg-surface`
- Border: `border-b border-outline-variant`
- Logo: Material Symbol `edit_note` + "MJAI" text
- Nav tabs: `Sessions` (active), `Dashboard`, `Archive` (Coming Soon)
- Right side: New Session button, notification bell, settings (disabled), avatar, logout

### Three-Pane Layout

Desktop layout below TopAppBar.

```
┌───────────────┬─────────────────────────┬─────────────────┐
│  Left Pane    │     Center Pane         │   Right Pane    │
│  (Sessions)   │     (Editor)            │  (Queue + AI)   │
│               │                         │                 │
│  [Search]     │  ┌─────────────────┐    │  ┌───────────┐  │
│               │  │  Source Text    │    │  │ Job Queue │  │
│  Session 1 ✓  │  └─────────────────┘    │  └───────────┘  │
│  Session 2    │                         │                 │
│  Session 3    │  ┌─────────────────┐    │  ┌───────────┐  │
│               │  │  Target Text    │    │  │ AI提案    │  │
│               │  │                 │    │  │ Option A  │  │
│               │  │   [Generate] ──┼────│  │ Option B  │  │
│               │  └─────────────────┘    │  └───────────┘  │
└───────────────┴─────────────────────────┴─────────────────┘
```

- Left pane: `w-72` fixed width, session list with search
- Center pane: `flex-1`, source + target text cards
- Right pane: `w-96` fixed width, job queue + AI suggestions

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
