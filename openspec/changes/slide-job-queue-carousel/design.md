## Context

See `proposal.md` — Why.

Constraints that shape the approach:

- The Job Queue lives inside the **resizable right pane** (`RIGHT_PANE_MIN_WIDTH` 280px → `RIGHT_PANE_MAX_WIDTH` 600px, default 448px, persisted to localStorage). Below `lg` the pane becomes full-width and stacks under the editor. So "how many cards fit" is a *container* question, not a viewport-media-query question — Tailwind `sm:`/`md:` breakpoints would be wrong here.
- All job-queue state and rendering currently lives inline in `frontend/src/app/page.tsx` (~2900 lines). The job card markup already encodes status colors, badges, timestamps, the confirm affordance, and the retry button.
- `jobQueue` is the single source of truth for three surfaces: the Job Queue panel, the `activeJobCount` badge, and the TopAppBar bell (`completedJobs`). It is persisted to localStorage per session and merged with `pending` histories polled from Postgres every ~10s.
- Design tokens are fixed by `docs/UI-DESIGN.md` (MD3-inspired + "brutalist legibility": crisp 1px `border-outline-variant`, `shadow-none`, `text-label-caps` headers, Material Symbols icons). No new colors or radii may be invented.
- Jest + React Testing Library is available (`frontend/src/app/__tests__/`), but jsdom does not implement layout: `scrollWidth`, `clientWidth`, and `scrollTo` are all stubs. Anything depending on real measurement is not unit-testable here.

## Goals / Non-Goals

**Goals:**

- Constant-height Job Queue panel: adding jobs must never push AI Suggestions / History further down.
- The first card is always the most relevant job, by an explicit, tested ordering rule.
- "This slides horizontally" must be legible in a still screenshot — not discoverable only by trying to scroll.
- Ordering logic is a pure function shared with the bell list, unit-tested without DOM.
- Zero behavioral change to generation, polling, persistence, confirm/retry, and notification counts.

**Non-Goals:**

- No auto-advance / autoplay carousel, no infinite looping. The queue is a work list, not a banner.
- No virtualization. Even a pathological queue is tens of cards; DOM nodes are cheap and virtualization would break scroll-snap and native swipe.
- No drag-to-reorder, no per-card dismiss/delete (none exists today).
- No third-party carousel dependency.
- No changes to how the vertical AI Suggestions list renders.

## Decisions

### Decision 1: Native CSS scroll-snap over a JS transform carousel

The track is a plain `overflow-x-auto` flex row with `scroll-snap-type: x mandatory` and `scroll-snap-align: start` on each card; navigation buttons call `element.scrollBy({ left, behavior: 'smooth' })`.

*Why:* touch swipe, trackpad two-finger scroll, momentum, and RTL/accessibility behaviours come free from the browser and match platform expectations. A `transform: translateX()` carousel with a JS index would have to re-implement all of that, and would fight the fact that card count changes underneath it every ~10s poll (an index-based carousel can end up pointing at a card that no longer exists).

*Alternative considered:* `embla-carousel-react` (the carousel shadcn/ui ships). Rejected: a new runtime dependency for one panel, and its virtual-index model has the same "index vs. live-updating list" problem. Rejected `ScrollArea` (Radix) too — it hides the native scrollbar and its viewport wrapper makes scroll-snap + programmatic `scrollBy` on the right node awkward.

### Decision 2: Ordering as a pure helper module, shared with the bell

New `frontend/src/lib/jobQueue/ordering.ts` exports:

- `jobRelevanceRank(status)` → `processing: 0, queued: 1, completed: 2, failed: 3`
- `jobSortTimestamp(job)` → `completedAt ?? queuedAt` (ms)
- `sortJobsByRelevance(jobs)` → stable copy sorted by `(rank asc, timestamp desc)`
- `sortCompletedJobsNewestFirst(jobs)` → filter `completed` + timestamp desc

`page.tsx` uses `sortJobsByRelevance` for the carousel and replaces its inline `completedJobs` sort with `sortCompletedJobsNewestFirst`.

