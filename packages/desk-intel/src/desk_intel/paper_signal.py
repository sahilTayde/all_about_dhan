"""Map MARKET_SIGNAL → later GET /paper/signal shape (apps/api DeskSignal).

Directional leans only. NEUTRAL / NO_TRADE stay off the dashboard dict.
Does not place orders. Does not invent entry/stop/target.
"""

from __future__ import annotations

from typing import Any

from desk_intel.schema import COMPLIANCE_NOTE, MarketSignal
from desk_intel.time_ist import now_ist_iso


def lean_to_side(lean: str) -> str | None:
    if lean == "BUY_CE":
        return "BUY_CE"
    if lean == "BUY_PE":
        return "BUY_PE"
    return None


def market_signal_to_desk(signal: MarketSignal) -> dict[str, Any] | None:
    side = lean_to_side(signal.lean)
    if side is None:
        return None
    return {
        "id": signal.id,
        "underlying": signal.underlying,
        "side": side,
        "strike": signal.atm_strike,
        "entry": None,
        "stop": None,
        "target": None,
        "expiry": signal.expiry,
        "systemOutcome": None,
        "stage": signal.stage,
        "outcome": signal.outcome,
        "stillValid": signal.still_valid,
        "sentimentWindows": [w.to_dict() for w in (signal.sentiment_windows or [])],
        "note": (
            f"confidence={signal.confidence:.2f} regime={signal.risk_regime} "
            f"stage={signal.stage}. "
            "Bias only — not a fillable ticket. Stale CONFIRMED/IN-PROGRESS "
            "without an outcome is forbidden."
        ),
    }


def to_paper_desk(signals: list[MarketSignal]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    skipped: dict[str, str] = {}
    for signal in signals:
        desk = market_signal_to_desk(signal)
        if desk is None:
            skipped[signal.underlying] = f"{signal.lean} — not mapped to BUY_CE/BUY_PE"
            continue
        mapped[signal.underlying] = desk
        signal.paper_signal = desk
    as_of = signals[0].timestamp if signals else now_ist_iso()
    return {
        "meta": {
            "source": "desk_intel",
            "placeholder": True,
            "asOf": as_of,
            "note": COMPLIANCE_NOTE,
        },
        "underlyings": [s.underlying for s in signals],
        "signals": mapped,
        "skipped": skipped,
        "market_signals": [s.to_dict() for s in signals],
    }
