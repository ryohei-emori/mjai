"""
Tests for backend/app/llm/groq_provider.py model selection and rotation.

Regression coverage for the GROQ_MODEL env-var override plus the multi-model
rotation pool (ALLOWED_GROQ_MODELS) added to replace the single hardcoded
llama-3.3-70b-versatile default ahead of its 2026-08-16 Groq shutdown.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.llm.groq_provider import (
    ALLOWED_GROQ_MODELS,
    DEFAULT_GROQ_MODEL,
    get_groq_model,
    is_rotation_enabled,
    select_groq_models,
    call_groq,
    call_groq_with_rotation,
    GroqError,
    GroqRateLimitError,
    GroqServerError,
    GroqTimeoutError,
)


class TestGetGroqModel:
    def test_default_model_when_unset(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        assert get_groq_model() == DEFAULT_GROQ_MODEL
        assert get_groq_model() in ALLOWED_GROQ_MODELS

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3-32b")
        assert get_groq_model() == "qwen/qwen3-32b"

    def test_empty_env_falls_back_to_default(self, monkeypatch):
        """An empty-string GROQ_MODEL (e.g. unset dashboard var) should not
        send a blank model id to Groq's API."""
        monkeypatch.setenv("GROQ_MODEL", "")
        assert get_groq_model() == DEFAULT_GROQ_MODEL


class TestIsRotationEnabled:
    def test_enabled_when_unset(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        assert is_rotation_enabled() is True

    def test_disabled_when_set(self, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
        assert is_rotation_enabled() is False

    def test_enabled_when_empty_string(self, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "")
        assert is_rotation_enabled() is True


class TestSelectGroqModels:
    def test_rotation_enabled_returns_only_allowed_models(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        for _ in range(20):
            models = select_groq_models(n=2)
            assert len(models) == 2
            assert len(set(models)) == 2, "must be distinct models"
            for m in models:
                assert m in ALLOWED_GROQ_MODELS

    def test_rotation_disabled_returns_pinned_model_only(self, monkeypatch):
        monkeypatch.setenv("GROQ_MODEL", "some-custom-model")
        models = select_groq_models(n=2)
        assert models == ["some-custom-model"]

    def test_uses_random_sample_when_rotation_enabled(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        with patch("app.llm.groq_provider.random.sample") as mock_sample:
            mock_sample.return_value = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            result = select_groq_models(n=2)
            mock_sample.assert_called_once_with(ALLOWED_GROQ_MODELS, 2)
            assert result == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    def test_n_clamped_to_pool_size(self, monkeypatch):
        monkeypatch.delenv("GROQ_MODEL", raising=False)
        models = select_groq_models(n=100)
        assert len(models) == len(ALLOWED_GROQ_MODELS)


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
        assert kwargs["json"]["model"] == DEFAULT_GROQ_MODEL

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

    async def test_payload_respects_explicit_model_param(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}], model="openai/gpt-oss-20b")

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["model"] == "openai/gpt-oss-20b"

    async def test_qwen_model_disables_reasoning_effort(self, monkeypatch):
        """Regression test for a live-smoke-test finding: qwen/qwen3.6-27b's
        default reasoning mode emits a <think> block that can consume the
        entire max_tokens budget before any JSON is produced, causing the
        parser to silently fall back to placeholder text instead of raising
        an error. reasoning_effort="none" must be sent for this model to
        disable that behavior."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}], model="qwen/qwen3.6-27b")

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["reasoning_effort"] == "none"

    async def test_gpt_oss_models_do_not_set_reasoning_effort(self, monkeypatch):
        """gpt-oss models don't emit an inline <think> block at default
        settings, so no reasoning_effort override is needed (and gpt-oss
        only accepts low/medium/high, not "none", so sending it would be
        wrong for this family)."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        for model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
            mock_client = AsyncMock()
            mock_client.post.return_value = _FakeResponse()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = False

            with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
                await call_groq([{"role": "user", "content": "hi"}], model=model)

            _, kwargs = mock_client.post.call_args
            assert "reasoning_effort" not in kwargs["json"]


@pytest.mark.asyncio
class TestCallGroqWithRotation:
    async def test_first_model_success_no_retry(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        with patch(
            "app.llm.groq_provider.select_groq_models",
            return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        ):
            with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = '{"ok": true}'
                result = await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        assert result == ('{"ok": true}', "openai/gpt-oss-120b")
        mock_call.assert_called_once()
        _, kwargs = mock_call.call_args
        assert kwargs["model"] == "openai/gpt-oss-120b"

    async def test_first_model_retriable_failure_second_model_succeeds(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        with patch(
            "app.llm.groq_provider.select_groq_models",
            return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        ):
            with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = [
                    GroqRateLimitError("rate limited", status_code=429),
                    '{"ok": true}',
                ]
                result = await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        # The reported model is the one that answered, not the one first tried.
        assert result == ('{"ok": true}', "openai/gpt-oss-20b")
        assert mock_call.call_count == 2
        used_models = [c.kwargs["model"] for c in mock_call.call_args_list]
        assert used_models == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
        assert len(set(used_models)) == 2

    async def test_both_models_fail_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        with patch(
            "app.llm.groq_provider.select_groq_models",
            return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        ):
            with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = [
                    GroqServerError("server error", status_code=500),
                    GroqServerError("server error", status_code=500),
                ]
                with pytest.raises(GroqServerError):
                    await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        assert mock_call.call_count == 2

    async def test_timeout_then_success(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        with patch(
            "app.llm.groq_provider.select_groq_models",
            return_value=["qwen/qwen3.6-27b", "openai/gpt-oss-120b"],
        ):
            with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = [
                    GroqTimeoutError("timed out"),
                    '{"ok": true}',
                ]
                result = await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        assert result == ('{"ok": true}', "openai/gpt-oss-120b")
        assert mock_call.call_count == 2

    async def test_non_retriable_error_does_not_retry(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        with patch(
            "app.llm.groq_provider.select_groq_models",
            return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        ):
            with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = GroqError("unexpected response format")
                with pytest.raises(GroqError):
                    await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        mock_call.assert_called_once()

    async def test_groq_model_override_no_retry_on_failure(self, monkeypatch):
        """GROQ_MODEL set (rotation disabled): a retriable failure on the
        single pinned model propagates immediately without a second
        attempt, matching pre-change behavior exactly."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")

        with patch("app.llm.groq_provider.call_groq", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = GroqRateLimitError("rate limited", status_code=429)
            with pytest.raises(GroqRateLimitError):
                await call_groq_with_rotation([{"role": "user", "content": "hi"}])

        mock_call.assert_called_once()
        _, kwargs = mock_call.call_args
        assert kwargs["model"] == "openai/gpt-oss-120b"
