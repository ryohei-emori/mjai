import sqlite3
from pathlib import Path
from contextlib import contextmanager
import os

# DBファイルパスを相対パスで設定（PYTHONPATH=.により相対パスでアクセス可能）
DB_PATH = Path("db/app.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# 例: セッション一覧取得
def fetch_sessions():
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM Sessions ORDER BY updatedAt DESC')
        return [dict(row) for row in cur.fetchall()]

# 例: セッション追加
def insert_session(session):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO Sessions (sessionId, createdAt, updatedAt, name, correctionCount, isOpen) VALUES (?, ?, ?, ?, ?, ?)',
            (
                session['sessionId'],
                session['createdAt'],
                session['updatedAt'],
                session.get('name'),
                session.get('correctionCount', 0),
                session.get('isOpen', 1)
            )
        )
        conn.commit()

# セッション削除
def delete_session(session_id):
    with get_db() as conn:
        # セッションに関連する履歴を取得
        histories = fetch_histories_by_session(session_id)
        
        # 各履歴に関連する提案を削除
        for history in histories:
            conn.execute('DELETE FROM AIProposals WHERE historyId = ?', (history['historyId'],))
        
        # 履歴を削除
        conn.execute('DELETE FROM CorrectionHistories WHERE sessionId = ?', (session_id,))
        
        # セッションを削除
        conn.execute('DELETE FROM Sessions WHERE sessionId = ?', (session_id,))
        
        conn.commit()

# セッション更新
def update_session(session_id, updates):
    with get_db() as conn:
        # 更新可能なフィールドをチェック
        allowed_fields = ['name', 'correctionCount', 'isOpen', 'updatedAt']
        update_fields = []
        update_values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f'{field} = ?')
                update_values.append(value)
        
        if update_fields:
            update_values.append(session_id)
            query = f'UPDATE Sessions SET {", ".join(update_fields)} WHERE sessionId = ?'
            conn.execute(query, update_values)
            conn.commit()

# セッション取得
def fetch_session(session_id):
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM Sessions WHERE sessionId = ?', (session_id,))
        row = cur.fetchone()
        return dict(row) if row else None

# 必要に応じてCorrectionHistories, AIProposalsのCRUDも追加予定 

def fetch_histories_by_session(session_id):
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM CorrectionHistories WHERE sessionId = ? ORDER BY timestamp DESC', (session_id,))
        return [dict(row) for row in cur.fetchall()]

def insert_history(history):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO CorrectionHistories (historyId, sessionId, timestamp, originalText, instructionPrompt, targetText, combinedComment, selectedProposalIds, customProposals) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                history['historyId'],
                history['sessionId'],
                history['timestamp'],
                history['originalText'],
                history.get('instructionPrompt'),
                history['targetText'],
                history.get('combinedComment'),
                history.get('selectedProposalIds'),
                history.get('customProposals')
            )
        )
        conn.commit()

def fetch_proposals_by_history(history_id):
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM AIProposals WHERE historyId = ? ORDER BY selectedOrder ASC', (history_id,))
        return [dict(row) for row in cur.fetchall()]

def insert_proposal(proposal):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO AIProposals (proposalId, historyId, type, originalAfterText, originalReason, modifiedAfterText, modifiedReason, isSelected, isModified, isCustom, selectedOrder) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                proposal['proposalId'],
                proposal['historyId'],
                proposal['type'],
                proposal['originalAfterText'],
                proposal.get('originalReason'),
                proposal.get('modifiedAfterText'),
                proposal.get('modifiedReason'),
                proposal['isSelected'],
                proposal['isModified'],
                proposal.get('isCustom', 0),
                proposal.get('selectedOrder')
            )
        )
        conn.commit() 