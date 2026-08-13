#!/usr/bin/env python3
"""Live A/B probe: does an optional exemplar translation improve critiques?

Compares three prompt conditions on the multi-paragraph epic fixture:

- ``baseline``  — today's SOURCE + TARGET prompt (no exemplar block).
- ``guarded``   — exemplar block plus system rules that forbid citing the
                  exemplar as a reason and forbid treating "differs from the
                  exemplar" as a defect.
- ``naive``     — exemplar block with no anti-copy guard, to measure how far
                  the model degenerates into "the exemplar says X" critiques.

Reported per run: suggestion count, exemplar-mention hits, verbatim-copy
overlap between reasons and the exemplar, token usage, latency, finishReason.

Usage (from repo root, keys loaded from conf/.env):
  set -a && . conf/.env && set +a
  cd backend && PYTHONPATH=. python scripts/live_exemplar_compare.py

Env knobs:
  EXEMPLAR_PROBE_MODELS      comma-separated model ids (default: both allowed)
  EXEMPLAR_PROBE_CONDITIONS  comma-separated subset of baseline,guarded,naive
  EXEMPLAR_PROBE_SLEEP_S     sleep between calls (default 4)

Never prints API keys or key-derived material.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from app.llm import gemini_provider as gem  # noqa: E402
from app.llm.parser import parse_model_output  # noqa: E402
from app.llm import prompts as P  # noqa: E402
from tests.fixtures.epic_shi_source_target import (  # noqa: E402
    EPIC_SOURCE_TEXT,
    EPIC_TARGET_TEXT,
)

SLEEP_S = float(os.environ.get("EXEMPLAR_PROBE_SLEEP_S", "4"))

# A deliberately high-quality Japanese translation of EPIC_SOURCE_TEXT, playing
# the role of the 模範回答訳文 a user would paste. Written for this probe only.
EXEMPLAR_TRANSLATION = """現代人が叙事詩を読む経験とは、おそらくそれを紙に印刷された文字として読むことだろう。しかし実際には、叙事詩はまず声であり、語られ、歌われる口承文学である。広場に人々が輪になって座り、一人の吟誦者が叙事詩を歌うのを聴く——彼は長く伸びる節をつけ、その場の聴衆の反応に応じて内容を変えながら、聴き手の心を動かしていく。そんな光景を想像してみてほしい。

その光景は、今日の講釈を聴く体験に少し似ていたはずだ。芸人の多くは文字が読めなかったが、長大な詩篇を吟誦できたのは、機械的な暗記によるものではない。決まり文句、固定的な称号、型にはまった場面、そして誰もが知っている定型的なイメージを用いて語りを組み立て、自らの負担を軽くしていたのである。彼らの語りが、上演の場にいる全員にはっきり聞き取れたとは限らない。上演は長時間にわたり、聴衆の注意も途切れる。叙事詩の決まり文句は成語のようなもので、聴衆はひと言聞けば大筋を察し、筋を取り落とすことがない。

これが叙事詩の生まれた環境である。叙事詩は特定の個人の創作ではなく、民間の吟誦者集団が長年にわたって共同で作り、幾重にも積み重ねてきた成果なのだ。今日われわれの前にある姿は、ある一人あるいは一群の採録者が整理した一つの版に過ぎない。そして、一つの集団が年ごとに異なる聴衆の前で上演し続けたからこそ、叙事詩は神話、民謡、諺、宗教儀礼、さらには土地の知識までも取り込んでいった。ほとんどすべての叙事詩が、一つの民族あるいは共同体の共有された記憶を内に含んでいるのである。"""

# Candidate system-prompt appendix under evaluation (guarded condition).
GUARD_SYSTEM_NOTE = """
【六】模範回答訳文（可选参考，用户可能不提供）：
- 「模範回答訳文」是同一原文的一份高质量参考译文，只用来校准“原文意图 → 理想日语表达”的范围（语域、专名译词、情态强度）。它不是评分标准，也不是要把添削対象改写成它。
- MUST 仍以原文为判断依据评价添削対象。禁止把“与参考译文不同”本身当成问题；添削対象另有同样准确、同样自然的写法时，不得指为错误。
- 禁止在 reason / overallComment 里提及或引用参考译文的存在（禁止出现“参考译文”“模範回答”“参考訳”等字样）。推荐改法必须像没有参考译文时一样，用语言学理由说明为什么必须改。
- 参考译文的措辞可以启发推荐形，但“参考译文这么写”永远不是合格的理由。
"""

NAIVE_USER_BLOCK_LABEL = "模範回答訳文："
GUARDED_USER_BLOCK_LABEL = "模範回答訳文（参考・校准用，禁止直接当作理由或原样照搬）："

EXEMPLAR_MENTION_PATTERNS = [
    "参考译文",
    "参考訳",
    "参考譯",
    "模範回答",
    "模范回答",
    "模範訳",
    "模范译",
    "範例",
    "范例",
    "示范译",
    "標準訳",
    "标准译文",
    "正解例",
]


def build_messages_for(condition: str) -> list[dict]:
    """Assemble messages for a probe condition without touching prompts.py."""
    system = P.SYSTEM_PROMPT
    user = P.build_user_prompt(EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT)

    if condition == "guarded":
        system = system + "\n" + GUARD_SYSTEM_NOTE
        label = GUARDED_USER_BLOCK_LABEL
    elif condition == "naive":
        label = NAIVE_USER_BLOCK_LABEL
    elif condition == "baseline":
        label = None
    else:
        raise ValueError(f"unknown condition: {condition}")

    if label is not None:
        block = f"{label}{EXEMPLAR_TRANSLATION}\n\n添削対象："
        user = user.replace("添削対象：", block, 1)

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": P.FEW_SHOT_EXAMPLE},
        {"role": "user", "content": user},
    ]


def _longest_common_substring_len(a: str, b: str) -> int:
    """Length of the longest shared contiguous run (small inputs only)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def _quoted_jp_spans(text: str) -> list[str]:
    return re.findall(r"「([^」]{2,40})」", text)


