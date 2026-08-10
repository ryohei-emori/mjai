-- Add status column for soft-delete (archive) functionality
-- Valid values: 'active' (default), 'archived'

ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active';

-- Add index for efficient filtering by status
CREATE INDEX idx_sessions_status ON sessions(status);
