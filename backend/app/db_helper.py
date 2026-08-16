import logging
import os
import asyncpg
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

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
                COUNT(h.history_id) FILTER (WHERE h.is_archived = false) AS "correctionCount"
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

# The LLM provenance columns arrive with migration 007, which is applied to the
# shared Supabase project by hand. A deploy can therefore reach production
# before the migration does, and every history read and write names those
# columns — so they are probed once per process instead of assumed. Without
# them the app drops provenance (no model caption) rather than 500-ing on every
# history operation, which is the difference between a missing nicety and an
# unusable workspace.
_HAS_PROVENANCE_COLUMNS: Optional[bool] = None


async def _has_provenance_columns(conn) -> bool:
    global _HAS_PROVENANCE_COLUMNS
    if _HAS_PROVENANCE_COLUMNS is None:
        _HAS_PROVENANCE_COLUMNS = bool(
            await conn.fetchval(
                '''
                SELECT COUNT(*) = 2 FROM information_schema.columns
                WHERE table_name = 'correction_histories'
                  AND column_name IN ('llm_provider', 'llm_model')
                '''
            )
        )
        if not _HAS_PROVENANCE_COLUMNS:
            logger.warning(
                "correction_histories.llm_provider/llm_model are missing; "
                "serving histories without model provenance. Apply "
                "007_history_llm_provenance.sql to start recording it."
            )
    return _HAS_PROVENANCE_COLUMNS


def _history_columns(with_provenance: bool) -> str:
    """Projection shared by every history read."""
    provenance = (
        'llm_provider AS "llmProvider",\n                llm_model AS "llmModel",'
        if with_provenance
        else ''
    )
    return f'''
                history_id AS "historyId",
                session_id AS "sessionId",
                timestamp,
                original_text AS "originalText",
                instruction_prompt AS "instructionPrompt",
                target_text AS "targetText",
                combined_comment AS "combinedComment",
                selected_proposal_ids AS "selectedProposalIds",
                custom_proposals AS "customProposals",
                status,
                overall_comment AS "overallComment",
                provider,
                {provenance}
                client_job_id AS "clientJobId"
    '''


# 履歴一覧取得（アーカイブ済みラウンドを除く）
async def fetch_histories_by_session(session_id):
    async with get_db() as conn:
        columns = _history_columns(await _has_provenance_columns(conn))
        rows = await conn.fetch(
            f'''
            SELECT {columns}
            FROM correction_histories 
            WHERE session_id = $1 AND is_archived = false
            ORDER BY timestamp DESC
            ''', session_id
        )
        return [dict(row) for row in rows]

# 履歴ラウンドのアーカイブ（ソフトデリート）
async def archive_history(history_id):
    async with get_db() as conn:
        await conn.execute(
            "UPDATE correction_histories SET is_archived = true WHERE history_id = $1",
            history_id
        )

def _normalize_history_status(value, default='confirmed'):
    if value is None or value == '':
        return default
    status = str(value).strip().lower()
    if status not in ('pending', 'confirmed', 'failed'):
        raise ValueError(f"Invalid history status: {value}")
    return status


def _history_row_to_camel(history):
    return {
        'historyId': history['history_id'],
        'sessionId': history['session_id'],
        'timestamp': history['timestamp'],
        'originalText': history['original_text'],
        'instructionPrompt': history.get('instruction_prompt'),
        'targetText': history.get('target_text'),
        'combinedComment': history.get('combined_comment'),
        'selectedProposalIds': history.get('selected_proposal_ids'),
        'customProposals': history.get('custom_proposals'),
        'status': history.get('status', 'confirmed'),
        'overallComment': history.get('overall_comment'),
        'provider': history.get('provider'),
        'llmProvider': history.get('llm_provider'),
        'llmModel': history.get('llm_model'),
        'clientJobId': history.get('client_job_id'),
    }


