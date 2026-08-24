"""
AI suggestions generation with provider failover.
Private Codex CLI API (primary when configured) -> Gemini -> Groq -> Cloudflare Workers AI.

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
     (`parser.has_japanese_corner_quotes_in_critique`; JP TARGET cites OK); or
   - it parses and explains in Chinese but offers a Chinese word as the
     *corrected form* (`parser.has_non_japanese_recommendation`), which the
     learner cannot write into a Japanese sentence.
   Within a single pass, if Gemini returns either failure mode, this module
   still tries Groq, then Cloudflare, before returning (same-pass salvage),
   so a usable later response can rescue a Japanese/unparseable earlier body
   without burning the outer retry budget. When all providers in a pass still
   fail the content checks, `generate_suggestions()` retries the *entire*
   Gemini→Groq→Cloudflare pass up to `MAX_PARSE_RETRY_ATTEMPTS` times, sharing
   one attempt budget across all of these conditions, before giving up and
   returning the best result as-is. A genuine network-level failure
   (`SuggestionsError`, raised when all providers fail at the HTTP layer even
   after their own retries) is NOT retried by this axis and propagates
   immediately.

   Axis 2 is capped so it cannot turn a readable critique into a failed
   request (`fix-suggestion-retry-budget-hard-failure`). Once any pass has
   produced a body, that body is returned instead of raising when a later pass
   cannot run — whether because the wall-clock budget is gone or because the
   providers stopped answering — and a retry is not even started unless the
   remaining budget still covers a pass as long as the previous one. The
   Chinese-recommended-form check additionally stops after
   `MAX_RECOMMENDATION_RETRIES` passes, since that body is parseable Chinese
   critique whose remaining flaw does not justify more latency and free-tier
   requests. Before this cap, a model that kept recommending Chinese forms —
   exactly the behaviour the check exists to catch — spent four passes and then
   surfaced 503 "All cloud providers failed" for a critique the user could have
   read after the first pass.

The returned body also carries `llmProvider` / `llmModel` for the winning
provider and its exact model id, since Gemini and Groq rotate models per
request (`editable-prompt-model-log-and-critique-fix`).

Worst case total LLM calls for axis 2, per `generate_suggestions()` call:
`MAX_PARSE_RETRY_ATTEMPTS` passes * (up to 2 Gemini + up to 2 Groq + 1
Cloudflare attempts) — preferred for Chinese/JSON success, but truncated
in practice by `SUGGESTIONS_WALL_CLOCK_S` so Vercel does not emit
FUNCTION_INVOCATION_TIMEOUT (504) before we can return an app-level 503.
The second in-provider model attempt is also skipped when the remaining budget
would not leave the next provider room to answer, so a slow primary cannot
deny a fast, fresh secondary its turn.

Every provider call is sized to the budget that is actually left rather than to
its own static timeout (`budget.resolve_call_timeout`), and a provider whose
remaining slice is shorter than its measured latency is skipped outright with a
`timed_out` diagnostic. Without that sizing the budget bounded only *when* a
call could start, not when it could finish: two Gemini timeouts (44s) followed
by one Groq timeout (25s) passed every check here and still ran 69s into
Vercel's 60s limit, which is the FUNCTION_INVOCATION_TIMEOUT this module now
cannot produce (`fix-function-invocation-timeout`).
"""

from __future__ import annotations

import logging
import time
from typing import NamedTuple, Optional

