## Why

The Job Queue panel's description still reads `未確定ジョブはこの端末のみ（確定保存後に共有DBのHistoryへ）`. That statement was accurate when `fix-key-pool-quota-and-lazy-webllm` added it, but `persist-suggestions-on-generation` (commit `2bca0d5`, migration `005`) made generation write a `status=pending` `correction_histories` row plus full `ai_proposals` immediately — and the session-detail load and ~10 s poll merge those pending rows back into the Job Queue on any device. Unconfirmed jobs are therefore *not* device-local, so the note is both unwanted clutter and factually wrong.

## What Changes

- Remove the `未確定ジョブはこの端末のみ（確定保存後に共有DBのHistoryへ）` note from the Job Queue panel description, leaving the still-accurate processing-mode text (`WebLLMモード: 逐次処理（1件ずつ）` / `APIモード: 並列処理（最大N件同時）`).
- Audit remaining UI copy, tooltips, help text, and `docs/*.md` for the same device-local claim and correct or remove anything stale. The save-failure toast at `page.tsx` (`提案は表示されていますが、共有DBへの保存に失敗しました。この端末のジョブは残っています。`) stays: it describes the genuine fallback where persistence failed and the job really is local-only.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `correction-workspace-ui`: The Job Queue panel MUST NOT present unconfirmed jobs as device-local, because they are persisted to the shared database at generation time and are visible from other devices.

## Impact

- `frontend/src/app/page.tsx` (Job Queue `CardDescription`)
- No API, DB, schema, provider, or test-contract changes; no jest assertion referenced the removed string
