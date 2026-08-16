"""Tests for the shared editable correction prompt (/settings/prompt)."""

import asyncio
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app import db_helper, prompt_settings
from app.llm.prompts import SYSTEM_PROMPT_BODY
from app.llm import provider_health
from app.llm.provider_health import load_shared_state
from app.prompt_settings import (
    MAX_PROMPT_LENGTH,
    PromptValidationError,
    SETTING_KEY,
    prompt_override_from_row,
    validate_prompt,
)

TEST_JWT_SECRET = "test-secret-value"
ALLOWED_EMAIL = "owner@example.com"


def make_token(email: str = ALLOWED_EMAIL) -> str:
    now = int(time.time())
    return jwt.encode(
        {"email": email, "aud": "authenticated", "iat": now, "exp": now + 3600},
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("ALLOWED_USER_EMAIL", ALLOWED_EMAIL)
    monkeypatch.setenv("ALLOWED_USER_EMAILS", ALLOWED_EMAIL)

    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


class _FakeStore:
    """In-memory stand-in for the app_settings table."""

    def __init__(self):
        self.rows = {}
        self.deleted = []

    async def fetch_setting(self, key):
        return self.rows.get(key)

    async def upsert_setting(self, key, value, updated_by=None):
        row = {
            "settingKey": key,
            "settingValue": value,
            "updatedAt": "2026-08-16T07:00:00+00:00",
            "updatedBy": updated_by,
        }
        self.rows[key] = row
        return row

    async def delete_setting(self, key):
        self.deleted.append(key)
        self.rows.pop(key, None)


@pytest.fixture
def store(monkeypatch):
    fake = _FakeStore()
    monkeypatch.setattr(prompt_settings, "fetch_setting", fake.fetch_setting)
    monkeypatch.setattr(prompt_settings, "upsert_setting", fake.upsert_setting)
    monkeypatch.setattr(prompt_settings, "delete_setting", fake.delete_setting)
    return fake


class TestValidation:
    def test_trims_and_accepts_ordinary_prompt(self):
        assert validate_prompt("  规则正文  ") == "规则正文"

    def test_rejects_empty_and_whitespace_only(self):
        for bad in ("", "   ", "\n\t "):
            with pytest.raises(PromptValidationError):
                validate_prompt(bad)

    def test_rejects_over_length_and_states_the_limit(self):
        with pytest.raises(PromptValidationError) as exc:
            validate_prompt("あ" * (MAX_PROMPT_LENGTH + 1))
        assert str(MAX_PROMPT_LENGTH) in str(exc.value)

    def test_accepts_exactly_the_limit(self):
        assert len(validate_prompt("あ" * MAX_PROMPT_LENGTH)) == MAX_PROMPT_LENGTH

    def test_rejects_non_string(self):
        with pytest.raises(PromptValidationError):
            validate_prompt(None)


class TestReadEndpoint:
    def test_returns_builtin_default_when_no_row_stored(
        self, client, auth_headers, store
    ):
        response = client.get("/settings/prompt", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["systemPrompt"] == SYSTEM_PROMPT_BODY
        assert body["defaultSystemPrompt"] == SYSTEM_PROMPT_BODY
        assert body["isCustomized"] is False
        assert body["updatedAt"] is None
        assert body["updatedBy"] is None

    def test_returns_stored_prompt_with_attribution(
        self, client, auth_headers, store
    ):
        store.rows[SETTING_KEY] = {
            "settingKey": SETTING_KEY,
            "settingValue": "自定义规则",
            "updatedAt": "2026-08-16T07:00:00+00:00",
            "updatedBy": ALLOWED_EMAIL,
        }
        body = client.get("/settings/prompt", headers=auth_headers).json()
        assert body["systemPrompt"] == "自定义规则"
        assert body["defaultSystemPrompt"] == SYSTEM_PROMPT_BODY
        assert body["isCustomized"] is True
        assert body["updatedBy"] == ALLOWED_EMAIL
        assert body["updatedAt"] == "2026-08-16T07:00:00+00:00"

    def test_store_failure_serves_the_default_instead_of_erroring(
        self, client, auth_headers, monkeypatch
    ):
        async def boom(_key):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(prompt_settings, "fetch_setting", boom)
        response = client.get("/settings/prompt", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["isCustomized"] is False


class TestWriteEndpoints:
    def test_save_then_read_round_trip_attributes_the_caller(
        self, client, auth_headers, store
    ):
        saved = client.put(
            "/settings/prompt",
            json={"systemPrompt": "  自定义规则正文  "},
            headers=auth_headers,
        )
        assert saved.status_code == 200
        assert saved.json()["systemPrompt"] == "自定义规则正文"
        assert saved.json()["isCustomized"] is True
        assert saved.json()["updatedBy"] == ALLOWED_EMAIL

        reread = client.get("/settings/prompt", headers=auth_headers).json()
        assert reread["systemPrompt"] == "自定义规则正文"

    def test_empty_prompt_is_rejected_with_a_reason(
        self, client, auth_headers, store
    ):
        response = client.put(
            "/settings/prompt", json={"systemPrompt": "   "}, headers=auth_headers
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"]
        assert SETTING_KEY not in store.rows

    def test_oversized_prompt_is_rejected_stating_the_limit(
        self, client, auth_headers, store
    ):
        response = client.put(
            "/settings/prompt",
            json={"systemPrompt": "あ" * (MAX_PROMPT_LENGTH + 1)},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert str(MAX_PROMPT_LENGTH) in response.json()["detail"]
        assert SETTING_KEY not in store.rows

    def test_reset_deletes_the_row_and_reports_the_default(
        self, client, auth_headers, store
    ):
        store.rows[SETTING_KEY] = {
            "settingKey": SETTING_KEY,
            "settingValue": "自定义规则",
            "updatedAt": "2026-08-16T07:00:00+00:00",
            "updatedBy": ALLOWED_EMAIL,
        }
        body = client.delete("/settings/prompt", headers=auth_headers).json()
        assert body["systemPrompt"] == SYSTEM_PROMPT_BODY
        assert body["isCustomized"] is False
        assert store.deleted == [SETTING_KEY]

    def test_reset_is_idempotent_when_nothing_is_stored(
        self, client, auth_headers, store
    ):
        first = client.delete("/settings/prompt", headers=auth_headers)
        second = client.delete("/settings/prompt", headers=auth_headers)
        assert first.status_code == second.status_code == 200
        assert second.json()["isCustomized"] is False


class TestAuthorization:
    def test_unauthenticated_requests_are_rejected(self, client, store):
        assert client.get("/settings/prompt").status_code == 401
        assert client.put("/settings/prompt", json={"systemPrompt": "x"}).status_code == 401
        assert client.delete("/settings/prompt").status_code == 401

    def test_non_allow_listed_email_is_forbidden(self, client, store):
        headers = {"Authorization": f"Bearer {make_token('intruder@example.com')}"}
        assert client.get("/settings/prompt", headers=headers).status_code == 403
        assert client.put(
            "/settings/prompt", json={"systemPrompt": "x"}, headers=headers
        ).status_code == 403

    def test_routes_are_also_served_under_the_vercel_api_prefix(
        self, client, auth_headers, store
    ):
        assert client.get("/api/settings/prompt", headers=auth_headers).status_code == 200


class TestGenerationPathResolution:
    """Reading the stored prompt must never break generation."""

    def _resolve(self):
        row, _health = asyncio.run(load_shared_state(SETTING_KEY))
        return prompt_override_from_row(row)

    @pytest.fixture
    def shared_read(self, monkeypatch):
        """Stand in for the one combined read the generation path performs."""
        state = {"setting": None, "health": [], "error": None, "delay": 0.0}

        async def fake(_key):
            if state["delay"]:
                await asyncio.sleep(state["delay"])
            if state["error"]:
                raise state["error"]
            return state["setting"], state["health"]

        monkeypatch.setattr(db_helper, "fetch_setting_and_provider_health", fake)
        return state

    def test_returns_none_when_nothing_stored(self, shared_read):
        assert self._resolve() is None

    def test_returns_stored_body(self, shared_read):
        shared_read["setting"] = {
            "settingKey": SETTING_KEY,
            "settingValue": "自定义规则",
            "updatedAt": None,
            "updatedBy": None,
        }
        assert self._resolve() == "自定义规则"

    def test_blank_stored_value_falls_back_to_default(self, shared_read):
        shared_read["setting"] = {
            "settingKey": SETTING_KEY,
            "settingValue": "   ",
            "updatedAt": None,
            "updatedBy": None,
        }
        assert self._resolve() is None

    def test_store_error_falls_back_to_default(self, shared_read):
        shared_read["error"] = RuntimeError("connection refused")
        assert self._resolve() is None

    def test_slow_store_times_out_instead_of_eating_the_wall_clock(
        self, shared_read, monkeypatch
    ):
        shared_read["delay"] = 10
        monkeypatch.setattr(provider_health, "SHARED_STATE_TIMEOUT_S", 0.01)
        assert self._resolve() is None


class TestSettingsStoreQueries:
    """db_helper settings CRUD hits app_settings with the expected SQL."""

    class _Conn:
        def __init__(self):
            self.executed = []
            self.row = None

        async def execute(self, query, *params):
            self.executed.append((query, params))

        async def fetchrow(self, query, *params):
            self.executed.append((query, params))
            return self.row

    class _Ctx:
        def __init__(self, conn):
            self._conn = conn

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, *exc):
            return False

    @pytest.fixture
    def conn(self, monkeypatch):
        conn = self._Conn()
        monkeypatch.setattr(db_helper, "get_db", lambda: self._Ctx(conn))
        return conn

    def test_fetch_setting_selects_camel_cased_columns(self, conn):
        conn.row = {
            "settingKey": SETTING_KEY,
            "settingValue": "v",
            "updatedAt": None,
            "updatedBy": None,
        }
        result = asyncio.run(db_helper.fetch_setting(SETTING_KEY))
        assert result["settingValue"] == "v"
        query, params = conn.executed[0]
        assert "FROM app_settings" in query
        assert params == (SETTING_KEY,)

    def test_upsert_setting_replaces_value_and_stamps_editor(self, conn):
        conn.row = {
            "settingKey": SETTING_KEY,
            "settingValue": "v",
            "updatedAt": None,
            "updatedBy": ALLOWED_EMAIL,
        }
        asyncio.run(db_helper.upsert_setting(SETTING_KEY, "v", ALLOWED_EMAIL))
        query, params = conn.executed[0]
        assert "INSERT INTO app_settings" in query
        assert "ON CONFLICT (setting_key) DO UPDATE" in query
        assert params == (SETTING_KEY, "v", ALLOWED_EMAIL)

    def test_delete_setting_removes_the_row(self, conn):
        asyncio.run(db_helper.delete_setting(SETTING_KEY))
        query, params = conn.executed[0]
        assert "DELETE FROM app_settings" in query
        assert params == (SETTING_KEY,)
