"""
Gemini Generative Language API provider (generateContent / v1beta).
Primary cloud provider for suggestion generation (before Groq / Cloudflare).
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Any, Dict, List, Optional, Set

import httpx

from .budget import describe_skip, resolve_call_timeout
from .provider_output import ProviderOutput
from .key_pool import (
    PoolAvailability,
    acquire_gemini,
    cooldown_status_codes,
    credential_pool_index,
    format_credential_ref,
    is_gemini_configured,
    load_gemini_credentials,
    mark_cooldown,
    pool_availability,
    release_soonest_cooldown,
)
from .provider_health import (
    clamp_cooldown_seconds,
    observe_refusal,
    parse_duration_hint,
    parse_retry_after,
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
# Keep under Vercel api/index.py maxDuration (60s) and suggestions wall-clock
# budget so a hung primary call cannot alone cause FUNCTION_INVOCATION_TIMEOUT.
GEMINI_TIMEOUT = 22.0  # seconds

# Shortest slice worth spending on Gemini. Live probes with thinkingLevel=low
# measured 7.2-13.8s for a homework-length critique, so a call given less than
# this is a timeout with extra steps — and the seconds it burns are seconds
# Groq (1-3s) or Cloudflare (2-5s) could still have used.
GEMINI_MIN_SLICE_S = 10.0

# Both pooled models advertise outputTokenLimit=65536, so this ceiling cannot
# be rejected as out-of-range. Live probes consume 1.2k-2.1k completion tokens
# for a dense multi-paragraph critique, so this is headroom, not a target.
GEMINI_MAX_OUTPUT_TOKENS = 16384

# Gemini 3.x Flash thinks by default, spending ~2.9k-3.8k thought tokens that
# push a homework-length call to ~21s against GEMINI_TIMEOUT (live probes timed
# out outright) *and* yield a thinner critique (~1.4 suggestions per TARGET
# paragraph vs ~2-4 with thinking reduced). `thinkingLevel` is used rather than
# `thinkingBudget` because gemini-3.6-flash rejects `thinkingBudget` with HTTP
# 400 while accepting `thinkingLevel`.
DEFAULT_GEMINI_THINKING_LEVEL = "low"
# GEMINI_THINKING_LEVEL=none omits thinkingConfig entirely (provider default
# thinking) instead of sending a literal "none" the API would reject.
THINKING_LEVEL_OPT_OUT = "none"


class GeminiError(Exception):
    """Error from Gemini API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        # Seconds Gemini itself asked us to wait, when it said so. Carried on the
        # error so the caller can size the cooldown without re-reading the
        # response it no longer has.
        self.retry_after = retry_after


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


def get_thinking_level() -> str:
    """Get the Gemini thinking level, overridable via GEMINI_THINKING_LEVEL."""
    return (
        os.environ.get("GEMINI_THINKING_LEVEL") or ""
    ).strip() or DEFAULT_GEMINI_THINKING_LEVEL


def is_rotation_enabled() -> bool:
    """Rotation is disabled when GEMINI_MODEL pins a non-empty model id."""
    return not (os.environ.get("GEMINI_MODEL") or "").strip()


def select_gemini_models(n: int = 2) -> List[str]:
    """Select up to n distinct Gemini models for a single logical request."""
    if not is_rotation_enabled():
        return [get_gemini_model()]
    n = min(n, len(ALLOWED_GEMINI_MODELS))
    return random.sample(ALLOWED_GEMINI_MODELS, n)


def _rotation_scopes() -> List[Optional[str]]:
    """Models a request could pick, which is what cooldowns are scoped to."""
    if not is_rotation_enabled():
        return [get_gemini_model()]
    return list(ALLOWED_GEMINI_MODELS)


def gemini_availability() -> PoolAvailability:
    """
    Whether calling Gemini could plausibly succeed, from cooldown state alone.

    A pool counts as unusable only when every key is cooled down for every model
    rotation could choose — one model's 429 is not the provider's answer.
    """
    return pool_availability(load_gemini_credentials(), _rotation_scopes())


def release_gemini_cooldown() -> Optional[str]:
    """Free the soonest-recovering Gemini key so one attempt can still be made."""
    return release_soonest_cooldown(load_gemini_credentials(), _rotation_scopes())


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

    generation_config: Dict[str, Any] = {
        "temperature": 0.15,
        "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS,
        "responseMimeType": "application/json",
    }
    thinking_level = get_thinking_level()
    if thinking_level.lower() != THINKING_LEVEL_OPT_OUT:
        generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": generation_config,
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

    candidate0 = candidates[0] or {}
    finish_reason = candidate0.get("finishReason") or candidate0.get("finish_reason")
    if finish_reason:
        # Surface truncation vs STOP so ops can tell short critiques from
        # mid-JSON cutoff (no secrets / no full prompt bodies).
        level = (
            logging.WARNING
            if str(finish_reason).upper() in ("MAX_TOKENS", "LENGTH")
            else logging.INFO
        )
        logger.log(level, "Gemini finishReason=%s", finish_reason)

    # Token counts make "was the budget the constraint?" answerable from
    # production logs: a STOP with candidatesTokenCount far below
    # GEMINI_MAX_OUTPUT_TOKENS means the model chose to be brief, while a
    # thoughtsTokenCount in the thousands means thinking, not output, is
    # driving latency. Counts only — no prompt or response content.
    usage = data.get("usageMetadata")
    if isinstance(usage, dict):
        logger.info(
            "Gemini usage: prompt=%s candidates=%s thoughts=%s total=%s "
            "(maxOutputTokens=%s)",
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
            usage.get("thoughtsTokenCount"),
            usage.get("totalTokenCount"),
            GEMINI_MAX_OUTPUT_TOKENS,
        )

    parts = (candidate0.get("content") or {}).get("parts") or []
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


