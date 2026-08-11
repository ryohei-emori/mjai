"""Regression tests for proposal endpoints on the PostgreSQL path.

Previously, the PostgreSQL `ai_proposals` table had a thin legacy schema
(`proposal_text`, `confidence_score`) that didn't match the application's full
proposal model used by SQLite. The `insert_proposal()` function tried to access
keys like `proposal_id`, `proposal_text` which weren't in the camelCase proposal
dict from main.py, causing KeyError.

After the fix:
1. The PostgreSQL schema was migrated to match the full proposal model
2. `insert_proposal()` accepts camelCase keys and maps them to snake_case columns
3. `fetch_proposals_by_history()` uses column aliases to return camelCase keys
"""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app import db_helper

TEST_JWT_SECRET = "test-secret-value"
ALLOWED_EMAIL = "owner@example.com"


def make_token(email: str = ALLOWED_EMAIL) -> str:
    now = int(time.time())
    payload = {
        "email": email,
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("ALLOWED_USER_EMAIL", ALLOWED_EMAIL)
    # auth.py prefers ALLOWED_USER_EMAILS when set (e.g. from conf/.env in Docker)
    monkeypatch.setenv("ALLOWED_USER_EMAILS", ALLOWED_EMAIL)
    monkeypatch.setenv("USE_POSTGRESQL", "true")

    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


class _FakeRecord(dict):
    """Fake asyncpg Record that behaves like a dict."""
    pass


class _FakeConnection:
    """Fake asyncpg connection recording executed queries/params.

    Mimics real asyncpg's strict type checking for BOOLEAN columns: passing a
    Python `int` (e.g. 0/1) instead of an actual `bool` raises an error, just
    like `asyncpg.exceptions.DataError` does against a real Postgres
    connection. Without this, a mock that accepts anything would hide the
    real production bug where `insert_proposal()` forwarded raw 0/1 ints for
    the `is_selected`/`is_modified`/`is_custom` BOOLEAN columns.
    """

    # Positional index (0-based) of the is_selected/is_modified/is_custom
    # params in the `INSERT INTO ai_proposals (...)` call in db_helper.py.
    _AI_PROPOSALS_BOOL_PARAM_INDICES = (7, 8, 9)

    def __init__(self):
        self.executed = []
        self.fetch_result = []

    async def execute(self, query, *params):
        self.executed.append((query, params))
        if "INSERT INTO ai_proposals" in query:
            for idx in self._AI_PROPOSALS_BOOL_PARAM_INDICES:
                if idx < len(params) and not isinstance(params[idx], bool):
                    raise TypeError(
                        f"invalid input for query argument ${idx + 1}: "
                        f"{params[idx]!r} (a boolean is required (got type "
                        f"{type(params[idx]).__name__}))"
                    )
        return "INSERT 0 1"

    async def fetch(self, query, *params):
        self.executed.append((query, params))
        return self.fetch_result


class _FakeDbContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def fake_pg_connection(monkeypatch):
    """Swap `db_helper.get_db()` for a fake asyncpg connection."""
    conn = _FakeConnection()
    monkeypatch.setattr(db_helper, "get_db", lambda: _FakeDbContext(conn))
    return conn


def test_create_proposal_postgres_path_does_not_raise_key_error(client, auth_headers, fake_pg_connection):
    """Test POST /proposals works on PostgreSQL path with camelCase keys.
    
    Previously, insert_proposal() tried to access keys like `proposal_id`, `proposal_text`
    which weren't in the camelCase proposal dict from main.py, causing KeyError.
    After the fix, insert_proposal() correctly maps camelCase keys to snake_case columns.
    """
    payload = {
        "historyId": "test-history-id",
        "type": "AI",
        "originalAfterText": "corrected text",
        "originalReason": "grammar fix",
        "isSelected": 1,
        "isModified": 0,
    }

    response = client.post("/proposals", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["historyId"] == "test-history-id"
    assert body["type"] == "AI"
    assert body["originalAfterText"] == "corrected text"
    assert body.get("proposalId")  # Should have generated UUID

    # Verify the INSERT was executed with correct snake_case columns
    assert len(fake_pg_connection.executed) == 1
    query, params = fake_pg_connection.executed[0]
    assert "INSERT INTO ai_proposals" in query
    # Check the columns are the new snake_case ones
    assert "proposal_id" in query
    assert "history_id" in query
    assert "type" in query
    assert "original_after_text" in query
    assert "original_reason" in query
    assert "is_selected" in query
    # Old columns should NOT be present
    assert "proposal_text" not in query
    assert "confidence_score" not in query


def test_create_proposal_generates_uuid_when_missing(client, auth_headers, fake_pg_connection):
    """Test POST /proposals generates proposalId when not provided."""
    payload = {
        "historyId": "test-history-id",
        "type": "Custom",
        "originalAfterText": "custom correction",
    }

    response = client.post("/proposals", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body.get("proposalId")
    assert len(body["proposalId"]) == 36  # UUID format


def test_get_proposals_postgres_path_returns_camel_case_keys(client, auth_headers, fake_pg_connection):
    """Test GET /histories/{history_id}/proposals returns camelCase keys on PostgreSQL path.
    
    After the fix, fetch_proposals_by_history() uses column aliases to return
    camelCase keys matching the application model.
    """
    # Simulate proposals returned with camelCase keys (after our fix applies aliases)
    fake_pg_connection.fetch_result = [
        _FakeRecord({
            "proposalId": "proposal-1",
            "historyId": "test-history-id",
            "type": "AI",
            "originalAfterText": "corrected text 1",
            "originalReason": "fix 1",
            "modifiedAfterText": None,
            "modifiedReason": None,
            "isSelected": 1,
            "isModified": 0,
            "isCustom": 0,
            "selectedOrder": 1,
            "createdAt": "2026-08-11 10:00:00.000",
        }),
        _FakeRecord({
            "proposalId": "proposal-2",
            "historyId": "test-history-id",
            "type": "AI",
            "originalAfterText": "corrected text 2",
            "originalReason": "fix 2",
            "modifiedAfterText": None,
            "modifiedReason": None,
            "isSelected": 0,
            "isModified": 0,
            "isCustom": 0,
            "selectedOrder": None,
            "createdAt": "2026-08-11 10:01:00.000",
        }),
    ]

    response = client.get("/histories/test-history-id/proposals", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    
    # Check first proposal has camelCase keys
    assert body[0]["proposalId"] == "proposal-1"
    assert body[0]["historyId"] == "test-history-id"
    assert body[0]["type"] == "AI"
    assert body[0]["originalAfterText"] == "corrected text 1"
    assert body[0]["isSelected"] == 1
    assert body[0]["selectedOrder"] == 1


def test_get_proposals_empty_result(client, auth_headers, fake_pg_connection):
    """Test GET /histories/{history_id}/proposals returns empty array when no proposals."""
    fake_pg_connection.fetch_result = []

    response = client.get("/histories/nonexistent-history/proposals", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_create_selected_proposal_does_not_crash_on_boolean_columns(client, auth_headers, fake_pg_connection):
    """Regression test: POST /proposals with isSelected=1 (int) must not 500.

    Root cause: `insert_proposal()` forwarded `suggestion.selected ? 1 : 0`
    (a Python int, per the old frontend contract) directly as the asyncpg
    bind parameter for the `is_selected` BOOLEAN column. Real asyncpg raises
    `asyncpg.exceptions.DataError: ... (a boolean is required (got type
    int))` for this, which aborts the whole INSERT — meaning every proposal
    a user actually selects (required for the "3+ selected" HITL save flow)
    failed to persist, while unselected proposals (which happened to coerce
    to `False` via the old `x or False` fallback) saved fine.

    This test's fake connection enforces the same strict boolean typing as
    real asyncpg, so this only passes once `insert_proposal()` coerces
    isSelected/isModified/isCustom to real `bool` before binding.
    """
    payload = {
        "historyId": "test-history-id",
        "type": "AI",
        "originalAfterText": "corrected text",
        "originalReason": "grammar fix",
        "isSelected": 1,
        "isModified": 0,
        "isCustom": 0,
        "selectedOrder": 1,
    }

    response = client.post("/proposals", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["isSelected"] is True
    assert body["isModified"] is False
    assert body["isCustom"] is False

    # Verify the bound params really are Python bool, not int.
    _, params = fake_pg_connection.executed[0]
    assert params[7] is True
    assert params[8] is False
    assert params[9] is False


def test_create_proposal_preserves_empty_string_content_fields(client, auth_headers, fake_pg_connection):
    """Regression test: empty-string content fields must not be nulled out.

    Root cause: `insert_proposal()` picked between the camelCase and
    snake_case variant of a field with `proposal.get('originalAfterText') or
    proposal.get('original_after_text')`. Because `or` treats an empty
    string as falsy, a legitimately-empty (but present) `originalAfterText`
    fell through to the snake_case fallback key, which is never populated by
    `main.py` and is therefore `None` — silently turning "" into NULL in the
    database instead of preserving the empty string.
    """
    payload = {
        "historyId": "test-history-id",
        "type": "AI",
        "originalAfterText": "",
        "originalReason": "",
        "modifiedAfterText": "",
        "modifiedReason": "",
        "isSelected": 1,
    }

    response = client.post("/proposals", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["originalAfterText"] == ""
    assert body["originalReason"] == ""
    assert body["modifiedAfterText"] == ""
    assert body["modifiedReason"] == ""


def test_insert_proposal_accepts_snake_case_keys_with_boolean_flags():
    """`insert_proposal()` should also accept snake_case input keys (used
    internally/by scripts) and still coerce boolean-like flags correctly."""
    import asyncio

    from app import db_helper as _db_helper

    conn = _FakeConnection()

    class _Ctx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *exc):
            return False

    original_get_db = _db_helper.get_db
    _db_helper.get_db = lambda: _Ctx()
    try:
        result = asyncio.run(
            _db_helper.insert_proposal(
                {
                    "proposal_id": "p1",
                    "history_id": "h1",
                    "type": "Custom",
                    "original_after_text": "text",
                    "is_selected": 1,
                    "is_custom": 1,
                }
            )
        )
    finally:
        _db_helper.get_db = original_get_db

    assert result["isSelected"] is True
    assert result["isCustom"] is True
    assert result["isModified"] is False
    assert result["originalAfterText"] == "text"
