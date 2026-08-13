"""
Tests for backend/app/llm/suggestions.py with mock providers.

Note: suggestions.py calls call_gemini_with_rotation() / call_groq_with_rotation()
(not the single-model helpers) so in-provider model rotation/retry happens
before falling over Gemini → Groq → Cloudflare. Tests here mock
call_gemini_with_rotation / call_groq_with_rotation / call_cloudflare to
exercise the failover chain without needing to also mock the rotation
internals (those are covered by provider unit tests).
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.llm.suggestions import (
    generate_suggestions,
    SuggestionsError,
    NoProvidersConfiguredError,
    are_providers_configured,
    SUGGESTIONS_WALL_CLOCK_S,
)
from app.llm.groq_provider import GroqError, GroqRateLimitError, GroqServerError, GroqTimeoutError
from app.llm.cloudflare_provider import CloudflareError
from app.llm.gemini_provider import GeminiError, GeminiRateLimitError, GEMINI_TIMEOUT


# overallComment/reason ("コメント"/"全体講評") are intentionally pure
# Chinese (Hanzi only, no Hiragana/Katakana) so this fixture passes the
# has_non_chinese_reason() check added by refine-suggestion-card-interactions
# and doesn't spuriously trigger the language-check retry axis in tests
# that don't care about it. "箇所" (-> original) legitimately stays Japanese.
VALID_LLM_RESPONSE = '''{"指摘": [{"番号": 1, "箇所": "テスト箇所", "コメント": "修正建议内容"}], "全体講評": "整体质量良好"}'''
UNPARSEABLE_LLM_RESPONSE = "I'm sorry, I cannot help with that request."
NON_CHINESE_LLM_RESPONSE = '''{"指摘": [{"番号": 1, "箇所": "テスト箇所", "コメント": "これは日本語のコメントです"}], "全体講評": "全体的に良いです"}'''


class TestAreProvidersConfigured:
    def test_groq_only(self):
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            assert are_providers_configured() is True
    
    def test_cloudflare_only(self):
        with patch.dict('os.environ', {'CLOUDFLARE_ACCOUNT_ID': 'acc', 'CLOUDFLARE_API_TOKEN': 'tok'}, clear=True):
            assert are_providers_configured() is True
    
    def test_both_configured(self):
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            assert are_providers_configured() is True
    
    def test_none_configured(self):
        with patch.dict('os.environ', {}, clear=True):
            assert are_providers_configured() is False

    def test_gemini_only(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'gem-key'}, clear=True):
            assert are_providers_configured() is True


@pytest.mark.asyncio
class TestGenerateSuggestionsGroqSuccess:
    async def test_groq_success_returns_parsed_response(self):
        """Groq succeeds -> return parsed suggestions."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.return_value = VALID_LLM_RESPONSE
                
                result = await generate_suggestions("原文", "訳文")
                
                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["original"] == "テスト箇所"
                assert result["overallComment"] == "整体质量良好"
                mock_groq.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsGroqFailCFSuccess:
    async def test_groq_rate_limit_falls_back_to_cloudflare(self):
        """Groq 429 -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    # call_groq_with_rotation already exhausts its internal
                    # 2-model retry before raising, so a raised error here
                    # means both attempted Groq models failed.
                    mock_groq.side_effect = GroqRateLimitError("Rate limit", status_code=429)
                    mock_cf.return_value = VALID_LLM_RESPONSE
                    
                    result = await generate_suggestions("原文", "訳文")
                    
                    assert len(result["suggestions"]) == 1
                    mock_groq.assert_called_once()
                    mock_cf.assert_called_once()
    
    async def test_groq_server_error_falls_back_to_cloudflare(self):
        """Groq 5xx (both rotation attempts exhausted) -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqServerError("Server error", status_code=500)
                    mock_cf.return_value = VALID_LLM_RESPONSE
                    
                    result = await generate_suggestions("原文", "訳文")
                    
                    assert len(result["suggestions"]) == 1
    
    async def test_groq_timeout_falls_back_to_cloudflare(self):
        """Groq timeout (both rotation attempts exhausted) -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqTimeoutError("Timeout")
                    mock_cf.return_value = VALID_LLM_RESPONSE

                    result = await generate_suggestions("原文", "訳文")

                    assert len(result["suggestions"]) == 1

    async def test_groq_empty_content_falls_back_to_cloudflare(self):
        """HTTP-OK but empty Groq body -> Cloudflare succeeds (no parse burn)."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.return_value = "   "
                    mock_cf.return_value = VALID_LLM_RESPONSE

                    result = await generate_suggestions("原文", "訳文")

                    assert len(result["suggestions"]) == 1
                    mock_cf.assert_called_once()

    async def test_groq_rotation_retries_both_models_before_cloudflare_fallback(self):
        """End-to-end: real call_groq_with_rotation (not mocked) exhausts
        both rotation attempts (mocking the underlying call_groq) before
        the suggestions failover chain moves on to Cloudflare."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.groq_provider.call_groq', new_callable=AsyncMock) as mock_call_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_call_groq.side_effect = [
                        GroqRateLimitError("Rate limit", status_code=429),
                        GroqRateLimitError("Rate limit", status_code=429),
                    ]
                    mock_cf.return_value = VALID_LLM_RESPONSE

                    result = await generate_suggestions("原文", "訳文")

                    assert len(result["suggestions"]) == 1
                    assert mock_call_groq.call_count == 2
                    used_models = [c.kwargs["model"] for c in mock_call_groq.call_args_list]
                    assert len(set(used_models)) == 2, "must try two distinct Groq models before Cloudflare"
                    mock_cf.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsBothFail:
    async def test_both_fail_raises_suggestions_error(self):
        """Groq and Cloudflare fail, Gemini unconfigured -> SuggestionsError."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqRateLimitError("Rate limit", status_code=429)
                    mock_cf.side_effect = CloudflareError("CF error")
                    
                    with pytest.raises(SuggestionsError) as exc_info:
                        await generate_suggestions("原文", "訳文")
                    
                    assert exc_info.value.groq_error is not None
                    assert exc_info.value.cf_error is not None
                    assert exc_info.value.gemini_pool_size == 0
    
    async def test_groq_only_fails_raises_suggestions_error(self):
        """Only Groq configured and fails -> SuggestionsError."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.side_effect = GroqError("API error")
                
                with pytest.raises(SuggestionsError):
                    await generate_suggestions("原文", "訳文")

    async def test_all_three_fail_includes_gemini_pool_size(self):
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok',
            'GEMINI_API_KEYS': 'gem-a,gem-b',
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    with patch(
                        'app.llm.suggestions.call_gemini_with_rotation',
                        new_callable=AsyncMock,
                    ) as mock_gem:
                        mock_groq.side_effect = GroqRateLimitError("Rate limit", status_code=429)
                        mock_cf.side_effect = CloudflareError("CF error")
                        mock_gem.side_effect = GeminiRateLimitError("Gemini 429", status_code=429)

                        with pytest.raises(SuggestionsError) as exc_info:
                            await generate_suggestions("原文", "訳文")

                        assert exc_info.value.gemini_error is not None
                        assert exc_info.value.gemini_pool_size == 2
                        assert exc_info.value.rate_limited is True


@pytest.mark.asyncio
class TestGenerateSuggestionsNoProviders:
    async def test_no_providers_raises_error(self):
        """No providers configured -> NoProvidersConfiguredError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(NoProvidersConfiguredError):
                await generate_suggestions("原文", "訳文")


