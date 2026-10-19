"""Causal market-regime tags + narrow-open shadow for paper-extra rows (2026-10-19, Sahil 1:1 02:29 CT). LOGGING ONLY: never used for
admission, exits or P&L. Labels and thresholds are frozen copies of lab/2026-10-19_regime_playbook (regime.py, ER_MED.json, PREREG.md):
- trend_chop: efficiency ratio from the 09:15 open to the signal-minute close; TREND if >= the 2025 median of its time bucket, else CHOP;
  fewer than 5 bars -> TREND if |gap| >= 0.5%.
- side_vs_move: WITH if the trade direction matches (signal close - prior close), else AGAINST.
- vix_bucket: prior India VIX close, percentile vs the 250 closes before it (ties half, >= 100 needed): <1/3 VOL_LO, >2/3 VOL_HI, else VOL_MID.
- gap_bucket: (09:15 open - prior close)/prior close: >= +0.5% GAP_UP, <= -0.5% GAP_DN, else GAP_SMALL.
- or15: 09:15-09:29 high-low vs the median of the prior 20 sessions' or15 (>= 10 sessions needed): >= OR_WIDE, < OR_NARROW; before 09:29 OR_NOTYET.
  or30 (09:15-09:44) is the same rule on a 30-min range; NOT part of the study (extra context, no study label to match).
  The study has no "normal" band, so none is invented here; the ratio is logged for later banding.
- prior_day_type: prior session |close-open|/(high-low) >= 0.5 PD_TREND else PD_RANGE.
- expiry_day: the trade's underlying nearest weekly expiry == today.  time_bucket: T1 <10:00, T2 <11:30, T3 <13:30, else T4 (signal minute).
Missing data -> the field is None and missing[field] holds the reason. Nothing here raises: tag_safe() returns {"error": ...} at worst."""
import json, math
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30)); M0 = 555; NM = 376
VERSION = "regime_tags v1 (lab/2026-10-19_regime_playbook frozen)"
ER_MED = {"T1_0915_1000": 0.233, "T2_1000_1130": 0.114, "T3_1130_1330": 0.076, "T4_1330_1515": 0.06}
GAP_T = 0.005; PD_T = 0.5; OR_N = 20; OR_MIN = 10; VIX_N = 250; VIX_MIN = 100
NARROW_RULE = "opening range 15m < 20d median"
nan = float("nan")
def _fin(x): return x is not None and isinstance(x, (int, float)) and math.isfinite(x)
def tbucket(m): return "T1_0915_1000" if m < 600 else "T2_1000_1130" if m < 690 else "T3_1130_1330" if m < 810 else "T4_1330_1515"
def days_from_dhan(j: dict) -> dict:
    """Dhan intraday 1m json (open/high/low/close/timestamp) -> {day: {minute_index: (o,h,l,c)}} for 09:15..15:30 IST."""
    out = {}
    ts = j.get("timestamp") or []
    for i, t in enumerate(ts):
        try:
            dt = datetime.fromtimestamp(int(t), IST); k = dt.hour * 60 + dt.minute - M0
            if 0 <= k < NM:
                out.setdefault(dt.strftime("%Y-%m-%d"), {})[k] = (float(j["open"][i]), float(j["high"][i]), float(j["low"][i]), float(j["close"][i]))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return out
def _rng(b, upto):
    hs = [b[k][1] for k in range(upto) if k in b]; ls = [b[k][2] for k in range(upto) if k in b]
    return (max(hs) - min(ls)) if hs and ls else None
def _median(v):
    v = sorted(v); n = len(v)
    return None if n == 0 else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)
def vix_pct(vix: list, day: str):
    """vix = [[date, close], ...]. Percentile of the PRIOR close vs the 250 closes before it (ties half). Returns (pct, prior_date) or (None, reason)."""
    s = sorted({d: float(c) for d, c in vix if d < day and _fin(float(c))}.items())
    if not s: return None, "no VIX close before the day"
    d1, v = s[-1]; w = [c for _, c in s[max(0, len(s) - 1 - VIX_N):len(s) - 1]]
    if len(w) < VIX_MIN: return None, f"only {len(w)} VIX closes before {d1} (need {VIX_MIN})"
    return (sum(1 for c in w if c < v) + 0.5 * sum(1 for c in w if c == v)) / len(w), d1
