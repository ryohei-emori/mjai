"""
AI suggestions generation with provider failover.
Groq (primary) -> Cloudflare Workers AI (fallback).
"""

from __future__ import annotations

import logging
from typing import Optional

from .prompts import build_messages
from .parser import parse_model_output, ParsedResponse
from .groq_provider import (
    call_groq_with_rotation,
    get_groq_api_key,
    GroqError,
    GroqRateLimitError,
    GroqServerError,
    GroqTimeoutError,
)
from .cloudflare_provider import (
    call_cloudflare,
    get_cloudflare_credentials,
    CloudflareError,
)

logger = logging.getLogger(__name__)


class SuggestionsError(Exception):
    """Error generating suggestions from all providers."""
    def __init__(self, message: str, groq_error: Optional[str] = None, cf_error: Optional[str] = None):
        super().__init__(message)
        self.groq_error = groq_error
        self.cf_error = cf_error


class NoProvidersConfiguredError(SuggestionsError):
    """No LLM providers are configured."""
    pass


def are_providers_configured() -> bool:
    """Check if at least one provider is configured."""
    groq_key = get_groq_api_key()
    cf_account, cf_token = get_cloudflare_credentials()
    return bool(groq_key) or (bool(cf_account) and bool(cf_token))


async def generate_suggestions(original_text: str, target_text: str) -> ParsedResponse:
    """
    Generate AI correction suggestions for the given text.
    
    Tries Groq first (with in-provider model rotation and one retry across
    a different Groq model on a retriable failure), falls back to
    Cloudflare on failure.
    
    Args:
        original_text: The original Japanese text.
        target_text: The target/translated text to correct.
        
    Returns:
        ParsedResponse with suggestions and overall comment.
        
    Raises:
        NoProvidersConfiguredError: If no providers are configured.
        SuggestionsError: If all providers fail.
    """
    if not are_providers_configured():
        raise NoProvidersConfiguredError(
            "No LLM providers configured. Set GROQ_API_KEY or CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN."
        )
    
    messages = build_messages(original_text, target_text)
    
    groq_error: Optional[str] = None
    cf_error: Optional[str] = None
    
    groq_key = get_groq_api_key()
    if groq_key:
        try:
            logger.info("Attempting Groq inference...")
            raw_output = await call_groq_with_rotation(messages)
            logger.info(f"Groq inference successful, raw output length: {len(raw_output)}")
            logger.debug(f"Groq raw output: {raw_output[:500]}...")
            result = parse_model_output(raw_output)
            logger.info(f"Parsed result: {len(result['suggestions'])} suggestions")
            return result
        except (GroqRateLimitError, GroqServerError, GroqTimeoutError) as e:
            logger.warning(f"Groq failed with retriable error, falling back to Cloudflare: {e}")
            groq_error = str(e)
        except GroqError as e:
            logger.error(f"Groq failed with non-retriable error: {e}")
            groq_error = str(e)
    else:
        logger.info("Groq not configured, trying Cloudflare directly")
        groq_error = "GROQ_API_KEY not configured"
    
    cf_account, cf_token = get_cloudflare_credentials()
    if cf_account and cf_token:
        try:
            logger.info("Attempting Cloudflare Workers AI inference...")
            raw_output = await call_cloudflare(messages)
            logger.info(f"Cloudflare inference successful, raw output length: {len(raw_output)}")
            logger.debug(f"Cloudflare raw output: {raw_output[:500]}...")
            result = parse_model_output(raw_output)
            logger.info(f"Parsed result: {len(result['suggestions'])} suggestions")
            return result
        except CloudflareError as e:
            logger.error(f"Cloudflare also failed: {e}")
            cf_error = str(e)
    else:
        cf_error = "Cloudflare credentials not configured"
    
    raise SuggestionsError(
        "All LLM providers failed",
        groq_error=groq_error,
        cf_error=cf_error,
    )
