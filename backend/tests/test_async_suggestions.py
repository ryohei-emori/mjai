"""Contract tests for the optional long-running Codex suggestion transport."""

import logging
import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.llm.codexcli_provider import CodexCLIError

TEST_JWT_SECRET = "test-secret-value"
ALLOWED_EMAIL = "owner@example.com"


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "email": ALLOWED_EMAIL,
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
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
def headers():
    return {"Authorization": f"Bearer {_token()}"}


@pytest.fixture
def request_body():
    return {
        "originalText": "研究対象となる十分に長い原文です。",
        "targetText": "这是一个足够长的翻译测试文本。",
    }


def _start_patches(*, configured=True, submit=None):
    submit_mock = submit or AsyncMock(return_value="task-1")
    return (
        patch("app.llm.codexcli_provider.is_codexcli_configured", return_value=configured),
        patch("app.llm.codexcli_provider.submit_codexcli_task", new=submit_mock),
        patch("app.llm.local_fastpath.try_local_fastpath", return_value=None),
        patch(
            "app.llm.provider_health.load_shared_state",
            new=AsyncMock(return_value=(None, [])),
        ),
    )


def test_start_rejects_missing_text(client, headers):
    response = client.post(
        "/suggestions/async",
        json={"originalText": "", "targetText": "対象"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["error"] == "originalText and targetText are required"


def test_start_reports_unconfigured_gateway(client, headers, request_body):
    configured, submit, fastpath, shared = _start_patches(configured=False)
    with configured, submit as submit_mock, fastpath, shared:
        response = client.post("/suggestions/async", json=request_body, headers=headers)

    assert response.status_code == 404
    assert response.json()["error"] == "Codex CLI API is not configured"
    submit_mock.assert_not_awaited()


def test_start_reports_configured_gateway_submission_failure(
    client, headers, request_body, caplog
):
    submit_mock = AsyncMock(side_effect=CodexCLIError("gateway refused connection"))
    configured, submit, fastpath, shared = _start_patches(submit=submit_mock)
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with configured, submit, fastpath, shared:
            response = client.post("/suggestions/async", json=request_body, headers=headers)

    assert response.status_code == 502
    assert response.json() == {
        "error": "Codex CLI task submission failed",
        "codex_error": "gateway refused connection",
    }
    assert "async task submission failed" in caplog.text


def test_start_accepts_pending_task(client, headers, request_body):
    configured, submit, fastpath, shared = _start_patches()
    with configured, submit as submit_mock, fastpath, shared:
        response = client.post("/suggestions/async", json=request_body, headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "status": "pending",
        "taskId": "task-1",
        "llmProvider": "codex-cli",
        "llmModel": "gpt-5.6-sol",
    }
    submit_mock.assert_awaited_once()


def test_poll_reports_pending_task(client, headers):
    with patch(
        "app.llm.codexcli_provider.get_codexcli_task",
        new=AsyncMock(return_value={"state": "running"}),
    ):
        response = client.get("/suggestions/async/task-1", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "status": "pending",
        "taskId": "task-1",
        "state": "running",
    }


def test_poll_returns_completed_task(client, headers):
    output = {"suggestions": [], "overallComment": "完了"}
    with patch(
        "app.llm.codexcli_provider.get_codexcli_task",
        new=AsyncMock(
            return_value={"state": "completed", "output_json": output, "model": "gpt-5.6-terra"}
        ),
    ):
        response = client.get("/suggestions/async/task-1", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        **output,
        "llmProvider": "codex-cli",
        "llmModel": "gpt-5.6-terra",
        "status": "completed",
        "taskId": "task-1",
    }


@pytest.mark.parametrize(
    "task, expected_error",
    [
        ({"state": "failed", "error": "worker exited"}, "worker exited"),
        ({"state": "completed", "output_json": "not-an-object"}, "output_json was not an object"),
    ],
)
def test_poll_reports_failed_or_invalid_task(client, headers, task, expected_error, caplog):
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with patch(
            "app.llm.codexcli_provider.get_codexcli_task",
            new=AsyncMock(return_value=task),
        ):
            response = client.get("/suggestions/async/task-1", headers=headers)

    assert response.status_code == 502
    assert response.json()["codex_error"] == expected_error
    assert "Codex CLI async task" in caplog.text


def test_poll_reports_gateway_error(client, headers, caplog):
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with patch(
            "app.llm.codexcli_provider.get_codexcli_task",
            new=AsyncMock(side_effect=CodexCLIError("status endpoint unavailable")),
        ):
            response = client.get("/suggestions/async/task-1", headers=headers)

    assert response.status_code == 502
    assert response.json()["codex_error"] == "status endpoint unavailable"
    assert "async task polling failed" in caplog.text
