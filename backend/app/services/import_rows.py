"""Parse and check rows of the flats and members template (docs/02 §4). Pure functions, no
database: the caller passes the flats that already exist.

Every problem is an Issue with an i18n key and parameters, so the preview can say it in the
reader's language ("Row 14: owner phone has 9 digits"). Errors stop a row; warnings do not.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

# (key, header text) in template order. Header text is matched loosely (case, spaces).
COLUMNS: list[tuple[str, str]] = [
    ("wing", "Wing"),
    ("wing_has_lift", "Wing has lift (Y/N)"),
    ("flat_number", "Flat number"),
    ("carpet_area_sqft", "Carpet area sq ft"),
    ("flat_type", "Flat type"),
    ("usage", "Usage"),
    ("construction_cost", "Certified construction cost (₹)"),
    ("water_points", "Water taps"),
    ("municipal_account", "Municipal account no."),
    ("occupancy", "Occupancy"),
    ("owner_name", "Owner name"),
    ("owner_phone", "Owner phone"),
    ("owner_email", "Owner email"),
    ("tenant_name", "Tenant name"),
    ("tenant_phone", "Tenant phone"),
    ("opening_balance", "Opening balance (₹, positive = flat owes)"),
]

USAGE_CHOICES = {"residential": "residential", "commercial": "commercial"}
OCCUPANCY_CHOICES = {
    "owner occupied": "owner_occupied",
    "family occupied": "family_occupied",
    "let out": "let_out",
    "vacant": "vacant",
}
YES = {"y", "yes"}
NO = {"n", "no"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

Status = Literal["ok", "warning", "error"]

ERROR_KEYS = {
    "required",
    "notNumber",
    "notPositive",
    "tooManyDecimals",
    "phoneDigits",
    "invalidEmail",
    "badChoice",
    "duplicateInFile",
    "alreadyExists",
    "liftConflict",
    "tenantPhoneNoName",
}


@dataclass(frozen=True)
class Issue:
    key: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return self.key in ERROR_KEYS


@dataclass
class RowResult:
    row: int
    status: Status
    issues: list[Issue]
    data: dict[str, Any]


def normalise_header(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def _decimal(value: object) -> Decimal | None:
    """Excel gives floats; read them at 15 significant digits so binary noise
    (0.30000000000000004) does not become a fraction of a paisa."""
    if isinstance(value, float):
        return Decimal(f"{value:.15g}")
    if isinstance(value, int | Decimal):
        return Decimal(value)
    text = re.sub(r"[₹,\s]", "", str(value))
    if text.lower().startswith("rs."):
        text = text[3:]
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_money_paise(value: object) -> tuple[int | None, str | None]:
    """Rupees → integer paise. Returns (paise, problem_key)."""
    amount = _decimal(value)
    if amount is None or not amount.is_finite():
        return None, "notNumber"
    paise = amount * 100
    if paise != paise.to_integral_value():
        return None, "tooManyDecimals"
    return int(paise), None


def parse_phone(value: object) -> tuple[str | None, int | None]:
    """Indian numbers → E.164. Returns (phone, digit_count_when_wrong)."""
    digits = re.sub(r"\D", "", _text(value) or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10:
        return None, len(digits)
    return f"+91{digits}", None


def _positive_number(value: object, places: int) -> tuple[str | None, str | None]:
    number = _decimal(value)
    if number is None or not number.is_finite():
        return None, "notNumber"
    if number < 0:
        return None, "notPositive"
    if number != round(number, places):
        return None, "tooManyDecimals"
    return format(number.normalize(), "f"), None


def _check_one(row: int, raw: dict[str, object]) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    data: dict[str, Any] = {}

    def problem(key: str, field_name: str, **params: str | int | None) -> None:
        issues.append(Issue(key, {"field": field_name, **params}))

    data["wing"] = _text(raw.get("wing"))
    data["flat_number"] = _text(raw.get("flat_number"))
    if not data["flat_number"]:
        problem("required", "flat_number")

    lift = (_text(raw.get("wing_has_lift")) or "").lower()
    data["wing_has_lift"] = True if lift in YES else False if lift in NO else None
    if lift and data["wing_has_lift"] is None:
        problem("badChoice", "wing_has_lift", allowed="Y, N")

    data["carpet_area_sqft"] = None
    if _text(raw.get("carpet_area_sqft")):
        data["carpet_area_sqft"], key = _positive_number(raw["carpet_area_sqft"], 2)
        if key:
            problem(key, "carpet_area_sqft")
        elif data["carpet_area_sqft"] == "0":
            data["carpet_area_sqft"] = None
            problem("notPositive", "carpet_area_sqft")
    else:
        issues.append(Issue("carpetMissing"))

    data["flat_type"] = _text(raw.get("flat_type"))

    usage = (_text(raw.get("usage")) or "residential").lower()
    data["usage"] = USAGE_CHOICES.get(usage)
    if data["usage"] is None:
        problem("badChoice", "usage", allowed="Residential, Commercial")

    data["construction_cost_paise"] = None
    if _text(raw.get("construction_cost")):
        paise, key = parse_money_paise(raw["construction_cost"])
        if key:
            problem(key, "construction_cost")
        elif paise is not None and paise < 0:
            problem("notPositive", "construction_cost")
        else:
            data["construction_cost_paise"] = paise
    else:
        issues.append(Issue("costMissing"))

    data["water_points"] = None
    if _text(raw.get("water_points")):
        data["water_points"], key = _positive_number(raw["water_points"], 2)
        if key:
            problem(key, "water_points")

    data["municipal_account"] = _text(raw.get("municipal_account"))

    occupancy = re.sub(r"[-_]", " ", (_text(raw.get("occupancy")) or "owner occupied").lower())
    data["occupancy"] = OCCUPANCY_CHOICES.get(occupancy)
    if data["occupancy"] is None:
        problem(
            "badChoice", "occupancy", allowed="Owner occupied, Family occupied, Let out, Vacant"
        )

    data["owner_name"] = _text(raw.get("owner_name"))
    if not data["owner_name"]:
        issues.append(Issue("ownerMissing"))
    for who in ("owner", "tenant"):
        data[f"{who}_phone"] = None
        if _text(raw.get(f"{who}_phone")):
            phone, digits = parse_phone(raw[f"{who}_phone"])
            if phone:
                data[f"{who}_phone"] = phone
            else:
                problem("phoneDigits", f"{who}_phone", digits=digits)

    data["owner_email"] = _text(raw.get("owner_email"))
    if data["owner_email"]:
        data["owner_email"] = data["owner_email"].lower()
        if not EMAIL.match(data["owner_email"]):
            problem("invalidEmail", "owner_email")

    data["tenant_name"] = _text(raw.get("tenant_name"))
    if _text(raw.get("tenant_phone")) and not data["tenant_name"]:
        issues.append(Issue("tenantPhoneNoName"))
    if data["occupancy"] == "let_out" and not data["tenant_name"]:
        issues.append(Issue("letOutNoTenant"))

    data["opening_balance_paise"] = 0
    if _text(raw.get("opening_balance")):
        paise, key = parse_money_paise(raw["opening_balance"])
        if key:
            problem(key, "opening_balance")
        else:
            data["opening_balance_paise"] = paise

    return issues, data


def _wing_key(name: str | None) -> str:
    return (name or "").strip().lower()


def check_rows(
    rows: list[tuple[int, dict[str, object]]],
    existing_flats: set[tuple[str, str]] | frozenset[tuple[str, str]] = frozenset(),
    existing_lifts: dict[str, bool] | None = None,
    blank_wing: str = "",
) -> list[RowResult]:
    """rows: (excel_row_number, raw values by column key).
    existing_flats: (wing name lower-cased, flat number lower-cased) already in the society.
    existing_lifts: wing name lower-cased → has_lift, for wings already saved.
    blank_wing: the wing (lower-cased) that rows without a wing name will go into."""
    existing_lifts = existing_lifts or {}
    any_wing_named = any(_text(raw.get("wing")) for _, raw in rows)
    seen: dict[tuple[str, str], int] = {}
    lift_by_wing: dict[str, tuple[bool, int]] = {}
    results: list[RowResult] = []

    for row_number, raw in rows:
        issues, data = _check_one(row_number, raw)
        wing = _wing_key(data["wing"])
        if any_wing_named and not wing:
            issues.insert(0, Issue("required", {"field": "wing"}))

        if data["flat_number"]:
            key = (wing, data["flat_number"].lower())
            if key in seen:
                issues.insert(0, Issue("duplicateInFile", {"otherRow": seen[key]}))
            else:
                seen[key] = row_number
            if (wing or blank_wing, data["flat_number"].lower()) in existing_flats:
                issues.insert(0, Issue("alreadyExists"))

        lift = data["wing_has_lift"]
        if lift is not None:
            earlier = lift_by_wing.get(wing)
            if earlier and earlier[0] != lift:
                issues.append(Issue("liftConflict", {"wing": data["wing"], "otherRow": earlier[1]}))
            else:
                lift_by_wing.setdefault(wing, (lift, row_number))
            if wing in existing_lifts and existing_lifts[wing] != lift:
                issues.append(Issue("liftDiffers", {"wing": data["wing"]}))

        status: Status = (
            "error" if any(i.is_error for i in issues) else "warning" if issues else "ok"
        )
        results.append(RowResult(row_number, status, issues, data))
    return results
