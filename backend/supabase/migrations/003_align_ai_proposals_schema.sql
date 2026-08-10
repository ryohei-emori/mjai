-- Align ai_proposals schema with application model
-- Adds columns needed for full proposal functionality (type, text fields, flags, ordering)
-- Legacy columns (proposal_text, confidence_score) are retained for backward compatibility

-- Add new columns to match SQLite AIProposals schema
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS type TEXT;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS original_after_text TEXT;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS original_reason TEXT;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS modified_after_text TEXT;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS modified_reason TEXT;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS is_selected BOOLEAN DEFAULT false;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS is_modified BOOLEAN DEFAULT false;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT false;
ALTER TABLE ai_proposals ADD COLUMN IF NOT EXISTS selected_order INTEGER;

-- Add index for efficient ordering by selected_order
CREATE INDEX IF NOT EXISTS idx_proposals_selected_order ON ai_proposals(history_id, selected_order);
