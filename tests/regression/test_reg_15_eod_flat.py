"""REG-15d: no position remains open after flat_by_ist (shared with the §6.2 invariant)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gate.merge_gate import check_invariants, clean_book  # noqa: E402


def test_reg_15d_no_position_open_after_flat_by_ist() -> None:
    book = clean_book()
    assert "flat_after_flat_by_ist" not in check_invariants(book)
    book.open_after_flat = True
    assert "flat_after_flat_by_ist" in check_invariants(book)
