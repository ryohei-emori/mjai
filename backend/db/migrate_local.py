import sqlite3
import asyncio
import asyncpg
from pathlib import Path
import uuid
from datetime import datetime

# SQLite DBのパス
DB_PATH = Path(__file__).resolve().parent / 'app.db'

# ローカルPostgreSQL接続URL
LOCAL_DATABASE_URL = "postgresql://localhost/mjai_temp"

async def migrate_data():
    print("Starting migration from SQLite to Local PostgreSQL...")
    
    # SQLite接続
    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    
    # データ量を事前に取得
    print("Counting records...")
    session_count = sqlite_conn.execute('SELECT COUNT(*) FROM Sessions').fetchone()[0]
    history_count = sqlite_conn.execute('SELECT COUNT(*) FROM CorrectionHistories').fetchone()[0]
    proposal_count = sqlite_conn.execute('SELECT COUNT(*) FROM AIProposals').fetchone()[0]
    total_records = session_count + history_count + proposal_count
    
    print(f"Found {session_count} sessions, {history_count} histories, {proposal_count} proposals")
    print(f"Total records to migrate: {total_records}")
    print("=" * 50)
    
    # ローカルPostgreSQL接続
    pg_conn = await asyncpg.connect(LOCAL_DATABASE_URL)
    
    try:
        migration_start_time = datetime.now()
        total_migrated = 0
        
        # テーブル作成
        print("\nCreating tables...")
        await pg_conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id UUID PRIMARY KEY,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                name TEXT,
                correction_count INTEGER DEFAULT 0,
                is_open BOOLEAN DEFAULT true
            )
        ''')
        
        await pg_conn.execute('''
            CREATE TABLE IF NOT EXISTS correction_histories (
                history_id UUID PRIMARY KEY,
                session_id UUID REFERENCES sessions(session_id),
                timestamp TIMESTAMP,
                original_text TEXT,
                instruction_prompt TEXT,
                target_text TEXT,
                combined_comment TEXT,
                selected_proposal_ids TEXT,
                custom_proposals TEXT
            )
        ''')
        
        await pg_conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_proposals (
                proposal_id UUID PRIMARY KEY,
                history_id UUID REFERENCES correction_histories(history_id),
                proposal_text TEXT,
                confidence_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        print("✓ Tables created")
        
        # セッションの移行
        print("\nMigrating sessions...")
        cursor = sqlite_conn.execute('SELECT * FROM Sessions')
        sessions = cursor.fetchall()
        
        session_id_map = {}
        history_id_map = {}
        
        session_data = []
        for session in sessions:
            session_dict = dict(session)
            original_session_id = session_dict.get('sessionId')
            
            session_id = original_session_id
            if not is_valid_uuid(session_id):
                session_id = str(uuid.uuid4())
            
            created_at = parse_timestamp(session_dict.get('createdAt'))
            updated_at = parse_timestamp(session_dict.get('updatedAt'))
            
            session_data.append((
                session_id,
                created_at,
                updated_at,
                session_dict.get('name'),
                session_dict.get('correctionCount', 0),
                bool(session_dict.get('isOpen', 1))
            ))
            session_id_map[original_session_id] = session_id
        
        if session_data:
            start_time = datetime.now()
            await pg_conn.executemany('''
                INSERT INTO sessions 
                (session_id, created_at, updated_at, name, correction_count, is_open)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', session_data)
            elapsed = (datetime.now() - start_time).total_seconds()
            total_migrated += len(session_data)
            print(f"✓ Migrated {len(session_data)} sessions in {elapsed:.1f}s")
        
        # 履歴の移行
        print("\nMigrating correction histories...")
        cursor = sqlite_conn.execute('SELECT * FROM CorrectionHistories')
        histories = cursor.fetchall()
        
        history_data = []
        skipped_histories = 0
        for history in histories:
            history_dict = dict(history)
            
            original_history_id = history_dict.get('historyId')
            history_id = original_history_id
            if not is_valid_uuid(history_id):
                history_id = str(uuid.uuid4())
            
            orig_session_ref = history_dict.get('sessionId')
            session_id = orig_session_ref
            if not is_valid_uuid(session_id):
                mapped = session_id_map.get(orig_session_ref)
                if mapped:
                    session_id = mapped
                else:
                    # 無効なセッションIDを持つ履歴はスキップ
                    print(f"Warning: Skipping history with invalid session_id '{orig_session_ref}'")
                    skipped_histories += 1
                    continue
            
            timestamp = parse_timestamp(history_dict.get('timestamp'))
            
            history_data.append((
                history_id,
                session_id,
                timestamp,
                history_dict.get('originalText') or history_dict.get('original_text'),
                history_dict.get('instructionPrompt') or history_dict.get('instruction_prompt'),
                history_dict.get('targetText') or history_dict.get('target_text'),
                history_dict.get('combinedComment') or history_dict.get('combined_comment'),
                history_dict.get('selectedProposalIds'),
                history_dict.get('customProposals')
            ))
            history_id_map[original_history_id] = history_id
        
        if skipped_histories > 0:
            print(f"Skipped {skipped_histories} histories with invalid session references")
        
        if history_data:
            start_time = datetime.now()
            await pg_conn.executemany('''
                INSERT INTO correction_histories 
                (history_id, session_id, timestamp, original_text, instruction_prompt, 
                target_text, combined_comment, selected_proposal_ids, custom_proposals)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', history_data)
            elapsed = (datetime.now() - start_time).total_seconds()
            total_migrated += len(history_data)
            print(f"✓ Migrated {len(history_data)} histories in {elapsed:.1f}s")
        
        # AI提案の移行
        print("\nMigrating AI proposals...")
        cursor = sqlite_conn.execute('SELECT * FROM AIProposals')
        proposals = cursor.fetchall()
        
        proposal_data = []
        skipped_proposals = 0
        for proposal in proposals:
            proposal_dict = dict(proposal)
            
            original_proposal_id = proposal_dict.get('proposalId')
            proposal_id = original_proposal_id
            if not is_valid_uuid(proposal_id):
                proposal_id = str(uuid.uuid4())
            
            orig_history_ref = proposal_dict.get('historyId')
            mapped_history_id = orig_history_ref
            if not is_valid_uuid(orig_history_ref):
                mapped = history_id_map.get(orig_history_ref)
                if mapped:
                    mapped_history_id = mapped
                else:
                    # 無効な履歴IDを持つ提案はスキップ
                    skipped_proposals += 1
                    continue
            
            confidence_score = None
            if 'isSelected' in proposal_dict and 'selectedOrder' in proposal_dict:
                if proposal_dict.get('isSelected'):
                    confidence_score = 1.0 - (proposal_dict.get('selectedOrder') or 0) * 0.1
            
            proposal_data.append((
                proposal_id,
                mapped_history_id,
                proposal_dict.get('originalAfterText') or proposal_dict.get('proposal_text') or '',
                confidence_score
            ))
        
        if skipped_proposals > 0:
            print(f"Skipped {skipped_proposals} proposals with invalid history references")
        
        # バッチで挿入
        batch_size = 1000
        total_batches = (len(proposal_data) + batch_size - 1) // batch_size
        
        for i in range(0, len(proposal_data), batch_size):
            batch = proposal_data[i:i + batch_size]
            batch_start_time = datetime.now()
            
            await pg_conn.executemany('''
                INSERT INTO ai_proposals 
                (proposal_id, history_id, proposal_text, confidence_score, created_at)
                VALUES ($1, $2, $3, $4, NOW())
            ''', batch)
            
            batch_elapsed = (datetime.now() - batch_start_time).total_seconds()
            total_migrated += len(batch)
            batch_num = i//batch_size + 1
            
            total_elapsed = (datetime.now() - migration_start_time).total_seconds()
            remaining = total_records - total_migrated
            if total_migrated > 0:
                avg_time_per_record = total_elapsed / total_migrated
                estimated_remaining = avg_time_per_record * remaining
                progress_pct = (total_migrated / total_records) * 100
                print(f"✓ Batch {batch_num}/{total_batches}: {len(batch)} proposals in {batch_elapsed:.1f}s")
                print(f"  Progress: {total_migrated}/{total_records} ({progress_pct:.1f}%) | Est. remaining: {estimated_remaining:.1f}s")
        
        total_time = (datetime.now() - migration_start_time).total_seconds()
        print("\n" + "=" * 50)
        print(f"✓ Migration to local PostgreSQL completed!")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Total records migrated: {total_migrated}")
        print("=" * 50)
        
    finally:
        sqlite_conn.close()
        await pg_conn.close()

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def parse_timestamp(ts_str):
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt
    except ValueError:
        return datetime.now()

if __name__ == '__main__':
    asyncio.run(migrate_data())
