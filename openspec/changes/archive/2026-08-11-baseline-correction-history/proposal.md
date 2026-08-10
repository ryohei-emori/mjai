## Why

OpenSpec was just adopted in this repository, but `openspec/specs/` currently has no entries. The `correction-history` capability (session-scoped correction history records) is already fully implemented in the FastAPI backend and used by the frontend, yet its behavior is undocumented in spec form. Before any future change to this capability is proposed, we need an accurate baseline spec that captures what the system actually does today (including its real edge cases and quirks), so future changes can be diffed against a known-correct starting point.

## What Changes

- Document the existing, already-implemented `correction-history` capability as a new OpenSpec capability spec.
- No code, API, schema, or behavior changes of any kind. This is a documentation-only baseline.
- Capture actual (not aspirational) behavior of:
  - `GET /sessions/{session_id}/histories` — listing correction histories for a session.
  - `POST /histories` — creating a correction history record.
  - The underlying `CorrectionHistories` SQLite table and its relationship to `Sessions`.
  - Observed quirks: server-generated timestamps, loose/dict-based request validation, non-standard error responses (200 with an `error` field instead of 4xx), no FK enforcement in SQLite, and double JSON-encoding of `selectedProposalIds`/`customProposals`.

## Capabilities

### New Capabilities
- `correction-history`: Session-scoped correction history records (original text, instruction prompt, target text, combined comment, selected/custom proposal references) — listing histories for a session and creating new history entries, as currently implemented in `backend/app/main.py` and persisted via `backend/app/db_helper.py` / `backend/db/schema.sql`.

### Modified Capabilities
(none — no existing specs exist yet for this or any capability)

## Impact

- **Affected code (read-only, for documentation purposes)**: `backend/app/main.py` (`get_histories`, `create_history` endpoints), `backend/app/db_helper.py` (`fetch_histories_by_session_sqlite`, `insert_history_sqlite`, and the parallel PostgreSQL-oriented `fetch_histories_by_session`/`insert_history` functions), `backend/db/schema.sql` (`CorrectionHistories` table).
- **Affected systems**: None — this change only adds files under `openspec/changes/baseline-correction-history/` and (once synced/archived, out of scope here) `openspec/specs/correction-history/`.
- **Out of scope**: Sessions CRUD (`Sessions` table, `/sessions*` endpoints) and AIProposals CRUD/generation (`AIProposals` table, `/histories/{id}/proposals`, `/proposals`, `/suggestions`) are owned by parallel baseline-documentation efforts and are only referenced here minimally (e.g., the `sessionId` foreign key relationship).
