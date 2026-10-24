"""Society A must never see Society B (docs/04 §6, CLAUDE.md §4.4).

Every route under /societies/{society_id} is listed here with a valid request. A new route
that is not listed fails test_every_society_route_is_covered, so isolation is tested for
every endpoint without anyone having to remember.
"""

from uuid import uuid4

from tests.conftest import needs_db

pytestmark = needs_db

FILE = "multipart-file"
ANY_ID = str(uuid4())

SOCIETY_ROUTES: dict[tuple[str, str], object] = {
    ("GET", "/api/v1/societies/{society_id}/payments"): None,
    ("POST", "/api/v1/societies/{society_id}/payments"): {
        "flat_id": ANY_ID,
        "amount_paise": 100,
        "method": "cash",
        "received_on": "2026-11-01",
    },
    ("GET", "/api/v1/societies/{society_id}/payments/{payment_id}"): None,
    ("POST", "/api/v1/societies/{society_id}/payments/{payment_id}/confirm"): None,
    ("POST", "/api/v1/societies/{society_id}/payments/{payment_id}/bounce"): {"reason": "test"},
    ("POST", "/api/v1/societies/{society_id}/payments/{payment_id}/reverse"): {"reason": "test"},
    ("GET", "/api/v1/societies/{society_id}/payments/{payment_id}/receipt"): None,
    ("GET", "/api/v1/societies/{society_id}/dues"): None,
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}/ledger"): None,
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}/ledger/export"): None,
    ("POST", "/api/v1/societies/{society_id}/flats/{flat_id}/payment-reports"): {
        "amount_paise": 100,
        "received_on": "2026-11-01",
    },
    ("GET", "/api/v1/societies/{society_id}"): None,
    ("GET", "/api/v1/societies/{society_id}/memberships"): None,
    ("POST", "/api/v1/societies/{society_id}/invites"): {
        "role": "committee",
        "email": "x@example.com",
    },
    ("POST", "/api/v1/societies/{society_id}/invites/accept"): {"token": "x" * 43},
    ("GET", "/api/v1/societies/{society_id}/wings"): None,
    ("POST", "/api/v1/societies/{society_id}/wings"): {"name": "Z"},
    ("PATCH", "/api/v1/societies/{society_id}/wings/{wing_id}"): {"has_lift": True},
    ("GET", "/api/v1/societies/{society_id}/flats"): None,
    ("POST", "/api/v1/societies/{society_id}/flats"): {"wing_id": ANY_ID, "flat_number": "1"},
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}"): None,
    ("PATCH", "/api/v1/societies/{society_id}/flats/{flat_id}"): {"flat_type": "1BHK"},
    ("POST", "/api/v1/societies/{society_id}/flats/{flat_id}/members"): {
        "full_name": "Member",
        "member_type": "owner",
    },
    ("PATCH", "/api/v1/societies/{society_id}/flats/{flat_id}/members/{member_id}"): {
        "full_name": "Member"
    },
    ("GET", "/api/v1/societies/{society_id}/imports/template"): None,
    ("POST", "/api/v1/societies/{society_id}/imports"): FILE,
    ("GET", "/api/v1/societies/{society_id}/imports/{job_id}"): None,
    ("POST", "/api/v1/societies/{society_id}/imports/{job_id}/confirm"): None,
    ("GET", "/api/v1/societies/{society_id}/settings"): None,
    ("PATCH", "/api/v1/societies/{society_id}/settings"): {"due_days": 10},
    ("GET", "/api/v1/societies/{society_id}/charges/standard-heads"): None,
    ("GET", "/api/v1/societies/{society_id}/charges/heads"): None,
    ("POST", "/api/v1/societies/{society_id}/charges/heads"): {
        "name": "Service",
        "standard_code": "service",
        "calc_type": "equal_per_flat",
        "period_total_paise": 100,
    },
    ("PATCH", "/api/v1/societies/{society_id}/charges/heads/{head_id}"): {"sort_order": 2},
    ("GET", "/api/v1/societies/{society_id}/charges/preview"): None,
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}/overrides"): None,
    ("POST", "/api/v1/societies/{society_id}/flats/{flat_id}/overrides"): {
        "charge_head_id": ANY_ID,
        "amount_paise": 1,
        "reason": "test reason",
        "valid_from": "2026-11-01",
    },
    ("PATCH", "/api/v1/societies/{society_id}/flats/{flat_id}/overrides/{override_id}"): {
        "end_date": "2026-11-30"
    },
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}/parking"): None,
    ("POST", "/api/v1/societies/{society_id}/flats/{flat_id}/parking"): {
        "slot_label": "P1",
        "slot_type": "open",
        "vehicle_type": "two_wheeler",
        "monthly_rate_paise": 100,
        "from_date": "2026-11-01",
    },
    ("PATCH", "/api/v1/societies/{society_id}/flats/{flat_id}/parking/{allotment_id}"): {
        "end_date": "2026-11-30"
    },
    ("GET", "/api/v1/societies/{society_id}/billing-runs"): None,
    ("POST", "/api/v1/societies/{society_id}/billing-runs"): {"period_start": "2026-11-01"},
    ("GET", "/api/v1/societies/{society_id}/billing-runs/{run_id}"): None,
    ("POST", "/api/v1/societies/{society_id}/billing-runs/{run_id}/approve"): None,
    ("POST", "/api/v1/societies/{society_id}/billing-runs/{run_id}/cancel"): {"reason": "test"},
    ("GET", "/api/v1/societies/{society_id}/billing-runs/{run_id}/pdf"): None,
    ("GET", "/api/v1/societies/{society_id}/bills"): None,
    ("GET", "/api/v1/societies/{society_id}/bills/{bill_id}"): None,
    ("POST", "/api/v1/societies/{society_id}/bills/{bill_id}/cancel"): {"reason": "test"},
    ("POST", "/api/v1/societies/{society_id}/bills/{bill_id}/reissue"): None,
    ("GET", "/api/v1/societies/{society_id}/bills/{bill_id}/pdf"): None,
    ("GET", "/api/v1/societies/{society_id}/property-tax/template"): None,
    ("POST", "/api/v1/societies/{society_id}/property-tax/imports"): FILE,
    ("POST", "/api/v1/societies/{society_id}/property-tax/imports/{job_id}/confirm"): None,
    ("GET", "/api/v1/societies/{society_id}/flats/{flat_id}/property-tax"): None,
    ("POST", "/api/v1/societies/{society_id}/flats/{flat_id}/property-tax"): {
        "authority": "MCGM",
        "financial_year": "2026-27",
        "annual_amount_paise": 100,
    },
    ("GET", "/api/v1/societies/{society_id}/complaints"): None,
    ("POST", "/api/v1/societies/{society_id}/complaints"): {
        "category": "water",
        "location": "common_area",
    },
    ("GET", "/api/v1/societies/{society_id}/complaints/{complaint_id}"): None,
    ("POST", "/api/v1/societies/{society_id}/complaints/{complaint_id}/updates"): {"message": "x"},
    ("PATCH", "/api/v1/societies/{society_id}/complaints/{complaint_id}/assignee"): {
        "assigned_to_text": "x"
    },
    ("POST", "/api/v1/societies/{society_id}/complaints/{complaint_id}/feedback"): {
        "feedback": "fixed"
    },
    ("POST", "/api/v1/societies/{society_id}/complaints/{complaint_id}/photos"): FILE,
    (
        "GET",
        "/api/v1/societies/{society_id}/complaints/{complaint_id}/photos/{attachment_id}",
    ): None,
}