@pytest.mark.asyncio
class TestGenerateSuggestionsCloudflareOnly:
    async def test_cloudflare_only_success(self):
        """Only Cloudflare configured -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                mock_cf.return_value = VALID_LLM_RESPONSE
                
                result = await generate_suggestions("原文", "訳文")
                
                assert len(result["suggestions"]) == 1
                mock_cf.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsGeminiPrimary:
    async def test_gemini_primary_success_skips_groq_and_cloudflare(self):
        """Gemini succeeds first -> Groq/CF not called."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok',
            'GEMINI_API_KEY': 'gem-key',
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    with patch(
                        'app.llm.suggestions.call_gemini_with_rotation',
                        new_callable=AsyncMock,
                    ) as mock_gem:
                        mock_gem.return_value = VALID_LLM_RESPONSE

                        result = await generate_suggestions("原文", "訳文")

                        assert len(result["suggestions"]) == 1
                        mock_gem.assert_called_once()
                        mock_groq.assert_not_called()
                        mock_cf.assert_not_called()

    async def test_gemini_fails_groq_succeeds(self):
        """Gemini 429 -> Groq succeeds (Cloudflare unused)."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok',
            'GEMINI_API_KEY': 'gem-key',
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    with patch(
                        'app.llm.suggestions.call_gemini_with_rotation',
                        new_callable=AsyncMock,
                    ) as mock_gem:
                        mock_gem.side_effect = GeminiRateLimitError("Gemini 429", status_code=429)
                        mock_groq.return_value = VALID_LLM_RESPONSE

                        result = await generate_suggestions("原文", "訳文")

                        assert len(result["suggestions"]) == 1
                        mock_gem.assert_called_once()
                        mock_groq.assert_called_once()
                        mock_cf.assert_not_called()

    async def test_gemini_only_success(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'gem-key'}, clear=True):
            with patch(
                'app.llm.suggestions.call_gemini_with_rotation',
                new_callable=AsyncMock,
            ) as mock_gem:
                mock_gem.return_value = VALID_LLM_RESPONSE
                result = await generate_suggestions("原文", "訳文")
                assert len(result["suggestions"]) == 1
                mock_gem.assert_called_once()

    async def test_unusable_gemini_and_groq_salvaged_by_cloudflare(self):
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok',
            'GEMINI_API_KEY': 'gem-key',
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    with patch(
                        'app.llm.suggestions.call_gemini_with_rotation',
                        new_callable=AsyncMock,
                    ) as mock_gem:
                        mock_gem.return_value = NON_CHINESE_LLM_RESPONSE
                        mock_groq.return_value = UNPARSEABLE_LLM_RESPONSE
                        mock_cf.return_value = VALID_LLM_RESPONSE

                        result = await generate_suggestions("原文", "訳文")

                        assert result["suggestions"][0]["reason"] == "修正建议内容"
                        mock_gem.assert_called_once()
                        mock_groq.assert_called_once()
                        mock_cf.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsContentSalvage:
    """Same-pass Cloudflare salvage when Groq body is unusable."""

    async def test_groq_non_chinese_salvaged_by_cloudflare_same_pass(self):
        """Groq returns Japanese reasons -> CF Chinese in same pass (no outer retry)."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.return_value = NON_CHINESE_LLM_RESPONSE
                    mock_cf.return_value = VALID_LLM_RESPONSE

                    result = await generate_suggestions("原文", "訳文")

                    assert result["suggestions"][0]["reason"] == "修正建议内容"
                    assert mock_groq.call_count == 1
                    mock_cf.assert_called_once()

    async def test_groq_unparseable_salvaged_by_cloudflare_same_pass(self):
        """Groq prose (no JSON) -> CF JSON in same pass."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.return_value = UNPARSEABLE_LLM_RESPONSE
                    mock_cf.return_value = VALID_LLM_RESPONSE

                    result = await generate_suggestions("原文", "訳文")

                    assert len(result["suggestions"]) == 1
                    assert mock_groq.call_count == 1
                    mock_cf.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsParseFailureRetry:
    """
    Tests for the JSON-parse-failure retry axis in generate_suggestions()
    (MAX_PARSE_RETRY_ATTEMPTS). This is distinct from the network-level
    retry covered by TestGenerateSuggestionsGroqFailCFSuccess above: here
    call_groq_with_rotation always succeeds at the network level, but its
    *content* sometimes fails to parse as JSON.
    """

    async def test_parse_fails_twice_then_succeeds_on_third_attempt(self):
        """Attempts 1 and 2 return unparseable content; attempt 3 succeeds."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.side_effect = [
                    UNPARSEABLE_LLM_RESPONSE,
                    UNPARSEABLE_LLM_RESPONSE,
                    VALID_LLM_RESPONSE,
                ]

                result = await generate_suggestions("原文", "訳文")

                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["original"] == "テスト箇所"
                assert mock_groq.call_count == 3

    async def test_gives_up_after_max_parse_retry_attempts(self):
        """Every attempt fails to parse -> returns parse-failure placeholder
        after exactly MAX_PARSE_RETRY_ATTEMPTS attempts, without raising."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.return_value = UNPARSEABLE_LLM_RESPONSE

                result = await generate_suggestions("原文", "訳文")

                assert result["suggestions"] == []
                assert "抽出できませんでした" in result["overallComment"]
                assert mock_groq.call_count == 4

    async def test_parse_failure_retry_does_not_affect_network_failure_raising(self):
        """A genuine network-level failure (both providers down) still
        raises immediately on the first attempt, without consuming the
        parse-retry budget (these are independent, composable axes)."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqRateLimitError("Rate limit", status_code=429)
                    mock_cf.side_effect = CloudflareError("CF error")

                    with pytest.raises(SuggestionsError):
                        await generate_suggestions("原文", "訳文")

                    mock_groq.assert_called_once()
                    mock_cf.assert_called_once()


