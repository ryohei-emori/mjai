"""
Groq LLM provider using OpenAI-compatible API.
Primary provider for fast inference (~1-3 seconds).
"""

from __future__ import annotations

import os
import httpx
from typing import Any, Optional, List, Dict

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TIMEOUT = 10.0  # seconds


class GroqError(Exception):
    """Error from Groq API."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GroqRateLimitError(GroqError):
    """Groq API rate limit error (429)."""
    pass


class GroqServerError(GroqError):
    """Groq API server error (5xx)."""
    pass


class GroqTimeoutError(GroqError):
    """Groq API timeout error."""
    pass


def get_groq_api_key() -> Optional[str]:
    """Get Groq API key from environment."""
    return os.environ.get("GROQ_API_KEY")


async def call_groq(messages: list[dict[str, str]]) -> str:
    """
    Call Groq API with the given messages.
    
    Args:
        messages: List of message dicts with role and content keys.
        
    Returns:
        The assistant's response content.
        
    Raises:
        GroqError: If API key is missing or other error occurs.
        GroqRateLimitError: If rate limited (429).
        GroqServerError: If server error (5xx).
        GroqTimeoutError: If request times out.
    """
    api_key = get_groq_api_key()
    if not api_key:
        raise GroqError("GROQ_API_KEY not configured")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload: dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.2,
    }
    
    try:
        async with httpx.AsyncClient(timeout=GROQ_TIMEOUT) as client:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise GroqTimeoutError(f"Groq request timed out after {GROQ_TIMEOUT}s") from e
    except httpx.RequestError as e:
        raise GroqError(f"Groq request failed: {e}") from e
    
    if response.status_code == 429:
        raise GroqRateLimitError("Groq rate limit exceeded", status_code=429)
    
    if response.status_code >= 500:
        raise GroqServerError(f"Groq server error: {response.status_code}", status_code=response.status_code)
    
    if response.status_code != 200:
        raise GroqError(f"Groq API error: {response.status_code} - {response.text}", status_code=response.status_code)
    
    data = response.json()
    
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise GroqError(f"Unexpected Groq response format: {data}") from e
