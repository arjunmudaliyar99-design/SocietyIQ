"""docs/06 §1-2: charges for one flat in one period. Pure functions, every worked example."""

from datetime import date
from decimal import Decimal

import pytest

from app.calc.charges import (
    FlatData,
    HeadConfig,
    Period,
    bill_rounding,
    compute_charges,
    flat_sort_key,
    round_half_up,
    split_by_weight,
    split_equally,
)

MONTH = Period(start=date(2026, 11, 1), end=date(2026, 11, 30), months=1, periods_per_year=12)


def flat(fid: str, **kw: object) -> FlatData:
    base: dict[str, object] = {
        "id": fid,
        "wing": "A",
        "number": fid,
        "wing_has_lift": True,
        "carpet_area_sqft": None,
        "water_points": None,
        "construction_cost_paise": None,
        "occupancy": "owner_occupied",
        "member_count": 1,
    }
    base.update(kw)
    return FlatData(**base)  # type: ignore[arg-type]


def head(hid: str, calc_type: str, **kw: object) -> HeadConfig:
    base: dict[str, object] = {"id": hid, "name": hid, "calc_type": calc_type}
    base.update(kw)
    return HeadConfig(**base)  # type: ignore[arg-type]


def amounts(result, head_id: str) -> dict[str, int]:  # noqa: ANN001
    return {f: lines.get(head_id, 0) for f, lines in result.by_flat.items()}


# --- basics --------------------------------------------------------------------------


def test_round_half_up() -> None:
    assert round_half_up(Decimal("2.5")) == 3
    assert round_half_up(Decimal("3.5")) == 4
    assert round_half_up(Decimal("2.4999")) == 2
    assert round_half_up(Decimal("-2.5")) == -3


def test_flat_sort_key_is_natural() -> None:
    labels = [("A", "1001"), ("A", "201"), ("B", "101"), ("A", "1001A"), ("A", "45")]
    assert sorted(labels, key=lambda x: flat_sort_key(*x)) == [
        ("A", "45"),
        ("A", "201"),
        ("A", "1001"),
        ("A", "1001A"),
        ("B", "101"),
    ]


def test_split_equally_gives_remainder_in_flat_order() -> None:
    assert split_equally(1000, 3) == [334, 333, 333]
    assert sum(split_equally(100001, 7)) == 100001
    assert split_equally(0, 4) == [0, 0, 0, 0]
    assert split_equally(5, 0) == []


def test_split_by_weight_adds_up_exactly() -> None:
    parts = split_by_weight(100000, [Decimal("450"), Decimal("1000"), Decimal("3550")])
    assert parts == [9000, 20000, 71000]
    odd = split_by_weight(1000, [Decimal(1), Decimal(1), Decimal(1)])
    assert odd == [334, 333, 333]
    assert sum(split_by_weight(99999, [Decimal("1.5"), Decimal("2.25"), Decimal("7")])) == 99999
    assert split_by_weight(500, [Decimal(0), Decimal(0)]) == [0, 0]


def test_bill_rounding() -> None:
    assert bill_rounding(454550, "nearest_rupee") == 50  # ₹4,545.50 → ₹4,546
    assert bill_rounding(454549, "nearest_rupee") == -49
    assert bill_rounding(454500, "nearest_rupee") == 0
    assert bill_rounding(454549, "none") == 0


# --- docs/06 §2 worked example -------------------------------------------------------


def test_statutory_example_flat_301() -> None:
    """10 flats in a wing with a lift. Service ₹30,000; lift ₹9,500; insurance ₹500/month by
    carpet area (301 has 450 of 5,000 sq ft); sinking 0.25% of ₹12,00,000; 301 let out.
    Total for 301 = 3,000 + 300 + 950 + 45 + 250 = ₹4,545."""
    areas = [Decimal(450)] + [Decimal(4550) / 9] * 9
    flats = [
        flat(
            "301" if i == 0 else f"40{i}",
            carpet_area_sqft=areas[i],
            construction_cost_paise=120000000,
            occupancy="let_out" if i == 0 else "owner_occupied",
        )
        for i in range(10)
    ]
    heads = [
        head("service", "equal_per_flat", standard_code="service", period_total_paise=3000000),
        head(
            "non_occ",
            "pct_of_head",
            standard_code="non_occupancy",
            percent=Decimal(10),
            percent_of_head_id="service",
            applies_to="let_out_only",
        ),
        head("lift", "equal_per_flat_with_lift", period_total_paise=950000),
        head("insurance", "per_carpet_area", period_total_paise=50000),
        head("sinking", "pct_of_construction_cost", percent=Decimal("0.25")),
    ]
    result = compute_charges(flats, heads, MONTH)
    lines = result.by_flat["301"]
    assert lines == {
        "service": 300000,
        "non_occ": 30000,
        "lift": 95000,
        "insurance": 4500,
        "sinking": 25000,
    }
    assert result.totals["301"] == 454500
    assert result.excluded == {}
    # Owner-occupied flats pay no non-occupancy charge.
    assert result.by_flat["401"]["non_occ"] == 0
    # The split heads add up exactly to their totals.
    assert sum(amounts(result, "service").values()) == 3000000
    assert sum(amounts(result, "insurance").values()) == 50000


