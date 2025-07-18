-- Sessions: ユーザーごとの作業セッション
CREATE TABLE IF NOT EXISTS Sessions (
    sessionId TEXT PRIMARY KEY,
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL,
    name TEXT,
    correctionCount INTEGER,
    isOpen INTEGER
);

-- CorrectionHistories: 各セッション内の添削履歴
CREATE TABLE IF NOT EXISTS CorrectionHistories (
    historyId TEXT PRIMARY KEY,
    sessionId TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    originalText TEXT NOT NULL,
    instructionPrompt TEXT,
    targetText TEXT NOT NULL,
    combinedComment TEXT,
    selectedProposalIds TEXT, -- JSON文字列
    customProposals TEXT,     -- JSON文字列
    FOREIGN KEY (sessionId) REFERENCES Sessions(sessionId)
);

-- AIProposals: AI生成・カスタム提案の詳細
CREATE TABLE IF NOT EXISTS AIProposals (
    proposalId TEXT PRIMARY KEY,
    historyId TEXT NOT NULL,
    type TEXT NOT NULL, -- 'AI' or 'Custom'
    originalAfterText TEXT NOT NULL,
    originalReason TEXT,
    modifiedAfterText TEXT,
    modifiedReason TEXT,
    isSelected INTEGER NOT NULL,
    isModified INTEGER NOT NULL,
    isCustom INTEGER, -- 拡張: カスタム提案フラグ
    selectedOrder INTEGER, -- 拡張: 選択順序
    FOREIGN KEY (historyId) REFERENCES CorrectionHistories(historyId)
); 