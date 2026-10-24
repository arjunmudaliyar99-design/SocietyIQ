"""Test setup. Database tests run against a real PostgreSQL 16 (docs/04 §15).

TEST_DATABASE_ADMIN_URL points at a server where we may create a scratch database, as its
owner. Locally: `docker run -d --name societyiq-pg -e POSTGRES_PASSWORD=postgres
-p 54329:5432 postgres:16`. Without a reachable server, database tests are skipped.
"""

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest

ADMIN_URL = os.environ.get(
    "TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:54329/postgres"
)
TEST_DB = "societyiq_test"
APP_PASSWORD = "app_backend_test_only"
JWT_SECRET = "test-secret-not-for-production-use-0123456789"


def _with_db(url: str, db: str, user: str | None = None, password: str | None = None) -> str:
    scheme, rest = url.split("://", 1)
    creds, hostpart = rest.rsplit("@", 1)
    host = hostpart.split("/", 1)[0]
    if user:
        creds = f"{user}:{password}"
    return f"{scheme}://{creds}@{host}/{db}"


OWNER_URL = _with_db(ADMIN_URL, TEST_DB)
# Roles are server-wide, so tests log in as their own role that inherits app_backend's
# grants. Changing app_backend's password here would break a developer's local database.
APP_ROLE = "app_backend_test"
APP_URL = _with_db(ADMIN_URL, TEST_DB, APP_ROLE, APP_PASSWORD)

# Settings are read once (lru_cache), so set them before the app is imported.
os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": APP_URL.replace("postgresql://", "postgresql+asyncpg://"),
        "MIGRATIONS_DATABASE_URL": OWNER_URL.replace("postgresql://", "postgresql+asyncpg://"),
        "SUPABASE_JWT_SECRET": JWT_SECRET,
        "SUPABASE_JWKS_URL": "",
        "STORAGE_BACKEND": "local",
        "INTERNAL_JOBS_TOKEN": "jobs-token-for-tests-only",
        "LOCAL_STORAGE_DIR": tempfile.mkdtemp(prefix="societyiq-test-storage-"),
    }
)


async def _prepare_database() -> bool:
    try:
        admin = await asyncpg.connect(ADMIN_URL, timeout=3)
    except (OSError, asyncpg.PostgresError):
        return False
    try:
        await admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        await admin.execute(f"CREATE DATABASE {TEST_DB}")
    finally:
        await admin.close()
    return True


def _migrate() -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.upgrade(cfg, "head")


async def _enable_app_login() -> None:
    owner = await asyncpg.connect(OWNER_URL)
    try:
        exists = await owner.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", APP_ROLE)
        if not exists:
            await owner.execute(f"CREATE ROLE {APP_ROLE} LOGIN NOBYPASSRLS INHERIT")
        await owner.execute(f"ALTER ROLE {APP_ROLE} PASSWORD '{APP_PASSWORD}'")
        await owner.execute(f"GRANT app_backend TO {APP_ROLE}")
    finally:
        await owner.close()


DB_READY = asyncio.run(_prepare_database())
if not DB_READY and os.environ.get("REQUIRE_TEST_DB") == "1":
    raise RuntimeError(f"REQUIRE_TEST_DB=1 but no PostgreSQL at {ADMIN_URL}")
if DB_READY:
    _migrate()
    asyncio.run(_enable_app_login())

needs_db = pytest.mark.skipif(not DB_READY, reason="PostgreSQL test server not reachable")


def make_token(
    user_id: UUID, email: str, *, secret: str = JWT_SECRET, expired: bool = False
) -> str:
    exp = datetime.now(UTC) + (timedelta(minutes=-5) if expired else timedelta(hours=1))
    claims = {"sub": str(user_id), "email": email, "aud": "authenticated", "exp": exp}
    return jwt.encode(claims, secret, "HS256")


@dataclass
class TestUser:
    id: UUID
    email: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(self.id, self.email)}"}


def new_user(label: str = "user") -> TestUser:
    uid = uuid4()
    return TestUser(id=uid, email=f"{label}-{uid.hex[:8]}@example.com")


@pytest.fixture
async def client() -> AsyncIterator[object]:
    import httpx

    from app.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


SOCIETY_BODY = {
    "details": {"name": "Shanti Sadan CHS", "city": "Mumbai", "pincode": "400071"},
    "billing": {"bill_day": 1, "due_days": 15},
    "invites": [],
}


@dataclass
class TwoSocieties:
    a_admin: TestUser
    b_admin: TestUser
    a_id: UUID
    b_id: UUID


@pytest.fixture
async def two_societies(client) -> TwoSocieties:  # noqa: ANN001
    """The isolation fixture (docs/04 §6): two societies, each with its own admin."""
    a_admin, b_admin = new_user("a-admin"), new_user("b-admin")
    ra = await client.post("/api/v1/societies", json=SOCIETY_BODY, headers=a_admin.headers)
    body_b = {**SOCIETY_BODY, "details": {"name": "Gulmohar Heights CHS", "city": "Thane"}}
    rb = await client.post("/api/v1/societies", json=body_b, headers=b_admin.headers)
    assert ra.status_code == 201, ra.text
    assert rb.status_code == 201, rb.text
    return TwoSocieties(
        a_admin=a_admin,
        b_admin=b_admin,
        a_id=UUID(ra.json()["society"]["id"]),
        b_id=UUID(rb.json()["society"]["id"]),
    )
