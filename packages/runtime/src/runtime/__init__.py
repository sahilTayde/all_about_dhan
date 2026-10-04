"""V2 runtime: engine kernel, job deadlines, service entry points, frozen legacy benchmark.

Recovery (brokers/ledger) is lazy: ``from runtime.kernel import Engine`` must
work in the Mac .venv-v2 shadow venv, which does not install brokers.
"""

from typing import Any

from runtime.jobs import JOBS, DeadlineExceeded, JobTimeout, run_with_deadline
from runtime.kernel import Engine, RunSummary
from runtime.services import (
    BREAKER_EXIT,
    SERVICES,
    BreakerView,
    RestartBreaker,
    deploy,
    reset_breaker,
    run_guarded,
    run_llm_advisor,
    write_engine_status,
)

__version__ = "2.19.0"

_RECOVERY_EXPORTS = frozenset({"RecoveryResult", "rebuild_paper_broker", "recover"})


def __getattr__(name: str) -> Any:
    """Load recovery only when asked. Shadow follow never needs it."""
    if name in _RECOVERY_EXPORTS:
        from runtime.recovery import RecoveryResult, rebuild_paper_broker, recover

        exports: dict[str, Any] = {
            "RecoveryResult": RecoveryResult,
            "rebuild_paper_broker": rebuild_paper_broker,
            "recover": recover,
        }
        globals().update(exports)
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BREAKER_EXIT",
    "JOBS",
    "SERVICES",
    "BreakerView",
    "DeadlineExceeded",
    "Engine",
    "JobTimeout",
    "RecoveryResult",
    "RestartBreaker",
    "RunSummary",
    "deploy",
    "rebuild_paper_broker",
    "recover",
    "reset_breaker",
    "run_guarded",
    "run_llm_advisor",
    "run_with_deadline",
    "write_engine_status",
]
