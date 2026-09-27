"""Entry-location policy: how far a signal's entry is stretched from the imbalance it came out of.

Legacy entries chase the top of big impulse candles and give 4-5 points back to the retrace into the
imbalance. Every strategy card therefore declares an `entry_policy`:

    chase                 enter at the signal (what legacy does)
    pullback_limit        rest a limit at `zone` (fvg | candle_50 | poc) for `timeout_bars` closed 1m bars
    wait_consolidation    wait for the impulse to base (`timeout_bars` optional)
    max_stretch_atr       optional per-card cap; else the basket's `entry_location.max_stretch_atr`

`measure` computes, for one signal, each zone on today's index 1m bars that CLOSED before the signal
tick, and the signed distance of the index price from it in ATR (Wilder, closed bars). Positive =
price is stretched beyond the zone in the trade's direction (above it for CE, below it for PE).
`entry_distance_atr` / `zone_type` is the nearest zone behind the price (distance >= 0); zones still
ahead of the price (negative) are logged but never picked. `verdict` turns that into ENTER /
VETO_STRETCHED / WAIT_PULLBACK / WAIT_CONSOLIDATION / CHASE_NOT_ALLOWED / NO_ZONE_BEHIND /
DATA_INSUFFICIENT. Nothing is enforced: the basket is shadow only.
Thresholds are placeholders in config/baskets/<market>.yaml until research round 10 sets them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from analysts.shadow import wilder_atr  # type: ignore[import-untyped]

POLICIES = ("chase", "pullback_limit", "wait_consolidation")
ZONES = ("fvg", "candle_50", "poc")
MODES = ("log_only", "prefer", "require")
ENTRY_KEYS = {"mode", "max_stretch_atr", "chase_weight_mult", "atr_period", "lookback_bars",
              "impulse_atr_mult", "poc_bucket_atr"}
POLICY_KEYS = {"kind", "zone", "timeout_bars", "max_stretch_atr"}


def closed_bars(bars: Sequence[Mapping[str, Any]], now_ts: int) -> list[Mapping[str, Any]]:
    """1m bars (ts = minute start) that closed at or before ``now_ts``; the forming minute is dropped."""
    return [b for b in bars if int(b["ts"]) + 60 <= int(now_ts)]


def last_fvg(bars: Sequence[Mapping[str, Any]], side: str) -> tuple[float, float] | None:
    """Most recent 3-candle fair-value gap in the trade's direction: (low, high) of the gap."""
    for i in range(len(bars) - 1, 1, -1):
        a, c = bars[i - 2], bars[i]
        if side == "CE" and float(a["high"]) < float(c["low"]):
            return float(a["high"]), float(c["low"])
        if side == "PE" and float(a["low"]) > float(c["high"]):
            return float(c["high"]), float(a["low"])
    return None


def impulse_mid(bars: Sequence[Mapping[str, Any]], side: str, atr: float, mult: float) -> tuple[float, float] | None:
    """50% of the most recent impulse candle (range >= mult x ATR, body in the trade's direction)."""
    for b in reversed(bars):
        o, h, lo, c = (float(b[k]) for k in ("open", "high", "low", "close"))
        if h - lo >= mult * atr and ((side == "CE" and c > o) or (side == "PE" and c < o)):
            mid = (h + lo) / 2.0
            return mid, mid
    return None


