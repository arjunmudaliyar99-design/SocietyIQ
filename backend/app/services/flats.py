"""Wings, flats and members (docs/02 §4, docs/05 §2). Every change is audited."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError, not_found
from app.models import Flat, Member, User, Wing
from app.services import audit, ledger

# docs/02 §2: flats, members and import are managed by admin, treasurer and consultant;
# committee members and auditors can view.
MANAGE_ROLES = ("admin", "treasurer", "consultant")
VIEW_ROLES = (*MANAGE_ROLES, "committee", "auditor")

FLAT_FIELDS = (
    "wing_id",
    "flat_number",
    "carpet_area_sqft",
    "flat_type",
    "usage",
    "certified_construction_cost_paise",
    "water_points",
    "municipal_property_account",
    "occupancy",
    "is_active",
)
MEMBER_FIELDS = (
    "full_name",
    "phone_e164",
    "email",
    "member_type",
    "is_primary",
    "from_date",
    "to_date",
    "tenant_can_pay",
)


def _jsonable(value: object) -> object:
    if isinstance(value, UUID | date):
        return str(value)
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return value


def snapshot(obj: object, fields: tuple[str, ...]) -> dict[str, Any]:
    return {f: _jsonable(getattr(obj, f)) for f in fields}


# --- wings ---------------------------------------------------------------------------


async def list_wings(session: AsyncSession, society_id: UUID) -> list[Wing]:
    rows = await session.scalars(
        select(Wing).where(Wing.society_id == society_id).order_by(Wing.name)
    )
    return list(rows)


async def _wing_name_taken(
    session: AsyncSession, society_id: UUID, name: str, except_id: UUID | None = None
) -> bool:
    query = select(Wing.id).where(
        Wing.society_id == society_id, func.lower(Wing.name) == name.strip().lower()
    )
    if except_id:
        query = query.where(Wing.id != except_id)
    return (await session.scalar(query)) is not None


async def create_wing(
    session: AsyncSession, society_id: UUID, actor: User, name: str, has_lift: bool
) -> Wing:
    if await _wing_name_taken(session, society_id, name):
        raise AppError(409, "WING_EXISTS", "errors.wingExists")
    wing = Wing(society_id=society_id, name=name.strip(), has_lift=has_lift, created_by=actor.id)
    session.add(wing)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="wing.create",
        entity_type="wing",
        entity_id=wing.id,
        after={"name": wing.name, "has_lift": has_lift},
    )
    return wing


async def get_wing(session: AsyncSession, society_id: UUID, wing_id: UUID) -> Wing:
    wing = await session.get(Wing, wing_id)
    if wing is None or wing.society_id != society_id:
        raise not_found()
    return wing


async def update_wing(
    session: AsyncSession, society_id: UUID, actor: User, wing_id: UUID, changes: dict[str, Any]
) -> Wing:
    wing = await get_wing(session, society_id, wing_id)
    if "name" in changes and await _wing_name_taken(
        session, society_id, changes["name"], except_id=wing.id
    ):
        raise AppError(409, "WING_EXISTS", "errors.wingExists")
    before = snapshot(wing, ("name", "has_lift"))
    for key, value in changes.items():
        setattr(wing, key, value.strip() if isinstance(value, str) else value)
    await session.flush()
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="wing.update",
        entity_type="wing",
        entity_id=wing.id,
        before=before,
        after=snapshot(wing, ("name", "has_lift")),
    )
    return wing


# --- flats ---------------------------------------------------------------------------


@dataclass
class FlatSummary:
    flat: Flat
    wing_name: str
    primary_member: str | None
    balance_paise: int


async def _primary_names(session: AsyncSession, flat_ids: list[UUID]) -> dict[UUID, str]:
    if not flat_ids:
        return {}
    rows = await session.execute(
        select(Member.flat_id, Member.full_name)
        .where(Member.flat_id.in_(flat_ids), Member.to_date.is_(None))
        .order_by(Member.flat_id, Member.is_primary.desc(), Member.created_at)
    )
    names: dict[UUID, str] = {}
    for flat_id, name in rows:
        names.setdefault(flat_id, name)
    return names


async def list_flats(session: AsyncSession, society_id: UUID) -> list[FlatSummary]:
    rows = (
        await session.execute(
            select(Flat, Wing.name)
            .join(Wing, Wing.id == Flat.wing_id)
            .where(Flat.society_id == society_id)
            .order_by(Wing.name, Flat.flat_number)
        )
    ).all()
    ids = [flat.id for flat, _ in rows]
    names = await _primary_names(session, ids)
    totals = await ledger.balances(session, ids)
    return [FlatSummary(flat, wing, names.get(flat.id), totals[flat.id]) for flat, wing in rows]


async def get_flat(session: AsyncSession, society_id: UUID, flat_id: UUID) -> Flat:
    flat = await session.get(Flat, flat_id)
    if flat is None or flat.society_id != society_id:
        raise not_found()
    return flat


@dataclass
class FlatDetail:
    summary: FlatSummary
    members: list[Member]


async def flat_detail(session: AsyncSession, society_id: UUID, flat_id: UUID) -> FlatDetail:
    flat = await get_flat(session, society_id, flat_id)
    wing = await get_wing(session, society_id, flat.wing_id)
    members = list(
        await session.scalars(
            select(Member)
            .where(Member.flat_id == flat.id)
            .order_by(Member.to_date.is_not(None), Member.is_primary.desc(), Member.created_at)
        )
    )
    names = await _primary_names(session, [flat.id])
    totals = await ledger.balances(session, [flat.id])
    return FlatDetail(FlatSummary(flat, wing.name, names.get(flat.id), totals[flat.id]), members)


async def _flat_number_taken(
    session: AsyncSession, society_id: UUID, wing_id: UUID, number: str, except_id: UUID | None
) -> bool:
    query = select(Flat.id).where(
        Flat.society_id == society_id,
        Flat.wing_id == wing_id,
        func.lower(Flat.flat_number) == number.strip().lower(),
    )
    if except_id:
        query = query.where(Flat.id != except_id)
    return (await session.scalar(query)) is not None


async def create_flat(
    session: AsyncSession, society_id: UUID, actor: User, fields: dict[str, Any]
) -> Flat:
    await get_wing(session, society_id, fields["wing_id"])
    fields["flat_number"] = fields["flat_number"].strip()
    if await _flat_number_taken(
        session, society_id, fields["wing_id"], fields["flat_number"], None
    ):
        raise AppError(409, "FLAT_EXISTS", "errors.flatExists")
    flat = Flat(society_id=society_id, created_by=actor.id, **fields)
    session.add(flat)
    await session.flush()
    await session.refresh(flat)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="flat.create",
        entity_type="flat",
        entity_id=flat.id,
        after=snapshot(flat, FLAT_FIELDS),
    )
    return flat


async def update_flat(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, changes: dict[str, Any]
) -> Flat:
    flat = await get_flat(session, society_id, flat_id)
    wing_id = changes.get("wing_id", flat.wing_id)
    if "wing_id" in changes:
        await get_wing(session, society_id, wing_id)
    number = changes.get("flat_number", flat.flat_number).strip()
    if ("wing_id" in changes or "flat_number" in changes) and await _flat_number_taken(
        session, society_id, wing_id, number, flat.id
    ):
        raise AppError(409, "FLAT_EXISTS", "errors.flatExists")
    before = snapshot(flat, FLAT_FIELDS)
    for key, value in changes.items():
        setattr(flat, key, value.strip() if isinstance(value, str) else value)
    await session.flush()
    await session.refresh(flat)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="flat.update",
        entity_type="flat",
        entity_id=flat.id,
        before=before,
        after=snapshot(flat, FLAT_FIELDS),
    )
    return flat


# --- members -------------------------------------------------------------------------


async def create_member(
    session: AsyncSession, society_id: UUID, actor: User, flat_id: UUID, fields: dict[str, Any]
) -> Member:
    await get_flat(session, society_id, flat_id)
    member = Member(society_id=society_id, flat_id=flat_id, created_by=actor.id, **fields)
    session.add(member)
    await session.flush()
    await session.refresh(member)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="member.create",
        entity_type="member",
        entity_id=member.id,
        after={"flat_id": str(flat_id), **snapshot(member, MEMBER_FIELDS)},
    )
    return member


async def update_member(
    session: AsyncSession,
    society_id: UUID,
    actor: User,
    flat_id: UUID,
    member_id: UUID,
    changes: dict[str, Any],
) -> Member:
    member = await session.get(Member, member_id)
    if member is None or member.society_id != society_id or member.flat_id != flat_id:
        raise not_found()
    before = snapshot(member, MEMBER_FIELDS)
    for key, value in changes.items():
        setattr(member, key, value.strip() if isinstance(value, str) else value)
    if member.to_date and member.from_date and member.to_date < member.from_date:
        raise AppError(422, "DATES_REVERSED", "errors.datesReversed")
    await session.flush()
    await session.refresh(member)
    await audit.record(
        session,
        society_id=society_id,
        actor_user_id=actor.id,
        action="member.update",
        entity_type="member",
        entity_id=member.id,
        before=before,
        after=snapshot(member, MEMBER_FIELDS),
    )
    return member
