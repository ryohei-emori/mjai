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
        
        for session in sessions:
            # SQLiteのデータを辞書に変換
            session_dict = dict(session)
            
            # UUIDの生成（必要な場合）
            session_id = session_dict['sessionId']
            if not is_valid_uuid(session_id):
                session_id = str(uuid.uuid4())
            
            # タイムスタンプの変換
            created_at = parse_timestamp(session_dict['createdAt'])
            updated_at = parse_timestamp(session_dict['updatedAt'])
            
            # PostgreSQLに挿入
            await pg_conn.execute('''
                INSERT INTO sessions 
                (session_id, created_at, updated_at, name, correction_count, is_open)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''',
                session_id,
                created_at,
                updated_at,
                session_dict['name'],
                session_dict.get('correctionCount', 0),
                bool(session_dict.get('isOpen', 1))
            )
            print(f"Migrated session: {session_id}")

        # 履歴の移行
        print("\nMigrating correction histories...")
        cursor = sqlite_conn.execute('SELECT * FROM CorrectionHistories')
        histories = cursor.fetchall()
        
        for history in histories:
            history_dict = dict(history)
            
            # UUIDの生成（必要な場合）
            history_id = history_dict['historyId']
            if not is_valid_uuid(history_id):
                history_id = str(uuid.uuid4())
            
            # セッションIDの変換（必要な場合）
            session_id = history_dict['sessionId']
            if not is_valid_uuid(session_id):
                # 既に変換済みのセッションIDとマッピングする必要がある場合の処理
                pass
            
            # タイムスタンプの変換
            timestamp = parse_timestamp(history_dict['timestamp'])
            
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
                history_dict['originalText'],
                history_dict.get('instructionPrompt'),
                history_dict['targetText'],
                history_dict.get('combinedComment'),
                selected_proposal_ids,
                custom_proposals
            )
            print(f"Migrated history: {history_id}")

        # AI提案の移行
        print("\nMigrating AI proposals...")
        cursor = sqlite_conn.execute('SELECT * FROM AIProposals')
        proposals = cursor.fetchall()
        
        for proposal in proposals:
            proposal_dict = dict(proposal)
            
            # UUIDの生成（必要な場合）
            proposal_id = proposal_dict['proposalId']
            if not is_valid_uuid(proposal_id):
                proposal_id = str(uuid.uuid4())
            
            # 信頼度スコアの計算（オプション）
            confidence_score = None
            if 'isSelected' in proposal_dict and 'selectedOrder' in proposal_dict:
                if proposal_dict['isSelected']:
                    confidence_score = 1.0 - (proposal_dict['selectedOrder'] or 0) * 0.1
            
            await pg_conn.execute('''
                INSERT INTO ai_proposals 
                (proposal_id, history_id, proposal_text, confidence_score, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            ''',
                proposal_id,
                proposal_dict['historyId'],
                proposal_dict.get('originalAfterText', ''),
                confidence_score
            )
            print(f"Migrated proposal: {proposal_id}")

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
