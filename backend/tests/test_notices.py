"""M9 acceptance: notices and email (docs/02 §9, docs/07 M9)."""

import asyncpg

from tests.conftest import OWNER_URL, needs_db, new_user

pytestmark = needs_db


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


async def _setup(client, s):  # noqa: ANN001, ANN202
    """Wing A: 101 (owner with email, tenant with email), 102 (owner without email).
    Wing B: 201 (owner with email, joint owner sharing the same email)."""
    base = f"/api/v1/societies/{s.a_id}"
    h = s.a_admin.headers
    wing_a = (await client.get(f"{base}/wings", headers=h)).json()[0]["id"]
    wing_b = (await client.post(f"{base}/wings", json={"name": "B"}, headers=h)).json()["id"]

    async def flat(wing: str, number: str) -> str:
        r = await client.post(
            f"{base}/flats", json={"wing_id": wing, "flat_number": number}, headers=h
        )
        return r.json()["id"]

    async def member(flat_id: str, name: str, kind: str, email: str | None) -> None:
        body = {"full_name": name, "member_type": kind}
        if email:
            body["email"] = email
        r = await client.post(f"{base}/flats/{flat_id}/members", json=body, headers=h)
        assert r.status_code == 201, r.text

    f101, f102, f201 = (
        await flat(wing_a, "101"),
        await flat(wing_a, "102"),
        await flat(wing_b, "201"),
    )
    await member(f101, "Owner 101", "owner", "owner101@example.com")
    await member(f101, "Tenant 101", "tenant", "tenant101@example.com")
    await member(f102, "Owner 102", "owner", None)
    await member(f201, "Owner 201", "owner", "family201@example.com")
    await member(f201, "Joint 201", "joint_owner", "FAMILY201@example.com")
    return {"wing_a": wing_a, "wing_b": wing_b, "f101": f101, "f201": f201}


async def _log(notice_id: str) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(OWNER_URL)
    try:
        return await conn.fetch(
            "SELECT to_address_masked, status, channel, language FROM notification_log"
            " WHERE source_id = $1 ORDER BY to_address_masked",
            notice_id,
        )
    finally:
        await conn.close()


async def test_publish_sends_one_email_per_member_and_logs_each(client, two_societies) -> None:  # noqa: ANN001
    from app.notify import fake_outbox

    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/notices"
    await _setup(client, s)
    h = s.a_admin.headers

    r = await client.post(
        base, json={"title": "Water cut on Sunday", "body": "No water 10 am to 2 pm."}, headers=h
    )
    assert r.status_code == 201, r.text
    notice = r.json()
    assert notice["status"] == "draft"
    # 3 distinct addresses: owner 101, tenant 101, and the shared family address of 201.
    assert notice["recipient_count"] == 3
    assert notice["emails_sent"] == 0

    outbox = fake_outbox()
    before = len(outbox.sent)
    pub = await client.post(f"{base}/{notice['id']}/publish", headers=h)
    assert pub.status_code == 200, pub.text
    assert pub.json()["status"] == "published"
    assert pub.json()["emails_sent"] == 3

    new = outbox.sent[before:]
    assert sorted(e.to for e in new) == [
        "family201@example.com",
        "owner101@example.com",
        "tenant101@example.com",
    ]
    assert all(e.subject == "Shanti Sadan CHS: Water cut on Sunday" for e in new)
    assert f"/notices/{notice['id']}" in new[0].text

    log = await _log(notice["id"])
    assert [(r["to_address_masked"], r["status"], r["channel"]) for r in log] == [
        ("f***@example.com", "sent", "email"),
        ("o***@example.com", "sent", "email"),
        ("t***@example.com", "sent", "email"),
    ]

    # Published notices are not edited or sent twice.
    again = await client.post(f"{base}/{notice['id']}/publish", headers=h)
    assert again.status_code == 409
    edit = await client.patch(f"{base}/{notice['id']}", json={"title": "X"}, headers=h)
    assert edit.status_code == 409
    assert len(outbox.sent) == before + 3


