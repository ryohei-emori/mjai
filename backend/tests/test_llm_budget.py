"""
Tests for the wall-clock budget that keeps a request inside Vercel's function
limit (`backend/app/llm/budget.py`).

These cover the invariant whose absence produced FUNCTION_INVOCATION_TIMEOUT in
production: the old budget bounded only *when* a provider call could start, so a
25s Groq call begun at t=44s passed every check and still ran to t=69s past a
60s limit. The assertions below are therefore about elapsed time and granted
timeouts, not just about which branch was taken.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.llm.budget import (
    PLATFORM_MAX_DURATION_S,
    PLATFORM_RESERVE_S,
    RESPONSE_OVERHEAD_S,
    describe_skip,
    resolve_call_timeout,
    seconds_left,
)
from app.llm.cloudflare_provider import CF_MIN_SLICE_S, CF_TIMEOUT
from app.llm.gemini_provider import (
    GEMINI_MIN_SLICE_S,
    GEMINI_TIMEOUT,
    GeminiTimeoutError,
)
from app.llm.groq_provider import GROQ_MIN_SLICE_S, GROQ_TIMEOUT
from app.llm.suggestions import SUGGESTIONS_WALL_CLOCK_S, generate_suggestions

from test_llm_suggestions import VALID_LLM_RESPONSE, FakeClock


class TestPlatformLimitAgreement:
    """The budget is only safe if it still matches the deployed limit."""

    def test_platform_max_duration_matches_vercel_json(self):
        vercel = json.loads(
            (Path(__file__).resolve().parents[2] / "vercel.json").read_text()
        )
        configured = vercel["functions"]["api/index.py"]["maxDuration"]
        assert float(configured) == PLATFORM_MAX_DURATION_S

    def test_request_budget_leaves_room_for_cold_start(self):
        assert (
            SUGGESTIONS_WALL_CLOCK_S + PLATFORM_RESERVE_S == PLATFORM_MAX_DURATION_S
        )
        assert SUGGESTIONS_WALL_CLOCK_S < PLATFORM_MAX_DURATION_S

    def test_every_provider_can_answer_inside_a_full_budget(self):
        for timeout in (GEMINI_TIMEOUT, GROQ_TIMEOUT, CF_TIMEOUT):
            assert timeout + RESPONSE_OVERHEAD_S < SUGGESTIONS_WALL_CLOCK_S

    def test_min_slices_are_below_their_own_timeouts(self):
        assert GEMINI_MIN_SLICE_S <= GEMINI_TIMEOUT
        assert GROQ_MIN_SLICE_S <= GROQ_TIMEOUT
        assert CF_MIN_SLICE_S <= CF_TIMEOUT


class TestResolveCallTimeout:
    def test_full_budget_grants_the_providers_own_timeout(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            deadline = clock() + SUGGESTIONS_WALL_CLOCK_S
            assert (
                resolve_call_timeout(deadline, GROQ_TIMEOUT, GROQ_MIN_SLICE_S)
                == GROQ_TIMEOUT
            )

    def test_short_budget_clamps_the_call_to_what_is_left(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            deadline = clock() + 12.0
            granted = resolve_call_timeout(deadline, GROQ_TIMEOUT, GROQ_MIN_SLICE_S)
        assert granted == pytest.approx(12.0 - RESPONSE_OVERHEAD_S)
        assert granted < GROQ_TIMEOUT

    def test_call_can_never_be_granted_more_than_remains(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            for remaining in (6.0, 10.0, 20.0, 40.0, SUGGESTIONS_WALL_CLOCK_S):
                deadline = clock() + remaining
                granted = resolve_call_timeout(deadline, CF_TIMEOUT, CF_MIN_SLICE_S)
                if granted is not None:
                    assert granted <= remaining

    def test_slice_shorter_than_the_provider_needs_is_no_call_at_all(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            deadline = clock() + GEMINI_MIN_SLICE_S  # minus overhead => too short
            assert (
                resolve_call_timeout(deadline, GEMINI_TIMEOUT, GEMINI_MIN_SLICE_S)
                is None
            )

    def test_passed_deadline_is_no_call_at_all(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            assert (
                resolve_call_timeout(clock() - 1.0, GROQ_TIMEOUT, GROQ_MIN_SLICE_S)
                is None
            )

    def test_no_deadline_means_unbounded(self):
        assert seconds_left(None) == float("inf")
        assert resolve_call_timeout(None, GROQ_TIMEOUT, GROQ_MIN_SLICE_S) == GROQ_TIMEOUT

    def test_skip_reason_names_the_provider_and_what_was_left(self):
        clock = FakeClock()
        with patch("time.monotonic", clock):
            reason = describe_skip("Gemini", clock() + 2.0, GEMINI_MIN_SLICE_S)
        assert "Gemini" in reason
        assert "2.0s" in reason


@pytest.mark.asyncio
class TestProviderCallsCannotOutliveTheDeadline:
    """The clamp has to reach the HTTP layer, not just the chain's branching."""

    async def test_gemini_attempt_is_sized_to_the_remaining_budget(self):
        from app.llm import gemini_provider

        clock = FakeClock()
        granted: list[float] = []

        async def capture(api_key, messages, model, timeout):
            granted.append(timeout)
            return VALID_LLM_RESPONSE

        with patch.dict("os.environ", {"GEMINI_API_KEY": "gem-key"}, clear=True):
            with patch.object(gemini_provider, "_call_gemini_once", new=capture):
                with patch("time.monotonic", clock):
                    await gemini_provider.call_gemini(
                        [{"role": "user", "content": "x"}],
                        model="gemini-3.7-flash",
                        deadline_monotonic=clock() + 15.0,
                    )

        assert granted == [pytest.approx(15.0 - RESPONSE_OVERHEAD_S)]

    async def test_gemini_refuses_a_call_that_cannot_fit(self):
        from app.llm import gemini_provider

        clock = FakeClock()
        with patch.dict("os.environ", {"GEMINI_API_KEY": "gem-key"}, clear=True):
            with patch.object(
                gemini_provider, "_call_gemini_once", new=AsyncMock()
            ) as never:
                with patch("time.monotonic", clock):
                    with pytest.raises(GeminiTimeoutError):
                        await gemini_provider.call_gemini(
                            [{"role": "user", "content": "x"}],
                            model="gemini-3.7-flash",
                            deadline_monotonic=clock() + 2.0,
                        )
        never.assert_not_called()

    async def test_pooled_keys_share_one_budget_instead_of_one_each(self):
        """Two keys must not cost two full timeouts."""
        from app.llm import gemini_provider
        from app.llm.gemini_provider import GeminiRateLimitError

        clock = FakeClock()
        granted: list[float] = []

        async def timing_out(api_key, messages, model, timeout):
            granted.append(timeout)
            clock.advance(timeout)
            raise GeminiRateLimitError("429", status_code=429)

        with patch.dict(
            "os.environ", {"GEMINI_API_KEYS": "key-a,key-b"}, clear=True
        ):
            with patch.object(gemini_provider, "_call_gemini_once", new=timing_out):
                with patch("time.monotonic", clock):
                    deadline = clock() + SUGGESTIONS_WALL_CLOCK_S
                    with pytest.raises(GeminiRateLimitError):
                        await gemini_provider.call_gemini(
                            [{"role": "user", "content": "x"}],
                            model="gemini-3.7-flash",
                            deadline_monotonic=deadline,
                        )
                    assert clock() <= deadline

        assert sum(granted) <= SUGGESTIONS_WALL_CLOCK_S


