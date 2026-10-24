"""Payments (docs/06 §4), dues ageing (§6) and receipt amounts in words (docs/02 §6).
Pure functions; integer paise."""

from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Literal


@dataclass(frozen=True)
class DueItem:
    """Something a payment can settle: an opening balance or a bill, with what is unpaid."""

    id: str
    due_on: date
    unpaid_paise: int


@dataclass(frozen=True)
class Allocation:
    allocations: list[tuple[str, int]]
    # Left after every item is settled: an advance (the ledger balance goes negative).
    remainder_paise: int


def allocate(items: list[DueItem], amount_paise: int) -> Allocation:
    """Oldest first; items on the same day keep the order given. Each item is settled as a
    whole (charges and interest together) until Q-008 decides otherwise."""
    if amount_paise <= 0:
        raise ValueError("A payment must be more than zero")
    if any(i.unpaid_paise < 0 for i in items):
        raise ValueError("Unpaid amounts cannot be negative")
    left = amount_paise
    result: list[tuple[str, int]] = []
    ordered = sorted(enumerate(items), key=lambda pair: (pair[1].due_on, pair[0]))
    for _, item in ordered:
        if left == 0:
            break
        if item.unpaid_paise == 0:
            continue
        take = min(left, item.unpaid_paise)
        result.append((item.id, take))
        left -= take
    return Allocation(result, left)


Bucket = Literal["paid_up", "friendly", "formal", "long"]


def bucket_for(months_pending: int) -> Bucket:
    """docs/06 §6: 0 paid up; 1-2 friendly reminder; 3-5 formal reminder; 6+ long pending."""
    if months_pending <= 0:
        return "paid_up"
    if months_pending <= 2:
        return "friendly"
    if months_pending <= 5:
        return "formal"
    return "long"


def opening_months_left(original_paise: int, months: int | None, unpaid_paise: int) -> int:
    """Months still pending in an opening balance: its months scaled by the share unpaid,
    rounded up. Without a month count it counts as one pending item while anything is unpaid."""
    if unpaid_paise <= 0 or original_paise <= 0:
        return 0
    if not months:
        return 1
    return ceil(months * unpaid_paise / original_paise)


_ONES = [
    "Zero",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def _below_thousand(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if rest:
        parts.append(_below_hundred(rest))
    return " ".join(parts)


def _indian(n: int) -> str:
    """Indian system: crore, lakh, thousand (docs/03 §6)."""
    if n == 0:
        return "Zero"
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1000)
    parts = []
    if crore:
        parts.append(f"{_indian(crore)} Crore")
    if lakh:
        parts.append(f"{_below_hundred(lakh)} Lakh")
    if thousand:
        parts.append(f"{_below_hundred(thousand)} Thousand")
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def amount_in_words(paise: int) -> str:
    """'Rupees Ten Thousand Only'; paise added only when non-zero."""
    if paise < 0:
        raise ValueError("Amount cannot be negative")
    rupees, rest = divmod(paise, 100)
    text = f"Rupees {_indian(rupees)}"
    if rest:
        text += f" and {_below_hundred(rest)} Paise"
    return text + " Only"
