"""Settings from environment variables (docs/04 §14: secrets only in the environment).

Every name here is listed in backend/.env.example. Values not needed until a later
milestone are optional so the app starts in M0 without them.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "demo", "production"] = "local"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    # Database (M2). The app connects as the restricted app_backend role; migrations
    # run as the owner role (docs/04 §4, §6).
    database_url: str | None = None
    migrations_database_url: str | None = None

    # Supabase Auth and Storage (M2). The service-role key stays on the backend only.
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None
    jwt_audience: str = "authenticated"

    # Invites (M2). Expiry is not set in the docs: TODO(confirm): Q-031.
    invite_expiry_days: int = 7
    committee_web_url: str = "http://localhost:5173"
    resident_pwa_url: str = "http://localhost:5174"

    # Version of the terms and privacy text a user consents to (docs/08 §8). The texts need
    # a lawyer's review before the first pilot; bump this when they change.
    policy_version: str = "draft-2026-10"

    # AI (docs/04 §11). "fake" works without any key.
    ai_provider: Literal["fake", "groq", "gemini"] = "fake"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    # Email (docs/04 §12). Provider not chosen yet (docs/09 §6).
    email_provider: str | None = None
    email_provider_api_key: str | None = None
    email_from: str = "no-reply@example.com"

    # Scheduled jobs call /internal/jobs/* with this token (docs/04 §13).
    internal_jobs_token: str | None = None

    # Company identity (CLAUDE.md §4a). Placeholders until real values exist.
    support_email: str = "support@example.com"
    support_phone: str = ""
    support_hours: str = ""
    company_legal_name: str = ""
    company_address: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
