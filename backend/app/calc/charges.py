"""Charges for every flat in one billing period (docs/06 §1-2). Pure functions: no database,
no clock, integer paise in and out. Rates use Decimal and round half-up to whole paise.

Split methods (equal, by carpet area, by water points) share a total so the parts add up
exactly: each flat gets the floor of its share, then the remaining paise go one each to
flats in flat-number order (docs/06 §2).

A flat missing an input a head needs (carpet area, water points, construction cost) is left
out of the whole run with the reason, never billed a silent zero (docs/06 §2).
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

SPLIT_TYPES = {"equal_per_flat", "equal_per_flat_with_lift", "per_carpet_area", "per_water_point"}
TOTAL_TYPES = SPLIT_TYPES
CALC_TYPES = {
    *SPLIT_TYPES,
    "as_assessed_per_flat",
    "pct_of_head",
    "pct_of_construction_cost",
    "per_parking_allotment",
    "per_member_fixed",
    "fixed_per_flat",
    "custom_per_flat",
    "voluntary",
}

# Head type → the flat input it needs, and the reason key when it is missing.
REQUIRED_INPUT = {
    "per_carpet_area": ("carpet_area_sqft", "missingCarpetArea"),
    "per_water_point": ("water_points", "missingWaterPoints"),
    "pct_of_construction_cost": ("construction_cost_paise", "missingConstructionCost"),
}


def round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _floor(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_FLOOR))


def _natural(text: str) -> tuple[tuple[int, int, str], ...]:
    return tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part.lower())
        for part in re.findall(r"\d+|\D+", text)
    )


def flat_sort_key(wing: str, number: str) -> tuple[object, ...]:
    """Flat-number order: wing, then number, comparing digit runs as numbers (45 < 201)."""
    return (_natural(wing), _natural(number))


def split_equally(total_paise: int, count: int) -> list[int]:
    if count <= 0:
        return []
    base, remainder = divmod(total_paise, count)
    return [base + (1 if i < remainder else 0) for i in range(count)]


def split_by_weight(total_paise: int, weights: Sequence[Decimal]) -> list[int]:
    whole = sum(weights, Decimal(0))
    if whole <= 0:
        return [0 for _ in weights]
    parts = [_floor(Decimal(total_paise) * w / whole) for w in weights]
    for i in range(total_paise - sum(parts)):
        parts[i % len(parts)] += 1
    return parts


def bill_rounding(charges_paise: int, rule: str) -> int:
    """The "Rounding off" line (docs/06 §1): what to add so the charges total is whole
    rupees. Zero when the society keeps exact paise."""
    if rule != "nearest_rupee":
        return 0
    return round_half_up(Decimal(charges_paise) / 100) * 100 - charges_paise


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    months: int
    periods_per_year: int

    def __post_init__(self) -> None:
        if self.months * self.periods_per_year != 12 or self.months not in (1, 3):
            raise ValueError("A billing period is one month or one quarter")

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True)
class FlatData:
    id: str
    wing: str
    number: str
    wing_has_lift: bool
    carpet_area_sqft: Decimal | None
    water_points: Decimal | None
    construction_cost_paise: int | None
    occupancy: str
    member_count: int


@dataclass(frozen=True)
class HeadConfig:
    id: str
    name: str
    calc_type: str
    standard_code: str | None = None
    period_total_paise: int | None = None
    fixed_amount_paise: int | None = None
    percent: Decimal | None = None
    percent_of_head_id: str | None = None
    applies_to: str = "all"
    frequency: str = "every_bill"
    one_time_period: date | None = None
    # flat id → annual municipal amount (as_assessed_per_flat)
    assessed_annual_paise: dict[str, int] = field(default_factory=dict)
    # flat id → monthly GB rate of its active allotments (per_parking_allotment)
    parking_monthly_paise: dict[str, int] = field(default_factory=dict)
    # flat id → amount replacing the computed one this period
    overrides: dict[str, int] = field(default_factory=dict)


@dataclass
class ChargesResult:
    # flat id → head id → paise, for flats in the run, in flat-number order
    by_flat: dict[str, dict[str, int]]
    totals: dict[str, int]
    # flat id → reason keys; these flats are left out of the run until fixed
    excluded: dict[str, list[str]]
    # flat id → reason keys; billed, but worth a look
    warnings: dict[str, list[str]]
    # flat id → head ids whose amount came from an override
    overridden: dict[str, list[str]]


def _ordered(heads: Iterable[HeadConfig]) -> list[HeadConfig]:
    """Base heads first, then heads that are a percent of another head."""
    heads = list(heads)
    ids = {h.id: h for h in heads}
    for h in heads:
        if h.calc_type not in CALC_TYPES:
            raise ValueError(f"Unknown calc_type {h.calc_type!r}")
        if h.calc_type == "pct_of_head":
            base = ids.get(h.percent_of_head_id or "")
            if base is None or base.calc_type == "pct_of_head":
                raise ValueError(f"Head {h.id}: percent_of_head_id must name a non-percent head")
    return sorted(heads, key=lambda h: h.calc_type == "pct_of_head")


def _applies(head: HeadConfig, flat: FlatData) -> bool:
    return head.applies_to != "let_out_only" or flat.occupancy == "let_out"


def _pct(amount: int | Decimal, percent: Decimal | None) -> Decimal:
    return Decimal(amount) * (percent or Decimal(0)) / 100


def compute_charges(
    flats: Iterable[FlatData], heads: Iterable[HeadConfig], period: Period
) -> ChargesResult:
    active = [
        h
        for h in _ordered(heads)
        if h.frequency != "one_time" or (h.one_time_period and period.contains(h.one_time_period))
    ]
    all_flats = sorted(flats, key=lambda f: flat_sort_key(f.wing, f.number))

    excluded: dict[str, list[str]] = {}
    for f in all_flats:
        for h in active:
            need = REQUIRED_INPUT.get(h.calc_type)
            if need and _applies(h, f) and getattr(f, need[0]) is None:
                reasons = excluded.setdefault(f.id, [])
                if need[1] not in reasons:
                    reasons.append(need[1])
    billed = [f for f in all_flats if f.id not in excluded]

    by_flat: dict[str, dict[str, int]] = {f.id: {} for f in billed}
    warnings: dict[str, list[str]] = {}
    overridden: dict[str, list[str]] = {}

    for h in active:
        eligible = [f for f in billed if _applies(h, f)]
        amounts: dict[str, int] = {f.id: 0 for f in billed}
        total = h.period_total_paise or 0

        if h.calc_type == "equal_per_flat":
            amounts.update(
                zip([f.id for f in eligible], split_equally(total, len(eligible)), strict=True)
            )
        elif h.calc_type == "equal_per_flat_with_lift":
            lifted = [f for f in eligible if f.wing_has_lift]
            amounts.update(
                zip([f.id for f in lifted], split_equally(total, len(lifted)), strict=True)
            )
        elif h.calc_type in ("per_carpet_area", "per_water_point"):
            attr = "carpet_area_sqft" if h.calc_type == "per_carpet_area" else "water_points"
            weights = [getattr(f, attr) for f in eligible]
            amounts.update(
                zip([f.id for f in eligible], split_by_weight(total, weights), strict=True)
            )
        elif h.calc_type == "pct_of_construction_cost":
            for f in eligible:
                yearly = _pct(f.construction_cost_paise or 0, h.percent)
                amounts[f.id] = round_half_up(yearly / period.periods_per_year)
        elif h.calc_type == "as_assessed_per_flat":
            for f in eligible:
                if f.id not in h.assessed_annual_paise:
                    warnings.setdefault(f.id, []).append("missingAssessment")
                annual = h.assessed_annual_paise.get(f.id, 0)
                amounts[f.id] = round_half_up(Decimal(annual) / period.periods_per_year)
        elif h.calc_type == "per_parking_allotment":
            for f in eligible:
                amounts[f.id] = h.parking_monthly_paise.get(f.id, 0) * period.months
        elif h.calc_type == "per_member_fixed":
            for f in eligible:
                amounts[f.id] = (h.fixed_amount_paise or 0) * f.member_count * period.months
        elif h.calc_type == "fixed_per_flat":
            for f in eligible:
                amounts[f.id] = h.fixed_amount_paise or 0
        elif h.calc_type == "pct_of_head":
            base_id = h.percent_of_head_id or ""
            for f in eligible:
                amounts[f.id] = round_half_up(_pct(by_flat[f.id].get(base_id, 0), h.percent))
        # custom_per_flat and voluntary stay 0 unless overridden for the flat.

        for f in billed:
            if f.id in h.overrides:
                amounts[f.id] = h.overrides[f.id]
                overridden.setdefault(f.id, []).append(h.id)
            by_flat[f.id][h.id] = amounts[f.id]

    totals = {fid: sum(lines.values()) for fid, lines in by_flat.items()}
    return ChargesResult(by_flat, totals, excluded, warnings, overridden)
