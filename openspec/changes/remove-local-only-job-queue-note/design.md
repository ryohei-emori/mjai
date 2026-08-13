## Context

The note was added deliberately: `fix-key-pool-quota-and-lazy-webllm`'s design recorded `[Trade-off] Unconfirmed jobs stay device-local → Document in UI copy under Job Queue; syncing them is a separate change`, and its task 4.4 implemented exactly that. `persist-suggestions-on-generation` then *was* that separate change, but it never retired the copy the earlier trade-off had introduced. So this is stale documentation left behind by a resolved limitation, not a new decision.

## Goals / Non-Goals

**Goals**
- Remove the note the user asked to remove.
- Leave no other UI or docs text asserting the same resolved limitation.

**Non-Goals**
- Changing Job Queue layout, ordering, or the carousel behavior being built concurrently in `slide-job-queue-carousel`.
- Rewriting historical planning artifacts of past changes: `fix-key-pool-quota-and-lazy-webllm` and `persist-suggestions-on-generation` documents correctly describe what was true when they were written.

## Decisions

### Delete the note rather than reword it to describe pending sync

The user's request was to remove the UI text, not to replace it with a corrected version. The Job Queue already shows job status visually, and a running commentary on persistence internals is not information the operator needs at that spot. The processing-mode text stays because it explains observable throughput (why jobs run one at a time in オフラインモード).

### Keep the save-failure toast

`提案は表示されていますが、共有DBへの保存に失敗しました。この端末のジョブは残っています。` fires only on a real persistence failure, where "this device only" is the accurate and actionable description. Removing it would hide a genuine data-loss risk.

### Coordinate with concurrent `page.tsx` edits

`slide-job-queue-carousel` is editing the same file and the same Job Queue region. This change touches only the `CardDescription` children, re-reading the file immediately before editing and staging `page.tsx` explicitly rather than with a bulk add, so the carousel work is not reverted or overwritten.

## Risks / Trade-offs

- **Merge collision on `page.tsx`.** Mitigated by editing only the two lines of the description and by re-reading the file at edit time.
- **Losing an explanation users relied on.** Low: the statement it made is no longer true, so keeping it would be worse than removing it.

## Migration Plan

Frontend-only copy removal. No migration, no flag, no rollback concern beyond reverting the commit.

## Open Questions

- None.
