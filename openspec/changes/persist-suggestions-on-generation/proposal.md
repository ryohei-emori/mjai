## Why

Successful AI suggestion generation today lands only in React state + `localStorage` (Job Queue / Draft). Shared Supabase Postgres receives rows mainly after 「確定してコピー・保存」, so another browser, device, or environment on the same DB cannot see completed-but-unconfirmed suggestions. Follow-up to `fix-key-pool-quota-and-lazy-webllm`, which documented this gap and deferred cross-client Job Queue sync.

## What Changes

- Persist every successful suggestion generation (cloud API or explicit offline WebLLM) to Postgres immediately when the job completes and suggestions appear in the right pane — not only on confirm/save.
- Extend `correction_histories` (+ linked `ai_proposals`) with a clear pending vs confirmed lifecycle so confirm/save updates the same rows instead of double-writing junk.
- On app load / session select / existing ~10s polling: hydrate unconfirmed (pending) generations into the Job Queue / right-pane review UI so another account/environment sees them.
- Keep confirm/save (clipboard + History) working; mark confirmed when the user finishes HITL selection.
- Optional cheap persist of failed-job error status for observability; success payloads are required.
- Brief AGENTS.md / SYSTEM-DESIGN updates for the persistence model. Migration SQL under `backend/supabase/migrations/`.
- Do **not** reintroduce WebLLM auto-fallback; do **not** store API keys; leave `add-optional-exemplar-translation-input` untouched.

## Capabilities

### New Capabilities

<!-- none — reuse existing history/proposal model -->

### Modified Capabilities

- `correction-history`: Support pending (generated, unconfirmed) vs confirmed history records; create on generation success; update on confirm; expose fields needed for right-pane restore (`overallComment`, provider, client job id, status).
- `ai-proposal-management`: Persist full suggestion sets for pending histories; allow selection/reason updates when confirming without creating duplicate proposal rows when a pending history already exists.
- `correction-workspace-ui`: After generation success, write pending history+proposals to the API; on load/poll, merge pending server rows into Job Queue / review UI; confirm/save promotes pending → confirmed without double History junk.

## Impact

- **DB**: Additive migration on `correction_histories` (status, overall_comment, provider, client_job_id; defaults keep existing rows confirmed).
- **Backend**: `db_helper.py` / `main.py` — create/list/update history with new fields; proposal create unchanged for inserts; confirm may PATCH history + update proposal flags.
- **Frontend**: `page.tsx` `processJobAsync` persist-after-success; `loadSessionDetails` + poll hydrate pending; `saveCorrections` promote-or-update; `api.ts` helpers.
- **Docs**: `AGENTS.md`, `docs/SYSTEM-DESIGN.md`.
- **Tests**: API persist + load paths (mocked asyncpg) where practical.
