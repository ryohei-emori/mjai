"""HTTP provider for the private Codex CLI gateway running on the host Mac."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Optional

import httpx

from .provider_output import ProviderOutput

CODEXCLI_DEFAULT_MODEL = "codex-cli"
CODEXCLI_MODELS = (
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
)
CODEXCLI_TIMEOUT = 45.0
CODEXCLI_MIN_SLICE_S = 5.0
CODEXCLI_POLL_INTERVAL_S = 0.75

CODEXCLI_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "original": {"type": "string"},
                    "reason": {"type": "string"},
                    "sourceExcerpt": {"type": "string"},
                },
                "required": ["id", "original", "reason", "sourceExcerpt"],
                "additionalProperties": False,
            },
        },
        "overallComment": {"type": "string"},
    },
    "required": ["suggestions", "overallComment"],
    "additionalProperties": False,
}


class CodexCLIError(Exception):
    """The private Codex CLI gateway could not produce a response."""


def get_codexcli_url() -> str:
    return os.environ.get("CODEXCLI_API_URL", "").strip().rstrip("/")


def get_codexcli_model(requested: Optional[str] = None) -> str:
    return (
        (requested or "").strip()
        or os.environ.get("CODEXCLI_API_MODEL", "").strip()
        or CODEXCLI_MODELS[0]
    )


def get_codexcli_token() -> str:
    return os.environ.get("CODEXCLI_API_TOKEN", "").strip()


def is_codexcli_configured() -> bool:
    return bool(get_codexcli_url() and get_codexcli_token())


def _prompt_from_messages(messages: list[dict[str, str]]) -> str:
    sections: list[str] = []
    for message in messages:
        role = message.get("role", "user").upper()
        sections.append(f"[{role}]\n{message.get('content', '')}")
    return "\n\n".join(sections)


def _request_timeout(deadline_monotonic: Optional[float]) -> float:
    if deadline_monotonic is None:
        return CODEXCLI_TIMEOUT
    return min(CODEXCLI_TIMEOUT, deadline_monotonic - time.monotonic() - 1.5)


async def call_codexcli(
    messages: list[dict[str, str]],
    *,
    model: Optional[str] = None,
    deadline_monotonic: Optional[float] = None,
) -> ProviderOutput:
    """Submit a task to codexcli-api and poll for structured output."""
    base_url = get_codexcli_url()
    token = get_codexcli_token()
    if not base_url or not token:
        raise CodexCLIError("Codex CLI API is not configured")

    timeout = _request_timeout(deadline_monotonic)
    if timeout < CODEXCLI_MIN_SLICE_S:
        raise CodexCLIError("Codex CLI API skipped: insufficient request time left")

    payload = {
        "prompt": _prompt_from_messages(messages),
        "model": get_codexcli_model(model),
        "sandbox": "read-only",
        "output_schema": CODEXCLI_OUTPUT_SCHEMA,
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.post(f"{base_url}/v1/tasks", headers=headers, json=payload)
            response.raise_for_status()
            task_id = response.json().get("task_id")
            if not task_id:
                raise CodexCLIError("Codex CLI API returned no task_id")

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                status_response = await client.get(
                    f"{base_url}/v1/tasks/{task_id}", headers=headers
                )
                status_response.raise_for_status()
                status = status_response.json()
                state = status.get("state")
                if state == "completed":
                    output = status.get("output_json")
                    if not isinstance(output, dict):
                        raise CodexCLIError("Codex CLI API returned non-object output")
                    return ProviderOutput(
                        text=json.dumps(output, ensure_ascii=False),
                        model=get_codexcli_model(model),
                    )
                if state in {"failed", "cancelled"}:
                    detail = status.get("error") or status.get("stderr") or state
                    raise CodexCLIError(f"Codex CLI task {state}: {detail}")
                await asyncio.sleep(min(CODEXCLI_POLL_INTERVAL_S, max(0, deadline - time.monotonic())))
    except CodexCLIError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise CodexCLIError(f"Codex CLI API request failed: {exc}") from exc

    raise CodexCLIError("Codex CLI API task timed out")
