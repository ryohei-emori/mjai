/**
 * ジョブキューの並び順ルール（slide-job-queue-carousel change、design.md
 * Decision 2 参照）。
 *
 * Job Queueパネル（横スライド）とTopAppBarのベル通知の両方がここを使う。
 * 以前はベル側だけがインラインで完了ジョブをソートしていたため、「最新」の
 * 定義が2箇所に分かれてズレる余地があった。
 *
 * `page.tsx` の `QueuedJob` 型を直接importせず構造的な型で受け取るのは、
 * `QueuedJob` がexportされていない上に `"use client"` ページ側（WebLLM /
 * Supabase を引き込む）に属するため。純関数だけを切り出しておくことで
 * DOMなしでユニットテストできる。
 */

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed'

export type OrderableJob = {
  status: JobStatus
  queuedAt: Date
  completedAt?: Date
}

/**
 * ユーザーが今気にしている度合いの順位（小さいほど先頭）。
 *
 * `processing` が最優先なのは「今動いているか」への答えだから。`queued` を
 * その次に置いて進行中の仕事を連続させ、終了済みは `completed`（確定操作が
 * 必要＝アクショナブル）を `failed`（再試行できるが基本は情報）より前にする。
 */
const RELEVANCE_RANK: Record<JobStatus, number> = {
  processing: 0,
  queued: 1,
  completed: 2,
  failed: 3,
}

export function jobRelevanceRank(status: JobStatus): number {
  return RELEVANCE_RANK[status] ?? Number.MAX_SAFE_INTEGER
}

/** グループ内の新しさ判定に使う時刻。完了済みなら完了時刻、そうでなければ投入時刻。 */
export function jobSortTimestamp(job: OrderableJob): number {
  return (job.completedAt ?? job.queuedAt).getTime()
}

/**
 * 関連度（status）→ 新しさ（降順）でソートしたコピーを返す。入力配列は変更しない。
 */
export function sortJobsByRelevance<T extends OrderableJob>(jobs: readonly T[]): T[] {
  return jobs
    .slice()
    .sort((a, b) => {
      const rankDiff = jobRelevanceRank(a.status) - jobRelevanceRank(b.status)
      if (rankDiff !== 0) return rankDiff
      return jobSortTimestamp(b) - jobSortTimestamp(a)
    })
}

/**
 * HITL確認待ちの完了ジョブのみを新しい順で返す（TopAppBarのベル通知用）。
 */
export function sortCompletedJobsNewestFirst<T extends OrderableJob>(jobs: readonly T[]): T[] {
  return jobs
    .filter((job) => job.status === 'completed')
    .sort((a, b) => jobSortTimestamp(b) - jobSortTimestamp(a))
}
