"""The restore-test comparison script (docs/09 §6c). No database needed."""

import importlib.util
from pathlib import Path

from openpyxl import Workbook

SCRIPT = Path(__file__).parent.parent / "scripts" / "compare_exports.py"
spec = importlib.util.spec_from_file_location("compare_exports", SCRIPT)
assert spec and spec.loader
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def _book(path: Path, flats: list[tuple[str, int]]) -> str:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "flats"
    sheet.append(["flat_number", "amount (₹)"])
    for row in flats:
        sheet.append(list(row))
    book.save(path)
    return str(path)


def test_same_exports_pass(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    a = _book(tmp_path / "a.xlsx", [("A-101", 0), ("B-207", 29400)])
    b = _book(tmp_path / "b.xlsx", [("A-101", 0), ("B-207", 29400)])
    assert compare.main(a, b) == 0
    assert "OK" in capsys.readouterr().out


def test_missing_or_changed_rows_fail_without_printing_data(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    live = _book(tmp_path / "live.xlsx", [("A-101", 0), ("B-207", 29400)])
    fewer = _book(tmp_path / "fewer.xlsx", [("A-101", 0)])
    changed = _book(tmp_path / "changed.xlsx", [("A-101", 0), ("B-207", 4200)])
    assert compare.main(live, fewer) == 1
    assert compare.main(live, changed) == 1
    out = capsys.readouterr().out
    assert "2 rows live, 1 restored" in out
    assert "different contents" in out
    assert "B-207" not in out
