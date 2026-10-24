"""What a resident may see and do for the flats they are linked to (docs/02 §2, docs/07 M7).

Owners and delegates see their flat's dues, bills and receipts and can pay. A tenant sees and
pays only if the owner allowed it (`members.tenant_can_pay`); otherwise bills go to the owner.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError, not_found
from app.models import Member, SocietyMembership, User

RESIDENT_ROLES = ("owner", "tenant", "delegate")


@dataclass(frozen=True)
class FlatAccess:
    flat_id: UUID
    role: str
    can_pay: bool


async def _tenant_allowed(session: AsyncSession, flat_id: UUID, user: User) -> bool:
    found = await session.scalar(
        select(Member.id).where(
            Member.flat_id == flat_id,
            Member.member_type == "tenant",
            Member.tenant_can_pay.is_(True),
            Member.to_date.is_(None),
            or_(Member.user_id == user.id, Member.email == (user.email or "").lower()),
        )
    )
    return found is not None


async def my_flats(session: AsyncSession, society_id: UUID, user: User) -> list[FlatAccess]:
    rows = await session.execute(
        select(SocietyMembership.flat_id, SocietyMembership.role).where(
            SocietyMembership.society_id == society_id,
            SocietyMembership.user_id == user.id,
            SocietyMembership.status == "active",
            SocietyMembership.role.in_(RESIDENT_ROLES),
            SocietyMembership.flat_id.is_not(None),
        )
    )
    result: dict[UUID, FlatAccess] = {}
    for flat_id, role in rows:
        can_pay = role != "tenant" or await _tenant_allowed(session, flat_id, user)
        previous = result.get(flat_id)
        # A person linked twice (e.g. owner and delegate) gets the stronger access.
        if previous is None or (can_pay and not previous.can_pay):
            result[flat_id] = FlatAccess(flat_id, role, can_pay)
    return list(result.values())


async def flat_access(
    session: AsyncSession, society_id: UUID, user: User, flat_id: UUID, *, to_pay: bool = False
) -> FlatAccess:
    """404 for a flat the person is not linked to; 403 for a tenant the owner has not allowed."""
    flats = await my_flats(session, society_id, user)
    access = next((a for a in flats if a.flat_id == flat_id), None)
    if access is None:
        raise not_found()
    if to_pay and not access.can_pay:
        raise AppError(403, "TENANT_CANNOT_PAY", "errors.tenantCannotPay")
    return access
