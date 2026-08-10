# CANCELLED — migrate-database-to-supabase

**Status:** Rejected / cancelled (not implemented)  
**Date:** 2026-08-11

## Decision

Project decision: **keep Render Postgres for application data**. Supabase is used for **Auth only**, not as the app database / persistence backend.

This OpenSpec change proposed consolidating persistence exclusively onto Supabase Postgres (removing the SQLite dual-path and migrating `backend/db/app.db`). That direction is no longer the product plan.

## Archive handling

- All implementation tasks are cancelled; none were applied under this change.
- Delta specs under `specs/` were **not** synced into `openspec/specs/` (they describe rejected Supabase-as-DB behavior).
- This change folder is archived under `openspec/changes/archive/` for historical record only.
