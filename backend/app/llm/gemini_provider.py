"""
Gemini Generative Language API provider (generateContent / v1beta).
Primary cloud provider for suggestion generation (before Groq / Cloudflare).
"""

from __future__ import annotations

import logging
import os
import random
from typing import Any, Dict, List, Optional, Set

import httpx

from .key_pool import (
    acquire_gemini,
    cooldown_status_codes,
    credential_pool_index,
    format_credential_ref,
    is_gemini_configured,
    load_gemini_credentials,
    mark_cooldown,
)

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Curated free-tier Flash models confirmed via live generateContent probes
# (2026-08) against Google AI Studio keys. Prefer stable IDs over floating
# `gemini-flash-latest`. Excluded and why:
# - gemini-2.5-flash / gemini-2.5-pro: 404 on probed free-tier keys
# - gemini-3.5-flash: works but older than 3.6/3.7 — omit from default pool
# - gemini-flash-latest: floating alias; pin-able via GEMINI_MODEL only
# - Pro / preview paid-only models: out of free-tier default scope
ALLOWED_GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

DEFAULT_GEMINI_MODEL = ALLOWED_GEMINI_MODELS[0]
GEMINI_TIMEOUT = 45.0  # seconds; tertiary path — allow more headroom than Groq


class GeminiError(Exception):
    """Error from Gemini API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GeminiRateLimitError(GeminiError):
    """Gemini API rate limit / auth cooldown error (401/403/429)."""

    pass


class GeminiServerError(GeminiError):
    """Gemini API server error (5xx)."""

    pass


class GeminiTimeoutError(GeminiError):
    """Gemini API timeout error."""

    pass


def get_gemini_api_key() -> Optional[str]:
    """Return a configured Gemini key if the pool is non-empty (back-compat).

    Prefer `call_gemini` / the key pool for outbound calls — this helper is
    used for "is configured?" checks and does not advance round-robin.
    """
    creds = load_gemini_credentials()
    return creds[0].api_key if creds else None


def get_gemini_model() -> str:
    """Get Gemini model id, overridable via GEMINI_MODEL env var."""
    return (os.environ.get("GEMINI_MODEL") or "").strip() or DEFAULT_GEMINI_MODEL


def is_rotation_enabled() -> bool:
    """Rotation is disabled when GEMINI_MODEL pins a non-empty model id."""
    return not (os.environ.get("GEMINI_MODEL") or "").strip()


def select_gemini_models(n: int = 2) -> List[str]:
    """Select up to n distinct Gemini models for a single logical request."""
    if not is_rotation_enabled():
        return [get_gemini_model()]
    n = min(n, len(ALLOWED_GEMINI_MODELS))
    return random.sample(ALLOWED_GEMINI_MODELS, n)


def _messages_to_gemini_payload(
    messages: list[dict[str, str]],
) -> Dict[str, Any]:
    """Map OpenAI-style chat messages to Gemini generateContent body parts."""
    system_chunks: List[str] = []
    contents: List[Dict[str, Any]] = []

    for msg in messages:
        role = (msg.get("role") or "user").strip().lower()
        text = msg.get("content") or ""
        if role == "system":
            if text:
                system_chunks.append(text)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            {
                "role": gemini_role,
                "parts": [{"text": text}],
            }
        )

    if not contents:
        contents = [{"role": "user", "parts": [{"text": ""}]}]

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    if system_chunks:
        payload["system_instruction"] = {
            "parts": [{"text": "\n\n".join(system_chunks)}]
        }
    return payload


def _extract_text_from_response(data: dict[str, Any]) -> str:
    """Pull concatenated text parts from a generateContent response."""
    candidates = data.get("candidates") or []
    if not candidates:
        # promptFeedback / blocked responses often omit candidates
        feedback = data.get("promptFeedback") or data.get("error")
        raise GeminiError(f"Unexpected Gemini response (no candidates): {feedback or data}")

    parts = (
        ((candidates[0] or {}).get("content") or {}).get("parts")
        or []
    )
    texts: List[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        # Skip thought-only parts if present; keep textual output.
        if part.get("thought") is True and not part.get("text"):
            continue
        text = part.get("text")
        if isinstance(text, str) and text:
            texts.append(text)
    return "".join(texts)


async def _call_gemini_once(
    api_key: str,
    messages: list[dict[str, str]],
    resolved_model: str,
) -> str:
    """Single Gemini HTTP attempt with a concrete API key."""
    url = f"{GEMINI_API_BASE}/{resolved_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = _messages_to_gemini_payload(messages)

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise GeminiTimeoutError(
            f"Gemini request timed out after {GEMINI_TIMEOUT}s"
        ) from e
    except httpx.RequestError as e:
        raise GeminiError(f"Gemini request failed: {e}") from e

    if response.status_code == 429:
        raise GeminiRateLimitError("Gemini rate limit exceeded", status_code=429)

    if response.status_code in (401, 403):
        raise GeminiRateLimitError(
            f"Gemini auth/forbidden: {response.status_code}",
            status_code=response.status_code,
        )

    if response.status_code >= 500:
        raise GeminiServerError(
            f"Gemini server error: {response.status_code}",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        # Avoid echoing response bodies that might include request echoes;
        # keep status + short snippet for ops.
        snippet = (response.text or "")[:200]
        raise GeminiError(
            f"Gemini API error: {response.status_code} - {snippet}",
            status_code=response.status_code,
        )

    data = response.json()
    try:
        return _extract_text_from_response(data)
    except GeminiError:
        raise
    except (KeyError, IndexError, TypeError) as e:
        raise GeminiError(f"Unexpected Gemini response format: {data}") from e


async def call_gemini(messages: list[dict[str, str]], model: Optional[str] = None) -> str:
    """
    Call Gemini generateContent with the given messages.

    Uses the API key pool: on 401/403/429, cools down the failing key and
    retries with another eligible key (bounded by pool size).
    """
    if not is_gemini_configured():
        raise GeminiError("GEMINI_API_KEY not configured")

    resolved_model = model or get_gemini_model()
    pool = load_gemini_credentials()
    pool_size = len(pool)
    attempted: Set[str] = set()
    last_error: Optional[GeminiError] = None
    cooldown_codes = cooldown_status_codes()

    while True:
        cred = acquire_gemini(
            exclude_ids=list(attempted),
            cooldown_scope=resolved_model,
        )
        if cred is None:
            if last_error is not None:
                raise GeminiRateLimitError(
                    f"All Gemini API keys are in cooldown or exhausted "
                    f"(pool_size={pool_size}, model={resolved_model}, "
                    f"cooled_or_tried={len(attempted)})",
                    status_code=getattr(last_error, "status_code", None) or 429,
                )
            raise GeminiRateLimitError(
                f"All Gemini API keys are in cooldown or exhausted "
                f"(pool_size={pool_size}, model={resolved_model})",
                status_code=429,
            )

        attempted.add(cred.id)
        idx = credential_pool_index(pool, cred.id)
        cred_ref = format_credential_ref("gemini", idx, cred.label)
        try:
            return await _call_gemini_once(cred.api_key, messages, resolved_model)
        except GeminiError as e:
            status = e.status_code
            if status in cooldown_codes:
                mark_cooldown(cred.id, scope=resolved_model)
                logger.warning(
                    "%s model=%s failed with HTTP %s; cooling down for this "
                    "model and trying next key",
                    cred_ref,
                    resolved_model,
                    status,
                )
                last_error = e
                continue
            raise


async def call_gemini_with_rotation(messages: list[dict[str, str]]) -> str:
    """
    Call Gemini with in-provider model rotation and bounded retry.

    When rotation is enabled (GEMINI_MODEL unset), attempts up to 2 distinct
    models from ALLOWED_GEMINI_MODELS. When GEMINI_MODEL pins a model,
    behaves like a single call_gemini() with no model retry.
    """
    models = select_gemini_models(n=2)
    first_model = models[0]

    try:
        return await call_gemini(messages, model=first_model)
    except (GeminiRateLimitError, GeminiServerError, GeminiTimeoutError):
        if len(models) < 2:
            raise
        second_model = models[1]
        return await call_gemini(messages, model=second_model)
