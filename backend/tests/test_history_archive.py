"""Tests for history round archive (soft-delete) functionality.

Mirrors test_session_archive.py's pattern for the analogous
correction_histories soft-delete: archiving a "添削データ" round
(a single correction_histories row) should hide it from
GET /sessions/{session_id}/histories without hard-deleting it (and
therefore without cascading to its ai_proposals rows).
"""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

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
    monkeypatch.setenv("ALLOWED_USER_EMAILS", ALLOWED_EMAIL)
    monkeypatch.setenv("USE_POSTGRESQL", "true")

    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


class TestHistoryArchive:
    """Test history round archive functionality."""

    def test_delete_endpoint_archives_history(self, client, auth_headers, monkeypatch):
        """DELETE /histories/{id} should archive (not hard-delete) the history round."""
        calls = []

        async def fake_archive_history(history_id):
            calls.append(history_id)

        import app.main as main_module
        monkeypatch.setattr(main_module, "db_archive_history", fake_archive_history)

        response = client.delete("/histories/test-history-id", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "History archived"
        assert data["historyId"] == "test-history-id"
        assert calls == ["test-history-id"]

    def test_get_histories_excludes_archived(self, client, auth_headers, monkeypatch):
        """GET /sessions/{id}/histories should only return non-archived rounds."""
        async def fake_fetch_histories_by_session(session_id):
            return [
                {
                    "historyId": "active-history-1",
                    "sessionId": session_id,
                    "originalText": "original",
                    "targetText": "target",
                }
            ]

        import app.main as main_module
        monkeypatch.setattr(main_module, "fetch_histories_by_session", fake_fetch_histories_by_session)

        response = client.get("/sessions/test-session-id/histories", headers=auth_headers)

        assert response.status_code == 200
        histories = response.json()
        assert len(histories) == 1
        assert histories[0]["historyId"] == "active-history-1"


class TestHistoryArchivePreservesData:
    """Test that archiving a history round preserves related ai_proposals data."""

    def test_archive_history_db_helper_uses_update_not_delete(self):
        """Verify archive_history() in db_helper uses UPDATE, not DELETE."""
        import inspect
        from app.db_helper import archive_history

        source = inspect.getsource(archive_history)
        assert "UPDATE correction_histories SET is_archived" in source
        assert "DELETE FROM correction_histories" not in source
        assert "DELETE FROM ai_proposals" not in source

    def test_fetch_histories_by_session_filters_by_is_archived(self):
        """Verify fetch_histories_by_session() filters by is_archived in SQL query."""
        import inspect
        from app.db_helper import fetch_histories_by_session

        source = inspect.getsource(fetch_histories_by_session)
        assert "is_archived = false" in source