# 履歴追加（作成したオブジェクトを返す）
async def insert_history(history):
    status = _normalize_history_status(history.get('status'), default='confirmed')
    overall_comment = history.get('overall_comment')
    if overall_comment is None:
        overall_comment = history.get('combined_comment')
    async with get_db() as conn:
        with_provenance = await _has_provenance_columns(conn)
        columns = [
            'history_id', 'session_id', 'timestamp', 'original_text',
            'instruction_prompt', 'target_text', 'combined_comment',
            'selected_proposal_ids', 'custom_proposals', 'status',
            'overall_comment', 'provider', 'client_job_id',
        ]
        values = [
            history['history_id'],
            history['session_id'],
            history['timestamp'],
            history['original_text'],
            history.get('instruction_prompt'),
            history.get('target_text'),
            history.get('combined_comment'),
            history.get('selected_proposal_ids'),
            history.get('custom_proposals'),
            status,
            overall_comment,
            history.get('provider'),
            history.get('client_job_id'),
        ]
        if with_provenance:
            columns += ['llm_provider', 'llm_model']
            values += [history.get('llm_provider'), history.get('llm_model')]
        placeholders = ', '.join(f'${i}' for i in range(1, len(values) + 1))
        await conn.execute(
            f'''
            INSERT INTO correction_histories ({', '.join(columns)})
            VALUES ({placeholders})
            ''',
            *values,
        )
        stored = {
            **history,
            'status': status,
            'overall_comment': overall_comment,
        }
        if not with_provenance:
            # Do not claim provenance the row does not carry.
            stored.pop('llm_provider', None)
            stored.pop('llm_model', None)
        return _history_row_to_camel(stored)


async def update_history(history_id, updates):
    """Update a correction_histories row. Returns camelCase dict or None if missing."""
    allowed = {
        'combined_comment': 'combined_comment',
        'combinedComment': 'combined_comment',
        'overall_comment': 'overall_comment',
        'overallComment': 'overall_comment',
        'selected_proposal_ids': 'selected_proposal_ids',
        'selectedProposalIds': 'selected_proposal_ids',
        'custom_proposals': 'custom_proposals',
        'customProposals': 'custom_proposals',
        'status': 'status',
        'provider': 'provider',
        # Provenance is only written when explicitly sent, so a confirm/update
        # that omits these keys leaves the generating model on the row.
        'llm_provider': 'llm_provider',
        'llmProvider': 'llm_provider',
        'llm_model': 'llm_model',
        'llmModel': 'llm_model',
        'client_job_id': 'client_job_id',
        'clientJobId': 'client_job_id',
        'instruction_prompt': 'instruction_prompt',
        'instructionPrompt': 'instruction_prompt',
    }
    async with get_db() as conn:
        with_provenance = await _has_provenance_columns(conn)
        columns = _history_columns(with_provenance)
        set_parts = []
        params = []
        for key, column in allowed.items():
            if key not in updates:
                continue
            if column in ('llm_provider', 'llm_model') and not with_provenance:
                continue
            value = updates[key]
            if column == 'status':
                value = _normalize_history_status(value)
            # Avoid duplicate column sets when both camel and snake keys are present
            if any(part.startswith(f"{column} =") for part in set_parts):
                continue
            params.append(value)
            set_parts.append(f"{column} = ${len(params)}")

        if not set_parts:
            row = await conn.fetchrow(
                f'''
                SELECT {columns}
                FROM correction_histories
                WHERE history_id = $1 AND is_archived = false
                ''',
                history_id,
            )
            return dict(row) if row else None

        params.append(history_id)
        row = await conn.fetchrow(
            f'''
            UPDATE correction_histories
            SET {", ".join(set_parts)}
            WHERE history_id = ${len(params)} AND is_archived = false
            RETURNING {columns}
            ''',
            *params,
        )
        return dict(row) if row else None

# --- app_settings (global key/value settings shared by all users) -----------
# Row absence means "built-in code default in effect" (see migration 006), so
# reset deletes the row instead of writing the default text into it.

async def fetch_setting(setting_key):
    """Return one setting as camelCase dict, or None when unset."""
    async with get_db() as conn:
        row = await conn.fetchrow(
            '''
            SELECT
                setting_key AS "settingKey",
                setting_value AS "settingValue",
                updated_at AS "updatedAt",
                updated_by AS "updatedBy"
            FROM app_settings
            WHERE setting_key = $1
            ''',
            setting_key,
        )
        return dict(row) if row else None


async def upsert_setting(setting_key, setting_value, updated_by=None):
    """Insert or replace a setting, stamping who saved it and when."""
    async with get_db() as conn:
        row = await conn.fetchrow(
            '''
            INSERT INTO app_settings (setting_key, setting_value, updated_at, updated_by)
            VALUES ($1, $2, NOW(), $3)
            ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value,
                    updated_at = EXCLUDED.updated_at,
                    updated_by = EXCLUDED.updated_by
            RETURNING
                setting_key AS "settingKey",
                setting_value AS "settingValue",
                updated_at AS "updatedAt",
                updated_by AS "updatedBy"
            ''',
            setting_key,
            setting_value,
            updated_by,
        )
        return dict(row) if row else None


