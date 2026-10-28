"""FIN1 shadow (paper log only, never an order; founder OK 2026-10-27). Rule frozen from round 2
(teams/06_backtesting/docs/BACKTEST_ROUND2_OPTIONS_1Y.md): at 09:45 IST, RV of 1m spot 09:15..09:45 (annualised
x sqrt(252*375/30)) / mean ATM CE+PE IV; if > THRESH, buy 10 lots ATM CE + ATM PE at 09:46, sell both at 15:15.

Reads the recorder tape data/tape/v2/<day>/ (spot from depth_quotes NSE_IDX/BSE_IDX ltp, options from
quote_snapshots). Fills: ask at the first quote >= 09:46:00, bid at the first quote >= 15:15:00 (last bid if the
strike left the recorded window: forced). Costs = config/charges.yaml x1.5, same formula as opt1y_lab.cost.
The tape has no IV field: IV is Black-Scholes on the 09:45 mid, r=6.5%, T=(calendar days to expiry + 0.5)/365;
that convention gave the same trade/no-trade call as Dhan's IV on 96% of the 492 round-2 days (19 flips).
Every day logs the straddle P&L whether or not FIN1 fires, so `week` can compare signal days to all days.

S2 (round 4, shadow only, added 2026-10-28; BACKTEST_ROUND2_OPTIONS_1Y.md "Round 4"): the other side of the same
signal. If ratio <= THRESH, SELL 10 lots ATM CE + PE at the bid of the first quote >= 09:47:00; buy back at the ask
of the first quote >= the next minute once spot (minute last ltp) is 2 strike steps from the 09:47 spot, else at the
ask nearest 15:15:00. Dev +5.07L (257 trades, p 0.03) but holdout -53k (97): logged to see which regime we are in.

  .venv/bin/python scripts/lab5y/fin1_shadow.py day [YYYY-MM-DD]   # one day -> data/recon/fin1_shadow.jsonl
  .venv/bin/python scripts/lab5y/fin1_shadow.py week [N]           # report on the last N logged days (default 5)
  .venv/bin/python scripts/lab5y/fin1_shadow.py selftest"""
import json, math, random, sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
TAPE = ROOT / "data" / "tape" / "v2"
LOG = ROOT / "data" / "recon" / "fin1_shadow.jsonl"
THRESH = 1.0041598  # dev-period (before 2026-07-27) 70th pct of or_iv, the holdout threshold. Frozen.
LOT = {"NIFTY": 65, "SENSEX": 20}; LOTS = 10; CM = 1.5
TXN = {"NIFTY": 0.000355299, "SENSEX": 0.000325}
STEP = {"NIFTY": 50, "SENSEX": 100}
IDX = {"NSE_IDX:NIFTY": "NIFTY", "BSE_IDX:SENSEX": "SENSEX"}


def cost(b, s, sym):  # == scripts/lab5y/opt1y_lab.py cost()
    q = LOT[sym] * LOTS; bt, st = b * q, s * q; tx = TXN[sym] * (bt + st); se = 1e-6 * (bt + st)
    return CM * (40 + tx + se + 0.18 * (40 + tx + se) + 0.00003 * bt + 0.0015 * st)


