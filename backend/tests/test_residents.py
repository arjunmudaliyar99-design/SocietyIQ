"""M7 (docs/07): residents see their own flat's dues, how to pay, bills and receipts; a tenant
without `tenant_can_pay` sees no amounts and cannot pay."""

from tests.conftest import needs_db, new_user

pytestmark = needs_db


async def _society_with_resident(client, admin):  # noqa: ANN001, ANN202
    r = await client.post(
        "/api/v1/societies",
        json={
            "details": {"name": "Shanti Sadan CHS"},
            "billing": {
                "bill_day": 1,
                "due_days": 15,
                "upi_id": "shantisadan@examplebank",
                "upi_payee_name": "Shanti Sadan CHS",
            },
        },
        headers=admin.headers,
    )
    sid = r.json()["society"]["id"]
    base = f"/api/v1/societies/{sid}"
    h = admin.headers
    wing = (await client.get(f"{base}/wings", headers=h)).json()[0]["id"]
    flat = (
        await client.post(
            f"{base}/flats", json={"wing_id": wing, "flat_number": "B-207"}, headers=h
        )
    ).json()["id"]
    other = (
        await client.post(
            f"{base}/flats", json={"wing_id": wing, "flat_number": "C-302"}, headers=h
        )
    ).json()["id"]
    await client.post(
        f"{base}/charges/heads",
        json={
            "name": "Maintenance",
            "standard_code": "service",
            "calc_type": "equal_per_flat",
            "period_total_paise": 840000,
        },
        headers=h,
    )
    run = (
        await client.post(f"{base}/billing-runs", json={"period_start": "2026-11-01"}, headers=h)
    ).json()
    await client.post(f"{base}/billing-runs/{run['id']}/approve", headers=h)

    async def join(role: str):  # noqa: ANN202
        user = new_user(role)
        inv = (
            await client.post(
                f"{base}/invites",
                json={"role": role, "email": user.email, "flat_id": flat},
                headers=h,
            )
        ).json()
        token = inv["invite_link"].split("token=", 1)[1]
        assert (
            await client.post(f"{base}/invites/accept", json={"token": token}, headers=user.headers)
        ).status_code == 200
        return user

    return base, flat, other, await join("owner"), await join("tenant")


async def test_owner_sees_dues_pay_info_bills_and_receipts(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base, flat, other, owner, _ = await _society_with_resident(client, s.a_admin)
    [mine] = (await client.get(f"{base}/my/flats", headers=owner.headers)).json()
    assert (mine["label"], mine["role"], mine["can_pay"]) == ("B-207", "owner", True)
    assert mine["balance_paise"] == 420000
    assert mine["latest_bill"]["bill_number"] == "B/2026-27/000001"
    assert mine["latest_bill"]["due_date"] == "2026-11-16"
    assert mine["pay"]["upi_link"].startswith("upi://pay?pa=shantisadan@examplebank")
    assert "&am=4200.00&" in mine["pay"]["upi_link"]
    assert mine["pay"]["qr_data_uri"].startswith("data:image/png;base64,")

    bills = (await client.get(f"{base}/my/flats/{flat}/bills", headers=owner.headers)).json()
    assert [b["bill_number"] for b in bills] == ["B/2026-27/000001"]

    report = {
        "amount_paise": 420000,
        "method": "upi",
        "received_on": "2026-11-04",
        "reference": "UPI-1",
    }
    reported = (
        await client.post(
            f"{base}/flats/{flat}/payment-reports", json=report, headers=owner.headers
        )
    ).json()
    payments = (await client.get(f"{base}/my/flats/{flat}/payments", headers=owner.headers)).json()
    assert [(p["status"], p["receipt_number"]) for p in payments] == [("pending", None)]
    assert (await client.get(f"{base}/my/flats", headers=owner.headers)).json()[0][
        "pending_reports"
    ] == 1

    await client.post(f"{base}/payments/{reported['id']}/confirm", headers=s.a_admin.headers)
    payments = (await client.get(f"{base}/my/flats/{flat}/payments", headers=owner.headers)).json()
    assert [(p["status"], p["receipt_number"]) for p in payments] == [
        ("confirmed", "R/2026-27/000001")
    ]
    after = (await client.get(f"{base}/my/flats", headers=owner.headers)).json()[0]
    assert (after["balance_paise"], after["pay"], after["latest_bill"]["status"]) == (
        0,
        None,
        "paid",
    )

    for url in (
        f"{base}/my/flats/{flat}/bills/{bills[0]['id']}/pdf",
        f"{base}/my/flats/{flat}/payments/{reported['id']}/receipt",
    ):
        r = await client.get(url, headers=owner.headers)
        assert r.status_code in (200, 503)
        if r.status_code == 503:
            assert r.json()["error"]["code"] == "PDF_UNAVAILABLE"

    # Another flat in the same society stays hidden.
    assert (
        await client.get(f"{base}/my/flats/{other}/bills", headers=owner.headers)
    ).status_code == 404


async def test_tenant_needs_the_owners_permission(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base, flat, _, _, tenant = await _society_with_resident(client, s.a_admin)
    [mine] = (await client.get(f"{base}/my/flats", headers=tenant.headers)).json()
    assert (mine["can_pay"], mine["balance_paise"], mine["pay"], mine["latest_bill"]) == (
        False,
        None,
        None,
        None,
    )
    assert (await client.get(f"{base}/my/flats/{flat}/bills", headers=tenant.headers)).json()[
        "error"
    ]["code"] == "TENANT_CANNOT_PAY"

    await client.post(
        f"{base}/flats/{flat}/members",
        json={
            "full_name": "Tenant B-207",
            "member_type": "tenant",
            "email": tenant.email,
            "tenant_can_pay": True,
        },
        headers=s.a_admin.headers,
    )
    [mine] = (await client.get(f"{base}/my/flats", headers=tenant.headers)).json()
    assert mine["can_pay"] is True and mine["balance_paise"] == 420000


async def test_committee_member_has_no_flats(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    assert (
        await client.get(f"/api/v1/societies/{s.a_id}/my/flats", headers=s.a_admin.headers)
    ).json() == []
