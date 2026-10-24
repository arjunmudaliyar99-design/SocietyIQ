"""Committee home (docs/02 §10)."""

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

CardKey = Literal["collected", "outstanding", "payments_waiting"]


class LatestRunOut(BaseModel):
    id: UUID
    period_start: date
    status: Literal["draft", "approved", "sent", "cancelled"]


class AttentionOut(BaseModel):
    key: str
    params: dict[str, Any]
    link: str


class HomeOut(BaseModel):
    coming_soon: list[CardKey]
    open_complaints: int
    compliance_overdue: int
    compliance_due_soon: int
    next_bill_date: date | None
    latest_run: LatestRunOut | None
    attention: list[AttentionOut]