def _N(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(S, K, T, v, r, cp):
    d1 = (math.log(S / K) + (r + v * v / 2) * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return S * _N(d1) - K * math.exp(-r * T) * _N(d2) if cp == "CE" else K * math.exp(-r * T) * _N(-d2) - S * _N(-d1)


def implied_vol(p, S, K, T, cp, r=0.065):
    """percent; nan if the price is outside the no-arbitrage band."""
    lo, hi = 1e-4, 5.0
    if T <= 0 or not bs(S, K, T, lo, r, cp) < p < bs(S, K, T, hi, r, cp): return float("nan")
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if bs(S, K, T, mid, r, cp) < p else (lo, mid)
    return (lo + hi) / 2 * 100


def rv_open(closes):
    """annualised % RV from 31 one-minute closes (09:15..09:45), as opt1y_lab.vol_days rv_or (i0=30)."""
    s = sum(math.log(b / a) ** 2 for a, b in zip(closes, closes[1:]))
    return math.sqrt(s * 252 * 375 / (len(closes) - 1)) * 100


def _hms(ts): return ts[11:19]  # "2026-10-22T09:45:12.3+05:30" -> "09:45:12" (tape timestamps are IST)


def load(day):
    d = TAPE / day; spot = {u: {} for u in IDX.values()}  # sym -> {"HH:MM": last ltp in that minute}
    with open(d / "depth_quotes.jsonl", encoding="utf-8") as f:
        for ln in f:
            if "_IDX:" not in ln: continue
            try: e = json.loads(ln); p = e["payload"]
            except (ValueError, KeyError): continue
            u = IDX.get(p.get("instrument_id")); t = _hms(e.get("timestamp", ""))
            if u and p.get("ltp") and "09:15:00" <= t < "15:30:00": spot[u][t[:5]] = float(p["ltp"])
    q = {}  # (sym, strike, side) -> [(hh:mm:ss, bid, ask)]
    with open(d / "quote_snapshots.jsonl", encoding="utf-8") as f:
        for ln in f:
            try: e = json.loads(ln); p = e["payload"]
            except (ValueError, KeyError): continue
            iid = str(p.get("instrument_id", "")).split(":")
            if len(iid) != 5 or iid[1] not in LOT or not p.get("bid") or not p.get("ask") or p.get("stale"): continue
            q.setdefault((iid[1], float(iid[3]), iid[4]), []).append((_hms(e["timestamp"]), float(p["bid"]), float(p["ask"]), iid[2]))
    return spot, q


def _first(xs, t):
    return next((x for x in xs if x[0] >= t), None)


def s2_trade(sym, sp, xs_ce, xs_pe):
    """short straddle 09:47 -> 2-step spot move (next minute) or 15:15. Returns (pnl, why, exit_t) or None."""
    e = {s: _first(xs, "09:47:00") for s, xs in (("CE", xs_ce), ("PE", xs_pe))}
    if None in e.values() or "09:47" not in sp: return None
    s0 = sp["09:47"]; t_exit, why = "15:15:00", "time"
    for m in sorted(k for k in sp if "09:47" <= k < "15:15"):
        if abs(sp[m] - s0) >= 2 * STEP[sym]:
            h, mm = int(m[:2]), int(m[3:]) + 1; t_exit, why = f"{h + mm // 60:02d}:{mm % 60:02d}:00", "spot"; break
    pnl = 0.0
    for s, xs in (("CE", xs_ce), ("PE", xs_pe)):
        if why == "time":
            ex = [x for x in xs if "15:14:00" <= x[0] <= "15:16:00"]
            x = min(ex, key=lambda x: abs(int(x[0][3:5]) * 60 + int(x[0][6:8]) - 900)) if ex else None
        else:
            x = _first(xs, t_exit)
        if x is None: x = xs[-1]; why += "+forced"
        pnl += (e[s][1] - x[2]) * LOT[sym] * LOTS - cost(x[2], e[s][1], sym)
    return round(pnl, 2), why, t_exit


def day_rows(day, spot, q):
    out = []
    for sym in LOT:
        row = dict(day=day, sym=sym, rule="FIN1", thresh=THRESH, shadow_only=True)
        mins = [f"09:{m:02d}" for m in range(15, 46)]; sp = spot.get(sym, {})
        have = [sp[m] for m in mins if m in sp]
        if len(have) < 28 or "09:45" not in sp:  # need the opening half hour on tape
            out.append(dict(row, status="NO_DATA", spot_minutes=len(have))); continue
        S = sp["09:45"]; K = round(S / STEP[sym]) * STEP[sym]; legs = {}
        taped = [k for (u, k, s) in q if u == sym and s == "CE" and (u, k, "PE") in q]  # recorder keeps ATM +-100/200 pts
        if (sym, K, "CE") not in q and taped: K = min(taped, key=lambda k: abs(k - S))
        for side in ("CE", "PE"):
            xs = sorted(q.get((sym, K, side), []))
            pre = [x for x in xs if x[0] < "09:46:00"]; en = [x for x in xs if x[0] >= "09:46:00"]
            if not pre or not en:
                legs = None; break
            ex = [x for x in en if "15:14:00" <= x[0] <= "15:16:00"]  # quote nearest 15:15:00; none = strike left the window
            x = min(ex, key=lambda x: abs(int(x[0][3:5]) * 60 + int(x[0][6:8]) - 900)) if ex else ([x for x in en if x[0] < "15:15:00"] or en)[-1]
            exp = pre[-1][3]; T = ((date.fromisoformat(exp) - date.fromisoformat(day)).days + 0.5) / 365
            legs[side] = dict(iv=implied_vol((pre[-1][1] + pre[-1][2]) / 2, S, K, T, side), entry=en[0][2], entry_t=en[0][0],
                              exit=x[1], exit_t=x[0], forced=not ex, expiry=exp)
        if not legs:
            out.append(dict(row, status="NO_QUOTES", strike=K)); continue
        iv = (legs["CE"]["iv"] + legs["PE"]["iv"]) / 2; rv = rv_open(have)
        pnl = sum((l["exit"] - l["entry"]) * LOT[sym] * LOTS - cost(l["entry"], l["exit"], sym) for l in legs.values())
        ratio = rv / iv if iv == iv else float("nan")
        s2 = s2_trade(sym, sp, sorted(q.get((sym, K, "CE"), [])), sorted(q.get((sym, K, "PE"), [])))
        s2d = dict(s2_signal=bool(ratio <= THRESH), s2_short_pnl_inr=s2[0] if s2 else None, s2_exit=s2[1] if s2 else "NO_QUOTES",
                   s2_pnl_inr=(s2[0] if s2 and ratio <= THRESH else 0.0))
        out.append(dict(row, **s2d, status="OK", spot_0945=S, strike=K, rv_open=round(rv, 2), iv_atm=round(iv, 2),
                        ratio=round(ratio, 4), signal=bool(ratio > THRESH), straddle_pnl_inr=round(pnl, 2),
                        pnl_inr=round(pnl, 2) if ratio > THRESH else 0.0, legs=legs))
    return out


def save(rows):
    keep = [r for r in read_log() if (r["day"], r["sym"]) not in {(x["day"], x["sym"]) for x in rows}]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(r) + "\n" for r in sorted(keep + rows, key=lambda r: (r["day"], r["sym"]))))


