"""Q01 ITM100 v1.1 (paper desk) + Q01_T15 shadow. Pure python (desk venv has no pandas). PAPER ONLY, orders refused.

Spec: research/lab/2026-10-12_q01_forward_spec/FORWARD_SPEC.md (v1, sha 8bca2921...) + FORWARD_SPEC_v1.1.md (stop from REAL entry),
SHADOW_Q01_T15.md (sha a1867606...). Port of 2026-10-13_q01_exits/run_a.py sim() (PLAIN = v1.1, T15 = shadow), checked on its 73 real-price trades.
- Filter (pre-open): V1 = last India VIX close before today, V2 = the one before. pct = share of the 250 closes before V1 that are < V1;
  chg = V1/V2 - 1. Armed iff pct >= 0.80 and chg > 0.02.
- Open = official NSE open (pre-open value: last raw_frames NIFTY sid 13 tick with recv_ts in [09:08, 09:15), fallback depth_quotes
  NSE_IDX:NIFTY ltp). Missing -> DATA_MISSING. Never the first tick at/after 09:15.
- Signal at the 10:00 close S10: mv = S10 - open; mv > 0 -> PE, mv < 0 -> CE (fade); 0 -> none.
- Strike = round(S10/50)*50 -/+ 100 (ITM100). Entry E = open of the first option bar in 10:01..10:03 + 1 tick.
- Stop: D = 0.3*E/0.54 index pts from S10, checked on 1-min NIFTY closes from 10:01; exit = option close of that minute - 2 ticks
  (last bar up to 3 min back). T15 only: target = E + 1.5*(0.3*E) on 1-min option closes, exit close - 1 tick; stop checked first.
- Time exit: the 10:21 minute (21 min after the 10:00 signal) close - 1 tick."""
from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from typing import Any, Optional

TICK = 0.05
SIG_M = 600  # 10:00
LAST_ENTRY_M = 603
TIME_EXIT_AFTER = 21
STOP_FRAC = 0.3
IDX_PER_PREM = 0.54
T15_MULT = 1.5


def hm(m: int) -> str:
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def vix_filter(closes: list, day: str) -> dict[str, Any]:
    """closes = [(YYYY-MM-DD, close), ...] (any order). Uses only closes dated before `day`."""
    v = sorted((d, float(c)) for d, c in closes if d < day)
    if len(v) < 3:
        return {"armed": False, "status": "DATA_MISSING", "reason": "VIX history"}
    vv = [c for _, c in v]
    j = len(vv) - 1
    h = vv[max(0, j - 250):j]
    pct = sum(1 for x in h if x < vv[j]) / len(h)
    chg = vv[j] / vv[j - 1] - 1
    return {"armed": pct >= 0.80 and chg > 0.02, "pct": round(pct, 4), "chg": round(chg, 5), "v1": vv[j], "v1_date": v[-1][0],
            "status": "OK"}


def official_open(tape_day_dir: Path) -> tuple[Optional[float], str]:
    """Pre-open NIFTY value from the V2 recorder tape (raw_frames, then depth_quotes)."""
    pre = None
    p = Path(tape_day_dir) / "raw_frames.jsonl"
    if p.is_file():
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if '"recv_ts"' not in line:
                    continue
                o = json.loads(line)
                ts = str(o.get("recv_ts") or "")[11:19]
                if ts >= "09:15:00":
                    break
                if ts < "09:08:00":
                    continue
                b = base64.b64decode(o["raw_b64"]); i = 0
                while i + 8 <= len(b):
                    code, ln, seg, sid = struct.unpack_from("<BHBi", b, i)
                    if ln <= 0:
                        break
                    if code == 2 and seg == 0 and sid == 13 and ln >= 16:
                        pre = round(float(struct.unpack_from("<f", b, i + 8)[0]), 2)
                    i += ln
    if pre is not None:
        return pre, "raw_frames_preopen"
    p = Path(tape_day_dir) / "depth_quotes.jsonl"
    v = None
    if p.is_file():
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if '"NSE_IDX:NIFTY"' not in line:
                    continue
                o = json.loads(line)
                t = (o["payload"].get("exchange_ts") or o["timestamp"])[11:19]
                if t >= "09:15:00":
                    break
                if t >= "09:08:00" and o["payload"].get("ltp") is not None:
                    v = round(float(o["payload"]["ltp"]), 2)
    return (v, "depth_quotes_preopen") if v is not None else (None, "OPEN_MISSING")


def side_strike(open_px: float, s10: float) -> Optional[tuple[int, str, int]]:
    mv = s10 - open_px
    if mv == 0:
        return None
    sg = -1 if mv > 0 else 1
    atm = int(round(s10 / 50) * 50)
    return sg, ("CE" if sg > 0 else "PE"), atm - 100 * sg


def _lastbar(opt: dict, m: int, em: int) -> Optional[float]:
    for mm in range(m, m - 4, -1):
        if mm in opt and mm >= em:
            return opt[mm][1]
    return None


def simulate(*, sg: int, s10: float, idx: dict, opt: dict, variant: str = "PLAIN", now_m: Optional[int] = None,
             sig_m: int = SIG_M) -> dict[str, Any]:
    """idx = {minute: NIFTY 1m close}, opt = {minute: (open, close)} of the traded contract. now_m = last COMPLETE minute
    (live); None = full history. Returns status OPEN / CLOSED / PENDING_ENTRY / DATA_MISSING."""
    last = now_m if now_m is not None else 10 ** 9
    em = next((m for m in (sig_m + 1, sig_m + 2, sig_m + 3) if m in opt and m <= last), None)
    if em is None:
        return {"status": "PENDING_ENTRY" if last < sig_m + 3 else "DATA_MISSING", "reason": "no option bar 10:01-10:03"}
    E = round(opt[em][0] + TICK, 2)
    D = STOP_FRAC * E / IDX_PER_PREM
    R = STOP_FRAC * E
    tgt = round(E + T15_MULT * R, 2) if variant == "T15" else None
    out = {"entry_min": hm(em), "entry_px": E, "stop_dist_idx": round(D, 2), "index_stop": round(s10 - sg * D, 2), "R_prem": round(R, 2),
           "target_px": tgt, "planned_exit": hm(sig_m + TIME_EXIT_AFTER)}
    for m in sorted(k for k in idx if k > sig_m):
        if m > 915 or m > last:
            break
        if sg * (idx[m] - s10) <= -D:
            p = _lastbar(opt, m, em)
            return dict(out, status="CLOSED" if p is not None else "DATA_MISSING", exit_min=hm(m), exit_reason="STOP",
                        exit_px=None if p is None else round(max(p - 2 * TICK, 0.05), 2))
        if tgt is not None and m in opt and m >= em and opt[m][1] >= tgt:
            return dict(out, status="CLOSED", exit_min=hm(m), exit_reason="TARGET", exit_px=round(max(opt[m][1] - TICK, 0.05), 2))
        if m - sig_m >= TIME_EXIT_AFTER:
            p = _lastbar(opt, m, em)
            return dict(out, status="CLOSED" if p is not None else "DATA_MISSING", exit_min=hm(m), exit_reason="TIME",
                        exit_px=None if p is None else round(max(p - TICK, 0.05), 2))
    mk = max((k for k in opt if em <= k <= last), default=em)
    return dict(out, status="OPEN", mark_min=hm(mk), mark_px=opt[mk][1])
