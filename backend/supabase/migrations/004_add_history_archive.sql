-- Add is_archived column for soft-delete (archive) functionality on correction_histories
-- Mirrors the sessions.status soft-delete pattern (see 002_add_session_status.sql):
-- individual history rounds can be archived (hidden from the normal History list)
-- without permanently deleting the row, so downstream ai_proposals remain intact.

ALTER TABLE correction_histories ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT false;

-- Add index for efficient filtering of non-archived history rows per session
CREATE INDEX IF NOT EXISTS idx_histories_is_archived ON correction_histories(session_id, is_archived);
