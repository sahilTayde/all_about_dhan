"""S2 order-flow shadow score from option-chain snapshots. Log only.

Near-the-money CE vs PE open interest and volume, change across the last 1–5
snapshots, divided by the sum of absolute changes so the score sits in [-1, 1].
Positive means call flow increased relative to put flow. Missing prints stay
None — this module does not invent OI.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

STRIKE_STEP = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "SENSEX": 100.0}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def near_money_totals(
    wing_quotes: Optional[dict],
    *,
    atm: Optional[float],
    step: float,
) -> Optional[dict[str, Optional[float]]]:
    """Sum CE/PE OI and volume on strikes within one step of ATM."""
    if not isinstance(wing_quotes, dict) or atm is None or step <= 0:
        return None
    ce_oi = pe_oi = ce_vol = pe_vol = 0.0
    seen_oi = seen_vol = False
    n = 0
    for key, cell in wing_quotes.items():
        if not isinstance(cell, dict):
            continue
        try:
            strike = float(key)
        except (TypeError, ValueError):
            continue
        if abs(strike - float(atm)) > float(step) + 1e-6:
            continue
        n += 1
        for side, bucket in (("ce", "oi"), ("pe", "oi"), ("ce", "volume"), ("pe", "volume")):
            val = _num(cell.get(f"{side}_{bucket}"))
            if val is None:
                continue
            if bucket == "oi" and side == "ce":
                ce_oi += val
                seen_oi = True
            elif bucket == "oi":
                pe_oi += val
                seen_oi = True
            elif side == "ce":
                ce_vol += val
                seen_vol = True
            else:
                pe_vol += val
                seen_vol = True
    if n == 0 or not (seen_oi or seen_vol):
        return None
    return {
        "ce_oi": ce_oi if seen_oi else None,
        "pe_oi": pe_oi if seen_oi else None,
        "ce_vol": ce_vol if seen_vol else None,
        "pe_vol": pe_vol if seen_vol else None,
        "n_strikes": float(n),
    }


def _delta(newer: Optional[float], older: Optional[float]) -> Optional[float]:
    if newer is None or older is None:
        return None
    return float(newer) - float(older)


def order_flow_score(snapshots: Sequence[Optional[dict[str, Any]]]) -> dict[str, Any]:
    """Change from the oldest snapshot in the window to the newest.

    The window is the last 1–5 snapshots the caller kept. One snapshot has no
    change, so the score is None.
    """
    rows = [r for r in snapshots if isinstance(r, dict)][-5:]
    empty: dict[str, Any] = {
        "score": None,
        "n_snapshots": len(rows),
        "d_ce_oi": None,
        "d_pe_oi": None,
        "d_ce_vol": None,
        "d_pe_vol": None,
    }
    if len(rows) < 2:
        return empty
    first, last = rows[0], rows[-1]
    deltas = {
        "d_ce_oi": _delta(last.get("ce_oi"), first.get("ce_oi")),
        "d_pe_oi": _delta(last.get("pe_oi"), first.get("pe_oi")),
        "d_ce_vol": _delta(last.get("ce_vol"), first.get("ce_vol")),
        "d_pe_vol": _delta(last.get("pe_vol"), first.get("pe_vol")),
    }
    used = [v for v in deltas.values() if v is not None]
    if not used:
        return {**empty, **deltas, "n_snapshots": len(rows)}
    # CE minus PE. Missing legs are left out of both the numerator and the scale.
    num = 0.0
    den = 0.0
    if deltas["d_ce_oi"] is not None and deltas["d_pe_oi"] is not None:
        num += deltas["d_ce_oi"] - deltas["d_pe_oi"]
        den += abs(deltas["d_ce_oi"]) + abs(deltas["d_pe_oi"])
    if deltas["d_ce_vol"] is not None and deltas["d_pe_vol"] is not None:
        num += deltas["d_ce_vol"] - deltas["d_pe_vol"]
        den += abs(deltas["d_ce_vol"]) + abs(deltas["d_pe_vol"])
    score = None if den <= 0 else max(-1.0, min(1.0, num / den))
    return {"score": score, "n_snapshots": len(rows), **deltas}