*Why this ordering:* the user's attention is on (a) what is running now and (b) what just finished and needs HITL confirm. `processing` first answers "is it working?"; `queued` next keeps in-flight work contiguous; `completed` before `failed` because completed is actionable (confirm) while failed is mostly informational (retry). Newest-first within a group matches the bell's existing rule and the general "latest at the front" expectation stated in the request.

*Why a module and not two inline `useMemo`s:* the bell already had its own sort; duplicating the rule invites drift where the bell's "newest" and the queue's "newest" disagree. Pure functions are also the only part of this change that is meaningfully unit-testable in jsdom.

The helper is generic over `{ status, queuedAt, completedAt }` rather than importing `QueuedJob` from `page.tsx` (which is not exported and lives in a `"use client"` page module) — this keeps the helper importable from tests without pulling in the WebLLM/Supabase-touching page tree.

### Decision 3: Container-width-driven cards-per-view via ResizeObserver

The carousel component measures its own track with a `ResizeObserver` and derives `cardsPerView = clamp(floor(trackWidth / MIN_CARD_WIDTH), 1, MAX_CARDS_PER_VIEW)` with `MIN_CARD_WIDTH = 230`, `MAX_CARDS_PER_VIEW = 3`. Card flex-basis is then `calc((100% - gaps) / cardsPerView)`, minus a small **peek reserve** (28px) when the content overflows so the next card is partially visible.

Effective breakpoints, measured in a browser rather than assumed: the panel's `p-4`/`lg:p-6` plus `CardContent` padding take about **84px** out of the right-pane width before the track sees it.

| Right pane width | Track width (measured) | Cards per view |
|---|---|---|
| 280px (min) | ~196px | 1 |
| 448px (default) | ~364px | 1 |
| ~544–600px (max) | ~460–516px | 2 (~240px each) |
| full-width mobile / very wide | ≥ ~720px | 3 (capped) |

`MIN_CARD_WIDTH` was tuned against these measurements: at 260 the maximum-width pane still only fit one card, so the "wider pane shows more cards" behaviour was unreachable inside the pane's actual range.

