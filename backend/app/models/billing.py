"""Billing runs, bills and numbering (docs/05 §3), job runs (§8)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, SmallInteger, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class BillingRun(Timestamps, CreatedBy, Base):
    __tablename__ = "billing_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    period_start: Mapped[date]
    period_end: Mapped[date]
    bill_date: Mapped[date]
    due_date: Mapped[date]
    status: Mapped[str]
    flat_count: Mapped[int] = mapped_column(server_default="0")
    total_paise: Mapped[int] = mapped_column(BigInteger, server_default="0")
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default="[]")
    charges_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    created_by_job: Mapped[bool] = mapped_column(server_default="false")
    approved_by: Mapped[UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_reason: Mapped[str | None]


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    billing_run_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    bill_number: Mapped[str]
    period_start: Mapped[date]
    period_end: Mapped[date]
    bill_date: Mapped[date]
    due_date: Mapped[date]
    charges_paise: Mapped[int] = mapped_column(BigInteger)
    arrears_paise: Mapped[int] = mapped_column(BigInteger)
    advance_paise: Mapped[int] = mapped_column(BigInteger, server_default="0")
    interest_paise: Mapped[int] = mapped_column(BigInteger, server_default="0")
    total_due_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str]
    cancelled_reason: Mapped[str | None]
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaces_bill_id: Mapped[UUID | None]
    pdf_path: Mapped[str | None]
    language: Mapped[str] = mapped_column(server_default="en")
    member_name: Mapped[str | None]
    created_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillLine(Base):
    __tablename__ = "bill_lines"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bill_id: Mapped[UUID]
    society_id: Mapped[UUID]
    charge_head_id: Mapped[UUID | None]
    line_type: Mapped[str] = mapped_column(server_default="charge")
    description: Mapped[str]
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default="0")


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    society_id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(primary_key=True)
    financial_year: Mapped[str] = mapped_column(primary_key=True)
    next_value: Mapped[int] = mapped_column(server_default="1")


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_name: Mapped[str]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str]
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
