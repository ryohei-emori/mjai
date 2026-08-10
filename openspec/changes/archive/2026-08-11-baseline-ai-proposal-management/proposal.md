## Why

MJAI adopted OpenSpec, but no capability has a spec yet. The `ai-proposal-management` capability (creating and listing per-correction AI/custom proposals) is already fully implemented and in production use, but its behavior is undocumented outside the source code. Before planning any future changes to this capability, the team needs an accurate baseline spec that reflects what the system actually does today, including its quirks and edge cases.

## What Changes

- Document the existing, already-implemented behavior of AI proposal management (list proposals for a correction history; create a proposal) as a new OpenSpec capability spec.
- No functional or behavioral changes to the backend. This is a documentation-only baseline: `openspec/specs/ai-proposal-management/spec.md` does not exist yet, so this change adds it via an `ADDED Requirements` delta describing current behavior only.
- Capture actual (not aspirational) behavior, including: the raw-`dict` (non-strict-Pydantic) request handling, default field values, the `USE_POSTGRESQL` environment toggle and its fallback/error semantics, lack of `historyId` existence validation, and SQLite ordering behavior.

## Capabilities

### New Capabilities
- `ai-proposal-management`: Creating and listing AI-generated/custom correction proposals (`AIProposals` table) tied to a `CorrectionHistory`, including selection/modification/custom tracking fields.

### Modified Capabilities
(none — this is a net-new spec for a previously undocumented capability)

## Impact

- **Affected code (read-only reference, no edits)**: `backend/app/main.py` (`GET /histories/{history_id}/proposals`, `POST /proposals`), `backend/app/db_helper.py` (`fetch_proposals_by_history_sqlite`, `insert_proposal_sqlite`, and their PostgreSQL/Supabase counterparts `fetch_proposals_by_history`, `insert_proposal`), `backend/db/schema.sql` (`AIProposals` table).
- **Out of scope**: Sessions and CorrectionHistories CRUD endpoints, and the `/suggestions` Gemini-generation endpoint (covered by the sibling `ai-suggestion-generation` capability) — referenced here only where directly relevant (e.g. the `historyId` foreign key relationship, and that AI-generated proposal content originates from that flow before being persisted via these endpoints).
- **No code, schema, or API changes.** This change only adds planning artifacts under `openspec/changes/baseline-ai-proposal-management/`.
