## 1. Remove the stale note

- [x] 1.1 Re-read `frontend/src/app/page.tsx` immediately before editing (concurrent carousel work in the same region) — `slide-job-queue-carousel` had already landed as `3837d0c`, so the edit applied to its committed output
- [x] 1.2 Delete `未確定ジョブはこの端末のみ（確定保存後に共有DBのHistoryへ）` and its `" · "` separator from the Job Queue `CardDescription`, keeping the processing-mode text

## 2. Audit for the same stale claim elsewhere

- [x] 2.1 Search UI copy, tooltips, and help text for other device-local / pending-sync claims — none found
- [x] 2.2 Search `docs/*.md` and `README.md` for the same claim and correct anything stale — none found; remaining matches are historical planning artifacts of `fix-key-pool-quota-and-lazy-webllm` / `persist-suggestions-on-generation`, which correctly describe their own point in time
- [x] 2.3 Confirm the save-failure toast is retained (it describes a real local-only fallback)

## 3. Verify

- [x] 3.1 Confirm no jest test asserts the removed string; run frontend jest — 16 suites / 192 tests passed
- [x] 3.2 Stage only `page.tsx` (plus this change's artifacts) so concurrent frontend work is untouched
