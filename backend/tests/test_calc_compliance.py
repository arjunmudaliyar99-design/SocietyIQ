"""docs/06 §9 (compliance status and reminders). Pure functions."""

from datetime import date, timedelta

import pytest

from app.calc.compliance import add_months, next_due_after, reminder_today, status

TODAY = date(2026, 10, 24)


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(-5, "overdue"), (-1, "overdue"), (0, "due_soon"), (12, "due_soon"), (30, "due_soon"),
     (31, "ok"), (150, "ok")],
)  # fmt: skip
def test_status(offset: int, expected: str) -> None:
    assert status(TODAY + timedelta(days=offset), TODAY) == expected


def test_seed_generator_overdue_and_tank_due_soon() -> None:
    assert status(TODAY - timedelta(days=5), TODAY) == "overdue"
    assert status(TODAY + timedelta(days=12), TODAY) == "due_soon"


@pytest.mark.parametrize(
    ("day", "months", "expected"),
    [
        (date(2026, 10, 24), 6, date(2027, 4, 24)),
        (date(2026, 10, 24), 12, date(2027, 10, 24)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 8, 31), 3, date(2026, 11, 30)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
        (date(2026, 11, 30), 14, date(2028, 1, 30)),
    ],
)
def test_add_months_same_day_clamped_to_month_end(day: date, months: int, expected: date) -> None:
    assert add_months(day, months) == expected


def test_add_months_rejects_zero() -> None:
    with pytest.raises(ValueError):
        add_months(TODAY, 0)


def test_next_due_after_mark_done() -> None:
    assert next_due_after(date(2026, 10, 20), 6) == date(2027, 4, 20)
    assert next_due_after(date(2026, 10, 20), None) is None


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(90, 90), (60, 60), (30, 30), (7, 7), (0, 0), (89, None), (1, None), (-1, None),
     (-6, None), (-7, -7), (-14, -14), (-15, None)],
)  # fmt: skip
def test_reminder_days(offset: int, expected: int | None) -> None:
    assert reminder_today(TODAY + timedelta(days=offset), TODAY) == expected
