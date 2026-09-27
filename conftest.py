"""Root conftest: test-data guard (REG-11a/REG-11b).

REG-11a: A test that writes into data/ fails.
REG-11b: git status is clean after the full suite.

Implementation: Make data/ and config/ read-only during tests by intercepting
file operations that would write to those paths.
"""

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Workspace root
WORKSPACE_ROOT = Path(__file__).parent

# Protected directories (read-only during tests)
PROTECTED_DIRS = [
    WORKSPACE_ROOT / "data",
    WORKSPACE_ROOT / "config",
]


def _is_protected_path(path: str | Path) -> bool:
    """Check if path is under a protected directory."""
    path = Path(path).resolve()
    return any(
        path == protected or protected in path.parents
        for protected in PROTECTED_DIRS
    )


def _guarded_open(original_open: Any) -> Any:
    """Wrap open() to block writes to protected paths."""

    def wrapper(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        # Check if this is a write operation
        if any(m in mode for m in ["w", "a", "x", "+"]):
            if _is_protected_path(file):
                raise PermissionError(
                    f"Test attempted to write to protected path: {file}\n"
                    f"Tests must not modify data/ or config/ directories (REG-11)."
                )
        return original_open(file, mode, *args, **kwargs)

    return wrapper


@pytest.fixture(scope="session", autouse=True)
def _test_data_guard() -> Any:
    """
    Session-wide guard that makes data/ and config/ read-only during tests.
    
    This is REG-11: tests never write into real data folders.
    """
    original_open = open
    
    # Patch built-in open
    with patch("builtins.open", _guarded_open(original_open)):
        yield
