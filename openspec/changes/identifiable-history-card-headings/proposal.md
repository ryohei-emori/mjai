## Why

Every card in the right pane's History panel is titled `添削データ #1`, `添削データ #2`, … — a bare sequence number that says nothing about which correction round it is. To find a specific round the user has to click cards until the editor happens to show the text they were looking for. The Job Queue cards already solve this by previewing the beginning of the target text, so the workspace is internally inconsistent: the same underlying object is identifiable in one panel and anonymous in the other.

## What Changes

- History cards SHALL lead with a **content preview derived from the entry's text**, not with the sequence number. The sequence number stays visible but demotes to the metadata line next to the timestamp, so it can still be used to refer to a round without being the only way to tell rounds apart.
- Introduce **one shared, unit-tested derivation rule** for "what short label identifies this correction text", and use it from all three surfaces that need such a label: the History card heading, the Job Queue card preview, and the TopAppBar bell's completed-job list. Today the latter two each inline their own `targetText.slice(0, 40)`.
- The rule prefers a **title-like first line** (short, followed by more content, not sentence-terminated) verbatim — a corpus like 「英雄史詩ーいかが宿命に直面」 followed by paragraphs should show that heading, not the first 40 characters that cut into the body. Otherwise it shows a whitespace-collapsed **excerpt of the beginning of the text** with an ellipsis.
- Blank/whitespace-only text falls back to the existing 「(空のテキスト)」 placeholder rather than rendering an empty heading.
- Font weights, badges, timestamps, and the `check_circle` / `archive` actions are unchanged — only what the heading says and where the sequence number sits.

No change to persistence, the HITL confirm flow, archive behaviour, job execution, or ordering.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `correction-workspace-ui`: adds requirements for content-identifiable History card headings and for a single shared correction-label derivation rule used by History cards, Job Queue cards, and the bell notification list. Existing History restore/archive behaviour and Job Queue behaviour are preserved.

## Impact

- `frontend/src/lib/correctionLabel.ts` (new) — pure derivation helper (`deriveCorrectionLabel`) plus unit tests under `frontend/src/lib/__tests__/`.
- `frontend/src/app/page.tsx` — History card heading and metadata line; Job Queue card preview and bell list switch to the shared helper.
- `docs/UI-DESIGN.md` — document the correction-label pattern (title-line vs excerpt, ellipsis, blank fallback, where the sequence number lives).
- No backend, API, DB, LLM-provider, or prompt changes. No new design tokens.
