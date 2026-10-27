"""Exit-status labels + shadow overlays for paper-extra rows (2026-10-19, Sahil 'your decision' 02:58 CT). DISPLAY / LOGGING ONLY:
nothing here is read by admission, exits, the cap, the premium limit or P&L. Definitions are frozen copies of
research/lab/2026-10-19_giveback_forensics (REPORT.md "Exit-status labels", PREREG.md DR / TS, labels.py, score.py).

Exit status (per OPEN trade, each cycle and each live-guard tick):
  REVERSING  if (peak gain >= +15% and price <= entry + 0.60 x (peak - entry))   [gave back >= 40% of the peak gain]
             or the index crossed VWAP against the trade since entry (on our side at the signal minute, on the wrong side now)
  FADING     if (peak gain >= +10% and price <= entry + 0.80 x (peak - entry))   [gave back >= 20%]
             or (3-min index slope against the trade and premium 3-min change < 0)
  HEALTHY    otherwise.
  VWAP = running mean of the index typical price (H+L+C)/3 from 09:15 (TWAP proxy; the index has no volume).
  Slopes in bps of the index, signed so + = the trade's direction (CE up, PE down). Index minute = latest complete 1m bar <= now.
Shadow overlays (never applied):
  T50 : same stop 30% / trail (BE at +30%, then HW x 0.70), no time close, target 50%, on the 1m-close path (fill next minute open).
  TS  : target 50% if trend morning (09:15-09:44 move >= 20.7 bps AND efficiency >= 0.196, signal at/after 09:45) OR expiry day
        OR entry before 10:00 OR entry at/after 13:30 IST; else 60%. Same path rules.
  BASE60: the live rule (60%) on the same 1m-close path, so T50/TS compare like for like.
  DR  : after a giveback trade (1m-close peak >= +15%, closed at a loss after 1.5x charges) has EXITED today, a later entry is a
        'would skip' unless at its signal minute the 10-min index slope is with the trade (> 0) AND the index is on the trade's side of VWAP.
  CHASE8 (2026-10-22, Sahil 'all pending items now'): would skip if the option premium rose > 8% on the signal candle
        (signal-minute close / signal-minute open - 1 > 0.08). Would-have result = not traded (0) vs the actual trade.
  BE10  (2026-10-22): same path as BASE60 but the stop moves to entry (break-even) once the 1m close reaches +10%.
Every public function is wrapped by the runner; a failure yields {"error": ...}, never a raise into the desk path."""
import math
VERSION = "shadow_overlays v2 (v1 lab/2026-10-19_giveback_forensics frozen + CHASE8/BE10 2026-10-22)"
CHASE8_RISE, BE10_AT = 0.08, 0.10
M0 = 555; SAFE_M = 915
STOP, TARGET = 0.30, 0.60
MED_M30, MED_EFF = 20.7, 0.196          # 2025 medians, frozen (PREREG.md)
REV_GB, FAD_GB = 0.60, 0.80             # price <= entry + x * (peak - entry)
REV_UP, FAD_UP = 0.15, 0.10


