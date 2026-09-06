"""Walk-forward logistic leans on INDEX 3m. Train never sees future bars. Not a theorem."""

from __future__ import annotations

import math

from backtest_engine.clocks import minutes_ist, session_date_ist
from backtest_engine.indicators import Bar, sma


def _sigmoid(z: float) -> float:
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def _feat(bars: list[Bar], i: int, sma20: list[float | None]) -> list[float] | None:
    if i < 20:
        return None
    c = bars[i].close
    prev = bars[i - 1].close
    lag5 = bars[i - 5].close
    if c <= 0 or prev <= 0 or lag5 <= 0:
        return None
    m = sma20[i]
    if m is None or m <= 0:
        return None
    rng = bars[i].high - bars[i].low
    body = abs(bars[i].close - bars[i].open)
    tod = (minutes_ist(bars[i].ts) - 9 * 60) / (6.0 * 60)
    return [
        (c - prev) / prev,
        (c - lag5) / lag5,
        body / (rng + 1e-9),
        (c - m) / m,
        tod,
        1.0 if bars[i].close > bars[i].open else 0.0,
        1.0 if bars[i].close > bars[i - 1].close else 0.0,
        1.0 if bars[i].close > bars[i - 3].close else 0.0,
    ]


def _fit(
    xs: list[list[float]], ys: list[float], *, epochs: int = 25, lr: float = 0.15
) -> tuple[list[float], float]:
    nfeat = len(xs[0])
    w = [0.0] * nfeat
    b = 0.0
    for _ in range(epochs):
        for x, y in zip(xs, ys):
            z = b + sum(wj * xj for wj, xj in zip(w, x))
            err = _sigmoid(z) - y
            for j in range(nfeat):
                w[j] -= lr * err * x[j]
            b -= lr * err
    return w, b


def _mean_std(cols: list[list[float]]) -> tuple[list[float], list[float]]:
    n = len(cols)
    nf = len(cols[0])
    mu = [sum(row[j] for row in cols) / n for j in range(nf)]
    sd = []
    for j in range(nf):
        var = sum((row[j] - mu[j]) ** 2 for row in cols) / n
        sd.append(math.sqrt(var) if var > 1e-12 else 1.0)
    return mu, sd


def _scale(x: list[float], mu: list[float], sd: list[float]) -> list[float]:
    return [(a - m) / s for a, m, s in zip(x, mu, sd)]


def lean_ml_logit(bars: list[Bar], *, train_end_ts: int) -> list[str]:
    """Fit on bars with next-bar label strictly before train_end_ts. Predict after.

    Label is next INDEX 3m close direction, not option premium (no fill leak).
    """
    n = len(bars)
    out = ["SKIP"] * n
    if n < 40:
        return out
    sma20 = sma([b.close for b in bars], 20)
    xs: list[list[float]] = []
    ys: list[float] = []
    for i in range(n - 1):
        if bars[i].ts >= train_end_ts:
            break
        if session_date_ist(bars[i].ts) != session_date_ist(bars[i + 1].ts):
            continue
        feat = _feat(bars, i, sma20)
        if feat is None:
            continue
        ys.append(1.0 if bars[i + 1].close > bars[i].close else 0.0)
        xs.append(feat)
    if len(xs) < 200:
        return out
    if len(xs) > 25000:
        step = max(1, len(xs) // 25000)
        xs = xs[::step]
        ys = ys[::step]
    mu, sd = _mean_std(xs)
    xs_s = [_scale(x, mu, sd) for x in xs]
    w, b = _fit(xs_s, ys)
    for i in range(n):
        if bars[i].ts < train_end_ts:
            continue
        feat = _feat(bars, i, sma20)
        if feat is None:
            continue
        z = b + sum(wj * xj for wj, xj in zip(w, _scale(feat, mu, sd)))
        p = _sigmoid(z)
        if p >= 0.55:
            out[i] = "CE"
        elif p <= 0.45:
            out[i] = "PE"
    return out
