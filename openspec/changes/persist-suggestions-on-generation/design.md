## Context

See proposal.md. Today: Job Queue + unconfirmed suggestions = React + `localStorage`; `correction_histories` + `ai_proposals` written mainly in `saveCorrections()`. `fix-key-pool-quota-and-lazy-webllm` already polls histories ~10s but leaves unconfirmed jobs device-local. Shared Supabase DB + allow-listed single user; no API keys in DB.

## Goals / Non-Goals

**Goals:**
- Persist successful generations to Postgres immediately (pending).
- Hydrate pending rows into Job Queue / review via load + existing poll.
- Confirm promotes pending → confirmed without duplicate history junk.
- Minimal API surface matching `main.py` / `db_helper.py` / `page.tsx` patterns.
- Additive migration; docs + tests for persist/load.

**Non-Goals:**
- Reintroducing WebLLM auto-fallback.
- Syncing in-flight `queued`/`processing` jobs (only completed suggestion payloads required).
- Per-user RLS tightening.
- Storing `sourceExcerpt` (still generation-time UI aid unless already in proposals).
- Touching `add-optional-exemplar-translation-input`.

## Decisions

### 1. Reuse `correction_histories` + `ai_proposals` with `status`

**Choice:** Additive columns on `correction_histories`:

| Column | Type | Role |
|--------|------|------|
| `status` | TEXT NOT NULL DEFAULT `'confirmed'` | `pending` \| `confirmed` (optional `failed` if cheap) |
| `overall_comment` | TEXT | Model overall comment for restore (confirm still writes numbered `combined_comment`) |
| `provider` | TEXT | `api` \| `webllm` (observability) |
| `client_job_id` | TEXT | Frontend job id for merge/dedupe across clients |

Proposals stay as today (`type`, texts, reasons, selection flags). Pending create inserts all AI suggestions with `isSelected=false`.

**Alternatives rejected:** New `suggestion_jobs` table (more schema + dual sync); localStorage-only sync (does not meet shared-DB requirement).

### 2. API shape

- Extend `POST /histories` to accept `status`, `overallComment`, `provider`, `clientJobId`.
- Add `PUT /histories/{history_id}` for confirm promote + finalize fields.
- Keep `POST /proposals` for initial pending inserts and any new custom proposals at confirm.
- Add `PUT /proposals/{proposal_id}` to update selection/edit fields in place (avoid delete-all/recreate for the AI set).

Default `status` on create = `confirmed` so older confirm-only clients keep working until the frontend switches pending-first.

### 3. Frontend lifecycle

1. **Generation success** (`processJobAsync`): mark job completed locally → `POST /histories` (`status=pending`, texts, `overallComment`, provider, `clientJobId`) → `POST /proposals` per suggestion → attach `historyId` (+ proposal ids if useful) on the job.
2. **Load / poll** (`loadSessionDetails`): histories with `status=pending` → merge into `jobQueue` as `completed` (dedupe by `historyId` / `clientJobId`); `status=confirmed` → `savedData` History as today (`confirmed: true`). Do not clobber an in-progress local review of the same job if the user is mid-edit (prefer local suggestions when `confirmingJobId` matches).
3. **Confirm** (`saveCorrections`): if job has `historyId`, `PUT` history to `confirmed` + `PUT` each proposal’s flags + `POST` any new customs; else legacy create path. Clipboard + local UI reset unchanged (async-confirm-copy-background-save).

### 4. Failed jobs (nice-to-have)

If low cost: allow `status=failed` with `overall_comment` or reuse `combined_comment` for error message + `client_job_id`. Skip if it complicates History UI; success path is mandatory.

### 5. Migration & deploy

- File: `backend/supabase/migrations/005_pending_suggestion_histories.sql` (`ADD COLUMN IF NOT EXISTS`, default `'confirmed'`).
- Apply to shared Supabase (SQL editor / CLI) before or with the Vercel deploy that writes the new columns.
- Rollback: stop writing new columns (app ignores extras); columns are nullable/defaulted so safe to leave.

## Risks / Trade-offs

- **[Risk] Double History if confirm still POSTs** → Confirm must prefer PUT when `historyId` present; tests cover promote path.
- **[Risk] Poll overwrites mid-review edits** → Skip overwriting suggestions for the actively confirming job; merge by id.
- **[Risk] Pending rows clutter History** → UI lists only `confirmed` in History; pending only in Job Queue/review.
- **[Trade-off] In-flight jobs stay local** → Acceptable; only completed payloads are required for cross-env visibility.
- **[Trade-off] PUT proposals N times on confirm** → Simple and matches REST style; batch endpoint deferred.

## Migration Plan

1. Apply `005_pending_suggestion_histories.sql` to Supabase.
2. Deploy backend+frontend together (frontend depends on new fields/endpoints).
3. Existing histories remain `confirmed` via default; no backfill required.
4. Smoke: generate on local → open prod (same session) → see pending job → confirm once → single History row.
