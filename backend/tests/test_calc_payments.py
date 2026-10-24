"""docs/06 §4 (allocation), §6 (dues buckets), and amounts in words for receipts (docs/02 §6).
Pure functions."""

from datetime import date

import pytest

from app.calc.payments import (
    DueItem,
    allocate,
    amount_in_words,
    bucket_for,
    opening_months_left,
)


def _bills(n: int, amount: int = 420000) -> list[DueItem]:
    return [DueItem(id=f"b{i}", due_on=date(2026, 4 + i, 1), unpaid_paise=amount) for i in range(n)]


def test_worked_example_oldest_first() -> None:
    """B-207 owes ₹29,400 across 7 bills of ₹4,200. Cash ₹10,000 → oldest 2 bills paid,
    third partly paid ₹1,600; ₹19,400 left."""
    result = allocate(_bills(7), 1000000)
    assert result.allocations == [("b0", 420000), ("b1", 420000), ("b2", 160000)]
    assert result.remainder_paise == 0
    assert sum(i.unpaid_paise for i in _bills(7)) - 1000000 == 1940000


def test_remainder_becomes_advance() -> None:
    result = allocate(_bills(1), 500000)
    assert result.allocations == [("b0", 420000)]
    assert result.remainder_paise == 80000


def test_order_is_by_date_then_given_order_and_skips_paid_items() -> None:
    items = [
        DueItem("late", date(2026, 6, 1), 100),
        DueItem("paid", date(2026, 1, 1), 0),
        DueItem("early", date(2026, 2, 1), 100),
        DueItem("same-day", date(2026, 2, 1), 100),
    ]
    assert allocate(items, 250).allocations == [("early", 100), ("same-day", 100), ("late", 50)]


def test_allocate_rejects_bad_amounts() -> None:
    with pytest.raises(ValueError):
        allocate(_bills(1), 0)
    with pytest.raises(ValueError):
        allocate([DueItem("x", date(2026, 1, 1), -5)], 100)


@pytest.mark.parametrize(
    ("months", "bucket"),
    [
        (0, "paid_up"),
        (1, "friendly"),
        (2, "friendly"),
        (3, "formal"),
        (5, "formal"),
        (6, "long"),
        (7, "long"),
    ],
)
def test_buckets(months: int, bucket: str) -> None:
    assert bucket_for(months) == bucket


def test_opening_months_left_scales_with_what_is_unpaid() -> None:
    # ₹29,400 for 7 months, nothing paid → 7; ₹10,000 paid → ₹19,400 left → ceil(4.62) = 5
    assert opening_months_left(2940000, 7, 2940000) == 7
    assert opening_months_left(2940000, 7, 1940000) == 5
    assert opening_months_left(2940000, 7, 0) == 0
    # Months unknown (old imports): one pending item while anything is unpaid.
    assert opening_months_left(500000, None, 1) == 1
    assert opening_months_left(0, None, 0) == 0


@pytest.mark.parametrize(
    ("paise", "words"),
    [
        (1000000, "Rupees Ten Thousand Only"),
        (2940000, "Rupees Twenty-Nine Thousand Four Hundred Only"),
        (13100000, "Rupees One Lakh Thirty-One Thousand Only"),
        (
            1234567805,
            "Rupees One Crore Twenty-Three Lakh Forty-Five Thousand Six Hundred Seventy-Eight"
            " and Five Paise Only",
        ),
        (50, "Rupees Zero and Fifty Paise Only"),
        (100, "Rupees One Only"),
        (10000000000, "Rupees Ten Crore Only"),
    ],
)
def test_amount_in_words_indian_system(paise: int, words: str) -> None:
    assert amount_in_words(paise) == words


def test_amount_in_words_rejects_negative() -> None:
    with pytest.raises(ValueError):
        amount_in_words(-1)
