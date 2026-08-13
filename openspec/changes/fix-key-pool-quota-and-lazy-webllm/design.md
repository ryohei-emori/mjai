## Context

See proposal.md. Shared Supabase Postgres is already used for sessions / histories / ai_proposals. Vercel local and production share the same DB when configured per AGENTS.md.

## Root causes (operator-facing)

### Why proposals did not appear on “the other account”

Interpretation of「他のアカウント」in this codebase: another browser tab, device, or environment (local vs prod) logged in as the allow-listed user against the **same shared DB** — not “another Groq API key.”

| Layer | Where data lives | Shared? |
|-------|------------------|---------|
| Job Queue + completed-but-unconfirmed suggestions | React state + `localStorage` (`mjai:jobQueue:*`) | **No** — per browser profile |
| Draft AI suggestions before confirm | React + `localStorage` draft | **No** |
| After「確定してコピー・保存」 | `correction_histories` + `ai_proposals` in Postgres | **Yes** |
| Right-pane History refresh | `loadSessionDetails` only on session switch/select | **Gap** — no poll while staying on session |

So: if A only finished generation (green Job Queue) but did not confirm/save, B will never see it (by design today). If A **did** save, B still missed it until re-selecting the session because nothing re-fetched histories/proposals.

Not caused by RLS (policies are permissive) or API filtering by user id (single allow-list; sessions are global in DB).

### Why Quota exceeded did not show in UI

1. `apiFetch` / suggestions path threw a generic error without promoting `message` / `rate_limited`.
2. `processJobAsync` caught **any** API failure and **auto-fell back to WebLLM**, hiding the real failure.
3. If WebLLM succeeded, the job was `completed` with source `webllm` — quota looked like success.

**Policy now:** WebLLM runs **only** when オフラインモード is explicitly ON. Cloud failures always fail the job + toast; no auto-fallback.

### Key pool vs quota

Pool is **not** the root cause of hard quota. Cooldown is process-local memory (not shared across Vercel isolates). Plural env does not double-count. See prior investigation table in git history / AGENTS.md.

## Goals / Non-Goals

**Goals:**
- Poll saved histories/proposals for the open session (~8–12s); merge into right-pane History.
- Structured suggestion API errors; visible quota/rate-limit; no silent WebLLM success on quota.
- Lazy WebLLM; pool hardening + docs.

**Non-Goals:**
- Syncing unconfirmed Job Queue across devices (would need a new shared draft store).
- Live Groq/Cloudflare dashboard RPD scraping.
- Full credential-status top-bar DB panel (deferred unless time remains).

## Decisions

### 1. Poll `loadSessionDetails` while session open

Interval ~10s when authenticated + `currentSessionId` set. Merge server `savedData` by `historyId`; keep local-only rows still missing `historyId` (optimistic background save). Do not touch `jobQueue` or in-progress `suggestions` from the poll.

### 2. No automatic WebLLM fallback

When オフラインモード is off, cloud path failures (429/quota, 503, network, etc.) mark the job `failed` and show a destructive toast with the server/human message. **No** WebLLM import/call. User must turn on オフラインモード to use local AI.

### 3. Lazy WebLLM only for explicit offline mode

Dynamic `import("@/lib/webllm/engine")` only inside the `offlineMode === true` branch.

## Risks / Trade-offs

- **[Risk] Poll overwrites optimistic History** → Keep local rows without `historyId`.
- **[Trade-off] Unconfirmed jobs stay device-local** → Document in UI copy under Job Queue; syncing them is a separate change.
- **[Trade-off] No auto-offline on any API failure** → User must enable オフラインモード explicitly; cloud errors stay visible.
