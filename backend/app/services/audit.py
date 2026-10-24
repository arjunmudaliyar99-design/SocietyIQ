"""Audit log writes and the viewer (docs/04 §14, docs/05 §8).

Callers write in the same transaction as the change, so a change is never saved without its
audit row.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, SocietyMembership

PAGE_SIZE = 50


async def record(
    session: AsyncSession,
    *,
    society_id: UUID | None,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    flush: bool = True,
) -> None:
    session.add(
        AuditLog(
            society_id=society_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            reason=reason,
        )
    )
    # Bulk writers (billing runs) flush once at the end of the transaction instead.
    if flush:
        await session.flush()


@dataclass
class AuditPage:
    rows: list[AuditLog]
    actors: dict[UUID, str]
    # Pass as before_id to get the next (older) page; None on the last page.
    next_before_id: int | None


async def list_entries(
    session: AsyncSession,
    society_id: UUID,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    before_id: int | None = None,
    limit: int = PAGE_SIZE,
) -> AuditPage:
    """Newest first, paged by id (stable while new rows arrive)."""
    query = select(AuditLog).where(AuditLog.society_id == society_id)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)
    if before_id:
        query = query.where(AuditLog.id < before_id)
    rows = list(await session.scalars(query.order_by(AuditLog.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    return AuditPage(rows, await _actor_names(session, society_id), rows[-1].id if more else None)


async def _actor_names(session: AsyncSession, society_id: UUID) -> dict[UUID, str]:
    """Who did it, as the society knows them (name or email from their membership). Other
    users' profiles are not readable under row-level security, and need not be."""
    names: dict[UUID, str] = {}
    rows = await session.execute(
        select(
            SocietyMembership.user_id,
            SocietyMembership.invited_name,
            SocietyMembership.invited_email,
        ).where(SocietyMembership.society_id == society_id, SocietyMembership.user_id.is_not(None))
    )
    for user_id, name, email in rows:
        label = name or email
        if user_id and label and user_id not in names:
            names[user_id] = label
    return names