*Why ResizeObserver over Tailwind breakpoints or container queries:* the pane is resized by dragging, not by viewport changes, so media queries cannot see it. Tailwind container queries (`@container`) would work for layout but the component also needs the numeric page size in JS (for `scrollBy` distance and the indicator's page count), so a measured value is needed regardless. `ResizeObserver` is guarded for absence so jsdom/SSR degrade to 1 card rather than crashing.

*Why cap at 3:* the pane maxes at 600px; more than 3 cards there would shrink each below the width its badges + timestamp + confirm affordance need.

### Decision 4: Affordance stack (four redundant cues)

1. **Arrow buttons** — Material Symbols `chevron_left` / `chevron_right`, `rounded-full` icon buttons in a control row the carousel renders directly above its own track (not in the `CardHeader`), so the component keeps sole ownership of scroll state per Decision 5. They use the existing `hover:bg-surface-container` icon-button pattern from the TopAppBar, get `disabled` + `opacity-50` at the ends, and carry `aria-label="前のジョブへ"` / `"次のジョブへ"`. The same row carries a short `text-metadata` hint ("横スライドで他のジョブを表示") so the affordance is legible even before the arrows are noticed.
2. **Page indicator** — `●`/`○` dots (`rounded-full`, `bg-md3-primary` active / `bg-outline-variant` inactive) below the track when there is more than one page, with a `text-metadata` `N / M` fallback when pages exceed 6 (dots stop being scannable past that).
3. **Edge fade + peek** — absolutely positioned `w-6` gradients (`from-surface` → `transparent`) on whichever side has more content, rendered only when that side overflows, plus the peek reserve from Decision 3 so a sliver of the next card is always visible when there is a next card. The fade is `pointer-events-none` so it never eats a click on a card underneath.
4. **Visible thin scrollbar** — the track keeps a native scrollbar rather than hiding it (`.no-scrollbar` is deliberately *not* used here, unlike `HighlightedTextarea`), because a scrollbar is the most universally understood "this scrolls" signal.

*Why all four:* each covers a gap in the others — arrows for mouse users who never scroll horizontally, dots for "how much is there", fade/peek for "there is more right now", scrollbar for direct manipulation. They are all cheap and all suppressed when the track does not overflow (`hasOverflow === false`), so a 1-job queue stays visually identical to today.

### Decision 5: Presentational component, state stays in `page.tsx`

`frontend/src/components/ui/job-queue-carousel.tsx` exports `JobQueueCarousel<T>({ items, getKey, renderItem, ariaLabel })`. It owns only scroll/measurement state; it knows nothing about jobs, statuses, or the confirm flow. `page.tsx` passes the already-sorted jobs and the existing card JSX (moved verbatim into a `renderItem` callback).

*Why:* keeps the risky part (job state machine, confirm/retry wiring, persistence) untouched in `page.tsx`, and keeps the new component free of app coupling so it is reusable if History ever needs the same treatment. Generic over `T` rather than typed to `QueuedJob` for the same reason as Decision 2 — `QueuedJob` is a page-local type.

### Decision 6: Keyboard handling scoped to the track, not global

`ArrowLeft`/`ArrowRight` are handled by an `onKeyDown` on the track element (which carries `tabIndex={0}`, `role="group"`, `aria-label`). The handler ignores the event when it originated from a text input/textarea, and does not `preventDefault` when the track has no overflow.

*Why not a `window` listener:* the page has two large textareas and inline suggestion-comment editors; a global arrow-key hijack would break caret movement. Scoping to the track means arrows only slide when the user is actually in the queue.

*Card focusability is unchanged:* `completed`-with-suggestions cards keep `role="button"` / `tabIndex={0}` / Enter-Space, so Tab still walks the cards. Because the track is a scroll container, browsers auto-scroll a focused off-screen card into view — which combines correctly with scroll-snap.

### Decision 7: No layout shift while jobs re-sort under the user

Cards are keyed by `job.id`, and the sort is applied in a `useMemo` in `page.tsx`. When the ~10s poll or a completion mutates `jobQueue`, a card can move (e.g. `processing` → `completed` demotes it behind `queued` jobs). We deliberately do **not** try to preserve the visual scroll offset across re-sorts: the whole point of the ordering is that the front of the track is the current answer, and the user is normally parked at the front.

*Trade-off accepted:* a user who has slid deep into old jobs may see the content under them shift when a job completes. Mitigated by the fact that arrows/dots make it obvious where they are, and re-sorting only happens on real state transitions (not on every poll tick, since the sort is stable and derived).

## Risks / Trade-offs

- **jsdom cannot exercise scroll behaviour** → tests cover the pure ordering helper thoroughly plus a render-level test that the carousel renders all items and exposes labelled controls; actual snap/scroll verified manually in a browser.
- **`ResizeObserver` unavailable (older Safari, SSR, jsdom)** → feature-detected; falls back to `cardsPerView = 1` and a fully functional (if less optimally packed) track. No crash, no `useLayoutEffect` warning on the server since measurement runs in `useEffect`.
- **Horizontal scroll can conflict with browser back-swipe on trackpads** → the track is a nested scroller with its own overflow, so the browser routes the gesture to it; `overscroll-behavior-x: contain` on the track prevents the gesture chaining out to the page/history.
- **Long queues make the dot indicator unreadable** → switch to `N / M` text past 6 pages (Decision 4).
- **Cards shrink below legibility on a 280px pane** → `MIN_CARD_WIDTH` 260 with `cardsPerView` clamped to ≥1 means at minimum width one card takes the full track; the card's own content already wraps/truncates (`truncate` on the snippet) as it does today.
- **Re-sort moves a card the user was about to click** → accepted (Decision 7); status transitions are the only trigger and each card's status is re-rendered with its own color/badge, so a mis-click lands on a card whose state is visibly different.

## Migration Plan

Pure frontend presentation change; no data migration, no API/env changes.

1. Add the ordering helper + tests (no UI impact on its own).
2. Add `JobQueueCarousel`; swap the Job Queue panel's `space-y-2` stack for it, moving the existing card JSX into `renderItem` unchanged.
3. Point the bell's `completedJobs` at the shared helper.
4. Update `docs/UI-DESIGN.md` with the Job Queue carousel pattern.

Rollback: revert the commit. localStorage job-queue payloads are untouched (ordering is derived at render time, never persisted), so there is no forward/backward data compatibility concern.
