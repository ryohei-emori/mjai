import os
import asyncpg
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

# Supabase接続設定
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# セッション一覧取得
async def fetch_sessions():
    async with get_db() as conn:
        rows = await conn.fetch(
            'SELECT * FROM sessions ORDER BY updated_at DESC'
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