@pytest.mark.asyncio
class TestGenerateSuggestionsChineseLanguageRetry:
    """
    Tests for the Chinese-language content-check retry axis in
    generate_suggestions() (composes with, and shares the same
    MAX_PARSE_RETRY_ATTEMPTS budget as, the JSON-parse-failure retry axis
    covered by TestGenerateSuggestionsParseFailureRetry above).
    """

    async def test_non_chinese_reason_twice_then_valid_chinese_on_third_attempt(self):
        """Attempts 1 and 2 return a Japanese (not Chinese) reason/overallComment;
        attempt 3 returns a valid Chinese response."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.side_effect = [
                    NON_CHINESE_LLM_RESPONSE,
                    NON_CHINESE_LLM_RESPONSE,
                    VALID_LLM_RESPONSE,
                ]

                result = await generate_suggestions("原文", "訳文")

                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["original"] == "テスト箇所"
                assert mock_groq.call_count == 3

    async def test_gives_up_after_max_attempts_still_non_chinese(self):
        """Every attempt returns a Japanese (not Chinese) reason -> returns
        the last result after exactly MAX_PARSE_RETRY_ATTEMPTS attempts,
        without raising."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.return_value = NON_CHINESE_LLM_RESPONSE

                result = await generate_suggestions("原文", "訳文")

                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["reason"] == "これは日本語のコメントです"
                assert mock_groq.call_count == 4

    async def test_parse_failure_and_language_failure_share_one_attempt_budget(self):
        """A JSON-parse failure on attempt 1 and a non-Chinese-reason
        failure on attempt 2 both count against the same shared retry
        budget before attempt 3 succeeds."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.side_effect = [
                    UNPARSEABLE_LLM_RESPONSE,
                    NON_CHINESE_LLM_RESPONSE,
                    VALID_LLM_RESPONSE,
                ]

                result = await generate_suggestions("原文", "訳文")

                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["original"] == "テスト箇所"
                assert mock_groq.call_count == 3


class TestVercelTimeoutBudget:
    def test_gemini_http_timeout_fits_platform_budget(self):
        assert GEMINI_TIMEOUT <= 25.0
        assert SUGGESTIONS_WALL_CLOCK_S < 60.0
        assert GEMINI_TIMEOUT < SUGGESTIONS_WALL_CLOCK_S


@pytest.mark.asyncio
class TestEmptyGeminiSkipsAndWallClock:
    async def test_empty_gemini_pool_skips_without_gemini_http(self):
        """No Gemini env -> Groq succeeds; Gemini call never made."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new_callable=AsyncMock,
            ) as mock_gem:
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation",
                    new_callable=AsyncMock,
                ) as mock_groq:
                    mock_groq.return_value = VALID_LLM_RESPONSE
                    result = await generate_suggestions("原文", "訳文")
                    assert len(result["suggestions"]) == 1
                    mock_gem.assert_not_called()
                    mock_groq.assert_called_once()

    async def test_wall_clock_budget_raises_before_next_provider(self):
        """Exhausted deadline before Groq -> SuggestionsError (app 503 path)."""
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "gem-key",
                "GROQ_API_KEY": "test-key",
            },
            clear=True,
        ):
            with patch(
                "app.llm.suggestions.call_gemini_with_rotation",
                new_callable=AsyncMock,
            ) as mock_gem:
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation",
                    new_callable=AsyncMock,
                ) as mock_groq:
                    with patch(
                        "app.llm.suggestions.time.monotonic",
                        side_effect=[0.0, 0.0, 0.0, 100.0],
                    ):
                        mock_gem.side_effect = GeminiRateLimitError(
                            "Gemini 429", status_code=429
                        )
                        with pytest.raises(SuggestionsError) as exc_info:
                            await generate_suggestions("原文", "訳文")
                        assert "wall-clock" in str(exc_info.value).lower()
                        mock_gem.assert_called_once()
                        mock_groq.assert_not_called()


