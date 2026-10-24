"""M3: wings, flats and members (docs/02 §4)."""

from tests.conftest import needs_db, new_user

pytestmark = needs_db


async def _join(client, society_id, admin, role: str):  # noqa: ANN001, ANN202
    """A new user with the given committee role in the society."""
    user = new_user(role)
    inv = await client.post(
        f"/api/v1/societies/{society_id}/invites",
        json={"role": role, "email": user.email},
        headers=admin.headers,
    )
    token = inv.json()["invite_link"].split("token=", 1)[1]
    r = await client.post(
        f"/api/v1/societies/{society_id}/invites/accept",
        json={"token": token},
        headers=user.headers,
    )
    assert r.status_code == 200, r.text
    return user


async def _default_wing(client, society_id, admin) -> str:  # noqa: ANN001
    wings = (
        await client.get(f"/api/v1/societies/{society_id}/wings", headers=admin.headers)
    ).json()
    return wings[0]["id"]


async def test_wings(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/wings"
    h = s.a_admin.headers
    assert [w["name"] for w in (await client.get(base, headers=h)).json()] == ["Main"]

    r = await client.post(base, json={"name": "B", "has_lift": True}, headers=h)
    assert r.status_code == 201
    wing_id = r.json()["id"]
    dup = await client.post(base, json={"name": "b"}, headers=h)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "WING_EXISTS"

    r = await client.patch(f"{base}/{wing_id}", json={"has_lift": False}, headers=h)
    assert r.json()["has_lift"] is False


async def test_flat_and_members(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    wing = await _default_wing(client, s.a_id, s.a_admin)

    r = await client.post(
        f"{base}/flats",
        json={
            "wing_id": wing,
            "flat_number": "B-207",
            "carpet_area_sqft": "650.5",
            "certified_construction_cost_paise": 96000000,
            "occupancy": "let_out",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    flat = r.json()
    assert flat["carpet_area_sqft"] == "650.50"

    dup = await client.post(
        f"{base}/flats", json={"wing_id": wing, "flat_number": "b-207"}, headers=h
    )
    assert dup.json()["error"]["code"] == "FLAT_EXISTS"

    owner = await client.post(
        f"{base}/flats/{flat['id']}/members",
        json={
            "full_name": "Member B-207",
            "member_type": "owner",
            "is_primary": True,
            "phone_e164": "+919800000000",
        },
        headers=h,
    )
    assert owner.status_code == 201, owner.text
    await client.post(
        f"{base}/flats/{flat['id']}/members",
        json={"full_name": "Tenant B-207", "member_type": "tenant"},
        headers=h,
    )

    detail = (await client.get(f"{base}/flats/{flat['id']}", headers=h)).json()
    assert detail["primary_member"] == "Member B-207"
    assert detail["balance_paise"] == 0
    assert [m["full_name"] for m in detail["members"]] == ["Member B-207", "Tenant B-207"]

    listed = (await client.get(f"{base}/flats", headers=h)).json()
    assert [(f["flat_number"], f["wing_name"]) for f in listed] == [("B-207", "Main")]

    bad_dates = await client.patch(
        f"{base}/flats/{flat['id']}/members/{owner.json()['id']}",
        json={"from_date": "2026-05-01", "to_date": "2026-04-01"},
        headers=h,
    )
    assert bad_dates.status_code == 422

    moved_out = await client.patch(
        f"{base}/flats/{flat['id']}/members/{owner.json()['id']}",
        json={"to_date": "2026-10-01"},
        headers=h,
    )
    assert moved_out.json()["to_date"] == "2026-10-01"

    bad_phone = await client.post(
        f"{base}/flats/{flat['id']}/members",
        json={"full_name": "X", "member_type": "owner", "phone_e164": "98000"},
        headers=h,
    )
    assert bad_phone.status_code == 422


async def test_committee_and_auditor_can_view_but_not_change(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}"
    wing = await _default_wing(client, s.a_id, s.a_admin)
    for role in ("committee", "auditor"):
        user = await _join(client, s.a_id, s.a_admin, role)
        assert (await client.get(f"{base}/flats", headers=user.headers)).status_code == 200
        r = await client.post(
            f"{base}/flats", json={"wing_id": wing, "flat_number": role}, headers=user.headers
        )
        assert r.status_code == 403
        r = await client.post(f"{base}/wings", json={"name": role}, headers=user.headers)
        assert r.status_code == 403
        r = await client.get(f"{base}/imports/template", headers=user.headers)
        assert r.status_code == 403


async def test_treasurer_can_manage(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    treasurer = await _join(client, s.a_id, s.a_admin, "treasurer")
    wing = await _default_wing(client, s.a_id, s.a_admin)
    r = await client.post(
        f"/api/v1/societies/{s.a_id}/flats",
        json={"wing_id": wing, "flat_number": "T-1"},
        headers=treasurer.headers,
    )
    assert r.status_code == 201


async def test_resident_invite_needs_a_flat_and_opens_the_pwa(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    h = s.a_admin.headers
    base = f"/api/v1/societies/{s.a_id}"
    wing = await _default_wing(client, s.a_id, s.a_admin)
    flat = (
        await client.post(f"{base}/flats", json={"wing_id": wing, "flat_number": "R-1"}, headers=h)
    ).json()

    no_flat = await client.post(
        f"{base}/invites", json={"role": "owner", "email": "o@example.com"}, headers=h
    )
    assert no_flat.json()["error"]["code"] == "FLAT_REQUIRED"
    committee_with_flat = await client.post(
        f"{base}/invites",
        json={"role": "committee", "email": "c@example.com", "flat_id": flat["id"]},
        headers=h,
    )
    assert committee_with_flat.json()["error"]["code"] == "FLAT_NOT_ALLOWED"

    owner = new_user("owner")
    inv = await client.post(
        f"{base}/invites",
        json={"role": "owner", "email": owner.email, "flat_id": flat["id"]},
        headers=h,
    )
    assert inv.status_code == 201, inv.text
    link = inv.json()["invite_link"]
    assert link.startswith("http://localhost:5174/invite/")
    accepted = await client.post(
        f"{base}/invites/accept", json={"token": link.split("token=", 1)[1]}, headers=owner.headers
    )
    assert accepted.json()["flat_id"] == flat["id"]
    # Residents do not see the committee's flat list.
    assert (await client.get(f"{base}/flats", headers=owner.headers)).status_code == 403
