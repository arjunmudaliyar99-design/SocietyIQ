"""Audit log writes (docs/04 §14, docs/05 §8). The viewer comes in M11.

Callers write in the same transaction as the change, so a change is never saved without its
audit row.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


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
    await session.flush()
