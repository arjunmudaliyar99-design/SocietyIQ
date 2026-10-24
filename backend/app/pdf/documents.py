"""Receipts (docs/02 §6) and the flat ledger for recovery (docs/02 §7, docs/06 §6): HTML views
for the PDF templates, and the ledger as an Excel sheet."""

import io
from dataclasses import dataclass
from datetime import date
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from app.calc.payments import amount_in_words
from app.pdf.bills import day, rupees


@dataclass
class ReceiptView:
    society_name: str
    society_address: str | None
    number: str
    flat: str
    member: str | None
    received_on: str
    method: str
    reference: str | None
    amount: str
    words: str
    allocations: list[dict[str, Any]]
    advance: str | None
    cancelled: bool


def _address(society: Any) -> str | None:  # noqa: ANN401
    return ", ".join(p for p in (society.address_line, society.city, society.pincode) if p) or None


def receipt_view(
    *,
    society: Any,  # noqa: ANN401
    payment: Any,  # noqa: ANN401
    receipt: Any,  # noqa: ANN401
    flat_label: str,
    member: str | None,
    allocations: list[tuple[str, int]],
) -> ReceiptView:
    settled = sum(amount for _, amount in allocations)
    advance = payment.amount_paise - settled if receipt.cancelled_at is None else 0
    return ReceiptView(
        society_name=society.name,
        society_address=_address(society),
        number=receipt.receipt_number,
        flat=flat_label,
        member=member,
        received_on=day(payment.received_on),
        method=payment.method,
        reference=payment.reference,
        amount=rupees(payment.amount_paise),
        words=amount_in_words(payment.amount_paise),
        allocations=[
            {"settles": name, "opening": name == "opening", "amount": rupees(amount)}
            for name, amount in allocations
        ],
        advance=rupees(advance) if advance > 0 else None,
        cancelled=receipt.cancelled_at is not None,
    )


@dataclass
class LedgerView:
    society_name: str
    society_address: str | None
    registration_number: str | None
    flat: str
    member: str | None
    as_on: str
    lines: list[dict[str, Any]]
    balance: str
    resolutions: list[dict[str, Any]]
    interest_resolution: str | None


def ledger_view(
    *,
    society: Any,  # noqa: ANN401
    flat_label: str,
    member: str | None,
    lines: list[Any],
    heads: list[Any],
    as_on: date,
) -> LedgerView:
    """Every bill, payment, interest line and reversal with a running balance, plus the general
    body resolutions behind the charges and interest: what a recovery application needs."""
    rows = []
    for line in lines:
        amount = line.entry.amount_paise
        rows.append(
            {
                "date": day(line.entry.entry_date),
                "type": line.entry.entry_type,
                "document": line.document,
                "reason": line.entry.reason,
                "debit": rupees(amount) if amount > 0 else None,
                "credit": rupees(-amount) if amount < 0 else None,
                "running": rupees(line.running_paise),
            }
        )
    balance = lines[-1].running_paise if lines else 0
    return LedgerView(
        society_name=society.name,
        society_address=_address(society),
        registration_number=society.registration_number,
        flat=flat_label,
        member=member,
        as_on=day(as_on),
        lines=rows,
        balance=rupees(balance),
        resolutions=[
            {
                "name": h.name,
                "ref": h.gb_resolution_ref,
                "date": day(h.gb_resolution_date) if h.gb_resolution_date else None,
            }
            for h in heads
        ],
        interest_resolution=(
            day(society.interest_gb_resolution_date)
            if society.interest_enabled and society.interest_gb_resolution_date
            else None
        ),
    )


def ledger_xlsx(view: LedgerView, lines: list[Any]) -> bytes:
    """Same statement as the PDF, with amounts as numbers (rupees) so it can be checked."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Ledger"
    sheet.append([view.society_name])
    sheet.append([f"Flat {view.flat}", view.member or "", f"As on {view.as_on}"])
    sheet.append([])
    sheet.append(
        ["Date", "Type", "Document", "Reason", "Charged (₹)", "Paid or credited (₹)", "Balance (₹)"]
    )
    for cell in sheet[4]:
        cell.font = Font(bold=True)
    for line in lines:
        amount = line.entry.amount_paise
        sheet.append(
            [
                line.entry.entry_date,
                line.entry.entry_type,
                line.document or "",
                line.entry.reason or "",
                amount / 100 if amount > 0 else None,
                -amount / 100 if amount < 0 else None,
                line.running_paise / 100,
            ]
        )
    sheet.append([])
    sheet.append(["Resolutions"])
    for r in view.resolutions:
        sheet.append([r["name"], r["ref"] or "Not recorded", r["date"] or ""])
    if view.interest_resolution:
        sheet.append(["Interest resolution", view.interest_resolution])
    for column, width in zip("ABCDEFG", (14, 16, 20, 30, 14, 18, 14), strict=True):
        sheet.column_dimensions[column].width = width
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
