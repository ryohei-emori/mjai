"""
Cloudflare Workers AI provider.
Fallback provider when Groq is unavailable.
"""

from __future__ import annotations

import json
import logging
import httpx
from typing import Any, Optional, Tuple, List, Dict, Set

from .key_pool import (
    acquire_cloudflare,
    cooldown_status_codes,
    credential_pool_index,
    format_credential_ref,
    is_cloudflare_configured,
    load_cloudflare_credentials,
    mark_cooldown,
)

logger = logging.getLogger(__name__)

# Prefer a stronger instruct model when available on Workers AI; 8B often
# returns Chinese prose without a JSON object on long bilingual prompts.
CF_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
CF_TIMEOUT = 45.0  # higher timeout for larger fallback model


class CloudflareError(Exception):
    """Error from Cloudflare Workers AI API."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CloudflareTimeoutError(CloudflareError):
    """Cloudflare API timeout error."""
    pass


class CloudflareRateLimitError(CloudflareError):
    """Cloudflare API rate limit / auth cooldown error (401/403/429)."""
    pass


def get_cloudflare_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Return first configured CF pair if the pool is non-empty (back-compat).

    Prefer `call_cloudflare` / the key pool for outbound calls — this helper
    is used for "is configured?" checks and does not advance round-robin.
    """
    creds = load_cloudflare_credentials()
    if not creds:
        return None, None
    return creds[0].account_id, creds[0].api_token


