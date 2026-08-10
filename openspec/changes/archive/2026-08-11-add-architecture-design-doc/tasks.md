## 1. Research current architecture

- [x] 1.1 Read `AGENTS.md` and `README.md` in full to establish the documented baseline and known caveats.
- [x] 1.2 Read backend source (`backend/app/main.py`, `backend/app/auth.py`, `backend/app/db_helper.py`) to confirm actual routes, auth enforcement, and the dual Postgres/SQLite data-access paths.
- [x] 1.3 Read `backend/db/schema.sql` and confirm the SQLite schema and its relationship to the Postgres path used by `db_helper.py`.
- [x] 1.4 Read `frontend/package.json`, `frontend/next.config.js`, and the `frontend/src` directory structure (app routes, auth provider, API client) to confirm the actual frontend stack and structure.
- [x] 1.5 Read `terraform/main.tf`, `.github/workflows/deploy.yml`, `backend/Dockerfile`, and `frontend/Dockerfile` to confirm the actual deployment path and any build/deploy inconsistencies.
- [x] 1.6 Read `conf/.env.example` to confirm the current set of configuration/environment variables and their purpose.
- [x] 1.7 Cross-check findings against `AGENTS.md`'s "Reality check" and "Never do" sections; note any additional inconsistencies found (e.g. mismatches between README's stated architecture and actual code) as caveats to include in the design doc.

## 2. Draft docs/DESIGN.md sections

- [x] 2.1 Draft Objective / Summary.
- [x] 2.2 Draft Background & Context (problem, relationship to `README.md` and `AGENTS.md`).
- [x] 2.3 Draft Goals and Non-Goals for the current system.
- [x] 2.4 Draft System Overview (component-level description of frontend, backend, database, Gemini API, Supabase auth).
- [x] 2.5 Draft Detailed Design: Components.
- [x] 2.6 Draft Detailed Design: Data Model.
- [x] 2.7 Draft Detailed Design: API.
- [x] 2.8 Draft Detailed Design: Deployment.
- [x] 2.9 Draft Cross-Cutting Concerns (auth/authorization, CORS, configuration, observability).
- [x] 2.10 Draft Alternatives Considered (brief, per design.md).
- [x] 2.11 Draft Future Work / Open Questions, referencing the in-flight OpenSpec changes and known caveats.

## 3. Write and validate the document

- [x] 3.1 Assemble all drafted sections into `docs/DESIGN.md` at the repository root.
- [x] 3.2 Cross-check the assembled document against `AGENTS.md` and `README.md` for contradictions; resolve any found by aligning wording (without editing those two files).
- [x] 3.3 Verify every technical claim in the document traces back to a specific source file read in Section 1 (no invented details).
- [x] 3.4 Run `openspec validate add-architecture-design-doc --strict` and fix any reported issues in the change's own artifacts.
