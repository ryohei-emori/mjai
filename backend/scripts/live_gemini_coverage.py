#!/usr/bin/env python3
"""Live Gemini coverage/token-budget probe on the epic multi-paragraph fixture.

Answers, with evidence rather than inference:
- how many suggestions Gemini actually returns for a 5-paragraph TARGET,
- whether generation stopped at STOP or MAX_TOKENS,
- how many output tokens were actually consumed (usageMetadata),
- how long the call took relative to GEMINI_TIMEOUT,
- the model's advertised inputTokenLimit / outputTokenLimit.

Usage (from repo root, keys loaded from conf/.env):
  set -a && . conf/.env && set +a
  cd backend && PYTHONPATH=. python scripts/live_gemini_coverage.py

Env knobs:
  GEMINI_PROBE_ITERS          iterations per max-tokens setting (default 1)
  GEMINI_PROBE_MAX_TOKENS     comma-separated maxOutputTokens values to compare
                              (default: the provider's configured value)
  GEMINI_PROBE_MODELS         comma-separated model ids (default ALLOWED_GEMINI_MODELS)
  GEMINI_PROBE_SLEEP_S        sleep between calls (default 4)
  GEMINI_PROBE_ENV_FILE       optional .env path to load before probing (useful
                              inside the docker backend, whose env_file snapshot
                              may predate newly added keys)

Never prints API keys or key-derived material.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_ENV_FILE = (os.environ.get("GEMINI_PROBE_ENV_FILE") or "").strip()
if _ENV_FILE:
    from dotenv import load_dotenv

    load_dotenv(_ENV_FILE, override=True)

import httpx  # noqa: E402

from app.llm import gemini_provider as gem  # noqa: E402
from app.llm.parser import parse_model_output  # noqa: E402
from app.llm.prompts import build_messages  # noqa: E402
from tests.fixtures.epic_shi_source_target import (  # noqa: E402
    EPIC_SOURCE_TEXT,
    EPIC_TARGET_TEXT,
)

ITERS = int(os.environ.get("GEMINI_PROBE_ITERS", "1"))
SLEEP_S = float(os.environ.get("GEMINI_PROBE_SLEEP_S", "4"))


def _max_token_settings() -> list[int | None]:
    raw = (os.environ.get("GEMINI_PROBE_MAX_TOKENS") or "").strip()
    if not raw:
        return [None]  # use provider default
    return [int(v.strip()) for v in raw.split(",") if v.strip()]


def _models() -> list[str]:
    raw = (os.environ.get("GEMINI_PROBE_MODELS") or "").strip()
    if not raw:
        return list(gem.ALLOWED_GEMINI_MODELS)
    return [v.strip() for v in raw.split(",") if v.strip()]


async def fetch_model_limits(api_key: str, model: str) -> dict:
    url = f"{gem.GEMINI_API_BASE}/{model}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, headers={"x-goog-api-key": api_key})
    if r.status_code != 200:
        return {"model": model, "error": f"HTTP {r.status_code}"}
    d = r.json()
    return {
        "model": model,
        "inputTokenLimit": d.get("inputTokenLimit"),
        "outputTokenLimit": d.get("outputTokenLimit"),
    }


def _thinking_overrides() -> list[dict | None]:
    """Parse GEMINI_PROBE_THINKING, e.g. `level:low,budget:0,none`."""
    raw = (os.environ.get("GEMINI_PROBE_THINKING") or "").strip()
    if not raw:
        return [None]
    out: list[dict | None] = []
    for spec in raw.split(","):
        spec = spec.strip()
        if not spec or spec == "none":
            out.append(None)
        elif spec.startswith("level:"):
            out.append({"thinkingLevel": spec.split(":", 1)[1]})
        elif spec.startswith("budget:"):
            out.append({"thinkingBudget": int(spec.split(":", 1)[1])})
    return out or [None]


async def probe_once(
    api_key: str,
    model: str,
    max_tokens: int | None,
    thinking: dict | None = None,
) -> dict:
    messages = build_messages(EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT)
    payload = gem._messages_to_gemini_payload(messages)
    configured = payload["generationConfig"].get("maxOutputTokens")
    if max_tokens is not None:
        payload["generationConfig"]["maxOutputTokens"] = max_tokens
    if thinking is not None:
        payload["generationConfig"]["thinkingConfig"] = thinking
    effective = payload["generationConfig"].get("maxOutputTokens")

    url = f"{gem.GEMINI_API_BASE}/{model}:generateContent"
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=gem.GEMINI_TIMEOUT) as client:
            r = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                },
                json=payload,
            )
    except httpx.TimeoutException:
        return {
            "model": model,
            "maxOutputTokens": effective,
            "provider_configured_maxOutputTokens": configured,
            "thinkingConfig": thinking,
            "http_status": "TIMEOUT",
            "elapsed_s": round(time.time() - t0, 2),
            "gemini_timeout_s": gem.GEMINI_TIMEOUT,
        }
    elapsed = time.time() - t0

    row: dict = {
        "model": model,
        "maxOutputTokens": effective,
        "provider_configured_maxOutputTokens": configured,
        "thinkingConfig": thinking,
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
            "thoughtsTokenCount": usage.get("thoughtsTokenCount"),
            "totalTokenCount": usage.get("totalTokenCount"),
            "raw_len_chars": len(text),
            "n_suggestions": len(parsed["suggestions"]),
            "reason_len_chars": [len(s["reason"]) for s in parsed["suggestions"]],
            "overall_len_chars": len(parsed["overallComment"]),
            "trailing_json_ok": text.rstrip().endswith("}"),
        }
    )
    return row


async def main() -> int:
    api_key = gem.get_gemini_api_key()
    if not api_key:
        print("GEMINI_API_KEY(S) not configured; skipping probe", file=sys.stderr)
        return 2
    print("gemini pool configured: True (keys never printed)")
    print(f"GEMINI_TIMEOUT={gem.GEMINI_TIMEOUT}s")
    print(f"thinkingLevel={gem.get_thinking_level()}")

    models = _models()
    for m in models:
        print(json.dumps(await fetch_model_limits(api_key, m), ensure_ascii=False))

    rows = []
    for thinking in _thinking_overrides():
        for max_tokens in _max_token_settings():
            for model in models:
                for i in range(ITERS):
                    row = await probe_once(api_key, model, max_tokens, thinking)
                    row["n"] = i + 1
                    rows.append(row)
                    print(json.dumps(row, ensure_ascii=False), flush=True)
                    await asyncio.sleep(SLEEP_S)

    out = Path("/tmp/live_gemini_coverage.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
