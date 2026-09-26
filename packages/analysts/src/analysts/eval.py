"""Deflated Sharpe Ratio (Bailey & López de Prado, Journal of Portfolio Management, 2014).

``dsr(trade_pnls, n_trials)`` is the probability that the observed per-trade Sharpe
beats the expected maximum Sharpe under ``n_trials`` independent trials, using the
non-normal variance of the Sharpe estimator.

Sharpe uses the sample standard deviation (divide by n − 1). Skew and kurtosis are
raw moments (divide by n). Kurtosis is not excess (a normal sample is about 3).
``n_trials == 1`` has no selection haircut: the benchmark Sharpe is 0 (the
probabilistic Sharpe ratio against zero).
"""

from __future__ import annotations

import math
from typing import Sequence

EULER = 0.5772156649015329  # Euler–Mascheroni

# Peter J. Acklam's rational approximation for the inverse normal CDF.
_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_P_LOW = 0.02425


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF. ``norm_ppf(0.975)`` ≈ 1.959963984540054."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"p must be in (0, 1), got {p}")
    if p < _P_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )
    if p > 1.0 - _P_LOW:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (
            (((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0
        )
    q = p - 0.5
    r = q * q
    return (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / (
        ((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0
    )


def dsr(trade_pnls: Sequence[float], n_trials: int) -> float:
    """Deflated Sharpe Ratio in [0, 1] for one strategy's trade P&Ls and a trial count."""
    x = [float(v) for v in trade_pnls]
    n = len(x)
    if n < 3:
        raise ValueError("dsr needs at least 3 trade pnls")
    trials = int(n_trials)
    if trials < 1:
        raise ValueError("n_trials must be >= 1")
    mean = sum(x) / n
    var = sum((v - mean) ** 2 for v in x) / (n - 1)
    if var <= 0.0:
        if mean > 0:
            return 1.0
        if mean < 0:
            return 0.0
        return 0.5
    std = math.sqrt(var)
    sr = mean / std
    m3 = sum((v - mean) ** 3 for v in x) / n
    m4 = sum((v - mean) ** 4 for v in x) / n
    skew = m3 / (std ** 3)
    kurt = m4 / (std ** 4)
    factor = 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * sr * sr
    if factor <= 1e-12:
        factor = 1e-12
    if trials == 1:
        sr0 = 0.0
    else:
        z1 = norm_ppf(1.0 - 1.0 / trials)
        z2 = norm_ppf(1.0 - 1.0 / (trials * math.e))
        sr0 = math.sqrt(factor / (n - 1)) * ((1.0 - EULER) * z1 + EULER * z2)
    stat = (sr - sr0) * math.sqrt(n - 1) / math.sqrt(factor)
    return norm_cdf(stat)
