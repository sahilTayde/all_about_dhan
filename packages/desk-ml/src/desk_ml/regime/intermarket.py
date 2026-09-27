"""Daily / weekly intermarket regime (risk_on / risk_off / neutral / unknown) and the boss overlay.

Inputs are whatever the data-recorder's global fetcher left in `data/recon/global_markets/YYYYMMDD.jsonl`
(USDINR, crude, US index futures or ETF, VIX). For session D only files dated before D are read, so
the regime is known pre-market. A missing input is dropped from the score; with no inputs at all
the regime is `unknown` and the overlay does nothing.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

RISK_ON = "risk_on"
RISK_OFF = "risk_off"
NEUTRAL = "neutral"
UNKNOWN = "unknown"

DEFAULT_INPUTS: dict[str, dict[str, Any]] = {
    "usdinr": {"symbols": ["USDINR=X", "USDINR"], "risk_off_when": "up", "dead_band_pct": 0.15},
    "crude": {"symbols": ["CL=F", "BZ=F", "CRUDE"], "risk_off_when": "up", "dead_band_pct": 1.0},
    "us_futures": {"symbols": ["ES=F", "NQ=F", "SPY"], "risk_off_when": "down", "dead_band_pct": 0.4},
    "vix": {"symbols": ["^VIX", "INDIAVIX", "^INDIAVIX"], "risk_off_when": "up", "dead_band_pct": 5.0},
}


def load_daily_closes(folder: Path, before: str) -> dict[str, list[tuple[str, float]]]:
    """{symbol: [(YYYY-MM-DD, close), ...]} from files dated strictly before `before` (last print per day)."""
    out: dict[str, dict[str, float]] = {}
    folder = Path(folder)
    if not folder.is_dir():
        return {}
    cutoff = before.replace("-", "")
    for path in sorted(folder.glob("*.jsonl")):
        stem = path.stem
        if len(stem) != 8 or not stem.isdigit() or stem >= cutoff:
            continue
        day = f"{stem[:4]}-{stem[4:6]}-{stem[6:]}"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                rec = json.loads(line)
                sym, close = str(rec["symbol"]), float(rec["close"])
            except (ValueError, KeyError, TypeError):
                continue
            if math.isfinite(close) and close > 0:
                out.setdefault(sym, {})[day] = close
    return {s: sorted(d.items()) for s, d in out.items()}


def _component(series: Sequence[tuple[str, float]], lag: int, spec: Mapping[str, Any], band_scale: float) -> Optional[dict[str, Any]]:
    if len(series) <= lag:
        return None
    last, ref = series[-1][1], series[-1 - lag][1]
    chg = (last / ref - 1.0) * 100.0
    band = float(spec.get("dead_band_pct", 0.0)) * band_scale
    sign = 1 if spec.get("risk_off_when", "up") == "up" else -1
    score = 0 if abs(chg) < band else (sign if chg > 0 else -sign)
    return {"as_of": series[-1][0], "chg_pct": round(chg, 4), "score": score}


def intermarket_regime(
    closes: Mapping[str, Sequence[tuple[str, float]]],
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Daily (last session vs the one before) and weekly (vs `weekly_sessions` back) regimes."""
    cfg = dict(cfg or {})
    inputs = cfg.get("inputs") or DEFAULT_INPUTS
    n_week = int(cfg.get("weekly_sessions", 5))
    off_at, on_at = float(cfg.get("risk_off_score", 0.5)), float(cfg.get("risk_on_score", -0.5))
    out: dict[str, Any] = {"inputs_used": [], "inputs_missing": []}
    for horizon, lag, scale in (("daily", 1, 1.0), ("weekly", n_week, math.sqrt(n_week))):
        comps: dict[str, Any] = {}
        for name, spec in inputs.items():
            series = next((closes[s] for s in spec.get("symbols") or () if len(closes.get(s) or ()) > lag), None)
            comp = _component(series, lag, spec, scale) if series else None
            if comp is not None:
                comps[name] = comp
        if comps:
            score = sum(c["score"] for c in comps.values()) / len(comps)
            label = RISK_OFF if score >= off_at else RISK_ON if score <= on_at else NEUTRAL
        else:
            score, label = None, UNKNOWN
        out[horizon] = {"label": label, "score": None if score is None else round(score, 4), "components": comps}
        if horizon == "daily":
            out["inputs_used"] = sorted(comps)
            out["inputs_missing"] = sorted(set(inputs) - set(comps))
    return out


def regime_for_session(root: Path, session_date: str, cfg: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    cfg = dict(cfg or {})
    folder = Path(cfg.get("dir") or "data/recon/global_markets")
    if not folder.is_absolute():
        folder = Path(root) / folder
    rep = intermarket_regime(load_daily_closes(folder, session_date), cfg)
    rep["session_date"] = session_date
    return rep


def overlay_decision(
    side: Optional[str],
    regime: Optional[Mapping[str, Any]],
    cfg: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Side preference / veto / size multiplier for one proposed ticket. Disabled = pass-through."""
    cfg = dict(cfg or {})
    out = {"enabled": bool(cfg.get("enabled", False)), "regime": UNKNOWN, "veto": False, "size_mult": 1.0,
           "prefer": None, "reason": None}
    if not out["enabled"] or not regime:
        return out
    use = str(cfg.get("use", "weekly"))
    daily = (regime.get("daily") or {}).get("label", UNKNOWN)
    weekly = (regime.get("weekly") or {}).get("label", UNKNOWN)
    if use == "daily":
        label = daily
    elif use == "either":
        label = RISK_OFF if RISK_OFF in (daily, weekly) else RISK_ON if RISK_ON in (daily, weekly) else daily
    else:
        label = weekly
    out["regime"] = label
    rule = cfg.get(label) if label in (RISK_ON, RISK_OFF) else None
    if not isinstance(rule, Mapping):
        return out
    prefer = rule.get("prefer")
    out["prefer"] = prefer
    if side in ("CE", "PE"):
        out["size_mult"] = float(rule.get("size_mult", 1.0))
        if prefer in ("CE", "PE") and side != prefer and rule.get("veto_other_side"):
            out["veto"] = True
            out["reason"] = f"OVERLAY_{label.upper()}_PREFER_{prefer}"
    return out
