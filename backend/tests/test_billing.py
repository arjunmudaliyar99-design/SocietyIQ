"""M5 acceptance (docs/07): approving a run for Shanti Sadan creates one bill per flat with
gap-free numbers; B-207's ledger balance equals the expected total; running the job twice does
not create two drafts."""

import asyncpg

from app.auth import dev_user_id
from app.seed.demo import DEMO_ADMIN_EMAIL, run
from tests.conftest import APP_URL, TestUser, needs_db

pytestmark = needs_db

DEMO = TestUser(id=dev_user_id(DEMO_ADMIN_EMAIL), email=DEMO_ADMIN_EMAIL)
JOBS = {"X-Jobs-Token": "jobs-token-for-tests-only"}


async def _ledger_balance(society_id: str, flat_id: str) -> int:
    conn = await asyncpg.connect(APP_URL)
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_society_id', $1, true)", society_id)
            value = await conn.fetchval(
                "SELECT coalesce(sum(amount_paise), 0) FROM ledger_entries"
                " WHERE flat_id = $1::uuid",
                flat_id,
            )
    finally:
        await conn.close()
    return int(value)


async def _small_society(client, admin, monthly_service_paise: int = 300000) -> tuple[str, str]:  # noqa: ANN001
    """One flat, one service head. Returns (society id, flat id)."""
    r = await client.post(
        "/api/v1/societies",
        json={"details": {"name": "Sagar Darshan CHS"}, "billing": {"bill_day": 1, "due_days": 15}},
        headers=admin.headers,
    )
    sid = r.json()["society"]["id"]
    base = f"/api/v1/societies/{sid}"
    wing = (await client.get(f"{base}/wings", headers=admin.headers)).json()[0]["id"]
    flat = (
        await client.post(
            f"{base}/flats", json={"wing_id": wing, "flat_number": "101"}, headers=admin.headers
        )
    ).json()
    await client.post(
        f"{base}/flats/{flat['id']}/members",
        json={
            "full_name": "Member 101",
            "member_type": "owner",
            "is_primary": True,
            "tenant_can_pay": False,
        },
        headers=admin.headers,
    )
    await client.post(
        f"{base}/charges/heads",
        json={
            "name": "Service charges",
            "standard_code": "service",
            "calc_type": "equal_per_flat",
            "period_total_paise": monthly_service_paise,
        },
        headers=admin.headers,
    )
    return sid, flat["id"]


