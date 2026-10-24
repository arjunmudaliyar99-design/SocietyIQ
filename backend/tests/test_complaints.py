"""M8 acceptance: complaints (docs/02 §8, docs/07 M8)."""

from tests.conftest import needs_db, new_user

pytestmark = needs_db

# Smallest valid JPEG and PNG headers; the API checks content, not names.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _join(client, society_id, admin, role: str, flat_id: str | None = None):  # noqa: ANN001, ANN202
    user = new_user(role)
    body = {"role": role, "email": user.email}
    if flat_id:
        body["flat_id"] = flat_id
    inv = await client.post(
        f"/api/v1/societies/{society_id}/invites", json=body, headers=admin.headers
    )
    assert inv.status_code == 201, inv.text
    token = inv.json()["invite_link"].split("token=", 1)[1]
    r = await client.post(
        f"/api/v1/societies/{society_id}/invites/accept",
        json={"token": token},
        headers=user.headers,
    )
    assert r.status_code == 200, r.text
    return user


async def _flat(client, society_id, admin, number: str) -> str:  # noqa: ANN001
    base = f"/api/v1/societies/{society_id}"
    wing = (await client.get(f"{base}/wings", headers=admin.headers)).json()[0]["id"]
    r = await client.post(
        f"{base}/flats", json={"wing_id": wing, "flat_number": number}, headers=admin.headers
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_resident_raises_with_photo_and_sees_only_own(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/complaints"
    flat1 = await _flat(client, s.a_id, s.a_admin, "101")
    flat2 = await _flat(client, s.a_id, s.a_admin, "102")
    owner1 = await _join(client, s.a_id, s.a_admin, "owner", flat1)
    tenant2 = await _join(client, s.a_id, s.a_admin, "tenant", flat2)

    # One flat linked, so the flat is filled in for the resident.
    r = await client.post(
        base,
        json={"category": "water", "location": "my_flat", "description": " Leak in kitchen "},
        headers=owner1.headers,
    )
    assert r.status_code == 201, r.text
    c1 = r.json()
    assert c1["flat_id"] == flat1
    assert c1["status"] == "open"
    assert c1["description"] == "Leak in kitchen"
    assert c1["raised_on_behalf"] is False

    photo = await client.post(
        f"{base}/{c1['id']}/photos",
        files={"file": ("IMG_0001.jpg", JPEG, "image/jpeg")},
        headers=owner1.headers,
    )
    assert photo.status_code == 201, photo.text
    [photo_id] = photo.json()["photo_ids"]
    got = await client.get(f"{base}/{c1['id']}/photos/{photo_id}", headers=owner1.headers)
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/jpeg"
    assert got.content == JPEG

    r2 = await client.post(
        base, json={"category": "lift", "location": "common_area"}, headers=tenant2.headers
    )
    assert r2.status_code == 201, r2.text
    c2 = r2.json()

    mine = (await client.get(base, headers=owner1.headers)).json()
    assert [c["id"] for c in mine] == [c1["id"]]
    # Another flat's complaint and its photo look like they do not exist.
    assert (await client.get(f"{base}/{c2['id']}", headers=owner1.headers)).status_code == 404
    assert (await client.get(f"{base}/{c1['id']}", headers=tenant2.headers)).status_code == 404
    seen = await client.get(f"{base}/{c1['id']}/photos/{photo_id}", headers=tenant2.headers)
    assert seen.status_code == 404
    # Residents cannot raise for a flat they are not linked to.
    other = await client.post(
        base,
        json={"category": "water", "location": "my_flat", "flat_id": flat1},
        headers=tenant2.headers,
    )
    assert other.status_code == 404

    every = (await client.get(base, headers=s.a_admin.headers)).json()
    assert {c["id"] for c in every} == {c1["id"], c2["id"]}


async def test_photo_is_checked_by_content(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/complaints"
    c = (
        await client.post(
            base, json={"category": "other", "location": "common_area"}, headers=s.a_admin.headers
        )
    ).json()
    fake = await client.post(
        f"{base}/{c['id']}/photos",
        files={"file": ("photo.jpg", b"MZ not an image", "image/jpeg")},
        headers=s.a_admin.headers,
    )
    assert fake.status_code == 415
    assert fake.json()["error"]["message_key"] == "errors.notAPhoto"
    for _ in range(3):
        ok = await client.post(
            f"{base}/{c['id']}/photos",
            files={"file": ("p.png", PNG, "image/png")},
            headers=s.a_admin.headers,
        )
        assert ok.status_code == 201
    fourth = await client.post(
        f"{base}/{c['id']}/photos",
        files={"file": ("p.png", PNG, "image/png")},
        headers=s.a_admin.headers,
    )
    assert fourth.status_code == 409


async def test_committee_flow_filters_and_resident_feedback(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/complaints"
    flat = await _flat(client, s.a_id, s.a_admin, "201")
    owner = await _join(client, s.a_id, s.a_admin, "owner", flat)
    committee = await _join(client, s.a_id, s.a_admin, "committee")
    auditor = await _join(client, s.a_id, s.a_admin, "auditor")

    # Raised on behalf of a resident without a phone.
    r = await client.post(
        base,
        json={"category": "electricity", "location": "my_flat", "flat_id": flat},
        headers=committee.headers,
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["raised_on_behalf"] is True
    assert c["can_manage"] is True
    common = await client.post(
        base, json={"category": "cleaning", "location": "common_area"}, headers=committee.headers
    )
    assert common.json()["raised_on_behalf"] is False

    # Residents see on-behalf complaints for their flat.
    assert c["id"] in {x["id"] for x in (await client.get(base, headers=owner.headers)).json()}

    assigned = await client.patch(
        f"{base}/{c['id']}/assignee",
        json={"assigned_to_text": "Electrician (vendor)"},
        headers=committee.headers,
    )
    assert assigned.json()["assigned_to_text"] == "Electrician (vendor)"
    await client.post(
        f"{base}/{c['id']}/updates",
        json={"message": "Vendor visit booked", "new_status": "in_progress"},
        headers=committee.headers,
    )
    await client.post(
        f"{base}/{c['id']}/updates",
        json={"message": "Committee-only note", "visible_to_resident": False},
        headers=committee.headers,
    )

    by_status = await client.get(f"{base}?status=in_progress", headers=committee.headers)
    assert [x["id"] for x in by_status.json()] == [c["id"]]
    open_ = await client.get(f"{base}?status=open", headers=committee.headers)
    assert [x["id"] for x in open_.json()] == [common.json()["id"]]

    resident_view = (await client.get(f"{base}/{c['id']}", headers=owner.headers)).json()
    assert [u["message"] for u in resident_view["updates"]] == ["Vendor visit booked"]
    assert resident_view["can_manage"] is False
    committee_view = (await client.get(f"{base}/{c['id']}", headers=committee.headers)).json()
    assert len(committee_view["updates"]) == 2

    # Residents and auditors cannot manage.
    for user in (owner, auditor):
        no = await client.post(
            f"{base}/{c['id']}/updates", json={"message": "x"}, headers=user.headers
        )
        assert no.status_code == 403
    assert (await client.get(base, headers=auditor.headers)).status_code == 403

    # Feedback only after Resolved.
    early = await client.post(
        f"{base}/{c['id']}/feedback", json={"feedback": "fixed"}, headers=owner.headers
    )
    assert early.status_code == 409
    resolved = await client.post(
        f"{base}/{c['id']}/updates",
        json={"message": "Wiring replaced", "new_status": "resolved"},
        headers=committee.headers,
    )
    assert resolved.json()["resolved_at"] is not None

    not_fixed = await client.post(
        f"{base}/{c['id']}/feedback", json={"feedback": "not_fixed"}, headers=owner.headers
    )
    assert not_fixed.status_code == 200, not_fixed.text
    body = not_fixed.json()
    assert body["status"] == "in_progress"
    assert body["resident_feedback"] == "not_fixed"
    assert body["resolved_at"] is None
    assert body["updates"][-1]["message"] == "complaints.feedback.not_fixed"

    await client.post(
        f"{base}/{c['id']}/updates",
        json={"message": "Fixed again", "new_status": "resolved"},
        headers=committee.headers,
    )
    fixed = await client.post(
        f"{base}/{c['id']}/feedback", json={"feedback": "fixed"}, headers=owner.headers
    )
    assert fixed.json()["status"] == "closed"
    assert fixed.json()["closed_at"] is not None


async def test_status_changes_follow_the_flow(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/complaints"
    h = s.a_admin.headers
    c = (
        await client.post(base, json={"category": "parking", "location": "common_area"}, headers=h)
    ).json()
    closed = await client.post(
        f"{base}/{c['id']}/updates", json={"message": "Done", "new_status": "closed"}, headers=h
    )
    assert closed.json()["status"] == "closed"
    # Closed can only be reopened to In progress, not jumped to Resolved.
    bad = await client.post(
        f"{base}/{c['id']}/updates", json={"message": "x", "new_status": "resolved"}, headers=h
    )
    assert bad.status_code == 409
    assert bad.json()["error"]["message_key"] == "errors.complaintStatusChange"
    # My-flat complaints from the committee must name the flat.
    no_flat = await client.post(base, json={"category": "water", "location": "my_flat"}, headers=h)
    assert no_flat.status_code == 422


async def test_resident_with_two_flats_must_choose(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}"
    f1 = await _flat(client, s.a_id, s.a_admin, "301")
    f2 = await _flat(client, s.a_id, s.a_admin, "302")
    owner = await _join(client, s.a_id, s.a_admin, "owner", f1)
    inv = await client.post(
        f"{base}/invites",
        json={"role": "delegate", "email": owner.email, "flat_id": f2},
        headers=s.a_admin.headers,
    )
    token = inv.json()["invite_link"].split("token=", 1)[1]
    await client.post(f"{base}/invites/accept", json={"token": token}, headers=owner.headers)
    r = await client.post(
        f"{base}/complaints",
        json={"category": "water", "location": "my_flat"},
        headers=owner.headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["message_key"] == "errors.complaintChooseFlat"
    ok = await client.post(
        f"{base}/complaints",
        json={"category": "water", "location": "my_flat", "flat_id": f2},
        headers=owner.headers,
    )
    assert ok.status_code == 201


async def test_society_b_complaints_are_404_inside_society_a(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    b_base = f"/api/v1/societies/{s.b_id}/complaints"
    cb = (
        await client.post(
            b_base, json={"category": "lift", "location": "common_area"}, headers=s.b_admin.headers
        )
    ).json()
    pb = await client.post(
        f"{b_base}/{cb['id']}/photos",
        files={"file": ("p.jpg", JPEG, "image/jpeg")},
        headers=s.b_admin.headers,
    )
    photo_b = pb.json()["photo_ids"][0]

    a_base = f"/api/v1/societies/{s.a_id}/complaints"
    a = s.a_admin.headers
    ca = (
        await client.post(a_base, json={"category": "lift", "location": "common_area"}, headers=a)
    ).json()
    checks = [
        ("GET", f"{a_base}/{cb['id']}", None),
        ("POST", f"{a_base}/{cb['id']}/updates", {"message": "x"}),
        ("PATCH", f"{a_base}/{cb['id']}/assignee", {"assigned_to_text": "x"}),
        ("GET", f"{a_base}/{cb['id']}/photos/{photo_b}", None),
        # B's photo id under A's own complaint.
        ("GET", f"{a_base}/{ca['id']}/photos/{photo_b}", None),
    ]
    for method, url, body in checks:
        r = await client.request(method, url, json=body, headers=a)
        assert r.status_code == 404, (method, url, r.status_code, r.text)
    assert cb["id"] not in {c["id"] for c in (await client.get(a_base, headers=a)).json()}


async def test_every_change_is_audited(client, two_societies) -> None:  # noqa: ANN001
    import asyncpg

    from tests.conftest import OWNER_URL

    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/complaints"
    h = s.a_admin.headers
    c = (
        await client.post(base, json={"category": "security", "location": "common_area"}, headers=h)
    ).json()
    await client.patch(f"{base}/{c['id']}/assignee", json={"assigned_to_text": "Guard"}, headers=h)
    await client.post(
        f"{base}/{c['id']}/updates",
        json={"message": "On it", "new_status": "in_progress"},
        headers=h,
    )
    conn = await asyncpg.connect(OWNER_URL)
    try:
        actions = await conn.fetch(
            "SELECT action FROM audit_log WHERE entity_id = $1 ORDER BY id", c["id"]
        )
    finally:
        await conn.close()
    assert [a["action"] for a in actions] == [
        "complaint.create",
        "complaint.assign",
        "complaint.status",
    ]