# 15-iteration enforcement harness (enforce-chinese-suggestion-comments).
# Runs the detector + generate_suggestions retry path fifteen times with
# mocked providers so CI stays deterministic (no live Groq).
CHINESE_ENFORCEMENT_ITERATIONS = 15

CHINESE_PAYLOAD = {
    "suggestions": [
        {
            "id": "1",
            "original": "行きます",
            "reason": "这里应该用过去式，而不是现在时",
            "sourceExcerpt": "行きました",
        }
    ],
    "overallComment": "整体表达清楚，继续保持！",
}

JAPANESE_PAYLOAD = {
    "suggestions": [
        {
            "id": "1",
            "original": "行きます",
            "reason": "ここは過去形を使うべきです",
            "sourceExcerpt": "行きました",
        }
    ],
    "overallComment": "全体的にとても良いです",
}


class TestChineseEnforcementFifteenIterations:
    """「毎回テストを１５回行い」— verify Chinese enforcement 15 times.

    Mock-only: patches Groq. For live Groq×15 on the epic corpus, see
    `test_live_groq_chinese_explanations_fifteen_iterations_optional`.
    """

    def test_detector_chinese_passes_and_japanese_fails_fifteen_times(self):
        from app.llm.parser import has_non_chinese_reason

        for i in range(CHINESE_ENFORCEMENT_ITERATIONS):
            assert has_non_chinese_reason(CHINESE_PAYLOAD) is False, (
                f"iteration {i + 1}/{CHINESE_ENFORCEMENT_ITERATIONS}: "
                "Chinese payload must pass"
            )
            assert has_non_chinese_reason(JAPANESE_PAYLOAD) is True, (
                f"iteration {i + 1}/{CHINESE_ENFORCEMENT_ITERATIONS}: "
                "Japanese payload must fail"
            )

    def test_retry_loop_accepts_chinese_after_japanese_fifteen_times(self):
        """Each of 15 runs: mock JP then CN; enforcement must retry and accept CN.

        Sync wrapper via asyncio.run so this harness executes even when
        pytest-asyncio is not installed in the test environment.
        Uses the real epic SOURCE/TARGET fixture as prompt inputs (provider
        response is still mocked).
        """
        import asyncio

        from app.llm.parser import has_non_chinese_reason
        from tests.fixtures.epic_shi_source_target import (
            EPIC_SOURCE_TEXT,
            EPIC_TARGET_TEXT,
        )

        async def _once(iteration: int) -> None:
            with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=True):
                with patch(
                    "app.llm.suggestions.call_groq_with_rotation",
                    new_callable=AsyncMock,
                ) as mock_groq:
                    mock_groq.side_effect = [
                        NON_CHINESE_LLM_RESPONSE,
                        VALID_LLM_RESPONSE,
                    ]

                    result = await generate_suggestions(
                        EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT
                    )

                    assert has_non_chinese_reason(result) is False, (
                        f"iteration {iteration + 1}/{CHINESE_ENFORCEMENT_ITERATIONS}: "
                        "final result must be Chinese"
                    )
                    assert result["suggestions"][0]["original"] == "テスト箇所"
                    assert mock_groq.call_count == 2, (
                        f"iteration {iteration + 1}: expected JP→CN retry (2 calls), "
                        f"got {mock_groq.call_count}"
                    )

        for i in range(CHINESE_ENFORCEMENT_ITERATIONS):
            asyncio.run(_once(i))


