"""Unit tests for backend/app/llm/key_pool.py."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.llm.key_pool import (
    DEFAULT_COOLDOWN_SECONDS,
    acquire_cloudflare,
    acquire_gemini,
    acquire_groq,
    is_cloudflare_configured,
    is_gemini_configured,
    is_groq_configured,
    load_cloudflare_credentials,
    load_gemini_credentials,
    load_groq_credentials,
    mark_cooldown,
    redact_secret,
    reset_key_pool_state,
)
from app.llm.groq_provider import (
    call_groq,
    call_groq_with_rotation,
    GroqRateLimitError,
)
from app.llm.cloudflare_provider import call_cloudflare, CloudflareRateLimitError
from app.llm.gemini_provider import call_gemini, GeminiRateLimitError


@pytest.fixture(autouse=True)
def _reset_pool():
    reset_key_pool_state()
    yield
    reset_key_pool_state()


class TestRedactSecret:
    def test_redacts_long_value(self):
        assert redact_secret("gsk_abcdefghijklmnop") == "gsk_…mnop"

    def test_short_value(self):
        assert redact_secret("short") == "***"


class TestLoadGroq:
    def test_singular_back_compat(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEYS", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "gsk_only")
        creds = load_groq_credentials()
        assert len(creds) == 1
        assert creds[0].api_key == "gsk_only"
        assert is_groq_configured()

    def test_plural_wins_over_singular(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.setenv("GROQ_API_KEY", "key-ignored")
        creds = load_groq_credentials()
        assert [c.api_key for c in creds] == ["key-a", "key-b"]

    def test_ignores_empty_csv_entries(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,,key-b,")
        assert [c.api_key for c in load_groq_credentials()] == ["key-a", "key-b"]

    def test_dedupes_identical_keys(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-a,key-b")
        monkeypatch.setenv("GROQ_API_KEY", "key-ignored")
        assert [c.api_key for c in load_groq_credentials()] == ["key-a", "key-b"]

    def test_empty_pool(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEYS", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        assert load_groq_credentials() == []
        assert not is_groq_configured()


class TestLoadCloudflare:
    def test_singular_back_compat(self, monkeypatch):
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_IDS", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_TOKENS", raising=False)
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc1")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok1")
        creds = load_cloudflare_credentials()
        assert len(creds) == 1
        assert creds[0].account_id == "acc1"
        assert creds[0].api_token == "tok1"
        assert is_cloudflare_configured()

    def test_parallel_lists(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_IDS", "a1,a2")
        monkeypatch.setenv("CLOUDFLARE_API_TOKENS", "t1,t2")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "ignored")
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "ignored")
        creds = load_cloudflare_credentials()
        assert [(c.account_id, c.api_token) for c in creds] == [
            ("a1", "t1"),
            ("a2", "t2"),
        ]

    def test_mismatched_lengths_empty_pool(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_IDS", "a1,a2")
        monkeypatch.setenv("CLOUDFLARE_API_TOKENS", "t1")
        assert load_cloudflare_credentials() == []
        assert not is_cloudflare_configured()


class TestLoadGemini:
    def test_singular_back_compat(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "gem_only")
        creds = load_gemini_credentials()
        assert len(creds) == 1
        assert creds[0].api_key == "gem_only"
        assert is_gemini_configured()

    def test_plural_wins_over_singular(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a,gem-b")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-ignored")
        creds = load_gemini_credentials()
        assert [c.api_key for c in creds] == ["gem-a", "gem-b"]

    def test_ignores_empty_csv_entries(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a,,gem-b,")
        assert [c.api_key for c in load_gemini_credentials()] == ["gem-a", "gem-b"]

    def test_dedupes_identical_keys(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "gem-a,gem-a,gem-b")
        assert [c.api_key for c in load_gemini_credentials()] == ["gem-a", "gem-b"]

    def test_empty_pool(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert load_gemini_credentials() == []
        assert not is_gemini_configured()


class TestAcquireAndCooldown:
    def test_round_robin_selection(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "k1,k2,k3")
        seen = [acquire_groq().api_key for _ in range(6)]
        assert seen == ["k1", "k2", "k3", "k1", "k2", "k3"]

    def test_cooldown_skips_credential(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "k1,k2")
        first = acquire_groq()
        assert first.api_key == "k1"
        mark_cooldown(first.id, seconds=60)
        second = acquire_groq()
        assert second is not None
        assert second.api_key == "k2"
        # Still only k2 eligible
        third = acquire_groq()
        assert third.api_key == "k2"

    def test_cooldown_expiry(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "k1,k2")
        c1 = acquire_groq()
        mark_cooldown(c1.id, seconds=0.05)
        time.sleep(0.08)
        # Both eligible again; RR continues
        keys = {acquire_groq().api_key for _ in range(4)}
        assert keys == {"k1", "k2"}

    def test_exclude_ids(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "k1,k2")
        c1 = load_groq_credentials()[0]
        picked = acquire_groq(exclude_ids=[c1.id])
        assert picked.api_key == "k2"

    def test_all_cooled_returns_none(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "k1")
        c = acquire_groq()
        mark_cooldown(c.id, seconds=DEFAULT_COOLDOWN_SECONDS)
        assert acquire_groq() is None


class _FakeResponse:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {"choices": [{"message": {"content": "{}"}}]}

    def json(self):
        return self._payload


@pytest.mark.asyncio
class TestProviderKeyFallback:
    async def test_groq_retries_next_key_on_429(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            result = await call_groq([{"role": "user", "content": "hi"}])

        assert result == "{}"
        assert mock_client.post.call_count == 2
        auth_headers = [
            c.kwargs["headers"]["Authorization"] for c in mock_client.post.call_args_list
        ]
        assert auth_headers[0] == "Bearer key-a"
        assert auth_headers[1] == "Bearer key-b"

    async def test_groq_exhausts_pool_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse(status_code=429, text="rate")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(GroqRateLimitError) as exc_info:
                await call_groq([{"role": "user", "content": "hi"}])

        assert mock_client.post.call_count == 2
        assert "pool_size=2" in str(exc_info.value)
        # Cooldown is model-scoped — same model must see an empty pool.
        from app.llm.groq_provider import get_groq_model

        assert acquire_groq(cooldown_scope=get_groq_model()) is None
        # Unscoped acquire (Cloudflare-style) is unaffected by Groq model cooldowns.
        assert acquire_groq() is not None

    async def test_groq_does_not_retry_cooled_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}])

        # Second call should skip cooled key-a and hit key-b only once.
        mock_client.post.reset_mock()
        mock_client.post.side_effect = None
        mock_client.post.return_value = _FakeResponse(status_code=200)
        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}])

        assert mock_client.post.call_count == 1
        auth = mock_client.post.call_args.kwargs["headers"]["Authorization"]
        assert auth == "Bearer key-b"

    async def test_groq_model_scoped_cooldown_allows_second_model(
        self, monkeypatch
    ):
        """429 on model A must not block the same keys for model B rotation."""
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_MODEL", raising=False)

        mock_client = AsyncMock()
        # Model A: both keys 429. Model B: key-a succeeds.
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            with patch(
                "app.llm.groq_provider.select_groq_models",
                return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
            ):
                result = await call_groq_with_rotation(
                    [{"role": "user", "content": "hi"}]
                )

        assert result == ("{}", "openai/gpt-oss-20b")
        assert mock_client.post.call_count == 3
        models = [
            c.kwargs["json"]["model"] for c in mock_client.post.call_args_list
        ]
        assert models[0] == "openai/gpt-oss-120b"
        assert models[1] == "openai/gpt-oss-120b"
        assert models[2] == "openai/gpt-oss-20b"
        auth = mock_client.post.call_args_list[2].kwargs["headers"]["Authorization"]
        assert auth in ("Bearer key-a", "Bearer key-b")

    async def test_groq_same_model_still_skips_cooled_key(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        model = "openai/gpt-oss-20b"
        monkeypatch.setenv("GROQ_MODEL", model)

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.groq_provider.httpx.AsyncClient", return_value=mock_client):
            await call_groq([{"role": "user", "content": "hi"}], model=model)

        # Same model: key-a still cooled; only key-b is eligible.
        assert acquire_groq(cooldown_scope=model).api_key == "key-b"

    async def test_cloudflare_retries_next_credential_on_429(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_IDS", "acc-a,acc-b")
        monkeypatch.setenv("CLOUDFLARE_API_TOKENS", "tok-a,tok-b")
        monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)

        ok_payload = {
            "success": True,
            "result": {"response": '{"suggestions":[],"overallComment":"ok"}'},
        }
        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200, payload=ok_payload),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch(
            "app.llm.cloudflare_provider.httpx.AsyncClient", return_value=mock_client
        ):
            result = await call_cloudflare([{"role": "user", "content": "hi"}])

        assert "overallComment" in result
        assert mock_client.post.call_count == 2
        urls = [c.args[0] for c in mock_client.post.call_args_list]
        assert "acc-a" in urls[0]
        assert "acc-b" in urls[1]

    async def test_cloudflare_exhausts_raises(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_IDS", "acc-a")
        monkeypatch.setenv("CLOUDFLARE_API_TOKENS", "tok-a")

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse(status_code=403, text="forbidden")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch(
            "app.llm.cloudflare_provider.httpx.AsyncClient", return_value=mock_client
        ):
            with pytest.raises(CloudflareRateLimitError):
                await call_cloudflare([{"role": "user", "content": "hi"}])


class TestCloudflareAcquire:
    def test_acquire_cloudflare_round_robin(self, monkeypatch):
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_IDS", "a1,a2")
        monkeypatch.setenv("CLOUDFLARE_API_TOKENS", "t1,t2")
        assert acquire_cloudflare().account_id == "a1"
        assert acquire_cloudflare().account_id == "a2"
        assert acquire_cloudflare().account_id == "a1"


class TestGeminiAcquire:
    def test_acquire_gemini_round_robin(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "g1,g2")
        assert acquire_gemini().api_key == "g1"
        assert acquire_gemini().api_key == "g2"
        assert acquire_gemini().api_key == "g1"

    def test_gemini_cooldown_skips_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "g1,g2")
        first = acquire_gemini(cooldown_scope="gemini-3.7-flash")
        mark_cooldown(first.id, scope="gemini-3.7-flash")
        second = acquire_gemini(cooldown_scope="gemini-3.7-flash")
        assert second.api_key == "g2"


@pytest.mark.asyncio
class TestGeminiProviderKeyFallback:
    async def test_gemini_retries_next_key_on_429(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")

        ok_payload = {
            "candidates": [
                {"content": {"parts": [{"text": '{"suggestions":[],"overallComment":"ok"}'}]}}
            ]
        }
        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _FakeResponse(status_code=429, text="rate"),
            _FakeResponse(status_code=200, payload=ok_payload),
        ]
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            result = await call_gemini([{"role": "user", "content": "hi"}])

        assert "overallComment" in result
        assert mock_client.post.call_count == 2
        keys = [
            c.kwargs["headers"]["x-goog-api-key"]
            for c in mock_client.post.call_args_list
        ]
        assert keys == ["key-a", "key-b"]

    async def test_gemini_exhausts_pool_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "key-a,key-b")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")

        mock_client = AsyncMock()
        mock_client.post.return_value = _FakeResponse(status_code=429, text="rate")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("app.llm.gemini_provider.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(GeminiRateLimitError) as exc_info:
                await call_gemini([{"role": "user", "content": "hi"}])

        assert mock_client.post.call_count == 2
        assert "pool_size=2" in str(exc_info.value)
