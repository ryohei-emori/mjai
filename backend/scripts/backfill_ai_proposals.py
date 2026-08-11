"""
app.db (legacy SQLite) の完全データで Supabase ai_proposals の NULLカラムを backfill するスクリプト。

背景: 過去の一回限りの移行スクリプトが SQLite の AIProposals データを
`proposal_text`（レガシーカラム）にのみコピーし、アプリが実際に参照する
新カラム（type, original_after_text, original_reason, modified_after_text,
modified_reason, is_selected, is_modified, is_custom, selected_order）には
コピーしていなかったため、本番テーブルにNULL行が多数残っている。
本スクリプトは proposal_id (UUID) で1:1にマッチさせ、それらのNULLカラムを
SQLite側の値で復元する。

安全策:
- --dry-run 時は件数集計とサンプル抽出のみ行い、一切書き込まない。
- 実更新は `WHERE proposal_id = $1 AND original_after_text IS NULL` 条件で
  ガードし、すでに値が入っている行を誤って上書きしない。
- 実行前に必ず ai_proposals テーブルの完全バックアップを取得すること。
"""
import argparse
import asyncio
import os
import sqlite3
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / "conf" / ".env")

SQLITE_PATH = Path(__file__).resolve().parent.parent / "db" / "app.db"


async def main(dry_run: bool):
    sconn = sqlite3.connect(SQLITE_PATH)
    sconn.row_factory = sqlite3.Row
    sqlite_rows = {
        r["proposalId"]: r
        for r in sconn.execute(
            "SELECT proposalId, type, originalAfterText, originalReason, "
            "modifiedAfterText, modifiedReason, isSelected, isModified, "
            "isCustom, selectedOrder FROM AIProposals"
        ).fetchall()
    }
    sconn.close()

    pg = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    try:
        null_rows = await pg.fetch(
            "SELECT proposal_id FROM ai_proposals WHERE original_after_text IS NULL"
        )
        to_update = [r["proposal_id"] for r in null_rows if str(r["proposal_id"]) in sqlite_rows]
        print(f"NULL行: {len(null_rows)}件 / SQLiteに対応データあり: {len(to_update)}件")
        unmatched = [r["proposal_id"] for r in null_rows if str(r["proposal_id"]) not in sqlite_rows]
        if unmatched:
            print(f"警告: SQLiteに対応データが無いNULL行: {len(unmatched)}件 — {unmatched[:10]}")

        if dry_run:
            print("\n--- サンプル (更新対象になる予定の最初の5件) ---")
            for pid in to_update[:5]:
                s = sqlite_rows[str(pid)]
                print(f"\nproposal_id: {pid}")
                print(f"  type              : {s['type']!r}")
                print(f"  originalAfterText : {str(s['originalAfterText'])[:80]!r}")
                print(f"  originalReason    : {str(s['originalReason'])[:80]!r}")
                print(f"  modifiedAfterText : {str(s['modifiedAfterText'])[:80]!r}")
                print(f"  modifiedReason    : {str(s['modifiedReason'])[:80]!r}")
                print(f"  isSelected        : {bool(s['isSelected'])}")
                print(f"  isModified        : {bool(s['isModified'])}")
                print(f"  isCustom          : {bool(s['isCustom'])}")
                print(f"  selectedOrder     : {s['selectedOrder']}")
            print("\n[dry-run] 書き込みは行われていません。")
            return

        async with pg.transaction():
            for pid in to_update:
                s = sqlite_rows[str(pid)]
                await pg.execute(
                    """
                    UPDATE ai_proposals SET
                        type = $2, original_after_text = $3, original_reason = $4,
                        modified_after_text = $5, modified_reason = $6,
                        is_selected = $7, is_modified = $8, is_custom = $9,
                        selected_order = $10
                    WHERE proposal_id = $1 AND original_after_text IS NULL
                    """,
                    pid, s["type"], s["originalAfterText"], s["originalReason"],
                    s["modifiedAfterText"], s["modifiedReason"],
                    bool(s["isSelected"]), bool(s["isModified"]), bool(s["isCustom"]),
                    s["selectedOrder"],
                )
        print(f"{len(to_update)}件を更新しました")
    finally:
        await pg.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    asyncio.run(main(parser.parse_args().dry_run))
