"""Job deadlines (REG-10a)."""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from runtime.jobs import DeadlineExceeded, JobTimeout, run_with_deadline


def test_job_completes_within_deadline() -> None:
    """Job that completes within deadline returns normally."""

    def quick_job() -> str:
        return "success"

    assert run_with_deadline(quick_job, timeout_s=5.0, job_name="quick") == "success"


def test_reg_10a_overrunning_job_killed() -> None:
    """REG-10a: overrunning job is killed and raises DeadlineExceeded."""

    def slow_job() -> None:
        time.sleep(10.0)

    with pytest.raises(DeadlineExceeded, match="slow exceeded") as exc_info:
        run_with_deadline(slow_job, timeout_s=1.0, job="slow")
    assert exc_info.value.job == "slow"
    assert exc_info.value.timeout_s == 1.0


def test_reg_10a_cli_exits_nonzero() -> None:
    """REG-10a: a caller that catches DeadlineExceeded exits non-zero."""
    code = (
        "import sys, time\n"
        "from runtime.jobs import DeadlineExceeded, run_with_deadline\n"
        "try:\n"
        "    run_with_deadline(lambda: time.sleep(10), 1.0, job='slow')\n"
        "except DeadlineExceeded:\n"
        "    sys.exit(1)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False, timeout=8)
    assert result.returncode == 1


def test_job_timeout_alias() -> None:
    """V2-15 name JobTimeout is the same class."""
    assert JobTimeout is DeadlineExceeded


def test_job_returns_result() -> None:
    """Job result is returned."""

    def calc_job() -> int:
        return 42 + 100

    assert run_with_deadline(calc_job, timeout_s=1.0, job_name="calc") == 142


def test_job_can_raise_other_exceptions() -> None:
    """Job can raise exceptions other than DeadlineExceeded."""

    def failing_job() -> None:
        raise ValueError("intentional error")

    with pytest.raises(ValueError, match="intentional error"):
        run_with_deadline(failing_job, timeout_s=5.0, job_name="failing")


def test_multiple_jobs_sequential() -> None:
    """Multiple jobs can run sequentially."""
    assert run_with_deadline(lambda: "first", timeout_s=1.0, job_name="job1") == "first"
    assert run_with_deadline(lambda: "second", timeout_s=1.0, job_name="job2") == "second"


def test_very_short_timeout() -> None:
    """Sub-second timeout is rounded up to 1s (signal.alarm limitation)."""

    def medium_job() -> None:
        time.sleep(2.0)

    with pytest.raises(DeadlineExceeded):
        run_with_deadline(medium_job, timeout_s=0.5, job_name="medium")
