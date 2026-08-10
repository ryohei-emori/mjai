"""
Tests for backend/app/llm/suggestions.py with mock providers.
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


VALID_LLM_RESPONSE = '''{"指摘": [{"番号": 1, "箇所": "テスト箇所", "コメント": "修正提案"}], "全体講評": "全体的に良好です"}'''


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
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
                mock_groq.return_value = VALID_LLM_RESPONSE
                
                result = await generate_suggestions("原文", "訳文")
                
                assert len(result["suggestions"]) == 1
                assert result["suggestions"][0]["original"] == "テスト箇所"
                assert result["overallComment"] == "全体的に良好です"
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
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqRateLimitError("Rate limit", status_code=429)
                    mock_cf.return_value = VALID_LLM_RESPONSE
                    
                    result = await generate_suggestions("原文", "訳文")
                    
                    assert len(result["suggestions"]) == 1
                    mock_groq.assert_called_once()
                    mock_cf.assert_called_once()
    
    async def test_groq_server_error_falls_back_to_cloudflare(self):
        """Groq 5xx -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqServerError("Server error", status_code=500)
                    mock_cf.return_value = VALID_LLM_RESPONSE
                    
                    result = await generate_suggestions("原文", "訳文")
                    
                    assert len(result["suggestions"]) == 1
    
    async def test_groq_timeout_falls_back_to_cloudflare(self):
        """Groq timeout -> Cloudflare succeeds."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
                with patch('app.llm.suggestions.call_cloudflare', new_callable=AsyncMock) as mock_cf:
                    mock_groq.side_effect = GroqTimeoutError("Timeout")
                    mock_cf.return_value = VALID_LLM_RESPONSE
                    
                    result = await generate_suggestions("原文", "訳文")
                    
                    assert len(result["suggestions"]) == 1


@pytest.mark.asyncio
class TestGenerateSuggestionsBothFail:
    async def test_both_fail_raises_suggestions_error(self):
        """Both Groq and Cloudflare fail -> SuggestionsError."""
        with patch.dict('os.environ', {
            'GROQ_API_KEY': 'test-key',
            'CLOUDFLARE_ACCOUNT_ID': 'acc',
            'CLOUDFLARE_API_TOKEN': 'tok'
        }, clear=True):
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
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
            with patch('app.llm.suggestions.call_groq', new_callable=AsyncMock) as mock_groq:
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