def day_context(bars_by_day: dict, day: str, vix: list, expiry_day, prev_day_expected: str = None) -> dict:
    """Everything known before/at the day level. bars_by_day from days_from_dhan (may hold today partially)."""
    miss = {}; ctx = {"day": day, "missing": miss}
    prior = sorted(d for d in bars_by_day if d < day)
    today = bars_by_day.get(day) or {}
    ctx["today"] = today
    if prior:
        p = bars_by_day[prior[-1]]; ks = sorted(p)
        ctx["prev_day"] = prior[-1]
        ctx["prev"] = dict(O=p[ks[0]][0], H=max(v[1] for v in p.values()), L=min(v[2] for v in p.values()), C=p[ks[-1]][3])
        if prev_day_expected and prior[-1] != prev_day_expected:
            miss["prev_day"] = f"last index session in data is {prior[-1]}, expected {prev_day_expected}"
    else:
        ctx["prev"] = None; miss["prev"] = "no prior session in index data"
    o15 = [x for x in (_rng(bars_by_day[d], 15) for d in prior[-OR_N:]) if x is not None]
    o30 = [x for x in (_rng(bars_by_day[d], 30) for d in prior[-OR_N:]) if x is not None]
    ctx["or15_med"] = _median(o15) if len(o15) >= OR_MIN else None
    ctx["or30_med"] = _median(o30) if len(o30) >= OR_MIN else None
    if ctx["or15_med"] is None: miss["or15_med"] = f"only {len(o15)} prior sessions with an opening range (need {OR_MIN})"
    try:
        v, info = vix_pct(vix or [], day)
    except Exception as e:  # malformed VIX input
        v, info = None, f"VIX error {type(e).__name__}"
    ctx["vix_pct"] = v
    if v is None: miss["vix"] = info
    else: ctx["vix_prior_date"] = info
    ctx["expiry_day"] = expiry_day
    if expiry_day is None: miss["expiry_day"] = "expiry unknown"
    return ctx
def tag(ctx: dict, signal_m: int, side: str) -> dict:
    """signal_m = IST minute of day of the signal bar (entry is at the next minute's open). side 'CE'/'PE'."""
    miss = dict(ctx.get("missing") or {}); b = ctx.get("today") or {}; j = signal_m - M0; sg = 1 if side == "CE" else -1
    out = {"version": VERSION, "at_signal_minute": f"{signal_m // 60:02d}:{signal_m % 60:02d}", "missing": miss}
    out["time_bucket"] = tbucket(signal_m)
    O0 = b[0][0] if 0 in b else (b[min(b)][3] if b else None)
    cj = b[j][3] if j in b else None
    prev = ctx.get("prev")
    gap = (O0 - prev["C"]) / prev["C"] if (prev and O0 is not None and prev["C"]) else None
    out["gap_pct"] = round(gap * 100, 3) if gap is not None else None
    out["gap_bucket"] = None if gap is None else "GAP_UP" if gap >= GAP_T else "GAP_DN" if gap <= -GAP_T else "GAP_SMALL"
    if gap is None: miss["gap_bucket"] = "no 09:15 open or prior close"
    cl = [b[k][3] for k in range(0, j + 1) if k in b]
    er = None
    if O0 is not None and len(cl) >= 5:
        path = abs(cl[0] - O0) + sum(abs(cl[i + 1] - cl[i]) for i in range(len(cl) - 1))
        er = abs(cl[-1] - O0) / path if path > 0 else 0.0
    out["er"] = round(er, 4) if er is not None else None
    if er is not None: out["trend_chop"] = "TREND" if er >= ER_MED[out["time_bucket"]] else "CHOP"
    elif gap is not None: out["trend_chop"] = "TREND" if abs(gap) >= GAP_T else "CHOP"; out["trend_chop_basis"] = "<5 bars: gap size"
    else: out["trend_chop"] = None; miss["trend_chop"] = "no bars and no gap"
    if cj is not None and prev: out["side_vs_move"] = "WITH" if sg * (cj - prev["C"]) > 0 else "AGAINST"
    else: out["side_vs_move"] = None; miss["side_vs_move"] = "no signal-minute close or prior close"
    v = ctx.get("vix_pct")
    out["vix_pct"] = round(v, 4) if v is not None else None
    out["vix_bucket"] = None if v is None else "VOL_LO" if v < 1 / 3 else "VOL_HI" if v > 2 / 3 else "VOL_MID"
    for nm, n, med in (("or15", 15, ctx.get("or15_med")), ("or30", 30, ctx.get("or30_med"))):
        if j < n - 1: out[nm] = "OR_NOTYET"; out[nm + "_ratio"] = None; continue
        r = _rng(b, n)
        if r is None or med is None or med <= 0:
            out[nm] = None; out[nm + "_ratio"] = None; miss[nm] = "no opening-range bars today" if r is None else "no 20d median"; continue
        out[nm] = "OR_WIDE" if r >= med else "OR_NARROW"; out[nm + "_ratio"] = round(r / med, 3)
    if prev:
        rg = prev["H"] - prev["L"]; out["prior_day_type"] = "PD_TREND" if rg > 0 and abs(prev["C"] - prev["O"]) / rg >= PD_T else "PD_RANGE"
    else: out["prior_day_type"] = None; miss["prior_day_type"] = "no prior session"
    out["expiry_day"] = ctx.get("expiry_day")
    out["cell"] = f"{out['trend_chop']}|{out['side_vs_move']}|{out['vix_bucket']}" if None not in (out["trend_chop"], out["side_vs_move"], out["vix_bucket"]) else None
    return out
def narrow_shadow(reg: dict) -> dict:
    o = (reg or {}).get("or15")
    return {"would_skip": o == "OR_NARROW", "would_halve": o == "OR_NARROW", "rule": NARROW_RULE, "or15": o,
            "basis": "or15 known" if o in ("OR_NARROW", "OR_WIDE") else f"or15 {o}: rule cannot fire"}
def tag_safe(ctx, signal_m, side) -> dict:
    try:
        return tag(ctx, signal_m, side)
    except Exception as e:
        return {"version": VERSION, "error": f"{type(e).__name__}: {e}"}
