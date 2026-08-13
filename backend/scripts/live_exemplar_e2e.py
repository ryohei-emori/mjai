#!/usr/bin/env python3
"""End-to-end live check of the optional exemplar through generate_suggestions().

Runs the real failover chain twice on the epic fixture — once without an
exemplar, once with one — and asserts the guard held: the exemplar must never
be named inside `reason` / `overallComment`.

Usage (from repo root, keys loaded from conf/.env):
  set -a && . conf/.env && set +a
  cd backend && PYTHONPATH=. python scripts/live_exemplar_e2e.py

Never prints API keys or key-derived material.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.llm.suggestions import generate_suggestions  # noqa: E402
from tests.fixtures.epic_shi_source_target import (  # noqa: E402
    EPIC_SOURCE_TEXT,
    EPIC_TARGET_TEXT,
)

EXEMPLAR = """現代人が叙事詩を読む経験とは、おそらくそれを紙に印刷された文字として読むことだろう。しかし実際には、叙事詩はまず声であり、語られ、歌われる口承文学である。
その光景は、今日の講釈を聴く体験に少し似ていたはずだ。芸人の多くは文字が読めなかったが、長大な詩篇を吟誦できたのは、機械的な暗記によるものではない。決まり文句、固定的な称号、型にはまった場面を用いて語りを組み立て、自らの負担を軽くしていたのである。
これが叙事詩の生まれた環境である。叙事詩は特定の個人の創作ではなく、民間の吟誦者集団が長年にわたって共同で作り、幾重にも積み重ねてきた成果なのだ。"""

BANNED_MENTIONS = ("参考译文", "模範回答", "参考訳", "正解例", "标准译文", "範例")


async def main() -> int:
    failures: list[str] = []

    for label, exemplar in (("no-exemplar", None), ("with-exemplar", EXEMPLAR)):
        result = await generate_suggestions(
            EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT, exemplar
        )
        suggestions = result["suggestions"]
        prose = "\n".join(
            [s["reason"] for s in suggestions] + [result["overallComment"]]
        )
        hits = [b for b in BANNED_MENTIONS if b in prose]
        print(
            f"{label}: n_suggestions={len(suggestions)} "
            f"banned_mentions={hits} overall_len={len(result['overallComment'])}"
        )
        for i, s in enumerate(suggestions, 1):
            print(f"  [{i}] «{s['original'][:40]}» :: {s['reason'][:120]}")

        if hits:
            failures.append(f"{label}: critique named the exemplar: {hits}")
        if not suggestions:
            failures.append(f"{label}: returned zero suggestions")

        await asyncio.sleep(4)

    if failures:
        print("FAILURES:\n" + "\n".join(failures))
        return 1
    print("OK: both paths returned suggestions and neither named the exemplar")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
