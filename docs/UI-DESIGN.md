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

**Emphasising a control uses a scale token, not a new size.** The wide-viewport New Session button pairs `text-body-base` (16px) with `font-semibold`, overriding the `size="sm"` default so the primary action in the TopAppBar reads as primary. The token supplies weight 400, so the explicit `font-semibold` is what carries the emphasis — keep both. Below `sm` the button is icon-only and the pairing does not apply.

### Custom Scale Values Must Be Registered With `tailwind-merge`

Every token in the table above lives under `theme.extend` in `tailwind.config.js`, which Tailwind understands and `tailwind-merge` does not. An unrecognised `text-*` value falls through to the **colour** group, so `cn("text-on-primary", "text-body-base")` resolves as two colours and keeps only the last — dropping the colour and leaving the element on the default body foreground. That is what turned the New Session button's `add` icon and label black once `text-body-base` was added beside `text-on-primary`.

`frontend/src/lib/utils.ts` therefore builds `cn` with `extendTailwindMerge`, declaring the custom `text` (typography) and `spacing` scales. **Adding a value to either scale in `tailwind.config.js` means adding it there too**, or it silently merges as a colour again. `frontend/src/lib/__tests__/classMerge.test.ts` guards the pairing.

Consequences worth knowing:

- A token composed with a colour now keeps both, so `text-<token> text-<colour>` is the normal way to write it — no inline `style` colour is needed to protect the size. The two inline colours in `highlighted-textarea.tsx` remain for a different reason (the backdrop layer needs a transparent textarea colour, not a utility).
- A token now correctly displaces the base size it was meant to override: `CardTitle`/`CardDescription`, `Label` and `Button` call sites that pass a scale token render at that token's size and line height rather than the shadcn default.

**Colour on a filled control is part of the variant's pairing.** A filled button carries its background and its foreground together — `bg-md3-primary text-on-primary` — and Material Symbols icons inside it inherit that `color`, so the icon needs no colour class of its own. Never leave a filled surface without an explicit `text-on-*`: the shadcn `default` variant's `text-primary-foreground` is displaced by any `text-*` the call site passes.

### UI Language

**Chrome is English**; content is not. Labels, buttons, placeholders, badges, `aria-label`s, tooltips, toasts and empty states are English throughout (OpenSpec change `english-ui-labels-and-chrome-polish`). Three categories are deliberately excluded and must stay as they are:

- **AI critique output** — `reason` / `overallComment` are Simplified Chinese by prompt design.
- **User input** — source, target and exemplar text, and session names.
- **Prompt and parser internals** — the prompt section headers in `webllm/prompts/templates.ts`, `instructionPrompt`, and the `抽出できませんでした` parser sentinel `page.tsx` matches on. These are protocol, not copy; translating them changes model behaviour or silently breaks a match.

