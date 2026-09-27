"""TRACE-01: every C# / A# in the comments log and every REG-nn has a §4.1 row."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gate.merge_gate import evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_trace_01_every_comment_and_reg_has_row() -> None:
    result = evaluate(only="TRACE-01", root=ROOT)
    check = next(c for c in result.checks if c.name == "TRACE-01")
    assert check.status == "PASS", check.detail
