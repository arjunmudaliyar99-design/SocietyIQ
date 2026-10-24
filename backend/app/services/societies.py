"""Societies, invites and memberships (docs/02 §2-3, docs/04 §6, docs/05 §1)."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import set_society_context
from app.errors import AppError, not_found
from app.models import Society, SocietyMembership, User, Wing
from app.services import audit

COMMITTEE_ROLES = ("admin", "treasurer", "committee", "consultant", "auditor")
# Flats arrive in M3; until then resident roles cannot be invited.
FLAT_ROLES = ("owner", "tenant", "delegate")

# docs/05 §2: create one default wing when a society has no wings. The name is ours.
DEFAULT_WING_NAME = "Main"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def active_roles(session: AsyncSession, society_id: UUID, user_id: UUID) -> set[str]:
    rows = await session.scalars(
        select(SocietyMembership.role).where(
            SocietyMembership.society_id == society_id,
            SocietyMembership.user_id == user_id,
            SocietyMembership.status == "active",
        )
    )
    return set(rows)


@dataclass
class MySociety:
    society: Society
    roles: list[str]


async def list_my_societies(session: AsyncSession, user: User) -> list[MySociety]:
    """Society picker. Runs without a society context; RLS shows only the user's own
    memberships and the societies they are active in."""
    rows = await session.execute(
        select(Society, SocietyMembership.role)
        .join(SocietyMembership, SocietyMembership.society_id == Society.id)
        .where(SocietyMembership.user_id == user.id, SocietyMembership.status == "active")
        .order_by(Society.name)
    )
    result: dict[UUID, MySociety] = {}
    for society, role in rows:
        result.setdefault(society.id, MySociety(society, [])).roles.append(role)
    return list(result.values())


@dataclass
class InviteInput:
    role: str
    name: str | None
    email: str | None
    phone_e164: str | None


@dataclass
class CreatedInvite:
    membership: SocietyMembership
    token: str
    link: str


def _invite_link(society_id: UUID, token: str) -> str:
    return f"{get_settings().committee_web_url}/invite/{society_id}?token={token}"


def _membership_snapshot(m: SocietyMembership) -> dict[str, Any]:
    # Never put the token or its hash in the audit log.
    return {
        "role": m.role,
        "status": m.status,
        "user_id": str(m.user_id) if m.user_id else None,
        "invited_name": m.invited_name,
        "invited_email": m.invited_email,
        "invited_phone_e164": m.invited_phone_e164,
    }


async def create_invite(
    session: AsyncSession, society_id: UUID, actor: User, invite: InviteInput
) -> CreatedInvite:
    if invite.role in FLAT_ROLES:
        raise AppError(422, "FLAT_REQUIRED", "errors.inviteNeedsFlat")
    if not invite.email and not invite.phone_e164:
        raise AppError(422, "CONTACT_REQUIRED", "errors.inviteNeedsContact")
    token = secrets.token_urlsafe(32)
    membership = SocietyMembership(
        society_id=society_id,
        role=invite.role,
        status="invited",
        invited_name=invite.name,
        invited_email=invite.email.lower() if invite.email else None,
        invited_phone_e164=invite.phone_e164,
        invite_token_hash=_hash_token(token),
        invite_expires_at=datetime.now(UTC) + timedelta(days=get_settings().invite_expiry_days),
        created_by=actor.id,
    )
    session.add(membership)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="membership.invite",
        entity_type="society_membership",
        entity_id=membership.id,
        after=_membership_snapshot(membership),
    )
    return CreatedInvite(membership, token, _invite_link(society_id, token))


SOCIETY_FIELDS = (
    "name",
    "registration_number",
    "address_line",
    "city",
    "state",
    "pincode",
    "financial_year_start_month",
    "billing_frequency",
    "bill_day",
    "due_days",
    "upi_id",
    "upi_payee_name",
    "bank_name",
    "bank_account_last4",
)


async def create_society(
    session: AsyncSession,
    creator: User,
    fields: dict[str, Any],
    invites: list[InviteInput],
) -> tuple[Society, list[CreatedInvite]]:
    """Steps 1-3 of the setup wizard saved together: the society, its default wing, the
    creator as admin, and the committee invites."""
    society_id = uuid4()
    # RLS only allows writing rows of the current society, so set it before the insert.
    await set_society_context(session, society_id)
    society = Society(id=society_id, created_by=creator.id, **fields)
    session.add(society)
    await session.flush()
    session.add(Wing(society_id=society_id, name=DEFAULT_WING_NAME, created_by=creator.id))
    admin = SocietyMembership(
        society_id=society_id,
        user_id=creator.id,
        role="admin",
        status="active",
        invited_name=creator.full_name,
        invited_email=creator.email,
        created_by=creator.id,
    )
    session.add(admin)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=creator.id,
        action="society.create",
        entity_type="society",
        entity_id=society_id,
        after={k: v for k, v in fields.items() if v is not None},
    )
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=creator.id,
        action="membership.create",
        entity_type="society_membership",
        entity_id=admin.id,
        after=_membership_snapshot(admin),
    )
    created = [await create_invite(session, society_id, creator, i) for i in invites]
    await session.refresh(society)
    return society, created


async def get_society(session: AsyncSession, society_id: UUID) -> Society:
    society = await session.get(Society, society_id)
    if society is None:
        raise not_found()
    return society


async def list_memberships(session: AsyncSession, society_id: UUID) -> list[SocietyMembership]:
    rows = await session.scalars(
        select(SocietyMembership)
        .where(SocietyMembership.society_id == society_id)
        .order_by(SocietyMembership.created_at)
    )
    return list(rows)


async def accept_invite(
    session: AsyncSession, society_id: UUID, user: User, token: str
) -> SocietyMembership:
    await set_society_context(session, society_id)
    membership = await session.scalar(
        select(SocietyMembership).where(
            SocietyMembership.society_id == society_id,
            SocietyMembership.invite_token_hash == _hash_token(token),
            SocietyMembership.status == "invited",
        )
    )
    if membership is None:
        raise not_found()
    if membership.invite_expires_at and membership.invite_expires_at < datetime.now(UTC):
        raise AppError(410, "INVITE_EXPIRED", "errors.inviteExpired")
    # An invite sent to an email address is only for that address.
    if membership.invited_email and membership.invited_email != (user.email or "").lower():
        raise AppError(403, "INVITE_OTHER_EMAIL", "errors.inviteOtherEmail")
    if membership.role in await active_roles(session, society_id, user.id):
        raise AppError(409, "ALREADY_MEMBER", "errors.alreadyMember")
    before = _membership_snapshot(membership)
    membership.user_id = user.id
    membership.status = "active"
    membership.invite_token_hash = None
    if not membership.invited_name:
        membership.invited_name = user.full_name
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=user.id,
        action="membership.accept",
        entity_type="society_membership",
        entity_id=membership.id,
        before=before,
        after=_membership_snapshot(membership),
    )
    return membership
