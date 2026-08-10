# MJAI — UI Design Document

| Field | Value |
|---|---|
| **Title** | MJAI visual identity (design tokens) |
| **Authors** | MJAI maintainers |
| **Status** | Living document — extracted from codebase |
| **Last updated** | 2026-08-11 |
| **Audience** | UI/frontend contributors |

> **What this document is (and is not)**
>
> This is a **visual-identity / design-token** document inspired by the Google Labs Stitch format. It describes the color palette, typography, spacing, border radii, and component library configuration actually used in the MJAI frontend — extracted from `globals.css`, `tailwind.config.js`, and `components.json`.
>
> **For engineering architecture** (system design, APIs, data model, deployment), see [`docs/SYSTEM-DESIGN.md`](./SYSTEM-DESIGN.md).

---

## Component Library

| Setting | Value | Source |
|---|---|---|
| **Framework** | shadcn/ui (Radix primitives + Tailwind) | `components.json` |
| **Style variant** | `new-york` | `components.json` |
| **Base color** | `neutral` | `components.json` |
| **Icon library** | Lucide React | `components.json` |
| **CSS variables** | Enabled | `components.json` |
| **Dark mode** | Class-based (`darkMode: ["class"]`) | `tailwind.config.js` |

---

## Color Palette

All colors are defined as HSL values (hue, saturation%, lightness%) in CSS custom properties. Tailwind utilities reference these via `hsl(var(--token))`.

### Light Mode (`:root`)

| Token | HSL Value | Description |
|---|---|---|
| `--background` | `0 0% 100%` | Page background (white) |
| `--foreground` | `0 0% 3.9%` | Primary text (near-black) |
| `--card` | `0 0% 100%` | Card surface |
| `--card-foreground` | `0 0% 3.9%` | Card text |
| `--popover` | `0 0% 100%` | Popover/dropdown surface |
| `--popover-foreground` | `0 0% 3.9%` | Popover text |
| `--primary` | `0 0% 9%` | Primary action (dark gray) |
| `--primary-foreground` | `0 0% 98%` | Text on primary (near-white) |
| `--secondary` | `0 0% 96.1%` | Secondary surface (light gray) |
| `--secondary-foreground` | `0 0% 9%` | Secondary text |
| `--muted` | `0 0% 96.1%` | Muted backgrounds |
| `--muted-foreground` | `0 0% 45.1%` | Muted/placeholder text |
| `--accent` | `0 0% 96.1%` | Accent surface |
| `--accent-foreground` | `0 0% 9%` | Accent text |
| `--destructive` | `0 84.2% 60.2%` | Destructive actions (red) |
| `--destructive-foreground` | `0 0% 98%` | Text on destructive |
| `--border` | `0 0% 89.8%` | Border color |
| `--input` | `0 0% 89.8%` | Input field borders |
| `--ring` | `0 0% 3.9%` | Focus ring color |

### Dark Mode (`.dark`)

| Token | HSL Value | Description |
|---|---|---|
| `--background` | `0 0% 3.9%` | Page background (near-black) |
| `--foreground` | `0 0% 98%` | Primary text (near-white) |
| `--card` | `0 0% 3.9%` | Card surface |
| `--card-foreground` | `0 0% 98%` | Card text |
| `--popover` | `0 0% 3.9%` | Popover/dropdown surface |
| `--popover-foreground` | `0 0% 98%` | Popover text |
| `--primary` | `0 0% 98%` | Primary action (inverted) |
| `--primary-foreground` | `0 0% 9%` | Text on primary |
| `--secondary` | `0 0% 14.9%` | Secondary surface |
| `--secondary-foreground` | `0 0% 98%` | Secondary text |
| `--muted` | `0 0% 14.9%` | Muted backgrounds |
| `--muted-foreground` | `0 0% 63.9%` | Muted/placeholder text |
| `--accent` | `0 0% 14.9%` | Accent surface |
| `--accent-foreground` | `0 0% 98%` | Accent text |
| `--destructive` | `0 62.8% 30.6%` | Destructive actions (darker red) |
| `--destructive-foreground` | `0 0% 98%` | Text on destructive |
| `--border` | `0 0% 14.9%` | Border color |
| `--input` | `0 0% 14.9%` | Input field borders |
| `--ring` | `0 0% 83.1%` | Focus ring color |

### Chart Colors

Used for data visualization elements (if applicable).

| Token | Light Mode | Dark Mode |
|---|---|---|
| `--chart-1` | `12 76% 61%` | `220 70% 50%` |
| `--chart-2` | `173 58% 39%` | `160 60% 45%` |
| `--chart-3` | `197 37% 24%` | `30 80% 55%` |
| `--chart-4` | `43 74% 66%` | `280 65% 60%` |
| `--chart-5` | `27 87% 67%` | `340 75% 55%` |

---

## Spacing & Radii

### Border Radius

| Token | Value | Tailwind class |
|---|---|---|
| `--radius` | `0.5rem` (8px) | — |
| `lg` | `var(--radius)` | `rounded-lg` |
| `md` | `calc(var(--radius) - 2px)` | `rounded-md` |
| `sm` | `calc(var(--radius) - 4px)` | `rounded-sm` |

### Spacing Scale

MJAI uses Tailwind's default spacing scale (based on `0.25rem` / 4px increments). No custom spacing tokens are defined.

---

## Typography

MJAI relies on the browser's system font stack via Tailwind defaults. No custom font families are configured in `globals.css` or `tailwind.config.js`.

**Font rendering:**
- `-webkit-font-smoothing: antialiased`
- `-moz-osx-font-smoothing: grayscale`

---

## Application-Specific Patterns

The following patterns are observed in the actual UI components (`page.tsx`, `login-screen.tsx`):

### Page Background

```
bg-gradient-to-br from-blue-50 to-indigo-100
```

A blue-to-indigo gradient used as the main page background for both logged-in and login screens.

### Semantic Colors (via Tailwind utilities)

| Purpose | Classes used |
|---|---|
| Error/destructive feedback | `text-red-600`, `bg-red-50`, `border-red-200` |
| Success feedback | `text-green-600` |
| Info/highlight | `text-blue-600`, `bg-blue-50`, `border-blue-200` |
| Warning | `bg-yellow-50`, `border-yellow-200`, `text-yellow-800` |
| Custom suggestions | `text-purple-600`, `border-purple-200` |
| Neutral muted | `text-gray-500`, `text-gray-400`, `bg-gray-50` |

### Interactive States

- **Hover:** `hover:bg-gray-50`, `hover:opacity-100`
- **Focus:** Uses shadcn/ui focus-ring styles
- **Selected:** `bg-blue-50 border-blue-200`
- **Loading:** `animate-spin` on `Loader2` icon

---

## Source Files

| File | Purpose |
|---|---|
| `frontend/src/app/globals.css` | CSS custom properties (design tokens) |
| `frontend/tailwind.config.js` | Tailwind theme extensions |
| `frontend/components.json` | shadcn/ui component library config |

When updating design tokens, modify these source files first, then update this document to match.
