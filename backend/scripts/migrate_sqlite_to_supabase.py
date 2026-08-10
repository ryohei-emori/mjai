#!/usr/bin/env python3
"""
SQLite to Supabase migration script.

Migrates missing data from local SQLite (backend/db/app.db) to Supabase Postgres.
Uses upsert (ON CONFLICT DO NOTHING) to preserve existing Supabase data.

Usage:
    python scripts/migrate_sqlite_to_supabase.py --dry-run  # Show what would be migrated
    python scripts/migrate_sqlite_to_supabase.py --apply    # Actually migrate
"""

import argparse
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
import uuid

import asyncpg
from dotenv import load_dotenv
import os


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DB_PATH = BACKEND_DIR / "db" / "app.db"
CONF_ENV = BACKEND_DIR.parent / "conf" / ".env"


def is_valid_uuid(val: str | None) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def parse_timestamp(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        return datetime.now()


async def get_supabase_ids(conn: asyncpg.Connection) -> dict[str, set[str]]:
    """Get existing IDs from Supabase."""
    result = {
        "sessions": set(),
        "histories": set(),
        "proposals": set(),
    }
    
    rows = await conn.fetch("SELECT session_id FROM sessions")
    result["sessions"] = {str(r["session_id"]) for r in rows}
    
    rows = await conn.fetch("SELECT history_id FROM correction_histories")
    result["histories"] = {str(r["history_id"]) for r in rows}
    
    rows = await conn.fetch("SELECT proposal_id FROM ai_proposals")
    result["proposals"] = {str(r["proposal_id"]) for r in rows}
    
    return result


def get_sqlite_data(sqlite_conn: sqlite3.Connection) -> dict:
    """Get all data from SQLite."""
    sqlite_conn.row_factory = sqlite3.Row
    
    sessions = [dict(row) for row in sqlite_conn.execute("SELECT * FROM Sessions").fetchall()]
    histories = [dict(row) for row in sqlite_conn.execute("SELECT * FROM CorrectionHistories").fetchall()]
    proposals = [dict(row) for row in sqlite_conn.execute("SELECT * FROM AIProposals").fetchall()]
    
    return {
        "sessions": sessions,
        "histories": histories,
        "proposals": proposals,
    }


async def migrate(dry_run: bool = True):
    """Run the migration."""
    load_dotenv(CONF_ENV)
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in conf/.env")
        return
    
    if not DB_PATH.exists():
        print(f"ERROR: SQLite database not found at {DB_PATH}")
        return
    
    print(f"Mode: {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"SQLite: {DB_PATH}")
    print(f"Target: Supabase (from conf/.env DATABASE_URL)")
    print("=" * 60)
    
    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_data = get_sqlite_data(sqlite_conn)
    
    print(f"\nSQLite counts:")
    print(f"  Sessions: {len(sqlite_data['sessions'])}")
    print(f"  CorrectionHistories: {len(sqlite_data['histories'])}")
    print(f"  AIProposals: {len(sqlite_data['proposals'])}")
    
    pg_conn = await asyncpg.connect(db_url, statement_cache_size=0)
    
    try:
        supabase_ids = await get_supabase_ids(pg_conn)
        
        print(f"\nSupabase counts:")
        print(f"  sessions: {len(supabase_ids['sessions'])}")
        print(f"  correction_histories: {len(supabase_ids['histories'])}")
        print(f"  ai_proposals: {len(supabase_ids['proposals'])}")
        
        missing_sessions = []
        for s in sqlite_data["sessions"]:
            sid = s.get("sessionId")
            if sid and is_valid_uuid(sid) and sid not in supabase_ids["sessions"]:
                missing_sessions.append(s)
        
        valid_session_ids = supabase_ids["sessions"] | {s["sessionId"] for s in missing_sessions}
        
        missing_histories = []
        skipped_histories = []
        for h in sqlite_data["histories"]:
            hid = h.get("historyId")
            sid = h.get("sessionId")
            
            if not is_valid_uuid(hid):
                skipped_histories.append((hid, "invalid history_id"))
                continue
            if hid in supabase_ids["histories"]:
                continue
            if not is_valid_uuid(sid) or sid not in valid_session_ids:
                skipped_histories.append((hid, f"invalid/missing session_id: {sid}"))
                continue
            
            missing_histories.append(h)
        
        valid_history_ids = supabase_ids["histories"] | {h["historyId"] for h in missing_histories}
        
        missing_proposals = []
        skipped_proposals = []
        for p in sqlite_data["proposals"]:
            pid = p.get("proposalId")
            hid = p.get("historyId")
            
            if not is_valid_uuid(pid):
                skipped_proposals.append((pid, "invalid proposal_id"))
                continue
            if pid in supabase_ids["proposals"]:
                continue
            if not is_valid_uuid(hid) or hid not in valid_history_ids:
                skipped_proposals.append((pid, f"invalid/missing history_id: {hid}"))
                continue
            
            missing_proposals.append(p)
        
        print(f"\n--- Analysis ---")
        print(f"Missing sessions: {len(missing_sessions)}")
        print(f"Missing histories: {len(missing_histories)} (skipped: {len(skipped_histories)})")
        print(f"Missing proposals: {len(missing_proposals)} (skipped: {len(skipped_proposals)})")
        
        if skipped_histories:
            print(f"\nSkipped histories (invalid references):")
            for hid, reason in skipped_histories[:5]:
                print(f"  - {hid}: {reason}")
            if len(skipped_histories) > 5:
                print(f"  ... and {len(skipped_histories) - 5} more")
        
        if skipped_proposals:
            print(f"\nSkipped proposals (invalid references):")
            for pid, reason in skipped_proposals[:5]:
                print(f"  - {pid}: {reason}")
            if len(skipped_proposals) > 5:
                print(f"  ... and {len(skipped_proposals) - 5} more")
        
        total_missing = len(missing_sessions) + len(missing_histories) + len(missing_proposals)
        
        if total_missing == 0:
            print("\n✓ No data to migrate. Supabase is up to date!")
            return
        
        if dry_run:
            print(f"\n[DRY-RUN] Would migrate {total_missing} records.")
            if missing_sessions:
                print(f"\nMissing sessions:")
                for s in missing_sessions:
                    print(f"  - {s['sessionId']}: {s.get('name', 'unnamed')}")
            return
        
        print(f"\n--- Migrating {total_missing} records ---")
        
        if missing_sessions:
            for s in missing_sessions:
                await pg_conn.execute(
                    """
                    INSERT INTO sessions (session_id, created_at, updated_at, name, correction_count, is_open)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    uuid.UUID(s["sessionId"]),
                    parse_timestamp(s.get("createdAt")),
                    parse_timestamp(s.get("updatedAt")),
                    s.get("name"),
                    s.get("correctionCount", 0),
                    bool(s.get("isOpen", 1)),
                )
            print(f"✓ Migrated {len(missing_sessions)} sessions")
        
        if missing_histories:
            for h in missing_histories:
                await pg_conn.execute(
                    """
                    INSERT INTO correction_histories 
                    (history_id, session_id, timestamp, original_text, instruction_prompt, 
                     target_text, combined_comment, selected_proposal_ids, custom_proposals)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (history_id) DO NOTHING
                    """,
                    uuid.UUID(h["historyId"]),
                    uuid.UUID(h["sessionId"]),
                    parse_timestamp(h.get("timestamp")),
                    h.get("originalText") or h.get("original_text"),
                    h.get("instructionPrompt") or h.get("instruction_prompt"),
                    h.get("targetText") or h.get("target_text"),
                    h.get("combinedComment") or h.get("combined_comment"),
                    h.get("selectedProposalIds"),
                    h.get("customProposals"),
                )
            print(f"✓ Migrated {len(missing_histories)} histories")
        
        if missing_proposals:
            for p in missing_proposals:
                confidence_score = None
                if p.get("isSelected") and p.get("selectedOrder") is not None:
                    confidence_score = 1.0 - (p.get("selectedOrder") or 0) * 0.1
                
                await pg_conn.execute(
                    """
                    INSERT INTO ai_proposals 
                    (proposal_id, history_id, proposal_text, confidence_score, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (proposal_id) DO NOTHING
                    """,
                    uuid.UUID(p["proposalId"]),
                    uuid.UUID(p["historyId"]),
                    p.get("originalAfterText") or p.get("proposal_text") or "",
                    confidence_score,
                )
            print(f"✓ Migrated {len(missing_proposals)} proposals")
        
        final_ids = await get_supabase_ids(pg_conn)
        print(f"\n--- Final Supabase counts ---")
        print(f"  sessions: {len(final_ids['sessions'])}")
        print(f"  correction_histories: {len(final_ids['histories'])}")
        print(f"  ai_proposals: {len(final_ids['proposals'])}")
        print(f"\n✓ Migration complete!")
        
    finally:
        sqlite_conn.close()
        await pg_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Show what would be migrated")
    group.add_argument("--apply", action="store_true", help="Actually migrate data")
    
    args = parser.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
