"""
Job deadlines: run_with_deadline wrapper for every one-shot job.

Spec: V2_BUILD_PLAN.md V2-04, REG-10a
"""

from __future__ import annotations

import logging
import signal
import sys
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("runtime.jobs")

T = TypeVar("T")


class DeadlineExceeded(Exception):
    """Job exceeded its deadline."""



def run_with_deadline(fn: Callable[[], T], timeout_s: float, job_name: str = "job") -> T:
    """
    Run fn with a wall-clock timeout.

    On timeout:
    - Raises DeadlineExceeded
    - Exits non-zero (1)
    - Logs alert-level message
    - Leaves no partial output (caller must handle cleanup)

    Args:
        fn: Function to run
        timeout_s: Timeout in seconds (minimum 1s; rounded up)
        job_name: Job name for logging

    Returns:
        Result of fn()

    Raises:
        DeadlineExceeded: if fn() takes longer than timeout_s
    """

    def _timeout_handler(signum: int, frame: object) -> None:
        log.critical("Job %s exceeded deadline of %.1fs", job_name, timeout_s)
        raise DeadlineExceeded(f"{job_name} exceeded deadline of {timeout_s}s")

    # signal.alarm requires integer seconds; round up for sub-second timeouts
    alarm_seconds = max(1, int(timeout_s + 0.999))

    # Set alarm
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(alarm_seconds)

    try:
        log.info("Starting job %s with deadline %.1fs (alarm at %ds)", job_name, timeout_s, alarm_seconds)
        result = fn()
        log.info("Job %s completed in time", job_name)
        return result
    except DeadlineExceeded:
        # Alert and exit non-zero
        log.critical("ALERT: Job %s killed at deadline", job_name)
        sys.exit(1)
    finally:
        # Cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
