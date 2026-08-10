"""Tests for backend/app/auth.py's get_current_user dependency.

These tests mount the dependency on a minimal isolated FastAPI app (not the
full app.main app) so they don't require a live database connection.
"""

import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import get_current_user

TEST_JWT_SECRET = "test-secret-value"
ALLOWED_EMAIL = "owner@example.com"
OTHER_EMAIL = "someone-else@example.com"


def make_token(email: str, secret: str = TEST_JWT_SECRET, expired: bool = False) -> str:
    now = int(time.time())
    payload = {
        "email": email,
        "aud": "authenticated",
        "iat": now,
        "exp": now - 60 if expired else now + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("ALLOWED_USER_EMAIL", ALLOWED_EMAIL)
    monkeypatch.setenv("ALLOWED_USER_EMAILS", ALLOWED_EMAIL)

    app = FastAPI()

    @app.get("/protected")
    async def protected(user: dict = Depends(get_current_user)):
        return {"email": user["email"]}

    return TestClient(app)


def test_request_without_token_is_401(client):
    response = client.get("/protected")
    assert response.status_code == 401


def test_request_with_malformed_token_is_401(client):
    response = client.get("/protected", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_request_with_expired_token_is_401(client):
    token = make_token(ALLOWED_EMAIL, expired=True)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_request_with_wrong_signature_is_401(client):
    token = make_token(ALLOWED_EMAIL, secret="a-different-secret")
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_request_with_valid_token_but_non_allowlisted_email_is_403(client):
    token = make_token(OTHER_EMAIL)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_request_with_valid_token_and_allowlisted_email_succeeds(client):
    token = make_token(ALLOWED_EMAIL)
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"email": ALLOWED_EMAIL}


def test_allowlist_comparison_is_case_insensitive(client):
    token = make_token(ALLOWED_EMAIL.upper())
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