def read_log():
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()] if LOG.is_file() else []


def week(n=5, rows=None):
    rows = [r for r in (rows if rows is not None else read_log()) if r.get("status") == "OK"]
    days = sorted({r["day"] for r in rows}); last = set(days[-n:])
    lines = []
    for title, R in ((f"last {len(last)} days", [r for r in rows if r["day"] in last]), ("since start", rows)):
        sig = [r for r in R if r["signal"]]; net = sum(r["pnl_inr"] for r in sig); allp = [r["straddle_pnl_inr"] for r in R]
        # placebo: same number of sym-days drawn at random from all logged sym-days (10k draws)
        rnd = random.Random(7); k = len(sig)
        p = (sum(sum(rnd.sample(allp, k)) >= net for _ in range(10000)) + 1) / 10001 if 0 < k < len(allp) else float("nan")
        lines.append(f"FIN1 shadow, {title} ({len(R)} sym-days): {k} signals, net Rs {net:,.0f}, "
                     f"wins {sum(r['pnl_inr'] > 0 for r in sig)}/{k}; straddle every day Rs {sum(allp):,.0f}; "
                     f"random-days p={p:.3f}")
        s2 = [r for r in R if r.get("s2_signal") and r.get("s2_short_pnl_inr") is not None]
        if any("s2_signal" in r for r in R):
            lines.append(f"S2 shadow (short straddle when RV/IV <= thresh), {title}: {len(s2)} signals, "
                         f"net Rs {sum(r['s2_pnl_inr'] for r in s2):,.0f}, wins {sum(r['s2_pnl_inr'] > 0 for r in s2)}/{len(s2)}")
    for r in sorted(rows, key=lambda r: (r["day"], r["sym"]))[-2 * n:]:
        lines.append(f"  {r['day']} {r['sym']:6s} RV/IV {r['ratio']:.2f} {'SIGNAL' if r['signal'] else 'skip  '} "
                     f"straddle Rs {r['straddle_pnl_inr']:>9,.0f}{' (forced exit)' if any(l['forced'] for l in r['legs'].values()) else ''}")
    lines.append("Paper log only. Adopt only after 40+ trading days with p < 0.05 outside Oct-2026.")
    return "\n".join(lines)