Japanese code comments are unaffected — they document intent for maintainers rather than address the user.

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
│ ☰ MJAI │ Sessions │ Dashboard │ Archive │ [+ New]  🔔 ⚙ 👤 🚪 │
└─────────────────────────────────────────────────────────────┘
```

- Height: 64px (`h-16`)
- Background: `bg-surface`
- Border: `border-b border-outline-variant`
- Leftmost: session pane trigger (`☰`) — see "Session pane: docked ⇄ floating"
- Logo: "MJAI" text wordmark only (no icon)
- Nav tabs: `Sessions` (active), `Dashboard`, `Archive` (Coming Soon)
- Right side: New Session button, notification bell, settings (opens the prompt settings dialog), avatar, logout
- **Notification bell badge**: Count of **completed** jobs in the current session's Job Queue that still await HITL confirm/save (`status === 'completed'`). Does **not** show active (`queued`/`processing`) count — that remains on the Job Queue panel's "N Active" badge.
- **Bell click**: Opens a compact dropdown listing those completed-awaiting-HITL jobs (time, target-text snippet, status). Item click runs the same HITL confirm flow as clicking the job in Job Queue. Empty state when none.

### Three-Pane Layout

Desktop layout below TopAppBar. Right pane is user-resizable; the left pane can be docked or floated.

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

- Left pane: `w-72` (288px) fixed width, session list with search — **docked or floating**, see below
- Center pane: `flex-1`, SOURCE TEXT + EXEMPLAR TEXT + TARGET TEXT cards (English-primary bilingual headers)
- Right pane: Default `448px`, resizable (drag handle between center and right panes, persisted to localStorage)
- Section headers: `text-label-caps` uppercase style, English primary with Japanese in parentheses

#### Session pane: docked ⇄ floating

The session list is either **docked** (the `w-72` column above) or **floating** (an overlay `Sheet`, with the column removed from the layout so the center pane absorbs its full 288px). This exists so the two panes where work actually happens are not permanently squeezed by chrome the user only touches when switching sessions (OpenSpec change `floating-session-pane-and-collapsible-panels`).

```
docked (lg+)                          floating (any width)
┌──────┬─────────┬────────┐           ┌────────────────┬────────┐
│ ☰ …  │         │        │           │ ☰ …            │        │
├──────┼─────────┼────────┤    ☰ →    ├────────────────┼────────┤
│ Sess │ Editor  │ Queue  │    ← ⊐    │ Editor (wider) │ Queue  │
│ list │         │ + AI   │           │                │ + AI   │
└──────┴─────────┴────────┘           └────────────────┴────────┘
```

| Control | Placement | Behavior |
|---|---|---|
| Session pane trigger | **Leftmost item in the TopAppBar**, before the `MJAI` wordmark. Same icon-button pattern as the bell / logout (`p-2 rounded-full hover:bg-surface-container`, `md-24 text-on-surface-variant`), plus `focus-visible:ring-2 focus-visible:ring-md3-primary` | `menu` / `menu_open` glyph. Docked → floats the pane (widening the work area). Floating → opens/closes the overlay. State-specific `aria-label`; `aria-expanded` is true whenever the list is visible |
| Dock button | Inside the floating panel header, left of the Sheet's close `X` (`lg`+ only) | `dock_to_left` at `md-20`. Returns the list to the docked column and closes the overlay |

- **Modality**: the floating panel is the existing `Sheet` (Radix Dialog), so backdrop click, `Escape`, focus trapping, and focus restore to the trigger come for free. Selecting a session closes it.
- **`docked` is clamped to `lg`+**: below `lg` the pane always renders floating, without overwriting a stored `docked` preference — widening the window restores docking.
- **Persistence**: `mjai-session-pane-mode` (`"docked"` / `"floating"`) in `localStorage`, same flat `mjai-…` naming as `mjai-right-pane-width`. First visit defaults by viewport (docked at `lg`+, floating below). Unreadable or malformed values fall back to that default. Read in a mount effect, never during render, so SSR and first client render agree.
- The docked column and the floating panel render from **one shared list renderer** in `page.tsx` — previously the same markup was duplicated in both places.
- The former `fixed bottom-4 left-4` mobile-only menu FAB is gone; the TopAppBar trigger replaces it at every width.

### Exemplar Text Card (optional)

`ExemplarTextCard` (`frontend/src/components/ui/exemplar-text-card.tsx`) sits between the SOURCE and TARGET cards and holds an optional 模範回答訳文 — a known-good translation of the source that the AI uses only to calibrate expected meaning and register.

- Same card chrome as SOURCE/TARGET: `bg-surface`, `border-outline-variant`, `shadow-none`, `text-label-caps` header, copy button.
- Header carries an inline `任意` marker in `text-metadata` at `text-on-surface-variant/70`, so "optional" reads from the header rather than from a tooltip.
- Plain `Textarea` at `min-h-[140px]` (shorter than SOURCE's 180px and TARGET's 200px, since it is supplementary). Deliberately **not** `HighlightedTextarea`: suggestion spans only ever point at SOURCE and TARGET excerpts.
- Never gates the generate button — that stays governed by non-blank SOURCE + TARGET.

**Collapsible, collapsed by default.** The exemplar is fixed per exercise and rarely needs re-reading, so a permanently expanded textarea only pushed TARGET TEXT and the generate button down the center pane.

```
collapsed                                        expanded
┌──────────────────────────────────────────┐     ┌──────────────────────────┐
│ ⌄ EXEMPLAR TEXT (模範回答訳文) 任意        │     │ ⌃ EXEMPLAR TEXT … 任意 📋│
│   [入力あり] 15文字                    📋 │     │ ┌──────────────────────┐ │
└──────────────────────────────────────────┘     │ │ (textarea)           │ │
                                                 │ └──────────────────────┘ │
                                                 └──────────────────────────┘
