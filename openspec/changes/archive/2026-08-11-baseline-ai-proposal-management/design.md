## Context

See `proposal.md` - Why. This change only documents existing, already-implemented behavior of the `ai-proposal-management` capability; it introduces no new architecture, external dependency, data model change, or migration.

## Goals / Non-Goals

**Goals:**
- Record why no technical design work is needed for this change.

**Non-Goals:**
- Proposing any implementation, refactor, or architectural change to `backend/app/main.py`, `backend/app/db_helper.py`, or `backend/db/schema.sql`.

## Decisions

**Decision: No design content beyond this note.**
This change is a documentation baseline, not a new feature or refactor. None of the schema's "when to include design.md" triggers apply:
- Not cross-cutting (touches only two existing, already-implemented endpoints and one existing table).
- No new external dependency or data model change (the `AIProposals` table in `backend/db/schema.sql` is unchanged).
- No security, performance, or migration complexity introduced.
- No ambiguity requiring a technical decision before "coding" - there is no coding in this change.

This file exists only because the `spec-driven` schema's `tasks` artifact structurally requires `design` to be present before it can be written; see the final report for this note.

## Risks / Trade-offs

None - this change makes no code, schema, or behavioral changes. [Risk: none identified] → [Mitigation: n/a]
