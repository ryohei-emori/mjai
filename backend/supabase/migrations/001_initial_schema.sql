-- Supabase SQL Editorで実行する初期スキーマ

-- Sessionsテーブル
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    name TEXT,
    correction_count INTEGER DEFAULT 0,
    is_open BOOLEAN DEFAULT true
);

-- CorrectionHistoriesテーブル
CREATE TABLE correction_histories (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    original_text TEXT NOT NULL,
    instruction_prompt TEXT,
    target_text TEXT,
    combined_comment TEXT,
    selected_proposal_ids TEXT,
    custom_proposals TEXT
);

-- AIProposalsテーブル
CREATE TABLE ai_proposals (
    proposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    history_id UUID REFERENCES correction_histories(history_id) ON DELETE CASCADE,
    proposal_text TEXT NOT NULL,
    confidence_score REAL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックスの作成
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX idx_histories_session_id ON correction_histories(session_id);
CREATE INDEX idx_histories_timestamp ON correction_histories(timestamp DESC);
CREATE INDEX idx_proposals_history_id ON ai_proposals(history_id);

-- RLS (Row Level Security) の有効化
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE correction_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_proposals ENABLE ROW LEVEL SECURITY;

-- 基本的なポリシー（必要に応じて調整）
CREATE POLICY "Allow all operations for authenticated users" ON sessions FOR ALL USING (true);
CREATE POLICY "Allow all operations for authenticated users" ON correction_histories FOR ALL USING (true);
CREATE POLICY "Allow all operations for authenticated users" ON ai_proposals FOR ALL USING (true); 