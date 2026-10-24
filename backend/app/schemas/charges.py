"""Charge setup (docs/02 §5, docs/05 §3). Money in paise; rates as decimals (18.0 = 18%)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.flats import ImportIssueOut

StandardCode = Literal[
    "service",
    "property_tax",
    "water",
    "lift",
    "parking",
    "non_occupancy",
    "insurance",
    "lease_rent",
    "major_repair",
    "sinking_fund",
    "repair_fund",
    "election_fund",
    "education_fund",
    "welfare_fund",
    "other",
]
CalcType = Literal[
    "equal_per_flat",
    "equal_per_flat_with_lift",
    "per_carpet_area",
    "per_water_point",
    "as_assessed_per_flat",
    "pct_of_head",
    "pct_of_construction_cost",
    "per_parking_allotment",
    "per_member_fixed",
    "fixed_per_flat",
    "custom_per_flat",
    "voluntary",
]
Percent = Decimal


class StandardHeadOut(BaseModel):
    standard_code: StandardCode
    calc_type: CalcType
    applies_to: Literal["all", "let_out_only"]
    rule: str
    # From legal_parameters: fixed for non-occupancy, a minimum for sinking and repair funds.
    legal_percent: Percent | None
    legal_percent_kind: Literal["fixed", "minimum"] | None
    legal_source: str | None


class LegalProblemOut(BaseModel):
    level: Literal["block", "warn"]
    key: str
    params: dict[str, str]


class ChargeHeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    standard_code: StandardCode | None = None
    calc_type: CalcType
    period_total_paise: int | None = Field(default=None, ge=0)
    fixed_amount_paise: int | None = Field(default=None, ge=0)
    percent: Percent | None = Field(default=None, ge=0, max_digits=7, decimal_places=4)
    percent_of_head_id: UUID | None = None
    applies_to: Literal["all", "let_out_only"] = "all"
    gb_resolution_ref: str | None = Field(default=None, max_length=200)
    gb_resolution_date: date | None = None
    method_deviation_reason: str | None = Field(default=None, max_length=500)
    frequency: Literal["every_bill", "one_time"] = "every_bill"
    one_time_period: date | None = None
    sort_order: int = Field(default=0, ge=0, le=1000)


class ChargeHeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    calc_type: CalcType | None = None
    period_total_paise: int | None = Field(default=None, ge=0)
    fixed_amount_paise: int | None = Field(default=None, ge=0)
    percent: Percent | None = Field(default=None, ge=0, max_digits=7, decimal_places=4)
    percent_of_head_id: UUID | None = None
    applies_to: Literal["all", "let_out_only"] | None = None
    gb_resolution_ref: str | None = Field(default=None, max_length=200)
    gb_resolution_date: date | None = None
    method_deviation_reason: str | None = Field(default=None, max_length=500)
    frequency: Literal["every_bill", "one_time"] | None = None
    one_time_period: date | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1000)
    is_active: bool | None = None


class ChargeHeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    standard_code: StandardCode | None
    calc_type: CalcType
    period_total_paise: int | None
    fixed_amount_paise: int | None
    percent: Percent | None
    percent_of_head_id: UUID | None
    applies_to: Literal["all", "let_out_only"]
    gb_resolution_ref: str | None
    gb_resolution_date: date | None
    method_deviation_reason: str | None
    frequency: Literal["every_bill", "one_time"]
    one_time_period: date | None
    sort_order: int
    is_active: bool
    approved_at: datetime | None


class ChargeHeadSaved(BaseModel):
    head: ChargeHeadOut
    # Warnings the person accepted with a reason; blocks never get this far.
    warnings: list[LegalProblemOut]


class SettingsUpdate(BaseModel):
    billing_frequency: Literal["monthly", "quarterly"] | None = None
    bill_day: int | None = Field(default=None, ge=1, le=28)
    due_days: int | None = Field(default=None, ge=0)
    upi_id: str | None = Field(default=None, max_length=100)
    upi_payee_name: str | None = Field(default=None, max_length=100)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account_last4: str | None = Field(default=None, pattern=r"^[0-9]{4}$")
    interest_enabled: bool | None = None
    interest_rate_annual_pct: Percent | None = Field(default=None, max_digits=7, decimal_places=4)
    interest_gb_resolution_date: date | None = None
    interest_grace_days: int | None = Field(default=None, ge=0)
    rounding_rule: Literal["none", "nearest_rupee"] | None = None
    auto_approve_billing: bool | None = None


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    billing_frequency: Literal["monthly", "quarterly"]
    bill_day: int | None
    due_days: int
    upi_id: str | None
    upi_payee_name: str | None
    bank_name: str | None
    bank_account_last4: str | None
    interest_enabled: bool
    interest_rate_annual_pct: Percent | None
    interest_gb_resolution_date: date | None
    interest_grace_days: int | None
    rounding_rule: Literal["none", "nearest_rupee"]
    auto_approve_billing: bool


class OverrideIn(BaseModel):
    charge_head_id: UUID
    amount_paise: int = Field(ge=0)
    reason: str = Field(min_length=3, max_length=500)
    valid_from: date
    valid_to: date | None = None


class EndDateIn(BaseModel):
    end_date: date


class OverrideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    charge_head_id: UUID
    amount_paise: int
    reason: str
    valid_from: date
    valid_to: date | None


class ParkingIn(BaseModel):
    slot_label: str = Field(min_length=1, max_length=40)
    slot_type: Literal["open", "stilt", "covered", "podium", "mechanical", "other"]
    vehicle_type: Literal["two_wheeler", "four_wheeler", "other"]
    vehicle_number: str | None = Field(default=None, max_length=20)
    monthly_rate_paise: int = Field(ge=0)
    from_date: date
    to_date: date | None = None
    gb_resolution_ref: str | None = Field(default=None, max_length=200)


class ParkingOut(ParkingIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class PropertyTaxIn(BaseModel):
    authority: str = Field(min_length=1, max_length=40)
    financial_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    annual_amount_paise: int = Field(ge=0)
    is_exempt: bool = False
    exemption_reason: str | None = Field(default=None, max_length=200)


class PropertyTaxOut(PropertyTaxIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PreviewHeadOut(BaseModel):
    id: UUID
    name: str
    total_paise: int


class PreviewFlatOut(BaseModel):
    flat_id: UUID
    label: str
    lines: dict[str, int]
    charges_paise: int
    rounding_paise: int
    total_paise: int
    overridden: list[str]
    warnings: list[str]


class ExcludedFlatOut(BaseModel):
    flat_id: UUID
    label: str
    reasons: list[str]


class PreviewOut(BaseModel):
    period_start: date
    period_end: date
    heads: list[PreviewHeadOut]
    flats: list[PreviewFlatOut]
    excluded: list[ExcludedFlatOut]
    total_paise: int
    missing: dict[str, int]


class TaxImportRowOut(BaseModel):
    row: int
    status: Literal["ok", "warning", "error"]
    issues: list[ImportIssueOut]
    flat_label: str
    financial_year: str
    annual_amount_paise: int
    is_exempt: bool


class TaxImportOut(BaseModel):
    id: UUID
    status: Literal["uploaded", "previewed", "imported", "failed"]
    row_count: int
    ok_count: int
    error_count: int
    rows: list[TaxImportRowOut]
