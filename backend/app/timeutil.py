"""Dates in India time (docs/05: store UTC, show Asia/Kolkata). IST has no daylight saving,
so a fixed offset is exact and needs no time-zone database (absent on Windows)."""

from datetime import UTC, date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def today_ist() -> date:
    return datetime.now(UTC).astimezone(IST).date()
