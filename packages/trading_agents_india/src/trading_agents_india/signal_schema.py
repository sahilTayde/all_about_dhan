"""DESK_SIGNAL_JSON v1 — strict paper-signal JSON for the web app.

Modeled on the founder's GEMINI_SKILL.md §68 contract and hardened by a 4-round
Gemini+OpenAI counsel loop (teams/00_orchestrator/docs/COUNSEL_SIGNAL_FORMAT_2026-09-10.md).

Hard rules enforced HERE, not left to producers:
1. Veto / risk_veto        -> decision NO_TRADE, status VETOED (overrides everything).
2. BUY_CE / BUY_PE          -> requires non-empty invalidation + future valid_until_ist
                              + premium_ohlc_present, else DOWNGRADE to WAIT + risk flag.
3. WAIT                     -> status WATCHING.  NO_TRADE -> status INACTIVE.
4. confidence_score = None when data_quality.score < 40.
5. order_flow stays {"status": "UNAVAILABLE"} — Dhan has no aggressor-delta surface.
6. Never a win-rate claim. PAPER only. Execution refused. NO_PROMOTE.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

IST = timezone(timedelta(hours=5, minutes=30))

SCHEMA_VERSION = "desk-1.0"
CONFIDENCE_NULL_FLOOR = 40

DECISIONS = ("BUY_CE", "BUY_PE", "WAIT", "NO_TRADE")
STATUSES = ("WATCHING", "ACTIVE", "INACTIVE", "VETOED", "EXPIRED")
TREND_ENUM = ("UP", "DOWN", "FLAT", "UNKNOWN")
CONFIRM_ENUM = ("ABOVE", "BELOW", "RECLAIM", "REJECT", "FLAT", "UNKNOWN")

EVIDENCE_ALIGNMENT_NOTE = (
    "confidence_score is evidence alignment (0-100), NOT a win probability. "
    "PAPER research signal; UNVALIDATED; not investment advice."
)

RISK_FLAG_DOWNGRADED_INVALIDATION = "DOWNGRADED_MISSING_INVALIDATION"
RISK_FLAG_DOWNGRADED_PREMIUM = "DOWNGRADED_MISSING_PREMIUM_OHLC"
RISK_FLAG_DOWNGRADED_EXPIRED = "DOWNGRADED_EXPIRED_VALIDITY"


def _confirm(value: Optional[str]) -> str:
    v = (value or "").strip().upper()
    return v if v in CONFIRM_ENUM else "UNKNOWN"


def _trend(value: Optional[str]) -> str:
    v = (value or "").strip().upper()
    return v if v in TREND_ENUM else "UNKNOWN"


def _data_quality(ticket: Any, *, spot_present: bool, ltp_present: bool) -> dict[str, Any]:
    missing = [str(g) for g in (getattr(ticket, "data_gaps", None) or [])]
    warnings: list[str] = []
    score = 100
    if not spot_present:
        score -= 30
        warnings.append("spot missing")
    if not ltp_present:
        score -= 25
        warnings.append("option LTP missing")
    score -= min(30, 5 * len(missing))
    score = max(0, score)
    return {"score": score, "missing_fields": missing, "warnings": warnings}


def build_signal_json(
    ticket: Any,
    *,
    signal_id: str,
    supersedes_signal_id: Optional[str] = None,
    market_status: str = "UNKNOWN",
    now_ist: Optional[datetime] = None,
    invalidation: Optional[str] = None,
    valid_until_ist: Optional[str] = None,
    premium_ohlc_present: bool = False,
    spot: Optional[float] = None,
    trend: Optional[str] = None,
    technical: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Format one PaperTicket into DESK_SIGNAL_JSON v1. Pure formatter — no side effects."""
    now = now_ist or datetime.now(IST)
    premium = dict(getattr(ticket, "premium_lean", None) or {})
    option_ltp = premium.get("option_ltp")
    ltp_present = option_ltp not in (None, "")
    spot_present = spot is not None

    risk_veto = bool(getattr(ticket, "risk_veto", False))
    vetoes = [str(v) for v in (getattr(ticket, "vetoes", None) or [])]
    stage = str(getattr(ticket, "stage", "WATCH"))
    lean = str(getattr(ticket, "lean", "HOLD"))

    risk_flags: list[str] = []

    # Precedence rule 1: veto overrides everything.
    if risk_veto or stage == "VETOED" or vetoes:
        decision, status = "NO_TRADE", "VETOED"
    elif lean in ("BUY_CE", "BUY_PE"):
        decision, status = lean, "ACTIVE"
        # Precedence rule 2: BUY_* must carry invalidation + validity + premium tape.
        if not (invalidation or "").strip():
            decision, status = "WAIT", "WATCHING"
            risk_flags.append(RISK_FLAG_DOWNGRADED_INVALIDATION)
        elif not valid_until_ist or str(valid_until_ist) <= now.isoformat(timespec="seconds"):
            decision, status = "WAIT", "WATCHING"
            risk_flags.append(RISK_FLAG_DOWNGRADED_EXPIRED)
        elif not premium_ohlc_present:
            decision, status = "WAIT", "WATCHING"
            risk_flags.append(RISK_FLAG_DOWNGRADED_PREMIUM)
    elif stage in ("WATCH", "EARLY"):
        decision, status = "WAIT", "WATCHING"
    else:
        decision, status = "NO_TRADE", "INACTIVE"

    quality = _data_quality(ticket, spot_present=spot_present, ltp_present=ltp_present)

    confidence: Optional[int]
    raw_conf = float(getattr(ticket, "confidence", 0.0) or 0.0)
    confidence = round(max(0.0, min(1.0, raw_conf)) * 100)
    if quality["score"] < CONFIDENCE_NULL_FLOOR:
        confidence = None

    tech = technical or {}
    reasons = [str(r) for r in (getattr(ticket, "reasons", None) or [])]

    return {
        "schema_version": SCHEMA_VERSION,
        "signal_id": signal_id,
        "supersedes_signal_id": supersedes_signal_id,
        "analysis_timestamp_ist": now.isoformat(timespec="seconds"),
        "market_status": market_status,
        "instrument": str(getattr(ticket, "underlying", "")),
        "decision": decision,
        "stage": stage,
        "confidence_score": confidence,
        "underlying": {
            "spot": spot,
            "trend": _trend(trend),
            "trigger_level": None,
            "invalidation_level": None,
        },
        "option": {
            "symbol": premium.get("symbol"),
            "strike": premium.get("strike"),
            "type": premium.get("type"),
            "entry": None,
            "stop_loss": None,
            "target_1": None,
            "target_2": None,
            "target_3": None,
            "iv": None,
            "oi_change": None,
            "ltp": option_ltp if ltp_present else None,
            "option_data_timestamp_ist": premium.get("as_of_ist"),
            "premium_ohlc_present": bool(premium_ohlc_present),
        },
        "technical_confirmation": {
            "price_action": _confirm(tech.get("price_action")),
            "vwap": _confirm(tech.get("vwap")),
            "ema": _confirm(tech.get("ema")),
            "supertrend": _confirm(tech.get("supertrend")),
            "volume": _confirm(tech.get("volume")),
            "level": tech.get("level"),
        },
        "premium_analysis": {
            "source": premium.get("source"),
            "ltp_present": ltp_present,
            "confirmation": _confirm(premium.get("confirmation")),
        },
        "order_flow": {"status": "UNAVAILABLE"},
        "bull_case": [s for s in [str(getattr(ticket, "bull_summary", "") or "")] if s],
        "bear_case": [s for s in [str(getattr(ticket, "bear_summary", "") or "")] if s],
        "primary_reason": reasons[0] if reasons else "DATA_INSUFFICIENT",
        "reasons": reasons,
        "invalidation": (invalidation or None),
        "valid_until_ist": valid_until_ist,
        "risk_veto": risk_veto,
        "vetoes": vetoes,
        "data_quality": quality,
        "risk_flags": risk_flags,
        "compliance": {
            "paper_only": True,
            "execution": "refused",
            "NO_PROMOTE": True,
            "layer": str(getattr(ticket, "layer", "HYPOTHESIS")),
            "win_rate_claim": None,
            "evidence_alignment_note": EVIDENCE_ALIGNMENT_NOTE,
        },
        "status": status,
    }


