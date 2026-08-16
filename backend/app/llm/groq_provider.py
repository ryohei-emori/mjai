"""
Groq LLM provider using OpenAI-compatible API.
Primary provider for fast inference (~1-3 seconds).
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import httpx
from typing import Any, Optional, List, Dict, Set

from .budget import describe_skip, resolve_call_timeout
from .provider_output import ProviderOutput
from .key_pool import (
    PoolAvailability,
    acquire_groq,
    cooldown_status_codes,
    credential_pool_index,
    format_credential_ref,
    is_groq_configured,
    load_groq_credentials,
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

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Curated rotation pool of general-purpose instruction-following chat models
# known to produce coherent structured JSON output for this task. A model is
# selected per request (see select_groq_models()) instead of always using a
# single fixed id, so that a single model's rate limit, transient failure, or
# deprecation cannot silently break suggestion generation.
#
# Deliberately EXCLUDED, and why:
# - llama-3.3-70b-versatile, llama-3.1-8b-instant: both have a confirmed
#   Groq shutdown date of 2026-08-16 (console.groq.com/docs/deprecations,
#   reconfirmed live at implementation time) — including either would just
#   reintroduce the single-model-deprecation risk this rotation exists to fix.
#   (llama-3.3-70b-versatile was this module's previous DEFAULT_GROQ_MODEL.)
# - qwen/qwen3-32b: already deprecated/shut down (404s) as of 2026-07-17.
# - openai/gpt-oss-safeguard-20b: safety/policy-classification tuned, not a
#   general correction model.
# - groq/compound, groq/compound-mini: agentic/tool-use meta-models (web
#   search, code exec) atypical for a plain text-correction prompt, and
#   capped at a much lower 250 RPD than the chat models.
# - meta-llama/llama-prompt-guard-2-22m/86m: classifier/moderation models,
#   not general chat/completion models.
# - allam-2-7b: general chat but Arabic-focused; not evaluated for Japanese
#   quality, out of scope for this rotation pool.
#
# NOTE: This is a static, manually-reviewed allow-list — there is no runtime
# catalog-refresh mechanism. If Groq announces further deprecations, update
# this list manually as a follow-up change.
#
# qwen/qwen3.6-27b was removed from the default rotation pool after live
# Chinese-enforcement smoke on bilingual CN-source / JP-target corpora:
# even with reasoning_effort=none it frequently wrote Japanese
# reason/overallComment (or empty bodies), dragging Chinese-OK rates near
# zero. It remains pin-able via GROQ_MODEL for debugging.
ALLOWED_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

# Kept for backward compatibility / as the implicit single-model fallback
# target referenced by get_groq_model() when GROQ_MODEL is unset. Not used
# directly for rotation (see ALLOWED_GROQ_MODELS above).
DEFAULT_GROQ_MODEL = ALLOWED_GROQ_MODELS[0]
# Epic-length bilingual corpora + ≥5 suggestions regularly need >10s;
# keep bounded but avoid premature timeout→CF prose fallback.
GROQ_TIMEOUT = 25.0  # seconds

# Shortest slice worth spending on Groq. Measured 1-3s for this prompt, so Groq
# stays worth attempting on a nearly spent budget — which is exactly why it must
# not be crowded out by a slow primary (see budget.resolve_call_timeout).
GROQ_MIN_SLICE_S = 5.0

# Models whose default behavior on Groq is to emit a <think>...</think>
# reasoning block INSIDE the message content before the final answer.
# Discovered via live smoke-testing during implementation: with the default
# reasoning_effort ("default"), qwen/qwen3.6-27b's 1024-token response
# budget can be entirely consumed by the thinking block, truncating the
# response before any JSON is emitted — parse_model_output() then falls
# back to extracting the literal placeholder text from the system prompt's
# format example ("該当箇所の抜粋" etc.) as if it were a real answer, a
# silent correctness failure (not an exception, so it would not trigger
# in-provider retry or Cloudflare fallback). Fix: pass
# reasoning_effort="none" for these models to disable the thinking block
# entirely (confirmed via live testing to produce clean JSON output).
# gpt-oss-120b/20b are not in this set: they already return clean JSON
# content without an inline thinking block at default settings.
QWEN_REASONING_MODELS = {"qwen/qwen3.6-27b"}


class GroqError(Exception):
    """Error from Groq API."""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        # Seconds Groq itself asked us to wait, when it said so. Carried on the
        # error so the caller can size the cooldown without re-reading the
        # response it no longer has.
        self.retry_after = retry_after


class GroqRateLimitError(GroqError):
    """Groq API rate limit error (429)."""
    pass


class GroqServerError(GroqError):
    """Groq API server error (5xx)."""
    pass


class GroqTimeoutError(GroqError):
    """Groq API timeout error."""
    pass


class GroqJsonValidateError(GroqError):
    """Groq rejected the completion under response_format=json_object.

    Treated as retriable across a different model in the rotation pool —
    live smoke showed occasional empty `failed_generation` 400s that a
    second model (or Cloudflare) can salvage.
    """
    pass


def get_groq_api_key() -> Optional[str]:
    """Return a configured Groq key if the pool is non-empty (back-compat).

    Prefer `call_groq` / the key pool for outbound calls — this helper is
    used for "is configured?" checks and does not advance round-robin.
    """
    creds = load_groq_credentials()
    return creds[0].api_key if creds else None


def get_groq_model() -> str:
    """Get Groq model id, overridable via GROQ_MODEL env var."""
    return os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL


def is_rotation_enabled() -> bool:
    """
    Whether per-request model rotation across ALLOWED_GROQ_MODELS is active.

    Rotation is enabled unless GROQ_MODEL is explicitly set to a non-empty
    value, in which case that single model is pinned for every request
    (backward-compat / debugging override) and rotation is disabled.
    """
    return not os.environ.get("GROQ_MODEL")


def select_groq_models(n: int = 2) -> List[str]:
    """
    Select up to n distinct Groq models to attempt for a single request.

    When rotation is enabled, returns n distinct models chosen via
    random.sample() from ALLOWED_GROQ_MODELS (no persistent counter, since
    Vercel serverless invocations are stateless per-request — see
    design.md Decision 2). When GROQ_MODEL pins a single model, rotation is
    disabled and only that one model is returned regardless of n.
    """
    if not is_rotation_enabled():
        return [get_groq_model()]
    n = min(n, len(ALLOWED_GROQ_MODELS))
    return random.sample(ALLOWED_GROQ_MODELS, n)


def _rotation_scopes() -> List[Optional[str]]:
    """Models a request could pick, which is what cooldowns are scoped to."""
    if not is_rotation_enabled():
        return [get_groq_model()]
    return list(ALLOWED_GROQ_MODELS)


def groq_availability() -> PoolAvailability:
    """
    Whether calling Groq could plausibly succeed, from cooldown state alone.

    A pool counts as unusable only when every key is cooled down for every model
    rotation could choose — one model's 429 is not the provider's answer.
    """
    return pool_availability(load_groq_credentials(), _rotation_scopes())


def release_groq_cooldown() -> Optional[str]:
    """Free the soonest-recovering Groq key so one attempt can still be made."""
    return release_soonest_cooldown(load_groq_credentials(), _rotation_scopes())


def _retry_hint_seconds(response: httpx.Response) -> Optional[float]:
    """
    Seconds Groq asked us to wait, from `Retry-After` or its reset headers.

    Groq reports remaining limits on every response, so a refused request tells
    us when the limit clears (`x-ratelimit-reset-requests` uses a compact
    duration form such as `2m59.56s`). None means nothing usable was sent, and
    the default cooldown applies.
    """
    header = parse_retry_after(response.headers.get("retry-after"))
    if header is not None:
        return header
    for name in ("x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
        hint = parse_duration_hint(response.headers.get(name))
        if hint is not None:
            return hint
    return None


async def _call_groq_once(
    api_key: str,
    messages: list[dict[str, str]],
    resolved_model: str,
    timeout: float = GROQ_TIMEOUT,
) -> str:
    """Single Groq HTTP attempt with a concrete API key.

    `timeout` is a hard ceiling on the whole attempt (see
    `gemini_provider._call_gemini_once` for why httpx's own timeout is not
    sufficient on its own).
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        # Long TARGET TEXT (e.g. multi-paragraph epic corpus) with ≥5
        # suggestions needs headroom; 1024/2048 truncated mid-JSON in live smoke.
        "max_tokens": 4096,
        "temperature": 0.15,
        # Force a JSON object body — prompts already require JSON-only output;
        # this prevents prose-only replies that burn the parse-retry budget.
        "response_format": {"type": "json_object"},
    }
    if resolved_model in QWEN_REASONING_MODELS:
        # See QWEN_REASONING_MODELS comment: without this, thinking tokens
        # can consume the entire max_tokens budget before any JSON is emitted.
        payload["reasoning_effort"] = "none"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await asyncio.wait_for(
                client.post(GROQ_API_URL, headers=headers, json=payload),
                timeout=timeout,
            )
    except (httpx.TimeoutException, asyncio.TimeoutError) as e:
        raise GroqTimeoutError(f"Groq request timed out after {timeout:.1f}s") from e
    except httpx.RequestError as e:
        raise GroqError(f"Groq request failed: {e}") from e

    if response.status_code == 429:
        raise GroqRateLimitError(
            "Groq rate limit exceeded",
            status_code=429,
            retry_after=_retry_hint_seconds(response),
        )

    if response.status_code >= 500:
        raise GroqServerError(
            f"Groq server error: {response.status_code}",
            status_code=response.status_code,
        )

    if response.status_code == 400 and "json_validate_failed" in response.text:
        raise GroqJsonValidateError(
            f"Groq JSON validation failed: {response.text}",
            status_code=400,
        )

    if response.status_code != 200:
        raise GroqError(
            f"Groq API error: {response.status_code} - {response.text}",
            status_code=response.status_code,
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise GroqError(f"Unexpected Groq response format: {data}") from e


async def call_groq(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    deadline_monotonic: Optional[float] = None,
) -> str:
    """
    Call Groq API with the given messages.

    Uses the API key pool: on 401/403/429, cools down the failing key and
    retries with another eligible key (bounded by pool size).

    Args:
        messages: List of message dicts with role and content keys.
        model: Optional model id override. Defaults to get_groq_model()
            (the GROQ_MODEL env var, or DEFAULT_GROQ_MODEL if unset).
        deadline_monotonic: Optional monotonic deadline bounding every attempt
            in the key-pool loop, so N pooled keys cannot cost N times
            GROQ_TIMEOUT and overrun the caller's request budget.

    Returns:
        The assistant's response content.

    Raises:
        GroqError: If API key is missing or other error occurs.
        GroqRateLimitError: If rate limited (429).
        GroqServerError: If server error (5xx).
        GroqTimeoutError: If request times out.
    """
    if not is_groq_configured():
        raise GroqError("GROQ_API_KEY not configured")

    resolved_model = model or get_groq_model()
    pool = load_groq_credentials()
    pool_size = len(pool)
    attempted: Set[str] = set()
    last_error: Optional[GroqError] = None
    cooldown_codes = cooldown_status_codes()

    while True:
        # Scope cooldown by model so a 429 on model A does not block model B
        # rotation (Groq limits are often per-model TPM/RPD).
        cred = acquire_groq(
            exclude_ids=list(attempted),
            cooldown_scope=resolved_model,
        )
        if cred is None:
            if last_error is not None:
                # Preserve original status when possible; wrap message for ops clarity.
                raise GroqRateLimitError(
                    f"All Groq API keys are in cooldown or exhausted "
                    f"(pool_size={pool_size}, model={resolved_model}, "
                    f"cooled_or_tried={len(attempted)})",
                    status_code=getattr(last_error, "status_code", None) or 429,
                )
            # Pool has keys but all are cooled down (or excluded) for this model.
            raise GroqRateLimitError(
                f"All Groq API keys are in cooldown or exhausted "
                f"(pool_size={pool_size}, model={resolved_model})",
                status_code=429,
            )

        timeout = resolve_call_timeout(
            deadline_monotonic, GROQ_TIMEOUT, GROQ_MIN_SLICE_S
        )
        if timeout is None:
            # A failure that already happened explains more than "and then we
            # ran out of time", so it wins when both are true.
            if last_error is not None:
                raise last_error
            raise GroqTimeoutError(
                describe_skip("Groq", deadline_monotonic, GROQ_MIN_SLICE_S)
            )

        attempted.add(cred.id)
        idx = credential_pool_index(pool, cred.id)
        cred_ref = format_credential_ref("groq", idx, cred.label)
        try:
            return await _call_groq_once(
                cred.api_key, messages, resolved_model, timeout
            )
        except GroqError as e:
            status = e.status_code
            if status in cooldown_codes:
                cooldown_s = clamp_cooldown_seconds(getattr(e, "retry_after", None))
                mark_cooldown(cred.id, cooldown_s, scope=resolved_model)
                observe_refusal(
                    "groq",
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


async def call_groq_with_rotation(
    messages: list[dict[str, str]],
    deadline_monotonic: Optional[float] = None,
) -> ProviderOutput:
    """
    Call Groq API with in-provider model rotation and bounded retry.

    When rotation is enabled (GROQ_MODEL unset), attempts up to 2 distinct
    models from ALLOWED_GROQ_MODELS: on a retriable failure
    (GroqRateLimitError/GroqServerError/GroqTimeoutError) from the first
    model, retries once against a second, different model. If GROQ_MODEL
    pins a single model, rotation is disabled and this behaves exactly like
    a single call_groq() invocation — no retry, matching prior behavior.

    `deadline_monotonic` is the end of Groq's *phase*, which the failover chain
    sets short of the request deadline by what Cloudflare needs to get a turn.
    The sibling attempt is skipped exactly when it would starve that turn
    (`fix-function-invocation-timeout`).

    Non-retriable GroqError (e.g. missing API key, malformed response) is
    raised immediately without a retry attempt, since a different model
    would not fix it.

    Returns the raw text together with the model that produced it — after a
    retry that is the second model, not the first one attempted.

    Raises:
        GroqError and subclasses: the final attempt's error, if all
            attempted models fail.
    """
    models = select_groq_models(n=2)
    first_model = models[0]

    try:
        return ProviderOutput(
            await call_groq(
                messages, model=first_model, deadline_monotonic=deadline_monotonic
            ),
            first_model,
        )
    except (GroqRateLimitError, GroqServerError, GroqTimeoutError, GroqJsonValidateError):
        if len(models) < 2:
            raise
        if (
            resolve_call_timeout(deadline_monotonic, GROQ_TIMEOUT, GROQ_MIN_SLICE_S)
            is None
        ):
            # Too little of the phase left for a sibling model, and the first
            # model's failure is the more useful error to report upward.
            raise
        second_model = models[1]
        return ProviderOutput(
            await call_groq(
                messages, model=second_model, deadline_monotonic=deadline_monotonic
            ),
            second_model,
        )