def _fin(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


# ---------------- index helpers; idx = {minute_index k (minute - 555): (o, h, l, c)} for today
def close_at(idx, k):
    """last close at or before k (same back-search as the lab harness)"""
    k = max(0, k)
    while k > 0 and k not in idx:
        k -= 1
    v = idx.get(k)
    return v[3] if v else None


def twap_at(idx, k):
    s = n = 0
    for j in range(0, k + 1):
        v = idx.get(j)
        if v:
            s += (v[1] + v[2] + v[3]) / 3; n += 1
    return s / n if n else None


def slope_bps(idx, k, look, sg):
    a, b = close_at(idx, k), close_at(idx, k - look)
    return sg * (a / b - 1) * 1e4 if _fin(a) and _fin(b) and b else None


def morning(idx):
    """first-30-min move (bps vs the 09:15 open) and efficiency |net| / sum|1m moves| over 09:15-09:44 closes"""
    ks = sorted(k for k in idx if k < 30)
    if len(ks) <= 5:
        return None, None
    o0 = idx[min(idx)][0]; c = [idx[k][3] for k in ks]
    path = sum(abs(c[i] - c[i - 1]) for i in range(1, len(c)))
    return abs(c[-1] - o0) / o0 * 1e4, (abs(c[-1] - c[0]) / path if path > 0 else None)


# ---------------- exit status (pure)
def status(p0, px, peak, prem_3ago, sg, idx, k_now, k_sig, held_min=None):
    """p0 entry, px price now, peak = highest price since entry (>= p0), prem_3ago = premium close 3 min before px (or None),
    sg +1 CE / -1 PE, idx today's index bars, k_now = index minute now, k_sig = signal minute (entry - 1). Returns the display dict."""
    p0 = float(p0); px = float(px); peak = max(float(peak), p0); g = peak / p0 - 1
    i, ie = close_at(idx, k_now), close_at(idx, k_sig)
    tw, tw0 = twap_at(idx, k_now), twap_at(idx, k_sig)
    s3, s10 = slope_bps(idx, k_now, 3, sg), slope_bps(idx, k_now, 10, sg)
    prem3 = (px / prem_3ago - 1) if _fin(prem_3ago) and prem_3ago > 0 else None
    side = None if not (_fin(i) and _fin(tw)) else ("WITH" if sg * (i - tw) >= 0 else "AGAINST")
    cross = bool(_fin(ie) and _fin(tw0) and _fin(i) and _fin(tw) and sg * (ie - tw0) >= 0 and sg * (i - tw) < 0)
    why = []
    if g >= REV_UP and px <= p0 + REV_GB * (peak - p0):
        why.append("gave back >=40% of a >=15% peak")
    if cross:
        why.append("index crossed VWAP against the trade")
    if why:
        lab = "REVERSING"
    else:
        if g >= FAD_UP and px <= p0 + FAD_GB * (peak - p0):
            why.append("gave back >=20% of a >=10% peak")
        if _fin(s3) and s3 < 0 and _fin(prem3) and prem3 < 0:
            why.append("index 3-min move against + premium falling")
        lab = "FADING" if why else "HEALTHY"
    r = lambda x, n=2: round(x, n) if _fin(x) else None
    return {"version": VERSION, "label": lab, "reasons": why, "gain_now_pct": r((px / p0 - 1) * 100), "peak_gain_pct": r(g * 100),
            "peak_px": r(peak), "index_vs_entry_bps": r(sg * (i / ie - 1) * 1e4 if _fin(i) and _fin(ie) and ie else None, 1),
            "slope3_bps": r(s3, 1), "slope10_bps": r(s10, 1), "premium_3min_pct": r(prem3 * 100 if _fin(prem3) else None),
            "vwap_side": side, "vwap": r(tw), "index": r(i), "minutes_held": held_min, "display_only": True}


# ---------------- shadow targets / DR
def path_1m(ob, em, p0, now_m, target, be_at=None):
    """same rules as runner.price_exit_path (from_m=None) with a different target; ob = {minute: (open, close)}.
    be_at (e.g. 0.10): once the 1m close reaches entry x (1 + be_at), the stop is at least entry (BE10 overlay)."""
    S = STOP; stop = p0 * (1 - S); tgt = p0 * (1 + target); hw = p0
    for m in range(em, now_m + 1):
        if m not in ob:
            continue
        c = ob[m][1]; hw = max(hw, c)
        if hw >= p0 * (1 + S):
            stop = max(stop, p0, hw * (1 - S))
        elif be_at is not None and hw >= p0 * (1 + be_at):
            stop = max(stop, p0)
        why = ("STOP" if c <= stop and stop < p0 else ("BE" if hw < p0 * (1 + S) else "TRAIL") if c <= stop
               else "TARGET" if c >= tgt else None)
        if why:
            fill = next(((m2, ob[m2][0]) for m2 in (m + 1, m + 2, m + 3) if m2 in ob), None)
            if fill is None and now_m >= m + 3:
                fill = (m, c)
            if fill is None or fill[0] > now_m:
                return dict(status="OPEN", hw=hw)
            return dict(status="CLOSED", exit_m=fill[0], exit_px=fill[1], why=why, hw=hw)
    return dict(status="OPEN", hw=hw)


def ts_target(idx, sig_m, entry_m, expiry_day):
    m30, eff = morning(idx)
    trend = sig_m >= 585 and _fin(m30) and _fin(eff) and m30 >= MED_M30 and eff >= MED_EFF
    why = [w for w, c in (("trend morning", trend), ("expiry day", bool(expiry_day)), ("entry before 10:00", entry_m < 600),
                          ("entry at/after 13:30", entry_m >= 810)) if c]
    return (0.50 if why else 0.60), why, (round(m30, 1) if _fin(m30) else None), (round(eff, 3) if _fin(eff) else None)


def dr_ok(idx, sig_m, sg):
    k = sig_m - M0; s10 = slope_bps(idx, k, 10, sg); i = close_at(idx, k); tw = twap_at(idx, k)
    ok = bool(_fin(s10) and s10 > 0 and _fin(i) and _fin(tw) and sg * (i - tw) > 0)
    return ok, (round(s10, 1) if _fin(s10) else None), (None if not (_fin(i) and _fin(tw)) else ("WITH" if sg * (i - tw) > 0 else "AGAINST"))


def dr_flags(trades):
    """trades: list of dict(key, entry_m, sig_m, exit_m or None, giveback bool, ok bool, ok_s10, ok_side) for today's booked trades.
    Same order and rule as the lab (entry minute, signal minute): skipped trades never count as givebacks."""
    out = {}; gbx = []
    for t in sorted(trades, key=lambda t: (t["entry_m"], t["sig_m"])):
        prior = [x for x in gbx if x < t["entry_m"]]
        skip = bool(prior) and not t["ok"]
        out[t["key"]] = {"would_skip": skip, "after_giveback_exit": bool(prior), "slope10_bps": t.get("ok_s10"), "vwap_side": t.get("ok_side"),
                         "rule": "after a giveback exit today: need 10-min index slope with the trade and index on our side of VWAP"}
        if not skip and t.get("giveback") and t.get("exit_m") is not None:
            gbx.append(t["exit_m"])
    return out


def chase8(ob, sig_m):
    """CHASE8 shadow skip: premium up > 8% on the signal candle (open -> close of the signal minute). Pure."""
    v = ob.get(sig_m)
    if not v or not _fin(v[0]) or not _fin(v[1]) or v[0] <= 0:
        return {"would_skip": None, "signal_candle_pct": None, "rule": "premium > +8% on the signal candle (no bar: unknown)"}
    rise = v[1] / v[0] - 1
    return {"would_skip": bool(round(rise, 9) > CHASE8_RISE), "signal_candle_pct": round(rise * 100, 2),
            "rule": "premium > +8% on the signal candle"}