from .budget import (
    PLATFORM_MAX_DURATION_S,
    PLATFORM_RESERVE_S,
    describe_skip,
    resolve_call_timeout,
    seconds_left,
)
from .prompts import build_messages
from .parser import (
    parse_model_output,
    is_json_extraction_failure,
    has_non_chinese_reason,
    has_japanese_corner_quotes_in_critique,
    has_non_japanese_recommendation,
    ParsedResponse,
)
from .provider_output import ProviderOutput
from .local_fastpath import try_local_fastpath
from .key_pool import (
    load_cloudflare_credentials,
    load_gemini_credentials,
    load_groq_credentials,
)
from .groq_provider import (
    call_groq_with_rotation,
    get_groq_api_key,
    get_groq_model,
    groq_availability,
    release_groq_cooldown,
    GROQ_MIN_SLICE_S,
    GROQ_TIMEOUT,
    GroqError,
    GroqRateLimitError,
    GroqServerError,
    GroqTimeoutError,
    GroqJsonValidateError,
)
from .cloudflare_provider import (
    call_cloudflare,
    cloudflare_availability,
    get_cloudflare_credentials,
    release_cloudflare_cooldown,
    CloudflareError,
    CF_MIN_SLICE_S,
    CF_MODEL,
    CF_TIMEOUT,
)
from .gemini_provider import (
    call_gemini_with_rotation,
    gemini_availability,
    get_gemini_api_key,
    get_gemini_model,
    release_gemini_cooldown,
    GEMINI_MIN_SLICE_S,
    GEMINI_TIMEOUT,
    GeminiError,
    GeminiRateLimitError,
    GeminiServerError,
    GeminiTimeoutError,
)
from .codexcli_provider import (
    call_codexcli,
    get_codexcli_model,
    is_codexcli_configured,
    CODEXCLI_MIN_SLICE_S,
    CODEXCLI_TIMEOUT,
    CodexCLIError,
)

logger = logging.getLogger(__name__)

# Total number of generate+parse passes attempted when the model's response
# either fails to parse as JSON or fails a critique-field content check
# (see parser.is_json_extraction_failure / has_non_chinese_reason /
# has_japanese_corner_quotes_in_critique /
# has_non_japanese_recommendation), before giving up. These
# conditions share this one attempt budget. See module docstring for how
# this composes with each provider's own network-level retry.
MAX_PARSE_RETRY_ATTEMPTS = 4

# Passes spent on a Chinese-recommended-form body before accepting it
# (`fix-suggestion-retry-budget-hard-failure`). Unlike an unparseable or
# Japanese-explanation body, this one is readable critique that merely quoted a
# Chinese form, so the whole retry budget is not worth burning on it: each extra
# pass costs seconds of the caller's wall clock and one free-tier request per
# provider, and the models that do this tend to keep doing it.
MAX_RECOMMENDATION_RETRIES = 1

# Soft stop before Vercel `api/index.py` maxDuration (60s) so we return
# app-level 503 with pool diagnostics instead of opaque FUNCTION_INVOCATION_TIMEOUT.
#
#
# Derived from the platform limit rather than hand-picked: the limit covers the
# whole invocation while this budget only covers what the handler measures, so
# the reserve is what makes "obeyed the budget" imply "was not killed at 60s".
# The previous hand-picked 55s left 5s for cold start and transfer, and a
# request that obeyed it exactly could still return an opaque 504
# (`fix-function-invocation-timeout`). The reserve only ever costs time in
# already-degraded requests: a healthy pass is Gemini (~7-16s) plus at most one
# fast secondary.
SUGGESTIONS_WALL_CLOCK_S = PLATFORM_MAX_DURATION_S - PLATFORM_RESERVE_S

# Fraction of the previous pass's duration that must still fit in the budget
# before another content retry is started, so a pass is not begun only to be
# aborted mid-flight (which used to discard an already-usable earlier body).
RETRY_BUDGET_MARGIN = 1.1

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

# Appended when the previous pass offered Chinese words as the corrected form
# (parser.has_non_japanese_recommendation) — the learner cannot use those.
RECOMMENDATION_RETRY_NUDGE = (
    "上次输出把中文词当成了修正后的形（例如 改为“理论上”），这是不合格的："
    "添削対象是日语，推荐形必须用日语写出（可用「」），中文只用于解释。"
    "另外只添削「添削対象」，不要改写原文；可互换的近义替换不算错误；"
    "推荐形要代入原句确认语法与搭配自然。请据此重写全部 reason。"
    "只输出完整 JSON，不要其他文字。"
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
        timed_out: bool = False,
        groq_pool_size: int = 0,
        cf_pool_size: int = 0,
        gemini_pool_size: int = 0,
        codex_error: Optional[str] = None,
    ):
        super().__init__(message)
        self.groq_error = groq_error
        self.cf_error = cf_error
        self.gemini_error = gemini_error
        self.codex_error = codex_error
        self.rate_limited = rate_limited
        # Distinguishes "ran out of wall-clock budget" from "every provider
        # refused", which need different advice (retry vs check keys/quota).
        self.timed_out = timed_out
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
    return (
        bool(groq_key)
        or (bool(cf_account) and bool(cf_token))
        or bool(gemini_key)
        or is_codexcli_configured()
    )


