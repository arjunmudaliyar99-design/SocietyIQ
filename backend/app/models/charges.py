"""Charge setup (docs/05 §3)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Numeric, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class ChargeHead(Timestamps, CreatedBy, Base):
    __tablename__ = "charge_heads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    name: Mapped[str]
    code: Mapped[str]
    standard_code: Mapped[str | None]
    calc_type: Mapped[str]
    period_total_paise: Mapped[int | None] = mapped_column(BigInteger)
    fixed_amount_paise: Mapped[int | None] = mapped_column(BigInteger)
    percent: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    percent_of_head_id: Mapped[UUID | None]
    applies_to: Mapped[str] = mapped_column(server_default="all")
    gb_resolution_ref: Mapped[str | None]
    gb_resolution_date: Mapped[date | None]
    method_deviation_reason: Mapped[str | None]
    frequency: Mapped[str] = mapped_column(server_default="every_bill")
    one_time_period: Mapped[date | None]
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    is_active: Mapped[bool] = mapped_column(server_default="true")
    approved_by: Mapped[UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FlatChargeOverride(Timestamps, CreatedBy, Base):
    __tablename__ = "flat_charge_overrides"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    charge_head_id: Mapped[UUID]
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]


class ParkingAllotment(Timestamps, CreatedBy, Base):
    __tablename__ = "parking_allotments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    slot_label: Mapped[str]
    slot_type: Mapped[str]
    vehicle_type: Mapped[str]
    vehicle_number: Mapped[str | None]
    monthly_rate_paise: Mapped[int] = mapped_column(BigInteger)
    from_date: Mapped[date]
    to_date: Mapped[date | None]
    gb_resolution_ref: Mapped[str | None]


class PropertyTaxAssessment(Base):
    __tablename__ = "property_tax_assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID | None]
    authority: Mapped[str]
    financial_year: Mapped[str]
    annual_amount_paise: Mapped[int] = mapped_column(BigInteger)
    is_exempt: Mapped[bool] = mapped_column(server_default="false")
    exemption_reason: Mapped[str | None]
    source_document_id: Mapped[UUID | None]
    entered_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
