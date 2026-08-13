#!/usr/bin/env python3
"""Live ×15 Chinese-enforcement smoke on epic SOURCE/TARGET fixture.

Usage (from host, with Docker backend up and keys in container env):
  docker exec mjai-backend-1 python /app/scripts/live_chinese_15x.py

Or locally (deps + GROQ_API_KEY loaded):
  set -a && . conf/.env && set +a
  cd backend && PYTHONPATH=. python scripts/live_chinese_15x.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Allow `import app` / `import tests` when run as a script.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.llm import groq_provider as gp  # noqa: E402
from app.llm import suggestions as sug_mod  # noqa: E402
from app.llm.parser import (  # noqa: E402
    _text_looks_japanese,
    has_non_chinese_reason,
    is_json_extraction_failure,
)
from tests.fixtures.epic_shi_source_target import (  # noqa: E402
    EPIC_SOURCE_TEXT,
    EPIC_TARGET_TEXT,
)

ITERATIONS = int(os.environ.get("LIVE_CHINESE_ITERS", "15"))
# Space out calls to reduce Groq free-tier 429s across sequential runs.
INTER_CALL_SLEEP_S = float(os.environ.get("LIVE_CHINESE_SLEEP_S", "2"))
last_model = {"provider": None, "model": None}

_orig_call_groq = gp.call_groq
_orig_call_cf = sug_mod.call_cloudflare


async def _call_groq_capture(messages, model=None, **kwargs):
    last_model["provider"] = "groq"
    last_model["model"] = model or os.environ.get("GROQ_MODEL") or "?"
    return await _orig_call_groq(messages, model=model, **kwargs)


async def _call_cf_capture(messages, *a, **kw):
    last_model["provider"] = "cloudflare"
    last_model["model"] = "cloudflare-workers-ai"
    return await _orig_call_cf(messages, *a, **kw)


def failing_fields(result) -> list[str]:
    fails: list[str] = []
    if _text_looks_japanese(result.get("overallComment") or ""):
        fails.append(f"overallComment: {(result.get('overallComment') or '')[:80]!r}")
    for i, s in enumerate(result.get("suggestions") or []):
        r = s.get("reason") or ""
        if _text_looks_japanese(r):
            fails.append(f"reason[{i}]: {r[:80]!r}")
    return fails


async def main() -> int:
    # Patch the underlying call sites (not the wrappers themselves) so
    # generate_suggestions' Groq→Cloudflare failover stays intact.
    gp.call_groq = _call_groq_capture
    sug_mod.call_cloudflare = _call_cf_capture

    print(f"GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY'))}")
    print(f"GROQ_MODEL pin: {os.environ.get('GROQ_MODEL') or '(rotation)'}")
    rows = []
    for i in range(1, ITERATIONS + 1):
        last_model["provider"] = None
        last_model["model"] = None
        t0 = time.time()
        try:
            result = await sug_mod.generate_suggestions(
                EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT
            )
            elapsed = time.time() - t0
            parse_fail = is_json_extraction_failure(result)
            non_cn = has_non_chinese_reason(result)
            fails = failing_fields(result)
            ok = (not parse_fail) and (not non_cn)
            row = {
                "n": i,
                "success": True,
                "chinese_ok": ok,
                "parse_fail": parse_fail,
                "non_chinese": non_cn,
                "provider": last_model["provider"],
                "model": last_model["model"],
                "n_suggestions": len(result.get("suggestions") or []),
                "elapsed_s": round(elapsed, 2),
                "fail_samples": fails[:3],
                "overall_sample": (result.get("overallComment") or "")[:60],
            }
        except Exception as e:
            elapsed = time.time() - t0
            row = {
                "n": i,
                "success": False,
                "chinese_ok": False,
                "error": f"{type(e).__name__}: {e}",
                "provider": last_model["provider"],
                "model": last_model["model"],
                "elapsed_s": round(elapsed, 2),
                "fail_samples": [],
            }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if i < ITERATIONS:
            await asyncio.sleep(INTER_CALL_SLEEP_S)

    chinese_ok = sum(1 for r in rows if r.get("chinese_ok"))
    success = sum(1 for r in rows if r.get("success"))
    summary = {
        "success": f"{success}/{ITERATIONS}",
        "chinese_ok": f"{chinese_ok}/{ITERATIONS}",
    }
    print("---SUMMARY---")
    print(json.dumps(summary, ensure_ascii=False))
    out = Path("/tmp/live_chinese_15x_results.json")
    out.write_text(
        json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0 if chinese_ok == ITERATIONS and success == ITERATIONS else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