def selftest():
    assert abs(implied_vol(bs(22700, 22700, 5 / 365, 0.14, 0.065, "CE"), 22700, 22700, 5 / 365, "CE") - 14) < 1e-6
    assert implied_vol(0.01, 22700, 22000, 5 / 365, "CE") != implied_vol(0.01, 22700, 22000, 5 / 365, "CE")  # below intrinsic: nan
    assert abs(rv_open([100 * math.exp(0.001 * i) for i in range(31)]) - math.sqrt(30 * 1e-6 * 252 * 375 / 30) * 100) < 1e-9
    assert abs(cost(100, 120, "NIFTY") - 1.5 * (40 + 0.000355299 * 143000 + 0.143 + 0.18 * (40 + 0.000355299 * 143000 + 0.143) + 0.00003 * 65000 + 0.0015 * 78000)) < 1e-6
    sp = {"NIFTY": {f"09:{m:02d}": 22700 * (1 + 0.0004 * (-1) ** m) for m in range(15, 46)}, "SENSEX": {}}
    q = {("NIFTY", 22700.0, s): [("09:45:30", 99.0, 101.0, "2026-10-27"), ("09:46:01", 99.5, 101.5, "2026-10-27"),
                                ("15:15:02", 130.0 if s == "CE" else 60.0, 131.0, "2026-10-27")] for s in ("CE", "PE")}
    n, s = day_rows("2026-10-22", sp, q)
    assert s["status"] == "NO_DATA" and n["status"] == "OK" and n["strike"] == 22700
    exp_pnl = (130 - 101.5) * 650 - cost(101.5, 130, "NIFTY") + (60 - 101.5) * 650 - cost(101.5, 60, "NIFTY")
    assert abs(n["straddle_pnl_inr"] - round(exp_pnl, 2)) < 0.01 and n["pnl_inr"] == (n["straddle_pnl_inr"] if n["signal"] else 0)
    assert "net Rs" in week(5, [n])
    # S2: calm opening (ratio << thresh), spot jumps 2 steps at 10:00 -> buy back at the ask of the first quote >= 10:01
    sp2 = {"NIFTY": dict({f"09:{m:02d}": 22700.0 for m in range(15, 60)}, **{"10:00": 22800.0}), "SENSEX": {}}
    q2 = {("NIFTY", 22700.0, s): [("09:45:30", 99.0, 101.0, "2026-10-27"), ("09:47:00", 100.0, 102.0, "2026-10-27"),
                                 ("10:01:00", 140.0 if s == "CE" else 70.0, 142.0 if s == "CE" else 72.0, "2026-10-27")] for s in ("CE", "PE")}
    m = day_rows("2026-10-22", sp2, q2)[0]
    exp2 = (100 - 142) * 650 - cost(142, 100, "NIFTY") + (100 - 72) * 650 - cost(72, 100, "NIFTY")
    assert m["s2_signal"] and m["s2_exit"] == "spot" and abs(m["s2_pnl_inr"] - round(exp2, 2)) < 0.01, m
    assert "S2 shadow" in week(5, [m])
    print("fin1_shadow selftest OK")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "day"
    if cmd == "selftest": selftest()
    elif cmd == "week": print(week(int(sys.argv[2]) if len(sys.argv) > 2 else 5))
    else:
        day = sys.argv[2] if len(sys.argv) > 2 else datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        if not (TAPE / day / "quote_snapshots.jsonl").is_file():
            print(f"FIN1 {day}: no tape"); sys.exit(0)
        rows = day_rows(day, *load(day)); save(rows)
        for r in rows:
            print(f"FIN1 {day} {r['sym']}: {r['status']}" + (f" RV/IV {r['ratio']:.2f} -> {'SIGNAL' if r['signal'] else 'no trade'}, "
                  f"straddle Rs {r['straddle_pnl_inr']:,.0f}, FIN1 Rs {r['pnl_inr']:,.0f}, S2 Rs {r['s2_pnl_inr']:,.0f} ({r['s2_exit']})"
                  if r["status"] == "OK" else ""))
