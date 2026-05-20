"""
Bearer token authentication for the Jengo API.

Tokens are loaded from the environment variable JENGO_API_TOKENS
(comma-separated) or from a config dict passed at construction time.

FastAPI dependency: get_current_user
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


class TokenStore:
    """Holds valid bearer tokens.  Loaded once at startup."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        if tokens is not None:
            self._tokens: frozenset[str] = frozenset(t.strip() for t in tokens if t.strip())
        else:
            raw = os.environ.get("JENGO_API_TOKENS", "")
            self._tokens = frozenset(t.strip() for t in raw.split(",") if t.strip())

        # Always accept the env-var single-token variant
        single = os.environ.get("API_TOKEN", "").strip()
        if single:
            self._tokens = self._tokens | {single}

    def is_valid(self, token: str) -> bool:
        return token in self._tokens

    def add_token(self, token: str) -> None:
        """Add a token at runtime (useful for tests)."""
        self._tokens = self._tokens | {token.strip()}


# Module-level singleton — initialised once at import time
_token_store = TokenStore()


def verify_token(token: str) -> bool:
    """Return True if the token is valid."""
    return _token_store.is_valid(token)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ] = None,
) -> str:
    """
    FastAPI dependency that validates the Bearer token.

    Returns the token string (acting as user identifier) on success.
    Raises HTTP 401 on missing or invalid token.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
