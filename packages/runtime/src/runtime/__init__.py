"""V2 runtime: engine kernel, job deadlines, service entry points, frozen legacy benchmark."""

from runtime.jobs import JOBS, DeadlineExceeded, JobTimeout, run_with_deadline
from runtime.kernel import Engine, RunSummary
from runtime.services import (
    BREAKER_EXIT,
    SERVICES,
    BreakerView,
    LlmAdvisorService,
    RestartBreaker,
    deploy,
    reset_breaker,
    run_guarded,
    run_llm_advisor,
    write_engine_status,
)

__version__ = "2.15.0"

__all__ = [
    "BREAKER_EXIT",
    "JOBS",
    "SERVICES",
    "BreakerView",
    "DeadlineExceeded",
    "Engine",
    "JobTimeout",
    "LlmAdvisorService",
    "RestartBreaker",
    "RunSummary",
    "deploy",
    "reset_breaker",
    "run_guarded",
    "run_llm_advisor",
    "run_with_deadline",
    "write_engine_status",
]