```

- **Disclosure control**: the header row is a `button` with `aria-expanded` and `aria-controls`, carrying an `expand_more` glyph at `md-18` that flips via the existing `transition-transform` + `rotate-180`. The copy button stays **outside** that button so it remains independently clickable while collapsed.
- **No height animation**: the textarea is conditionally rendered, not CSS-hidden — matching every other disclosure in this codebase (`showCustomForm`, the bell panel) and keeping the field out of the tab order while collapsed. There is no collapse-transition token in this document to draw on.
- **Content indicator**: when collapsed and non-blank, the header shows a `Filled` `Badge` in the existing `bg-session-complete text-white` pair plus a `N chars` count in `text-metadata text-on-surface-variant`, so entered text is never silently hidden. Both disappear when expanded, where the text speaks for itself.
- **Padding**: `CardHeader` keeps its `pb-3` override only while expanded; collapsed it falls back to the default symmetric `p-6`.
- **Persistence**: `mjai-exemplar-card-open` (`"1"` / `"0"`) in `localStorage`. Anything else, including unreadable storage, reads as collapsed. Collapsing never touches the value, its per-session draft persistence, or its inclusion in generation.

### Scroll Surfaces

Scrollbars are chrome and follow the outline tokens like every other rule and rail. Three things make this non-obvious, and all three are load-bearing:

1. **`html { color-scheme: light }`, unconditionally** (`globals.css`). `darkMode: ["class"]` and the `.dark` token block exist for shadcn compatibility, but nothing ever applies that class. The previous `@media (prefers-color-scheme: dark)` rule therefore told the browser to paint UA surfaces — **scrollbars above all** — for a dark UI that never renders, which is why they came out black inside a light app. Do not reintroduce the media query without a real dark theme.
2. **`::-webkit-scrollbar*`, not `scrollbar-color`.** The standard property sends Chrome back to macOS overlay scrollbars, which hides the rail the carousel deliberately shows. Both utilities use the `-webkit-` route so the whole app has one mechanism rather than two that disagree on the same machine. Firefox keeps its own scrollbar, now light.

| Utility | Applied to | Rail |
|---|---|---|
| `.job-carousel-track` | Job Queue carousel track only | Hairline — a row of cards, always visible as a "this scrolls" cue. **Does not set `scrollbar-width: thin`**, on purpose |
| `.token-scrollbar` | Editor pane, review pane, bell notification list | `10px`, thumb `--outline-variant` → `--outline` on hover, `border: 2px solid transparent` + `background-clip: content-box` to inset the thumb without shrinking its hit area |

3. **Radix `ScrollArea`** (session list) hides the native scrollbar and draws its own thumb, so neither utility reaches it. Its thumb is `bg-outline-variant hover:bg-outline` — not the legacy shadcn `bg-border`.

### Badges Are Readouts, Not Controls

`Badge` carries no `onClick` anywhere in this app. shadcn's variants ship a `hover:bg-*/80`, and with `--primary` at `0 0% 9%` that turned the timing, count and status badges near-black under the cursor while promising an interaction that does not exist. Those hover backgrounds are **removed from `badgeVariants`** rather than from call sites: a call site passing its own `bg-…` overrides the base colour through `tailwind-merge` but not the `hover:` variant, which lives in a different modifier group.

`transition-colors` stays — badges whose colour tracks state (the LATEST review timer moving between live, paused and completed) still need it. An intentionally clickable badge must ask for hover explicitly.

The same rule applies to the non-interactive timing readouts (`628.0s`, `AVG`, `—`): no hover background and no `cursor: pointer`. Genuinely interactive surfaces — job cards, suggestion cards, session entries, notification rows — keep theirs.

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
│ API mode: up to 30 generations in parallel   │
│ Slide sideways for more jobs           ‹  ›   │
│ ┌────────────┬────────────┬──┐              │
│ │ ⟳ Processing│ ✓ Completed│▒▒│ ← peek+fade  │
│ │ 翻訳文…    │ 翻訳文…    │  │              │
│ │ 09:12      │ 09:10→09:11│  │              │
│ │            │ ✓ Review   │  │              │
│ └────────────┴────────────┴──┘              │
│ ▬ ○ ○                        ← page dots    │
└──────────────────────────────────────────────┘
```

