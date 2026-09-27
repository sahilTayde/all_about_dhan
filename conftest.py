"""Root conftest: repo-wide test-data guard (REG-11a / REG-11b).

REG-11a: any write into data/ or config/ from test code fails the test.
         Enforced with a CPython audit hook, which sees every open() path
         (builtins.open, io.open, os.open, pathlib, shutil, pandas) plus
         sqlite3.connect, rename/replace, mkdir, remove, and is active from
         pytest_configure, so import/collection-time writes are caught too.
REG-11b: the session fails if data/ or config/ differ from the start of the run
         (catches C-extension and subprocess writes the hook cannot see, e.g.
         pyarrow's native writer or `subprocess.run(... > data/x)`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent
PROTECTED = tuple(str(ROOT / d) for d in ("data", "config"))
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_state: dict[str, Any] = {"armed": False, "violations": [], "snapshot": {}}


def _protected(path: Any) -> str | None:
    if isinstance(path, int) or path is None:
        return None
    try:
        p = os.path.realpath(os.fsdecode(path))
    except (TypeError, ValueError):
        return None
    return p if any(p == d or p.startswith(d + os.sep) for d in PROTECTED) else None


def _violation(what: str, path: str) -> None:
    msg = f"REG-11: test wrote into a protected path via {what}: {path}"
    _state["violations"].append(msg)
    raise PermissionError(msg)


def _at(path: Any, dir_fd: Any) -> Any:
    """Resolve a dir_fd-relative path (shutil.rmtree uses os.rmdir/unlink(name, dir_fd=fd))."""
    if isinstance(dir_fd, int) and not os.path.isabs(os.fsdecode(path)):
        try:
            return os.path.join(os.readlink(f"/proc/self/fd/{dir_fd}"), os.fsdecode(path))
        except OSError:
            return None
    return path


def _hook(event: str, args: tuple[Any, ...]) -> None:
    if not _state["armed"]:
        return
    if event in ("os.mkdir", "os.rmdir", "os.remove") and args:
        args = (_at(args[0], args[-1]),) + tuple(args[1:])
    if event == "open":
        path, mode, flags = args
        writing = (mode is not None and any(c in mode for c in "wax+")) or (
            mode is None and isinstance(flags, int) and flags & _WRITE_FLAGS
        )
        if writing and (p := _protected(path)):
            _violation("open", p)
    elif event == "sqlite3.connect":
        db = args[0]
        if (p := _protected(db)) and "mode=ro" not in str(db):
            _violation("sqlite3.connect", p)
    elif event in ("os.rename", "shutil.move", "shutil.copyfile", "shutil.copytree"):
        if p := _protected(args[1]):
            _violation(event, p)
    elif event == "os.mkdir":  # mkdir(exist_ok=True) on an existing dir changes nothing
        if (p := _protected(args[0])) and not os.path.exists(p):
            _violation(event, p)
    elif event == "os.rmdir":  # os.removedirs walks up; a non-empty dir cannot be removed anyway
        if (p := _protected(args[0])) and os.path.isdir(p) and not os.listdir(p):
            _violation(event, p)
    elif event in ("os.remove", "os.truncate", "os.chmod", "shutil.rmtree", "os.symlink", "os.link"):
        target = args[1] if event in ("os.symlink", "os.link") else args[0]
        if p := _protected(target):
            _violation(event, p)


def _snapshot() -> dict[str, tuple[int, int]]:
    snap: dict[str, tuple[int, int]] = {}
    for base in PROTECTED:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            snap[dirpath] = (0, 0)
            for name in filenames:
                full = os.path.join(dirpath, name)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                snap[full] = (st.st_size, st.st_mtime_ns)
    return snap


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "reg11a_probe: REG-11a probe test (exempt from guard)")
    if not getattr(sys, "_reg11_hook", False):  # audit hooks cannot be removed; install once
        sys.addaudithook(_hook)
        sys._reg11_hook = True  # type: ignore[attr-defined]
    _state["snapshot"] = _snapshot()
    _state["armed"] = True


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Any:
    # Skip guard check for probe tests
    is_probe = any(mark.name == "reg11a_probe" for mark in item.iter_markers())
    before = len(_state["violations"])
    outcome = yield
    if is_probe:
        return  # Probe tests are allowed to trigger the guard
    new = _state["violations"][before:]
    if new and outcome.excinfo is None:  # the code under test swallowed the PermissionError
        pytest.fail("\n".join(new), pytrace=False)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    _state["armed"] = False
    before, after = _state["snapshot"], _snapshot()
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    if changed:
        sys.stderr.write("\nREG-11b: data/ or config/ changed during the test run:\n  " + "\n  ".join(changed) + "\n")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
