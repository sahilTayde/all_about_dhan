"""Forward report: total net is the headline; deflated Sharpe and trial count always present."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ForwardReport:
    spec_id: str
    spec_hash: str
    session: str
    n: int
    state: str
    stage: str
    headline_total_net: float
    net_depth_inr: float
    net_fcmeas_inr: float
    gross_inr: float
    deflated_sharpe: float
    cumulative_trials: int
    depth_coverage: float
    legs: dict[str, dict[str, float]] = field(default_factory=dict)
    kernel_envelopes: int = 0
    kernel_hash: str = ""
    skipped: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def format_report(report: ForwardReport) -> str:
    """One founder-page line. Headline is always total net after costs."""
    if report.skipped:
        return f"{report.spec_id}: skipped ({report.reason})"
    return (
        f"{report.spec_id}: headline_total_net={report.headline_total_net:.2f} "
        f"deflated_sharpe={report.deflated_sharpe:.4f} "
        f"cumulative_trials={report.cumulative_trials} "
        f"n={report.n} state={report.state} stage={report.stage}"
    )
