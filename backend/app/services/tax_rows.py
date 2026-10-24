"""Rows of the property tax template (docs/02 §5, docs/08 §4). Pure: the caller passes the
society's flats. Amounts are copied from the municipal bill; nothing is computed here."""

import re
from typing import Any

from app.services.import_rows import Issue, RowResult, Status, _text, parse_money_paise

TAX_COLUMNS: list[tuple[str, str]] = [
    ("wing", "Wing"),
    ("flat_number", "Flat number"),
    ("authority", "Municipal authority"),
    ("financial_year", "Financial year"),
    ("annual_amount", "Annual property tax (₹)"),
    ("is_exempt", "Exempt (Y/N)"),
    ("exemption_reason", "Exemption reason"),
]

YEAR = re.compile(r"^(\d{4})-(\d{2})$")


def check_tax_rows(
    rows: list[tuple[int, dict[str, object]]],
    flats: dict[tuple[str, str], str],
    blank_wing: str,
) -> list[RowResult]:
    """flats: (wing lower-cased, flat number lower-cased) → flat id."""
    seen: dict[tuple[str, str, str], int] = {}
    results: list[RowResult] = []
    for row_number, raw in rows:
        issues: list[Issue] = []
        data: dict[str, Any] = {}

        wing = (_text(raw.get("wing")) or "").lower() or blank_wing
        number = _text(raw.get("flat_number"))
        data["flat_label"] = f"{_text(raw.get('wing')) or ''}-{number or ''}".strip("-")
        data["flat_id"] = None
        if not number:
            issues.append(Issue("required", {"field": "flat_number"}))
        else:
            data["flat_id"] = flats.get((wing, number.lower()))
            if data["flat_id"] is None:
                issues.append(Issue("flatNotFound"))

        data["authority"] = _text(raw.get("authority"))
        if not data["authority"]:
            issues.append(Issue("required", {"field": "authority"}))

        year = _text(raw.get("financial_year")) or ""
        match = YEAR.match(year)
        if not match or (int(match[1]) + 1) % 100 != int(match[2]):
            issues.append(Issue("badYear", {"field": "financial_year"}))
        data["financial_year"] = year

        exempt = (_text(raw.get("is_exempt")) or "n").lower()
        data["is_exempt"] = exempt in ("y", "yes")
        if exempt not in ("y", "yes", "n", "no"):
            issues.append(Issue("badChoice", {"field": "is_exempt", "allowed": "Y, N"}))
        data["exemption_reason"] = _text(raw.get("exemption_reason"))

        data["annual_amount_paise"] = 0
        if _text(raw.get("annual_amount")):
            paise, key = parse_money_paise(raw["annual_amount"])
            if key:
                issues.append(Issue(key, {"field": "annual_amount"}))
            elif paise is not None and paise < 0:
                issues.append(Issue("notPositive", {"field": "annual_amount"}))
            else:
                data["annual_amount_paise"] = paise
        elif not data["is_exempt"]:
            issues.append(Issue("required", {"field": "annual_amount"}))

        if data["is_exempt"]:
            if data["annual_amount_paise"]:
                issues.append(Issue("exemptWithAmount"))
            if not data["exemption_reason"]:
                issues.append(Issue("exemptionReasonMissing"))

        key = (wing, (number or "").lower(), year)
        if number and key in seen:
            issues.insert(0, Issue("duplicateInFile", {"otherRow": seen[key]}))
        else:
            seen.setdefault(key, row_number)

        # Every problem here would put a wrong amount on a bill, so all are errors.
        status: Status = "error" if issues else "ok"
        results.append(RowResult(row_number, status, issues, data))
    return results