def test_seed_shanti_sadan_monthly_total() -> None:
    """docs/02 §12: ₹3,400 service + ₹600 repair fund + ₹200 sinking = ₹4,200; A-305 let out
    pays ₹340 more."""
    flats = [flat(f"F{i:03d}", construction_cost_paise=96000000) for i in range(120)]
    flats[5] = flat("A-305", construction_cost_paise=96000000, occupancy="let_out")
    heads = [
        head("service", "equal_per_flat", standard_code="service", period_total_paise=340000 * 120),
        head("repair", "pct_of_construction_cost", percent=Decimal("0.75")),
        head("sinking", "pct_of_construction_cost", percent=Decimal("0.25")),
        head(
            "non_occ",
            "pct_of_head",
            percent=Decimal(10),
            percent_of_head_id="service",
            applies_to="let_out_only",
        ),
    ]
    result = compute_charges(flats, heads, MONTH)
    assert {t for f, t in result.totals.items() if f != "A-305"} == {420000}
    assert result.totals["A-305"] == 454000


# --- each method ---------------------------------------------------------------------


def test_lift_only_for_wings_with_a_lift() -> None:
    flats = [flat("1"), flat("2"), flat("3", wing="B", wing_has_lift=False)]
    result = compute_charges(
        flats, [head("lift", "equal_per_flat_with_lift", period_total_paise=1001)], MONTH
    )
    assert amounts(result, "lift") == {"1": 501, "2": 500, "3": 0}


def test_missing_carpet_area_excludes_the_flat_with_a_reason() -> None:
    flats = [flat("1", carpet_area_sqft=Decimal(500)), flat("2")]
    result = compute_charges(
        flats, [head("ins", "per_carpet_area", period_total_paise=10000)], MONTH
    )
    assert amounts(result, "ins") == {"1": 10000}
    assert result.excluded == {"2": ["missingCarpetArea"]}


def test_water_by_points_with_fractions() -> None:
    flats = [
        flat("1", water_points=Decimal(2)),
        flat("2", water_points=Decimal("1.5")),
        flat("3", water_points=Decimal("0.5")),
    ]
    result = compute_charges(
        flats, [head("water", "per_water_point", period_total_paise=40000)], MONTH
    )
    assert amounts(result, "water") == {"1": 20000, "2": 15000, "3": 5000}


def test_missing_water_points_and_cost_exclude() -> None:
    result = compute_charges(
        [flat("1")],
        [
            head("water", "per_water_point", period_total_paise=100),
            head("sink", "pct_of_construction_cost", percent=Decimal("0.25")),
        ],
        MONTH,
    )
    assert result.excluded == {"1": ["missingWaterPoints", "missingConstructionCost"]}
    assert result.totals == {}


def test_construction_cost_rounds_half_up_per_flat() -> None:
    # 0.25% of ₹10,00,001 a year = 250000.25 paise; / 12 = 20833.354 paise → 20833
    result = compute_charges(
        [flat("1", construction_cost_paise=100000100)],
        [head("s", "pct_of_construction_cost", percent=Decimal("0.25"))],
        MONTH,
    )
    assert result.by_flat["1"]["s"] == 20833


def test_quarter_uses_the_quarter_share() -> None:
    quarter = Period(start=date(2026, 10, 1), end=date(2026, 12, 31), months=3, periods_per_year=4)
    result = compute_charges(
        [flat("1", construction_cost_paise=96000000, member_count=2)],
        [
            head("s", "pct_of_construction_cost", percent=Decimal("0.25")),
            head("edu", "per_member_fixed", fixed_amount_paise=1000),
        ],
        quarter,
    )
    assert result.by_flat["1"] == {"s": 60000, "edu": 6000}


