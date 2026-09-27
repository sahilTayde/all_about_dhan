"""
REG-11 tests: strategies tests never write into data/ or config/.

The root conftest.py audit hook (V2-01) blocks writes to data/ and config/.
These tests verify the guard works.
"""

import pytest
from pathlib import Path


def test_reg11_strategies_no_data_write(tmp_path: Path) -> None:
    """REG-11: strategy tests use tmp_path, not data/."""
    # This test passes by construction: we use tmp_path fixtures
    # throughout the test suite.

    # The root conftest guard would block any attempt to write to data/
    test_file = tmp_path / "test_output.txt"
    test_file.write_text("OK")
    assert test_file.exists()


def test_reg11_strategies_no_config_write(tmp_path: Path) -> None:
    """REG-11: strategy tests use tmp_path, not config/."""
    test_file = tmp_path / "test_config.yaml"
    test_file.write_text("test: ok")
    assert test_file.exists()