def apply_expiry(signal: dict[str, Any], *, now_ist: Optional[datetime] = None) -> dict[str, Any]:
    """Lifecycle: past valid_until_ist an ACTIVE/WATCHING card becomes EXPIRED."""
    now = (now_ist or datetime.now(IST)).isoformat(timespec="seconds")
    until = signal.get("valid_until_ist")
    if until and str(until) <= now and signal.get("status") in ("ACTIVE", "WATCHING"):
        out = dict(signal)
        out["status"] = "EXPIRED"
        return out
    return signal


def human_summary(signal: dict[str, Any]) -> str:
    """Plain-words card text (skill §87 style). Frontend may use or replace this."""
    inst = signal.get("instrument", "?")
    decision = signal.get("decision", "NO_TRADE")
    conf = signal.get("confidence_score")
    conf_txt = f"{conf}/100 (evidence alignment, not win probability)" if conf is not None else "n/a (data too thin)"
    lines = [
        f"{inst} — PAPER {decision}",
        f"WHY: {signal.get('primary_reason', '')}",
        f"CONFIDENCE: {conf_txt}",
    ]
    if signal.get("invalidation"):
        lines.append(f"INVALIDATION: {signal['invalidation']}")
    if signal.get("valid_until_ist"):
        lines.append(f"VALID UNTIL: {signal['valid_until_ist']} IST")
    if signal.get("risk_flags"):
        lines.append("FLAGS: " + ", ".join(signal["risk_flags"]))
    lines.append(f"STATUS: {signal.get('status')}")
    lines.append("Paper research only. No orders. UNVALIDATED.")
    return "\n".join(lines)
