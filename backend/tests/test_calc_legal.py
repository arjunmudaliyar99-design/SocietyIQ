"""docs/06 §2 validation and §5 interest cap. Limits come from legal_parameters, passed in."""

from decimal import Decimal

from app.calc.legal import (
    STANDARD_HEADS,
    HeadDraft,
    LegalValue,
    Problem,
    needs_reason,
    validate_head,
    validate_interest,
)

LEGAL = {
    "interest_max_annual_pct": LegalValue(Decimal(12), "MCS Rules 106C-12 (2026)"),
    "non_occupancy_pct_of_service": LegalValue(Decimal(10), "MCS Rules 106C-12 (2026)"),
    "sinking_fund_min_annual_pct": LegalValue(Decimal("0.25"), "MCS Rules 106C-11 (2026)"),
    "repair_fund_min_annual_pct": LegalValue(Decimal("0.75"), "MCS Rules 106C-11 (2026)"),
}


def draft(code: str | None, calc_type: str | None = None, **kw: object) -> HeadDraft:
    base: dict[str, object] = {
        "standard_code": code,
        "calc_type": calc_type or (STANDARD_HEADS[code].calc_type if code else "fixed_per_flat"),
    }
    base.update(kw)
    return HeadDraft(**base)  # type: ignore[arg-type]


def keys(problems: list[Problem]) -> list[tuple[str, str]]:
    return [(p.level, p.key) for p in problems]


def test_every_standard_head_has_its_statutory_method() -> None:
    assert STANDARD_HEADS["service"].calc_type == "equal_per_flat"
    assert STANDARD_HEADS["lift"].calc_type == "equal_per_flat_with_lift"
    assert STANDARD_HEADS["insurance"].calc_type == "per_carpet_area"
    assert STANDARD_HEADS["sinking_fund"].calc_type == "pct_of_construction_cost"
    assert STANDARD_HEADS["non_occupancy"].applies_to == "let_out_only"
    assert STANDARD_HEADS["welfare_fund"].calc_type == "voluntary"
    assert "interest" not in STANDARD_HEADS  # interest is a society setting, docs/06 §5


def test_interest_above_cap_is_blocked_with_the_rule() -> None:
    [p] = validate_interest(Decimal("12.5"), LEGAL)
    assert (p.level, p.key) == ("block", "interestAboveCap")
    assert p.params == {"max": "12", "rule": "MCS Rules 106C-12 (2026)"}
    assert validate_interest(Decimal(12), LEGAL) == []
    assert validate_interest(Decimal(-1), LEGAL)[0].key == "notNegative"


def test_service_with_a_total_is_fine() -> None:
    assert validate_head(draft("service", period_total_paise=100), LEGAL) == []


def test_missing_inputs_block() -> None:
    assert keys(validate_head(draft("service"), LEGAL)) == [("block", "needsTotal")]
    assert keys(validate_head(draft("sinking_fund"), LEGAL)) == [("block", "needsPercent")]
    assert keys(validate_head(draft("education_fund"), LEGAL)) == [("block", "needsAmount")]
    assert ("block", "needsBaseHead") in keys(
        validate_head(draft("other", "pct_of_head", percent=Decimal(5)), LEGAL)
    )


def test_non_occupancy_other_than_ten_percent_is_blocked() -> None:
    ok = draft(
        "non_occupancy",
        percent=Decimal(10),
        base_standard_code="service",
        applies_to="let_out_only",
    )
    assert validate_head(ok, LEGAL) == []
    [p] = validate_head(
        draft(
            "non_occupancy",
            percent=Decimal(15),
            base_standard_code="service",
            applies_to="let_out_only",
        ),
        LEGAL,
    )
    assert (p.level, p.key, p.params["required"]) == ("block", "nonOccupancyPercent", "10")


def test_non_occupancy_must_be_on_service_charges_and_let_out_only() -> None:
    problems = validate_head(
        draft("non_occupancy", percent=Decimal(10), base_standard_code="lift", applies_to="all"),
        LEGAL,
    )
    assert ("block", "nonOccupancyBase") in keys(problems)
    assert ("block", "nonOccupancyLetOut") in keys(problems)
    other_method = validate_head(
        draft("non_occupancy", "fixed_per_flat", fixed_amount_paise=500), LEGAL
    )
    assert ("block", "nonOccupancyMethod") in keys(other_method)


def test_funds_below_minimum_warn_and_need_a_reason() -> None:
    low = draft("sinking_fund", percent=Decimal("0.2"))
    [p] = validate_head(low, LEGAL)
    assert (p.level, p.key) == ("warn", "belowFundMinimum")
    assert p.params == {"minimum": "0.25", "rule": "MCS Rules 106C-11 (2026)"}
    assert needs_reason([p]) == (True, False)
    assert validate_head(draft("repair_fund", percent=Decimal("0.75")), LEGAL) == []


def test_other_method_than_statutory_warns_and_needs_reason_and_resolution() -> None:
    [p] = validate_head(draft("service", "per_carpet_area", period_total_paise=100), LEGAL)
    assert (p.level, p.key) == ("warn", "methodDeviation")
    assert p.params == {"method": "equal_per_flat", "rule": "Rule 106C-12"}
    assert needs_reason([p]) == (True, True)
    # "Other" heads have no statutory method.
    assert validate_head(draft("other", "custom_per_flat"), LEGAL) == []


def test_negative_amounts_block() -> None:
    assert ("block", "notNegative") in keys(
        validate_head(draft("service", period_total_paise=-1), LEGAL)
    )
    assert ("block", "notNegative") in keys(
        validate_head(draft("other", fixed_amount_paise=-5), LEGAL)
    )
