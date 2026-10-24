"""Legal checks on charge setup (docs/06 §2 "Validation", §5 interest cap; docs/08 §2).

Pure functions. Every number comes from `legal_parameters` and is passed in as a LegalValue
with its source, so the message can cite the rule. Nothing here changes a value: it blocks or
warns and the person decides (docs/06: "block or warn, never silently change").
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

Level = Literal["block", "warn"]


@dataclass(frozen=True)
class StandardHead:
    calc_type: str
    rule: str
    applies_to: str = "all"


# Statutory apportionment per head (docs/06 §2 table). The rule is the citation shown with a
# warning; amounts and limits are never stored here.
STANDARD_HEADS: dict[str, StandardHead] = {
    "service": StandardHead("equal_per_flat", "Rule 106C-12"),
    "property_tax": StandardHead("as_assessed_per_flat", "Rule 106C-12"),
    "water": StandardHead("per_water_point", "Rule 106C-12"),
    "lift": StandardHead("equal_per_flat_with_lift", "Rule 106C-12"),
    "parking": StandardHead("per_parking_allotment", "Rule 106C-12"),
    "non_occupancy": StandardHead("pct_of_head", "Rule 106C-12", "let_out_only"),
    "insurance": StandardHead("per_carpet_area", "Rule 106C-12"),
    "lease_rent": StandardHead("per_carpet_area", "Rule 106C-12"),
    "major_repair": StandardHead("per_carpet_area", "Rule 106C-12"),
    "sinking_fund": StandardHead("pct_of_construction_cost", "Rule 106C-11"),
    "repair_fund": StandardHead("pct_of_construction_cost", "Rule 106C-11"),
    "election_fund": StandardHead("equal_per_flat", "Rule 106C-12"),
    "education_fund": StandardHead("per_member_fixed", "Rule 106C-7"),
    "welfare_fund": StandardHead("voluntary", "Rule 106C-12"),
    # Loan instalments, NA tax and other GB-approved charges: no statutory method.
    "other": StandardHead("fixed_per_flat", "Rule 106C-12"),
}

FUND_MINIMUM = {
    "sinking_fund": "sinking_fund_min_annual_pct",
    "repair_fund": "repair_fund_min_annual_pct",
}

NEEDS_TOTAL = {"equal_per_flat", "equal_per_flat_with_lift", "per_carpet_area", "per_water_point"}
NEEDS_PERCENT = {"pct_of_head", "pct_of_construction_cost"}
NEEDS_AMOUNT = {"per_member_fixed", "fixed_per_flat"}


@dataclass(frozen=True)
class LegalValue:
    value: Decimal
    source: str


@dataclass(frozen=True)
class Problem:
    level: Level
    key: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class HeadDraft:
    standard_code: str | None
    calc_type: str
    period_total_paise: int | None = None
    fixed_amount_paise: int | None = None
    percent: Decimal | None = None
    # standard_code of the head this one is a percent of (pct_of_head)
    base_standard_code: str | None = None
    has_base_head: bool | None = None
    applies_to: str = "all"


def _num(value: Decimal) -> str:
    return format(value.normalize(), "f")


def validate_interest(rate_pct: Decimal, legal: dict[str, LegalValue]) -> list[Problem]:
    if rate_pct < 0:
        return [Problem("block", "notNegative")]
    cap = legal["interest_max_annual_pct"]
    if rate_pct > cap.value:
        return [Problem("block", "interestAboveCap", {"max": _num(cap.value), "rule": cap.source})]
    return []


def validate_head(head: HeadDraft, legal: dict[str, LegalValue]) -> list[Problem]:
    problems: list[Problem] = []
    code = head.standard_code
    statutory = STANDARD_HEADS.get(code or "")

    for value in (head.period_total_paise, head.fixed_amount_paise, head.percent):
        if value is not None and value < 0:
            problems.append(Problem("block", "notNegative"))
            break
    if head.calc_type in NEEDS_TOTAL and head.period_total_paise is None:
        problems.append(Problem("block", "needsTotal"))
    if head.calc_type in NEEDS_PERCENT and head.percent is None:
        problems.append(Problem("block", "needsPercent"))
    if head.calc_type in NEEDS_AMOUNT and head.fixed_amount_paise is None:
        problems.append(Problem("block", "needsAmount"))
    if head.calc_type == "pct_of_head" and not (head.base_standard_code or head.has_base_head):
        problems.append(Problem("block", "needsBaseHead"))

    if code == "non_occupancy":
        fixed = legal["non_occupancy_pct_of_service"]
        cite = {"rule": fixed.source}
        if head.calc_type != "pct_of_head":
            problems.append(Problem("block", "nonOccupancyMethod", cite))
        else:
            if head.percent is not None and head.percent != fixed.value:
                problems.append(
                    Problem("block", "nonOccupancyPercent", {"required": _num(fixed.value), **cite})
                )
            if head.base_standard_code and head.base_standard_code != "service":
                problems.append(Problem("block", "nonOccupancyBase", cite))
        if head.applies_to != "let_out_only":
            problems.append(Problem("block", "nonOccupancyLetOut", cite))
        return problems

    if (
        code in FUND_MINIMUM
        and head.calc_type == "pct_of_construction_cost"
        and head.percent is not None
    ):
        minimum = legal[FUND_MINIMUM[code]]
        if head.percent < minimum.value:
            problems.append(
                Problem(
                    "warn",
                    "belowFundMinimum",
                    {"minimum": _num(minimum.value), "rule": minimum.source},
                )
            )

    if statutory and code != "other" and head.calc_type != statutory.calc_type:
        problems.append(
            Problem(
                "warn", "methodDeviation", {"method": statutory.calc_type, "rule": statutory.rule}
            )
        )
    return problems


def needs_reason(problems: list[Problem]) -> tuple[bool, bool]:
    """(needs a recorded reason, needs a general body resolution reference)."""
    warned = {p.key for p in problems if p.level == "warn"}
    return bool(warned), "methodDeviation" in warned
