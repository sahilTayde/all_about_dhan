"""Runtime package: engine kernel, job deadlines, and frozen legacy benchmark."""

from runtime.jobs import DeadlineExceeded, JobTimeout, run_with_deadline
from runtime.kernel import Engine, RunSummary

__version__ = "0.1.0"

__all__ = [
    "DeadlineExceeded",
    "Engine",
    "JobTimeout",
    "RunSummary",
    "run_with_deadline",
]
