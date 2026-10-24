"""M3 acceptance: the demo seed loads docs/02 §12 and is idempotent."""

import asyncpg

from app.auth import dev_user_id
from app.seed.demo import DEMO_ADMIN_EMAIL, run
from tests.conftest import APP_URL, needs_db

pytestmark = needs_db


async def _society_totals() -> dict[str, tuple[int, int]]:
    conn = await asyncpg.connect(APP_URL)
    result: dict[str, tuple[int, int]] = {}
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_user_id', $1, true)",
                str(dev_user_id(DEMO_ADMIN_EMAIL)),
            )
            societies = await conn.fetch("SELECT id, name FROM societies")
        for s in societies:
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('app.current_society_id', $1, true)", str(s["id"])
                )
                flats = await conn.fetchval("SELECT count(*) FROM flats")
                dues = await conn.fetchval(
                    "SELECT coalesce(sum(amount_paise), 0) FROM ledger_entries"
                    " WHERE entry_type = 'opening_balance'"
                )
            result[s["name"]] = (flats, int(dues))
    finally:
        await conn.close()
    return result


async def test_seed_loads_the_three_societies_and_is_idempotent() -> None:
    # Other tests may have seeded already; either way the end state must be the same.
    first = await run()
    assert first.societies_created in (0, 3)
    expected = {
        "Shanti Sadan CHS": (120, 7560000),  # ₹75,600 of listed dues
        "Gulmohar Heights CHS": (64, 4680000),  # ₹46,800
        "Sagar Darshan CHS": (42, 900000),  # ₹9,000
    }
    assert await _society_totals() == expected

    second = await run()
    assert (
        second.societies_created,
        second.flats_created,
        second.balances_created,
        second.heads_created,
    ) == (0, 0, 0, 0)
    assert await _society_totals() == expected
