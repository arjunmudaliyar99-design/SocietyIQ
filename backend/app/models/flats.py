"""Wings, flats and members (docs/05 §2)."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedBy, Timestamps


class Wing(Timestamps, CreatedBy, Base):
    __tablename__ = "wings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    name: Mapped[str]
    has_lift: Mapped[bool] = mapped_column(server_default="false")


class Flat(Timestamps, CreatedBy, Base):
    __tablename__ = "flats"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    wing_id: Mapped[UUID]
    flat_number: Mapped[str]
    carpet_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    flat_type: Mapped[str | None]
    usage: Mapped[str] = mapped_column(server_default="residential")
    certified_construction_cost_paise: Mapped[int | None] = mapped_column(BigInteger)
    water_points: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    municipal_property_account: Mapped[str | None]
    occupancy: Mapped[str] = mapped_column(server_default="owner_occupied")
    is_active: Mapped[bool] = mapped_column(server_default="true")


class Member(Timestamps, CreatedBy, Base):
    __tablename__ = "members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    society_id: Mapped[UUID]
    flat_id: Mapped[UUID]
    full_name: Mapped[str]
    phone_e164: Mapped[str | None]
    email: Mapped[str | None]
    member_type: Mapped[str]
    is_primary: Mapped[bool] = mapped_column(server_default="false")
    user_id: Mapped[UUID | None]
    from_date: Mapped[date | None]
    to_date: Mapped[date | None]
    tenant_can_pay: Mapped[bool] = mapped_column(server_default="false")
