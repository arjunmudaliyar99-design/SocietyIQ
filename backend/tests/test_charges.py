"""M4 acceptance (docs/07): the preview shows per-flat totals matching hand calculations for
the seed society; blocked values show the rule reference."""

from datetime import date

from app.auth import dev_user_id
from app.seed.demo import DEMO_ADMIN_EMAIL, run
from tests.conftest import TestUser, needs_db

pytestmark = needs_db

DEMO = TestUser(id=dev_user_id(DEMO_ADMIN_EMAIL), email=DEMO_ADMIN_EMAIL)
NOV = "2026-11-01"


async def _society(client, name: str) -> str:  # noqa: ANN001
    await run()
    mine = (await client.get("/api/v1/me/societies", headers=DEMO.headers)).json()
    return next(s["id"] for s in mine if s["name"] == name)


async def _wing(client, sid: str, headers: dict) -> str:  # noqa: ANN001
    return (await client.get(f"/api/v1/societies/{sid}/wings", headers=headers)).json()[0]["id"]


async def test_seed_society_preview_matches_hand_calculation(client) -> None:  # noqa: ANN001
    sid = await _society(client, "Shanti Sadan CHS")
    r = await client.get(
        f"/api/v1/societies/{sid}/charges/preview",
        params={"period_start": NOV},
        headers=DEMO.headers,
    )
    assert r.status_code == 200, r.text
    p = r.json()
    assert (p["period_start"], p["period_end"]) == ("2026-11-01", "2026-11-30")
    assert p["excluded"] == []
    totals = {f["label"]: f["total_paise"] for f in p["flats"]}
    assert len(totals) == 120
    # ₹3,400 + ₹600 + ₹200 = ₹4,200; A-305 is let out: + ₹340 non-occupancy.
    assert {t for label, t in totals.items() if label != "A-305"} == {420000}
    assert totals["A-305"] == 454000
    by_name = {h["name"]: h["total_paise"] for h in p["heads"]}
    assert by_name == {
        "Service charges": 340000 * 120,
        "Repair and maintenance fund": 60000 * 120,
        "Sinking fund": 20000 * 120,
        "Non-occupancy charges": 34000,
    }
    assert p["total_paise"] == 420000 * 120 + 34000


