#!/usr/bin/env python3
import os
import asyncio
import sqlite3
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env():
    project_root = resolve_project_root()
    # Prefer conf/.env if present
    conf_env = project_root / "conf/.env"
    local_env = project_root / "backend/.env"
    if conf_env.exists():
        load_dotenv(dotenv_path=str(conf_env), override=False)
    elif local_env.exists():
        load_dotenv(dotenv_path=str(local_env), override=False)


SCHEMA_SQL = """
create extension if not exists pgcrypto;
create table if not exists sessions (
  session_id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  name text,
  correction_count integer not null default 0,
  is_open boolean not null default true
);
create table if not exists correction_histories (
  history_id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(session_id) on delete cascade,
  timestamp timestamptz not null default now(),
  original_text text not null,
  instruction_prompt text,
  target_text text not null,
  combined_comment text,
  selected_proposal_ids text,
  custom_proposals text
);
create table if not exists ai_proposals (
  proposal_id uuid primary key default gen_random_uuid(),
  history_id uuid not null references correction_histories(history_id) on delete cascade,
  type text not null,
  original_after_text text not null,
  original_reason text,
  modified_after_text text,
  modified_reason text,
  is_selected boolean not null default false,
  is_modified boolean not null default false,
  is_custom boolean not null default false,
  selected_order integer,
  created_at timestamptz not null default now()
);
create index if not exists idx_histories_session_id on correction_histories(session_id);
create index if not exists idx_histories_timestamp on correction_histories(timestamp desc);
create index if not exists idx_proposals_history_id on ai_proposals(history_id);
"""


async def ensure_schema(conn: asyncpg.Connection) -> None:
    for stmt in SCHEMA_SQL.split(";"):
        s = stmt.strip()
        if not s:
            continue
        await conn.execute(s + ";")


def open_sqlite() -> sqlite3.Connection:
    db_path = resolve_project_root() / "backend/db/app.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


async def migrate(dsn: str, create_schema: bool = True) -> None:
    if "sslmode=" not in dsn:
        dsn = dsn + ("&" if "?" in dsn else "?") + "sslmode=require"
    conn = await asyncpg.connect(dsn)
    try:
        if create_schema:
            await ensure_schema(conn)

        sq = open_sqlite()
        try:
            # Sessions
            for row in sq.execute("select * from Sessions"):
                await conn.execute(
                    """
                    insert into sessions(session_id, created_at, updated_at, name, correction_count, is_open)
                    values($1,$2,$3,$4,$5,$6)
                    on conflict (session_id) do nothing
                    """,
                    row["sessionId"], row["createdAt"], row["updatedAt"], row["name"], row["correctionCount"], bool(row["isOpen"]),
                )

            # CorrectionHistories
            for row in sq.execute("select * from CorrectionHistories"):
                await conn.execute(
                    """
                    insert into correction_histories(
                      history_id, session_id, timestamp, original_text, instruction_prompt,
                      target_text, combined_comment, selected_proposal_ids, custom_proposals
                    ) values($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    on conflict (history_id) do nothing
                    """,
                    row["historyId"], row["sessionId"], row["timestamp"], row["originalText"], row["instructionPrompt"],
                    row["targetText"], row["combinedComment"], row["selectedProposalIds"], row["customProposals"],
                )

            # AIProposals
            for row in sq.execute("select * from AIProposals"):
                await conn.execute(
                    """
                    insert into ai_proposals(
                      proposal_id, history_id, type, original_after_text, original_reason,
                      modified_after_text, modified_reason, is_selected, is_modified, is_custom, selected_order
                    ) values($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    on conflict (proposal_id) do nothing
                    """,
                    row["proposalId"], row["historyId"], row["type"], row["originalAfterText"], row["originalReason"],
                    row["modifiedAfterText"], row["modifiedReason"], bool(row["isSelected"]), bool(row["isModified"]), bool(row["isCustom"] or 0), row["selectedOrder"],
                )
        finally:
            sq.close()
    finally:
        await conn.close()


if __name__ == "__main__":
    load_env()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set. Put it in conf/.env")
    asyncio.run(migrate(dsn, create_schema=True))


