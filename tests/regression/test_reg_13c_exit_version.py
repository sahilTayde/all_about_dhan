"""REG-13c: a PR fixture that edits exit params without a version bump fails."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from gate.merge_gate import exit_version_ok  # noqa: E402


def test_reg_13c_exit_params_without_version_bump_fails() -> None:
    before = {
        "version": "2.0.0",
        "exit_plan": {"catastrophic": {"max_loss": 30000}, "flat_by_ist": "15:15"},
    }
    edited = {
        "version": "2.0.0",
        "exit_plan": {"catastrophic": {"max_loss": 20000}, "flat_by_ist": "15:15"},
    }
    assert exit_version_ok(before, edited) is False
    assert exit_version_ok(before, {**edited, "version": "2.0.1"}) is True