async def test_blocks_carry_the_rule_reference(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    service = await client.post(
        f"{base}/charges/heads",
        json={
            "name": "Service charges",
            "standard_code": "service",
            "calc_type": "equal_per_flat",
            "period_total_paise": 3000000,
        },
        headers=h,
    )
    assert service.status_code == 201, service.text
    service_id = service.json()["head"]["id"]

    r = await client.post(
        f"{base}/charges/heads",
        json={
            "name": "Non-occupancy",
            "standard_code": "non_occupancy",
            "calc_type": "pct_of_head",
            "percent": "15",
            "percent_of_head_id": service_id,
            "applies_to": "let_out_only",
        },
        headers=h,
    )
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "LEGAL_BLOCK"
    assert error["details"] == [
        {
            "level": "block",
            "key": "nonOccupancyPercent",
            "params": {
                "required": "10",
                "rule": "MCS Rules 106C-12 (2026); earlier Govt order of Aug 2001 under s.79A",
            },
        }
    ]

    interest = await client.patch(
        f"{base}/settings", json={"interest_rate_annual_pct": "13"}, headers=h
    )
    assert interest.json()["error"]["details"][0]["key"] == "interestAboveCap"
    no_resolution = await client.patch(
        f"{base}/settings",
        json={"interest_enabled": True, "interest_rate_annual_pct": "12"},
        headers=h,
    )
    assert no_resolution.json()["error"]["details"][0]["key"] == "interestNeedsResolution"
    ok = await client.patch(
        f"{base}/settings",
        json={
            "interest_enabled": True,
            "interest_rate_annual_pct": "12",
            "interest_gb_resolution_date": "2026-09-20",
        },
        headers=h,
    )
    assert ok.status_code == 200
    assert ok.json()["interest_rate_annual_pct"] == "12.0000"


async def test_warnings_need_a_reason_and_resolution(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    url = f"/api/v1/societies/{s.a_id}/charges/heads"
    low = {
        "name": "Sinking fund",
        "standard_code": "sinking_fund",
        "calc_type": "pct_of_construction_cost",
        "percent": "0.2",
    }
    r = await client.post(url, json=low, headers=h)
    assert r.json()["error"]["code"] == "REASON_REQUIRED"
    r = await client.post(
        url, json={**low, "method_deviation_reason": "GB phasing in over 2 years"}, headers=h
    )
    assert r.status_code == 201
    assert r.json()["warnings"][0]["key"] == "belowFundMinimum"

    other_method = {
        "name": "Lift",
        "standard_code": "lift",
        "calc_type": "equal_per_flat",
        "period_total_paise": 1000,
    }
    r = await client.post(
        url, json={**other_method, "method_deviation_reason": "All wings share one lift"}, headers=h
    )
    assert r.json()["error"]["code"] == "RESOLUTION_REQUIRED"
    r = await client.post(
        url,
        json={
            **other_method,
            "method_deviation_reason": "All wings share one lift",
            "gb_resolution_ref": "GB 2026/4",
        },
        headers=h,
    )
    assert r.status_code == 201
    assert (
        await client.post(
            url,
            json={**other_method, "method_deviation_reason": "x", "gb_resolution_ref": "y"},
            headers=h,
        )
    ).status_code == 409


async def test_overrides_parking_tax_and_missing_data(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    wing = await _wing(client, s.a_id, h)
    flats = []
    for number, area in (("1", "500"), ("2", "650"), ("3", None)):
        body = {"wing_id": wing, "flat_number": number}
        if area:
            body["carpet_area_sqft"] = area
        flats.append((await client.post(f"{base}/flats", json=body, headers=h)).json()["id"])
    f1, f2, f3 = flats

    service = (
        await client.post(
            f"{base}/charges/heads",
            json={
                "name": "Service",
                "standard_code": "service",
                "calc_type": "equal_per_flat",
                "period_total_paise": 300000,
            },
            headers=h,
        )
    ).json()["head"]
    for body in (
        {
            "name": "Insurance",
            "standard_code": "insurance",
            "calc_type": "per_carpet_area",
            "period_total_paise": 11500,
        },
        {"name": "Parking", "standard_code": "parking", "calc_type": "per_parking_allotment"},
        {
            "name": "Property tax",
            "standard_code": "property_tax",
            "calc_type": "as_assessed_per_flat",
        },
    ):
        assert (await client.post(f"{base}/charges/heads", json=body, headers=h)).status_code == 201

    await client.post(
        f"{base}/flats/{f2}/parking",
        json={
            "slot_label": "P-4",
            "slot_type": "stilt",
            "vehicle_type": "four_wheeler",
            "monthly_rate_paise": 50000,
            "from_date": "2026-04-01",
        },
        headers=h,
    )
    exempt_without_reason = await client.post(
        f"{base}/flats/{f1}/property-tax",
        json={
            "authority": "MCGM",
            "financial_year": "2026-27",
            "annual_amount_paise": 0,
            "is_exempt": True,
        },
        headers=h,
    )
    assert exempt_without_reason.json()["error"]["code"] == "EXEMPTION_REASON"
    await client.post(
        f"{base}/flats/{f1}/property-tax",
        json={
            "authority": "MCGM",
            "financial_year": "2026-27",
            "annual_amount_paise": 0,
            "is_exempt": True,
            "exemption_reason": "MCGM residential ≤500 sq ft carpet",
        },
        headers=h,
    )
    await client.post(
        f"{base}/flats/{f2}/property-tax",
        json={"authority": "MCGM", "financial_year": "2026-27", "annual_amount_paise": 1200000},
        headers=h,
    )
    override = await client.post(
        f"{base}/flats/{f2}/overrides",
        json={
            "charge_head_id": service["id"],
            "amount_paise": 50000,
            "reason": "Hardship relief per GB 2026/7",
            "valid_from": "2026-11-01",
        },
        headers=h,
    )
    assert override.status_code == 201

    p = (
        await client.get(f"{base}/charges/preview", params={"period_start": NOV}, headers=h)
    ).json()
    assert p["excluded"] == [{"flat_id": f3, "label": "3", "reasons": ["missingCarpetArea"]}]
    assert p["missing"]["carpet_area"] == 1
    flats_out = {f["label"]: f for f in p["flats"]}
    # Service ₹3,000 split over the 2 billed flats; flat 2 overridden to ₹500.
    assert flats_out["1"]["lines"][service["id"]] == 150000
    assert flats_out["2"]["lines"][service["id"]] == 50000
    assert flats_out["2"]["overridden"] == [service["id"]]
    # Insurance ₹115 by carpet area 500:650 → 50 and 65.
    names = {h["id"]: h["name"] for h in p["heads"]}
    lines2 = {names[k]: v for k, v in flats_out["2"]["lines"].items()}
    lines1 = {names[k]: v for k, v in flats_out["1"]["lines"].items()}
    assert lines1 == {"Service": 150000, "Insurance": 5000, "Parking": 0, "Property tax": 0}
    assert lines2 == {"Service": 50000, "Insurance": 6500, "Parking": 50000, "Property tax": 100000}

    # Ending the override restores the computed amount from the next period.
    oid = override.json()["id"]
    ended = await client.patch(
        f"{base}/flats/{f2}/overrides/{oid}", json={"end_date": "2026-11-30"}, headers=h
    )
    assert ended.json()["valid_to"] == "2026-11-30"
    dec = (
        await client.get(
            f"{base}/charges/preview", params={"period_start": "2026-12-01"}, headers=h
        )
    ).json()
    assert {f["label"]: f["lines"][service["id"]] for f in dec["flats"]}["2"] == 150000


async def test_period_must_start_on_the_first(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    r = await client.get(
        f"/api/v1/societies/{s.a_id}/charges/preview",
        params={"period_start": "2026-11-15"},
        headers=s.a_admin.headers,
    )
    assert r.json()["error"]["code"] == "PERIOD_START"


async def test_quarterly_society_previews_a_quarter(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    await client.patch(
        f"/api/v1/societies/{s.a_id}/settings", json={"billing_frequency": "quarterly"}, headers=h
    )
    p = (
        await client.get(
            f"/api/v1/societies/{s.a_id}/charges/preview",
            params={"period_start": "2026-10-01"},
            headers=h,
        )
    ).json()
    assert (p["period_start"], p["period_end"]) == ("2026-10-01", "2026-12-31")


async def test_settings_are_admin_only_and_committee_can_view(client, two_societies) -> None:  # noqa: ANN001
    from tests.test_flats import _join

    s = two_societies
    committee = await _join(client, s.a_id, s.a_admin, "committee")
    base = f"/api/v1/societies/{s.a_id}"
    assert (
        await client.get(
            f"{base}/charges/preview", params={"period_start": NOV}, headers=committee.headers
        )
    ).status_code == 200
    assert (await client.get(f"{base}/charges/heads", headers=committee.headers)).status_code == 200
    r = await client.post(
        f"{base}/charges/heads",
        json={
            "name": "S",
            "standard_code": "service",
            "calc_type": "equal_per_flat",
            "period_total_paise": 1,
        },
        headers=committee.headers,
    )
    assert r.status_code == 403
    treasurer = await _join(client, s.a_id, s.a_admin, "treasurer")
    assert (
        await client.patch(f"{base}/settings", json={"due_days": 10}, headers=treasurer.headers)
    ).status_code == 403


def test_financial_year_label() -> None:
    from app.services.charges import financial_year

    assert financial_year(date(2026, 11, 1), 4) == "2026-27"
    assert financial_year(date(2027, 3, 1), 4) == "2026-27"
    assert financial_year(date(2027, 4, 1), 4) == "2027-28"


async def test_property_tax_import(client, two_societies) -> None:  # noqa: ANN001
    import io

    from openpyxl import load_workbook

    s = two_societies
    h = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    wing = await _wing(client, s.a_id, h)
    for number in ("101", "102"):
        await client.post(f"{base}/flats", json={"wing_id": wing, "flat_number": number}, headers=h)

    template = await client.get(f"{base}/property-tax/template", headers=h)
    wb = load_workbook(io.BytesIO(template.content))
    ws = wb["Property tax"]
    ws.append([None, "101", "MCGM", "2026-27", 12000, "N", None])
    ws.append([None, "102", "MCGM", "2026-27", None, "Y", "MCGM residential ≤500 sq ft carpet"])
    ws.append([None, "999", "MCGM", "2026-27", 5000, "N", None])
    buf = io.BytesIO()
    wb.save(buf)

    r = await client.post(
        f"{base}/property-tax/imports",
        files={"file": ("tax.xlsx", buf.getvalue(), "application/octet-stream")},
        headers=h,
    )
    assert r.status_code == 201, r.text
    job = r.json()
    assert [row["status"] for row in job["rows"]] == ["ok", "ok", "error"]
    assert job["rows"][2]["issues"][0]["key"] == "flatNotFound"
    done = (await client.post(f"{base}/property-tax/imports/{job['id']}/confirm", headers=h)).json()
    assert done["ok_count"] == 2

    await client.post(
        f"{base}/charges/heads",
        json={
            "name": "Property tax",
            "standard_code": "property_tax",
            "calc_type": "as_assessed_per_flat",
        },
        headers=h,
    )
    p = (
        await client.get(f"{base}/charges/preview", params={"period_start": NOV}, headers=h)
    ).json()
    assert {f["label"]: f["charges_paise"] for f in p["flats"]} == {"101": 100000, "102": 0}


async def test_standard_heads_carry_legal_percent_from_the_table(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    r = await client.get(
        f"/api/v1/societies/{s.a_id}/charges/standard-heads", headers=s.a_admin.headers
    )
    by_code = {h["standard_code"]: h for h in r.json()}
    assert by_code["non_occupancy"]["legal_percent"] == "10"
    assert by_code["non_occupancy"]["legal_percent_kind"] == "fixed"
    assert by_code["sinking_fund"]["legal_percent"] == "0.25"
    assert by_code["repair_fund"]["legal_percent_kind"] == "minimum"
    assert by_code["service"]["legal_percent"] is None
