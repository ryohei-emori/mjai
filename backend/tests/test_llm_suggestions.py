"""
Tests for backend/app/llm/suggestions.py with mock providers.

Note: suggestions.py calls call_groq_with_rotation() (not call_groq()
directly) so that in-provider model rotation/retry across the Groq pool
happens before falling back to Cloudflare. Tests here mock
call_groq_with_rotation to exercise the Groq-vs-Cloudflare failover chain
without needing to also mock the rotation internals (those are covered by
backend/tests/test_groq_provider.py).
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.llm.suggestions import (
    generate_suggestions,
    SuggestionsError,
    NoProvidersConfiguredError,
    are_providers_configured,
)
from app.llm.groq_provider import GroqError, GroqRateLimitError, GroqServerError, GroqTimeoutError
from app.llm.cloudflare_provider import CloudflareError


# overallComment/reason ("コメント"/"全体講評") are intentionally pure
# Chinese (Hanzi only, no Hiragana/Katakana) so this fixture passes the
# has_non_chinese_reason() check added by refine-suggestion-card-interactions
# and doesn't spuriously trigger the language-check retry axis in tests
# that don't care about it. "箇所" (-> original) legitimately stays Japanese.
VALID_LLM_RESPONSE = '''{"指摘": [{"番号": 1, "箇所": "テスト箇所", "コメント": "修正建议内容"}], "全体講評": "整体质量良好"}'''


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
        """Both Groq and Cloudflare fail -> SuggestionsError."""
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
    
    async def test_groq_only_fails_raises_suggestions_error(self):
        """Only Groq configured and fails -> SuggestionsError."""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'}, clear=True):
            with patch('app.llm.suggestions.call_groq_with_rotation', new_callable=AsyncMock) as mock_groq:
                mock_groq.side_effect = GroqError("API error")
                
                with pytest.raises(SuggestionsError):
                    await generate_suggestions("原文", "訳文")


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


UNPARSEABLE_LLM_RESPONSE = "I'm sorry, I cannot help with that request."


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
                assert mock_groq.call_count == 3

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


NON_CHINESE_LLM_RESPONSE = '''{"指摘": [{"番号": 1, "箇所": "テスト箇所", "コメント": "これは日本語のコメントです"}], "全体講評": "全体的に良いです"}'''


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
                assert mock_groq.call_count == 3

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
