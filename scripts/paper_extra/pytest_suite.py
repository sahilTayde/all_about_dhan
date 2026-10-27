"""2026-10-21 v4: run the whole paper_extra suite under pytest.
  python -m pytest -q scripts/paper_extra/pytest_suite.py scripts/paper_extra/test_runner_pshadow.py scripts/paper_extra/test_runner_q01.py
The self-running test_*.py scripts run each in its own subprocess (they exit non-zero on failure and must not be imported by pytest's
collector). test_exit_fill.py is a CLI checker that needs a day-file argument: xfail without one (failed the same way before the patch)."""
import os, subprocess, sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
PYTEST_FILES = {"test_runner_pshadow.py", "test_runner_q01.py"}
SCRIPTS = sorted(p.name for p in HERE.glob("test_*.py") if p.name not in PYTEST_FILES)


@pytest.mark.parametrize("name", SCRIPTS)
def test_script(name):
    if name == "test_exit_fill.py":
        pytest.xfail("CLI checker: needs a day-file argument (IndexError without one, same before the patch)")
    env = dict(os.environ, PX_TEST="1", PYTHONPATH=str(HERE.parents[1] / "packages" / "desk-ml" / "src"),
               DESKML_SRC=str(HERE.parents[1] / "packages" / "desk-ml" / "src"))
    env.pop("PX_STATE_DIR", None)
    p = subprocess.run([sys.executable, str(HERE / name)], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, (p.stdout[-2000:], p.stderr[-2000:])
