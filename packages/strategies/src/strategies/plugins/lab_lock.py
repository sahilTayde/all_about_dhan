"""Round 8 shadow helpers: causal feature reads, no orders."""

from __future__ import annotations

import math
from datetime import datetime

from contracts.clock import IST
from contracts.payloads import StrikeChoice, StrikeQuote

from strategies.feature_view_stub import FeatureView

PENDING_LAB = "PENDING_LAB"

# Confirmed look-ahead names (E2 used 09:59 HARI; E1 must not use same-minute OI).
LOOKAHEAD_FEATURES = frozenset(
    {"hari_0959", "hari_intraday", "oi_ce_chg", "oi_pe_chg", "oi_pc_chg"}
)


def as_ist(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        raise ValueError("timestamps must be tz-aware")
    return dt.astimezone(IST)


def feat(view: FeatureView, name: str) -> object | None:
    if name in LOOKAHEAD_FEATURES:
        return None
    return view.get(name)


def feat_f(view: FeatureView, name: str) -> float | None:
    raw = feat(view, name)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return float(raw)


def tercile(value: float, history: list[float]) -> int | None:
    """1=bottom, 2=mid, 3=top of the trailing sample. None if too short."""
    if len(history) < 3:
        return None
    ordered = sorted(history)
    n = len(ordered)
    lo = ordered[max(0, n // 3 - 1)]
    hi = ordered[min(n - 1, (2 * n) // 3)]
    if value >= hi:
        return 3
    if value <= lo:
        return 1
    return 2


def logistic(features: dict[str, float], weights: dict[str, float], intercept: float) -> float:
    z = intercept
    for key, weight in weights.items():
        z += weight * features.get(key, 0.0)
    if z > 30.0:
        return 1.0
    if z < -30.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


def fixed_strike(rule: str) -> StrikeChoice:
    empty = StrikeQuote(
        rule=rule,
        instrument_id="",
        bid=None,
        ask=None,
        mid=None,
        spread=None,
        quote_age_ms=None,
        est_delta=None,
        est_round_trip_pts=None,
    )
    return StrikeChoice(
        chosen=rule, reason="STRATEGY_FIXED", rule_version="r8-v1", alternatives=(empty,)
    )


def history_f(raw: object) -> list[float]:
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        out.append(float(item))
    return out
