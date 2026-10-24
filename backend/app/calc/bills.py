"""A bill's figures (docs/06 §3) and simple interest on overdue bills (docs/06 §5).
Pure functions; integer paise; rates as Decimal; half-up rounding."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.calc.charges import round_half_up


@dataclass(frozen=True)
class BillFigures:
    charges_paise: int
    arrears_paise: int
    advance_paise: int
    interest_paise: int
    total_due_paise: int


def bill_figures(charges_paise: int, balance_before_paise: int, interest_paise: int) -> BillFigures:
    """balance_before: the flat's ledger balance before this bill (positive = owes).
    Arrears are already in the ledger and are shown, never posted again."""
    if charges_paise < 0 or interest_paise < 0:
        raise ValueError("Charges and interest cannot be negative")
    arrears = max(balance_before_paise, 0)
    advance = max(-balance_before_paise, 0)
    total = max(charges_paise + arrears + interest_paise - advance, 0)
    return BillFigures(charges_paise, arrears, advance, interest_paise, total)


def bill_number(financial_year: str, sequence: int) -> str:
    """docs/05 §3: B/2026-27/000123."""
    return f"B/{financial_year}/{sequence:06d}"


@dataclass(frozen=True)
class OverdueBill:
    # Unpaid charges of the bill (never its interest: no interest on interest).
    principal_paise: int
    due_date: date


def interest_on_overdue(
    bills: Iterable[OverdueBill],
    rate_pct: Decimal,
    grace_days: int,
    charged_through: date,
    as_of: date,
) -> int:
    """Simple interest from the later of (due date + grace) and the date interest was last
    charged up to, until `as_of`. Summed exactly, rounded once.

    TODO(confirm): Q-002 — the exact day default starts (Act s.154B-1(11),(12), bye-laws)."""
    total = Decimal(0)
    for bill in bills:
        start = max(bill.due_date + timedelta(days=grace_days), charged_through)
        days = (as_of - start).days
        if days > 0 and bill.principal_paise > 0:
            total += Decimal(bill.principal_paise) * rate_pct / 100 * days / 365
    return round_half_up(total)