async def test_audiences(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/notices"
    ids = await _setup(client, s)
    h = s.a_admin.headers

    async def recipients(**audience: str) -> int:
        r = await client.post(base, json={"title": "T", "body": "B", **audience}, headers=h)
        assert r.status_code == 201, r.text
        return r.json()["recipient_count"]

    assert await recipients(audience="owners") == 2
    assert await recipients(audience="tenants") == 1
    assert await recipients(audience="wing", audience_wing_id=ids["wing_a"]) == 2
    assert await recipients(audience="wing", audience_wing_id=ids["wing_b"]) == 1
    no_wing = await client.post(
        base, json={"title": "T", "body": "B", "audience": "wing"}, headers=h
    )
    assert no_wing.status_code == 422


async def test_residents_read_only_published_notices_for_them(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/notices"
    ids = await _setup(client, s)
    h = s.a_admin.headers
    owner = await _join(client, s.a_id, s.a_admin, "owner", ids["f101"])
    tenant = await _join(client, s.a_id, s.a_admin, "tenant", ids["f201"])

    async def publish(**fields: str) -> str:
        n = (await client.post(base, json={"title": "T", "body": "B", **fields}, headers=h)).json()
        await client.post(f"{base}/{n['id']}/publish", headers=h)
        return n["id"]

    for_all = await publish()
    for_owners = await publish(audience="owners")
    for_wing_b = await publish(audience="wing", audience_wing_id=ids["wing_b"])
    draft = (await client.post(base, json={"title": "D", "body": "B"}, headers=h)).json()["id"]

    owner_sees = {n["id"] for n in (await client.get(base, headers=owner.headers)).json()}
    assert owner_sees == {for_all, for_owners}
    tenant_sees = {n["id"] for n in (await client.get(base, headers=tenant.headers)).json()}
    assert tenant_sees == {for_all, for_wing_b}
    assert (await client.get(f"{base}/{draft}", headers=owner.headers)).status_code == 404
    assert (await client.get(f"{base}/{for_wing_b}", headers=owner.headers)).status_code == 404

    # Read receipts: unread until opened; the committee sees the count.
    first = (await client.get(base, headers=owner.headers)).json()
    assert all(n["is_read"] is False for n in first)
    read = await client.post(f"{base}/{for_all}/read", headers=owner.headers)
    assert read.json() == {"read": True}
    await client.post(f"{base}/{for_all}/read", headers=owner.headers)
    await client.post(f"{base}/{for_all}/read", headers=tenant.headers)
    after = {n["id"]: n["is_read"] for n in (await client.get(base, headers=owner.headers)).json()}
    assert after == {for_all: True, for_owners: False}
    detail = (await client.get(f"{base}/{for_all}", headers=h)).json()
    assert detail["read_count"] == 2
    # Residents do not see counts or editing rights.
    resident_detail = (await client.get(f"{base}/{for_all}", headers=owner.headers)).json()
    assert resident_detail["read_count"] is None
    assert resident_detail["can_edit"] is False

    # Residents cannot draft.
    no = await client.post(base, json={"title": "T", "body": "B"}, headers=owner.headers)
    assert no.status_code == 403


async def test_roles_draft_and_publish(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/notices"
    committee = await _join(client, s.a_id, s.a_admin, "committee")
    treasurer = await _join(client, s.a_id, s.a_admin, "treasurer")

    n = await client.post(base, json={"title": "Lift AMC", "body": "B"}, headers=committee.headers)
    assert n.status_code == 201
    nid = n.json()["id"]
    assert n.json()["can_edit"] is True
    assert n.json()["can_publish"] is False
    # Committee members draft but do not publish (docs/02 §2); treasurers do neither.
    assert (
        await client.post(f"{base}/{nid}/publish", headers=committee.headers)
    ).status_code == 403
    assert (
        await client.post(base, json={"title": "T", "body": "B"}, headers=treasurer.headers)
    ).status_code == 403

    pub = await client.post(f"{base}/{nid}/publish", headers=s.a_admin.headers)
    assert pub.status_code == 200
    # Taking a published notice down is the admin's call.
    assert (
        await client.post(f"{base}/{nid}/archive", headers=committee.headers)
    ).status_code == 403
    gone = await client.post(f"{base}/{nid}/archive", headers=s.a_admin.headers)
    assert gone.json()["status"] == "archived"
    draft = (
        await client.post(base, json={"title": "X", "body": "B"}, headers=committee.headers)
    ).json()
    dropped = await client.post(f"{base}/{draft['id']}/archive", headers=committee.headers)
    assert dropped.json()["status"] == "archived"


async def test_ai_help_never_publishes_and_translations_need_review(client, two_societies) -> None:  # noqa: ANN001
    from app.notify import fake_outbox

    s = two_societies
    base = f"/api/v1/societies/{s.a_id}/notices"
    await _setup(client, s)
    h = s.a_admin.headers
    assert (await client.get(f"{base}/options", headers=h)).json() == {
        "ai_available": True,
        "whatsapp_available": False,
    }

    outbox = fake_outbox()
    before = len(outbox.sent)
    draft = await client.post(
        f"{base}/ai-draft",
        json={"notes": "water tank cleaning\nsunday 10 to 2\nstore water", "language": "en"},
        headers=h,
    )
    assert draft.status_code == 200, draft.text
    text = draft.json()
    assert text["title"] == "Water tank cleaning"
    assert "sunday 10 to 2" in text["body"]
    # The AI helper returns text only: nothing saved, nothing sent.
    assert (await client.get(base, headers=h)).json() == []
    assert len(outbox.sent) == before

    n = (await client.post(base, json={**text, "ai_assisted": True}, headers=h)).json()
    assert n["ai_assisted"] is True
    tr = await client.post(f"{base}/{n['id']}/ai-translate", json={"languages": ["mr"]}, headers=h)
    assert tr.status_code == 200, tr.text
    assert tr.json()["translations"]["mr"]["reviewed"] is False
    assert tr.json()["status"] == "draft"
    assert len(outbox.sent) == before

    # Someone who reads Marathi gets the original until a person reviews the translation.
    from app.services.notices import _text_for

    class N:  # the stored shape, without a database round trip
        language = "en"
        title = "Water tank cleaning"
        body = "x"
        translations = {"mr": {"title": "[MR] t", "body": "[MR] b", "status": "draft"}}

    assert _text_for(N, "mr")[2] == "en"
    N.translations["mr"]["status"] = "reviewed"
    assert _text_for(N, "mr") == ("[MR] t", "[MR] b", "mr")

    reviewed = await client.patch(
        f"{base}/{n['id']}",
        json={"translations": {"mr": {"title": "पाण्याची टाकी साफसफाई", "body": "रविवारी"}}},
        headers=h,
    )
    assert reviewed.json()["translations"]["mr"]["reviewed"] is True


async def test_ai_unavailable_in_production(client, two_societies, monkeypatch) -> None:  # noqa: ANN001
    from app.config import get_settings

    s = two_societies
    monkeypatch.setattr(get_settings(), "app_env", "production")
    base = f"/api/v1/societies/{s.a_id}/notices"
    r = await client.post(f"{base}/ai-draft", json={"notes": "abc def"}, headers=s.a_admin.headers)
    assert r.status_code == 503
    assert r.json()["error"]["message_key"] == "errors.aiNotConfigured"


async def test_society_b_notices_are_404_inside_society_a(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    nb = (
        await client.post(
            f"/api/v1/societies/{s.b_id}/notices",
            json={"title": "B notice", "body": "B"},
            headers=s.b_admin.headers,
        )
    ).json()
    a = f"/api/v1/societies/{s.a_id}/notices"
    h = s.a_admin.headers
    for method, url, body in [
        ("GET", f"{a}/{nb['id']}", None),
        ("PATCH", f"{a}/{nb['id']}", {"title": "x"}),
        ("POST", f"{a}/{nb['id']}/publish", None),
        ("POST", f"{a}/{nb['id']}/archive", None),
        ("POST", f"{a}/{nb['id']}/read", None),
        ("POST", f"{a}/{nb['id']}/ai-translate", {"languages": ["hi"]}),
    ]:
        r = await client.request(method, url, json=body, headers=h)
        assert r.status_code == 404, (method, url, r.status_code)
    # A wing of society B cannot be an audience in society A.
    wing_b = (
        await client.get(f"/api/v1/societies/{s.b_id}/wings", headers=s.b_admin.headers)
    ).json()[0]["id"]
    r = await client.post(
        a,
        json={"title": "T", "body": "B", "audience": "wing", "audience_wing_id": wing_b},
        headers=h,
    )
    assert r.status_code == 404


def test_mask_email() -> None:
    from app.notify import mask_email

    assert mask_email("owner101@example.com") == "o***@example.com"
    assert mask_email("not-an-email") == "***"
