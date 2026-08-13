# MJAI — UI Design Document

| Field | Value |
|---|---|
| **Title** | MJAI visual identity (MD3-inspired design tokens) |
| **Authors** | MJAI maintainers |
| **Status** | Living document — extracted from codebase |
| **Last updated** | 2026-08-14 |
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
| `--suggestion-highlight` | `6 100% 92%` (`#ffdad6`, DESIGN.md `error-container`) | `bg-suggestion-highlight` | In-textarea marker wash for a flagged AI-suggestion excerpt (SOURCE/TARGET TEXT). Soft MD3 error-container pastel — reads as a highlighter behind glyphs, not a saturated fill. Distinct from solid `--error` (destructive controls) and `--md3-primary` (selected-card). Hover uses `/70`; selected uses full wash + `inset` underline via `--error`. See `HighlightedTextarea`. |

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
- **Notification bell badge**: Count of **completed** jobs in the current session's Job Queue that still await HITL confirm/save (`status === 'completed'`). Does **not** show active (`queued`/`processing`) count — that remains on the Job Queue panel's "N Active" badge.
- **Bell click**: Opens a compact dropdown listing those completed-awaiting-HITL jobs (time, target-text snippet, status). Item click runs the same HITL confirm flow as clicking the job in Job Queue. Empty state when none.

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
│  Session 3    │  ┌─────────────────┐    │  ┌───────────┐  │
│               │  │ EXEMPLAR TEXT   │    │  │ AI Sugg.  │  │
│               │  │ (模範回答訳文)  │    │  │ Option A  │  │
│               │  └─────────────────┘    │  │ Option B  │  │
│               │  ┌─────────────────┐    │  └───────────┘  │
│               │  │ TARGET TEXT     │    │                 │
│               │  │ (翻訳/編集)     │    │  ┌───────────┐  │
│               │  │                 │    │  │ History   │  │
│               │  │ [Generate AI]   │    │  └───────────┘  │
│               │  └─────────────────┘    │                 │
└───────────────┴─────────────────────────┴─────────────────┘
```

- Left pane: `w-72` (288px) fixed width, session list with search
- Center pane: `flex-1`, SOURCE TEXT + EXEMPLAR TEXT + TARGET TEXT cards (English-primary bilingual headers)
- Right pane: Default `448px`, resizable (drag handle between center and right panes, persisted to localStorage)
- Section headers: `text-label-caps` uppercase style, English primary with Japanese in parentheses

### Exemplar Text Card (optional)

`ExemplarTextCard` (`frontend/src/components/ui/exemplar-text-card.tsx`) sits between the SOURCE and TARGET cards and holds an optional 模範回答訳文 — a known-good translation of the source that the AI uses only to calibrate expected meaning and register.

- Same card chrome as SOURCE/TARGET: `bg-surface`, `border-outline-variant`, `shadow-none`, `text-label-caps` header, copy button.
- Header carries an inline `任意` marker in `text-metadata` at `text-on-surface-variant/70`, so "optional" reads from the header rather than from a tooltip.
- Plain `Textarea` at `min-h-[140px]` (shorter than SOURCE's 180px and TARGET's 200px, since it is supplementary). Deliberately **not** `HighlightedTextarea`: suggestion spans only ever point at SOURCE and TARGET excerpts.
- Never gates the generate button — that stays governed by non-blank SOURCE + TARGET.
- Lives in its own component file because it is slated to become collapsible; a collapse wrapper goes around the component rather than into `page.tsx`.

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

### Job Queue Carousel (horizontal slide)

The Job Queue panel in the right pane presents jobs as a **horizontally sliding track**, not a vertical stack. With up to 30 concurrent API jobs a vertical list grew without bound and pushed AI Suggestions / History off-screen; the carousel keeps the panel at a constant height regardless of job count (OpenSpec change `slide-job-queue-carousel`).

```
┌──────────────────────────────────────────────┐
│ JOB QUEUE                        [3 Active]  │
│ APIモード: 並列処理（最大30件同時）…            │
│ 横スライドで他のジョブを表示           ‹  ›   │
│ ┌────────────┬────────────┬──┐              │
│ │ ⟳ 処理中   │ ✓ 完了     │▒▒│ ← peek + fade │
│ │ 翻訳文…    │ 翻訳文…    │  │              │
│ │ 09:12      │ 09:10→09:11│  │              │
│ │            │ ✓ 確認     │  │              │
│ └────────────┴────────────┴──┘              │
│ ▬ ○ ○                        ← page dots    │
└──────────────────────────────────────────────┘
```

**Ordering** (shared helper `frontend/src/lib/jobQueue/ordering.ts`, so the TopAppBar bell list cannot drift from the queue): `processing` → `queued` → `completed` → `failed`, and newest-first within each group using `completedAt ?? queuedAt`. The leftmost card is therefore always the job the user most likely needs — running work first, then the freshly completed job awaiting HITL confirm.

**Affordance stack** — four redundant cues, all suppressed when the track does not overflow (a 1-job queue looks exactly as it did before):

| Cue | Implementation |
|---|---|
| Arrow buttons | `chevron_left` / `chevron_right` at `md-20`, `rounded-full` with `hover:bg-surface-container` (same icon-button pattern as the TopAppBar), `disabled` + `opacity-50` at each end |
| Hint text | `text-metadata text-on-surface-variant` — 「横スライドで他のジョブを表示」 |
| Page indicator | `h-1.5 rounded-full` dots, active `w-4 bg-md3-primary` / inactive `w-1.5 bg-outline-variant`; switches to `N / M` `text-metadata` past 6 pages |
| Edge fade + peek | `w-6` `bg-gradient-to-r/l from-surface to-transparent`, `pointer-events-none`, rendered only on the side that has more content; card widths reserve 28px so the next card peeks in |

The track keeps a **visible thin native scrollbar** (`.job-carousel-track` in `globals.css`, styled with `--outline-variant` / `--outline`) — deliberately not `.no-scrollbar`, since a scrollbar is the most universally understood "this scrolls" signal. Movement uses CSS `scroll-snap-type: x mandatory` with `scroll-snap-align: start` per card, so wheel/trackpad/touch swipe all settle card-aligned. `overscroll-behavior-x: contain` keeps a trackpad swipe from triggering browser back-navigation.

**Responsive cards-per-view.** The right pane is user-resizable (280–600px), which media queries cannot observe, so the count is measured with a `ResizeObserver` on the track: `clamp(floor(trackWidth / 230), 1, 3)`. It falls back to 1 card where `ResizeObserver` is unavailable (older Safari, SSR, jsdom). Panel and card padding take roughly 84px out of the pane width before the track sees it.

| Right pane width | Track width | Cards per view |
|---|---|---|
| 280px (minimum) | ~196px | 1 |
| 448px (default) | ~364px | 1 |
| ~544–600px (maximum) | ~460–516px | 2 (~240px each) |
| Full-width mobile / very wide | ≥ ~720px | 3 (capped) |

**Accessibility.** The track is `role="group"` with `aria-label="ジョブキュー一覧（横スライド）"` and `tabIndex={0}`; `ArrowLeft`/`ArrowRight` slide it while focus is inside, except when the event came from an `input`/`textarea`/contenteditable (the page's textareas must keep their caret keys). Arrows carry `aria-label="前のジョブへ"` / `"次のジョブへ"`. Interactive elements use `focus-visible:ring-2 focus-visible:ring-md3-primary`. Completed job cards keep their existing `role="button"` / `tabIndex={0}` / Enter-Space HITL confirm behaviour, and the browser scrolls a Tab-focused off-screen card into view.

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
- **Text-span highlighting** (2026-08): hovering a card previews (and selecting a card persists) a highlight of the card's flagged excerpt inside the actual SOURCE TEXT and TARGET TEXT textareas, using the `--suggestion-highlight` token (see Core Tokens table above). Implemented via `HighlightedTextarea`, a non-interactive overlay layered behind the native `<textarea>` — see `docs/SYSTEM-DESIGN.md` / `openspec/changes/highlight-suggestion-text-spans/design.md` for the technique.

### Confirm / Save Button Loading

"確定してコピー・保存" (`saveCorrections`):

- While in flight (`isSaving`): button **disabled**; leading icon is Material Symbols `progress_activity` with Tailwind `animate-spin` (same ぐるぐる pattern as job `processing` / LATEST live timer). A static `progress_activity` glyph without spin is not allowed.
- Label while waiting: `保存中...`
- Interaction: clipboard copy + local UI commit run first; server history/proposal persistence continues in the background with separate success/failure toasts (see OpenSpec change `async-confirm-copy-background-save`).

### Bell Shake Animation

CSS animation triggered when a job **completes** (transitions to `completed` / badge would increase). Not triggered on enqueue or when a job merely enters `processing`.

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
| Exemplar card header | (did not exist) | EXEMPLAR TEXT (模範回答訳文) + `任意` |
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
| Job Queue "N Active" badge | `font-medium` | `font-semibold` | Stronger emphasis for in-flight queue count (not the TopAppBar bell) |
| TopAppBar bell badge | `font-medium` | `font-medium` (500) | Completed-awaiting-HITL count; keep medium weight for compact badge |
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
