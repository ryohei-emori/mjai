"""Tests for pending suggestion histories (persist-on-generation)."""

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
    monkeypatch.setenv("ALLOWED_USER_EMAILS", ALLOWED_EMAIL)
    monkeypatch.setenv("USE_POSTGRESQL", "true")

    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


class _FakeRecord(dict):
    pass


class _FakeConnection:
    def __init__(self):
        self.executed = []
        self.fetch_result = []
        self.fetchrow_result = None

    async def execute(self, query, *params):
        self.executed.append((query, params))
        return "INSERT 0 1"

    async def fetch(self, query, *params):
        self.executed.append((query, params))
        return self.fetch_result

    async def fetchrow(self, query, *params):
        self.executed.append((query, params))
        if self.fetchrow_result is not None:
            return self.fetchrow_result
        if self.fetch_result:
            return self.fetch_result[0]
        return None


class _FakeDbContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def fake_pg_connection(monkeypatch):
    conn = _FakeConnection()
    monkeypatch.setattr(db_helper, "get_db", lambda: _FakeDbContext(conn))
    return conn


def test_create_pending_history_persists_status_and_restore_fields(
    client, auth_headers, fake_pg_connection
):
    payload = {
        "sessionId": "sess-1",
        "originalText": "原文",
        "targetText": "訳文",
        "status": "pending",
        "overallComment": "整体评价",
        "provider": "api",
        "clientJobId": "job-123",
        "combinedComment": "整体评价",
    }

    response = client.post("/histories", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["overallComment"] == "整体评价"
    assert body["provider"] == "api"
    assert body["clientJobId"] == "job-123"
    assert body["historyId"]

    query, params = fake_pg_connection.executed[0]
    assert "INSERT INTO correction_histories" in query
    assert "status" in query
    assert "overall_comment" in query
    assert "pending" in params
    assert "api" in params
    assert "job-123" in params


def test_create_history_defaults_status_confirmed(
    client, auth_headers, fake_pg_connection
):
    payload = {
        "sessionId": "sess-1",
        "originalText": "原文",
        "targetText": "訳文",
        "combinedComment": "comment",
    }
    response = client.post("/histories", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    _, params = fake_pg_connection.executed[0]
    assert "confirmed" in params


def test_put_history_promotes_pending_to_confirmed(
    client, auth_headers, fake_pg_connection
):
    fake_pg_connection.fetchrow_result = _FakeRecord({
        "historyId": "hist-1",
        "sessionId": "sess-1",
        "timestamp": datetime(2026, 8, 14, 1, 0, 0),
        "originalText": "原文",
        "instructionPrompt": None,
        "targetText": "訳文",
        "combinedComment": "final",
        "selectedProposalIds": '["a"]',
        "customProposals": None,
        "status": "confirmed",
        "overallComment": "整体评价",
        "provider": "api",
        "clientJobId": "job-123",
    })

    response = client.put(
        "/histories/hist-1",
        json={
            "status": "confirmed",
            "combinedComment": "final",
            "selectedProposalIds": '["a"]',
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["historyId"] == "hist-1"
    query, _ = fake_pg_connection.executed[0]
    assert "UPDATE correction_histories" in query


def test_put_history_not_found(client, auth_headers, fake_pg_connection):
    fake_pg_connection.fetchrow_result = None
    response = client.put(
        "/histories/missing",
        json={"status": "confirmed"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_put_proposal_updates_selection(client, auth_headers, fake_pg_connection):
    fake_pg_connection.fetchrow_result = _FakeRecord({
        "proposalId": "prop-1",
        "historyId": "hist-1",
        "type": "AI",
        "originalAfterText": "指摘",
        "originalReason": "理由",
        "modifiedAfterText": "指摘",
        "modifiedReason": "編集後",
        "isSelected": True,
        "isModified": True,
        "isCustom": False,
        "selectedOrder": 1,
        "createdAt": datetime(2026, 8, 14, 1, 0, 0),
    })

    response = client.put(
        "/proposals/prop-1",
        json={
            "isSelected": True,
            "isModified": True,
            "modifiedReason": "編集後",
            "selectedOrder": 1,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["proposalId"] == "prop-1"
    assert body["isSelected"] is True
    query, params = fake_pg_connection.executed[0]
    assert "UPDATE ai_proposals" in query
    assert True in params


def test_list_histories_includes_pending_fields(
    client, auth_headers, fake_pg_connection
):
    fake_pg_connection.fetch_result = [
        _FakeRecord({
            "historyId": "hist-pending",
            "sessionId": "sess-1",
            "timestamp": datetime(2026, 8, 14, 1, 0, 0),
            "originalText": "原文",
            "instructionPrompt": None,
            "targetText": "訳文",
            "combinedComment": "整体评价",
            "selectedProposalIds": None,
            "customProposals": None,
            "status": "pending",
            "overallComment": "整体评价",
            "provider": "webllm",
            "clientJobId": "job-9",
        })
    ]

    response = client.get("/sessions/sess-1/histories", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"
    assert body[0]["provider"] == "webllm"
    assert body[0]["clientJobId"] == "job-9"
    assert body[0]["overallComment"] == "整体评价"


def test_create_history_persists_llm_provenance(
    client, auth_headers, fake_pg_connection
):
    """Which model produced a round is logged alongside the transport."""
    payload = {
        "sessionId": "sess-1",
        "originalText": "原文",
        "targetText": "訳文",
        "status": "pending",
        "provider": "api",
        "llmProvider": "gemini",
        "llmModel": "gemini-3.7-flash",
    }

    response = client.post("/histories", json=payload, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "api"
    assert body["llmProvider"] == "gemini"
    assert body["llmModel"] == "gemini-3.7-flash"

    query, params = fake_pg_connection.executed[0]
    assert "llm_provider" in query
    assert "llm_model" in query
    assert "gemini" in params
    assert "gemini-3.7-flash" in params


def test_create_history_without_provenance_stores_nulls(
    client, auth_headers, fake_pg_connection
):
    payload = {
        "sessionId": "sess-1",
        "originalText": "原文",
        "targetText": "訳文",
    }
    response = client.post("/histories", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["llmProvider"] is None
    assert response.json()["llmModel"] is None


def test_put_history_without_provenance_keys_leaves_them_untouched(
    client, auth_headers, fake_pg_connection
):
    """Confirming a pending round must not wipe the generating model."""
    fake_pg_connection.fetchrow_result = _FakeRecord({
        "historyId": "hist-1",
        "sessionId": "sess-1",
        "timestamp": datetime(2026, 8, 16, 1, 0, 0),
        "originalText": "原文",
        "instructionPrompt": None,
        "targetText": "訳文",
        "combinedComment": "final",
        "selectedProposalIds": '["a"]',
        "customProposals": None,
        "status": "confirmed",
        "overallComment": "整体评价",
        "provider": "api",
        "llmProvider": "groq",
        "llmModel": "openai/gpt-oss-120b",
        "clientJobId": "job-123",
    })

    response = client.put(
        "/histories/hist-1",
        json={"status": "confirmed", "combinedComment": "final"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["llmModel"] == "openai/gpt-oss-120b"
    query, _ = fake_pg_connection.executed[0]
    assert "llm_model =" not in query
    assert 'llm_model AS "llmModel"' in query


def test_list_histories_returns_stored_provenance(
    client, auth_headers, fake_pg_connection
):
    fake_pg_connection.fetch_result = [
        _FakeRecord({
            "historyId": "hist-1",
            "sessionId": "sess-1",
            "timestamp": datetime(2026, 8, 16, 1, 0, 0),
            "originalText": "原文",
            "instructionPrompt": None,
            "targetText": "訳文",
            "combinedComment": "整体评价",
            "selectedProposalIds": None,
            "customProposals": None,
            "status": "confirmed",
            "overallComment": "整体评价",
            "provider": "api",
            "llmProvider": "gemini",
            "llmModel": "gemini-3.6-flash",
            "clientJobId": "job-9",
        })
    ]

    body = client.get("/sessions/sess-1/histories", headers=auth_headers).json()
    assert body[0]["llmProvider"] == "gemini"
    assert body[0]["llmModel"] == "gemini-3.6-flash"
