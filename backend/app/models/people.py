"""People and access (docs/05 §1)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class User(Timestamps, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str | None]
    email: Mapped[str | None]
    phone_e164: Mapped[str | None]
    preferred_language: Mapped[str] = mapped_column(server_default="en")
    text_size: Mapped[str] = mapped_column(server_default="normal")
    simple_mode: Mapped[bool] = mapped_column(server_default="true")
    analytics_opt_out: Mapped[bool] = mapped_column(server_default="false")


class Society(Timestamps, CreatedBy, Base):
    __tablename__ = "societies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]
    registration_number: Mapped[str | None]
    address_line: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str] = mapped_column(server_default="Maharashtra")
    pincode: Mapped[str | None]
    financial_year_start_month: Mapped[int] = mapped_column(SmallInteger, server_default="4")
    default_language: Mapped[str] = mapped_column(server_default="en")
    billing_frequency: Mapped[str] = mapped_column(server_default="monthly")
    bill_day: Mapped[int | None] = mapped_column(SmallInteger)
    due_days: Mapped[int] = mapped_column(SmallInteger, server_default="15")
    upi_id: Mapped[str | None]
    upi_payee_name: Mapped[str | None]
    bank_name: Mapped[str | None]
    bank_account_last4: Mapped[str | None]
    interest_enabled: Mapped[bool] = mapped_column(server_default="false")
    interest_rate_annual_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    interest_gb_resolution_date: Mapped[date | None]
    interest_grace_days: Mapped[int | None] = mapped_column(SmallInteger)
    rounding_rule: Mapped[str] = mapped_column(server_default="nearest_rupee")
    auto_approve_billing: Mapped[bool] = mapped_column(server_default="false")
    plan: Mapped[str] = mapped_column(server_default="pilot")
    champion_name: Mapped[str | None]
    champion_phone_e164: Mapped[str | None]


class SocietyMembership(Timestamps, CreatedBy, Base):
    __tablename__ = "society_memberships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    user_id: Mapped[UUID | None]
    role: Mapped[str]
    flat_id: Mapped[UUID | None]
    status: Mapped[str]
    invited_name: Mapped[str | None]
    invited_email: Mapped[str | None]
    invited_phone_e164: Mapped[str | None]
    invite_token_hash: Mapped[str | None]
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID]
    society_id: Mapped[UUID | None]
    purpose: Mapped[str]
    policy_version: Mapped[str]
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
