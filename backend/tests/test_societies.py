"""M2 acceptance: sign-in, society setup, invites, consent, isolation (docs/07 M2)."""

from uuid import uuid4

import asyncpg
import pytest

from tests.conftest import APP_URL, SOCIETY_BODY, make_token, needs_db, new_user

pytestmark = needs_db


async def _audit_actions(society_id) -> list[str]:  # noqa: ANN001
    # Read as the app role inside the society's context, the way the API would.
    conn = await asyncpg.connect(APP_URL)
    try:
        async with conn.transaction():
            await conn.execute(
                "SELECT set_config('app.current_society_id', $1, true)", str(society_id)
            )
            rows = await conn.fetch(
                "SELECT action FROM audit_log WHERE society_id = $1 ORDER BY id", society_id
            )
    finally:
        await conn.close()
    return [r["action"] for r in rows]


# --- sign-in -------------------------------------------------------------------------


async def test_no_token_is_401(client) -> None:
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "UNAUTHORIZED", "message_key": "errors.signInAgain"}}


async def test_bad_signature_and_expired_tokens_are_401(client) -> None:
    u = new_user()
    for token in (
        make_token(u.id, u.email, secret="another-secret-that-is-long-enough-000000"),
        make_token(u.id, u.email, expired=True),
    ):
        r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


