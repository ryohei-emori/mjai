## Context

See `proposal.md` for motivation. Current audit of `frontend/src/app/page.tsx` + `globals.css`:

| Behavior | Already exists? | Notes |
|----------|-----------------|-------|
| CSS `@keyframes bell-shake` / `.bell-shake` | **Yes** | `globals.css` (~0.6s) |
| Shake on job **completion** | **Yes** | `setBellShake(true)` after successful job finish; timeout clears after 600ms |
| Shake on enqueue / active count change | **No** (correct) | Not wired; keep it that way |
| Badge on bell | **Yes, wrong semantics** | `activeJobCount` = `processing` \| `queued` |
| Bell click → list | **Missing** | `<button>` has no `onClick`; title only `"通知"` |
| HITL confirm path | **Yes** | `confirmJob(job)` used by Job Queue cards |

`execution-history-hitl-queue` already shipped the queue + HITL confirm; this change only retargets TopAppBar notification UX. No Popover/Dropdown primitive in `frontend/src/components/ui/` today (Sheet/Dialog exist; Sheet is heavy for a bell menu).

## Goals / Non-Goals

**Goals:**
- Badge = count of `status === 'completed'` jobs in the current session `jobQueue`
- Clickable bell opens a compact absolute-positioned panel listing those jobs
- Item click → `confirmJob(job)` then close panel
- Keep existing completion shake; document semantics in UI-DESIGN.md

**Non-Goals:**
- Cross-session notification aggregation
- Persisting "read/dismissed" notification state beyond job-queue membership
- Showing `failed` jobs in the bell list (Job Queue remains the place for failures)
- Adding `@radix-ui/react-popover` unless a simple absolute panel proves insufficient
- Changing toast copy on job complete

## Decisions

### 1. Badge count source

**Choice**: `completedJobCount = jobQueue.filter(j => j.status === 'completed').length`

**Rationale**: Jobs leave the queue only after successful confirm+save (`setJobQueue(prev => prev.filter(...))`), so `completed` in-queue === awaiting HITL. Failed jobs stay visible in Job Queue but are not "ready for confirmation" in the same sense (`confirmJob` requires `completed`).

**Alternative**: Exclude `confirmingJobId` from the badge. Rejected — user is still mid-review until save; keeping the count until removal matches "awaiting confirm/save."

### 2. Notification panel UI without new dependency

**Choice**: Local React state `bellPanelOpen` + absolutely positioned panel under the bell (`relative` on the icon cluster), `bg-surface border border-outline-variant`, `ScrollArea` for overflow, click-outside / Escape to close. Reuse Job Queue card summary fields: `completedAt \|\| queuedAt` via `toLocaleTimeString()`, `targetText` truncated (~40 chars), status label 「完了」 / `check_circle` Material Symbol.

**Rationale**: Matches MD3 brutalist tokens already used on Job Queue cards; avoids new package and Lucide (Sheet still uses Lucide `X` historically — do not introduce more Lucide icons; use Material Symbols for list rows).

**Alternative**: Sheet from the right. Rejected for a lightweight notification peek; Sheet is for session list on mobile.

### 3. Shake remains completion-only

**Choice**: Keep the existing `setBellShake(true)` block in the job-success path. Do not add shake on enqueue. Optionally ensure shake restarts if a second job completes while the class is still applied (current clear-timeout + re-set already handles this).

**Rationale**: Audit shows shake already targets completion; only badge/list were wrong/missing.

### 4. Docs

**Choice**: Update TopAppBar / Bell Shake sections in `docs/UI-DESIGN.md` — badge = completed awaiting HITL; shake on completion; bell opens list. Fix typography table note that still says `"N Active"` if it refers to this badge.

## Risks / Trade-offs

- [Panel clipped by `overflow-hidden` on ancestors] → Anchor panel inside TopAppBar (outside the `flex-1 overflow-hidden` content row); use high `z-index` (`z-50`).
- [Click-outside closes while interacting] → Ignore clicks inside the panel; toggle bell click to close.
- [Jobs with empty suggestions still listed] → List all `completed` jobs; `confirmJob` already toasts "提案なし" / parse failure — same as Job Queue click.

## Migration Plan

Frontend-only. Deploy with normal Vercel git push. No data migration. Rollback = revert the commit.

## Open Questions

None — scope is fully specified by the user request.
