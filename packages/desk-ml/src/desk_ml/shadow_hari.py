"""S1 HARI: intraday HAR-RV expected move for the next 30 minutes. Log only.

Realised variance is the sum of squared 1-minute log returns over 5, 30 and 120
minutes, plus the previous session. EM30 is spot * sqrt(forecast variance), in
index points. Coefficients live in config/shadow/hari.yaml (placeholders until
the lab fits them). Never read by the order path.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from desk_ml.persist import repo_root

COEFF_KEYS = ("intercept", "rv_5", "rv_30", "rv_120", "rv_prev_day")
_DEFAULTS = {k: 0.0 for k in COEFF_KEYS}


def hari_config_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "config" / "shadow" / "hari.yaml"


def load_hari_coefficients(path: Optional[Path] = None) -> dict[str, Any]:
    """Flat yaml (key: number). Missing file or bad rows fall back to zeros."""
    out: dict[str, Any] = {**_DEFAULTS, "fitted": False, "note": "", "path": None}
    cfg = path or hari_config_path()
    out["path"] = str(cfg)
    try:
        text = Path(cfg).read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "fitted":
            out["fitted"] = val.lower() in {"1", "true", "yes"}
        elif key == "note":
            out["note"] = val.strip("\"'")
        elif key in _DEFAULTS:
            try:
                out[key] = float(val)
            except ValueError:
                out[key] = 0.0
    return out


def log_returns(closes: Sequence[float]) -> list[float]:
    out: list[float] = []
    prev: Optional[float] = None
    for raw in closes:
        try:
            cur = float(raw)
        except (TypeError, ValueError):
            continue
        if prev is not None and prev > 0 and cur > 0:
            out.append(math.log(cur / prev))
        if cur > 0:
            prev = cur
    return out


def realized_variance(returns: Sequence[float], window: int) -> Optional[float]:
    """Sum of squared log returns over the last `window` minutes. None if short."""
    n = int(window)
    if n <= 0 or len(returns) < n:
        return None
    chunk = returns[-n:]
    return float(sum(r * r for r in chunk))


def hari_forecast(
    closes: Sequence[float],
    *,
    prior_day_closes: Optional[Sequence[float]] = None,
    coefficients: Optional[Mapping[str, Any]] = None,
    spot: Optional[float] = None,
) -> dict[str, Any]:
    """Expected move for the next 30 minutes, in index points.

    A missing window contributes nothing (the coefficient is not applied).
    Placeholder zeros therefore forecast 0 until the lab supplies weights.
    """
    coeffs = dict(coefficients or load_hari_coefficients())
    rets = log_returns(closes)
    rv_5 = realized_variance(rets, 5)
    rv_30 = realized_variance(rets, 30)
    rv_120 = realized_variance(rets, 120)
    prior_rets = log_returns(prior_day_closes or [])
    rv_prev = float(sum(r * r for r in prior_rets)) if prior_rets else None
    parts = {"rv_5": rv_5, "rv_30": rv_30, "rv_120": rv_120, "rv_prev_day": rv_prev}
    variance = float(coeffs.get("intercept") or 0.0)
    for key, value in parts.items():
        if value is None:
            continue
        variance += float(coeffs.get(key) or 0.0) * float(value)
    if variance < 0:
        variance = 0.0
    last = None
    if spot is not None:
        try:
            last = float(spot)
        except (TypeError, ValueError):
            last = None
    if last is None and closes:
        try:
            last = float(closes[-1])
        except (TypeError, ValueError):
            last = None
    em30 = None
    if last is not None and last > 0 and variance > 0:
        em30 = float(last) * math.sqrt(variance)
    elif variance == 0.0:
        em30 = 0.0
    return {
        "em30": em30,
        "variance": variance,
        "spot": last,
        "rv_5": rv_5,
        "rv_30": rv_30,
        "rv_120": rv_120,
        "rv_prev_day": rv_prev,
        "fitted": bool(coeffs.get("fitted")),
        "coefficients": {k: float(coeffs.get(k) or 0.0) for k in COEFF_KEYS},
    }