def _content_usable(result: ParsedResponse) -> bool:
    """True if result parses and passes the critique-field content checks."""
    if is_json_extraction_failure(result):
        return False
    if has_non_chinese_reason(result):
        return False
    if has_japanese_corner_quotes_in_critique(result):
        return False
    if has_non_japanese_recommendation(result):
        return False
    return True


class GenerationOutcome(NamedTuple):
    """A parsed body plus which provider/model produced it (None if unknown)."""

    result: ParsedResponse
    provider: Optional[str] = None
    model: Optional[str] = None


def _text_and_model(
    output: "ProviderOutput | str",
    fallback_model: str,
) -> tuple[str, str]:
    """
    Normalize a provider call result to (text, model).

    Rotating providers return ProviderOutput so the model that actually
    answered is known. Cloudflare has a single fixed model and returns plain
    text, in which case the caller's configured/default model id is used.
    """
    if isinstance(output, ProviderOutput):
        return output.text, output.model
    return str(output), fallback_model


def _prefer_outcome(
    primary: Optional[GenerationOutcome],
    secondary: GenerationOutcome,
) -> GenerationOutcome:
    """Prefer a non-parse-failure body when choosing among soft failures."""
    if primary is None:
        return secondary
    if is_json_extraction_failure(secondary.result) and not is_json_extraction_failure(
        primary.result
    ):
        return primary
    return secondary


def _pool_sizes() -> tuple[int, int, int]:
    return (
        len(load_gemini_credentials()),
        len(load_groq_credentials()),
        len(load_cloudflare_credentials()),
    )


CHAIN_ORDER = ("gemini", "groq", "cloudflare")

# Preference order encodes critique quality, so it is fixed. Availability decides
# which providers are *in* the chain, never in what order they are preferred: a
# provider is not promoted for being faster, because that would trade output
# quality for latency without anyone asking (see design.md — Non-Goals).
_AVAILABILITY_CHECKS = {
    "gemini": gemini_availability,
    "groq": groq_availability,
    "cloudflare": cloudflare_availability,
}
_COOLDOWN_RELEASES = {
    "gemini": release_gemini_cooldown,
    "groq": release_groq_cooldown,
    "cloudflare": release_cloudflare_cooldown,
}
_PROVIDER_LABELS = {
    "gemini": "Gemini",
    "groq": "Groq",
    "cloudflare": "Cloudflare",
}


class _ProviderPlan(NamedTuple):
    """Whether this provider is worth calling in this pass, and why not."""

    configured: bool
    # Set when every credential is already in cooldown, so calling would only
    # collect the same refusal again.
    unavailable_reason: Optional[str]

    @property
    def usable(self) -> bool:
        return self.configured and self.unavailable_reason is None


def _describe_unavailable(provider: str, availability) -> str:
    """Ops-facing reason a provider was skipped without being called."""
    label = _PROVIDER_LABELS.get(provider, provider)
    when = (
        f"expected usable in {availability.recover_in_s:.0f}s"
        if availability.recover_in_s is not None
        else "recovery time unknown"
    )
    if availability.carried_over:
        # Worth saying explicitly: this request never called the provider, so its
        # absence from the logs is expected rather than a missing attempt.
        return (
            f"{label} skipped: every credential was already in cooldown from an "
            f"earlier request, {when}"
        )
    return f"{label} skipped: every credential is in cooldown, {when}"


