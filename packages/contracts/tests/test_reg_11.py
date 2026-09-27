"""REG-11 test data guard: prevent test writes to data/ and config/."""

from __future__ import annotations

from pathlib import Path

import pytest

# Repo root for absolute paths in probe tests
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.reg11a_probe
def test_reg11a_write_to_data_is_blocked(tmp_path: Path) -> None:
    """REG-11a probe: writes into data/ must be blocked by audit hook."""
    with pytest.raises(PermissionError, match="REG-11"):
        (REPO_ROOT / "data" / "test.txt").write_text("forbidden")


@pytest.mark.reg11a_probe
def test_reg11a_write_to_config_is_blocked(tmp_path: Path) -> None:
    """REG-11a probe: writes into config/ must be blocked by audit hook."""
    with pytest.raises(PermissionError, match="REG-11"):
        (REPO_ROOT / "config" / "test.yaml").write_text("forbidden")


@pytest.mark.reg11a_probe
def test_reg11a_tmp_path_is_allowed(tmp_path: Path) -> None:
    """REG-11a probe: tmp_path must still work."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("allowed")
    assert test_file.read_text() == "allowed"
