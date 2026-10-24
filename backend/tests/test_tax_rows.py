"""Property tax template rows (docs/08 §4: copy the municipal bill; exempt flats show ₹0)."""

from app.services.tax_rows import check_tax_rows

FLATS = {("a", "101"): "f1", ("a", "102"): "f2"}


def _row(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "wing": "A",
        "flat_number": "101",
        "authority": "MCGM",
        "financial_year": "2026-27",
        "annual_amount": "12,000",
        "is_exempt": "N",
    }
    base.update(kw)
    return base


def test_good_rows() -> None:
    [ok, exempt] = check_tax_rows(
        [
            (2, _row()),
            (
                3,
                _row(
                    flat_number="102",
                    annual_amount=None,
                    is_exempt="Y",
                    exemption_reason="MCGM ≤500 sq ft",
                ),
            ),
        ],
        FLATS,
        "",
    )
    assert (ok.status, ok.data["flat_id"], ok.data["annual_amount_paise"]) == ("ok", "f1", 1200000)
    assert (exempt.status, exempt.data["annual_amount_paise"], exempt.data["is_exempt"]) == (
        "ok",
        0,
        True,
    )


def test_each_problem() -> None:
    rows = check_tax_rows(
        [
            (2, _row(flat_number="999")),
            (3, _row(financial_year="2026-28")),
            (4, _row(is_exempt="Y")),
            (5, _row(annual_amount=None, financial_year="2025-26")),
            (6, _row(annual_amount="-5", financial_year="2024-25")),
            (7, _row(authority=None, is_exempt="maybe", financial_year="2023-24")),
            (8, _row()),  # same flat and year as row 4
            (9, _row(flat_number=None)),
        ],
        FLATS,
        "",
    )
    keys = [[i.key for i in r.issues] for r in rows]
    assert keys == [
        ["flatNotFound"],
        ["badYear"],
        ["exemptWithAmount", "exemptionReasonMissing"],
        ["required"],
        ["notPositive"],
        ["required", "badChoice"],
        ["duplicateInFile"],
        ["required"],
    ]
    assert all(r.status == "error" for r in rows)


def test_blank_wing_uses_the_only_wing() -> None:
    [row] = check_tax_rows([(2, _row(wing=None))], FLATS, "a")
    assert row.data["flat_id"] == "f1"
