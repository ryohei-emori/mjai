## Why

The current `docs/DESIGN.md` combines two distinct purposes into one document and explicitly disclaims being a UI/visual design-system doc. Meanwhile, the frontend already has real design tokens (CSS custom properties in `globals.css`, Tailwind config, shadcn/ui `components.json`) that are undocumented. Splitting into **SYSTEM-DESIGN.md** (engineering architecture) and **UI-DESIGN.md** (visual identity / design tokens) provides:

1. Clearer separation of concerns — engineers read system architecture, UI contributors read visual identity.
2. A living record of actual frontend design decisions (colors, typography, spacing, components) extracted from the codebase rather than invented.
3. Removal of the obsolete §8 "Future Work / Open Questions" section (all items now implemented).

## What Changes

- **Remove** §8 "Future Work / Open Questions" from the engineering design doc (all listed items are implemented).
- **Rename** `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`.
- **Convert** ASCII-art system diagrams in SYSTEM-DESIGN.md to **Mermaid** for better rendering/maintenance.
- **Create** `docs/UI-DESIGN.md` — a Stitch-inspired visual-identity doc grounded in the existing frontend (`globals.css` CSS custom properties, Tailwind config, shadcn/ui `components.json`, actual page styles).
- **Update references** in `AGENTS.md`, `README.md` (if any), and the OpenSpec `architecture-documentation` spec to point to the new `SYSTEM-DESIGN.md` path.
- **Clarify** in both docs which is which (SYSTEM = engineering architecture; UI = visual identity).

## Capabilities

### New Capabilities

- `ui-design-documentation`: The project maintains a UI visual-identity document (`docs/UI-DESIGN.md`) describing design tokens, color palette, typography, spacing, and component patterns extracted from the actual frontend codebase.

### Modified Capabilities

- `architecture-documentation`: Update the spec to reference `docs/SYSTEM-DESIGN.md` instead of `docs/DESIGN.md`, and clarify that this covers **engineering** architecture (not UI/visual design — that now lives in `docs/UI-DESIGN.md`).

## Impact

- **Files modified**: `docs/DESIGN.md` (rename + edit), `AGENTS.md`, `README.md`, `openspec/specs/architecture-documentation/spec.md`.
- **Files created**: `docs/UI-DESIGN.md`, `docs/SYSTEM-DESIGN.md` (via rename).
- **No application code changes** — this is a documentation restructure only.
- **OpenSpec spec update required** to reflect new path.
