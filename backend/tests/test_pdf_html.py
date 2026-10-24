"""Bill HTML (docs/04 §8): labels in English plus the society's language, Indian number
format, UPI link and QR. Runs without WeasyPrint; the PDF itself is tested in test_billing."""

from datetime import date
from types import SimpleNamespace

from app.pdf.bills import bill_view, render_html, rupees, upi_link


def _society(**kw: object) -> SimpleNamespace:
    base = {
        "name": "Shanti Sadan CHS",
        "address_line": "Plot 7",
        "city": "Mumbai",
        "pincode": "400071",
        "registration_number": None,
        "upi_id": "shantisadan@examplebank",
        "upi_payee_name": "Shanti Sadan CHS",
        "bank_name": "Example Bank",
        "bank_account_last4": "1234",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def _bill(**kw: object) -> SimpleNamespace:
    base = {
        "bill_number": "B/2026-27/000045",
        "member_name": "Member B-207",
        "period_start": date(2026, 11, 1),
        "period_end": date(2026, 11, 30),
        "bill_date": date(2026, 11, 1),
        "due_date": date(2026, 11, 16),
        "charges_paise": 420000,
        "arrears_paise": 2520000,
        "advance_paise": 0,
        "interest_paise": 0,
        "total_due_paise": 2940000,
        "status": "issued",
    }
    base.update(kw)
    return SimpleNamespace(**base)


LINES = [
    SimpleNamespace(description="Service charges", line_type="charge", amount_paise=340000),
    SimpleNamespace(
        description="Repair and maintenance fund", line_type="charge", amount_paise=60000
    ),
    SimpleNamespace(description="Sinking fund", line_type="charge", amount_paise=20000),
]


def test_rupees_indian_grouping() -> None:
    assert rupees(13100000) == "₹1,31,000"
    assert rupees(2940000) == "₹29,400"
    assert rupees(105) == "₹1.05"
    assert rupees(1234567890) == "₹1,23,45,678.90"
    assert rupees(-50000) == "-₹500"


def test_upi_link_amount_has_two_decimals() -> None:
    link = upi_link("shantisadan@examplebank", "Shanti Sadan CHS", 2940000, "B/2026-27/000045")
    assert link == (
        "upi://pay?pa=shantisadan@examplebank&pn=Shanti%20Sadan%20CHS&am=29400.00&cu=INR"
        "&tn=B/2026-27/000045"
    )


def test_marathi_bill_has_both_languages_qr_and_totals() -> None:
    view = bill_view(society=_society(), bill=_bill(), lines=LINES, flat_label="B-207")
    html = render_html([view], "mr")
    assert "Maintenance bill" in html and "देखभाल बिल" in html
    assert "Total to pay" in html and "भरायची एकूण रक्कम" in html
    assert "₹29,400" in html and "₹25,200" in html and "₹4,200" in html
    assert "data:image/png;base64," in html
    assert "1 Nov 2026 – 30 Nov 2026" in html
    assert "••••1234" in html


def test_english_bill_has_no_second_language_and_cancelled_has_no_qr() -> None:
    view = bill_view(
        society=_society(), bill=_bill(status="cancelled"), lines=LINES, flat_label="B-207"
    )
    html = render_html([view], "en")
    assert 'class="local"' not in html
    assert "CANCELLED" in html
    assert "data:image/png" not in html


def test_no_upi_id_means_no_qr() -> None:
    view = bill_view(society=_society(upi_id=None), bill=_bill(), lines=LINES, flat_label="B-207")
    assert view.qr is None
