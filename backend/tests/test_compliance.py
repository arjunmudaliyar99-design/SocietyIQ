"""M10 acceptance (docs/07): the seed society shows the generator service as Overdue and the
tank cleaning as Due soon; marking done moves the next due date correctly. Also roles,
vendors, the committee home and the reminder job."""

from datetime import date, timedelta

import pytest

from app.auth import dev_user_id
from app.calc.compliance import add_months
from app.seed.demo import DEMO_ADMIN_EMAIL, run
from app.services.home import next_bill_date
from app.timeutil import today_ist
from tests.conftest import TestUser, needs_db

DEMO = TestUser(id=dev_user_id(DEMO_ADMIN_EMAIL), email=DEMO_ADMIN_EMAIL)
JOBS = {"X-Jobs-Token": "jobs-token-for-tests-only"}


@pytest.mark.parametrize(
    ("today", "bill_day", "frequency", "expected"),
    [
        (date(2026, 10, 24), None, "monthly", None),
        (date(2026, 10, 24), 1, "monthly", date(2026, 11, 1)),
        (date(2026, 10, 24), 24, "monthly", date(2026, 10, 24)),
        (date(2026, 10, 24), 28, "monthly", date(2026, 10, 28)),
        # No 31 November: the job only runs on a month's own bill day.
        (date(2026, 11, 2), 31, "monthly", date(2026, 12, 31)),
        # Quarterly with an April year: quarters start in Apr, Jul, Oct, Jan.
        (date(2026, 10, 24), 1, "quarterly", date(2027, 1, 1)),
        (date(2026, 10, 1), 1, "quarterly", date(2026, 10, 1)),
    ],
)
def test_next_bill_date(today: date, bill_day: int | None, frequency: str, expected: date) -> None:
    assert next_bill_date(today, bill_day, frequency, 4) == expected


async def _shanti(client) -> str:  # noqa: ANN001
    await run()
    mine = (await client.get("/api/v1/me/societies", headers=DEMO.headers)).json()
    return next(s["id"] for s in mine if s["name"] == "Shanti Sadan CHS")


