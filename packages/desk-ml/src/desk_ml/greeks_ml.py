"""MIX-ML-GREEKS — TOKEN_ML ML-2 paper stand-in. Dhan greeks only. No invent. No promote.

Quant use (Natenberg / McMillan / HAUS STRAT-006 WEAK delta):
- delta: moneyness / skip cheap-delta longs
- IV: do not buy rich vol vs the session (MIX-ALGO-IV-REGIME-HOLD cousin)
- theta: long premium pays decay; skip late-session high |theta|/entry
- gamma: high gamma = path noise; skip if also cheap delta
Side still comes from the dealer/index tape. Greeks do not pick CE vs PE.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Optional, Sequence

FEATURE_SET_VERSION = "ml-greeks-v1"
DELTA_SKIP_BELOW = 0.40
DELTA_PREF_LO = 0.45
IV_RICH_ABS = 20.0
IV_VS_SESSION = 1.15
THETA_BLEED = 0.06
THETA_LATE_MINUTES = 14 * 60  # 14:00 IST
FLAT_IV_CV = 0.04  # std/mean of wing IVs — MIX-ALGO-IV-REGIME-HOLD stub


def _num(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val != 0.0 else None


def wing_ivs(wing_quotes: Optional[dict]) -> list[float]:
    if not isinstance(wing_quotes, dict):
        return []
    out: list[float] = []
    for cell in wing_quotes.values():
        if not isinstance(cell, dict):
            continue
        for key in ("ce_iv", "pe_iv"):
            val = _num(cell.get(key))
            if val is not None and val > 0:
                out.append(val)
    return out


def session_iv_median(prior: Sequence[float]) -> Optional[float]:
    vals = [float(x) for x in prior if x is not None]
    if len(vals) < 5:
        return None
    return float(median(vals))


def flat_iv_surface(ivs: Sequence[float]) -> bool:
    """Quiet/flat IV book → HOLD new long premium (catalog MIX-ALGO-IV-REGIME-HOLD)."""
    vals = [float(x) for x in ivs if x and x > 0]
    if len(vals) < 6:
        return False
    mean = sum(vals) / len(vals)
    if mean <= 0:
        return False
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    cv = (var ** 0.5) / mean
    return cv < FLAT_IV_CV


def score_greeks_ticket(
    *,
    side: Optional[str],
    entry: Optional[float],
    delta: Optional[float] = None,
    gamma: Optional[float] = None,
    theta: Optional[float] = None,
    iv: Optional[float] = None,
    session_iv: Optional[float] = None,
    minutes_ist: Optional[int] = None,
    wing_iv_list: Optional[Sequence[float]] = None,
) -> dict[str, Any]:
    """TAKE or HOLD. Missing greeks → skip this book (do not clone dealer)."""
    notes: list[str] = []
    if side not in {"CE", "PE"}:
        return {"take": False, "reason": "NO_SIDE", "feature_set": FEATURE_SET_VERSION, "notes": notes}
    if delta is None and iv is None and theta is None:
        return {
            "take": False,
            "reason": "GREEKS_MISSING",
            "feature_set": FEATURE_SET_VERSION,
            "notes": ["Dhan chain greeks/IV not on this tick — DATA_INSUFFICIENT for MIX-ML-GREEKS"],
        }
    if delta is not None and abs(float(delta)) < DELTA_SKIP_BELOW:
        return {
            "take": False,
            "reason": "DELTA_TOO_LOW",
            "feature_set": FEATURE_SET_VERSION,
            "notes": [f"|delta|={delta} < {DELTA_SKIP_BELOW} (HAUS ~40d adverse)"],
        }
    if delta is not None and abs(float(delta)) < DELTA_PREF_LO:
        notes.append(f"|delta|={delta} below {DELTA_PREF_LO} pref band")
        return {
            "take": False,
            "reason": "DELTA_OTM_BAND",
            "feature_set": FEATURE_SET_VERSION,
            "notes": notes,
        }
    if iv is not None and float(iv) >= IV_RICH_ABS:
        return {
            "take": False,
            "reason": "IV_RICH_ABS",
            "feature_set": FEATURE_SET_VERSION,
            "notes": [f"IV={iv} ≥ {IV_RICH_ABS} — do not buy rich vol (Natenberg)"],
        }
    if iv is not None and session_iv is not None and session_iv > 0 and float(iv) >= float(session_iv) * IV_VS_SESSION:
        return {
            "take": False,
            "reason": "IV_RICH_VS_SESSION",
            "feature_set": FEATURE_SET_VERSION,
            "notes": [f"IV={iv} vs session median {session_iv}"],
        }
    if wing_iv_list and flat_iv_surface(wing_iv_list):
        return {
            "take": False,
            "reason": "IV_FLAT_REGIME_HOLD",
            "feature_set": FEATURE_SET_VERSION,
            "notes": ["flat wing IV surface — MIX-ALGO-IV-REGIME-HOLD stub"],
        }
    if (
        theta is not None
        and entry
        and float(entry) > 0
        and abs(float(theta)) / float(entry) >= THETA_BLEED
        and minutes_ist is not None
        and int(minutes_ist) >= THETA_LATE_MINUTES
    ):
        return {
            "take": False,
            "reason": "THETA_LATE_BLEED",
            "feature_set": FEATURE_SET_VERSION,
            "notes": ["|theta|/entry high after 14:00 IST — long premium pays decay"],
        }
    if gamma is not None and delta is not None and float(gamma) >= 0.01 and abs(float(delta)) < 0.48:
        notes.append("high gamma + mid delta: keep path stop (already on ticket)")
    return {
        "take": True,
        "reason": None,
        "feature_set": FEATURE_SET_VERSION,
        "notes": notes,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "iv": iv,
    }
