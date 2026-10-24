"""Flats and members import: parsing and checks of one row (docs/02 §4). No database."""

from decimal import Decimal

import pytest

from app.services.import_rows import (
    COLUMNS,
    Issue,
    check_rows,
    parse_money_paise,
    parse_phone,
)


def _row(**values: object) -> dict[str, object]:
    base: dict[str, object] = {key: None for key, _ in COLUMNS}
    base.update({"wing": "A", "flat_number": "101", "owner_name": "Member A-101"})
    base.update(values)
    return base


def _keys(issues: list[Issue]) -> list[str]:
    return [i.key for i in issues]


def _errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.is_error]


# --- money: rupees in the sheet, integer paise in the database (docs/06 §1) ----------


@pytest.mark.parametrize(
    ("raw", "paise"),
    [
        (4200, 420000),
        (4200.5, 420050),
        ("4,200", 420000),
        ("₹ 29,400.00", 2940000),
        ("1,31,000", 13100000),
        ("-1500", -150000),
        (0, 0),
        (Decimal("0.01"), 1),
    ],
)
def test_money_to_paise(raw: object, paise: int) -> None:
    assert parse_money_paise(raw) == (paise, None)


@pytest.mark.parametrize(
    ("raw", "problem"),
    [("12.345", "tooManyDecimals"), ("abc", "notNumber"), ("4,2,0,0x", "notNumber")],
)
def test_money_problems(raw: object, problem: str) -> None:
    assert parse_money_paise(raw) == (None, problem)


def test_float_cells_do_not_drift() -> None:
    # 0.1 + 0.2 style float noise from Excel must not change paise.
    assert parse_money_paise(0.1 + 0.2) == (30, None)
    assert parse_money_paise(1234.56) == (123456, None)


# --- phones --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("98000 00000", ("+919800000000", None)),
        ("+91 98000-00000", ("+919800000000", None)),
        ("09800000000", ("+919800000000", None)),
        (9800000000, ("+919800000000", None)),
        ("980000000", (None, 9)),
    ],
)
def test_phone(raw: object, expected: tuple[str | None, int | None]) -> None:
    assert parse_phone(raw) == expected


# --- rows ----------------------------------------------------------------------------


def test_clean_row_is_ok_and_normalised() -> None:
    [result] = check_rows(
        [
            (
                2,
                _row(
                    wing_has_lift="y",
                    carpet_area_sqft=650,
                    usage="Residential",
                    construction_cost="9,60,000",
                    water_points=2,
                    occupancy="Owner occupied",
                    owner_phone="98000 00000",
                    opening_balance="4,200",
                ),
            )
        ]
    )
    assert result.status == "ok", result.issues
    assert result.data["wing_has_lift"] is True
    assert result.data["construction_cost_paise"] == 96000000
    assert result.data["opening_balance_paise"] == 420000
    assert result.data["occupancy"] == "owner_occupied"
    assert result.data["owner_phone"] == "+919800000000"
    assert result.data["carpet_area_sqft"] == "650"


def test_missing_flat_number_is_error() -> None:
    [result] = check_rows([(5, _row(flat_number=None))])
    assert result.status == "error"
    assert _errors(result.issues) == [Issue("required", {"field": "flat_number"})]


def test_short_phone_says_how_many_digits() -> None:
    [result] = check_rows([(14, _row(owner_phone="980000000", carpet_area_sqft=500))])
    assert result.status == "error"
    assert _errors(result.issues) == [Issue("phoneDigits", {"field": "owner_phone", "digits": 9})]


def test_bad_choices_are_errors() -> None:
    [result] = check_rows([(2, _row(usage="shop", occupancy="rented", wing_has_lift="maybe"))])
    assert _keys(_errors(result.issues)) == ["badChoice", "badChoice", "badChoice"]


def test_warnings_do_not_block() -> None:
    [result] = check_rows([(2, _row(occupancy="let out"))])
    assert result.status == "warning"
    assert set(_keys(result.issues)) == {"carpetMissing", "costMissing", "letOutNoTenant"}


def test_duplicate_flat_in_file() -> None:
    rows = check_rows([(2, _row(carpet_area_sqft=1)), (3, _row(carpet_area_sqft=1))])
    assert rows[0].status != "error"
    assert rows[1].status == "error"
    assert rows[1].issues[0] == Issue("duplicateInFile", {"otherRow": 2})


def test_same_flat_number_in_two_wings_is_fine() -> None:
    rows = check_rows([(2, _row(wing="A")), (3, _row(wing="B"))])
    assert all(r.status != "error" for r in rows)


def test_lift_conflict_inside_file() -> None:
    rows = check_rows(
        [(2, _row(wing_has_lift="Y")), (3, _row(flat_number="102", wing_has_lift="N"))]
    )
    assert "liftConflict" in _keys(rows[1].issues)
    assert rows[1].status == "error"


def test_blank_wing_when_other_rows_name_wings() -> None:
    rows = check_rows([(2, _row(wing="A")), (3, _row(wing=None, flat_number="9"))])
    assert rows[1].status == "error"
    assert rows[1].issues[0] == Issue("required", {"field": "wing"})


def test_all_blank_wings_are_allowed() -> None:
    rows = check_rows([(2, _row(wing=None)), (3, _row(wing=None, flat_number="102"))])
    assert all(r.status != "error" for r in rows)
    assert rows[0].data["wing"] is None


def test_existing_flat_is_error() -> None:
    [result] = check_rows([(2, _row())], existing_flats={("a", "101")})
    assert result.status == "error"
    assert "alreadyExists" in _keys(result.issues)


def test_tenant_phone_without_name() -> None:
    [result] = check_rows([(2, _row(tenant_phone="9800000000"))])
    assert "tenantPhoneNoName" in _keys(result.issues)


def test_flat_number_from_numeric_cell() -> None:
    [result] = check_rows([(2, _row(flat_number=101.0))])
    assert result.data["flat_number"] == "101"
