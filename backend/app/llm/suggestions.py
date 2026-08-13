"""
AI suggestions generation with provider failover.
Gemini (primary) -> Groq (secondary) -> Cloudflare Workers AI (tertiary).

Two independent, composable retry axes exist across this module and its
providers:

1. Network-level retry (existing, unaffected by this module's own retry
   loop): `gemini_provider.call_gemini_with_rotation()` retries once against
   a second Gemini Flash model on a retriable HTTP failure (429/5xx/timeout)
   before this module falls over to Groq, then Cloudflare. Groq has its own
   in-provider model rotation. This axis handles *transport* failures —
   the provider never returned usable content.

2. Content-quality-level retry (`MAX_PARSE_RETRY_ATTEMPTS` below): a
   provider call can succeed at the network level yet return content that
   is unusable in one of two ways:
   - it fails to parse as valid JSON at all (e.g. a small/preview model
     emitting prose, reasoning tokens, or truncated output) — see
     `parser.is_json_extraction_failure`; or
   - it parses successfully but violates Chinese critique-field rules:
     Japanese prose in `reason`/`overallComment` (`parser.has_non_chinese_reason`)
     or misused Japanese corner brackets 「」 wrapping Chinese prose
     (`parser.has_japanese_corner_quotes_in_critique`; JP TARGET cites OK).
   Within a single pass, if Gemini returns either failure mode, this module
   still tries Groq, then Cloudflare, before returning (same-pass salvage),
   so a usable later response can rescue a Japanese/unparseable earlier body
   without burning the outer retry budget. When all providers in a pass still
   fail the content checks, `generate_suggestions()` retries the *entire*
   Gemini→Groq→Cloudflare pass up to `MAX_PARSE_RETRY_ATTEMPTS` times, sharing
   one attempt budget across both conditions, before giving up and returning
   the last result as-is. A genuine network-level failure (`SuggestionsError`,
   raised when all providers fail at the HTTP layer even after their own
   retries) is NOT retried by this axis and propagates immediately.

Worst case total LLM calls for axis 2, per `generate_suggestions()` call:
`MAX_PARSE_RETRY_ATTEMPTS` passes * (up to 2 Gemini + up to 2 Groq + 1
Cloudflare attempts) — preferred for Chinese/JSON success, but truncated
in practice by `SUGGESTIONS_WALL_CLOCK_S` so Vercel does not emit
FUNCTION_INVOCATION_TIMEOUT (504) before we can return an app-level 503.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .prompts import build_messages
from .parser import (
    parse_model_output,
    is_json_extraction_failure,
    has_non_chinese_reason,
    has_japanese_corner_quotes_in_critique,
    ParsedResponse,
)
from .key_pool import (
    load_cloudflare_credentials,
    load_gemini_credentials,
    load_groq_credentials,
)
from .groq_provider import (
    call_groq_with_rotation,
    get_groq_api_key,
    GroqError,
    GroqRateLimitError,
    GroqServerError,
    GroqTimeoutError,
    GroqJsonValidateError,
)
from .cloudflare_provider import (
    call_cloudflare,
    get_cloudflare_credentials,
    CloudflareError,
)
from .gemini_provider import (
    call_gemini_with_rotation,
    get_gemini_api_key,
    GeminiError,
    GeminiRateLimitError,
    GeminiServerError,
    GeminiTimeoutError,
)

logger = logging.getLogger(__name__)

# Total number of generate+parse passes attempted when the model's response
# either fails to parse as JSON or fails Chinese critique-field checks
# (see parser.is_json_extraction_failure / has_non_chinese_reason /
# has_japanese_corner_quotes_in_critique), before giving up. These
# conditions share this one attempt budget. See module docstring for how
# this composes with each provider's own network-level retry.
MAX_PARSE_RETRY_ATTEMPTS = 4

# Soft stop before Vercel `api/index.py` maxDuration (60s) so we return
# app-level 503 with pool diagnostics instead of opaque FUNCTION_INVOCATION_TIMEOUT.
SUGGESTIONS_WALL_CLOCK_S = 55.0

# Appended on language-check retries only (not JSON-parse failures) so the
# next pass gets an explicit correction signal without changing the base
# prompt for the first attempt.
LANGUAGE_RETRY_NUDGE = (
    "上次输出不合格。请只用简体中文重写全部 reason 与 overallComment。"
    "禁止日语说明文、禁止です/ます。中文引用用英文或中文双引号；日语词形可用「」，"
    "禁止用「」包裹中文说明词。overallComment 先优点再问题；"
    "reason 用自然中文写清问题、推荐改法（如有）与为什么，不要冒号标签口播。"
    "多段时逐段覆盖，勿只写 1–2 条就停。即使原文是中文也必须用中文说明。"
    "只输出完整 JSON，不要其他文字。"
)

# Appended when the previous pass failed JSON extraction (prose / truncated).
PARSE_RETRY_NUDGE = (
    "上次没有返回可解析的 JSON。请只输出一个完整 JSON 对象，"
    '格式为 {"suggestions":[...],"overallComment":"..."}，'
    "不要前言、后记或 Markdown 代码块。reason/overallComment 用简体中文。"
)


class SuggestionsError(Exception):
    """Error generating suggestions from all providers."""
    def __init__(
        self,
        message: str,
        groq_error: Optional[str] = None,
        cf_error: Optional[str] = None,
        gemini_error: Optional[str] = None,
        *,
        rate_limited: bool = False,
        groq_pool_size: int = 0,
        cf_pool_size: int = 0,
        gemini_pool_size: int = 0,
    ):
        super().__init__(message)
        self.groq_error = groq_error
        self.cf_error = cf_error
        self.gemini_error = gemini_error
        self.rate_limited = rate_limited
        self.groq_pool_size = groq_pool_size
        self.cf_pool_size = cf_pool_size
        self.gemini_pool_size = gemini_pool_size


class NoProvidersConfiguredError(SuggestionsError):
    """No LLM providers are configured."""
    pass


def _error_looks_rate_limited(err: Optional[str]) -> bool:
    """True if an error string indicates 429 / cooldown / quota exhaustion."""
    if not err:
        return False
    lower = err.lower()
    needles = (
        "rate limit",
        "cooldown",
        "exhausted",
        "quota",
        "429",
        "http 429",
    )
    return any(n in lower for n in needles)


def are_providers_configured() -> bool:
    """Check if at least one provider is configured."""
    groq_key = get_groq_api_key()
    cf_account, cf_token = get_cloudflare_credentials()
    gemini_key = get_gemini_api_key()
    return bool(groq_key) or (bool(cf_account) and bool(cf_token)) or bool(gemini_key)


def _content_usable(result: ParsedResponse) -> bool:
    """True if result is parseable JSON and passes Chinese critique-field checks."""
    if is_json_extraction_failure(result):
        return False
    if has_non_chinese_reason(result):
        return False
    if has_japanese_corner_quotes_in_critique(result):
        return False
    return True


def _prefer_result(
    primary: Optional[ParsedResponse],
    secondary: ParsedResponse,
) -> ParsedResponse:
    """Prefer a non-parse-failure body when choosing among soft failures."""
    if primary is None:
        return secondary
    if is_json_extraction_failure(secondary) and not is_json_extraction_failure(primary):
        return primary
    return secondary


def _pool_sizes() -> tuple[int, int, int]:
    return (
        len(load_gemini_credentials()),
        len(load_groq_credentials()),
        len(load_cloudflare_credentials()),
    )


def _raise_if_wall_clock_exceeded(
    deadline_monotonic: float,
    *,
    gemini_error: Optional[str] = None,
    groq_error: Optional[str] = None,
    cf_error: Optional[str] = None,
) -> None:
    """Raise SuggestionsError when the soft wall-clock budget is exhausted."""
    if time.monotonic() < deadline_monotonic:
        return
    gemini_pool_size, groq_pool_size, cf_pool_size = _pool_sizes()
    logger.warning(
        "Suggestions wall-clock budget exhausted (limit=%ss); "
        "aborting before platform timeout. gemini_pool_size=%s "
        "groq_pool_size=%s cf_pool_size=%s",
        SUGGESTIONS_WALL_CLOCK_S,
        gemini_pool_size,
        groq_pool_size,
        cf_pool_size,
    )
    raise SuggestionsError(
        f"Suggestions generation exceeded wall-clock budget "
        f"({SUGGESTIONS_WALL_CLOCK_S:.0f}s); aborting before platform timeout",
        groq_error=groq_error,
        cf_error=cf_error,
        gemini_error=gemini_error,
        groq_pool_size=groq_pool_size,
        cf_pool_size=cf_pool_size,
        gemini_pool_size=gemini_pool_size,
    )


async def _generate_suggestions_once(
    messages: list[dict],
    *,
    deadline_monotonic: float,
) -> ParsedResponse:
    """
    Single generate+parse pass: Gemini → Groq → Cloudflare on network
    failure *or* unusable content (same-pass salvage).

    May return a ParsedResponse that is itself a parse failure or still
    non-Chinese — the outer retry loop in `generate_suggestions()` decides
    whether to retry.

    Raises:
        SuggestionsError: If all configured providers fail at the network
            level (no usable HTTP body from any provider), or if the
            wall-clock budget is exhausted.
    """
    groq_error: Optional[str] = None
    cf_error: Optional[str] = None
    gemini_error: Optional[str] = None
    best_soft: Optional[ParsedResponse] = None
    gemini_pool_size, groq_pool_size, cf_pool_size = _pool_sizes()
    logger.info(
        "LLM credential pools: gemini_pool_size=%s groq_pool_size=%s cf_pool_size=%s",
        gemini_pool_size,
        groq_pool_size,
        cf_pool_size,
    )

    gemini_key = get_gemini_api_key()
    if gemini_key:
        _raise_if_wall_clock_exceeded(deadline_monotonic)
        try:
            logger.info("Attempting Gemini inference...")
            raw_output = await call_gemini_with_rotation(messages)
            # Empty/whitespace content is a successful HTTP response but unusable;
            # fall through to Groq instead of burning parse-retry budget.
            if not (raw_output or "").strip():
                logger.warning(
                    "Gemini returned empty content, falling back to Groq"
                )
                gemini_error = "Gemini returned empty content"
            else:
                logger.info(
                    f"Gemini inference successful, raw output length: {len(raw_output)}"
                )
                logger.debug(f"Gemini raw output: {raw_output[:500]}...")
                gemini_result = parse_model_output(raw_output)
                if _content_usable(gemini_result):
                    logger.info(
                        f"Parsed result: {len(gemini_result['suggestions'])} suggestions"
                    )
                    return gemini_result
                reason = (
                    "JSON parse failure"
                    if is_json_extraction_failure(gemini_result)
                    else "non-Chinese reason/overallComment"
                )
                logger.warning(
                    f"Gemini content unusable ({reason}); trying Groq salvage"
                )
                gemini_error = f"Gemini content unusable: {reason}"
                best_soft = gemini_result
        except (
            GeminiRateLimitError,
            GeminiServerError,
            GeminiTimeoutError,
        ) as e:
            logger.warning(
                f"Gemini failed with retriable error, falling back to Groq: {e}"
            )
            gemini_error = str(e)
        except GeminiError as e:
            logger.error(f"Gemini failed with non-retriable error: {e}")
            gemini_error = str(e)
    else:
        logger.info("Gemini not configured, trying Groq directly")
        gemini_error = "Gemini API key not configured"

    groq_key = get_groq_api_key()
    if groq_key:
        _raise_if_wall_clock_exceeded(
            deadline_monotonic,
            gemini_error=gemini_error,
        )
        try:
            logger.info("Attempting Groq inference...")
            raw_output = await call_groq_with_rotation(messages)
            if not (raw_output or "").strip():
                logger.warning(
                    "Groq returned empty content, falling back to Cloudflare"
                )
                groq_error = "Groq returned empty content"
            else:
                logger.info(
                    f"Groq inference successful, raw output length: {len(raw_output)}"
                )
                logger.debug(f"Groq raw output: {raw_output[:500]}...")
                groq_result = parse_model_output(raw_output)
                if _content_usable(groq_result):
                    logger.info(
                        f"Parsed result: {len(groq_result['suggestions'])} suggestions"
                    )
                    return groq_result
                reason = (
                    "JSON parse failure"
                    if is_json_extraction_failure(groq_result)
                    else "non-Chinese reason/overallComment"
                )
                logger.warning(
                    f"Groq content unusable ({reason}); trying Cloudflare salvage"
                )
                groq_error = f"Groq content unusable: {reason}"
                best_soft = _prefer_result(best_soft, groq_result)
        except (
            GroqRateLimitError,
            GroqServerError,
            GroqTimeoutError,
            GroqJsonValidateError,
        ) as e:
            logger.warning(
                f"Groq failed with retriable error, falling back to Cloudflare: {e}"
            )
            groq_error = str(e)
        except GroqError as e:
            logger.error(f"Groq failed with non-retriable error: {e}")
            groq_error = str(e)
    else:
        logger.info("Groq not configured, trying Cloudflare directly")
        groq_error = "Groq API key not configured"

    cf_account, cf_token = get_cloudflare_credentials()
    if cf_account and cf_token:
        _raise_if_wall_clock_exceeded(
            deadline_monotonic,
            gemini_error=gemini_error,
            groq_error=groq_error,
        )
        try:
            logger.info("Attempting Cloudflare Workers AI inference...")
            raw_output = await call_cloudflare(messages)
            logger.info(
                f"Cloudflare inference successful, raw output length: {len(raw_output)}"
            )
            logger.debug(f"Cloudflare raw output: {raw_output[:500]}...")
            cf_result = parse_model_output(raw_output)
            if _content_usable(cf_result):
                logger.info(
                    f"Parsed result: {len(cf_result['suggestions'])} suggestions"
                )
                return cf_result
            logger.warning(
                "Cloudflare content unusable; returning best soft result"
            )
            cf_error = "Cloudflare content unusable"
            return _prefer_result(best_soft, cf_result)
        except CloudflareError as e:
            logger.error(f"Cloudflare failed: {e}")
            cf_error = str(e)
    else:
        cf_error = "Cloudflare credentials not configured"

    if best_soft is not None:
        # Soft bodies from earlier providers: let outer retry nudge language/JSON.
        return best_soft

    rate_limited = (
        _error_looks_rate_limited(gemini_error)
        or _error_looks_rate_limited(groq_error)
        or _error_looks_rate_limited(cf_error)
    )
    message = (
        "All LLM providers rate-limited or quota exhausted"
        if rate_limited
        else "All LLM providers failed"
    )
    raise SuggestionsError(
        message,
        groq_error=groq_error,
        cf_error=cf_error,
        gemini_error=gemini_error,
        rate_limited=rate_limited,
        groq_pool_size=groq_pool_size,
        cf_pool_size=cf_pool_size,
        gemini_pool_size=gemini_pool_size,
    )


async def generate_suggestions(
    original_text: str,
    target_text: str,
    exemplar_translation: Optional[str] = None,
) -> ParsedResponse:
    """
    Generate AI correction suggestions for the given text.

    Tries Gemini first (with in-provider Flash rotation), then Groq,
    then Cloudflare on failure or unusable content. If a pass still fails
    JSON parse or the Chinese-language content check, the whole pass is
    retried up to `MAX_PARSE_RETRY_ATTEMPTS` times before giving up.

    Args:
        original_text: The original Japanese text.
        target_text: The target/translated text to correct.
        exemplar_translation: Optional known-good translation of
            `original_text` used purely as reference calibration. Omitted
            from the prompt entirely when empty/whitespace-only.

    Returns:
        ParsedResponse with suggestions and overall comment. May be the
        parse-failure placeholder response if every attempt failed to
        parse (see `parser.is_json_extraction_failure`), or the
        last-attempted result even if it still fails the Chinese-language
        check (see `parser.has_non_chinese_reason`) — either way this
        degrades gracefully rather than raising.

    Raises:
        NoProvidersConfiguredError: If no providers are configured.
        SuggestionsError: If all providers fail at the network level, or
            the wall-clock budget is exhausted.
    """
    if not are_providers_configured():
        raise NoProvidersConfiguredError(
            "No LLM providers configured. Set GROQ_API_KEY(S), "
            "CLOUDFLARE_ACCOUNT_ID(S) + CLOUDFLARE_API_TOKEN(S), "
            "or GEMINI_API_KEY(S)."
        )

    base_messages = build_messages(original_text, target_text, exemplar_translation)

    last_result: Optional[ParsedResponse] = None
    language_failed_last = False
    parse_failed_last = False
    deadline_monotonic = time.monotonic() + SUGGESTIONS_WALL_CLOCK_S
    for attempt in range(1, MAX_PARSE_RETRY_ATTEMPTS + 1):
        _raise_if_wall_clock_exceeded(deadline_monotonic)
        messages = list(base_messages)
        if language_failed_last:
            messages.append({"role": "user", "content": LANGUAGE_RETRY_NUDGE})
        elif parse_failed_last:
            messages.append({"role": "user", "content": PARSE_RETRY_NUDGE})

        result = await _generate_suggestions_once(
            messages,
            deadline_monotonic=deadline_monotonic,
        )
        if _content_usable(result):
            return result
        parse_failed = is_json_extraction_failure(result)
        language_failed_last = (not parse_failed) and (
            has_non_chinese_reason(result)
            or has_japanese_corner_quotes_in_critique(result)
        )
        parse_failed_last = parse_failed
        if parse_failed:
            reason = "JSON parse failure"
        elif has_japanese_corner_quotes_in_critique(result):
            reason = "Japanese corner quotes in reason/overallComment"
        else:
            reason = "non-Chinese reason/overallComment"

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
