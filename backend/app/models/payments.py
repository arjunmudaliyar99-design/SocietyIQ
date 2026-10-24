"""Payments, allocations and receipts (docs/05 §4)."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps


class Payment(Timestamps, Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str]
    status: Mapped[str]
    received_on: Mapped[date]
    reference: Mapped[str | None]
    cheque_bank: Mapped[str | None]
    cheque_date: Mapped[date | None]
    reported_by_resident: Mapped[bool] = mapped_column(server_default="false")
    proof_file_path: Mapped[str | None]
    recorded_by: Mapped[UUID | None]
    resident_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[UUID | None]
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversal_of: Mapped[UUID | None]
    reason: Mapped[str | None]
    notes: Mapped[str | None]


class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    payment_id: Mapped[UUID]
    bill_id: Mapped[UUID | None]
    ledger_entry_id: Mapped[UUID | None]
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    payment_id: Mapped[UUID]
    receipt_number: Mapped[str]
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    pdf_path: Mapped[str | None]
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_reason: Mapped[str | None]