def analyze(parsed: dict) -> dict:
    reasons = [s["reason"] for s in parsed["suggestions"]]
    overall = parsed["overallComment"]
    all_prose = "\n".join(reasons + [overall])

    mentions = [p for p in EXEMPLAR_MENTION_PATTERNS if p in all_prose]

    # Per-reason longest verbatim run shared with the exemplar. High values on
    # long runs indicate the model is transplanting exemplar sentences rather
    # than reasoning about the learner's text.
    lcs = [_longest_common_substring_len(r, EXEMPLAR_TRANSLATION) for r in reasons]

    quoted = _quoted_jp_spans(all_prose)
    quoted_from_exemplar_only = [
        q
        for q in quoted
        if q in EXEMPLAR_TRANSLATION and q not in EPIC_TARGET_TEXT
    ]

    return {
        "n_suggestions": len(parsed["suggestions"]),
        "exemplar_mentions": mentions,
        "reason_len_chars": [len(r) for r in reasons],
        "overall_len_chars": len(overall),
        "reason_max_lcs_with_exemplar": lcs,
        "reason_lcs_ge_15": sum(1 for v in lcs if v >= 15),
        "n_quoted_jp_spans": len(quoted),
        "n_quoted_spans_exemplar_only": len(quoted_from_exemplar_only),
        "quoted_spans_exemplar_only": quoted_from_exemplar_only[:8],
        "originals": [s["original"] for s in parsed["suggestions"]],
        "reasons": reasons,
        "overallComment": overall,
    }


async def probe_once(api_key: str, model: str, condition: str) -> dict:
    messages = build_messages_for(condition)
    payload = gem._messages_to_gemini_payload(messages)
    url = f"{gem.GEMINI_API_BASE}/{model}:generateContent"

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=gem.GEMINI_TIMEOUT) as client:
            r = await client.post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                json=payload,
            )
    except httpx.TimeoutException:
        return {
            "model": model,
            "condition": condition,
            "http_status": "TIMEOUT",
            "elapsed_s": round(time.time() - t0, 2),
        }
    elapsed = time.time() - t0

    row: dict = {
        "model": model,
        "condition": condition,
        "http_status": r.status_code,
        "elapsed_s": round(elapsed, 2),
        "gemini_timeout_s": gem.GEMINI_TIMEOUT,
    }
    if r.status_code != 200:
        row["error_snippet"] = (r.text or "")[:200]
        return row

    data = r.json()
    cand = (data.get("candidates") or [{}])[0] or {}
    usage = data.get("usageMetadata") or {}
    text = gem._extract_text_from_response(data)
    parsed = parse_model_output(text)

    row.update(
        {
            "finishReason": cand.get("finishReason"),
            "promptTokenCount": usage.get("promptTokenCount"),
            "candidatesTokenCount": usage.get("candidatesTokenCount"),
            "totalTokenCount": usage.get("totalTokenCount"),
            "trailing_json_ok": text.rstrip().endswith("}"),
        }
    )
    row.update(analyze(parsed))
    return row


def _models() -> list[str]:
    raw = (os.environ.get("EXEMPLAR_PROBE_MODELS") or "").strip()
    if not raw:
        return list(gem.ALLOWED_GEMINI_MODELS)
    return [v.strip() for v in raw.split(",") if v.strip()]


def _conditions() -> list[str]:
    raw = (os.environ.get("EXEMPLAR_PROBE_CONDITIONS") or "").strip()
    if not raw:
        return ["baseline", "guarded", "naive"]
    return [v.strip() for v in raw.split(",") if v.strip()]


async def main() -> int:
    api_key = gem.get_gemini_api_key()
    if not api_key:
        print("GEMINI_API_KEY(S) not configured; skipping probe", file=sys.stderr)
        return 2
    print("gemini pool configured: True (keys never printed)")

    rows = []
    for model in _models():
        for condition in _conditions():
            row = await probe_once(api_key, model, condition)
            rows.append(row)
            summary = {
                k: row.get(k)
                for k in (
                    "model",
                    "condition",
                    "http_status",
                    "elapsed_s",
                    "finishReason",
                    "promptTokenCount",
                    "candidatesTokenCount",
                    "n_suggestions",
                    "exemplar_mentions",
                    "reason_lcs_ge_15",
                    "n_quoted_spans_exemplar_only",
                )
            }
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            await asyncio.sleep(SLEEP_S)

    out = Path("/tmp/live_exemplar_compare.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
