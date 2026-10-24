"""Vendors and the compliance tracker (docs/05 §6)."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class Vendor(Timestamps, CreatedBy, Base):
    __tablename__ = "vendors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    name: Mapped[str]
    category: Mapped[str | None]
    phone_e164: Mapped[str | None]
    email: Mapped[str | None]
    gstin: Mapped[str | None]
    notes: Mapped[str | None]


class ComplianceItem(Timestamps, CreatedBy, Base):
    __tablename__ = "compliance_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    item_type: Mapped[str]
    title: Mapped[str]
    vendor_id: Mapped[UUID | None]
    last_done_on: Mapped[date | None]
    next_due_on: Mapped[date]
    repeat_months: Mapped[int | None] = mapped_column(SmallInteger)
    contract_value_paise: Mapped[int | None] = mapped_column(BigInteger)
    notes: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(server_default="true")


class ComplianceEvent(Base):
    __tablename__ = "compliance_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    compliance_item_id: Mapped[UUID]
    done_on: Mapped[date]
    notes: Mapped[str | None]
    recorded_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceReminder(Base):
    __tablename__ = "compliance_reminders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    compliance_item_id: Mapped[UUID]
    due_on: Mapped[date]
    days_before: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
