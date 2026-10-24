"""Compliance status, next due date and reminder days (docs/06 §9). Pure functions."""

import calendar
from datetime import date
from typing import Literal

Status = Literal["ok", "due_soon", "overdue"]

DUE_SOON_DAYS = 30
REMINDER_DAYS_BEFORE = (90, 60, 30, 7, 0)
OVERDUE_REPEAT_DAYS = 7


def status(next_due_on: date, today: date) -> Status:
    days = (next_due_on - today).days
    if days < 0:
        return "overdue"
    if days <= DUE_SOON_DAYS:
        return "due_soon"
    return "ok"


def add_months(day: date, months: int) -> date:
    """Same day of the month, clamped to the month end (31 Jan + 1 month → 28/29 Feb)."""
    if months < 1:
        raise ValueError("Repeat interval must be at least one month")
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_due_after(done_on: date, repeat_months: int | None) -> date | None:
    """None for a one-off item: nothing is due again after it is done."""
    return add_months(done_on, repeat_months) if repeat_months else None


def reminder_today(next_due_on: date, today: date) -> int | None:
    """Days before due (90, 60, 30, 7, 0) or, while overdue, minus the days overdue on each
    weekly reminder (-7, -14, ...). None when no reminder falls on this day."""
    days = (next_due_on - today).days
    if days in REMINDER_DAYS_BEFORE:
        return days
    if days < 0 and -days % OVERDUE_REPEAT_DAYS == 0:
        return days
    return None
