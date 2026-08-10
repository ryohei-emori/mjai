## Why

MJAI adopted OpenSpec but has no specs yet under `openspec/specs/`. The correction-workspace UI (the single-page frontend that end users interact with to manage sessions, submit text for correction, review AI proposals, and save results) is already fully implemented but undocumented. Before planning any future UI changes, the team needs an accurate baseline spec that captures the existing, already-implemented behavior of `frontend/src/app/page.tsx` and its API client.

## What Changes

- Documents the existing correction-workspace UI behavior as a new OpenSpec capability, `correction-workspace-ui`. No functional/behavioral changes to the application.
- Captures: session list display and selection, session creation/deletion, on-demand loading of session history/proposal details, the correction-history creation form (original text + target text inputs), triggering AI suggestion generation (with existing selection/custom-correction state preserved across regenerations), reviewing and selecting/deselecting AI proposals, editing a proposal's comment text, adding a custom proposal, the minimum-3-selection save gate, saving a history (which also persists all proposals and copies a combined comment to the clipboard), restoring a previously saved history into the active form, and the toast notifications shown for each of these flows (including API failure toasts).
- Also documents the responsive sidebar/session-switcher behavior (mobile sheet vs. collapsible desktop sidebar) to the extent it affects observable UI behavior, and the mock-mode (`NEXT_PUBLIC_FRONTEND_MODE=mock`) code path used for local development without a live AI backend.

## Capabilities

### New Capabilities
- `correction-workspace-ui`: The Next.js/React single-page workspace (`frontend/src/app/page.tsx`, `frontend/src/app/api.ts`, supporting `use-toast` hook) that end users use to manage sessions, submit text for AI correction, review/select/edit proposals, and save correction histories.

### Modified Capabilities
(none — this is a net-new baseline documentation entry; no existing spec exists for this capability)

## Impact

- No code changes. This is a documentation-only baseline capturing current behavior of `frontend/src/app/page.tsx`, `frontend/src/app/api.ts`, and `frontend/src/hooks/use-toast.ts`.
- Establishes `openspec/specs/correction-workspace-ui/spec.md` (via sync/archive, out of scope for this change) as the source of truth for future UI change proposals.
- Related, separately-documented backend capabilities (session management, correction-history creation, AI-proposal generation/persistence) are referenced but not authored here.