def test_assessed_property_tax_and_exemption() -> None:
    flats = [flat("300sqft"), flat("650sqft"), flat("no-assessment")]
    tax = head(
        "tax",
        "as_assessed_per_flat",
        assessed_annual_paise={"300sqft": 0, "650sqft": 1200000},
    )
    result = compute_charges(flats, [tax], MONTH)
    assert amounts(result, "tax") == {"300sqft": 0, "650sqft": 100000, "no-assessment": 0}
    assert result.warnings == {"no-assessment": ["missingAssessment"]}


def test_parking_fixed_and_custom() -> None:
    flats = [flat("1"), flat("2")]
    heads = [
        head("park", "per_parking_allotment", parking_monthly_paise={"1": 150000}),
        head("loan", "fixed_per_flat", fixed_amount_paise=25000),
        head("custom", "custom_per_flat"),
        head("welfare", "voluntary"),
    ]
    result = compute_charges(flats, heads, MONTH)
    assert result.by_flat["1"] == {"park": 150000, "loan": 25000, "custom": 0, "welfare": 0}
    assert result.by_flat["2"]["park"] == 0


def test_override_replaces_the_computed_amount() -> None:
    flats = [flat("1"), flat("2")]
    heads = [head("service", "equal_per_flat", period_total_paise=2000, overrides={"2": 500})]
    result = compute_charges(flats, heads, MONTH)
    assert amounts(result, "service") == {"1": 1000, "2": 500}
    assert result.overridden == {"2": ["service"]}


def test_pct_of_head_uses_the_overridden_base() -> None:
    flats = [flat("1", occupancy="let_out")]
    heads = [
        head("service", "equal_per_flat", period_total_paise=3000, overrides={"1": 2000}),
        head(
            "non",
            "pct_of_head",
            percent=Decimal(10),
            percent_of_head_id="service",
            applies_to="let_out_only",
        ),
    ]
    assert compute_charges(flats, heads, MONTH).by_flat["1"]["non"] == 200


def test_one_time_head_only_in_its_period() -> None:
    heads = [
        head(
            "paint",
            "fixed_per_flat",
            fixed_amount_paise=100,
            frequency="one_time",
            one_time_period=date(2026, 12, 1),
        )
    ]
    assert compute_charges([flat("1")], heads, MONTH).by_flat["1"] == {}
    december = Period(
        start=date(2026, 12, 1), end=date(2026, 12, 31), months=1, periods_per_year=12
    )
    assert compute_charges([flat("1")], heads, december).by_flat["1"] == {"paint": 100}


def test_vacant_and_family_flats_pay_no_non_occupancy() -> None:
    flats = [
        flat("v", occupancy="vacant"),
        flat("f", occupancy="family_occupied"),
        flat("l", occupancy="let_out"),
    ]
    heads = [
        head("service", "equal_per_flat", period_total_paise=3000),
        head(
            "non",
            "pct_of_head",
            percent=Decimal(10),
            percent_of_head_id="service",
            applies_to="let_out_only",
        ),
    ]
    assert amounts(compute_charges(flats, heads, MONTH), "non") == {"v": 0, "f": 0, "l": 100}


def test_excluded_flats_do_not_change_other_shares() -> None:
    """A flat missing carpet area is out of the run; equal heads split over the flats billed."""
    flats = [
        flat("1", carpet_area_sqft=Decimal(1)),
        flat("2", carpet_area_sqft=Decimal(1)),
        flat("3"),
    ]
    heads = [
        head("service", "equal_per_flat", period_total_paise=3000),
        head("ins", "per_carpet_area", period_total_paise=100),
    ]
    result = compute_charges(flats, heads, MONTH)
    assert result.excluded == {"3": ["missingCarpetArea"]}
    assert amounts(result, "service") == {"1": 1500, "2": 1500}


def test_unknown_reference_head_is_a_config_error() -> None:
    with pytest.raises(ValueError, match="percent_of_head_id"):
        compute_charges(
            [flat("1")],
            [head("n", "pct_of_head", percent=Decimal(10), percent_of_head_id="x")],
            MONTH,
        )


def test_period_must_be_whole_months() -> None:
    with pytest.raises(ValueError):
        Period(start=date(2026, 11, 1), end=date(2026, 11, 30), months=2, periods_per_year=12)


def test_unknown_method_is_a_config_error() -> None:
    with pytest.raises(ValueError, match="calc_type"):
        compute_charges([flat("1")], [head("x", "by_mood")], MONTH)