@pytest.mark.integration
@pytest.mark.skipif(
    __import__("os").environ.get("GROQ_API_KEY") in (None, ""),
    reason="GROQ_API_KEY not set; live Chinese-enforcement smoke skipped",
)
@pytest.mark.asyncio
async def test_live_groq_chinese_explanations_fifteen_iterations_optional():
    """Optional live smoke ×15 on epic fixture — skipped without API key (CI-safe)."""
    from app.llm.parser import has_non_chinese_reason, is_json_extraction_failure
    from tests.fixtures.epic_shi_source_target import (
        EPIC_SOURCE_TEXT,
        EPIC_TARGET_TEXT,
    )

    failures: list[str] = []
    for i in range(CHINESE_ENFORCEMENT_ITERATIONS):
        result = await generate_suggestions(EPIC_SOURCE_TEXT, EPIC_TARGET_TEXT)
        if is_json_extraction_failure(result):
            failures.append(f"iter {i + 1}: JSON extraction failure")
            continue
        if has_non_chinese_reason(result):
            oc = (result.get("overallComment") or "")[:60]
            jp_reasons = [
                (s.get("reason") or "")[:60]
                for s in result.get("suggestions") or []
                if s.get("reason")
            ][:2]
            failures.append(
                f"iter {i + 1}: non-Chinese fields; overall={oc!r}; "
                f"reason_samples={jp_reasons!r}"
            )
            continue
        assert len(result["suggestions"]) >= 1

    assert not failures, (
        f"{len(failures)}/{CHINESE_ENFORCEMENT_ITERATIONS} live iterations failed "
        f"Chinese enforcement:\n" + "\n".join(failures)
    )
