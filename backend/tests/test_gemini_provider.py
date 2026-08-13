"""Unit tests for backend/app/llm/gemini_provider.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.llm.gemini_provider import (
    ALLOWED_GEMINI_MODELS,
    GeminiError,
    GeminiRateLimitError,
    call_gemini,
    call_gemini_with_rotation,
    get_gemini_model,
    is_rotation_enabled,
    select_gemini_models,
    _extract_text_from_response,
    _messages_to_gemini_payload,
)
from app.llm.key_pool import reset_key_pool_state


@pytest.fixture(autouse=True)
def _reset_pool():
    reset_key_pool_state()
    yield
    reset_key_pool_state()


class _FakeResponse:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {
            "candidates": [{"content": {"parts": [{"text": "{}"}]}}]
        }

    def json(self):
        return self._payload


class TestModelSelection:
    def test_pin_disables_rotation(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
        assert not is_rotation_enabled()
        assert get_gemini_model() == "gemini-flash-latest"
        assert select_gemini_models(2) == ["gemini-flash-latest"]

    def test_default_pool(self, monkeypatch):
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        assert is_rotation_enabled()
        models = select_gemini_models(2)
        assert len(models) == 2
        assert set(models).issubset(set(ALLOWED_GEMINI_MODELS))


class TestMessageMapping:
    def test_system_and_user(self):
        payload = _messages_to_gemini_payload(
            [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "hi"},
            ]
        )
        assert payload["system_instruction"]["parts"][0]["text"] == "sys"
        assert payload["contents"][0]["role"] == "user"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["maxOutputTokens"] >= 8192

    def test_extract_logs_max_tokens_finish_reason(self, caplog):
        import logging

        payload = {
            "candidates": [
                {
                    "finishReason": "MAX_TOKENS",
                    "content": {"parts": [{"text": '{"suggestions":[]}'}]},
                }
            ]
        }
        with caplog.at_level(logging.WARNING, logger="app.llm.gemini_provider"):
            text = _extract_text_from_response(payload)
        assert "suggestions" in text
        assert any("MAX_TOKENS" in r.message for r in caplog.records)


@pytest.mark.asyncio
class TestCallGemini:
    async def test_success(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "k1")
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse(
            payload={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"suggestions":[],"overallComment":"好"}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
        )
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            result = await call_gemini([{"role": "user", "content": "hi"}])

        assert "overallComment" in result
        url = mock_client.post.call_args.args[0]
        assert "gemini-3.7-flash:generateContent" in url
        assert mock_client.post.call_args.kwargs["headers"]["x-goog-api-key"] == "k1"

    async def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        with pytest.raises(GeminiError):
            await call_gemini([{"role": "user", "content": "hi"}])

    async def test_rotation_retries_second_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "k1")
        monkeypatch.delenv("GEMINI_MODEL", raising=False)

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(
                payload={
                    "candidates": [
                        {"content": {"parts": [{"text": '{"ok":true}'}]}}
                    ]
                }
            ),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            with patch(
                "app.llm.gemini_provider.select_gemini_models",
                return_value=["gemini-3.7-flash", "gemini-3.6-flash"],
            ):
                result = await call_gemini_with_rotation(
                    [{"role": "user", "content": "hi"}]
                )

        assert result == '{"ok":true}'
        urls = [c.args[0] for c in mock_client.post.call_args_list]
        assert "gemini-3.7-flash" in urls[0]
        assert "gemini-3.6-flash" in urls[1]

    async def test_pin_no_model_retry(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "k1")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse(status_code=429, text="rate")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(GeminiRateLimitError):
                await call_gemini_with_rotation([{"role": "user", "content": "hi"}])

        assert mock_client.post.call_count == 1