**Ordering** (shared helper `frontend/src/lib/jobQueue/ordering.ts`, so the TopAppBar bell list cannot drift from the queue): `processing` → `queued` → `completed` → `failed`, and newest-first within each group using `completedAt ?? queuedAt`. The leftmost card is therefore always the job the user most likely needs — running work first, then the freshly completed job awaiting HITL confirm.

**Affordance stack** — four redundant cues, all suppressed when the track does not overflow (a 1-job queue looks exactly as it did before):

| Cue | Implementation |
|---|---|
| Arrow buttons | `chevron_left` / `chevron_right` at `md-20`, `rounded-full` with `hover:bg-surface-container` (same icon-button pattern as the TopAppBar), `disabled` + `opacity-50` at each end |
| Hint text | `text-metadata text-on-surface-variant` — `Slide sideways for more jobs` |
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

**Accessibility.** The track is `role="group"` with `aria-label="Job queue (slides horizontally)"` and `tabIndex={0}`; `ArrowLeft`/`ArrowRight` slide it while focus is inside, except when the event came from an `input`/`textarea`/contenteditable (the page's textareas must keep their caret keys). Arrows carry `aria-label="Previous jobs"` / `"Next jobs"`. Interactive elements use `focus-visible:ring-2 focus-visible:ring-md3-primary`. Completed job cards keep their existing `role="button"` / `tabIndex={0}` / Enter-Space HITL confirm behaviour, and the browser scrolls a Tab-focused off-screen card into view.

### Correction Label (shared card headings)

Three surfaces need a one-line label that says *which* correction round a card is: the **History** card heading, the **Job Queue** card preview, and the **TopAppBar bell** notification row. All three derive it from the same pure helper `frontend/src/lib/correctionLabel.ts` (OpenSpec change `identifiable-history-card-headings`), the same way ordering lives once in `jobQueue/ordering.ts`. Previously the queue and the bell each inlined `targetText.slice(0, 40)` and History had no preview at all — its heading was the bare sequence number `添削データ #1`, which made two rounds indistinguishable without opening them.

**Derivation rule** — reads the round's target text, falling back to its source text when the target is blank:

| Case | Label |
|---|---|
| First non-blank line is **title-like** — ≤ 30 characters, followed by more content, not ending in `。．.!！?？…、，,;；:：` | that line verbatim, **no** ellipsis |
| Anything else | whitespace-collapsed excerpt from the start of the text, cut at 30 characters, `…` appended only when characters were actually dropped |
| Target and source both blank/whitespace-only | `(空のテキスト)` |

Truncation counts **code points** (`Array.from`, not `slice`) so a label never ends in a broken surrogate pair and the 30-character budget means the same thing for Japanese, Chinese, and mixed text. Newlines and full-width spaces collapse to single spaces, so a multi-paragraph corpus still reads as one line.

The 30-character budget is set by the tightest consumer: the History heading is `text-body-sm` sharing its row with a badge, so anything longer is clipped by CSS regardless. `…` (U+2026) replaces the old hand-rolled `'...'` — one character instead of three, and it reads as elision rather than as part of the text.

**History card layout.** The label is the heading; the sequence number demotes to the metadata line so it can still be used to refer to a round (and to disambiguate two rounds pasted from the same corpus) without being the only way to tell them apart.

```
┌────────────────────────────────────────┐
│ 英雄史詩ーいかが宿命に直面   [Saved] ✓ 🗄 │
│ #1 · 2026/8/13 21:44:01                │
└────────────────────────────────────────┘
```

| Element | Classes |
|---|---|
| Heading | `font-semibold text-body-sm text-on-surface truncate` — weight unchanged from Iteration 3 |
| Metadata line | `text-metadata text-on-surface-variant`, `#N · <timestamp>` joined by a middle dot so the card gains no height |
| Text column | `min-w-0 flex-1` — required, or a long label pushes the action buttons out of the card |
| Badge / action group | `shrink-0`, row spaced with `gap-2` |

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

### Model Provenance Caption

The AI Suggestions panel header states which model wrote the suggestions on screen, as metadata rather than as a status badge.

```
┌────────────────────────────────────────┐
│ AI SUGGESTIONS              3 Results  │
│ Select 3+ to save                      │
│ gemini-3.7-flash used                  │
│ [選択済み: 0/3+]                        │
└────────────────────────────────────────┘
```

- Typography/colour: `text-metadata text-on-surface-variant/80` — dimmer than the surrounding metadata, so it never competes with the count and selection badges
- Its own line with `break-all`: a long model id wraps instead of displacing the badges below it
- Raw provider model id, not a friendly name: it is matchable against the Groq/Gemini dashboards, and the pools rotate models per request so a display-name table would go stale
- Omitted entirely when the model is unknown — including History rounds saved before provenance was recorded. No "unknown" placeholder
- The neighbouring クラウドAPI / ローカルAI badge (near the offline-mode checkbox) is the transport indicator and is set by the same generation-completion path

### Confirm / Save Button Loading

"確定してコピー・保存" (`saveCorrections`):

- While in flight (`isSaving`): button **disabled**; leading icon is Material Symbols `progress_activity` with Tailwind `animate-spin` (same ぐるぐる pattern as job `processing` / LATEST live timer). A static `progress_activity` glyph without spin is not allowed.
- Label while waiting: `保存中...`
- Interaction: clipboard copy + local UI commit run first; server history/proposal persistence continues in the background with separate success/failure toasts (see OpenSpec change `async-confirm-copy-background-save`).

### Dialog Widths

`components/ui/dialog.tsx` is a Radix Dialog wrapper sibling to `sheet.tsx`. Sheets are edge-anchored and `w-72`-narrow, which does not suit long-form content, so this one is centered. Width is a **named `size`**, not a per-call-site value, so the second long-form editor is sized like the first:

| `size` | Width | Use for |
|---|---|---|
| `prose` (default) | `max-w-3xl` | Confirmations, short explanations — content read as prose, where a reading measure helps |
| `wide` | `max-w-5xl` | Long-form editors, where a reading measure works against the user |

A reading width is the wrong default for an editor: the correction prompt is thousands of characters of dense rules, and wrapping that into a prose column makes it unreviewable — the complaint that introduced `wide`. Pick a size; do not pass `className="max-w-…"` at the call site.

Shared by both sizes: `w-[calc(100vw-2rem)]` (so a phone gets edge margins rather than the max width), `max-h-[90%]`, `flex flex-col gap-4 overflow-y-auto`, `rounded-lg border-outline-variant bg-surface p-4 sm:p-6`, overlay `bg-black/80`. See the fixed-element height note near the end of this document for why `max-h-[90%]` rather than `90vh`.

**Long-form editor input**: `flex-1 min-h-[12rem] sm:min-h-[24rem] overflow-y-auto`. `flex-1` lets the input take the height the dialog has left; the floor is what it may **not** shrink past. The tall floor is behind `sm:` on purpose — raising it unconditionally puts the footer buttons back below the fold on a phone with the on-screen keyboard open, which is exactly the bug `responsive-mobile-correction-ui` fixed.

### Prompt Settings Dialog (centered modal, `size="wide"`)

The shared AI-correction prompt editor, opened from the TopAppBar gear. Its copy is **English**: the operators who tune critique quality are reading a Chinese prompt, and Japanese chrome around it helped no one.

```
┌────────────────────────────────────────────────────────────┐
│ System Prompt  [Default|Custom]                          ✕ │
│ System prompt for AI suggestions. Shared across all users   │
│ and sessions… The JSON output format is always appended…    │
│ Last updated by owner@example.com / 2026-08-16 …            │
│ ▸ How your prompt is assembled                             │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ (monospace textarea, flex-1, tall floor on ≥sm)        │ │
│ └────────────────────────────────────────────────────────┘ │
│ 1,234 / 20,000 characters                                   │
│ ⚠ inline validation / error                                 │
│   [Reset to Default]        [Cancel]              [Save]    │
└────────────────────────────────────────────────────────────┘
```

- Textarea: `font-mono text-body-sm leading-relaxed`, the long-form editor input sizing above, `bg-surface-container border-outline-variant`
- Badge in the header shows `Default` (`secondary`) or `Custom` (`default`); attribution line below the description uses `text-metadata text-on-surface-variant` and appears only when customized
- **Assembly disclosure**: a collapsed `<details>` (`border-outline-variant bg-surface-container-low`) listing, in order, the pieces of the full prompt — the edited body, exemplar rules, JSON contract, built-in example, then SOURCE / EXEMPLAR / TARGET. It exists because the editor shows one field while seven pieces reach the model, so "where does EXEMPLAR TEXT go?" had no answer on screen. Steps come from `lib/promptComposition.ts`, which the prompt builders are tested against; the two exemplar steps are labelled *only when EXEMPLAR TEXT is filled in*
- Character count sits alone on a `text-metadata` row. There is **no** offline-mode note: the stored prompt now governs offline generation too, so the old disclaimer was false
- One `role="alert"` line carries either validation feedback or a request error; a load failure takes precedence over "empty" so the reason the prompt never arrived is not masked
- Save is disabled until the text both changed and validates; `Reset to Default` requires a second click (label becomes `Confirm Reset`) before it deletes the stored row
- Loads on open, not on mount, so reopening always reflects what is actually stored

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

### Browser Notifications Toggle (notifications panel)

A `Desktop notifications` checkbox at the head of the bell panel, below its subtitle (OpenSpec change `add-browser-job-notifications`). It is the **second** channel for one event — the bell above is the first — so the two never fire together.

- **Suppressed while the tab is visible.** The bell badge and shake are already on screen there, and a second signal for the same event is noise. Anything other than `document.visibilityState === 'visible'` is a case where the bell cannot be seen.
- **Permission is requested from the toggle's change handler and nowhere else.** Never on page load: an unprompted permission dialog is the fastest route to an origin the user has blocked forever, and a denial cannot be undone from the page.
- **Three states**, all rendered in place rather than hidden:

| Permission | Rendering |
|---|---|
| `default` / `granted` | Checkbox enabled, `text-metadata` hint explaining the background-tab rule |
| `denied` | Checkbox **disabled**, hint points at browser settings — the page cannot recover this itself |
| `unsupported` | No checkbox; one `text-metadata` line stating the browser cannot show them |

- **Persistence**: `mjai-browser-notifications` (`"1"` / `"0"`) in `localStorage`, matching the flat `mjai-*` naming of `mjai-session-pane-mode` and `mjai-exemplar-card-open`. Unreadable storage reads as **off** — for this preference, off is also the privacy-preserving answer, and storage we cannot read is not evidence of consent. The preference is only stored as on once permission is actually `granted`, so a dismissed prompt leaves the checkbox unticked rather than ticked and silent.
- **Copy is English**, like the rest of the chrome. Activating a notification focuses the tab and opens that job's HITL review; a job no longer in the queue is dropped silently.

---

## Mobile Responsive Behavior

Three breakpoints are load-bearing, each deciding one thing (OpenSpec change `responsive-mobile-correction-ui`):

| Breakpoint | What it decides |
|---|---|
| `sm` (640px) | Below it, identity and sign-out move from the TopAppBar to the foot of the session drawer, and the New Session button becomes icon-only |
| `md` (768px) | Below it, the section tabs (`Sessions` / `Dashboard` / `Archive`) move from the TopAppBar into the session drawer |
| `lg` (1024px) | Below it, one workspace pane is on screen at a time (see below) and the session list is always the floating Sheet — the docked column is `lg`+ only |

The TopAppBar is visible at every width. At 320px it holds the menu trigger, the wordmark and the three controls a correction session needs at hand: new session, notifications, settings.

### One pane at a time below `lg`

Above `lg` the editor and review panes sit side by side. Below it they used to stack, which put two independently scrolling regions inside one fixed-height container and let a long proposal list squeeze the editor to nothing. Instead:

```
below lg                              lg and above
┌──────────────────────┐              ┌─────────┬────────┐
│ ☰  MJAI    + 🔔 ⚙    │              │ Editor  │ Queue  │
├──────────┬───────────┤              │         │ + AI   │
│  編集    │ 添削案 ③  │  ← switch    │         │        │
├──────────┴───────────┤              │         │        │
│ Editor  (full height)│              │         │        │
└──────────────────────┘              └─────────┴────────┘
```

- Which pane shows is `mobilePane` state, deliberately **not** persisted: a stored pane would reopen the app on the review side of a session the user has since left. It resets when the session changes
- Whether the switch is in force is left entirely to CSS (`lg:` classes show and hide the panes), so there is no second definition of `lg` in JS to drift from Tailwind's
- The 添削案 button carries a count of what is waiting in the pane that is off screen: proposals under review, or failing that the generations that will produce them
- Opening a completed job for review brings the review pane forward — the same effect that scrolls the suggestions card into view on desktop

### Viewport height

The shell uses `.h-viewport` / `.min-h-viewport` from `globals.css`, each a `100vh` declaration followed by `100dvh`, rather than `h-screen` or `h-dvh`:

- `dvh` tracks the viewport the browser is actually showing, shrinking for mobile address bars where `vh` reports the largest possible viewport and leaves the bottom of the app behind browser chrome
- The `vh` line is a real fallback, not decoration: the panes take their height from the shell, so a browser that dropped an unknown unit would collapse the workspace rather than degrade it
- A declaration pair rather than two utilities, because which of `h-screen` / `h-dvh` wins depends on ordering in the generated sheet
- `layout.tsx` sets `interactiveWidget: 'resizes-content'` so the layout viewport — and therefore `dvh` — also shrinks for the on-screen keyboard
- `maximumScale` / `userScalable` are deliberately absent. Suppressing pinch zoom is the routine collateral damage of a mobile pass, and this app shows dense CJK text people need to magnify

Prefer flex-derived heights over `calc(100vh - …)`, which encodes a guess about how much chrome sits above an element and drifts when the header changes. For `fixed` elements a percentage (`max-h-[90%]`) resolves against the initial containing block, which is the visible viewport — that is what bounds the prompt dialog.

### Pointer capability, not screen size

Affordances that depend on hovering are gated on whether the pointer can hover, not on width — a narrow desktop window can hover, a 1280px tablet cannot:

| Mechanism | Where | Meaning |
|---|---|---|
| `can-hover:` variant (`tailwind.config.js`) | `can-hover:opacity-0 can-hover:group-hover:opacity-100` | `@media (hover: hover) and (pointer: fine)`. Quiet-until-hover reveals apply only where hovering is possible; elsewhere the control is simply present |
| `.touch-target` class (`globals.css`) | Icon-only buttons | Under `@media (hover: none)`, a 44px minimum with flex centering. A 18px glyph in `p-1` is a 26px target, and a minimum size alone would strand the glyph in a corner |

Both add rules inside a media query and never alter the base class, so desktop density is untouched. Where a hover-revealed control was the only route to an action — selecting a proposal, previously double-click only — the visible control is also a single-activation route.

### Rows that cannot fit a narrow viewport

Rows whose contents need more than 320px get `flex-wrap`, with what yields chosen per row rather than uniformly. The session name keeps a `basis-48` it will fight for so the short timing readouts wrap instead of the name being cut to a few characters; the exemplar card heading truncates for the mirror-image reason, being fixed text the user can predict next to badges that describe their own input.

---

## Source Files

| File | Purpose |
|---|---|
| `frontend/src/app/globals.css` | CSS custom properties (design tokens), `.h-viewport` / `.min-h-viewport`, `.touch-target` |
| `frontend/tailwind.config.js` | Tailwind theme extensions, `can-hover` variant |
| `frontend/src/app/layout.tsx` | Font loading (Inter, Material Symbols), `viewport` export (keyboard-aware layout, zoom left enabled) |
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
