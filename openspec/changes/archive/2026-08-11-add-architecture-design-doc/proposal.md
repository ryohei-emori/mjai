## Why

MJAI has no single document describing its current architecture. `README.md` is portfolio-facing (features, setup) and `AGENTS.md` is an agent-operational-constraints reference (env vars, deploy gotchas, "never do" list) — neither is a design document that explains the system's structure and rationale for a human reader (new contributor, reviewer, or the project owner revisiting the codebase later). As the system evolves (several architecture-level changes are already proposed: WebLLM migration, Vercel deployment, Supabase migration, Google auth), the lack of a baseline design doc makes it harder to see what is actually built today versus what is planned, and harder to keep design intent visible as those changes land.

## What Changes

- Establish an expectation that the project maintains a Google-style **engineering** design document at `docs/DESIGN.md` describing the **current** (as-built) system architecture: context/goals, system overview, detailed design (components, data model, API, deployment), and cross-cutting concerns. This is an eng design doc (problem, trade-offs, APIs) — **not** a UI/visual DESIGN.md (e.g. Google Labs Stitch design-token format).
- Require `docs/DESIGN.md` to be kept in sync when architecture actually changes (mirrors the maintenance rule already established for `AGENTS.md`'s "Never do" section), so the document does not go stale the way README's old Quick Start section did.
- Produce the first version of `docs/DESIGN.md`, documenting the system as it exists today — not the proposed/future architecture from in-flight changes (WebLLM, Vercel, Supabase, Google auth). Those are noted as future work to fold in once implemented.

## Capabilities

### New Capabilities
- `architecture-documentation`: The project must maintain a Google-style architecture design document (`docs/DESIGN.md`) describing the current system, and keep it updated when the architecture changes.

### Modified Capabilities
(none — no existing spec's behavior changes)

## Impact

- Affected files: adds `docs/DESIGN.md` (new file). No application code, backend routes, frontend components, or infrastructure are modified.
- Affected process: establishes a doc-maintenance expectation analogous to the one already in `AGENTS.md`, scoped to `docs/DESIGN.md` instead of `AGENTS.md`.
- No runtime, deployment, or API impact.
