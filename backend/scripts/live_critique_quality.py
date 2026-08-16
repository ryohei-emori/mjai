#!/usr/bin/env python3
"""Live critique-quality probe on the reported primate-sleep passage.

Scores the four defects that were reported against the pre-change prompt, so
the prompt rewrite in `editable-prompt-model-log-and-critique-fix` can be
judged on measurements rather than on reading the prompt:

  chinese_forms   recommended forms handed back in Chinese (改为"理论上")
  source_items    items whose `original` is not a span of the TARGET text,
                  i.e. the critique corrected the Chinese SOURCE
  synonym_only    items that recommend a swap without naming a defect
                  (比較⇄対比, 研究者⇄学者) — heuristic, see below
  numeral_caught  whether 「９点５時間」 (a real fault) is reported at all

Conditions (each `--iters` times, Gemini only, one model per call):
  current   the prompt as it ships now
  baseline  the pre-change prompt, loaded from a copy of the old module:
              git show <pre-change-sha>:backend/app/llm/prompts.py > /tmp/old_prompts.py
              CRITIQUE_PROBE_BASELINE_PROMPTS_FILE=/tmp/old_prompts.py
            Importing the old module (rather than pasting its text as an
            override) keeps the baseline byte-identical to what shipped.
  custom    a stored custom prompt body from CRITIQUE_PROBE_PROMPT_FILE, which
            exercises the same `system_prompt_override` path the settings
            dialog writes to — used to confirm an edited prompt reaches the
            provider and the output contract still holds.

Usage (from repo root, keys loaded from conf/.env):
  set -a && . conf/.env && set +a
  cd backend && PYTHONPATH=. python scripts/live_critique_quality.py

Env knobs:
  CRITIQUE_PROBE_ITERS      iterations per condition (default 2)
  CRITIQUE_PROBE_MODELS     comma-separated model ids (default ALLOWED_GEMINI_MODELS[0])
  CRITIQUE_PROBE_SLEEP_S    sleep between calls (default 4)

Never prints API keys or key-derived material.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from app.llm import gemini_provider as gem  # noqa: E402
from app.llm.parser import (  # noqa: E402
    _form_is_non_japanese,
    _recommended_forms,
    parse_model_output,
)
from app.llm.prompts import build_messages  # noqa: E402
from tests.fixtures.primate_sleep_source_target import (  # noqa: E402
    PRIMATE_SLEEP_SOURCE_TEXT,
    PRIMATE_SLEEP_TARGET_TEXT,
)

ITERS = int(os.environ.get("CRITIQUE_PROBE_ITERS", "2"))
SLEEP_S = float(os.environ.get("CRITIQUE_PROBE_SLEEP_S", "4"))

# A wording item is legitimate when the reason names what actually goes wrong.
# Absence of every one of these, together with a recommended replacement, is the
# synonym-preference shape the rules forbid. Heuristic by nature: it can only
# say "no defect vocabulary appears", so read the flagged reasons before
# trusting the count.
_DEFECT_MARKERS = re.compile(
    r"意[义義]|误解|误读|丢|漏|脱落|偏移|语域|語域|口语|书面|搭配|不成立|不自然|"
    r"语法|語法|活用|助词|助詞|情态|情態|时态|時態|规范|規範|术语|術語|专名|"
    r"数字|单位|写法|逻辑|邏輯|理论|語感|语感"
)
_NUMERAL_FAULT = re.compile(r"９点５|9点5|9\.5|九点五|９．５")


def _target_spans(target: str) -> Callable[[str], bool]:
    """Membership test for 'is this excerpt a span of the TARGET text?'."""
    normalized = re.sub(r"\s+", "", target)

    def is_span(excerpt: str) -> bool:
        candidate = re.sub(r"\s+", "", excerpt or "")
        return bool(candidate) and candidate in normalized

    return is_span


def score(parsed: dict) -> dict:
    """Per-run defect counts for one parsed critique."""
    is_span = _target_spans(PRIMATE_SLEEP_TARGET_TEXT)
    chinese_forms: list[str] = []
    source_items: list[str] = []
    synonym_only: list[str] = []
    numeral_caught = False

    for item in parsed["suggestions"]:
        reason = item.get("reason") or ""
        original = item.get("original") or ""
        forms = _recommended_forms(reason)
        chinese_forms.extend(f for f in forms if _form_is_non_japanese(f))
        if not is_span(original):
            source_items.append(original)
        if forms and not _DEFECT_MARKERS.search(reason):
            synonym_only.append(reason[:80])
        if _NUMERAL_FAULT.search(original) or _NUMERAL_FAULT.search(reason):
            numeral_caught = True

    return {
        "n_suggestions": len(parsed["suggestions"]),
        "chinese_forms": len(chinese_forms),
        "chinese_form_samples": chinese_forms[:5],
        "source_items": len(source_items),
        "source_item_samples": source_items[:5],
        "synonym_only": len(synonym_only),
        "synonym_only_samples": synonym_only[:3],
        "numeral_caught": numeral_caught,
        "overall_len_chars": len(parsed["overallComment"]),
    }


def _load_baseline_build_messages() -> Callable | None:
    """`build_messages` from a saved copy of the pre-change prompts module."""
    path = (os.environ.get("CRITIQUE_PROBE_BASELINE_PROMPTS_FILE") or "").strip()
    if not path:
        return None
    spec = importlib.util.spec_from_file_location("baseline_prompts", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load baseline prompts from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_messages


def _custom_prompt_body() -> str | None:
    path = (os.environ.get("CRITIQUE_PROBE_PROMPT_FILE") or "").strip()
    if not path:
        return None
    return Path(path).read_text(encoding="utf-8")


def _conditions() -> list[tuple[str, list[dict]]]:
    conditions: list[tuple[str, list[dict]]] = []
    baseline_build = _load_baseline_build_messages()
    if baseline_build is not None:
        conditions.append(
            (
                "baseline",
                baseline_build(PRIMATE_SLEEP_SOURCE_TEXT, PRIMATE_SLEEP_TARGET_TEXT),
            )
        )
    conditions.append(
        ("current", build_messages(PRIMATE_SLEEP_SOURCE_TEXT, PRIMATE_SLEEP_TARGET_TEXT))
    )
    custom = _custom_prompt_body()
    if custom:
        conditions.append(
            (
                "custom",
                build_messages(
                    PRIMATE_SLEEP_SOURCE_TEXT,
                    PRIMATE_SLEEP_TARGET_TEXT,
                    system_prompt_override=custom,
                ),
            )
        )
    return conditions


def _models() -> list[str]:
    raw = (os.environ.get("CRITIQUE_PROBE_MODELS") or "").strip()
    if raw:
        return [v.strip() for v in raw.split(",") if v.strip()]
    return [gem.ALLOWED_GEMINI_MODELS[0]]


async def probe_once(api_key: str, model: str, messages: list[dict]) -> dict:
    payload = gem._messages_to_gemini_payload(messages)
    url = f"{gem.GEMINI_API_BASE}/{model}:generateContent"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=gem.GEMINI_TIMEOUT) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                json=payload,
            )
    except httpx.TimeoutException:
        return {
            "http_status": "TIMEOUT",
            "elapsed_s": round(time.time() - t0, 2),
            "gemini_timeout_s": gem.GEMINI_TIMEOUT,
        }
    elapsed = round(time.time() - t0, 2)
    row: dict = {
        "http_status": response.status_code,
        "elapsed_s": elapsed,
        "gemini_timeout_s": gem.GEMINI_TIMEOUT,
    }
    if response.status_code != 200:
        row["error_snippet"] = (response.text or "")[:200]
        return row

    data = response.json()
    candidate = (data.get("candidates") or [{}])[0] or {}
    usage = data.get("usageMetadata") or {}
    text = gem._extract_text_from_response(data)
    parsed = parse_model_output(text)
    row.update(
        {
            "finishReason": candidate.get("finishReason"),
            "promptTokenCount": usage.get("promptTokenCount"),
            "candidatesTokenCount": usage.get("candidatesTokenCount"),
            "thoughtsTokenCount": usage.get("thoughtsTokenCount"),
            # An override must not be able to drop the JSON contract.
            "parsed_ok": bool(parsed["suggestions"]) or bool(parsed["overallComment"]),
            **score(parsed),
        }
    )
    return row


async def main() -> int:
    api_key = gem.get_gemini_api_key()
    if not api_key:
        print("GEMINI_API_KEY(S) not configured; skipping probe", file=sys.stderr)
        return 2
    print("gemini pool configured: True (keys never printed)")
    print(f"GEMINI_TIMEOUT={gem.GEMINI_TIMEOUT}s thinkingLevel={gem.get_thinking_level()}")

    rows: list[dict] = []
    for name, messages in _conditions():
        prompt_chars = sum(len(m["content"]) for m in messages)
        print(f"--- condition={name} prompt_chars={prompt_chars}")
        for model in _models():
            for i in range(ITERS):
                row = await probe_once(api_key, model, messages)
                row.update({"condition": name, "model": model, "n": i + 1})
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
                await asyncio.sleep(SLEEP_S)

    out = Path("/tmp/live_critique_quality.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
