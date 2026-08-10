## Context

See `proposal.md` for motivation. This design covers the structure of the `docs/DESIGN.md` document to be written and where its content is sourced from — it does not itself change any code.

## Goals / Non-Goals

**Goals:**
- Define a Google-style design doc structure appropriate for MJAI's current size and complexity (not over-engineered for a small full-stack app).
- Ensure the document is grounded entirely in verifiable, current code/config — no aspirational or planned content presented as already built.
- Make the document easy to extend later: clear section headers, and explicit notes where a section is intentionally minimal for now.

**Non-Goals:**
- Not designing the future architecture (WebLLM, Vercel, Supabase migration, Google auth) — only referencing already-proposed changes as forward pointers.
- Not producing a second portfolio-style overview (`README.md` already serves that purpose) or duplicating `AGENTS.md`'s operational/env-var reference — `docs/DESIGN.md` is complementary: **engineering** architecture and design rationale, not setup instructions, "never do" operational rules, or UI/visual design-system docs.
- Not resolving the inconsistencies discovered during research (e.g. `next.config.js` static-export vs. Dockerfile standalone-server mismatch, backend Postgres-path `insert_session` key-casing bug, README's `backend/app/llm/` claim not matching the actual inline Gemini call in `main.py`) — the design doc records them as known caveats; fixing them is out of scope for this documentation-only change.

## Decisions

**Section structure** — `docs/DESIGN.md` is a Google-style **engineering** design document (not UI/visual design; not Google Labs Stitch `DESIGN.md` tokens). Top-level sections, adapted from public Google eng design-doc descriptions (e.g. industrialempathy.com “Design Docs at Google”, Gerrit template):
1. **Header** — Title / Authors / Status (`Living document — as-built`) / Last updated; explicit note that this is eng design, not UI DESIGN.md.
2. **Objective** — what MJAI is (factual/engineering tone, distinct from README marketing).
3. **Context and Background** — problem, relationship to `README.md`/`AGENTS.md`.
4. **Goals and Non-Goals** — what the current system is designed to do and explicitly not do.
5. **Proposed Design (System Overview)** — high-level component diagram (ASCII) of frontend, backend, database, Gemini, Supabase Auth.
6. **Detailed Design** — components; data model/storage; APIs; frontend as API client only; deployment.
7. **Cross-Cutting Concerns** — security/privacy, observability/failure modes, configuration, known caveats.
8. **Alternatives Considered** — brief for brownfield; point forward-looking alternatives to OpenSpec.
9. **Future Work / Open Questions** — in-flight OpenSpec changes (WebLLM, Vercel, DB migration; auth mostly as-built).
10. **Sources** — public templates followed; note that Google has no single mandatory public eng DESIGN.md RFC.

**Sourcing** — all technical claims are drawn only from: `AGENTS.md`, `README.md`, `backend/app/main.py`, `backend/app/auth.py`, `backend/app/db_helper.py`, `backend/db/schema.sql`, `frontend/package.json`, `frontend/next.config.js`, `frontend/Dockerfile`, `backend/Dockerfile`, `terraform/main.tf`, `.github/workflows/deploy.yml`, `conf/.env.example`. No detail is invented; anything uncertain is flagged as a caveat rather than stated as fact.

**Scoping the "Google auth" item** — research during design confirmed the Google-authentication OpenSpec change (`add-google-authentication`, 19/30 tasks complete) is already functionally implemented in the current codebase: `backend/app/auth.py` enforces Supabase-JWT + allow-listed-email auth on every API route, and the frontend has a working `AuthProvider`/`LoginScreen`/Supabase client wired into `api.ts`. This is current, as-built architecture, not future work — `docs/DESIGN.md` will document it as such in Detailed Design and Cross-Cutting Concerns. Only the three changes with 0 completed tasks (WebLLM migration, Vercel deployment, Supabase database migration) are true future work for the "Future Work" section.

## Risks / Trade-offs

- [Risk] Documenting current architecture in detail could go stale quickly given several in-flight architecture changes. → Mitigation: the new spec requirement establishes an explicit expectation to update `docs/DESIGN.md` when architecture changes land, and the doc itself calls out which parts are most likely to change soon (deployment, database, AI generation, auth completion).
- [Risk] Some legacy/ambiguous config (e.g. `SUPABASE_SERVICE_ROLE_KEY` in `conf/.env`, `BACKEND_MODE` env var controlling mock vs. real suggestion generation) could be mis-described if guessed at. → Mitigation: only document what is directly verifiable in code; explicitly flag anything uncertain as a caveat instead of asserting it.
- [Risk] Discovering functional bugs (e.g. a key-casing mismatch in the Postgres session-insert path) while researching for documentation purposes only, with no mandate to fix them. → Mitigation: record as a known caveat in the doc and surface it to the user in the final report; do not fix application code in this documentation-only change.
