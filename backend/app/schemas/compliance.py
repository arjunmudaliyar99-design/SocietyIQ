"""Vendors and the compliance tracker (docs/02 §13, docs/05 §6). Money in paise."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.societies import PHONE_E164

ItemType = Literal[
    "fire_audit",
    "structural_audit",
    "lift_amc",
    "pump_amc",
    "generator_service",
    "tank_cleaning",
    "cctv_amc",
    "insurance",
    "pest_control",
    "other",
]
Status = Literal["ok", "due_soon", "overdue", "done"]


class VendorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    email: EmailStr | None = None
    gstin: str | None = Field(default=None, max_length=15)
    notes: str | None = Field(default=None, max_length=1000)


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    phone_e164: str | None = Field(default=None, pattern=PHONE_E164)
    email: EmailStr | None = None
    gstin: str | None = Field(default=None, max_length=15)
    notes: str | None = Field(default=None, max_length=1000)


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None
    phone_e164: str | None
    email: str | None
    gstin: str | None
    notes: str | None


class ItemIn(BaseModel):
    item_type: ItemType
    title: str = Field(min_length=1, max_length=200)
    vendor_id: UUID | None = None
    last_done_on: date | None = None
    next_due_on: date
    repeat_months: int | None = Field(default=None, ge=1, le=120)
    contract_value_paise: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class ItemUpdate(BaseModel):
    item_type: ItemType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    vendor_id: UUID | None = None
    next_due_on: date | None = None
    repeat_months: int | None = Field(default=None, ge=1, le=120)
    contract_value_paise: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class DoneIn(BaseModel):
    done_on: date
    notes: str | None = Field(default=None, max_length=2000)


class ItemOut(BaseModel):
    id: UUID
    item_type: ItemType
    title: str
    vendor_id: UUID | None
    vendor_name: str | None
    last_done_on: date | None
    next_due_on: date
    repeat_months: int | None
    contract_value_paise: int | None
    notes: str | None
    is_active: bool
    status: Status
    # Negative when overdue.
    days_left: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    done_on: date
    notes: str | None


class ItemDetailOut(ItemOut):
    events: list[EventOut]