async def delete_setting(setting_key):
    """Delete a setting so the built-in default applies again. Idempotent."""
    async with get_db() as conn:
        await conn.execute(
            'DELETE FROM app_settings WHERE setting_key = $1',
            setting_key,
        )


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

# camelCase/snake_case のどちらのキーでも値を取得するヘルパー。
# `or` によるフォールバックだと空文字列(falsy)が誤って捨てられ、次のキーの
# 値（大抵は未設定でNone）に置き換わってしまうため、値の有無は `is not None` で判定する。
def _pick(d: dict, *keys, default=None):
    for key in keys:
        value = d.get(key)
        if value is not None:
            return value
    return default


# asyncpgはBOOLEAN列に対してPythonのint(0/1)を渡すと
# `asyncpg.exceptions.DataError: invalid input ... (a boolean is required (got type int))`
# を送出し、INSERT文全体が失敗する。フロントエンドが1/0を送ってくるケースに備えて
# 明示的にPythonのboolへ変換する。
def _coerce_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


# 提案追加（フル field set）
async def insert_proposal(proposal):
    async with get_db() as conn:
        # Map camelCase to snake_case
        proposal_id = _pick(proposal, 'proposalId', 'proposal_id')
        history_id = _pick(proposal, 'historyId', 'history_id')
        proposal_type = _pick(proposal, 'type')
        original_after_text = _pick(proposal, 'originalAfterText', 'original_after_text')
        original_reason = _pick(proposal, 'originalReason', 'original_reason')
        modified_after_text = _pick(proposal, 'modifiedAfterText', 'modified_after_text')
        modified_reason = _pick(proposal, 'modifiedReason', 'modified_reason')
        is_selected = _coerce_bool(_pick(proposal, 'isSelected', 'is_selected'))
        is_modified = _coerce_bool(_pick(proposal, 'isModified', 'is_modified'))
        is_custom = _coerce_bool(_pick(proposal, 'isCustom', 'is_custom'))
        selected_order = _pick(proposal, 'selectedOrder', 'selected_order')
        created_at = _pick(proposal, 'createdAt', 'created_at', default=datetime.now())

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
            proposal_type,
            original_after_text,
            original_reason,
            modified_after_text,
            modified_reason,
            is_selected,
            is_modified,
            is_custom,
            selected_order,
            created_at,
        )
        # Return camelCase dict
        return {
            'proposalId': proposal_id,
            'historyId': history_id,
            'type': proposal_type,
            'originalAfterText': original_after_text,
            'originalReason': original_reason,
            'modifiedAfterText': modified_after_text,
            'modifiedReason': modified_reason,
            'isSelected': is_selected,
            'isModified': is_modified,
            'isCustom': is_custom,
            'selectedOrder': selected_order,
        }


async def update_proposal(proposal_id, updates):
    """Update selection/edit fields on an ai_proposals row. Returns camelCase or None."""
    field_map = {
        'originalAfterText': ('original_after_text', False),
        'original_after_text': ('original_after_text', False),
        'originalReason': ('original_reason', False),
        'original_reason': ('original_reason', False),
        'modifiedAfterText': ('modified_after_text', False),
        'modified_after_text': ('modified_after_text', False),
        'modifiedReason': ('modified_reason', False),
        'modified_reason': ('modified_reason', False),
        'isSelected': ('is_selected', True),
        'is_selected': ('is_selected', True),
        'isModified': ('is_modified', True),
        'is_modified': ('is_modified', True),
        'isCustom': ('is_custom', True),
        'is_custom': ('is_custom', True),
        'selectedOrder': ('selected_order', False),
        'selected_order': ('selected_order', False),
        'type': ('type', False),
    }
    set_parts = []
    params = []
    seen_columns = set()
    for key, (column, is_bool) in field_map.items():
        if key not in updates or column in seen_columns:
            continue
        value = updates[key]
        if is_bool:
            value = _coerce_bool(value)
        seen_columns.add(column)
        params.append(value)
        set_parts.append(f"{column} = ${len(params)}")
    if not set_parts:
        async with get_db() as conn:
            row = await conn.fetchrow(
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
                WHERE proposal_id = $1
                ''',
                proposal_id,
            )
            return dict(row) if row else None

    params.append(proposal_id)
    query = f'''
        UPDATE ai_proposals
        SET {", ".join(set_parts)}
        WHERE proposal_id = ${len(params)}
        RETURNING
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
    '''
    async with get_db() as conn:
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None
