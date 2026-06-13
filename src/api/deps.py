"""Shared FastAPI dependencies for Meridian API."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth.jwt import TokenData, get_token_data, require_scope

_bearer = HTTPBearer(auto_error=False)


def auth_required() -> bool:
    """Whether JWT is required for mutating supplier routes."""
    explicit = os.getenv("MERIDIAN_REQUIRE_AUTH", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return True
    if explicit in {"0", "false", "no"}:
        return False
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def require_write_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[TokenData]:
    """Require write scope when auth is enabled; allow anonymous writes in dev demo mode."""
    if not auth_required():
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = get_token_data(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not require_scope(credentials.credentials, "write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write scope required",
        )

    return token_data
