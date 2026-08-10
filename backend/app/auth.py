"""Supabase JWT verification and single-allow-listed-email authorization.

Verifies the `Authorization: Bearer <token>` header against the Supabase
project's JWT secret (HS256, symmetric) and checks the token's `email`
claim against the `ALLOWED_USER_EMAIL` (or `ALLOWED_USER_EMAILS`,
comma-separated) environment variable.

- Missing/malformed/invalid/expired token -> 401 Unauthorized
- Valid token but email not on the allow-list -> 403 Forbidden
"""

import os
from typing import Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


def _get_allowed_emails() -> set:
    raw = os.environ.get("ALLOWED_USER_EMAILS", os.environ.get("ALLOWED_USER_EMAIL", ""))
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> Dict:
    """FastAPI dependency verifying a Supabase-issued JWT and the allow-list.

    Returns the decoded token claims on success.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        # A missing server-side secret is a server misconfiguration, not the
        # caller's fault, but we must not silently accept unverified tokens.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = str(payload.get("email", "")).strip().lower()
    allowed_emails = _get_allowed_emails()
    if not email or email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not authorized to access this application",
        )

    return payload