def get_cloudflare_api_url(account_id: str) -> str:
    """Build Cloudflare Workers AI API URL."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_MODEL}"


async def _call_cloudflare_once(
    account_id: str,
    api_token: str,
    messages: list[dict[str, str]],
) -> str:
    """Single Cloudflare Workers AI HTTP attempt."""
    api_url = get_cloudflare_api_url(account_id)

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    # Prepend a short JSON-only reminder; small CF models otherwise drift to
    # Chinese prose without a suggestions array (live Chinese-enforcement smoke).
    cf_messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "只输出一个完整 JSON 对象："
                '{"suggestions":[{"id":"1","original":"...","reason":"简体中文","sourceExcerpt":""}],'
                '"overallComment":"简体中文"}。禁止其他文字或 Markdown。'
            ),
        },
        *messages,
    ]
    payload: dict[str, Any] = {
        "messages": cf_messages,
        # Match Groq headroom for multi-suggestion JSON on long TARGET TEXT.
        "max_tokens": 4096,
        "temperature": 0.15,
    }

    try:
        async with httpx.AsyncClient(timeout=CF_TIMEOUT) as client:
            response = await client.post(api_url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise CloudflareTimeoutError(f"Cloudflare request timed out after {CF_TIMEOUT}s") from e
    except httpx.RequestError as e:
        raise CloudflareError(f"Cloudflare request failed: {e}") from e

    if response.status_code == 429:
        raise CloudflareRateLimitError(
            "Cloudflare rate limit exceeded",
            status_code=429,
        )
    if response.status_code in (401, 403):
        raise CloudflareRateLimitError(
            f"Cloudflare auth error: {response.status_code}",
            status_code=response.status_code,
        )

    if response.status_code != 200:
        raise CloudflareError(
            f"Cloudflare API error: {response.status_code} - {response.text}",
            status_code=response.status_code,
        )

    data = response.json()

    if not data.get("success", False):
        errors = data.get("errors", [])
        raise CloudflareError(f"Cloudflare API returned error: {errors}")

    try:
        result = data["result"]
    except (KeyError, TypeError) as e:
        raise CloudflareError(f"Unexpected Cloudflare response format: {data}") from e

    content = _extract_cloudflare_text(result)
    if content is not None:
        return content
    raise CloudflareError(
        f"Unexpected Cloudflare response content: {type(result).__name__}"
    )


async def call_cloudflare(messages: list[dict[str, str]]) -> str:
    """
    Call Cloudflare Workers AI API with the given messages.

    Uses the credential pool: on 401/403/429, cools down the failing pair
    and retries with another eligible credential (bounded by pool size).

    Args:
        messages: List of message dicts with role and content keys.

    Returns:
        The assistant's response content.

    Raises:
        CloudflareError: If credentials are missing or other error occurs.
        CloudflareTimeoutError: If request times out.
        CloudflareRateLimitError: If rate limited or auth failed after pool exhaust.
    """
    if not is_cloudflare_configured():
        raise CloudflareError(
            "Cloudflare credentials not configured "
            "(CLOUDFLARE_ACCOUNT_ID/TOKEN or CLOUDFLARE_ACCOUNT_IDS/API_TOKENS)"
        )

    pool = load_cloudflare_credentials()
    pool_size = len(pool)
    attempted: Set[str] = set()
    last_error: Optional[CloudflareError] = None
    cooldown_codes = cooldown_status_codes()

    while True:
        cred = acquire_cloudflare(exclude_ids=list(attempted))
        if cred is None:
            if last_error is not None:
                raise CloudflareRateLimitError(
                    f"All Cloudflare credentials are in cooldown or exhausted "
                    f"(pool_size={pool_size}, cooled_or_tried={len(attempted)})",
                    status_code=getattr(last_error, "status_code", None) or 429,
                )
            raise CloudflareRateLimitError(
                f"All Cloudflare credentials are in cooldown or exhausted "
                f"(pool_size={pool_size})",
                status_code=429,
            )

        attempted.add(cred.id)
        idx = credential_pool_index(pool, cred.id)
        cred_ref = format_credential_ref("cloudflare", idx, cred.label)
        try:
            return await _call_cloudflare_once(
                cred.account_id, cred.api_token, messages
            )
        except CloudflareError as e:
            status = e.status_code
            if status in cooldown_codes:
                mark_cooldown(cred.id)
                logger.warning(
                    "%s failed with HTTP %s; cooling down and trying next credential",
                    cred_ref,
                    status,
                )
                last_error = e
                continue
            raise


def _extract_cloudflare_text(result: Any) -> Optional[str]:
    """Normalize Workers AI `result` payloads to a single assistant string.

    Observed shapes include:
    - bare string
    - {"response": "..."}
    - {"response": {...}} (some models nest the JSON object)
    - OpenAI-like {"message": {"content": "..."}} / {"choices":[...]}
    - list of content parts
    Returning a serialized JSON string when the model nests a dict under
    `response` avoids TypeError in callers that expect str and lets the
    shared parser extract suggestions.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        # OpenAI-compatible wrappers some Workers AI models return.
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            nested = _extract_cloudflare_text(choices[0])
            if nested:
                return nested
        message = result.get("message")
        if isinstance(message, dict):
            nested = _extract_cloudflare_text(message)
            if nested:
                return nested

        for key in ("response", "content", "text", "output", "generated_text"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):
                # Nested JSON object that *is* the answer — serialize for parser.
                if "suggestions" in value or "指摘" in value or "overallComment" in value:
                    return json.dumps(value, ensure_ascii=False)
                nested = _extract_cloudflare_text(value)
                if nested:
                    return nested
            if isinstance(value, list):
                nested = _extract_cloudflare_text(value)
                if nested:
                    return nested
        # Dict that itself looks like our schema.
        if "suggestions" in result or "指摘" in result or "overallComment" in result:
            return json.dumps(result, ensure_ascii=False)
        # Last resort: any non-empty string leaf under this object.
        for value in result.values():
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, (dict, list)):
                nested = _extract_cloudflare_text(value)
                if nested:
                    return nested
        return None
    if isinstance(result, list):
        parts: List[str] = []
        for item in result:
            if isinstance(item, str):
                parts.append(item)
            else:
                nested = _extract_cloudflare_text(item)
                if nested:
                    parts.append(nested)
        joined = "".join(parts)
        return joined or None
    return None
