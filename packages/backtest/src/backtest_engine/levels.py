"""Named SL/TP level builders. No silent hardcoded strategy.

Methods are MIX / method ids. DESK_PLACEHOLDER is deprecated and labeled.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from backtest_engine.indicators import Bar, _wilder_atr

# Deprecated desk placeholder — never present as an unnamed strategy.
DESK_PLACEHOLDER_STOP_PTS = {"NIFTY": 30.0, "BANKNIFTY": 60.0, "SENSEX": 100.0}
STRIKE_STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}

# Default paper method when ATR seed exists (MIX-DESK-IQ-ATR-RR2 / MIX-SLTP-ATR-R2).
DEFAULT_LEVELS_METHOD = "MIX-SLTP-ATR-R2"
DEFAULT_ATR_PERIOD = 14
DEFAULT_ATR_MULT = 1.5
DEFAULT_RR = 2.0


def round_strike(spot: float, underlying: str) -> int:
    step = STRIKE_STEP.get(underlying, 50)
    return int(round(spot / step) * step)


def atr_at(bars: Sequence[Bar], period: int = DEFAULT_ATR_PERIOD) -> Optional[float]:
    if not bars:
        return None
    atrs = _wilder_atr(list(bars), period)
    for v in reversed(atrs):
        if v is not None:
            return float(v)
    return None


def _empty(*, note: str, method_id: str) -> dict[str, Any]:
    return {
        "strike": None,
        "entry": None,
        "stop": None,
        "target": None,
        "unit": "INDEX_POINTS_PROXY",
        "levels_ready": False,
        "levels_method": method_id,
        "levels_note": note,
        "mix_id": method_id,
    }


def build_levels(
    *,
    underlying: str,
    lean: str,
    spot: Optional[float],
    state: str,
    method_id: str = DEFAULT_LEVELS_METHOD,
    atr_value: Optional[float] = None,
    atr_mult: float = DEFAULT_ATR_MULT,
    rr: float = DEFAULT_RR,
    bars: Optional[Sequence[Bar]] = None,
) -> dict[str, Any]:
    """Strategy-selected paper levels. Option premium UNKNOWN until chain binds."""
    if lean not in ("CE", "PE") or spot is None or state in (
        "VETOED",
        "EXPIRED",
        "WATCH",
        "EARLY",
    ):
        return _empty(
            method_id=method_id,
            note=(
                "No live ticket levels while the lean is mixing, early, or held. "
                "EARLY is not a fill."
            ),
        )

    method = (method_id or DEFAULT_LEVELS_METHOD).upper()
    entry = round(float(spot), 2)
    strike = round_strike(float(spot), underlying)

    if method in ("MIX-SLTP-ATR-R2", "MIX-DESK-IQ-ATR-RR2"):
        atr = atr_value
        if atr is None and bars is not None:
            atr = atr_at(bars, DEFAULT_ATR_PERIOD)
        if atr is None or atr <= 0:
            return _empty(
                method_id=method,
                note=(
                    f"{method}: DATA_INSUFFICIENT — ATR({DEFAULT_ATR_PERIOD}) seed missing. "
                    "Refusing fake fixed points. Not a fill."
                ),
            )
        stop_d = float(atr) * float(atr_mult)
        target_d = stop_d * float(rr)
        return _packed(
            lean=lean,
            strike=strike,
            entry=entry,
            stop_d=stop_d,
            target_d=target_d,
            method_id=method,
            unit="INDEX_POINTS_PROXY",
            rr=rr,
            extra={
                "atr": round(float(atr), 4),
                "atr_period": DEFAULT_ATR_PERIOD,
                "atr_mult": atr_mult,
                "levels_note": (
                    f"Paper levels from {method}: ATR({DEFAULT_ATR_PERIOD})×{atr_mult} stop, "
                    f"R×{rr} target (index proxy, not option premium). You decide. Orders refused."
                ),
            },
        )

    if method == "MIX-SLTP-ST-FLIP":
        # Ticket shows prefer RR as honesty label; exit is ST flip (no fixed stop points).
        return {
            "strike": strike,
            "entry": entry,
            "stop": None,
            "target": None,
            "unit": "SUPERTREND_FLIP",
            "levels_ready": True,
            "levels_method": method,
            "mix_id": method,
            "rr_prefer": 2.0,
            "levels_note": (
                "MIX-SLTP-ST-FLIP: exit = 3m close through Supertrend (STRAT-003). "
                "No fixed index-point stop on the ticket. Prefer RR 2.0 is preference only."
            ),
        }

    if method == "MIX-SLTP-PREM-PCT":
        return {
            "strike": strike,
            "entry": None,
            "stop": None,
            "target": None,
            "unit": "OPTION_PREMIUM_PCT",
            "levels_ready": False,
            "levels_method": method,
            "mix_id": method,
            "target_premium_pct_range": [0.20, 0.30],
            "levels_note": (
                "MIX-SLTP-PREM-PCT (STRAT-002): needs option LTP. "
                "DATA_INSUFFICIENT on index-only ticket. Never attach to STRAT-003."
            ),
        }

    if method in ("DESK_PLACEHOLDER", "STOP_PTS_DEPRECATED"):
        stop_d = DESK_PLACEHOLDER_STOP_PTS.get(underlying, 30.0)
        target_d = stop_d * 2.0
        return _packed(
            lean=lean,
            strike=strike,
            entry=entry,
            stop_d=stop_d,
            target_d=target_d,
            method_id="DESK_PLACEHOLDER",
            unit="INDEX_POINTS_PROXY",
            rr=2.0,
            extra={
                "deprecated": True,
                "levels_note": (
                    "DEPRECATED DESK_PLACEHOLDER fixed index points — not a named teacher strategy. "
                    "Prefer MIX-SLTP-ATR-R2 / MIX-DESK-IQ-ATR-RR2 when ATR exists."
                ),
            },
        )

    return _empty(
        method_id=method,
        note=f"Unknown levels method {method}. DATA_INSUFFICIENT — no silent hardcode.",
    )


def _packed(
    *,
    lean: str,
    strike: int,
    entry: float,
    stop_d: float,
    target_d: float,
    method_id: str,
    unit: str,
    rr: float,
    extra: dict[str, Any],
) -> dict[str, Any]:
    if lean == "CE":
        stop = round(entry - stop_d, 2)
        target = round(entry + target_d, 2)
    else:
        stop = round(entry + stop_d, 2)
        target = round(entry - target_d, 2)
    out: dict[str, Any] = {
        "strike": strike,
        "entry": entry,
        "stop": stop,
        "target": target,
        "unit": unit,
        "levels_ready": True,
        "levels_method": method_id,
        "mix_id": method_id,
        "rr_prefer": rr,
        "stop_pts": round(stop_d, 4),
        "target_pts": round(target_d, 4),
    }
    out.update(extra)
    return out
