"""Local-only sign-in for previews without a Supabase project. Mounted only when
APP_ENV=local and SUPABASE_JWT_SECRET is set; never in demo or production."""

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

import jwt
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.config import get_settings

router = APIRouter(prefix="/dev", tags=["dev"])


class DevTokenIn(BaseModel):
    email: EmailStr


class DevTokenOut(BaseModel):
    access_token: str


@router.post("/token")
async def dev_token(body: DevTokenIn) -> DevTokenOut:
    settings = get_settings()
    secret = settings.supabase_jwt_secret
    if settings.app_env != "local" or not secret:
        raise RuntimeError("dev sign-in is local-only")
    email = str(body.email).lower()
    claims = {
        "sub": str(uuid5(NAMESPACE_URL, f"societyiq-dev:{email}")),
        "email": email,
        "aud": settings.jwt_audience,
        "exp": datetime.now(UTC) + timedelta(hours=12),
    }
    return DevTokenOut(access_token=jwt.encode(claims, secret, "HS256"))
