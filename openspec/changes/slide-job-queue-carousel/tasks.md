## 1. Shared job ordering helper

- [x] 1.1 Create `frontend/src/lib/jobQueue/ordering.ts` with `JobStatus`, an `OrderableJob` structural type (`{ status, queuedAt, completedAt? }`), `jobRelevanceRank`, `jobSortTimestamp`, `sortJobsByRelevance`, and `sortCompletedJobsNewestFirst` (design Decision 2)
- [x] 1.2 Add `frontend/src/lib/jobQueue/__tests__/ordering.test.ts` covering: processing-first ordering, queued before finished, completed before failed, newest-first within each group, `completedAt` preferred over `queuedAt`, input array not mutated, and empty/single-item inputs

## 2. Carousel component

- [x] 2.1 Create `frontend/src/components/ui/job-queue-carousel.tsx` exporting a generic presentational `JobQueueCarousel<T>({ items, getKey, renderItem, ariaLabel })` (design Decision 5)
- [x] 2.2 Implement the scroll-snap track: `overflow-x-auto`, `scroll-snap-type: x mandatory`, `scroll-snap-align: start` per card, `overscroll-behavior-x: contain`, thin visible scrollbar (design Decision 1)
- [x] 2.3 Implement `ResizeObserver`-driven `cardsPerView` (`MIN_CARD_WIDTH` 230 after in-browser measurement — 260 left the maximum-width pane stuck at one card, cap 3) with a safe fallback to 1 when `ResizeObserver` is unavailable, and derive card flex-basis with a peek reserve when overflowing (design Decision 3)
- [x] 2.4 Implement overflow/edge state (`canScrollPrev`, `canScrollNext`, `hasOverflow`) from scroll position, updated on `scroll` and on resize
- [x] 2.5 Add prev/next `chevron_left`/`chevron_right` icon buttons with `aria-label`s, disabled at the ends, scrolling by ~one visible page; suppress the whole control row when `hasOverflow` is false (design Decision 4)
- [x] 2.6 Add the page indicator: dots when pages ≤ 6, `N / M` text beyond that; hidden when there is a single page
- [x] 2.7 Add `pointer-events-none` leading/trailing fade gradients rendered only on the side that has more content
- [x] 2.8 Add track keyboard handling: `tabIndex={0}`, `role="group"`, `aria-label`, `ArrowLeft`/`ArrowRight` scroll, ignoring events originating from inputs/textareas (design Decision 6)
- [x] 2.9 Verify all styling uses existing tokens only (`bg-surface`, `border-outline-variant`, `bg-md3-primary`, `text-metadata`, `rounded-lg`/`rounded-full`, `md-18`/`md-20` icons) — no new colors, radii, or font sizes
- [x] 2.10 Add `frontend/src/components/ui/__tests__/job-queue-carousel.test.tsx` covering: all items rendered inside the labelled region, controls hidden without overflow, edge arrow disabled, next scrolls ~one page, arrow-key sliding, arrow keys ignored inside text fields, and item-level Enter activation still firing

## 3. Wire into the Job Queue panel

- [x] 3.1 In `frontend/src/app/page.tsx`, add a `useMemo` producing `orderedJobQueue` from `sortJobsByRelevance(jobQueue)`
- [x] 3.2 Replace the Job Queue panel's `space-y-2` vertical stack with `JobQueueCarousel`, moving the existing job card JSX verbatim into `renderItem` (status colors, badges, timestamps, error text, confirm affordance, retry button all unchanged)
- [x] 3.3 Adjust the card's inner layout for a fixed-width horizontal card (full-height card, `h-full`, snippet still truncated) without changing which information is shown
- [x] 3.4 Replace the inline `completedJobs` sort with `sortCompletedJobsNewestFirst(jobQueue)` so the bell and the queue share one rule
- [x] 3.5 Confirm `activeJobCount`, bell badge/shake, `confirmJob`, `retryJob`, localStorage persistence, and the ~10s pending-history poll are untouched

## 4. Styles

- [x] 4.1 Add a `.job-carousel-track` (or equivalent) utility in `frontend/src/app/globals.css` for scroll-snap + `overscroll-behavior-x` + thin scrollbar styling, following the existing `@layer utilities` pattern

## 5. Verification

- [x] 5.1 Run `cd frontend && npm test` — new ordering tests pass, no regressions in existing suites
- [x] 5.2 Run `cd frontend && npm run lint` — no new errors
- [x] 5.3 Run `cd frontend && npm run build` — production build succeeds
- [x] 5.4 Manually verify in a browser: 1-job queue shows no controls; many-job queue slides via arrows, dots, wheel, and arrow keys; ends disable the correct arrow; resizing the right pane changes cards-per-view; clicking/Entering a completed card still opens HITL review

## 6. Documentation

- [x] 6.1 Update `docs/UI-DESIGN.md` with a "Job Queue Carousel" pattern entry: ordering rule, affordance stack, responsive cards-per-view table, and accessibility notes
- [x] 6.2 Mark all tasks complete and re-run `openspec validate --change slide-job-queue-carousel --strict`
