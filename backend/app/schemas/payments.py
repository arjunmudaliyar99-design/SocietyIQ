"""Payments, receipts, dues and the flat ledger (docs/02 §6-7). Money in paise."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Method = Literal["cash", "cheque", "upi", "neft", "other"]
Status = Literal["pending", "recorded", "confirmed", "bounced", "reversed"]


class PaymentIn(BaseModel):
    flat_id: UUID
    amount_paise: int = Field(gt=0)
    method: Method
    received_on: date
    reference: str | None = Field(default=None, max_length=60)
    cheque_bank: str | None = Field(default=None, max_length=60)
    cheque_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    # One tap for cash or a UPI/NEFT credit the treasurer can already see: record and confirm.
    confirm_now: bool = False


class ResidentPaymentIn(BaseModel):
    """'I have paid' from the resident app (docs/02 §11): waits for the treasurer."""

    amount_paise: int = Field(gt=0)
    method: Literal["upi", "neft", "cash", "cheque", "other"] = "upi"
    received_on: date
    reference: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=500)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flat_id: UUID
    flat_label: str = ""
    amount_paise: int
    method: str
    status: Status
    received_on: date
    reference: str | None
    cheque_bank: str | None
    cheque_date: date | None
    reported_by_resident: bool
    reason: str | None
    notes: str | None
    confirmed_at: datetime | None
    created_at: datetime
    receipt_number: str | None = None
    receipt_cancelled: bool = False


class AllocationOut(BaseModel):
    settles: str
    amount_paise: int


class PaymentDetailOut(PaymentOut):
    allocations: list[AllocationOut]


class DuesRowOut(BaseModel):
    flat_id: UUID
    flat_label: str
    balance_paise: int
    months_pending: int
    bucket: Literal["paid_up", "friendly", "formal", "long"]


class DuesOut(BaseModel):
    rows: list[DuesRowOut]
    counts: dict[str, int]
    outstanding_paise: int


class LedgerLineOut(BaseModel):
    id: UUID
    entry_date: date
    entry_type: Literal["opening_balance", "bill", "interest", "payment", "adjustment", "reversal"]
    amount_paise: int
    running_paise: int
    document: str | None
    reason: str | None


class FlatLedgerOut(BaseModel):
    flat_id: UUID
    flat_label: str
    balance_paise: int
    months_pending: int
    lines: list[LedgerLineOut]