def _plan_providers() -> dict[str, _ProviderPlan]:
    """
    Decide which providers this pass will actually call.

    A provider whose whole pool is in cooldown is skipped rather than called for
    the refusal we already have. The exception is the last resort: if that would
    leave nothing to call, the cooldown closest to expiring is released so one
    real attempt still happens. Recorded availability describes the past and can
    be stale, so it must never be the only reason no provider was tried —
    otherwise our own cache, not the provider, takes the feature offline.
    """
    availability = {name: check() for name, check in _AVAILABILITY_CHECKS.items()}
    plans = {
        name: _ProviderPlan(
            configured=state.configured,
            unavailable_reason=(
                _describe_unavailable(name, state) if state.all_cooled else None
            ),
        )
        for name, state in availability.items()
    }
    if any(plan.usable for plan in plans.values()):
        return plans

    cooled = [
        name
        for name in CHAIN_ORDER
        if availability[name].configured and availability[name].all_cooled
    ]
    if not cooled:
        return plans
    soonest = min(cooled, key=lambda n: availability[n].recover_in_s or float("inf"))
    if _COOLDOWN_RELEASES[soonest]() is None:
        return plans
    logger.info(
        "Every provider is in cooldown; attempting %s anyway (recovers soonest)",
        soonest,
    )
    plans[soonest] = _ProviderPlan(configured=True, unavailable_reason=None)
    return plans


def _later_provider_reserve(
    *,
    after: str,
    plan: Optional[dict[str, _ProviderPlan]] = None,
) -> float:
    """
    Seconds the providers *after* `after` need to each get a turn.

    Only their minimum useful slice is held back, not their full timeout: the
    point is that a slow primary cannot starve a fast secondary (Groq answers in
    1-3s), not that every provider is guaranteed its maximum.

    A provider that will be skipped holds back nothing — reserving for a call
    that is not going to happen would shrink the slice of the provider that is.
    """

    def will_be_called(name: str, configured: bool) -> bool:
        if plan is None:
            return configured
        return plan[name].usable

    reserve = 0.0
    if after == "gemini" and will_be_called("groq", bool(get_groq_api_key())):
        reserve += GROQ_MIN_SLICE_S
    if after in ("gemini", "groq"):
        cf_account, cf_token = get_cloudflare_credentials()
        if will_be_called("cloudflare", bool(cf_account and cf_token)):
            reserve += CF_MIN_SLICE_S
    return reserve


def _phase_deadline(
    deadline_monotonic: Optional[float],
    *,
    after: str,
    plan: Optional[dict[str, _ProviderPlan]] = None,
) -> Optional[float]:
    """
    Deadline for one provider's phase of the chain.

    Short of the request deadline by `_later_provider_reserve()`, so every
    attempt inside the phase — first model, sibling model, each pooled key — is
    clamped by `budget.resolve_call_timeout` to time that is genuinely this
    provider's to spend. Holding the reserve here rather than predicting it
    up-front is what makes the guarantee hold: the decision is re-taken against
    the clock before each attempt, so a first attempt that overran cannot leave
    the chain committed to a call the budget can no longer cover.
    """
    if deadline_monotonic is None:
        return None
    return deadline_monotonic - _later_provider_reserve(after=after, plan=plan)


class _PhaseBudget(NamedTuple):
    """What one provider may spend, and whether the budget pinched it."""

    deadline: Optional[float]
    # None means "skip this provider": too little time left to be worth calling.
    call_timeout: Optional[float]
    # Skipped, or granted less than its own timeout. Either way the request was
    # time-constrained, which is different advice for the user than bad keys.
    constrained: bool


def _phase_budget(
    deadline_monotonic: Optional[float],
    *,
    after: str,
    provider_timeout: float,
    min_slice: float,
    plan: Optional[dict[str, _ProviderPlan]] = None,
) -> _PhaseBudget:
    """Resolve one provider's share of the request budget."""
    deadline = _phase_deadline(deadline_monotonic, after=after, plan=plan)
    call_timeout = resolve_call_timeout(deadline, provider_timeout, min_slice)
    return _PhaseBudget(
        deadline=deadline,
        call_timeout=call_timeout,
        constrained=call_timeout is None or call_timeout < provider_timeout,
    )


def _can_afford_another_pass(
    deadline_monotonic: Optional[float],
    last_pass_seconds: float,
) -> bool:
    """
    True if the wall-clock budget still covers a pass like the previous one.

    Measured rather than assumed: provider latency varies with prompt and model,
    and the cost of guessing wrong is a pass that gets aborted partway and takes
    the earlier body down with it.
    """
    remaining = seconds_left(deadline_monotonic)
    return remaining >= max(last_pass_seconds, 0.0) * RETRY_BUDGET_MARGIN