async def test_first_request_creates_user_with_defaults(client) -> None:
    u = new_user()
    r = await client.get("/api/v1/me", headers=u.headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(u.id)
    assert body["email"] == u.email
    assert body["preferred_language"] == "en"
    assert body["simple_mode"] is True
    assert body["needs_consent"] is True


async def test_update_preferences(client) -> None:
    u = new_user()
    r = await client.patch(
        "/api/v1/me/preferences",
        json={"preferred_language": "mr", "text_size": "xlarge", "simple_mode": False},
        headers=u.headers,
    )
    assert r.status_code == 200
    assert r.json()["preferred_language"] == "mr"
    assert r.json()["text_size"] == "xlarge"
    assert r.json()["simple_mode"] is False
    bad = await client.patch(
        "/api/v1/me/preferences", json={"preferred_language": "fr"}, headers=u.headers
    )
    assert bad.status_code == 422


# --- consent -------------------------------------------------------------------------


async def test_consent_flow(client) -> None:
    u = new_user()
    r = await client.get("/api/v1/me/consents", headers=u.headers)
    assert r.json()["needs_consent"] is True
    r = await client.post(
        "/api/v1/me/consents",
        json={"accept_terms_and_privacy": True, "analytics": False},
        headers=u.headers,
    )
    assert r.status_code == 200
    assert r.json()["needs_consent"] is False
    assert {c["purpose"] for c in r.json()["granted"]} == {"terms", "privacy"}
    # Opting in to analytics later adds a row; opting out again withdraws it.
    r = await client.post(
        "/api/v1/me/consents",
        json={"accept_terms_and_privacy": True, "analytics": True},
        headers=u.headers,
    )
    assert "analytics" in {c["purpose"] for c in r.json()["granted"]}
    r = await client.post(
        "/api/v1/me/consents",
        json={"accept_terms_and_privacy": True, "analytics": False},
        headers=u.headers,
    )
    assert "analytics" not in {c["purpose"] for c in r.json()["granted"]}
    me = await client.get("/api/v1/me", headers=u.headers)
    assert me.json()["needs_consent"] is False


async def test_consent_requires_terms(client) -> None:
    u = new_user()
    r = await client.post(
        "/api/v1/me/consents", json={"accept_terms_and_privacy": False}, headers=u.headers
    )
    assert r.status_code == 422


# --- society setup -------------------------------------------------------------------


async def test_create_society_makes_admin_default_wing_and_audit(client) -> None:
    u = new_user()
    body = {
        **SOCIETY_BODY,
        "invites": [{"name": "Treasurer", "email": "treasurer@example.com", "role": "treasurer"}],
    }
    r = await client.post("/api/v1/societies", json=body, headers=u.headers)
    assert r.status_code == 201, r.text
    data = r.json()
    society_id = data["society"]["id"]
    assert data["society"]["state"] == "Maharashtra"
    assert data["society"]["financial_year_start_month"] == 4
    assert len(data["invites"]) == 1
    assert f"/invite/{society_id}?token=" in data["invites"][0]["invite_link"]

    mine = await client.get("/api/v1/me/societies", headers=u.headers)
    assert [(s["id"], s["roles"]) for s in mine.json()] == [(society_id, ["admin"])]

    members = await client.get(f"/api/v1/societies/{society_id}/memberships", headers=u.headers)
    assert sorted((m["role"], m["status"]) for m in members.json()) == [
        ("admin", "active"),
        ("treasurer", "invited"),
    ]
    assert await _audit_actions(society_id) == [
        "society.create",
        "membership.create",
        "membership.invite",
    ]


@pytest.mark.parametrize(
    ("patch", "where"),
    [
        ({"billing": {"bill_day": 29}}, "bill_day"),
        ({"details": {"name": ""}}, "name"),
        ({"details": {"name": "X", "pincode": "12345"}}, "pincode"),
        ({"billing": {"bill_day": 1, "bank_account_last4": "12a4"}}, "bank_account_last4"),
    ],
)
async def test_create_society_validation(client, patch, where) -> None:  # noqa: ANN001
    body = {**SOCIETY_BODY, **patch}
    r = await client.post("/api/v1/societies", json=body, headers=new_user().headers)
    assert r.status_code == 422
    assert where in r.text


# --- invites -------------------------------------------------------------------------


async def _invite(client, society_id, admin, **fields) -> dict:  # noqa: ANN001
    r = await client.post(
        f"/api/v1/societies/{society_id}/invites", json=fields, headers=admin.headers
    )
    assert r.status_code == 201, r.text
    return r.json()


def _token(link: str) -> str:
    return link.split("token=", 1)[1]


async def test_invite_and_accept(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    invited = new_user("treasurer")
    inv = await _invite(client, s.a_id, s.a_admin, email=invited.email, role="treasurer")

    # Before accepting, the invited person cannot see the society.
    r = await client.get(f"/api/v1/societies/{s.a_id}", headers=invited.headers)
    assert r.status_code == 404

    r = await client.post(
        f"/api/v1/societies/{s.a_id}/invites/accept",
        json={"token": _token(inv["invite_link"])},
        headers=invited.headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"

    r = await client.get(f"/api/v1/societies/{s.a_id}", headers=invited.headers)
    assert r.status_code == 200
    # Treasurer is not admin: invites and member list are admin-only (docs/02 §2).
    r = await client.get(f"/api/v1/societies/{s.a_id}/memberships", headers=invited.headers)
    assert r.status_code == 403

    # The token works once.
    again = await client.post(
        f"/api/v1/societies/{s.a_id}/invites/accept",
        json={"token": _token(inv["invite_link"])},
        headers=invited.headers,
    )
    assert again.status_code == 404
    assert await _audit_actions(s.a_id) == [
        "society.create",
        "membership.create",
        "membership.invite",
        "membership.accept",
    ]


async def test_invite_for_another_email_is_refused(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    inv = await _invite(client, s.a_id, s.a_admin, email="someone@example.com", role="committee")
    r = await client.post(
        f"/api/v1/societies/{s.a_id}/invites/accept",
        json={"token": _token(inv["invite_link"])},
        headers=new_user().headers,
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "INVITE_OTHER_EMAIL"


async def test_invite_token_is_scoped_to_its_society(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    invited = new_user()
    inv = await _invite(client, s.a_id, s.a_admin, email=invited.email, role="committee")
    r = await client.post(
        f"/api/v1/societies/{s.b_id}/invites/accept",
        json={"token": _token(inv["invite_link"])},
        headers=invited.headers,
    )
    assert r.status_code == 404


async def test_invite_rules(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    url = f"/api/v1/societies/{s.a_id}/invites"
    no_contact = await client.post(url, json={"role": "committee"}, headers=s.a_admin.headers)
    assert no_contact.json()["error"]["code"] == "CONTACT_REQUIRED"
    # Resident roles need a flat, and flats arrive in M3.
    resident = await client.post(
        url, json={"role": "owner", "email": "o@example.com"}, headers=s.a_admin.headers
    )
    assert resident.status_code == 422
    phone = await client.post(
        url, json={"role": "committee", "phone_e164": "+919800000000"}, headers=s.a_admin.headers
    )
    assert phone.status_code == 201


# --- isolation: see test_isolation.py ----------------------------------------------


async def test_unknown_society_is_404(client) -> None:
    r = await client.get(f"/api/v1/societies/{uuid4()}", headers=new_user().headers)
    assert r.status_code == 404


async def test_picker_lists_only_own_societies(client, two_societies) -> None:  # noqa: ANN001
    s = two_societies
    r = await client.get("/api/v1/me/societies", headers=s.a_admin.headers)
    assert [x["id"] for x in r.json()] == [str(s.a_id)]
