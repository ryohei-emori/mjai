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

# セッション一覧取得（API契約に合わせてカラム名をキャメルケースで返す）
async def fetch_sessions():
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
              session_id AS "sessionId",
              created_at AS "createdAt",
              updated_at AS "updatedAt",
              name AS "name",
              correction_count AS "correctionCount",
              is_open AS "isOpen"
            FROM sessions
            ORDER BY updated_at DESC
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
            session['sessionId'],
            session['createdAt'],
            session['updatedAt'],
            session.get('name'),
            session.get('correctionCount', 0),
            bool(session.get('isOpen', True))
        )

# セッション削除
async def delete_session(session_id):
    async with get_db() as conn:
        # 外部キー ON DELETE CASCADE を利用
        await conn.execute('DELETE FROM sessions WHERE session_id = $1', session_id)

# セッション更新
async def update_session(session_id, updates):
    async with get_db() as conn:
        # camelCase → snake_case へマッピング
        field_map = {
            'name': 'name',
            'correctionCount': 'correction_count',
            'isOpen': 'is_open',
            'updatedAt': 'updated_at',
        }
        update_fields = []
        update_values = []
        for camel, value in updates.items():
            snake = field_map.get(camel)
            if snake is not None:
                update_fields.append(f'{snake} = ${len(update_values) + 1}')
                # boolean 正規化
                if snake in ('is_open',):
                    value = bool(value)
                update_values.append(value)
        if update_fields:
            update_values.append(session_id)
            query = f'UPDATE sessions SET {", ".join(update_fields)} WHERE session_id = ${len(update_values)}'
            await conn.execute(query, *update_values)

# セッション取得
async def fetch_session(session_id):
    async with get_db() as conn:
        row = await conn.fetchrow(
            '''
            SELECT 
              session_id AS "sessionId",
              created_at AS "createdAt",
              updated_at AS "updatedAt",
              name AS "name",
              correction_count AS "correctionCount",
              is_open AS "isOpen"
            FROM sessions WHERE session_id = $1
            ''',
            session_id
        )
        return dict(row) if row else None

async def fetch_histories_by_session(session_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
              history_id AS "historyId",
              session_id AS "sessionId",
              timestamp AS "timestamp",
              original_text AS "originalText",
              instruction_prompt AS "instructionPrompt",
              target_text AS "targetText",
              combined_comment AS "combinedComment",
              selected_proposal_ids AS "selectedProposalIds",
              custom_proposals AS "customProposals"
            FROM correction_histories
            WHERE session_id = $1
            ORDER BY timestamp DESC
            ''',
            session_id
        )
        return [dict(row) for row in rows]

async def insert_history(history):
    async with get_db() as conn:
        await conn.execute(
            '''
            INSERT INTO correction_histories (
              history_id, session_id, timestamp, original_text, instruction_prompt,
              target_text, combined_comment, selected_proposal_ids, custom_proposals
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ''',
            history['historyId'],
            history['sessionId'],
            history['timestamp'],
            history['originalText'],
            history.get('instructionPrompt'),
            history.get('targetText'),
            history.get('combinedComment'),
            history.get('selectedProposalIds'),
            history.get('customProposals')
        )

# 既存のSQLite関数をPostgreSQL用に変換
async def fetch_proposals_by_history(history_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
              proposal_id AS "proposalId",
              history_id AS "historyId",
              type AS "type",
              original_after_text AS "originalAfterText",
              original_reason AS "originalReason",
              modified_after_text AS "modifiedAfterText",
              modified_reason AS "modifiedReason",
              (is_selected)::int AS "isSelected",
              (is_modified)::int AS "isModified",
              (is_custom)::int AS "isCustom",
              selected_order AS "selectedOrder",
              created_at AS "createdAt"
            FROM ai_proposals
            WHERE history_id = $1
            ORDER BY created_at DESC
            ''',
            history_id
        )
        return [dict(row) for row in rows]

async def insert_proposal(proposal):
    async with get_db() as conn:
        await conn.execute(
            '''
            INSERT INTO ai_proposals (
              proposal_id, history_id, type, original_after_text, original_reason,
              modified_after_text, modified_reason, is_selected, is_modified, is_custom, selected_order, created_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            ''',
            proposal['proposalId'],
            proposal['historyId'],
            proposal['type'],
            proposal['originalAfterText'],
            proposal.get('originalReason'),
            proposal.get('modifiedAfterText'),
            proposal.get('modifiedReason'),
            int(proposal.get('isSelected', 0)) == 1,
            int(proposal.get('isModified', 0)) == 1,
            int(proposal.get('isCustom', 0)) == 1,
            proposal.get('selectedOrder'),
            None
        )

# SQLite用の関数
def fetch_sessions_sqlite():
    with get_sqlite_db() as conn:
        cur = conn.execute('SELECT * FROM Sessions ORDER BY updatedAt DESC')
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
    with get_sqlite_db() as conn:
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