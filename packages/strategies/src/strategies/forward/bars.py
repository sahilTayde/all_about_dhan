"""Round 8 FWD-BAR state machine. Win rate is never a pass criterion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

RUNNING = "RUNNING"
KILLED = "KILLED"
PROMISING = "PROMISING"
PASS_TO_REVIEW = "PASS_TO_REVIEW"
NET_POSITIVE_NOT_SIGNIFICANT = "NET_POSITIVE_NOT_SIGNIFICANT"
DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
EULER = 0.5772156649015329


@dataclass(frozen=True)
class FwdBars:
    n_kill: int = 30
    n_promising: int = 60
    n_pass: int = 120
    t_crit: float = 2.13

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> FwdBars:
        src = raw or {}
        t_raw = src.get("t_crit", src.get("t_one_sided", 2.13))
        return cls(
            n_kill=int(str(src.get("n_kill", 30))),
            n_promising=int(str(src.get("n_promising", 60))),
            n_pass=int(str(src.get("n_pass", 120))),
            t_crit=float(str(t_raw)),
        )


def one_sided_t(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    if var <= 0:
        return math.inf if mean > 0 else 0.0
    return mean / math.sqrt(var / n)


def _halves_net_positive(nets: list[float]) -> bool:
    mid = len(nets) // 2
    if mid == 0:
        return False
    return sum(nets[:mid]) > 0 and sum(nets[mid:]) > 0


def bar_state(
    *,
    n: int,
    gross: float,
    nets: list[float],
    bars: FwdBars | None = None,
    depth_coverage: float | None = None,
) -> str:
    """FWD-BAR. ``depth_coverage`` < 0.95 is DATA_INSUFFICIENT and does not count as n."""
    cfg = bars or FwdBars()
    if depth_coverage is not None and depth_coverage < 0.95:
        return DATA_INSUFFICIENT
    if n >= cfg.n_kill and gross <= 0:
        return KILLED
    t_stat = one_sided_t(nets)
    significant = n >= cfg.n_pass and t_stat >= cfg.t_crit and _halves_net_positive(nets)
    total_net = sum(nets)
    if n >= cfg.n_pass:
        if significant:
            return PASS_TO_REVIEW
        if total_net > 0:
            return NET_POSITIVE_NOT_SIGNIFICANT
        return KILLED
    if n >= cfg.n_promising and _halves_net_positive(nets):
        return PROMISING
    return RUNNING


def deflated_sharpe(returns: list[float], n_trials: int) -> float:
    """Bailey / López de Prado expected-max haircut. ``n_trials`` is the cumulative count."""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    var = sum((x - mean) ** 2 for x in returns) / (n - 1)
    if var <= 0:
        return 0.0
    sharpe = mean / math.sqrt(var)
    trials = max(int(n_trials), 1)
    # Expected max of ``trials`` independent standard Sharpes (extreme-value approx).
    inv = _norm_ppf(1.0 - 1.0 / trials)
    inv_e = _norm_ppf(1.0 - 1.0 / (trials * math.e))
    expected_max = (1.0 - EULER) * inv + EULER * inv_e
    return sharpe - expected_max


def _norm_ppf(p: float) -> float:
    """Acklam rational approximation of the standard-normal quantile."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = (
        -3.969683028665376e01,
        2.209460984213454e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671384974443e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )
