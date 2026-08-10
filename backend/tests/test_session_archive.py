"""Tests for session archive (soft-delete) functionality.

These tests verify that:
1. Archiving a session hides it from GET /sessions list
2. Archived session's histories and proposals remain intact
"""

import time
from unittest.mock import AsyncMock, patch

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


class TestSessionArchive:
    """Test session archive functionality."""

    @patch("app.main.db_delete_session")
    async def test_delete_endpoint_archives_session(self, mock_delete, client, auth_headers):
        """DELETE /sessions/{id} should archive (not hard-delete) the session."""
        mock_delete.return_value = None
        
        response = client.delete("/sessions/test-session-id", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session archived"
        assert data["sessionId"] == "test-session-id"
        mock_delete.assert_called_once_with("test-session-id")

    @patch("app.main.fetch_sessions")
    async def test_get_sessions_excludes_archived(self, mock_fetch, client, auth_headers):
        """GET /sessions should only return active (non-archived) sessions."""
        mock_fetch.return_value = [
            {
                "sessionId": "active-session-1",
                "name": "Active Session",
                "createdAt": "2024-01-01 00:00:00",
                "updatedAt": "2024-01-01 00:00:00",
                "correctionCount": 5
            }
        ]
        
        response = client.get("/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 1
        assert sessions[0]["sessionId"] == "active-session-1"


class TestArchivePreservesData:
    """Test that archiving preserves related data."""

    def test_delete_session_db_helper_uses_update_not_delete(self):
        """Verify delete_session() in db_helper uses UPDATE, not DELETE."""
        import inspect
        from app.db_helper import delete_session
        
        source = inspect.getsource(delete_session)
        assert "UPDATE sessions SET status" in source
        assert "DELETE FROM sessions" not in source
        assert "DELETE FROM correction_histories" not in source
        assert "DELETE FROM ai_proposals" not in source

    def test_fetch_sessions_filters_by_status(self):
        """Verify fetch_sessions() filters by status in SQL query."""
        import inspect
        from app.db_helper import fetch_sessions
        
        source = inspect.getsource(fetch_sessions)
        assert "status = 'active'" in source or "status IS NULL" in source