def point_of_control(bars: Sequence[Mapping[str, Any]], bucket: float) -> tuple[float, float] | None:
    """Session price bucket with the most volume (bar count when the index tape has no volume)."""
    if not bars or bucket <= 0:
        return None
    use_volume = all((b.get("volume") or 0) > 0 for b in bars)
    hist: dict[int, float] = {}
    for b in bars:
        k = int(float(b["close"]) // bucket)
        hist[k] = hist.get(k, 0.0) + (float(b["volume"]) if use_volume else 1.0)
    k = max(sorted(hist), key=lambda key: hist[key])  # ties: lowest bucket (sorted first)
    return k * bucket, (k + 1) * bucket


def stretch_atr(price: float, zone: tuple[float, float], side: str, atr: float) -> float:
    """Signed distance from the zone's nearest edge, in ATR: positive = beyond it in the trade's direction
    (the run since the imbalance), negative = the zone is still ahead of the price. Inside the zone = 0."""
    lo, hi = zone
    if lo <= price <= hi:
        return 0.0
    if side == "CE":
        d = price - hi if price > hi else price - lo
    else:
        d = lo - price if price < lo else hi - price
    return round(d / atr, 4)


def measure(bars_1m: Sequence[Mapping[str, Any]], now_ts: int, price: float, side: str,
            cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Zones and entry distance for one signal, from bars closed before ``now_ts`` only."""
    today = closed_bars(bars_1m, now_ts)
    recent = today[-int(cfg["lookback_bars"]):]
    atr = wilder_atr(today[-(int(cfg["atr_period"]) * 3):], int(cfg["atr_period"]))
    out: dict[str, Any] = {"price": float(price), "side": side, "atr": None if atr is None else round(atr, 4),
                           "n_bars": len(today), "zones": {z: None for z in ZONES},
                           "entry_distance_atr": None, "zone_type": None}
    if atr is None or atr <= 0 or side not in ("CE", "PE"):
        return out
    found = {
        "fvg": last_fvg(recent, side),
        "candle_50": impulse_mid(recent, side, atr, float(cfg["impulse_atr_mult"])),
        "poc": point_of_control(today, float(cfg["poc_bucket_atr"]) * atr),
    }
    for name in ZONES:
        z = found[name]
        if z is not None:
            out["zones"][name] = {"lo": round(z[0], 2), "hi": round(z[1], 2),
                                  "distance_atr": stretch_atr(float(price), z, side, atr)}
    # Only zones behind the price (distance >= 0) are where the move came from; a negative distance is
    # a zone still ahead of the price, which says nothing about how far this entry has run.
    behind = [(v["distance_atr"], name) for name, v in out["zones"].items() if v is not None and v["distance_atr"] >= 0]
    if behind:
        out["entry_distance_atr"], out["zone_type"] = min(behind)
    return out


def verdict(policy: Mapping[str, Any], sig: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """What a card's entry policy says about this signal. Logged only; never enforced here."""
    kind = policy["kind"]
    cap = policy.get("max_stretch_atr")
    cap = cfg.get("max_stretch_atr") if cap is None else cap
    zone = policy.get("zone")
    dist = sig["entry_distance_atr"] if zone is None else (sig["zones"].get(zone) or {}).get("distance_atr")
    out = {"policy": kind, "zone": zone or sig["zone_type"], "timeout_bars": policy.get("timeout_bars"),
           "max_stretch_atr": cap, "distance_atr": dist, "stretched": None, "action": "ENTER",
           "veto_reason": None, "enforced": False}
    if kind == "chase" and cfg["mode"] == "require":
        out.update(action="CHASE_NOT_ALLOWED", veto_reason="CHASE_POLICY_NOT_ALLOWED")
        return out
    if sig["atr"] is None:
        out["action"] = "DATA_INSUFFICIENT"
        return out
    if dist is None or dist < 0:  # no zone behind the price to measure the run from (or the card's zone is ahead)
        out["action"] = "NO_ZONE_BEHIND"
        return out
    out["stretched"] = cap is not None and dist > cap
    if not out["stretched"]:
        return out
    if kind == "pullback_limit":
        z = sig["zones"][zone]
        out.update(action="WAIT_PULLBACK", limit_index_level=z["hi"] if sig["side"] == "CE" else z["lo"])
    elif kind == "wait_consolidation":
        out["action"] = "WAIT_CONSOLIDATION"
    else:
        out.update(action="VETO_STRETCHED",
                   veto_reason=f"STRETCHED_ENTRY: {dist} ATR beyond {out['zone']} > max {cap}")
    return out