@pytest.mark.asyncio
class TestChainStaysInsideThePlatformLimit:
    async def test_the_production_timeout_sequence_no_longer_overruns(self):
        """
        Gemini burns two full timeouts, then Groq is asked for a body.

        This is the sequence that produced FUNCTION_INVOCATION_TIMEOUT: 22 + 22
        + 25 = 69s, every step of which passed a "has the deadline passed?"
        check. The chain must now finish inside the budget — and must still give
        Groq a turn, since a fast secondary is the point of the failover.
        """
        clock = FakeClock()
        groq_timeouts: list[float] = []

        async def gemini_burns_two_timeouts(messages, deadline_monotonic=None):
            for _ in range(2):
                granted = resolve_call_timeout(
                    deadline_monotonic, GEMINI_TIMEOUT, GEMINI_MIN_SLICE_S
                )
                if granted is None:
                    break
                clock.advance(granted)
            raise GeminiTimeoutError("Gemini timed out")

        async def groq_answers(messages, deadline_monotonic=None):
            granted = resolve_call_timeout(
                deadline_monotonic, GROQ_TIMEOUT, GROQ_MIN_SLICE_S
            )
            assert granted is not None, "Groq must still get a turn"
            groq_timeouts.append(granted)
            clock.advance(2.0)
            return VALID_LLM_RESPONSE

        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "gem-key", "GROQ_API_KEY": "groq-key"},
            clear=True,
        ):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new=gemini_burns_two_timeouts,
            ):
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation", new=groq_answers
                ):
                    with patch("time.monotonic", clock):
                        started = clock()
                        result = await generate_suggestions(
                            "原文",
                            "訳文",
                            deadline_monotonic=started + SUGGESTIONS_WALL_CLOCK_S,
                        )

        assert len(result["suggestions"]) == 1
        assert clock() - started <= SUGGESTIONS_WALL_CLOCK_S
        assert clock() - started < PLATFORM_MAX_DURATION_S

    async def test_all_three_providers_burning_every_granted_second_still_fits(self):
        """
        The full chain, worst case: every provider spends its whole slice and
        fails, including in-provider sibling retries.

        Statically this is 22+22 (Gemini) + 25+25 (Groq) + 20 (Cloudflare) =
        114s of provider timeouts against a 60s platform limit, which is why the
        chain can only be safe if each call is sized to what is left. The
        request must finish inside the budget, and every provider must still get
        a turn rather than being starved by the one before it.
        """
        from app.llm.suggestions import SuggestionsError

        clock = FakeClock()
        turns: list[tuple[str, float]] = []

        def burn(name, provider_timeout, min_slice, deadline, attempts):
            for _ in range(attempts):
                granted = resolve_call_timeout(deadline, provider_timeout, min_slice)
                if granted is None:
                    return
                turns.append((name, granted))
                clock.advance(granted)

        async def gemini(messages, deadline_monotonic=None):
            burn("gemini", GEMINI_TIMEOUT, GEMINI_MIN_SLICE_S, deadline_monotonic, 2)
            raise GeminiTimeoutError("Gemini timed out")

        async def groq(messages, deadline_monotonic=None):
            from app.llm.groq_provider import GroqTimeoutError

            burn("groq", GROQ_TIMEOUT, GROQ_MIN_SLICE_S, deadline_monotonic, 2)
            raise GroqTimeoutError("Groq timed out")

        async def cloudflare(messages, deadline_monotonic=None):
            from app.llm.cloudflare_provider import CloudflareTimeoutError

            burn("cloudflare", CF_TIMEOUT, CF_MIN_SLICE_S, deadline_monotonic, 1)
            raise CloudflareTimeoutError("Cloudflare timed out")

        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "gem-key",
                "GROQ_API_KEY": "groq-key",
                "CLOUDFLARE_ACCOUNT_ID": "acc",
                "CLOUDFLARE_API_TOKEN": "tok",
            },
            clear=True,
        ):
            with patch("app.llm.suggestions.call_gemini_with_rotation", new=gemini):
                with patch("app.llm.suggestions.call_groq_with_rotation", new=groq):
                    with patch("app.llm.suggestions.call_cloudflare", new=cloudflare):
                        with patch("time.monotonic", clock):
                            started = clock()
                            with pytest.raises(SuggestionsError) as exc_info:
                                await generate_suggestions(
                                    "原文",
                                    "訳文",
                                    deadline_monotonic=started
                                    + SUGGESTIONS_WALL_CLOCK_S,
                                )

        elapsed = clock() - started
        assert elapsed <= SUGGESTIONS_WALL_CLOCK_S
        assert elapsed < PLATFORM_MAX_DURATION_S
        assert {name for name, _ in turns} == {"gemini", "groq", "cloudflare"}
        # Clamped-and-failed is a budget symptom, so the advice is "retry",
        # not "check your keys".
        assert exc_info.value.timed_out is True

    async def test_a_spent_budget_reports_a_timeout_not_a_provider_failure(self):
        """A skipped-for-budget chain must be diagnosable as such."""
        from app.llm.suggestions import SuggestionsError

        clock = FakeClock()

        with patch.dict(
            "os.environ",
            {"GEMINI_API_KEY": "gem-key", "GROQ_API_KEY": "groq-key"},
            clear=True,
        ):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new_callable=AsyncMock,
            ) as mock_gemini:
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation",
                    new_callable=AsyncMock,
                ) as mock_groq:
                    with patch("time.monotonic", clock):
                        with pytest.raises(SuggestionsError) as exc_info:
                            await generate_suggestions(
                                "原文", "訳文", deadline_monotonic=clock() + 1.0
                            )

        mock_gemini.assert_not_called()
        mock_groq.assert_not_called()
        assert exc_info.value.timed_out is True
        assert exc_info.value.rate_limited is False
        assert "Gemini skipped" in (exc_info.value.gemini_error or "")
        assert "Groq skipped" in (exc_info.value.groq_error or "")

    async def test_a_deadline_from_the_caller_is_honoured(self):
        """The endpoint measures from request entry, not from the first call."""
        clock = FakeClock()
        seen: list[float] = []

        async def groq_answers(messages, deadline_monotonic=None):
            seen.append(deadline_monotonic)
            return VALID_LLM_RESPONSE

        with patch.dict("os.environ", {"GROQ_API_KEY": "groq-key"}, clear=True):
            with patch(
                "app.llm.suggestions.call_groq_with_rotation", new=groq_answers
            ):
                with patch("time.monotonic", clock):
                    # 3s already spent on auth and the stored-prompt lookup.
                    clock.advance(3.0)
                    await generate_suggestions(
                        "原文", "訳文", deadline_monotonic=SUGGESTIONS_WALL_CLOCK_S
                    )

        assert seen == [SUGGESTIONS_WALL_CLOCK_S]
