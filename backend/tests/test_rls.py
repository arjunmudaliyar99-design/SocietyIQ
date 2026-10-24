"""Row-level security without the API (docs/04 §6 point 3). Queries here deliberately have
no society filter: only the database policies stand between Society A and Society B."""

from collections.abc import AsyncIterator

import asyncpg
import pytest

from tests.conftest import APP_URL, needs_db

pytestmark = needs_db

SOCIETY_TABLES = ["societies", "wings", "society_memberships", "audit_log"]


@pytest.fixture
async def app_conn() -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(APP_URL)
    try:
        yield conn
    finally:
        await conn.close()


async def _set_context(conn: asyncpg.Connection, society_id: object, user_id: object) -> None:
    await conn.execute("SELECT set_config('app.current_society_id', $1, true)", str(society_id))
    await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(user_id))


async def test_app_role_cannot_bypass_rls(app_conn) -> None:  # noqa: ANN001
    row = await app_conn.fetchrow(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
    )
    assert row["rolsuper"] is False
    assert row["rolbypassrls"] is False


@pytest.mark.parametrize("table", SOCIETY_TABLES)
async def test_context_a_cannot_read_b(app_conn, two_societies, table) -> None:  # noqa: ANN001
    s = two_societies
    key = "id" if table == "societies" else "society_id"
    async with app_conn.transaction():
        await _set_context(app_conn, s.a_id, s.a_admin.id)
        rows_b = await app_conn.fetchval(f"SELECT count(*) FROM {table} WHERE {key} = $1", s.b_id)
        rows_a = await app_conn.fetchval(f"SELECT count(*) FROM {table} WHERE {key} = $1", s.a_id)
    assert rows_b == 0
    assert rows_a > 0


async def test_no_context_sees_no_society_data(app_conn, two_societies) -> None:  # noqa: ANN001
    for table in SOCIETY_TABLES:
        assert await app_conn.fetchval(f"SELECT count(*) FROM {table}") == 0, table


async def test_context_a_cannot_write_into_b(app_conn, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await _set_context(app_conn, s.a_id, s.a_admin.id)
            await app_conn.execute(
                "INSERT INTO wings (society_id, name) VALUES ($1, 'Sneaky')", s.b_id
            )


async def test_context_a_cannot_update_b(app_conn, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    async with app_conn.transaction():
        await _set_context(app_conn, s.a_id, s.a_admin.id)
        result = await app_conn.execute(
            "UPDATE societies SET name = 'Changed' WHERE id = $1", s.b_id
        )
    assert result == "UPDATE 0"


async def test_audit_log_is_append_only(app_conn, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    for sql in ("UPDATE audit_log SET reason = 'x'", "DELETE FROM audit_log"):
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            async with app_conn.transaction():
                await _set_context(app_conn, s.a_id, s.a_admin.id)
                await app_conn.execute(sql)


async def test_no_deletes_on_society_tables(app_conn, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with app_conn.transaction():
            await _set_context(app_conn, s.a_id, s.a_admin.id)
            await app_conn.execute("DELETE FROM society_memberships")


async def test_users_see_only_themselves(app_conn, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    async with app_conn.transaction():
        await _set_context(app_conn, s.a_id, s.a_admin.id)
        ids = [r["id"] for r in await app_conn.fetch("SELECT id FROM users")]
    assert ids == [s.a_admin.id]


async def test_legal_parameters_are_read_only(app_conn) -> None:  # noqa: ANN001
    count = await app_conn.fetchval(
        "SELECT count(*) FROM legal_parameters WHERE code = 'interest_max_annual_pct'"
    )
    assert count == 1
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await app_conn.execute("UPDATE legal_parameters SET value = 18")