def test_every_society_route_is_covered() -> None:
    from app.main import app

    found = {
        (method.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        if "{society_id}" in path
        for method in ops
    }
    assert found == set(SOCIETY_ROUTES)


def _url(path: str, society_id: object) -> str:
    url = path.replace("{society_id}", str(society_id))
    for name in (
        "wing_id",
        "flat_id",
        "member_id",
        "job_id",
        "head_id",
        "override_id",
        "allotment_id",
        "complaint_id",
        "attachment_id",
    ):
        url = url.replace("{" + name + "}", ANY_ID)
    if url.endswith("/charges/preview"):
        url += "?period_start=2026-11-01"
    return url


async def _call(client, method: str, url: str, body: object, headers: dict):  # noqa: ANN001, ANN202
    if body == FILE:
        files = {"file": ("flats.xlsx", b"PK\x03\x04not-really", "application/octet-stream")}
        return await client.request(method, url, files=files, headers=headers)
    return await client.request(method, url, json=body, headers=headers)


async def test_society_a_user_gets_404_on_every_society_b_route(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    for (method, path), body in SOCIETY_ROUTES.items():
        r = await _call(client, method, _url(path, s.b_id), body, s.a_admin.headers)
        assert r.status_code == 404, (method, path, r.status_code, r.text)


async def test_society_b_records_are_404_inside_society_a(client, two_societies) -> None:  # noqa: ANN001
    """Using B's record ids under A's own society path must not reach B's rows."""
    s = two_societies
    b = s.b_admin.headers
    wing_b = (await client.get(f"/api/v1/societies/{s.b_id}/wings", headers=b)).json()[0]["id"]
    flat_b = await client.post(
        f"/api/v1/societies/{s.b_id}/flats",
        json={"wing_id": wing_b, "flat_number": "B-1"},
        headers=b,
    )
    flat_b_id = flat_b.json()["id"]
    member_b = await client.post(
        f"/api/v1/societies/{s.b_id}/flats/{flat_b_id}/members",
        json={"full_name": "Member B-1", "member_type": "owner"},
        headers=b,
    )
    member_b_id = member_b.json()["id"]

    a = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    checks = [
        ("GET", f"{base}/flats/{flat_b_id}", None),
        ("PATCH", f"{base}/flats/{flat_b_id}", {"flat_type": "2BHK"}),
        ("PATCH", f"{base}/wings/{wing_b}", {"has_lift": True}),
        ("POST", f"{base}/flats", {"wing_id": wing_b, "flat_number": "X"}),
        ("POST", f"{base}/flats/{flat_b_id}/members", {"full_name": "X", "member_type": "owner"}),
        ("PATCH", f"{base}/flats/{flat_b_id}/members/{member_b_id}", {"full_name": "X"}),
    ]
    for method, url, body in checks:
        r = await client.request(method, url, json=body, headers=a)
        assert r.status_code == 404, (method, url, r.status_code, r.text)
    # B's flat is not in A's list either.
    flats_a = (await client.get(f"{base}/flats", headers=a)).json()
    assert flat_b_id not in {f["id"] for f in flats_a}
