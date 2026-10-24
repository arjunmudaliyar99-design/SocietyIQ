"""Wings, flats and members (docs/02 §4, docs/05 §2). Money in paise."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.societies import PHONE_E164

Usage = Literal["residential", "commercial"]
Occupancy = Literal["owner_occupied", "family_occupied", "let_out", "vacant"]
MemberType = Literal["owner", "joint_owner", "tenant", "delegate"]


class WingIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    has_lift: bool = False


class WingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    has_lift: bool | None = None


class WingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    has_lift: bool


class FlatIn(BaseModel):
    wing_id: UUID
    flat_number: str = Field(min_length=1, max_length=30)
    carpet_area_sqft: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    flat_type: str | None = Field(default=None, max_length=30)
    usage: Usage = "residential"
    certified_construction_cost_paise: int | None = Field(default=None, ge=0)
    water_points: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)
    municipal_property_account: str | None = Field(default=None, max_length=60)
    occupancy: Occupancy = "owner_occupied"


class FlatUpdate(BaseModel):
    wing_id: UUID | None = None
    flat_number: str | None = Field(default=None, min_length=1, max_length=30)
    carpet_area_sqft: Decimal | None = Field(default=None, gt=0, max_digits=9, decimal_places=2)
    flat_type: str | None = Field(default=None, max_length=30)
    usage: Usage | None = None
    certified_construction_cost_paise: int | None = Field(default=None, ge=0)
    water_points: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)
    municipal_property_account: str | None = Field(default=None, max_length=60)
    occupancy: Occupancy | None = None
    is_active: bool | None = None


class FlatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    wing_id: UUID
    flat_number: str
    carpet_area_sqft: Decimal | None
    flat_type: str | None
    usage: Usage
    certified_construction_cost_paise: int | None
    water_points: Decimal | None
    municipal_property_account: str | None
    occupancy: Occupancy
    is_active: bool


class FlatSummaryOut(FlatOut):
    wing_name: str
    primary_member: str | None
    # Positive = flat owes; negative = advance.
    balance_paise: int


class MemberIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    email: EmailStr | None = None
    member_type: MemberType
    is_primary: bool = False
    from_date: date | None = None
    to_date: date | None = None
    tenant_can_pay: bool = False


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    email: EmailStr | None = None
    member_type: MemberType | None = None
    is_primary: bool | None = None
    from_date: date | None = None
    to_date: date | None = None
    tenant_can_pay: bool | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flat_id: UUID
    full_name: str
    phone_e164: str | None
    email: str | None
    member_type: MemberType
    is_primary: bool
    from_date: date | None
    to_date: date | None
    tenant_can_pay: bool
    has_login: bool = False


class FlatDetailOut(FlatSummaryOut):
    members: list[MemberOut]


class ImportIssueOut(BaseModel):
    key: str
    params: dict[str, str | int | None]


class ImportRowOut(BaseModel):
    row: int
    status: Literal["ok", "warning", "error"]
    issues: list[ImportIssueOut]
    wing: str | None
    flat_number: str | None
    owner_name: str | None
    opening_balance_paise: int | None


class ImportJobOut(BaseModel):
    id: UUID
    status: Literal["uploaded", "previewed", "imported", "failed"]
    row_count: int
    ok_count: int
    error_count: int
    rows: list[ImportRowOut]
