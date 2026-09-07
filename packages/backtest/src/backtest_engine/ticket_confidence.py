"""Paper ticket levels + agreement confidence. Not a fill. Not a win-rate.

Customer `/` speaks plain labels. Mix IDs stay in the payload for /desk / ledger.
Levels come from named MIX / method ids — see levels.py. Hardcoded STOP_PTS removed
from the default path (deprecated DESK_PLACEHOLDER only if explicitly requested).
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from backtest_engine.indicators import Bar
from backtest_engine.levels import (
    DEFAULT_LEVELS_METHOD,
    DESK_PLACEHOLDER_STOP_PTS,
    build_levels,
    quarantine_index_proxy_from_customer_ticket,
    round_strike,
)

# Re-export deprecated map for tests/migration only — do not use as unnamed strategy.
STOP_PTS = DESK_PLACEHOLDER_STOP_PTS  # noqa: N816 — legacy alias, deprecated
STRIKE_STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}

STAGE_BASE = {
    "WATCH": 18,
    "EARLY": 36,
    "CONFIRMED": 55,
    "IN-PROGRESS": 58,
    "VETOED": 0,
    "EXPIRED": 0,
    "HOLD": 0,
}

CONFIDENCE_CAP = 72

PLAIN = {
    "MIX-DEFAULT-BUY": {
        "label": "Session trend stack",
        "why": "Futures-style session average + trend tools agree on one side.",
    },
    "MIX-CLUB-GR": {
        "label": "Gap + expansion",
        "why": "Open gap direction and a range expansion print agree on one side.",
    },
    "MIX-DESK-IQ-ATR-RR2": {
        "label": "VWAP lean + ATR risk",
        "why": "Session stack lean with ATR stop and 2R target (external interview club).",
    },
    "MIX-CF-OKALA-IN-LEVEL": {
        "label": "Okala India level (paper starter)",
        "why": "FOUNDER_PAPER_ACCEPT magnet reaction — PAPER notify only, not a win-rate claim.",
    },
    "MIX-CF-OKALA-IN-FORK": {
        "label": "Okala India fork (paper starter)",
        "why": "FOUNDER_PAPER_ACCEPT fork reclaim — PAPER notify only, not a win-rate claim.",
    },
    "MIX-CF-OKALA-IN-H-CROSS": {
        "label": "Okala India H-cross (paper starter)",
        "why": "FOUNDER_PAPER_ACCEPT H+cross stand-in — PAPER notify only, not a win-rate claim.",
    },
    "MIX-CF-OKALA-IN-REPAIR": {
        "label": "Okala India repair (paper starter)",
        "why": "FOUNDER_PAPER_ACCEPT repair confluence — PAPER notify only, not a win-rate claim.",
    },
}


def paper_levels(
    *,
    underlying: str,
    lean: str,
    spot: Optional[float],
    state: str,
    method_id: str = DEFAULT_LEVELS_METHOD,
    atr_value: Optional[float] = None,
    bars: Optional[Sequence[Bar]] = None,
    atr_mult: float = 1.5,
    rr: float = 2.0,
) -> dict[str, Any]:
    """Named-strategy paper levels (may be INDEX_POINTS_PROXY for chart/research)."""
    return build_levels(
        underlying=underlying,
        lean=lean if lean in ("CE", "PE") else "SKIP",
        spot=spot,
        state=state,
        method_id=method_id,
        atr_value=atr_value,
        atr_mult=atr_mult,
        rr=rr,
        bars=bars,
    )


def customer_ticket_levels(
    *,
    underlying: str,
    lean: str,
    spot: Optional[float],
    state: str,
    method_id: str = DEFAULT_LEVELS_METHOD,
    atr_value: Optional[float] = None,
    bars: Optional[Sequence[Bar]] = None,
    atr_mult: float = 1.5,
    rr: float = 2.0,
    option_ltp: Optional[float] = None,
    premium_meta: Optional[dict[str, Any]] = None,
    stop_pct: Optional[float] = None,
    target_pct: Optional[float] = None,
    paper_starter_premium_stop: bool = False,
) -> dict[str, Any]:
    """Customer `/` ticket: premium Entry/SL/Target only — never index masquerade.

    When option_ltp is set, binds MIX-SLTP-PREM-PCT premium levels. Else DI with gap.
    ``paper_starter_premium_stop`` (or stop_pct) fills premium Stop = entry×(1−pct)
    for Okala PAPER starter tickets (HYPOTHESIS until swing/greek map).
    """
    meta = dict(premium_meta or {})
    if paper_starter_premium_stop:
        meta["paper_starter_premium_stop"] = True
        if stop_pct is None:
            stop_pct = 0.25
        if target_pct is None:
            target_pct = 0.25
    raw = paper_levels(
        underlying=underlying,
        lean=lean,
        spot=spot,
        state=state,
        method_id=method_id,
        atr_value=atr_value,
        bars=bars,
        atr_mult=atr_mult,
        rr=rr,
    )
    return quarantine_index_proxy_from_customer_ticket(
        raw,
        underlying_spot=spot,
        option_ltp=option_ltp,
        lean=lean,
        premium_meta=meta or None,
        bars=bars,
        stop_pct=stop_pct,
        target_pct=target_pct,
    )


def _band(score: int) -> str:
    if score <= 0:
        return "none"
    if score < 35:
        return "low"
    if score < 55:
        return "moderate"
    return "higher_agreement"


def confidence_from_books(
    *,
    underlying: str,
    default_row: dict[str, Any],
    club_row: Optional[dict[str, Any]] = None,
    okala_row: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Agreement score across predefined paper books. Not a predicted win %."""
    d_lean = default_row.get("lean")
    d_state = str(default_row.get("state") or "WATCH").upper()
    score = STAGE_BASE.get(d_state, 15)
    eligible: list[dict[str, str]] = []
    why_bits: list[str] = []

    if d_lean in ("CE", "PE") and d_state not in ("VETOED", "EXPIRED"):
        meta = PLAIN["MIX-DEFAULT-BUY"]
        eligible.append(
            {
                "mix_id": "MIX-DEFAULT-BUY",
                "label": meta["label"],
                "side": "BUY_CE" if d_lean == "CE" else "BUY_PE",
                "state": d_state,
                "why": meta["why"],
            }
        )
        why_bits.append(meta["why"])

    club = club_row or {}
    c_lean = club.get("lean")
    c_state = str(club.get("state") or "WATCH").upper()
    if c_lean in ("CE", "PE") and c_state not in ("VETOED", "EXPIRED"):
        meta = PLAIN["MIX-CLUB-GR"]
        eligible.append(
            {
                "mix_id": "MIX-CLUB-GR",
                "label": meta["label"],
                "side": "BUY_CE" if c_lean == "CE" else "BUY_PE",
                "state": c_state,
                "why": meta["why"],
            }
        )
        if d_lean == c_lean and d_lean in ("CE", "PE"):
            score += 15
            why_bits.append("A second playbook agrees on the same side.")
        elif not eligible:
            why_bits.append(meta["why"])
            score = max(score, STAGE_BASE.get(c_state, 15))

    okala = okala_row or {}
    o_lean = okala.get("lean")
    o_state = str(okala.get("state") or "WATCH").upper()
    o_mix = str(okala.get("mix_id") or "")
    if o_mix not in PLAIN:
        o_mix = "MIX-CF-OKALA-IN-H-CROSS"
    if o_lean in ("CE", "PE") and o_state not in ("VETOED", "EXPIRED"):
        meta = PLAIN[o_mix]
        eligible.append(
            {
                "mix_id": str(okala.get("mix_id") or o_mix),
                "label": meta["label"],
                "side": "BUY_CE" if o_lean == "CE" else "BUY_PE",
                "state": o_state,
                "why": meta["why"],
            }
        )
        if d_lean == o_lean and d_lean in ("CE", "PE"):
            score += 12
            why_bits.append("Okala India paper starter agrees on the same side.")
        elif not any(e.get("mix_id") == "MIX-DEFAULT-BUY" for e in eligible):
            why_bits.append(meta["why"])
            score = max(score, STAGE_BASE.get(o_state, 15))

    active_extra = (c_lean in ("CE", "PE")) or (o_lean in ("CE", "PE"))
    if d_state == "VETOED" or (d_lean not in ("CE", "PE") and not active_extra):
        score = 0

    score = min(int(score), CONFIDENCE_CAP)
    band = _band(score)
    side = None
    if d_lean in ("CE", "PE"):
        side = "BUY_CE" if d_lean == "CE" else "BUY_PE"
    elif c_lean in ("CE", "PE"):
        side = "BUY_CE" if c_lean == "CE" else "BUY_PE"
    elif o_lean in ("CE", "PE"):
        side = "BUY_CE" if o_lean == "CE" else "BUY_PE"

    return {
        "underlying": underlying,
        "score_pct": score,
        "band": band,
        "label": {
            "none": "No active lean",
            "low": "Low agreement",
            "moderate": "Moderate agreement",
            "higher_agreement": "Higher agreement",
        }[band],
        "side": side,
        "eligible": eligible,
        "eligible_count": len(eligible),
        "why": " ".join(why_bits) if why_bits else "No playbook is firing a side yet.",
        "fairness": (
            "This is a desk agreement score (stage + how many playbooks agree). "
            "It is NOT a win rate and NOT a promise the trade will work."
        ),
        "customer_decide": True,
        "orders": "refused",
        "cap": CONFIDENCE_CAP,
    }