async def test_shanti_sadan_run_issues_one_bill_per_flat_with_gap_free_numbers(client) -> None:  # noqa: ANN001
    await run()
    mine = (await client.get("/api/v1/me/societies", headers=DEMO.headers)).json()
    sid = next(s["id"] for s in mine if s["name"] == "Shanti Sadan CHS")
    base = f"/api/v1/societies/{sid}"

    r = await client.post(
        f"{base}/billing-runs", json={"period_start": "2027-01-01"}, headers=DEMO.headers
    )
    assert r.status_code == 201, r.text
    draft = r.json()
    assert draft["status"] == "draft"
    assert draft["flat_count"] == 120
    assert draft["total_paise"] == 420000 * 119 + 454000
    assert (draft["bill_date"], draft["due_date"]) == ("2027-01-01", "2027-01-16")
    again = await client.post(
        f"{base}/billing-runs", json={"period_start": "2027-01-01"}, headers=DEMO.headers
    )
    assert again.json()["error"]["code"] == "RUN_EXISTS"

    detail = (await client.get(f"{base}/billing-runs/{draft['id']}", headers=DEMO.headers)).json()
    assert len(detail["draft_flats"]) == 120 and detail["bills"] == []

    approved = await client.post(f"{base}/billing-runs/{draft['id']}/approve", headers=DEMO.headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    bills = (await client.get(f"{base}/billing-runs/{draft['id']}", headers=DEMO.headers)).json()[
        "bills"
    ]
    assert len(bills) == 120
    assert len({b["flat_id"] for b in bills}) == 120
    sequence = sorted(int(b["bill_number"].rsplit("/", 1)[1]) for b in bills)
    assert sequence == list(range(sequence[0], sequence[0] + 120))
    assert all(b["bill_number"].startswith("B/2026-27/") for b in bills)
    # Numbers follow flat order: A-101 gets the first.
    first = min(bills, key=lambda b: b["bill_number"])
    assert first["flat_label"] == "A-101"

    b207 = next(b for b in bills if b["flat_label"] == "B-207")
    assert (b207["arrears_paise"], b207["charges_paise"], b207["total_due_paise"]) == (
        2940000,
        420000,
        3360000,
    )
    assert await _ledger_balance(sid, b207["flat_id"]) == 3360000
    a305 = next(b for b in bills if b["flat_label"] == "A-305")
    lines = (await client.get(f"{base}/bills/{a305['id']}", headers=DEMO.headers)).json()["lines"]
    assert {line["description"]: line["amount_paise"] for line in lines} == {
        "Service charges": 340000,
        "Repair and maintenance fund": 60000,
        "Sinking fund": 20000,
        "Non-occupancy charges": 34000,
    }


async def test_changed_charges_make_the_draft_stale(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    sid, _ = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    h = s.a_admin.headers
    draft = (
        await client.post(f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=h)
    ).json()
    head = (await client.get(f"{base}/charges/heads", headers=h)).json()[0]
    await client.patch(
        f"{base}/charges/heads/{head['id']}", json={"period_total_paise": 310000}, headers=h
    )
    r = await client.post(f"{base}/billing-runs/{draft['id']}/approve", headers=h)
    assert r.json()["error"]["code"] == "RUN_STALE"
    cancelled = await client.post(
        f"{base}/billing-runs/{draft['id']}/cancel", json={"reason": "Charges changed"}, headers=h
    )
    assert cancelled.json()["status"] == "cancelled"
    # A cancelled draft frees the period for a new one.
    assert (
        await client.post(f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=h)
    ).status_code == 201


async def test_cancel_reverses_and_reissue_replaces(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    sid, flat_id = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    h = s.a_admin.headers
    draft = (
        await client.post(f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=h)
    ).json()
    await client.post(f"{base}/billing-runs/{draft['id']}/approve", headers=h)
    [bill] = (await client.get(f"{base}/bills", headers=h)).json()
    assert bill["bill_number"] == "B/2026-27/000001"
    assert await _ledger_balance(sid, flat_id) == 300000

    no_reason = await client.post(
        f"{base}/bills/{bill['id']}/cancel", json={"reason": ""}, headers=h
    )
    assert no_reason.status_code == 422
    r = await client.post(
        f"{base}/bills/{bill['id']}/cancel", json={"reason": "Wrong service amount"}, headers=h
    )
    assert r.json()["status"] == "cancelled"
    assert await _ledger_balance(sid, flat_id) == 0
    twice = await client.post(
        f"{base}/bills/{bill['id']}/cancel", json={"reason": "again"}, headers=h
    )
    assert twice.json()["error"]["code"] == "BILL_NOT_CANCELLABLE"

    head = (await client.get(f"{base}/charges/heads", headers=h)).json()[0]
    await client.patch(
        f"{base}/charges/heads/{head['id']}", json={"period_total_paise": 280000}, headers=h
    )
    new = await client.post(f"{base}/bills/{bill['id']}/reissue", headers=h)
    assert new.status_code == 201, new.text
    assert (new.json()["bill_number"], new.json()["charges_paise"]) == ("B/2026-27/000002", 280000)
    assert new.json()["replaces_bill_id"] == bill["id"]
    assert await _ledger_balance(sid, flat_id) == 280000
    old = (await client.get(f"{base}/bills/{bill['id']}", headers=h)).json()
    assert old["replaced_by_bill_id"] == new.json()["id"]
    assert (await client.post(f"{base}/bills/{bill['id']}/reissue", headers=h)).json()["error"][
        "code"
    ] == "BILL_ALREADY_REISSUED"


async def test_interest_is_simple_and_its_own_line(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    sid, _ = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    h = s.a_admin.headers
    r = await client.patch(
        f"{base}/settings",
        json={
            "interest_enabled": True,
            "interest_rate_annual_pct": "12",
            "interest_gb_resolution_date": "2026-09-20",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    for month in ("2026-11-01", "2026-12-01"):
        run_ = (
            await client.post(f"{base}/billing-runs", json={"period_start": month}, headers=h)
        ).json()
        await client.post(f"{base}/billing-runs/{run_['id']}/approve", headers=h)
    bills = (await client.get(f"{base}/bills", headers=h)).json()
    december = next(b for b in bills if b["bill_number"].endswith("000002"))
    # ₹3,000 overdue from 16 Nov (due date) to 1 Dec = 15 days at 12%: 300000 × 0.12 × 15/365
    assert december["interest_paise"] == 1479
    assert december["arrears_paise"] == 300000
    assert december["total_due_paise"] == 300000 + 300000 + 1479
    detail = (await client.get(f"{base}/bills/{december['id']}", headers=h)).json()
    assert [line["line_type"] for line in detail["lines"]] == ["charge", "interest"]


async def test_roles(client, two_societies) -> None:  # noqa: ANN001
    from tests.test_flats import _join

    s = two_societies
    sid, _ = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    consultant = await _join(client, sid, s.a_admin, "consultant")
    committee = await _join(client, sid, s.a_admin, "committee")
    draft = await client.post(
        f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=consultant.headers
    )
    assert draft.status_code == 201
    assert (
        await client.post(
            f"{base}/billing-runs/{draft.json()['id']}/approve", headers=consultant.headers
        )
    ).status_code == 403
    assert (await client.get(f"{base}/billing-runs", headers=committee.headers)).status_code == 200
    assert (
        await client.post(
            f"{base}/billing-runs", json={"period_start": "2026-12-01"}, headers=committee.headers
        )
    ).status_code == 403


async def test_no_charges_no_run(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    r = await client.post(
        f"/api/v1/societies/{s.a_id}/billing-runs",
        json={"period_start": "2026-11-01"},
        headers=s.a_admin.headers,
    )
    assert r.json()["error"]["code"] == "NO_CHARGES"


async def test_job_is_idempotent_and_auto_approves_unchanged_setup(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    sid, _ = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    h = s.a_admin.headers
    # Day 27 is used by no other test society.
    await client.patch(f"{base}/settings", json={"bill_day": 27}, headers=h)

    unauthorised = await client.post("/api/v1/internal/jobs/create-draft-billing-runs", json={})
    assert unauthorised.status_code == 401

    first = await client.post(
        "/api/v1/internal/jobs/create-draft-billing-runs",
        json={"today": "2026-11-27"},
        headers=JOBS,
    )
    assert first.status_code == 200, first.text
    assert sid in first.json()["created"]
    second = await client.post(
        "/api/v1/internal/jobs/create-draft-billing-runs",
        json={"today": "2026-11-27"},
        headers=JOBS,
    )
    assert sid in second.json()["skipped"]
    runs = (await client.get(f"{base}/billing-runs", headers=h)).json()
    assert [(r["period_start"], r["status"], r["created_by_job"]) for r in runs] == [
        ("2026-11-01", "draft", True)
    ]
    assert runs[0]["bill_date"] == "2026-11-27"

    # Approve November by hand, turn on auto-approve; December's unchanged setup approves itself.
    await client.post(f"{base}/billing-runs/{runs[0]['id']}/approve", headers=h)
    await client.patch(f"{base}/settings", json={"auto_approve_billing": True}, headers=h)
    december = await client.post(
        "/api/v1/internal/jobs/create-draft-billing-runs",
        json={"today": "2026-12-27"},
        headers=JOBS,
    )
    assert sid in december.json()["approved"]
    statuses = {
        r["period_start"]: r["status"]
        for r in (await client.get(f"{base}/billing-runs", headers=h)).json()
    }
    assert statuses == {"2026-11-01": "approved", "2026-12-01": "approved"}


async def test_pdf_or_a_clear_503(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    sid, _ = await _small_society(client, s.a_admin)
    base = f"/api/v1/societies/{sid}"
    h = s.a_admin.headers
    draft = (
        await client.post(f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=h)
    ).json()
    await client.post(f"{base}/billing-runs/{draft['id']}/approve", headers=h)
    [bill] = (await client.get(f"{base}/bills", headers=h)).json()
    try:
        import weasyprint  # noqa: F401

        available = True
    except (ImportError, OSError):
        available = False
    for url in (f"{base}/bills/{bill['id']}/pdf", f"{base}/billing-runs/{draft['id']}/pdf"):
        r = await client.get(url, headers=h)
        if available:
            assert r.status_code == 200
            assert r.content.startswith(b"%PDF")
        else:
            assert r.json()["error"]["code"] == "PDF_UNAVAILABLE"
