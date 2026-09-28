"""V2-20a forward-test harness. Generic; off by default. Paper only."""

from .bars import FwdBars, bar_state, deflated_sharpe, one_sided_t
from .eval import ForwardRefused, evaluate_session
from .report import ForwardReport, format_report
from .spec import SpecError, SpecRefused, compute_lock_digest, load_lock, load_spec, verify_lock

__all__ = [
    "ForwardRefused",
    "ForwardReport",
    "FwdBars",
    "SpecError",
    "SpecRefused",
    "bar_state",
    "compute_lock_digest",
    "deflated_sharpe",
    "evaluate_session",
    "format_report",
    "load_lock",
    "load_spec",
    "one_sided_t",
    "verify_lock",
]
