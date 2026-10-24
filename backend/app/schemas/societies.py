"""Societies, invites, memberships (docs/02 §3, docs/05 §1)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

CommitteeRole = Literal["admin", "treasurer", "committee", "consultant", "auditor"]
Role = Literal[
    "admin", "treasurer", "committee", "consultant", "auditor", "owner", "tenant", "delegate"
]
PHONE_E164 = r"^\+[1-9][0-9]{7,14}$"


class SocietyDetailsIn(BaseModel):
    """Step 1 of 3."""

    name: str = Field(min_length=1, max_length=200)
    registration_number: str | None = Field(default=None, max_length=100)
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    state: str = Field(default="Maharashtra", max_length=100)
    pincode: str | None = Field(default=None, pattern=r"^[1-9][0-9]{5}$")
    financial_year_start_month: int = Field(default=4, ge=1, le=12)


class BillingSettingsIn(BaseModel):
    """Step 2 of 3."""

    billing_frequency: Literal["monthly", "quarterly"] = "monthly"
    bill_day: int = Field(ge=1, le=28)
    due_days: int = Field(default=15, ge=0)
    upi_id: str | None = Field(default=None, max_length=100)
    upi_payee_name: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account_last4: str | None = Field(default=None, pattern=r"^[0-9]{4}$")


class InviteIn(BaseModel):
    """Step 3 of 3, and the invite screen later."""

    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    role: Role
    # Required for owner, tenant and delegate (docs/05 §1).
    flat_id: UUID | None = None


class CommitteeInviteIn(BaseModel):
    """Setup wizard step 3: flats do not exist yet, so committee roles only."""

    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    role: CommitteeRole


class SocietyCreateIn(BaseModel):
    details: SocietyDetailsIn
    billing: BillingSettingsIn
    invites: list[CommitteeInviteIn] = Field(default_factory=list, max_length=20)


class SocietyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    registration_number: str | None
    address_line: str | None
    city: str | None
    state: str
    pincode: str | None
    financial_year_start_month: int
    billing_frequency: str
    bill_day: int | None
    due_days: int
    upi_id: str | None
    upi_payee_name: str | None
    bank_name: str | None
    bank_account_last4: str | None


class MySocietyOut(BaseModel):
    id: UUID
    name: str
    city: str | None
    roles: list[Role]


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Role
    status: Literal["invited", "active", "removed"]
    invited_name: str | None
    invited_email: str | None
    invited_phone_e164: str | None
    invite_expires_at: datetime | None
    flat_id: UUID | None
    is_you: bool = False


class InviteOut(BaseModel):
    membership: MembershipOut
    # Shown once so the admin can share it until email sending exists (M9).
    invite_link: str


class SocietyCreatedOut(BaseModel):
    society: SocietyOut
    invites: list[InviteOut]


class AcceptInviteIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
