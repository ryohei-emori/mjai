import {
  jobRelevanceRank,
  jobSortTimestamp,
  sortCompletedJobsNewestFirst,
  sortJobsByRelevance,
  type JobStatus,
  type OrderableJob,
} from '../ordering'

type TestJob = OrderableJob & { id: string }

const at = (minute: number) => new Date(2026, 7, 14, 9, minute, 0)

function job(
  id: string,
  status: JobStatus,
  queuedMinute: number,
  completedMinute?: number,
): TestJob {
  return {
    id,
    status,
    queuedAt: at(queuedMinute),
    completedAt: completedMinute === undefined ? undefined : at(completedMinute),
  }
}

const ids = (jobs: TestJob[]) => jobs.map((j) => j.id)

describe('jobRelevanceRank', () => {
  it('ranks processing ahead of queued, and both ahead of finished jobs', () => {
    expect(jobRelevanceRank('processing')).toBeLessThan(jobRelevanceRank('queued'))
    expect(jobRelevanceRank('queued')).toBeLessThan(jobRelevanceRank('completed'))
    expect(jobRelevanceRank('completed')).toBeLessThan(jobRelevanceRank('failed'))
  })

  it('falls back to a last-place rank for an unknown status', () => {
    expect(jobRelevanceRank('bogus' as JobStatus)).toBeGreaterThan(jobRelevanceRank('failed'))
  })
})

describe('jobSortTimestamp', () => {
  it('prefers completedAt over queuedAt when present', () => {
    expect(jobSortTimestamp(job('a', 'completed', 1, 5))).toBe(at(5).getTime())
  })

  it('falls back to queuedAt when the job has not finished', () => {
    expect(jobSortTimestamp(job('a', 'queued', 1))).toBe(at(1).getTime())
  })
})

describe('sortJobsByRelevance', () => {
  it('puts the processing job first regardless of insertion order', () => {
    const jobs = [
      job('done', 'completed', 1, 2),
      job('waiting', 'queued', 3),
      job('running', 'processing', 4),
    ]
    expect(ids(sortJobsByRelevance(jobs))).toEqual(['running', 'waiting', 'done'])
  })

  it('orders finished jobs newest-first', () => {
    const jobs = [
      job('old', 'completed', 1, 2),
      job('newest', 'completed', 3, 9),
      job('middle', 'completed', 2, 5),
    ]
    expect(ids(sortJobsByRelevance(jobs))).toEqual(['newest', 'middle', 'old'])
  })

  it('places completed jobs before failed jobs even when the failure is newer', () => {
    const jobs = [
      job('broken', 'failed', 1, 20),
      job('ok', 'completed', 2, 3),
    ]
    expect(ids(sortJobsByRelevance(jobs))).toEqual(['ok', 'broken'])
  })

  it('orders queued jobs newest-first by enqueue time', () => {
    const jobs = [job('first', 'queued', 1), job('second', 'queued', 2)]
    expect(ids(sortJobsByRelevance(jobs))).toEqual(['second', 'first'])
  })

  it('groups every status in the documented order', () => {
    const jobs = [
      job('f1', 'failed', 1, 4),
      job('c1', 'completed', 1, 3),
      job('q1', 'queued', 2),
      job('p1', 'processing', 3),
    ]
    expect(ids(sortJobsByRelevance(jobs))).toEqual(['p1', 'q1', 'c1', 'f1'])
  })

  it('does not mutate the input array', () => {
    const jobs = [job('a', 'completed', 1, 2), job('b', 'processing', 3)]
    const snapshot = ids(jobs)
    sortJobsByRelevance(jobs)
    expect(ids(jobs)).toEqual(snapshot)
  })

  it('handles empty and single-item inputs', () => {
    expect(sortJobsByRelevance([])).toEqual([])
    expect(ids(sortJobsByRelevance([job('only', 'queued', 1)]))).toEqual(['only'])
  })
})

describe('sortCompletedJobsNewestFirst', () => {
  it('keeps only completed jobs, newest first', () => {
    const jobs = [
      job('c-old', 'completed', 1, 2),
      job('running', 'processing', 3),
      job('c-new', 'completed', 4, 8),
      job('broken', 'failed', 5, 9),
      job('waiting', 'queued', 6),
    ]
    expect(ids(sortCompletedJobsNewestFirst(jobs))).toEqual(['c-new', 'c-old'])
  })

  it('falls back to queuedAt for a completed job missing completedAt', () => {
    const jobs = [job('with-completed', 'completed', 1, 3), job('no-completed', 'completed', 7)]
    expect(ids(sortCompletedJobsNewestFirst(jobs))).toEqual(['no-completed', 'with-completed'])
  })

  it('does not mutate the input array', () => {
    const jobs = [job('a', 'completed', 1, 2), job('b', 'completed', 3, 9)]
    const snapshot = ids(jobs)
    sortCompletedJobsNewestFirst(jobs)
    expect(ids(jobs)).toEqual(snapshot)
  })

  it('returns an empty list when nothing has completed', () => {
    expect(sortCompletedJobsNewestFirst([job('a', 'queued', 1)])).toEqual([])
  })
})
