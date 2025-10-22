import sqlite3
import asyncio
import asyncpg
import os
from pathlib import Path
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

# .envファイルの読み込み
env_path = Path(__file__).resolve().parent.parent.parent / 'conf' / '.env'
load_dotenv(env_path)

# SQLite DBのパス
DB_PATH = Path(__file__).resolve().parent / 'app.db'

# Supabase接続URL（環境変数から取得）
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please check your .env file.")

async def migrate_data():
    print("Starting migration from SQLite to Supabase...")
    
    # SQLite接続
    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Supabase(PostgreSQL)接続
    pg_conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # トランザクション開始
        async with pg_conn.transaction():
            print("Transaction started")
            # セッションの移行
            print("\nMigrating sessions...")
            cursor = sqlite_conn.execute('SELECT * FROM Sessions')
            sessions = cursor.fetchall()

            # マッピングを保持して、後続の履歴・提案で正しい外部キーを使えるようにする
            session_id_map = {}
            history_id_map = {}

            for session in sessions:
                # SQLiteのデータを辞書に変換
                session_dict = dict(session)
                original_session_id = session_dict.get('sessionId')

                # UUIDの生成（必要な場合）
                session_id = original_session_id
                if not is_valid_uuid(session_id):
                    session_id = str(uuid.uuid4())

                # タイムスタンプの変換
                created_at = parse_timestamp(session_dict.get('createdAt'))
                updated_at = parse_timestamp(session_dict.get('updatedAt'))

                # PostgreSQLに挿入
                await pg_conn.execute('''
                    INSERT INTO sessions 
                    (session_id, created_at, updated_at, name, correction_count, is_open)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                    session_id,
                    created_at,
                    updated_at,
                    session_dict.get('name'),
                    session_dict.get('correctionCount', 0),
                    bool(session_dict.get('isOpen', 1))
                )
                session_id_map[original_session_id] = session_id
                print(f"Migrated session: {original_session_id} -> {session_id}")

            # 履歴の移行
            print("\nMigrating correction histories...")
            cursor = sqlite_conn.execute('SELECT * FROM CorrectionHistories')
            histories = cursor.fetchall()

            for history in histories:
                history_dict = dict(history)

                # UUIDの生成（必要な場合）
                original_history_id = history_dict.get('historyId')
                history_id = original_history_id
                if not is_valid_uuid(history_id):
                    history_id = str(uuid.uuid4())

                # セッションIDの変換（マッピングがあればそれを利用）
                orig_session_ref = history_dict.get('sessionId')
                session_id = orig_session_ref
                if not is_valid_uuid(session_id):
                    mapped = session_id_map.get(orig_session_ref)
                    if mapped:
                        session_id = mapped
                    else:
                        # フォールバック: try to use original value as-is
                        print(f"Warning: no mapping found for session_id {orig_session_ref}; using original value")

                # タイムスタンプの変換
                timestamp = parse_timestamp(history_dict.get('timestamp'))

                # JSON文字列の処理
                selected_proposal_ids = history_dict.get('selectedProposalIds')
                custom_proposals = history_dict.get('customProposals')

                await pg_conn.execute('''
                    INSERT INTO correction_histories 
                    (history_id, session_id, timestamp, original_text, instruction_prompt, 
                    target_text, combined_comment, selected_proposal_ids, custom_proposals)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''',
                    history_id,
                    session_id,
                    timestamp,
                    history_dict.get('originalText') or history_dict.get('original_text'),
                    history_dict.get('instructionPrompt') or history_dict.get('instruction_prompt'),
                    history_dict.get('targetText') or history_dict.get('target_text'),
                    history_dict.get('combinedComment') or history_dict.get('combined_comment'),
                    selected_proposal_ids,
                    custom_proposals
                )
                history_id_map[original_history_id] = history_id
                print(f"Migrated history: {original_history_id} -> {history_id}")

            # AI提案の移行
            print("\nMigrating AI proposals...")
            cursor = sqlite_conn.execute('SELECT * FROM AIProposals')
            proposals = cursor.fetchall()

            for proposal in proposals:
                proposal_dict = dict(proposal)

                # UUIDの生成（必要な場合）
                original_proposal_id = proposal_dict.get('proposalId')
                proposal_id = original_proposal_id
                if not is_valid_uuid(proposal_id):
                    proposal_id = str(uuid.uuid4())

                # history_id のマッピングを適用
                orig_history_ref = proposal_dict.get('historyId')
                mapped_history_id = orig_history_ref
                if not is_valid_uuid(orig_history_ref):
                    mapped = history_id_map.get(orig_history_ref)
                    if mapped:
                        mapped_history_id = mapped
                    else:
                        print(f"Warning: no mapping found for history_id {orig_history_ref}; using original value")

                # 信頼度スコアの計算（オプション）
                confidence_score = None
                if 'isSelected' in proposal_dict and 'selectedOrder' in proposal_dict:
                    if proposal_dict.get('isSelected'):
                        confidence_score = 1.0 - (proposal_dict.get('selectedOrder') or 0) * 0.1

                await pg_conn.execute('''
                    INSERT INTO ai_proposals 
                    (proposal_id, history_id, proposal_text, confidence_score, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                ''',
                    proposal_id,
                    mapped_history_id,
                    proposal_dict.get('originalAfterText') or proposal_dict.get('proposal_text') or '',
                    confidence_score
                )
                print(f"Migrated proposal: {original_proposal_id} -> {proposal_id}")

        print("\nMigration completed successfully!")

    finally:
        # 接続のクローズ
        sqlite_conn.close()
        await pg_conn.close()

def is_valid_uuid(val):
    """文字列がUUID形式かどうかを確認"""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def parse_timestamp(ts_str):
    """タイムスタンプ文字列をPostgreSQLのタイムスタンプ形式に変換"""
    if not ts_str:
        return None
    try:
        # ISO形式のタイムスタンプをパース
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt
    except ValueError as e:
        print(f"Warning: Could not parse timestamp {ts_str}: {e}")
        # フォールバック: 現在時刻を使用
        return datetime.now()

if __name__ == '__main__':
    asyncio.run(migrate_data())