def _unusable_reason(result: ParsedResponse) -> str:
    """Short description of why `_content_usable()` rejected a body."""
    if is_json_extraction_failure(result):
        return "JSON parse failure"
    if has_japanese_corner_quotes_in_critique(result):
        return "Japanese corner quotes in reason/overallComment"
    if has_non_japanese_recommendation(result):
        return "Chinese recommended form in reason"
    return "non-Chinese reason/overallComment"


async def _generate_suggestions_once(
    messages: list[dict],
    *,
    codex_model: Optional[str] = None,
    deadline_monotonic: Optional[float],
) -> GenerationOutcome:
    """
    Single generate+parse pass: Codex CLI → Gemini → Groq → Cloudflare on network
    failure *or* unusable content (same-pass salvage).

    May return an outcome whose body is itself a parse failure or still fails
    a content check — the outer retry loop in `generate_suggestions()` decides
    whether to retry. The outcome also carries the provider and model that
    produced the body, so a critique can be attributed to a specific model.

    Raises:
        SuggestionsError: If all configured providers fail at the network
            level (no usable HTTP body from any provider), or if the
            wall-clock budget is exhausted.
    """
    groq_error: Optional[str] = None
    cf_error: Optional[str] = None
    gemini_error: Optional[str] = None
    codex_error: Optional[str] = None
    best_soft: Optional[GenerationOutcome] = None
    budget_constrained = False
    gemini_pool_size, groq_pool_size, cf_pool_size = _pool_sizes()
    logger.info(
        "LLM credential pools: gemini_pool_size=%s groq_pool_size=%s cf_pool_size=%s",
        gemini_pool_size,
        groq_pool_size,
        cf_pool_size,
    )

    # The private host is the preferred provider when configured. It is kept
    # opt-in so existing Vercel deployments retain the old cloud-only chain.
    if is_codexcli_configured():
        try:
            logger.info("Attempting private Codex CLI API inference first...")
            codex_output = await call_codexcli(
                messages,
                model=codex_model,
                deadline_monotonic=deadline_monotonic,
            )
            raw_output, codex_model = _text_and_model(
                codex_output, get_codexcli_model()
            )
            codex_result = parse_model_output(raw_output)
            codex_outcome = GenerationOutcome(codex_result, "codex-cli", codex_model)
            if _content_usable(codex_result):
                return codex_outcome
            codex_error = f"Codex CLI API content unusable: {_unusable_reason(codex_result)}"
            best_soft = codex_outcome
            logger.warning(codex_error)
        except CodexCLIError as e:
            codex_error = str(e)
            if "insufficient request time" in codex_error:
                budget_constrained = True
            logger.warning("Codex CLI API failed; falling back to cloud providers: %s", e)

    plan = _plan_providers()
    gemini_budget = _phase_budget(
        deadline_monotonic,
        after="gemini",
        provider_timeout=GEMINI_TIMEOUT,
        min_slice=GEMINI_MIN_SLICE_S,
        plan=plan,
    )
    if not plan["gemini"].configured:
        logger.info("Gemini not configured, trying Groq directly")
        gemini_error = "Gemini API key not configured"
    elif plan["gemini"].unavailable_reason:
        gemini_error = plan["gemini"].unavailable_reason
        logger.info(gemini_error)
    elif gemini_budget.call_timeout is None:
        # Skipped rather than started-and-clamped: a call shorter than the
        # model's own latency would time out and spend seconds Groq still needs.
        gemini_error = describe_skip(
            "Gemini", gemini_budget.deadline, GEMINI_MIN_SLICE_S
        )
        budget_constrained = True
        logger.warning(gemini_error)
    else:
        budget_constrained = budget_constrained or gemini_budget.constrained
        try:
            logger.info("Attempting Gemini inference...")
            raw_output, gemini_model = _text_and_model(
                await call_gemini_with_rotation(
                    messages,
                    deadline_monotonic=gemini_budget.deadline,
                ),
                get_gemini_model(),
            )
            # Empty/whitespace content is a successful HTTP response but unusable;
            # fall through to Groq instead of burning parse-retry budget.
            if not (raw_output or "").strip():
                logger.warning(
                    "Gemini returned empty content, falling back to Groq"
                )
                gemini_error = "Gemini returned empty content"
            else:
                logger.info(
                    f"Gemini inference successful (model={gemini_model}), "
                    f"raw output length: {len(raw_output)}"
                )
                logger.debug(f"Gemini raw output: {raw_output[:500]}...")
                gemini_result = parse_model_output(raw_output)
                gemini_outcome = GenerationOutcome(
                    gemini_result, "gemini", gemini_model
                )
                if _content_usable(gemini_result):
                    logger.info(
                        f"Parsed result: {len(gemini_result['suggestions'])} suggestions"
                    )
                    return gemini_outcome
                reason = _unusable_reason(gemini_result)
                logger.warning(
                    f"Gemini content unusable ({reason}); trying Groq salvage"
                )
                gemini_error = f"Gemini content unusable: {reason}"
                best_soft = gemini_outcome
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

    groq_budget = _phase_budget(
        deadline_monotonic,
        after="groq",
        provider_timeout=GROQ_TIMEOUT,
        min_slice=GROQ_MIN_SLICE_S,
        plan=plan,
    )
    if not plan["groq"].configured:
        logger.info("Groq not configured, trying Cloudflare directly")
        groq_error = "Groq API key not configured"
    elif plan["groq"].unavailable_reason:
        groq_error = plan["groq"].unavailable_reason
        logger.info(groq_error)
    elif groq_budget.call_timeout is None:
        groq_error = describe_skip("Groq", groq_budget.deadline, GROQ_MIN_SLICE_S)
        budget_constrained = True
        logger.warning(groq_error)
        if best_soft is not None:
            # Nothing later in the chain can fit either, so stop here with the
            # body already in hand rather than walking to the final raise.
            return best_soft
    else:
        budget_constrained = budget_constrained or groq_budget.constrained
        try:
            logger.info("Attempting Groq inference...")
            raw_output, groq_model = _text_and_model(
                await call_groq_with_rotation(
                    messages,
                    deadline_monotonic=groq_budget.deadline,
                ),
                get_groq_model(),
            )
            if not (raw_output or "").strip():
                logger.warning(
                    "Groq returned empty content, falling back to Cloudflare"
                )
                groq_error = "Groq returned empty content"
            else:
                logger.info(
                    f"Groq inference successful (model={groq_model}), "
                    f"raw output length: {len(raw_output)}"
                )
                logger.debug(f"Groq raw output: {raw_output[:500]}...")
                groq_result = parse_model_output(raw_output)
                groq_outcome = GenerationOutcome(groq_result, "groq", groq_model)
                if _content_usable(groq_result):
                    logger.info(
                        f"Parsed result: {len(groq_result['suggestions'])} suggestions"
                    )
                    return groq_outcome
                reason = _unusable_reason(groq_result)
                logger.warning(
                    f"Groq content unusable ({reason}); trying Cloudflare salvage"
                )
                groq_error = f"Groq content unusable: {reason}"
                best_soft = _prefer_outcome(best_soft, groq_outcome)
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

    # Last in the chain, so its phase is the whole remaining request budget.
    cf_budget = _phase_budget(
        deadline_monotonic,
        after="cloudflare",
        provider_timeout=CF_TIMEOUT,
        min_slice=CF_MIN_SLICE_S,
        plan=plan,
    )
    if not plan["cloudflare"].configured:
        cf_error = "Cloudflare credentials not configured"
    elif plan["cloudflare"].unavailable_reason:
        cf_error = plan["cloudflare"].unavailable_reason
        logger.info(cf_error)
    elif cf_budget.call_timeout is None:
        cf_error = describe_skip("Cloudflare", cf_budget.deadline, CF_MIN_SLICE_S)
        budget_constrained = True
        logger.warning(cf_error)
    else:
        budget_constrained = budget_constrained or cf_budget.constrained
        try:
            logger.info("Attempting Cloudflare Workers AI inference...")
            raw_output = await call_cloudflare(
                messages, deadline_monotonic=cf_budget.deadline
            )
            logger.info(
                f"Cloudflare inference successful, raw output length: {len(raw_output)}"
            )
            logger.debug(f"Cloudflare raw output: {raw_output[:500]}...")
            cf_result = parse_model_output(raw_output)
            cf_outcome = GenerationOutcome(cf_result, "cloudflare", CF_MODEL)
            if _content_usable(cf_result):
                logger.info(
                    f"Parsed result: {len(cf_result['suggestions'])} suggestions"
                )
                return cf_outcome
            logger.warning(
                "Cloudflare content unusable; returning best soft result"
            )
            cf_error = "Cloudflare content unusable"
            return _prefer_outcome(best_soft, cf_outcome)
        except CloudflareError as e:
            logger.error(f"Cloudflare failed: {e}")
            cf_error = str(e)

    if best_soft is not None:
        # Soft bodies from earlier providers: let outer retry nudge language/JSON.
        return best_soft

    rate_limited = (
        _error_looks_rate_limited(gemini_error)
        or _error_looks_rate_limited(groq_error)
        or _error_looks_rate_limited(cf_error)
    )
    if rate_limited:
        message = "All LLM providers rate-limited or quota exhausted"
    elif budget_constrained:
        message = (
            f"Suggestions generation ran out of its "
            f"{SUGGESTIONS_WALL_CLOCK_S:.0f}s wall-clock budget before a "
            f"provider answered"
        )
        logger.warning(
            "%s. gemini_pool_size=%s groq_pool_size=%s cf_pool_size=%s",
            message,
            gemini_pool_size,
            groq_pool_size,
            cf_pool_size,
        )
    else:
        message = "All LLM providers failed"
    raise SuggestionsError(
        message,
        groq_error=groq_error,
        cf_error=cf_error,
        gemini_error=gemini_error,
        codex_error=codex_error,
        rate_limited=rate_limited,
        # Both can be true — a rate-limited primary that also ate the budget.
        # The flags are reported as facts; the client picks which advice leads.
        timed_out=budget_constrained,
        groq_pool_size=groq_pool_size,
        cf_pool_size=cf_pool_size,
        gemini_pool_size=gemini_pool_size,
    )


