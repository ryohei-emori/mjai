import os
import asyncpg
import sqlite3
from typing import List, Dict, Optional
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

# Supabase接続設定
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# DBファイルを backend/db/app.db に移動
# backend/app/db_helper.py から backend/db/app.db への相対パス
DB_PATH = Path(__file__).resolve().parent.parent / 'db' / 'app.db'

@contextmanager
def get_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# セッション一覧取得
async def fetch_sessions():
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
                s.session_id AS "sessionId", 
                s.name, 
                s.created_at AS "createdAt", 
                s.updated_at AS "updatedAt",
                COUNT(h.history_id) AS "correctionCount"
            FROM sessions s
            LEFT JOIN correction_histories h ON s.session_id = h.session_id
            GROUP BY s.session_id, s.name, s.created_at, s.updated_at
            ORDER BY s.updated_at DESC
            '''
        )
        return [dict(row) for row in rows]

# セッション追加
async def insert_session(session):
    async with get_db() as conn:
        await conn.execute(
            '''
            INSERT INTO sessions (session_id, created_at, updated_at, name, correction_count, is_open) 
            VALUES ($1, $2, $3, $4, $5, $6)
            ''',
            session['session_id'],
            session['created_at'],
            session['updated_at'],
            session.get('name'),
            session.get('correction_count', 0),
            session.get('is_open', True)
        )

# セッション削除
async def delete_session(session_id):
    async with get_db() as conn:
        # セッションに関連する履歴を取得
        histories = await fetch_histories_by_session(session_id)
        
        # 各履歴に関連する提案を削除
        for history in histories:
            await conn.execute('DELETE FROM ai_proposals WHERE history_id = $1', history['history_id'])
        
        # 履歴を削除
        await conn.execute('DELETE FROM correction_histories WHERE session_id = $1', session_id)
        
        # セッションを削除
        await conn.execute('DELETE FROM sessions WHERE session_id = $1', session_id)

# セッション更新
async def update_session(session_id, updates):
    async with get_db() as conn:
        # 更新可能なフィールドをチェック
        allowed_fields = ['name', 'correction_count', 'is_open', 'updated_at']
        update_fields = []
        update_values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f'{field} = ${len(update_values) + 1}')
                update_values.append(value)
        
        if update_fields:
            update_values.append(session_id)
            query = f'UPDATE sessions SET {", ".join(update_fields)} WHERE session_id = ${len(update_values)}'
            await conn.execute(query, *update_values)

# セッション取得
async def fetch_session(session_id):
    async with get_db() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM sessions WHERE session_id = $1', session_id
        )
        return dict(row) if row else None

async def fetch_histories_by_session(session_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            'SELECT * FROM correction_histories WHERE session_id = $1 ORDER BY timestamp DESC', session_id
        )
        return [dict(row) for row in rows]

async def insert_history(history):
    async with get_db() as conn:
        print(f"[insert_history] session_id: {history.get('session_id')} type: {type(history.get('session_id'))}")
        await conn.execute(
            '''
            INSERT INTO correction_histories (history_id, session_id, timestamp, original_text, instruction_prompt, target_text, combined_comment, selected_proposal_ids, custom_proposals) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
            history['history_id'],
            history['session_id'],
            history['timestamp'],
            history['original_text'],
            history.get('instruction_prompt'),
            history.get('target_text'),
            history.get('combined_comment'),
            history.get('selected_proposal_ids'),
            history.get('custom_proposals')
        )

# 既存のSQLite関数をPostgreSQL用に変換
async def fetch_proposals_by_history(history_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            'SELECT * FROM ai_proposals WHERE history_id = $1 ORDER BY created_at DESC', history_id
        )
        return [dict(row) for row in rows]

async def insert_proposal(proposal):
    async with get_db() as conn:
        await conn.execute(
            '''
            INSERT INTO ai_proposals (proposal_id, history_id, proposal_text, confidence_score, created_at) 
            VALUES ($1, $2, $3, $4, $5)
            ''',
            proposal['proposal_id'],
            proposal['history_id'],
            proposal['proposal_text'],
            proposal.get('confidence_score'),
            proposal.get('created_at')
        )

# SQLite用の関数
def fetch_sessions_sqlite():
    with get_sqlite_db() as conn:
        cur = conn.execute('''
            SELECT 
                s.sessionId AS sessionId,
                s.name,
                s.createdAt AS createdAt,
                s.updatedAt AS updatedAt,
                COUNT(h.historyId) AS correctionCount,
                s.isOpen
            FROM Sessions s
            LEFT JOIN CorrectionHistories h ON s.sessionId = h.sessionId
            GROUP BY s.sessionId, s.name, s.createdAt, s.updatedAt, s.isOpen
            ORDER BY s.updatedAt DESC
        ''')
        return [dict(row) for row in cur.fetchall()]

def insert_session_sqlite(session):
    with get_sqlite_db() as conn:
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

def delete_session_sqlite(session_id):
    with get_sqlite_db() as conn:
        # セッションに関連する履歴を取得
        histories = fetch_histories_by_session_sqlite(session_id)
        
        # 各履歴に関連する提案を削除
        for history in histories:
            conn.execute('DELETE FROM AIProposals WHERE historyId = ?', (history['historyId'],))
        
        # 履歴を削除
        conn.execute('DELETE FROM CorrectionHistories WHERE sessionId = ?', (session_id,))
        
        # セッションを削除
        conn.execute('DELETE FROM Sessions WHERE sessionId = ?', (session_id,))
        
        conn.commit()

def update_session_sqlite(session_id, updates):
    with get_sqlite_db() as conn:
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

def fetch_session_sqlite(session_id):
    with get_sqlite_db() as conn:
        cur = conn.execute('SELECT * FROM Sessions WHERE sessionId = ?', (session_id,))
        row = cur.fetchone()
        return dict(row) if row else None

def fetch_histories_by_session_sqlite(session_id):
    with get_sqlite_db() as conn:
        cur = conn.execute('SELECT * FROM CorrectionHistories WHERE sessionId = ? ORDER BY timestamp DESC', (session_id,))
        return [dict(row) for row in cur.fetchall()]

def insert_history_sqlite(history):
    import json
    # SQLite用はキャメルケースでアクセス
    print(f"[insert_history_sqlite] session_id: {history.get('sessionId')} type: {type(history.get('sessionId'))}")
    with get_sqlite_db() as conn:
        conn.execute(
            'INSERT INTO CorrectionHistories (historyId, sessionId, timestamp, originalText, instructionPrompt, targetText, combinedComment, selectedProposalIds, customProposals) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                history.get('historyId'),
                history.get('sessionId'),
                history.get('timestamp'),
                history.get('originalText'),
                history.get('instructionPrompt'),
                history.get('targetText'),
                history.get('combinedComment'),
                json.dumps(history.get('selectedProposalIds')) if history.get('selectedProposalIds') is not None else None,
                json.dumps(history.get('customProposals')) if history.get('customProposals') is not None else None
            )
        )
        conn.commit()

def fetch_proposals_by_history_sqlite(history_id):
    with get_sqlite_db() as conn:
        cur = conn.execute('SELECT * FROM AIProposals WHERE historyId = ? ORDER BY selectedOrder ASC', (history_id,))
        return [dict(row) for row in cur.fetchall()]

def insert_proposal_sqlite(proposal):
    with get_sqlite_db() as conn:
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