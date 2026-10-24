"""Billing runs and bills (docs/02 §5, docs/05 §3). Money in paise."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["draft", "approved", "sent", "cancelled"]
BillStatus = Literal["issued", "partially_paid", "paid", "cancelled"]


class RunCreateIn(BaseModel):
    period_start: date


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RunWarningOut(BaseModel):
    key: str
    flat: str | None = None
    reasons: list[str] = Field(default_factory=list)


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    period_start: date
    period_end: date
    bill_date: date
    due_date: date
    status: RunStatus
    flat_count: int
    total_paise: int
    created_by_job: bool
    approved_at: datetime | None
    cancelled_reason: str | None
    warnings: list[RunWarningOut]


class DraftFlatOut(BaseModel):
    flat_id: UUID
    label: str
    charges_paise: int


class BillSummaryOut(BaseModel):
    id: UUID
    flat_id: UUID
    flat_label: str
    bill_number: str
    member_name: str | None
    charges_paise: int
    arrears_paise: int
    advance_paise: int
    interest_paise: int
    total_due_paise: int
    status: BillStatus
    replaces_bill_id: UUID | None


class RunDetailOut(RunOut):
    # Draft: what each flat will be charged. Approved: the bills.
    draft_flats: list[DraftFlatOut]
    bills: list[BillSummaryOut]


class BillLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    charge_head_id: UUID | None
    line_type: Literal["charge", "rounding", "interest"]
    description: str
    amount_paise: int


class BillOut(BillSummaryOut):
    billing_run_id: UUID
    period_start: date
    period_end: date
    bill_date: date
    due_date: date
    cancelled_reason: str | None
    cancelled_at: datetime | None
    lines: list[BillLineOut]
    replaced_by_bill_id: UUID | None


def warnings_out(raw: list[dict[str, Any]]) -> list[RunWarningOut]:
    return [RunWarningOut(**w) for w in raw]
