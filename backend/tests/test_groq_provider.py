"""
Tests for backend/app/llm/groq_provider.py model selection.

Regression coverage for the GROQ_MODEL default switch (llama-3.1-8b-instant ->
llama-3.3-70b-versatile) and its env-var override, kept overridable per
AGENTS.md so a future model swap doesn't require a code change.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.llm.groq_provider import DEFAULT_GROQ_MODEL, get_groq_model, call_groq


class TestGetGroqModel:
    def test_default_model_when_unset(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        assert get_groq_model() == DEFAULT_GROQ_MODEL
        assert get_groq_model() == "llama-3.3-70b-versatile"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3-32b")
        assert get_groq_model() == "qwen/qwen3-32b"

    def test_empty_env_falls_back_to_default(self, monkeypatch):
        """An empty-string GROQ_MODEL (e.g. unset dashboard var) should not
        send a blank model id to Groq's API."""
        monkeypatch.setenv("GROQ_MODEL", "")
        assert get_groq_model() == DEFAULT_GROQ_MODEL


class _FakeResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "{}"}}]}


@pytest.mark.asyncio
class TestCallGroqUsesConfiguredModel:
    async def test_payload_uses_default_model(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}])

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"

    async def test_payload_respects_env_override(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}])

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["model"] == "llama-3.1-8b-instant"