@needs_db
async def test_seed_generator_overdue_tank_due_soon_and_mark_done(client) -> None:  # noqa: ANN001
    sid = await _shanti(client)
    base = f"/api/v1/societies/{sid}"
    items = {
        i["title"]: i
        for i in (await client.get(f"{base}/compliance/items", headers=DEMO.headers)).json()
    }
    # Another test may have marked the generator done already; only check a fresh seed.
    generator = items["Generator service"]
    if generator["last_done_on"] is None:
        assert (generator["status"], generator["days_left"]) == ("overdue", -5)
        assert generator["vendor_name"] == "Powergen Services"
    assert (items["Water tank cleaning"]["status"], items["Water tank cleaning"]["days_left"]) == (
        "due_soon",
        12,
    )
    assert items["Building insurance"]["status"] == "ok"
    assert items["Lift AMC renewal"]["contract_value_paise"] == 19200000
    assert len(items) == 7

    # Seeding again adds nothing.
    assert (await run()).compliance_created == 0

    home = (await client.get(f"{base}/home", headers=DEMO.headers)).json()
    assert home["compliance_due_soon"] >= 2  # tank cleaning and lift AMC
    assert home["coming_soon"] == []
    assert home["open_complaints"] >= 0
    # Seed dues are opening balances (docs/02 §12): ₹75,600 over 6 flats, unless other
    # tests have recorded payments or bills for Shanti Sadan since.
    assert home["outstanding_paise"] >= 0 and home["flats_with_dues"] >= 0

    # Mark done: generator repeats every 3 months in the seed.
    done_on = today_ist() - timedelta(days=1)
    r = await client.post(
        f"{base}/compliance/items/{generator['id']}/done",
        json={"done_on": done_on.isoformat(), "notes": "Serviced"},
        headers=DEMO.headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["next_due_on"] == add_months(done_on, 3).isoformat()
    assert body["last_done_on"] == done_on.isoformat()
    assert body["status"] == "ok"
    assert body["events"][0]["done_on"] == done_on.isoformat()

    future = await client.post(
        f"{base}/compliance/items/{generator['id']}/done",
        json={"done_on": (today_ist() + timedelta(days=1)).isoformat()},
        headers=DEMO.headers,
    )
    assert future.json()["error"]["code"] == "DONE_IN_FUTURE"


@needs_db
async def test_one_off_item_is_turned_off_when_done(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}"
    h = s.a_admin.headers
    item = await client.post(
        f"{base}/compliance/items",
        json={"item_type": "other", "title": "Terrace waterproofing", "next_due_on": "2026-11-30"},
        headers=h,
    )
    assert item.status_code == 201, item.text
    done = await client.post(
        f"{base}/compliance/items/{item.json()['id']}/done",
        json={"done_on": "2026-10-01"},
        headers=h,
    )
    assert (done.json()["is_active"], done.json()["status"]) == (False, "done")
    again = await client.post(
        f"{base}/compliance/items/{item.json()['id']}/done",
        json={"done_on": "2026-10-02"},
        headers=h,
    )
    assert again.status_code == 409


@needs_db
async def test_vendors_and_cross_society_vendor_ids(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    a, b = f"/api/v1/societies/{s.a_id}", f"/api/v1/societies/{s.b_id}"
    vb = await client.post(f"{b}/vendors", json={"name": "AquaClean"}, headers=s.b_admin.headers)
    assert vb.status_code == 201
    va = await client.post(f"{a}/vendors", json={"name": "AquaClean"}, headers=s.a_admin.headers)
    assert va.status_code == 201  # names are unique per society only
    dup = await client.post(f"{a}/vendors", json={"name": " aquaclean "}, headers=s.a_admin.headers)
    assert dup.json()["error"]["code"] == "VENDOR_EXISTS"

    # B's vendor cannot be attached to A's item.
    r = await client.post(
        f"{a}/compliance/items",
        json={
            "item_type": "tank_cleaning",
            "title": "Tank",
            "next_due_on": "2026-12-01",
            "vendor_id": vb.json()["id"],
        },
        headers=s.a_admin.headers,
    )
    assert r.json()["error"]["code"] == "VENDOR_NOT_FOUND"
    assert (
        await client.patch(
            f"{a}/vendors/{vb.json()['id']}", json={"notes": "x"}, headers=s.a_admin.headers
        )
    ).status_code == 404


@needs_db
async def test_roles(client, two_societies) -> None:  # noqa: ANN001
    from tests.test_flats import _join

    s = two_societies
    base = f"/api/v1/societies/{s.a_id}"
    committee = await _join(client, s.a_id, s.a_admin, "committee")
    auditor = await _join(client, s.a_id, s.a_admin, "auditor")
    body = {"item_type": "pest_control", "title": "Pest control", "next_due_on": "2026-11-15"}
    assert (
        await client.post(f"{base}/compliance/items", json=body, headers=committee.headers)
    ).status_code == 201
    assert (
        await client.post(f"{base}/compliance/items", json=body, headers=auditor.headers)
    ).status_code == 403
    assert (
        await client.get(f"{base}/compliance/items", headers=auditor.headers)
    ).status_code == 200
    assert (await client.get(f"{base}/home", headers=auditor.headers)).status_code == 200


@needs_db
async def test_reminder_job_is_idempotent(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}"
    today = date(2031, 3, 3)  # a day no other test uses
    for offset in (90, 45, -14):
        await client.post(
            f"{base}/compliance/items",
            json={
                "item_type": "other",
                "title": f"Item {offset}",
                "next_due_on": (today + timedelta(days=offset)).isoformat(),
            },
            headers=s.a_admin.headers,
        )
    assert (
        await client.post("/api/v1/internal/jobs/compliance-reminders", json={})
    ).status_code == 401
    first = await client.post(
        "/api/v1/internal/jobs/compliance-reminders",
        json={"today": today.isoformat()},
        headers=JOBS,
    )
    assert first.status_code == 200, first.text
    assert first.json()["created"] >= 2  # 90 days before and 2 weeks overdue; not 45
    assert first.json()["failed"] == {}
    second = await client.post(
        "/api/v1/internal/jobs/compliance-reminders",
        json={"today": today.isoformat()},
        headers=JOBS,
    )
    assert second.json()["created"] == 0