def _with_provenance(outcome: GenerationOutcome) -> dict:
    """Response body: parsed fields plus which provider/model produced them."""
    logger.info(
        "Suggestions produced by provider=%s model=%s (%s suggestions)",
        outcome.provider,
        outcome.model,
        len(outcome.result["suggestions"]),
    )
    return {
        **outcome.result,
        "llmProvider": outcome.provider,
        "llmModel": outcome.model,
    }


async def generate_suggestions(
    original_text: str,
    target_text: str,
    exemplar_translation: Optional[str] = None,
    system_prompt_override: Optional[str] = None,
    codex_model: Optional[str] = None,
    deadline_monotonic: Optional[float] = None,
) -> dict:
    """
    Generate AI correction suggestions for the given text.

    Tries Gemini first (with in-provider Flash rotation), then Groq,
    then Cloudflare on failure or unusable content. If a pass still fails
    JSON parse or a critique-field content check, the whole pass is
    retried up to `MAX_PARSE_RETRY_ATTEMPTS` times before giving up.

    Args:
        original_text: The original Japanese text.
        target_text: The target/translated text to correct.
        exemplar_translation: Optional known-good translation of
            `original_text` used purely as reference calibration. Omitted
            from the prompt entirely when empty/whitespace-only.
        system_prompt_override: Optional stored custom rules body replacing
            `prompts.SYSTEM_PROMPT_BODY`. The output contract is appended by
            `build_system_prompt()` either way, so an override cannot break
            the JSON response shape.
        deadline_monotonic: Monotonic instant by which this call must return.
            Callers serving an HTTP request should pass a deadline measured
            from when the request arrived, so work done before generation
            (auth, the stored-prompt lookup) counts against the same platform
            limit. Defaults to SUGGESTIONS_WALL_CLOCK_S from now.

    Returns:
        The parsed suggestions and overall comment, plus `llmProvider` and
        `llmModel` naming the model that produced them. May be the
        parse-failure placeholder response if every attempt failed to
        parse (see `parser.is_json_extraction_failure`), or a result that
        still fails a content check (see `parser.has_non_chinese_reason`) —
        either way this degrades gracefully rather than raising.

    Raises:
        NoProvidersConfiguredError: If no providers are configured.
        SuggestionsError: If no pass produced any body at all — every
            provider failed at the network level, or the wall-clock budget
            ran out before one answered. Once a body exists it is returned
            instead, even if it fails a content check.
    """
    fast_result = try_local_fastpath(original_text, target_text)
    if fast_result is not None:
        logger.info("Using local fast path for an unambiguous short typo")
        return fast_result

    if not are_providers_configured():
        raise NoProvidersConfiguredError(
            "No LLM providers configured. Set CODEXCLI_API_URL + CODEXCLI_API_TOKEN, GROQ_API_KEY(S), "
            "CLOUDFLARE_ACCOUNT_ID(S) + CLOUDFLARE_API_TOKEN(S), "
            "or GEMINI_API_KEY(S)."
        )

    base_messages = build_messages(
        original_text,
        target_text,
        exemplar_translation,
        system_prompt_override,
    )

    best_outcome: Optional[GenerationOutcome] = None
    language_failed_last = False
    parse_failed_last = False
    recommendation_failed_last = False
    recommendation_failures = 0
    last_pass_seconds = 0.0
    if deadline_monotonic is None:
        deadline_monotonic = time.monotonic() + SUGGESTIONS_WALL_CLOCK_S
    for attempt in range(1, MAX_PARSE_RETRY_ATTEMPTS + 1):
        if attempt > 1 and not _can_afford_another_pass(
            deadline_monotonic, last_pass_seconds
        ):
            logger.warning(
                "Skipping content retry %s/%s: %.1fs left is under the %.1fs the "
                "previous pass took; returning the best body already generated",
                attempt,
                MAX_PARSE_RETRY_ATTEMPTS,
                seconds_left(deadline_monotonic),
                last_pass_seconds,
            )
            break
        messages = list(base_messages)
        if language_failed_last:
            messages.append({"role": "user", "content": LANGUAGE_RETRY_NUDGE})
        elif parse_failed_last:
            messages.append({"role": "user", "content": PARSE_RETRY_NUDGE})
        elif recommendation_failed_last:
            messages.append(
                {"role": "user", "content": RECOMMENDATION_RETRY_NUDGE}
            )

        pass_started = time.monotonic()
        try:
            outcome = await _generate_suggestions_once(
                messages,
                codex_model=codex_model,
                deadline_monotonic=deadline_monotonic,
            )
        except SuggestionsError:
            # A body already in hand beats a 503: the earlier pass failed only a
            # content check, which the caller can still read and act on.
            if best_outcome is None:
                raise
            logger.warning(
                "Content retry %s/%s aborted (providers failed or budget "
                "exhausted); returning the best body already generated",
                attempt,
                MAX_PARSE_RETRY_ATTEMPTS,
            )
            break
        last_pass_seconds = time.monotonic() - pass_started
        result = outcome.result
        if _content_usable(result):
            return _with_provenance(outcome)
        parse_failed = is_json_extraction_failure(result)
        language_failed_last = (not parse_failed) and (
            has_non_chinese_reason(result)
            or has_japanese_corner_quotes_in_critique(result)
        )
        parse_failed_last = parse_failed
        recommendation_failed_last = (
            (not parse_failed)
            and (not language_failed_last)
            and has_non_japanese_recommendation(result)
        )
        reason = _unusable_reason(result)
        best_outcome = _prefer_outcome(best_outcome, outcome)

        if recommendation_failed_last:
            recommendation_failures += 1
            if recommendation_failures > MAX_RECOMMENDATION_RETRIES:
                # The body is parseable Chinese critique that merely quoted a
                # Chinese form somewhere; further passes cost the user latency
                # and provider quota for a body they can already read.
                logger.warning(
                    "%s persisted across %s pass(es); accepting the body instead "
                    "of spending the remaining retry budget on it",
                    reason,
                    recommendation_failures,
                )
                break

        logger.warning(
            f"{reason} on attempt {attempt}/{MAX_PARSE_RETRY_ATTEMPTS}; "
            f"{'retrying' if attempt < MAX_PARSE_RETRY_ATTEMPTS else 'giving up'}"
        )

    # Attempts stopped without a clean body — return the best one rather than
    # raising, matching the pre-existing "degrade gracefully" behavior of
    # surfacing a best-effort/placeholder response rather than a 503.
    assert best_outcome is not None  # loop runs at least once (MAX_PARSE_RETRY_ATTEMPTS >= 1)
    return _with_provenance(best_outcome)
