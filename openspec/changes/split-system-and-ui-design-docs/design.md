# Design: Split System and UI Design Docs

## Context

See `proposal.md` for motivation. The current `docs/DESIGN.md` is a Google-style engineering design document that:
- Explicitly disclaims being a UI/visual design doc (header note, §3 non-goals, §9 name-collision note)
- Contains ASCII-art system diagrams that render poorly in some Markdown viewers
- Retains a §8 "Future Work / Open Questions" section where all items are now implemented

Meanwhile, real design tokens exist in the frontend codebase but are undocumented:
- `frontend/src/app/globals.css`: CSS custom properties for colors (HSL), spacing radius
- `frontend/tailwind.config.js`: Tailwind theme extensions referencing those CSS vars
- `frontend/components.json`: shadcn/ui configuration (style: new-york, base color: neutral)

## Goals / Non-Goals

**Goals:**
- Split into two files: `SYSTEM-DESIGN.md` (engineering) and `UI-DESIGN.md` (visual identity)
- Remove obsolete §8 Future Work section (all items implemented)
- Convert ASCII diagrams to Mermaid for better maintenance/rendering
- Extract actual design tokens from `globals.css`, `tailwind.config.js`, `components.json` — no invented colors or typography
- Update all references (`AGENTS.md`, `README.md`, `openspec/specs/architecture-documentation/spec.md`)

**Non-Goals:**
- Redesigning the actual UI or changing any design tokens
- Adding new colors/typography not already in the codebase
- Changing any application code beyond documentation updates

## Decisions

### Decision 1: File naming — `SYSTEM-DESIGN.md` and `UI-DESIGN.md`

**Choice:** Use `SYSTEM-DESIGN.md` for engineering architecture and `UI-DESIGN.md` for visual identity.

**Rationale:** Clear semantic distinction; "SYSTEM" emphasizes backend/infrastructure/API architecture, "UI" emphasizes frontend visual design. Both live in `docs/` alongside each other.

**Alternatives considered:**
- `ARCHITECTURE.md` + `DESIGN.md` — rejected because "DESIGN.md" is overloaded (Google eng design doc vs. Google Labs Stitch visual design)
- `ENGINEERING-DESIGN.md` + `UI-DESIGN.md` — verbose; "SYSTEM" is more concise

### Decision 2: Mermaid for system diagrams

**Choice:** Replace ASCII-art boxes with Mermaid `flowchart` diagrams.

**Rationale:** 
- Mermaid is widely supported in GitHub, GitLab, VS Code, Cursor, and most Markdown renderers
- Easier to maintain than fixed-width ASCII art
- Better accessibility (can be parsed semantically)

**Scope:** Convert all ASCII diagrams in the system overview section (§4). Currently there is one main diagram showing Vercel → Supabase architecture.

### Decision 3: Extract real tokens, don't invent

**Choice:** `UI-DESIGN.md` documents only tokens that exist in the codebase (`globals.css`, `tailwind.config.js`, `components.json`).

**Rationale:** Avoids "AI slop" brand invention; keeps the doc grounded in reality; any future brand evolution happens in code first, then doc is updated.

**Token sources:**
- Colors: CSS custom properties in `globals.css` `:root` and `.dark` selectors (HSL values)
- Radii: `--radius: 0.5rem` in `globals.css`, extended in `tailwind.config.js`
- Component base: shadcn/ui "new-york" style, "neutral" base color, Lucide icons

### Decision 4: §8 removal vs. archival

**Choice:** Remove §8 "Future Work / Open Questions" entirely rather than moving to a separate file.

**Rationale:** All items listed (WebLLM, Vercel frontend/backend, Supabase DB, Google auth, session archive) are now implemented per the doc's own status column. The "Open questions" subsection (logging, RLS, cold start) can remain as inline notes in relevant sections if needed, but a dedicated future-work section for already-shipped work is misleading.

## Risks / Trade-offs

**[Risk]** `UI-DESIGN.md` could go stale if frontend tokens change and no one updates the doc.
→ **Mitigation:** The new `ui-design-documentation` spec requires sync on token changes, mirroring the existing pattern for `AGENTS.md` / `SYSTEM-DESIGN.md`.

**[Risk]** Mermaid diagrams may not render in all environments.
→ **Mitigation:** Mermaid is supported in GitHub, GitLab, VS Code, Cursor, and Notion. For unsupported renderers, the text is still readable as a directed graph description.

**[Risk]** Reference updates may be incomplete (other files may link to `docs/DESIGN.md`).
→ **Mitigation:** Tasks include a grep-based search for references; known files are `AGENTS.md`, `README.md`, and the `architecture-documentation` spec.

## Migration Plan

No runtime migration required — this is a docs-only change.

Deployment steps:
1. Remove §8 from current `docs/DESIGN.md`
2. Rename `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`
3. Convert ASCII diagram to Mermaid
4. Add clarifying cross-references between SYSTEM and UI docs
5. Create `docs/UI-DESIGN.md` with extracted tokens
6. Update `AGENTS.md` references
7. Update `openspec/specs/architecture-documentation/spec.md`
8. Check `README.md` for any references (appears to have none currently)

Rollback: Revert the commit. No data migration or external service changes.
