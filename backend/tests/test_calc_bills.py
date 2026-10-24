"""docs/06 §3 (a bill) and §5 (interest). Pure functions."""

from datetime import date
from decimal import Decimal

import pytest

from app.calc.bills import OverdueBill, bill_figures, bill_number, interest_on_overdue


def test_b207_example_arrears_carry_into_total() -> None:
    """Balance before ₹25,200, new charges ₹4,200, interest off → total due ₹29,400."""
    f = bill_figures(charges_paise=420000, balance_before_paise=2520000, interest_paise=0)
    assert (f.arrears_paise, f.advance_paise, f.total_due_paise) == (2520000, 0, 2940000)


def test_advance_reduces_the_total() -> None:
    f = bill_figures(charges_paise=420000, balance_before_paise=-50000, interest_paise=0)
    assert (f.arrears_paise, f.advance_paise, f.total_due_paise) == (0, 50000, 370000)


def test_advance_larger_than_charges_gives_zero_due() -> None:
    f = bill_figures(charges_paise=420000, balance_before_paise=-500000, interest_paise=0)
    assert f.total_due_paise == 0


def test_interest_is_added_as_its_own_figure() -> None:
    f = bill_figures(charges_paise=420000, balance_before_paise=420000, interest_paise=4142)
    assert (f.interest_paise, f.total_due_paise) == (4142, 844142)


def test_negative_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        bill_figures(charges_paise=-1, balance_before_paise=0, interest_paise=0)
    with pytest.raises(ValueError):
        bill_figures(charges_paise=0, balance_before_paise=0, interest_paise=-1)


def test_bill_number_format() -> None:
    assert bill_number("2026-27", 123) == "B/2026-27/000123"


def test_simple_interest_on_one_overdue_bill() -> None:
    # ₹4,200 at 12% for 30 days: 420000 × 0.12 × 30/365 = 4142.47 paise → 4142
    paise = interest_on_overdue(
        [OverdueBill(principal_paise=420000, due_date=date(2026, 10, 16))],
        rate_pct=Decimal(12),
        grace_days=0,
        charged_through=date(2026, 10, 1),
        as_of=date(2026, 11, 15),
    )
    assert paise == 4142


def test_grace_days_and_charged_through_limit_the_days() -> None:
    bills = [OverdueBill(principal_paise=365000, due_date=date(2026, 10, 1))]
    # Grace pushes the start to 11 Oct; 20 days to 31 Oct at 10%: 365000 × 0.10 × 20/365 = 2000
    assert interest_on_overdue(bills, Decimal(10), 10, date(2026, 9, 1), date(2026, 10, 31)) == 2000
    # Interest already charged up to 21 Oct: only 10 more days → 1000 (never twice)
    assert (
        interest_on_overdue(bills, Decimal(10), 10, date(2026, 10, 21), date(2026, 10, 31)) == 1000
    )


def test_not_yet_overdue_and_zero_rate_give_nothing() -> None:
    bills = [OverdueBill(principal_paise=420000, due_date=date(2026, 11, 20))]
    assert interest_on_overdue(bills, Decimal(12), 0, date(2026, 11, 1), date(2026, 11, 15)) == 0
    assert interest_on_overdue(bills, Decimal(0), 0, date(2026, 1, 1), date(2026, 12, 1)) == 0
    assert interest_on_overdue([], Decimal(12), 0, date(2026, 1, 1), date(2026, 12, 1)) == 0


def test_interest_sums_bills_then_rounds_once() -> None:
    bills = [
        OverdueBill(principal_paise=100, due_date=date(2026, 1, 1)),
        OverdueBill(principal_paise=100, due_date=date(2026, 1, 1)),
    ]
    # Each alone: 100 × 0.12 × 1/365 = 0.0329 → would round to 0 twice; together still 0.0657 → 0
    # With 200 days: each 6.575 → rounding separately gives 14, once gives 13
    assert interest_on_overdue(bills, Decimal(12), 0, date(2026, 1, 1), date(2026, 7, 20)) == 13