def _retry_hint_seconds(response: httpx.Response) -> Optional[float]:
    """
    Seconds Gemini asked us to wait, from `Retry-After` or a `RetryInfo` detail.

    Gemini reports quota timing in the error body rather than only in headers:
    `error.details[]` may carry `{"@type": ".../RetryInfo", "retryDelay": "37s"}`.
    None means it told us nothing usable, and the default cooldown applies.
    """
    header = parse_retry_after(response.headers.get("retry-after"))
    if header is not None:
        return header
    try:
        body = response.json()
    except Exception:
        return None
    details = ((body or {}).get("error") or {}).get("details")
    if not isinstance(details, list):
        return None
    for detail in details:
        if not isinstance(detail, dict):
            continue
        if "RetryInfo" not in str(detail.get("@type") or ""):
            continue
        hint = parse_duration_hint(detail.get("retryDelay"))
        if hint is not None:
            return hint
    return None


async def _call_gemini_once(
    api_key: str,
    messages: list[dict[str, str]],
    resolved_model: str,
    timeout: float = GEMINI_TIMEOUT,
) -> str:
    """Single Gemini HTTP attempt with a concrete API key.

    `timeout` is a hard ceiling on the whole attempt, enforced with
    `asyncio.wait_for` rather than left to httpx: httpx applies its timeout per
    operation, so connect and read can each take the full value and a call sized
    to the remaining request budget could still overshoot it.
    """
    url = f"{GEMINI_API_BASE}/{resolved_model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = _messages_to_gemini_payload(messages)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await asyncio.wait_for(
                client.post(url, headers=headers, json=payload),
                timeout=timeout,
            )
    except (httpx.TimeoutException, asyncio.TimeoutError) as e:
        raise GeminiTimeoutError(
            f"Gemini request timed out after {timeout:.1f}s"
        ) from e
    except httpx.RequestError as e:
        raise GeminiError(f"Gemini request failed: {e}") from e

    if response.status_code == 429:
        raise GeminiRateLimitError(
            "Gemini rate limit exceeded",
            status_code=429,
            retry_after=_retry_hint_seconds(response),
        )

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


async def call_gemini(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    deadline_monotonic: Optional[float] = None,
) -> str:
    """
    Call Gemini generateContent with the given messages.

    Uses the API key pool: on 401/403/429, cools down the failing key and
    retries with another eligible key (bounded by pool size).

    `deadline_monotonic` bounds every attempt in that loop, so N pooled keys
    cannot cost N times GEMINI_TIMEOUT and overrun the caller's request budget.
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

        timeout = resolve_call_timeout(
            deadline_monotonic, GEMINI_TIMEOUT, GEMINI_MIN_SLICE_S
        )
        if timeout is None:
            # A failure that already happened explains more than "and then we
            # ran out of time", so it wins when both are true.
            if last_error is not None:
                raise last_error
            raise GeminiTimeoutError(
                describe_skip("Gemini", deadline_monotonic, GEMINI_MIN_SLICE_S)
            )

        attempted.add(cred.id)
        idx = credential_pool_index(pool, cred.id)
        cred_ref = format_credential_ref("gemini", idx, cred.label)
        try:
            return await _call_gemini_once(
                cred.api_key, messages, resolved_model, timeout
            )
        except GeminiError as e:
            status = e.status_code
            if status in cooldown_codes:
                cooldown_s = clamp_cooldown_seconds(getattr(e, "retry_after", None))
                mark_cooldown(cred.id, cooldown_s, scope=resolved_model)
                observe_refusal(
                    "gemini",
                    cred.id,
                    cooldown_s,
                    model=resolved_model,
                    reason=f"HTTP {status}",
                )
                logger.warning(
                    "%s model=%s failed with HTTP %s; cooling down %.0fs for this "
                    "model and trying next key",
                    cred_ref,
                    resolved_model,
                    status,
                    cooldown_s,
                )
                last_error = e
                continue
            raise


async def call_gemini_with_rotation(
    messages: list[dict[str, str]],
    deadline_monotonic: Optional[float] = None,
) -> ProviderOutput:
    """
    Call Gemini with in-provider model rotation and bounded retry.

    When rotation is enabled (GEMINI_MODEL unset), attempts up to 2 distinct
    models from ALLOWED_GEMINI_MODELS. When GEMINI_MODEL pins a model,
    behaves like a single call_gemini() with no model retry.

    `deadline_monotonic` is the end of Gemini's *phase*, which the failover
    chain sets short of the request deadline by what Groq and Cloudflare need to
    get a turn. The sibling attempt is therefore skipped exactly when it would
    starve them — decided from the time the first attempt actually spent, which
    a flag computed before that attempt could not know
    (`fix-function-invocation-timeout`).

    Returns the raw text together with the model that produced it — after a
    retry that is the second model, not the first one attempted.
    """
    models = select_gemini_models(n=2)
    first_model = models[0]

    try:
        return ProviderOutput(
            await call_gemini(
                messages, model=first_model, deadline_monotonic=deadline_monotonic
            ),
            first_model,
        )
    except (GeminiRateLimitError, GeminiServerError, GeminiTimeoutError):
        if len(models) < 2:
            raise
        if (
            resolve_call_timeout(
                deadline_monotonic, GEMINI_TIMEOUT, GEMINI_MIN_SLICE_S
            )
            is None
        ):
            # Too little of the phase left for a sibling model, and the first
            # model's failure is the more useful error to report upward.
            raise
        second_model = models[1]
        return ProviderOutput(
            await call_gemini(
                messages, model=second_model, deadline_monotonic=deadline_monotonic
            ),
            second_model,
        )
