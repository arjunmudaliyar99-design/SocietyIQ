"""Bill PDFs (docs/04 §8): Jinja2 HTML → WeasyPrint, Noto fonts for Indic scripts, UPI QR.

Building the HTML needs nothing native and is tested everywhere. Turning it into a PDF needs
WeasyPrint's system libraries (Pango); where they are missing, `PdfUnavailable` is raised and
the API answers 503 instead of failing a money operation.
"""

import base64
import io
import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

HERE = Path(__file__).parent
LABELS_FILE = HERE.parent / "i18n" / "bill_labels.json"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class PdfUnavailable(RuntimeError):
    """WeasyPrint or its system libraries are not installed on this machine."""


def rupees(paise: int) -> str:
    """Indian grouping, paise only when non-zero: 13100000 → ₹1,31,000 (docs/03 §6)."""
    sign = "-" if paise < 0 else ""
    whole, rest = divmod(abs(paise), 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"{sign}₹{digits}" + (f".{rest:02d}" if rest else "")


def day(value: date) -> str:
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def upi_link(upi_id: str, payee: str, amount_paise: int, note: str) -> str:
    """docs/04 §8: amount in rupees with two decimals."""
    whole, rest = divmod(amount_paise, 100)
    return (
        f"upi://pay?pa={quote(upi_id, safe='@.')}&pn={quote(payee)}"
        f"&am={whole}.{rest:02d}&cu=INR&tn={quote(note)}"
    )


def qr_data_uri(text: str) -> str:
    image = qrcode.make(text, box_size=6, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


@lru_cache
def _labels() -> dict[str, dict[str, str]]:
    data = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    data.pop("_status", None)
    return data


def label_function(language: str) -> Any:  # noqa: ANN401
    """English always; the society's language under it when it is not English."""
    labels = _labels()
    english = labels["en"]
    local = labels.get(language, {}) if language != "en" else {}

    def label(key: str) -> Markup:
        text = escape(english[key])
        if key in local:
            return Markup(f'{text}<span class="local">{escape(local[key])}</span>')
        return Markup(text)

    return label


@dataclass
class BillView:
    society_name: str
    society_address: str | None
    registration_number: str | None
    bill_number: str
    flat: str
    member: str | None
    period: str
    bill_date: str
    due_date: str
    lines: list[dict[str, str]]
    charges: str
    arrears: str | None
    advance: str | None
    interest: str | None
    total_due: str
    qr: str | None
    upi_id: str | None
    bank: str | None
    cancelled: bool
    replaces: str | None


def bill_view(
    *,
    society: Any,  # noqa: ANN401
    bill: Any,  # noqa: ANN401
    lines: list[Any],
    flat_label: str,
    replaces_number: str | None = None,
) -> BillView:
    address = ", ".join(p for p in (society.address_line, society.city, society.pincode) if p)
    payable = bill.total_due_paise if bill.status != "cancelled" else 0
    qr = None
    if society.upi_id and payable > 0:
        qr = qr_data_uri(
            upi_link(
                society.upi_id, society.upi_payee_name or society.name, payable, bill.bill_number
            )
        )
    bank = None
    if society.bank_name:
        bank = society.bank_name + (
            f" ••••{society.bank_account_last4}" if society.bank_account_last4 else ""
        )
    return BillView(
        society_name=society.name,
        society_address=address or None,
        registration_number=society.registration_number,
        bill_number=bill.bill_number,
        flat=flat_label,
        member=bill.member_name,
        period=f"{day(bill.period_start)} – {day(bill.period_end)}",
        bill_date=day(bill.bill_date),
        due_date=day(bill.due_date),
        # Charge and rounding lines add up to "charges"; interest has its own row below.
        lines=[
            {
                "description": line.description,
                "label": line.line_type == "rounding",
                "amount": rupees(line.amount_paise),
            }
            for line in lines
            if line.line_type != "interest"
        ],
        charges=rupees(bill.charges_paise),
        arrears=rupees(bill.arrears_paise) if bill.arrears_paise else None,
        advance=rupees(bill.advance_paise) if bill.advance_paise else None,
        interest=rupees(bill.interest_paise) if bill.interest_paise else None,
        total_due=rupees(bill.total_due_paise),
        qr=qr,
        upi_id=society.upi_id,
        bank=bank,
        cancelled=bill.status == "cancelled",
        replaces=replaces_number,
    )


@lru_cache
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html"]),
    )


def render_template(name: str, language: str, company: str = "", **context: object) -> str:
    template = _environment().get_template(name)
    return template.render(
        language=language, L=label_function(language), company=company, **context
    )


def render_html(bills: list[BillView], language: str, company: str = "") -> str:
    return render_template("bills.html", language, company, bills=bills)


def render_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML  # noqa: PLC0415 — needs native libraries; import only here
    except (ImportError, OSError) as exc:
        raise PdfUnavailable(str(exc)) from exc
    return HTML(string=html, base_url=str(HERE)).write_pdf()
