## Why

The Job Queue panel in the right pane renders every job as a vertically stacked card. With up to 30 concurrent API jobs, the panel grows without bound and pushes the AI Suggestions and History panels far below the fold — the user has to scroll past dead queue history to reach the panel they actually work in. The jobs the user cares about right now (the one being processed, and the freshly completed one awaiting HITL confirm) are also not guaranteed to be at the top, because the queue renders in raw insertion order.

## What Changes

- Replace the Job Queue panel's vertical stack with a **horizontal slide (carousel)** track: fixed panel height regardless of job count, horizontal scroll with CSS scroll-snap.
- **Reorder jobs by relevance** instead of insertion order: in-flight work first (`processing`, then `queued`), then finished work newest-first (`completed`, then `failed`). The first card is always the job the user most likely wants.
- Add affordances that make horizontal sliding obvious: previous/next arrow buttons (disabled at the ends), a page-position indicator, edge fade masks with a partially visible peek of the next card, and native wheel/trackpad/touch swipe scrolling.
- Add keyboard and screen-reader support: `←`/`→` move the carousel, arrows are labelled buttons, the track is a labelled scrollable region, and job cards keep their existing focus/Enter/Space confirm behaviour.
- Extract the completed-job ordering used by the TopAppBar bell and the new queue ordering into one shared, unit-tested helper module so both surfaces agree on what "newest" means.
- Responsive: one card per view on narrow panes, more cards per view as the resizable right pane widens.

No change to job execution, polling, persistence, notification counts, retry, or the HITL confirm flow — this is a presentation-layer change plus a pure ordering helper.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `correction-workspace-ui`: adds requirements for Job Queue horizontal-slide presentation, relevance-based job ordering, slide affordances/keyboard accessibility, and responsive cards-per-view. The existing job-card content, confirm-on-click, and retry behaviours are preserved.

## Impact

- `frontend/src/app/page.tsx` — Job Queue panel rendering; reuse of the shared ordering helper for the bell list.
- `frontend/src/components/ui/` — new `job-queue-carousel.tsx` presentational component (arrows, track, indicator, edge fades).
- `frontend/src/lib/jobQueue/ordering.ts` (new) — pure ordering helpers (`sortJobsByRelevance`, `sortCompletedJobsNewestFirst`) plus unit tests.
- `frontend/src/app/globals.css` — utility for the scroll-snap track / hidden-scrollbar variant if not already covered by `.no-scrollbar`.
- `docs/UI-DESIGN.md` — document the Job Queue carousel pattern (ordering, affordances, breakpoints).
- No backend, API, DB, or LLM-provider changes.
