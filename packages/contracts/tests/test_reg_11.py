"""Tests for REG-11: test-data guard.

REG-11a: A test that writes into data/ fails.
REG-11b: git status is clean after the full suite.
"""

import tempfile
from pathlib import Path

import pytest


def test_reg_11a_write_to_data_fails() -> None:
    """REG-11a: A test writing into data/ fails (acceptance criterion)."""
    # Attempt to write to data/ should raise PermissionError
    data_file = Path(__file__).parent.parent.parent.parent / "data" / "test_write.txt"
    
    with pytest.raises(PermissionError, match="protected path"):
        with open(data_file, "w") as f:
            f.write("test")


def test_reg_11a_write_to_config_fails() -> None:
    """REG-11a: A test writing into config/ fails."""
    config_file = Path(__file__).parent.parent.parent.parent / "config" / "test_write.yaml"
    
    with pytest.raises(PermissionError, match="protected path"):
        with open(config_file, "w") as f:
            f.write("test: value")


def test_write_to_tmp_is_allowed() -> None:
    """Writes to /tmp or temp directories are allowed."""
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as f:
        f.write("test data")
        f.flush()
        # Should succeed


def test_read_from_data_is_allowed() -> None:
    """Reading from data/ is allowed."""
    # This should not raise
    # (Even if the file doesn't exist, the guard only blocks writes)
    try:
        data_file = Path(__file__).parent.parent.parent.parent / "data" / "nonexistent.txt"
        with open(data_file, "r") as f:
            f.read()
    except FileNotFoundError:
        pass  # Expected if file doesn't exist


# REG-11b is checked by running the full suite and verifying git status is clean
# That's done in the CI pipeline, not as a pytest test
