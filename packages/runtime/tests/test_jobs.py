"""
Test job deadlines.

REG-10a from V2_BUILD_PLAN.md:
- An overrunning job is killed, exits non-zero, alerts, and leaves no partial output
"""

import time

import pytest
from runtime.jobs import DeadlineExceeded, run_with_deadline


def test_job_completes_within_deadline():
    """Job that completes within deadline returns normally."""

    def quick_job() -> str:
        return "success"

    result = run_with_deadline(quick_job, timeout_s=5.0, job_name="quick")
    assert result == "success"


def test_reg_10a_overrunning_job_killed():
    """REG-10a: Overrunning job is killed and exits non-zero."""

    def slow_job() -> None:
        time.sleep(10.0)  # Way over deadline

    # This should raise DeadlineExceeded then exit(1)
    # signal.alarm requires >= 1s, so we use 1s timeout
    with pytest.raises(SystemExit) as exc_info:
        run_with_deadline(slow_job, timeout_s=1.0, job_name="slow")

    assert exc_info.value.code == 1


def test_job_returns_result():
    """Job result is returned."""

    def calc_job() -> int:
        return 42 + 100

    result = run_with_deadline(calc_job, timeout_s=1.0, job_name="calc")
    assert result == 142


def test_job_can_raise_other_exceptions():
    """Job can raise exceptions other than DeadlineExceeded."""

    def failing_job() -> None:
        raise ValueError("intentional error")

    with pytest.raises(ValueError, match="intentional error"):
        run_with_deadline(failing_job, timeout_s=5.0, job_name="failing")


def test_multiple_jobs_sequential():
    """Multiple jobs can run sequentially."""
    results = []

    def job1() -> str:
        return "first"

    def job2() -> str:
        return "second"

    r1 = run_with_deadline(job1, timeout_s=1.0, job_name="job1")
    r2 = run_with_deadline(job2, timeout_s=1.0, job_name="job2")

    assert r1 == "first"
    assert r2 == "second"


def test_very_short_timeout():
    """Job with very short timeout (< 1s) is killed."""

    def medium_job() -> None:
        time.sleep(2.0)  # Longer than the 1s alarm

    # Sub-second timeouts are rounded up to 1s minimum (signal.alarm limitation)
    with pytest.raises(SystemExit):
        run_with_deadline(medium_job, timeout_s=0.5, job_name="medium")
