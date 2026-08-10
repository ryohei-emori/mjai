import os
import asyncpg
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime

# Supabase Postgres接続設定
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def get_db():
    # statement_cache_size=0 is required for Supabase's PgBouncer transaction
    # pooler (port 6543); otherwise asyncpg hits DuplicatePreparedStatementError.
    conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
    try:
        yield conn
    finally:
        await conn.close()

# セッション一覧取得（アクティブなセッションのみ）
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
            WHERE s.status = 'active' OR s.status IS NULL
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

# セッションアーカイブ（ソフトデリート）
async def delete_session(session_id):
    async with get_db() as conn:
        await conn.execute(
            "UPDATE sessions SET status = 'archived' WHERE session_id = $1",
            session_id
        )

# セッション更新
async def update_session(session_id, updates):
    async with get_db() as conn:
        # Map camelCase to snake_case for allowed fields
        field_mapping = {
            'name': 'name',
            'correctionCount': 'correction_count',
            'correction_count': 'correction_count',
            'isOpen': 'is_open',
            'is_open': 'is_open',
            'updatedAt': 'updated_at',
            'updated_at': 'updated_at'
        }
        
        update_fields = []
        update_values = []
        
        for field, value in updates.items():
            if field in field_mapping:
                snake_field = field_mapping[field]
                if snake_field not in [f.split(' = ')[0] for f in update_fields]:
                    update_fields.append(f'{snake_field} = ${len(update_values) + 1}')
                    update_values.append(value)
        
        if update_fields:
            update_values.append(session_id)
            query = f'UPDATE sessions SET {", ".join(update_fields)} WHERE session_id = ${len(update_values)}'
            await conn.execute(query, *update_values)

# セッション取得（camelCase dictを返す）
async def fetch_session(session_id):
    async with get_db() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM sessions WHERE session_id = $1', session_id
        )
        if row:
            return {
                'sessionId': str(row['session_id']),
                'name': row['name'],
                'createdAt': row['created_at'].isoformat() if isinstance(row['created_at'], datetime) else row['created_at'],
                'updatedAt': row['updated_at'].isoformat() if isinstance(row['updated_at'], datetime) else row['updated_at'],
                'correctionCount': row.get('correction_count', 0),
                'isOpen': row.get('is_open', True),
                'status': row.get('status', 'active')
            }
        return None

# 履歴一覧取得
async def fetch_histories_by_session(session_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
                history_id AS "historyId",
                session_id AS "sessionId",
                timestamp,
                original_text AS "originalText",
                instruction_prompt AS "instructionPrompt",
                target_text AS "targetText",
                combined_comment AS "combinedComment",
                selected_proposal_ids AS "selectedProposalIds",
                custom_proposals AS "customProposals"
            FROM correction_histories 
            WHERE session_id = $1 
            ORDER BY timestamp DESC
            ''', session_id
        )
        return [dict(row) for row in rows]

# 履歴追加（作成したオブジェクトを返す）
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
        # Return camelCase dict
        return {
            'historyId': history['history_id'],
            'sessionId': history['session_id'],
            'timestamp': history['timestamp'],
            'originalText': history['original_text'],
            'instructionPrompt': history.get('instruction_prompt'),
            'targetText': history.get('target_text'),
            'combinedComment': history.get('combined_comment'),
            'selectedProposalIds': history.get('selected_proposal_ids'),
            'customProposals': history.get('custom_proposals')
        }

# 提案一覧取得（フル field set, camelCase)
async def fetch_proposals_by_history(history_id):
    async with get_db() as conn:
        rows = await conn.fetch(
            '''
            SELECT 
                proposal_id AS "proposalId",
                history_id AS "historyId",
                type,
                original_after_text AS "originalAfterText",
                original_reason AS "originalReason",
                modified_after_text AS "modifiedAfterText",
                modified_reason AS "modifiedReason",
                is_selected AS "isSelected",
                is_modified AS "isModified",
                is_custom AS "isCustom",
                selected_order AS "selectedOrder",
                created_at AS "createdAt"
            FROM ai_proposals 
            WHERE history_id = $1 
            ORDER BY selected_order ASC NULLS FIRST, created_at DESC
            ''', history_id
        )
        return [dict(row) for row in rows]

# 提案追加（フル field set）
async def insert_proposal(proposal):
    async with get_db() as conn:
        # Map camelCase to snake_case
        proposal_id = proposal.get('proposalId') or proposal.get('proposal_id')
        history_id = proposal.get('historyId') or proposal.get('history_id')
        
        await conn.execute(
            '''
            INSERT INTO ai_proposals (
                proposal_id, history_id, type, 
                original_after_text, original_reason, 
                modified_after_text, modified_reason, 
                is_selected, is_modified, is_custom, selected_order, created_at
            ) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''',
            proposal_id,
            history_id,
            proposal.get('type'),
            proposal.get('originalAfterText') or proposal.get('original_after_text'),
            proposal.get('originalReason') or proposal.get('original_reason'),
            proposal.get('modifiedAfterText') or proposal.get('modified_after_text'),
            proposal.get('modifiedReason') or proposal.get('modified_reason'),
            proposal.get('isSelected', False) or proposal.get('is_selected', False),
            proposal.get('isModified', False) or proposal.get('is_modified', False),
            proposal.get('isCustom', False) or proposal.get('is_custom', False),
            proposal.get('selectedOrder') or proposal.get('selected_order'),
            proposal.get('createdAt') or proposal.get('created_at') or datetime.now()
        )
        # Return camelCase dict
        return {
            'proposalId': proposal_id,
            'historyId': history_id,
            'type': proposal.get('type'),
            'originalAfterText': proposal.get('originalAfterText') or proposal.get('original_after_text'),
            'originalReason': proposal.get('originalReason') or proposal.get('original_reason'),
            'modifiedAfterText': proposal.get('modifiedAfterText') or proposal.get('modified_after_text'),
            'modifiedReason': proposal.get('modifiedReason') or proposal.get('modified_reason'),
            'isSelected': proposal.get('isSelected', False) or proposal.get('is_selected', False),
            'isModified': proposal.get('isModified', False) or proposal.get('is_modified', False),
            'isCustom': proposal.get('isCustom', False) or proposal.get('is_custom', False),
            'selectedOrder': proposal.get('selectedOrder') or proposal.get('selected_order')
        }
