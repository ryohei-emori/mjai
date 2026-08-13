"""
Cloudflare Workers AI provider.
Fallback provider when Groq is unavailable.
"""

from __future__ import annotations

import os
import httpx
from typing import Any, Optional, Tuple, List, Dict

CF_MODEL = "@cf/meta/llama-3.1-8b-instruct"
CF_TIMEOUT = 15.0  # slightly higher timeout for fallback


class CloudflareError(Exception):
    """Error from Cloudflare Workers AI API."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CloudflareTimeoutError(CloudflareError):
    """Cloudflare API timeout error."""
    pass


def get_cloudflare_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Get Cloudflare credentials from environment."""
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    return account_id, api_token


def get_cloudflare_api_url(account_id: str) -> str:
    """Build Cloudflare Workers AI API URL."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_MODEL}"


async def call_cloudflare(messages: list[dict[str, str]]) -> str:
    """
    Call Cloudflare Workers AI API with the given messages.
    
    Args:
        messages: List of message dicts with role and content keys.
        
    Returns:
        The assistant's response content.
        
    Raises:
        CloudflareError: If credentials are missing or other error occurs.
        CloudflareTimeoutError: If request times out.
    """
    account_id, api_token = get_cloudflare_credentials()
    
    if not account_id or not api_token:
        raise CloudflareError("Cloudflare credentials not configured (CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN)")
    
    api_url = get_cloudflare_api_url(account_id)
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    
    payload: dict[str, Any] = {
        "messages": messages,
        # Match Groq headroom for multi-suggestion JSON on long TARGET TEXT.
        "max_tokens": 2048,
        "temperature": 0.2,
    }
    
    try:
        async with httpx.AsyncClient(timeout=CF_TIMEOUT) as client:
            response = await client.post(api_url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise CloudflareTimeoutError(f"Cloudflare request timed out after {CF_TIMEOUT}s") from e
    except httpx.RequestError as e:
        raise CloudflareError(f"Cloudflare request failed: {e}") from e
    
    if response.status_code != 200:
        raise CloudflareError(f"Cloudflare API error: {response.status_code} - {response.text}", status_code=response.status_code)
    
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


def _extract_cloudflare_text(result: Any) -> Optional[str]:
    """Normalize Workers AI `result` payloads to a single assistant string."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        # Common shapes: {"response": "..."} or nested content/text fields.
        for key in ("response", "content", "text", "output", "generated_text"):
            value = result.get(key)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict):
                nested = _extract_cloudflare_text(value)
                if nested:
                    return nested
            if isinstance(value, list):
                nested = _extract_cloudflare_text(value)
                if nested:
                    return nested
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
