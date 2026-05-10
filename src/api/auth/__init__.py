"""Authentication module for Meridian API.

JWT-based authentication and authorization.
"""

from .jwt import (
    TokenData,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_data,
    verify_token_type,
    verify_password,
    get_password_hash,
    authenticate_user,
    get_user_by_id,
    require_scope,
    get_current_user,
    get_current_active_user,
    require_scope_dependency,
    refresh_access_token,
    create_auth_endpoints,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

__all__ = [
    "TokenData",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_token_data",
    "verify_token_type",
    "verify_password",
    "get_password_hash",
    "authenticate_user",
    "get_user_by_id",
    "require_scope",
    "get_current_user",
    "get_current_active_user",
    "require_scope_dependency",
    "refresh_access_token",
    "create_auth_endpoints",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
]
