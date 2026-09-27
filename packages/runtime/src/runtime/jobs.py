"""Job deadlines: ``run_with_deadline`` for every one-shot job (REG-10a).

Library raises ``DeadlineExceeded`` (alias ``JobTimeout`` for V2-15). Callers
(``python -m runtime``, deploy scripts) exit non-zero. Partial output is the
caller's job: this wrapper does not write files.
"""

from __future__ import annotations

import logging
import signal
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("runtime.jobs")

T = TypeVar("T")


class DeadlineExceeded(Exception):
    """Job exceeded its wall-clock deadline."""

    def __init__(self, job: str, timeout_s: float) -> None:
        super().__init__(f"{job} exceeded deadline of {timeout_s}s")
        self.job = job
        self.timeout_s = timeout_s


JobTimeout = DeadlineExceeded


def run_with_deadline(
    fn: Callable[[], T],
    timeout_s: float,
    job_name: str | None = None,
    *,
    job: str = "job",
) -> T:
    """Run ``fn`` with a wall-clock timeout.

    Uses ``signal.alarm`` (POSIX, 1s minimum). On timeout raises
    ``DeadlineExceeded`` after a CRITICAL log. Does not ``sys.exit`` so V2-15
    can catch ``JobTimeout`` and return 1 from ``python -m runtime``.
    """
    name = job if job_name is None else job_name

    def _timeout_handler(signum: int, frame: object) -> None:
        log.critical("Job %s exceeded deadline of %.1fs", name, timeout_s)
        raise DeadlineExceeded(name, timeout_s)

    alarm_seconds = max(1, int(timeout_s + 0.999))
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(alarm_seconds)
    try:
        log.info("Starting job %s with deadline %.1fs (alarm at %ds)", name, timeout_s, alarm_seconds)
        result = fn()
        log.info("Job %s completed in time", name)
        return result
    except DeadlineExceeded:
        log.critical("ALERT: Job %s killed at deadline", name)
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
