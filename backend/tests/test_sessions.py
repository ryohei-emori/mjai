"""Regression tests for POST /sessions on the PostgreSQL path.

Previously, `create_session()` in `backend/app/main.py` built the session dict
with camelCase keys (`sessionId`, `createdAt`, ...), while
`backend/app/db_helper.py`'s async `insert_session()` reads snake_case keys
(`session_id`, `created_at`, ...) matching the Postgres schema's snake_case
columns. Since `USE_POSTGRESQL` defaults to `"true"`, this mismatch raised a
`KeyError` inside `insert_session()` on every session creation, which was then
re-raised (Postgres failures do not silently fall back to SQLite when
`USE_POSTGRESQL=true`).

These tests exercise the real `insert_session()` implementation (only the
underlying `asyncpg` connection is faked) so a reintroduced key mismatch would
surface here exactly as it would against a real Postgres connection.
"""

import time
from datetime import datetime

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
    """Fake asyncpg connection recording executed queries/params."""

    def __init__(self):
        self.executed = []
        self.fetchrow_result = None

    async def execute(self, query, *params):
        self.executed.append((query, params))
        return "INSERT 0 1"

    async def fetchrow(self, query, *params):
        self.executed.append((query, params))
        return self.fetchrow_result


class _FakeDbContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def fake_pg_connection(monkeypatch):
    """Swap `db_helper.get_db()` for a fake asyncpg connection.

    This runs the *real* `insert_session()` body (not a mock of the route),
    so a key-name mismatch between main.py's payload and db_helper.py's
    column access raises a real KeyError here, just as it would against a
    real Postgres connection.
    """
    conn = _FakeConnection()
    monkeypatch.setattr(db_helper, "get_db", lambda: _FakeDbContext(conn))
    return conn


def test_create_session_postgres_path_does_not_raise_key_error(client, auth_headers, fake_pg_connection):
    response = client.post("/sessions", json={"name": "Test Session"}, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    # frontend/src/app/page.tsx::createNewSession reads these camelCase fields
    # off the response, so the route must return them even on the Postgres path.
    assert body["name"] == "Test Session"
    assert body.get("sessionId")
    assert body.get("createdAt")

    # insert_session() should have issued exactly one INSERT against the
    # sessions table's real (snake_case) columns.
    assert len(fake_pg_connection.executed) == 1
    query, params = fake_pg_connection.executed[0]
    assert "INSERT INTO sessions" in query
    session_id, created_at, updated_at, name, correction_count, is_open = params
    assert session_id == body["sessionId"]
    assert isinstance(created_at, datetime)
    assert isinstance(updated_at, datetime)
    assert name == "Test Session"
    assert correction_count == 0
    assert is_open is True


def test_create_session_uses_default_name_when_missing(client, auth_headers, fake_pg_connection):
    response = client.post("/sessions", json={}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "セッション"


def test_get_session_postgres_path_returns_camel_case_keys(client, auth_headers, fake_pg_connection):
    """Test GET /sessions/{session_id} returns camelCase keys on PostgreSQL path.
    
    Previously, fetch_session() used SELECT * which returned snake_case columns,
    but main.py tried to read camelCase keys, causing KeyError. After the fix,
    fetch_session() uses column aliases to return camelCase keys.
    """
    # SELECT * returns snake_case columns; fetch_session() maps them to camelCase
    fake_pg_connection.fetchrow_result = _FakeRecord({
        "session_id": "test-session-id",
        "name": "Test Session",
        "created_at": "2026-08-11 10:00:00.000",
        "updated_at": "2026-08-11 10:00:00.000",
        "correction_count": 5,
        "is_open": True,
        "status": "active",
    })

    response = client.get("/sessions/test-session-id", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["sessionId"] == "test-session-id"
    assert body["name"] == "Test Session"
    assert body["createdAt"] == "2026-08-11 10:00:00.000"
    assert body["correctionCount"] == 5


def test_get_session_not_found(client, auth_headers, fake_pg_connection):
    """Test GET /sessions/{session_id} returns error for non-existent session."""
    fake_pg_connection.fetchrow_result = None

    response = client.get("/sessions/nonexistent-id", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "Session not found"
    assert body["sessionId"] == "nonexistent-id"


def test_update_session_postgres_path_maps_camel_case_to_snake_case(client, auth_headers, fake_pg_connection):
    """Test PUT /sessions/{session_id} correctly maps camelCase fields on PostgreSQL path.
    
    Previously, the PostgreSQL path's allow-list used snake_case field names only,
    so camelCase fields from clients were silently ignored. After the fix,
    update_session() maps camelCase keys to snake_case before checking the allow-list.
    """
    response = client.put(
        "/sessions/test-session-id",
        json={"name": "Updated Name", "correctionCount": 10, "isOpen": False},
        headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Session updated"
    assert body["sessionId"] == "test-session-id"

    # Verify the UPDATE query was executed with mapped snake_case columns
    assert len(fake_pg_connection.executed) == 1
    query, params = fake_pg_connection.executed[0]
    assert "UPDATE sessions SET" in query
    # The order depends on dict iteration, but all fields should be present
    assert "name =" in query
    assert "correction_count =" in query
    assert "is_open =" in query
    # Check params contain the values
    assert "Updated Name" in params
    assert 10 in params
    assert False in params
