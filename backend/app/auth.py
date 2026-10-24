"""Verify the Supabase access token and read the user (docs/04 §5).

Supabase projects sign tokens either with a shared secret (HS256) or with asymmetric keys
published at a JWKS endpoint. SUPABASE_JWKS_URL wins when set.
"""

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt

from app.config import get_settings
from app.errors import AppError


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str | None


def _unauthorized() -> AppError:
    return AppError(401, "UNAUTHORIZED", "errors.signInAgain")


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def verify_token(token: str) -> AuthUser:
    settings = get_settings()
    try:
        if settings.supabase_jwks_url:
            key = _jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token).key
            algorithms = ["ES256", "RS256"]
        elif settings.supabase_jwt_secret:
            key = settings.supabase_jwt_secret
            algorithms = ["HS256"]
        else:
            raise _unauthorized()
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=settings.jwt_audience,
            options={"require": ["sub", "exp"]},
        )
        return AuthUser(id=UUID(claims["sub"]), email=claims.get("email"))
    except (jwt.PyJWTError, ValueError) as exc:
        raise _unauthorized() from exc
