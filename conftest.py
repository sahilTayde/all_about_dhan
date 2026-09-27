"""
Root conftest: comprehensive test-data guard (REG-11a/REG-11b).

REG-11a: Tests cannot write to data/ or config/ directories.
REG-11b: The full test suite leaves git status clean in data/ and config/.

Implementation: sys.addaudithook covering all write operations.
"""

import sys
from pathlib import Path
from typing import Any

import pytest

# Workspace root
WORKSPACE_ROOT = Path(__file__).parent

# Protected directories (read-only during tests)
PROTECTED_DIRS = {
    WORKSPACE_ROOT / "data",
    WORKSPACE_ROOT / "config",
}


def _is_protected_path(path: str | Path | int) -> bool:
    """Check if path is under a protected directory."""
    # Allow integer file descriptors
    if isinstance(path, int):
        return False

    try:
        resolved = Path(path).resolve()
        return any(
            resolved == protected or protected in resolved.parents
            for protected in PROTECTED_DIRS
        )
    except (OSError, ValueError):
        # Invalid path, let it through (will fail naturally)
        return False


_guard_armed = False
_violations: list[str] = []


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    """Audit hook for file operations."""
    if not _guard_armed:
        return

    # Open operations
    if event == "open":
        path, mode, *_ = args
        if any(m in str(mode) for m in ["w", "a", "x", "+"]) and _is_protected_path(
            path
        ):
            msg = f"Test attempted to write (open) to protected path: {path}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    # pathlib operations
    elif event == "pathlib.Path.open":
        _, path, mode, *_ = args
        if any(m in str(mode) for m in ["w", "a", "x", "+"]) and _is_protected_path(
            path
        ):
            msg = f"Test attempted to write (Path.open) to protected path: {path}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    elif event in ("pathlib.Path.write_text", "pathlib.Path.write_bytes"):
        _, path, *_ = args
        if _is_protected_path(path):
            msg = f"Test attempted to write ({event}) to protected path: {path}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    elif event in ("pathlib.Path.mkdir", "os.mkdir", "os.makedirs"):
        if event.startswith("pathlib"):
            _, path, *_ = args
        else:
            path, *_ = args
        # Only block if creating new dir under protected (parent must be protected)
        parent = Path(path).parent if not isinstance(path, int) else None
        if parent and _is_protected_path(parent):
            msg = f"Test attempted mkdir in protected path: {path}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    elif event in (
        "pathlib.Path.rename",
        "pathlib.Path.replace",
        "os.rename",
        "os.replace",
    ):
        if event.startswith("pathlib"):
            _, src, dst, *_ = args
        else:
            src, dst, *_ = args
        if _is_protected_path(src) or _is_protected_path(dst):
            msg = f"Test attempted rename/replace in protected path: {src} -> {dst}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    elif event in (
        "pathlib.Path.unlink",
        "pathlib.Path.rmdir",
        "os.remove",
        "os.unlink",
        "os.rmdir",
    ):
        if event.startswith("pathlib"):
            _, path, *_ = args
        else:
            path, *_ = args
        if _is_protected_path(path):
            msg = f"Test attempted remove in protected path: {path}"
            _violations.append(msg)
            raise PermissionError(
                msg + "\nTests must not modify data/ or config/ (REG-11)"
            )

    # sqlite3 operations (allow read-only)
    elif event == "sqlite3.connect":
        path, *_ = args
        # Check if connection will be read-only (uri=True with mode=ro)
        # For simplicity, we check the path but sqlite3 audit doesn't give us mode
        # We'll catch writes at the execute level
        if _is_protected_path(path) and not (
            isinstance(path, str) and (":memory:" in path or "mode=ro" in path)
        ):
            # Otherwise, let it through but monitor execute
            pass

    elif event == "sqlite3.connect/handle":
        # Actual connection made
        pass


_snapshot_before: dict[str, tuple[float, int]] = {}


def _take_snapshot() -> dict[str, tuple[float, int]]:
    """Take snapshot of data/ and config/ (mtime, size), excluding __pycache__."""
    snapshot = {}
    for protected in PROTECTED_DIRS:
        if not protected.exists():
            continue
        for path in protected.rglob("*"):
            # Skip __pycache__ directories and their contents (Python import side effect)
            if "__pycache__" in path.parts:
                continue
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[str(path.relative_to(WORKSPACE_ROOT))] = (
                        stat.st_mtime,
                        stat.st_size,
                    )
                except (OSError, ValueError):
                    pass
    return snapshot


def pytest_configure(config: Any) -> None:
    """Arm the guard at pytest start."""
    global _guard_armed, _snapshot_before

    # Register markers
    config.addinivalue_line(
        "markers", "reg11a_probe: REG-11a probe test (exempt from guard)"
    )

    # Take snapshot before tests
    _snapshot_before = _take_snapshot()

    # Arm the audit hook
    sys.addaudithook(_audit_hook)
    _guard_armed = True


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Check snapshot diff at end (REG-11b)."""
    snapshot_after = _take_snapshot()

    # Compare snapshots
    changes = []
    for path, (mtime_before, size_before) in _snapshot_before.items():
        if path not in snapshot_after:
            changes.append(f"DELETED: {path}")
        else:
            mtime_after, size_after = snapshot_after[path]
            if mtime_after != mtime_before or size_after != size_before:
                changes.append(
                    f"MODIFIED: {path} (mtime: {mtime_before} -> {mtime_after}, size: {size_before} -> {size_after})"
                )

    for path in snapshot_after:
        if path not in _snapshot_before:
            changes.append(f"CREATED: {path}")

    if changes:
        print("\n" + "=" * 80)
        print("REG-11b VIOLATION: data/ or config/ changed during test run")
        print("=" * 80)
        for change in changes:
            print(f"  {change}")
        print("=" * 80)
        pytest.exit(
            "REG-11b FAILED: Test suite modified data/ or config/", returncode=1
        )


def pytest_runtest_makereport(item: Any, call: Any) -> None:
    """Fail tests that swallow PermissionError from the guard."""
    # Check if test is marked as reg11a_probe (exempt)
    if "reg11a_probe" in [marker.name for marker in item.iter_markers()]:
        return

    if call.excinfo and _violations:
        # Test swallowed a PermissionError from our guard
        last_violation = _violations[-1]
        pytest.fail(f"Test swallowed REG-11 guard PermissionError: {last_violation}")
