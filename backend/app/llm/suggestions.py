"""
AI suggestions generation with provider failover.
Groq (primary) -> Cloudflare Workers AI (fallback).

Two independent, composable retry axes exist across this module and its
providers:

1. Network-level retry (existing, unaffected by this module's own retry
   loop): `groq_provider.call_groq_with_rotation()` retries once against a
   second Groq model on a retriable HTTP failure (429/5xx/timeout) before
   this module falls over to Cloudflare. This axis handles *transport*
   failures — the provider never returned usable content.

2. Content-quality-level retry (`MAX_PARSE_RETRY_ATTEMPTS` below): a
   provider call can succeed at the network level yet return content that
   is unusable in one of two ways:
   - it fails to parse as valid JSON at all (e.g. a small/preview model
     emitting prose, reasoning tokens, or truncated output) — see
     `parser.is_json_extraction_failure`; or
   - it parses successfully but violates the bilingual field-content rule
     (a suggestion's `reason` or the `overallComment` written in Japanese
     instead of the required Simplified Chinese) — see
     `parser.has_non_chinese_reason`.
   When either condition is true, `generate_suggestions()` retries the
   *entire* Groq-then-Cloudflare pass (not just a single provider call) up
   to `MAX_PARSE_RETRY_ATTEMPTS` times, sharing one attempt budget across
   both conditions, before giving up and returning the last result as-is
   (the parse-failure placeholder, or the best available but
   still-non-Chinese response). A genuine network-level failure
   (`SuggestionsError`, raised when both providers fail at the HTTP layer
   even after their own retries) is NOT retried by this axis and propagates
   immediately — retrying a fully-down network path would not help and
   would only add latency.

Worst case total LLM calls for axis 2, per `generate_suggestions()` call:
`MAX_PARSE_RETRY_ATTEMPTS` passes * (up to 2 Groq attempts via rotation,
plus 1 Cloudflare attempt if Groq raises) = up to 9 calls. In practice
almost every pass succeeds at parsing on the first attempt (parse/language
failures are rare), so this bound is a deliberate trade-off favoring
eventual success over a strict latency guarantee for the rare failure case
— see design.md Decision 8 in the `add-groq-cloudflare-suggestions` change,
and Decision 6 in the `refine-suggestion-card-interactions` change for the
language-check addition.
"""

from __future__ import annotations

import logging
from typing import Optional

from .prompts import build_messages
from .parser import (
    parse_model_output,
    is_json_extraction_failure,
    has_non_chinese_reason,
    ParsedResponse,
)
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

# Total number of generate+parse passes attempted when the model's response
# either fails to parse as JSON or fails the Chinese-language content check
# (see parser.is_json_extraction_failure / parser.has_non_chinese_reason),
# before giving up. Both conditions share this one attempt budget. See
# module docstring for how this composes with each provider's own
# network-level retry.
MAX_PARSE_RETRY_ATTEMPTS = 3


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


async def _generate_suggestions_once(messages: list[dict]) -> ParsedResponse:
    """
    Single generate+parse pass: try Groq (with its own in-provider model
    rotation/retry), fall back to Cloudflare on failure.

    This is the body of what used to be `generate_suggestions()` before the
    JSON-parse retry loop (see module docstring) was added around it. May
    return a ParsedResponse that is itself a parse failure (see
    `parser.is_json_extraction_failure`) — that is not treated as an
    exception here, since it's a valid (if unhelpful) response from the
    caller's perspective; the retry loop in `generate_suggestions()`
    decides whether to retry based on that.

    Raises:
        SuggestionsError: If all configured providers fail at the network
            level.
    """
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


async def generate_suggestions(original_text: str, target_text: str) -> ParsedResponse:
    """
    Generate AI correction suggestions for the given text.
    
    Tries Groq first (with in-provider model rotation and one retry across
    a different Groq model on a retriable failure), falls back to
    Cloudflare on failure. If a pass succeeds at the network level but its
    content either fails to parse as JSON or fails the Chinese-language
    content check (a suggestion's `reason` or `overallComment` written in
    Japanese instead of the required Simplified Chinese), the whole pass is
    retried up to `MAX_PARSE_RETRY_ATTEMPTS` times before giving up (see
    module docstring for how this composes with the network-level retry
    above).
    
    Args:
        original_text: The original Japanese text.
        target_text: The target/translated text to correct.
        
    Returns:
        ParsedResponse with suggestions and overall comment. May be the
        parse-failure placeholder response if every attempt failed to
        parse (see `parser.is_json_extraction_failure`), or the
        last-attempted result even if it still fails the Chinese-language
        check (see `parser.has_non_chinese_reason`) — either way this
        degrades gracefully rather than raising.
        
    Raises:
        NoProvidersConfiguredError: If no providers are configured.
        SuggestionsError: If all providers fail at the network level.
    """
    if not are_providers_configured():
        raise NoProvidersConfiguredError(
            "No LLM providers configured. Set GROQ_API_KEY or CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN."
        )

    messages = build_messages(original_text, target_text)

    last_result: Optional[ParsedResponse] = None
    for attempt in range(1, MAX_PARSE_RETRY_ATTEMPTS + 1):
        result = await _generate_suggestions_once(messages)
        if not is_json_extraction_failure(result) and not has_non_chinese_reason(result):
            return result
        reason = (
            "JSON parse failure" if is_json_extraction_failure(result) else "non-Chinese reason/overallComment"
        )
        logger.warning(
            f"{reason} on attempt {attempt}/{MAX_PARSE_RETRY_ATTEMPTS}; "
            f"{'retrying' if attempt < MAX_PARSE_RETRY_ATTEMPTS else 'giving up'}"
        )
        last_result = result

    # All attempts failed (JSON parse and/or Chinese-language check) —
    # return the last result rather than raising, matching the pre-existing
    # "degrade gracefully" behavior of surfacing a best-effort/placeholder
    # response rather than a 503.
    assert last_result is not None  # loop runs at least once (MAX_PARSE_RETRY_ATTEMPTS >= 1)
    return last_result
