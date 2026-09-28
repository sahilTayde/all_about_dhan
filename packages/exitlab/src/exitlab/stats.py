"""Summaries, bootstrap CIs, deflated Sharpe. No fabricated cells."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from exitlab.types import TradeResult


@dataclass(frozen=True)
class Summary:
    plan_id: str
    entry_set: str
    scenario: str
    split: str
    n_trades: int
    n_skipped: int
    win_rate: float | None
    avg_win: float | None
    avg_loss: float | None
    net_inr: float
    avg_net: float | None
    max_dd: float
    avg_mfe: float | None
    avg_mae: float | None
    avg_time_s: float | None
    sharpe: float | None
    deflated_sharpe: float | None
    net_ci_lo: float | None
    net_ci_hi: float | None
    n_variants_tested: int
    data_source: str
    low_confidence: bool = False


def _closed(rows: Sequence[TradeResult]) -> list[TradeResult]:
    return [r for r in rows if r.skipped is None]


def max_drawdown(nets: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    dd = 0.0
    for x in nets:
        equity += x
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return dd


def sharpe_ratio(nets: Sequence[float]) -> float | None:
    if len(nets) < 2:
        return None
    mu = sum(nets) / len(nets)
    var = sum((x - mu) ** 2 for x in nets) / (len(nets) - 1)
    if var <= 1e-18:
        return None
    return mu / math.sqrt(var) * math.sqrt(len(nets))


def deflated_sharpe(
    sr: float | None, n: int, n_trials: int, skew: float = 0.0, kurt: float = 3.0
) -> float | None:
    """Bailey / Lopez de Prado deflated Sharpe (approx). n_trials = variants tested."""
    if sr is None or n < 2 or n_trials < 1:
        return None
    # Expected max SR under n_trials tests (Bailey / Lopez de Prado DSR).
    euler = 0.5772156649
    if n_trials == 1:
        e_max = 0.0
    else:
        e_max = ((1.0 - euler) * _inv_norm(1.0 - 1.0 / n_trials)) + euler * _inv_norm(
            1.0 - 1.0 / (n_trials * math.e)
        )
    se = math.sqrt((1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr) / (n - 1))
    if se <= 1e-18:
        return None
    return (sr - e_max) / se


def _inv_norm(p: float) -> float:
    """Acklam inverse normal CDF, good enough for DSR."""
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
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
        -2.549732386500654e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00, 3.754408661907416e00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
        * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def bootstrap_mean_ci(
    xs: Sequence[float], *, seed: int, n_boot: int = 400, alpha: float = 0.05
) -> tuple[float, float] | None:
    if not xs:
        return None
    rng = random.Random(seed)
    means: list[float] = []
    n = len(xs)
    for _ in range(n_boot):
        sample = [xs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(alpha / 2 * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo * n, hi * n  # CI on the sum (net)


def summarize(
    rows: Sequence[TradeResult],
    *,
    plan_id: str,
    entry_set: str,
    scenario: str,
    split: str,
    n_variants: int,
    data_source: str,
    seed: int = 7,
) -> Summary:
    closed = _closed(rows)
    nets = [r.net_inr for r in closed]
    wins = [r.net_inr for r in closed if r.net_inr > 0]
    losses = [r.net_inr for r in closed if r.net_inr <= 0]
    sr = sharpe_ratio(nets)
    ci = bootstrap_mean_ci(nets, seed=seed) if nets else None
    return Summary(
        plan_id=plan_id,
        entry_set=entry_set,
        scenario=scenario,
        split=split,
        n_trades=len(closed),
        n_skipped=sum(1 for r in rows if r.skipped),
        win_rate=(len(wins) / len(closed)) if closed else None,
        avg_win=(sum(wins) / len(wins)) if wins else None,
        avg_loss=(sum(losses) / len(losses)) if losses else None,
        net_inr=round(sum(nets), 2),
        avg_net=(sum(nets) / len(nets)) if nets else None,
        max_dd=round(max_drawdown(nets), 2),
        avg_mfe=(sum(r.mfe_inr for r in closed) / len(closed)) if closed else None,
        avg_mae=(sum(r.mae_inr for r in closed) / len(closed)) if closed else None,
        avg_time_s=(sum(r.time_in_trade_s for r in closed) / len(closed)) if closed else None,
        sharpe=sr,
        deflated_sharpe=deflated_sharpe(sr, len(nets), n_variants),
        net_ci_lo=None if ci is None else round(ci[0], 2),
        net_ci_hi=None if ci is None else round(ci[1], 2),
        n_variants_tested=n_variants,
        data_source=data_source,
        low_confidence=len(closed) < 30,
    )


def as_row(s: Summary) -> dict[str, object]:
    return asdict(s)


def group_key(r: TradeResult, *, by_scenario: bool) -> tuple[str, str, str]:
    return (r.plan_id, r.entry_set, r.scenario if by_scenario else "ALL")
