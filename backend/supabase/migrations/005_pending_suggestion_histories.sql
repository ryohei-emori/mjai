-- Persist AI suggestion generations before confirm/save (pending vs confirmed).
-- Existing rows default to 'confirmed' so pre-migration History behavior is unchanged.
-- Apply to shared Supabase (SQL editor or CLI) before/with the deploy that writes these columns.

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'confirmed';

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS overall_comment TEXT;

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS provider TEXT;

ALTER TABLE correction_histories
  ADD COLUMN IF NOT EXISTS client_job_id TEXT;

-- Optional observability for failed generations (nice-to-have; app may leave unused).
COMMENT ON COLUMN correction_histories.status IS 'pending | confirmed | failed';
COMMENT ON COLUMN correction_histories.overall_comment IS 'Model overall comment for right-pane restore';
COMMENT ON COLUMN correction_histories.provider IS 'api | webllm';
COMMENT ON COLUMN correction_histories.client_job_id IS 'Frontend Job Queue id for cross-client dedupe';

CREATE INDEX IF NOT EXISTS idx_histories_session_status
  ON correction_histories(session_id, status)
  WHERE is_archived = false;
