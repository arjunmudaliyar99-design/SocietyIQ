"""Audit log viewer (docs/04 §14, docs/05 §8)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    created_at: datetime
    actor_user_id: UUID | None
    # Name or email from the actor's membership; None for the system (scheduled jobs).
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None


class AuditPageOut(BaseModel):
    entries: list[AuditEntryOut]
    next_before_id: int | None
