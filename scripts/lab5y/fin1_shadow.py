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
  .venv/bin/python scripts/lab5y/fin1_shadow.py forward [YYYY-MM-DD|all]  # read-only forward view: 1-sigma cone from 09:46 ATM IV
  .venv/bin/python scripts/lab5y/fin1_shadow.py leads             # one line per log-only lead (B1, SC1, S1 in a 20-day-range high)
  .venv/bin/python scripts/lab5y/fin1_shadow.py selftest

Log-only forward leads (2026-10-29, registry B1 / SC1 / E21; never change FIN1/S2): B1 Crabel NR4 stretch breakout (book_lab.sig_b1
+ sell_lab.struct long, shadow fills), SC1 = S1 (the S2 legs without the RV/IV filter) after a contracting day (prior range < 0.7 x
mean of the 20 before), E21 labels LOC20 / TREND (scen_lab.dfeat). Prior-day bars: 5y idx 1m json (book_lab.daily source), then the
options-panel spot (expired_opts ATM CE spot, as the panel), then this log's own `bar` field for tape days."""
import json, math, os, random, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("FIN1_DATA", ROOT / "data"))  # history (ohlc json, expired_opts); the tape is TAPE
TAPE = Path(os.environ.get("FIN1_TAPE", ROOT / "data" / "tape" / "v2"))
LOG = ROOT / "data" / "recon" / "fin1_shadow.jsonl"
FWD = ROOT / "data" / "recon" / "forward_view.jsonl"; FWD_SVG = ROOT / "data" / "recon" / "forward_view"
MED_RVIV = 0.5434115813664702  # frozen: dev-period median of rest-of-day RV/IV (research E6)
M0 = 555; NMIN = 329  # minutes 09:46 -> 15:15


def _left_min(day, exp):  # trading minutes from 09:46 on `day` to the 15:30 close on expiry `exp` (weekdays; ponytail: ignores holidays)
    d0, d1 = date.fromisoformat(day).toordinal(), date.fromisoformat(exp).toordinal()
    return 344 + 375 * sum(date.fromordinal(o).weekday() < 5 for o in range(d0 + 1, d1 + 1))
THRESH = 1.0041598  # dev-period (before 2026-07-27) 70th pct of or_iv, the holdout threshold. Frozen.
LOT = {"NIFTY": 65, "SENSEX": 20}; LOTS = 10; CM = 1.5
TXN = {"NIFTY": 0.000355299, "SENSEX": 0.000325}
STEP = {"NIFTY": 50, "SENSEX": 100}
SID = {"NIFTY": 13, "SENSEX": 51}; IST = ZoneInfo("Asia/Kolkata")
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


def _atm(sym, S, q):
    K = round(S / STEP[sym]) * STEP[sym]
    taped = [k for (u, k, s) in q if u == sym and s == "CE" and (u, k, "PE") in q]  # recorder keeps ATM +-100/200 pts
    return min(taped, key=lambda k: abs(k - S)) if (sym, K, "CE") not in q and taped else K


def _exit_q(xs, why, t_exit):
    """quote for a time exit (nearest 15:15:00 within 15:14-15:16) or a spot exit (first >= t_exit); last quote + forced if none."""
    if why == "time":
        ex = [x for x in xs if "15:14:00" <= x[0] <= "15:16:00"]
        x = min(ex, key=lambda x: abs(int(x[0][3:5]) * 60 + int(x[0][6:8]) - 900)) if ex else None
    else: x = _first(xs, t_exit)
    return (x, False) if x else (xs[-1], True)


def s2_trade(sym, sp, xs_ce, xs_pe):
    """short straddle 09:47 -> 2-step spot move (next minute) or 15:15. Returns (pnl, why, exit_t) or None."""
    e = {s: _first(xs, "09:47:00") for s, xs in (("CE", xs_ce), ("PE", xs_pe))}
    if None in e.values() or "09:47" not in sp: return None
    s0 = sp["09:47"]; t_exit, why = "15:15:00", "time"
    for m in sorted(k for k in sp if "09:47" <= k < "15:15"):
        if abs(sp[m] - s0) >= 2 * STEP[sym]:
            h, mm = int(m[:2]), int(m[3:]) + 1; t_exit, why = f"{h + mm // 60:02d}:{mm % 60:02d}:00", "spot"; break
    pnl, forced = 0.0, False
    for s, xs in (("CE", xs_ce), ("PE", xs_pe)):  # same exit method for both legs (audit 2026-10-28)
        x, f = _exit_q(xs, why, t_exit); forced = forced or f
        pnl += (e[s][1] - x[2]) * LOT[sym] * LOTS - cost(x[2], e[s][1], sym)
    return round(pnl, 2), why + ("+forced" if forced else ""), t_exit


def _hm(i): return f"{(M0 + i) // 60:02d}:{(M0 + i) % 60:02d}"  # bar i of the day (0 = 09:15) -> HH:MM


def _bar(sp):
    """(oc, hc, lc, c, H, L) of the day from spot minute closes (as the panel); None unless the open and >= 300 minutes are on tape."""
    v = [sp[k] for k in sorted(sp)]
    return [v[0], max(v), min(v), v[-1], max(v), min(v)] if len(v) >= 300 and min(sp) <= "09:16" else None


def _hist_base(sym):
    """prior days before the tape: 5y idx 1m json (book_lab.daily source: o/h/l/c of minute closes, H/L of highs/lows), then for later days
    the options-panel spot (expired_opts ATM CE spot, what book_lab/scen_lab use as the panel days). day -> (oc, hc, lc, c, H, L)."""
    if sym in _HB: return _HB[sym]
    out = {}; g = {}
    for f in sorted(DATA.glob(f"recon/ohlc/INDEX_IDX_I_{SID[sym]}_1_*.json"))[-2:]:
        j = json.load(open(f))
        for t, h, l, c in zip(j["timestamp"], j["high"], j["low"], j["close"]):
            d = datetime.fromtimestamp(t, IST); m = d.hour * 60 + d.minute
            if M0 <= m < M0 + 375: g.setdefault(d.strftime("%Y-%m-%d"), {})[m] = (h, l, c)
    for day, b in g.items():
        if len(b) >= 300: cl = [b[m][2] for m in sorted(b)]; out[day] = (cl[0], max(cl), min(cl), cl[-1], max(x[0] for x in b.values()), min(x[1] for x in b.values()))
    g = {}; last = max(out, default="")
    for f in sorted(DATA.glob(f"cache/expired_opts/{sym}/ATM_CALL_*.json"))[-3:]:
        d = (json.load(open(f)).get("data") or {}).get("ce") or {}
        for t, s in zip(d.get("timestamp", []), d.get("spot", [])):
            dt = datetime.fromtimestamp(t, IST); m = dt.hour * 60 + dt.minute; day = dt.strftime("%Y-%m-%d")
            if s and M0 <= m < M0 + 375 and day > last: g.setdefault(day, {})[m] = s
    for day, b in g.items():
        if len(b) >= 300: v = [b[m] for m in sorted(b)]; out[day] = (v[0], max(v), min(v), v[-1], max(v), min(v))  # <300 = partial day (opt1y_load drops it)
    _HB[sym] = out; return out


_HB = {}


def prior_days(sym, before, log=None):
    """bars of the trading days < `before`, oldest first. Tape days after the base come from this log's `bar` field; a tape day whose
    bar is missing becomes a NaN row, and so does every weekday after the base that has no row and is not a holiday in
    config/v2/calendar/nse_holidays_*.yaml. ponytail: those files only exist for years we listed; an unlisted holiday (or any 2027 day
    until its file is added) counts as a missing day, i.e. conservative: the leads go NO_HIST for 21 days rather than span a hole."""
    rows = dict(_hist_base(sym)); last = max(rows, default=""); nan = tuple([float("nan")] * 6)
    for r in (read_log() if log is None else log):
        if r["sym"] == sym and last < r["day"] < before: rows[r["day"]] = tuple(r.get("bar") or nan)
    hol = {m for f in (ROOT / "config" / "v2" / "calendar").glob("nse_holidays_*.yaml") for m in re.findall(r"date:\s*(\d{4}-\d\d-\d\d)", f.read_text())}
    if last:
        d = date.fromisoformat(last) + timedelta(1)
        while d.isoformat() < before:
            if d.weekday() < 5 and d.isoformat() not in hol: rows.setdefault(d.isoformat(), nan)
            d += timedelta(1)
    return [rows[d] for d in sorted(rows) if d < before][-60:]


def lead_feats(h):
    """h = prior-day bars, last = yesterday. Same definitions as book_lab.daily (nr4, stretch, rr1) and scen_lab.dfeat (LOC20, TREND);
    None if fewer than 21 days or a NaN in them."""
    h = h[-21:]
    if len(h) < 21 or any(x != x for r in h for x in r): return None
    r = [x[1] - x[2] for x in h]; H20, L20, pc = max(x[4] for x in h[-20:]), min(x[5] for x in h[-20:]), h[-1][3]
    loc = (pc - L20) / (H20 - L20) if H20 > L20 else None  # scen_lab: 0/0 -> NaN -> no label
    return dict(nr4=bool(r[-1] <= min(r[-4:])), stretch=sum(min(x[1] - x[0], x[0] - x[2]) for x in h[-10:]) / 10, rr1=r[-1] / (sum(r[:-1]) / 20),
                loc20=None if loc is None else "LOW" if loc <= 0.2 else "HIGH" if loc >= 0.8 else "MID", trend="UP" if pc > sum(x[3] for x in h[-20:]) / 20 else "DN")


def b1_trade(sym, sp, q, stretch):
    """B1: book_lab.sig_b1 (first minute close beyond open +- stretch, 09:20-14:00; stop = opposite trigger, 2.5-step cap both ways) executed as
    sell_lab.struct long ATM with shadow fills: ask of the first quote >= the next minute, bid of the first quote >= the exit minute
    (spot exit: minute after the breach, as S2) else nearest 15:15. Returns (status, pnl, side, why, t_entry, t_exit)."""
    s = []; v = None
    for i in range(375): v = sp.get(_hm(i), v); s.append(v)  # ffill, as the panel spot
    o = next((x for x in s if x is not None), None)
    if o is None or min(sp) > "09:16": return ("NO_SPOT",)  # the open must be the 09:15/09:16 close (book_lab._open: first finite, 2 NIFTY days lack 09:15), not a late first tick
    x = next(((i, "CE" if s[i] >= o + stretch else "PE") for i in range(5, 286) if s[i] is not None and (s[i] >= o + stretch or s[i] <= o - stretch)), None)
    if not x: return ("NO_CROSS",)
    i, side = x; e = i + 1; dirn = 1 if side == "CE" else -1; stp = min(2.5, max(0.5, 2 * stretch / STEP[sym])); K = _atm(sym, s[i], q)
    xs = sorted(q.get((sym, K, side), [])); en = _first(xs, _hm(e) + ":00")
    if en is None or s[e] is None: return ("NO_QUOTES",)
    t_exit, why = "15:15:00", "time"
    for j in range(e, 360):
        mv = dirn * (s[j] - s[e]) / STEP[sym]
        if mv >= 2.5 or mv <= -stp: t_exit, why = _hm(j + 1) + ":00", "spot_tgt" if mv >= 2.5 else "spot_stop"; break
    ex, forced = _exit_q(xs, why, t_exit)
    return ("TRADE", round((ex[1] - en[2]) * LOT[sym] * LOTS - cost(en[2], ex[1], sym), 2), side, why + ("+forced" if forced else ""), en[0], t_exit)


def _safe_hist(sym, day):
    try: return prior_days(sym, day)
    except Exception as e: return e  # leads() re-raises it inside its own guard


def leads(sym, sp, q, h):
    """log-only fields: B1, SC1, LOC20/TREND labels and S1 (= s2_trade without the RV/IV filter). Never read by FIN1/S2."""
    if isinstance(h, Exception): raise h
    F = lead_feats(h) if h else None; S = sp.get("09:45"); s1 = None
    if S: K = _atm(sym, S, q); s1 = s2_trade(sym, sp, sorted(q.get((sym, K, "CE"), [])), sorted(q.get((sym, K, "PE"), [])))
    o = dict(lead_hist="OK" if F else "NO_HIST", s1_pnl_inr=s1[0] if s1 else None, s1_exit=s1[1] if s1 else "NO_INPUT", bar=_bar(sp))
    if not F: return dict(o, b1_status="NO_HIST")
    sc1 = F["rr1"] < 0.7
    o.update(loc20=F["loc20"], trend=F["trend"], rr1=round(F["rr1"], 4), b1_nr4=F["nr4"], b1_stretch=round(F["stretch"], 2), sc1_signal=sc1,
             sc1_pnl_inr=s1[0] if s1 and sc1 else 0.0, s1_loc20_high_pnl_inr=s1[0] if s1 and F["loc20"] == "HIGH" else 0.0)
    b = b1_trade(sym, sp, q, F["stretch"]) if F["nr4"] else ("NR4_NO",)
    return dict(o, b1_status=b[0], b1_pnl_inr=b[1] if b[0] == "TRADE" else 0.0, **(dict(b1_side=b[2], b1_exit=b[3], b1_entry_t=b[4]) if b[0] == "TRADE" else {}))


def day_rows(day, spot, q, hist=None):
    out = []
    for sym in LOT:
        sp = spot.get(sym, {})
        try: ld = leads(sym, sp, q, (hist or {}).get(sym))
        except Exception as e: ld = dict(lead_hist="ERROR:" + type(e).__name__)  # a leads/history failure must never lose the FIN1/S2 row
        row = dict(day=day, sym=sym, rule="FIN1", thresh=THRESH, shadow_only=True, **ld)
        mins = [f"09:{m:02d}" for m in range(15, 46)]
        have = [sp[m] for m in mins if m in sp]
        if len(have) < 28 or "09:45" not in sp:  # need the opening half hour on tape
            out.append(dict(row, status="NO_DATA", spot_minutes=len(have))); continue
        S = sp["09:45"]; K = _atm(sym, S, q); legs = {}
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


def save(rows, log=LOG):
    keep = [r for r in read_log(log) if (r["day"], r["sym"]) not in {(x["day"], x["sym"]) for x in rows}]
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(json.dumps(r) + "\n" for r in sorted(keep + rows, key=lambda r: (r["day"], r["sym"]))))


def read_log(log=LOG):
    return [json.loads(l) for l in log.read_text().splitlines() if l.strip()] if log.is_file() else []


def leads_report(rows=None):
    """one line: per lead n trades / total paper Rs / wins, and sym-days that lacked inputs (log only)."""
    R = rows if rows is not None else read_log(); parts = []
    for nm, ok, f, fx, lack in (("B1 NR4 stretch", lambda r: r.get("b1_status") == "TRADE", "b1_pnl_inr", "b1_exit", lambda r: r.get("b1_status") in (None, "NO_HIST", "NO_SPOT", "NO_QUOTES")),
                            ("SC1 S1 after contracting day", lambda r: r.get("sc1_signal") and r.get("s1_pnl_inr") is not None, "sc1_pnl_inr", "s1_exit", lambda r: r.get("lead_hist") != "OK" or r.get("s1_pnl_inr") is None),
                            ("S1 in 20d-range HIGH", lambda r: r.get("loc20") == "HIGH" and r.get("s1_pnl_inr") is not None, "s1_loc20_high_pnl_inr", "s1_exit", lambda r: r.get("lead_hist") != "OK" or r.get("s1_pnl_inr") is None)):
        T = [r for r in R if ok(r)]; parts.append(f"{nm}: n={len(T)} net Rs {sum(r[f] for r in T):,.0f} wins {sum(r[f] > 0 for r in T)} forced {sum('forced' in r.get(fx, '') for r in T)} (no inputs {sum(lack(r) for r in R)}/{len(R)})")
    return "Leads (log only, " + f"{len({r['day'] for r in R})} days): " + " | ".join(parts)


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


def _mm(m): return f"{9 + (46 + m) // 60:02d}:{(46 + m) % 60:02d}"  # minutes after 09:46 -> HH:MM


def forward(day, spot, q):
    """read-only forward view: 1-sigma cone to 15:15 from the 09:46 ATM IV; realized fields null before 15:15."""
    out = []
    for r in day_rows(day, spot, q):
        o = dict(day=day, sym=r["sym"], status=r["status"], shadow_only=True)
        sp = spot.get(r["sym"], {})
        if r["status"] != "OK" or "09:46" not in sp: out.append(o); continue
        S0, K = r["spot_0945"], r["strike"]; ivs = []  # spot at the decision (last 09:45 tick), quotes 09:46:00-09:46:59 only
        for side in ("CE", "PE"):
            x = _first(sorted(q[(r["sym"], K, side)]), "09:46:00")
            if x is None or x[0] >= "09:47:00": break
            T = ((date.fromisoformat(x[3]) - date.fromisoformat(day)).days + 0.5) / 365
            ivs.append(implied_vol((x[1] + x[2]) / 2, S0, K, T, side))
        iv = sum(ivs) / 2 if len(ivs) == 2 else float("nan")
        if iv != iv: out.append(dict(o, status="IV_NAN")); continue
        # IV is solved on calendar time T: the 09:46->15:15 share of the option's total variance is NMIN / trading minutes left
        sig = S0 * iv / 100 * math.sqrt(T * NMIN / _left_min(day, x[3]))
        o.update(S0=S0, K=K, iv=round(iv, 3), sig=round(sig, 3), ratio=r["ratio"], fin1_signal=r["signal"], s2_signal=r["s2_signal"],
                 path=[sp[_mm(m)] if _mm(m) in sp else None for m in range(NMIN + 1)], move=None, z=None, broke1=None, broke2=None, rv_rest=None, y_ratio=None, y=None)
        cl = [sp[_mm(m)] for m in range(NMIN + 1) if _mm(m) in sp]
        if "15:15" in sp and len(cl) >= 320:  # gaps would annualise a multi-minute return as one minute
            rv = rv_open(cl)
            o.update(move=round(sp["15:15"] - S0, 2), z=round((sp["15:15"] - S0) / sig, 3), rv_rest=round(rv, 2), y_ratio=round(rv / iv, 4))
            o.update(broke1=abs(o["z"]) > 1, broke2=abs(o["z"]) > 2, y=o["y_ratio"] > MED_RVIV)
        out.append(o)
    return out


def _auc(scores, pos):
    """Mann-Whitney AUC, ties averaged; nan if one class is empty."""
    o = sorted(range(len(scores)), key=lambda i: scores[i]); rk = [0.0] * len(o); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and scores[o[j + 1]] == scores[o[i]]: j += 1
        for k in range(i, j + 1): rk[o[k]] = (i + j) / 2 + 1
        i = j + 1
    n1 = sum(pos); n0 = len(pos) - n1
    return (sum(r for r, p in zip(rk, pos) if p) - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else float("nan")


def _binom_p(k, n, p):  # exact two-sided: total prob of outcomes no likelier than k
    pm = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in pm if x <= pm[k] * (1 + 1e-9)))


def calibration(rows):
    R = [r for r in rows if r.get("z") is not None]; n = len(R)
    if not n: return "Forward calibration: no sym-day with a 15:15 close yet"
    k1, k2 = sum(r["broke1"] for r in R), sum(r["broke2"] for r in R); A = [r for r in R if r["ratio"] == r["ratio"]]
    return (f"Forward calibration (n={n} sym-days, {len({r['day'] for r in R})} days): |move| > 1sigma in {k1}/{n} = {100 * k1 / n:.0f}% "
            f"(~32% if IV were unbiased, binomial p={_binom_p(k1, n, 0.3173):.2f}; history says IV overstates the day: dev median RV/IV {MED_RVIV:.2f}); > 2sigma {k2}/{n} (~5%); "
            f"or_iv AUC vs y = {_auc([r['ratio'] for r in A], [r['y'] for r in A]):.2f} ({sum(r['y'] for r in A)}/{sum(not r['y'] for r in A)} pos/neg)")


def svg(rows):
    """one self-contained SVG, one 600x260 panel per OK sym: spot path, +-1/2 sigma cone, 09:46 decision, 15:15 close."""
    R = [r for r in rows if r["status"] == "OK" and "S0" in r]; o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 {260 * max(1, len(R))}" font-family="sans-serif" font-size="11"><rect width="100%" height="100%" fill="#fff"/>']
    for i, r in enumerate(R):
        S0, sg, N = r["S0"], r["sig"], NMIN; hi = max([S0 + 2.2 * sg] + [p for p in r["path"] if p]); lo = min([S0 - 2.2 * sg] + [p for p in r["path"] if p])
        X = lambda m: 50 + 530 * m / N; Y = lambda v: 40 + 190 * (hi - v) / (hi - lo)
        band = lambda k: "M" + " L".join(f"{X(m):.1f},{Y(S0 + k * sg * math.sqrt(m / N)):.1f}" for m in range(0, N + 1, 7)) + " L" + " L".join(f"{X(m):.1f},{Y(S0 - k * sg * math.sqrt(m / N)):.1f}" for m in range(N - N % 7, -1, -7)) + " Z"
        z = f" z={r['z']:+.2f}" if r["z"] is not None else " (open)"; ratio = f"{r['ratio']:.2f}" if r["ratio"] == r["ratio"] else "nan"
        dec = f"FIN1 buy (ratio {ratio} > {THRESH:.2f})" if r["fin1_signal"] else f"S2 sell (ratio {ratio} <= {THRESH:.2f})" if r["s2_signal"] else f"no trade (ratio {ratio})"
        pts = " L".join(f"{X(m):.1f},{Y(p):.1f}" for m, p in enumerate(r["path"]) if p)
        o.append(f'<g transform="translate(0,{260 * i})"><text x="50" y="16" font-weight="bold">{r["day"]} {r["sym"]}  ratio {ratio}  1sigma {sg:.0f} pts ({100 * sg / S0:.2f}%){z}</text>'
                 f'<path d="{band(2)}" fill="#cfe3f7" stroke="#6fa8dc" stroke-dasharray="3 3" class="band2"/><path d="{band(1)}" fill="#9cc4ee" stroke="#2f77c4" class="band1"/>'
                 f'<line x1="50" x2="580" y1="{Y(S0):.1f}" y2="{Y(S0):.1f}" stroke="#999" stroke-dasharray="2 4"/><line x1="50" x2="50" y1="28" y2="232" stroke="#c0392b" stroke-width="1.5"/>'
                 f'<text x="54" y="34" fill="#c0392b">09:46 {dec.replace("<", "&lt;")}</text><path d="M{pts}" fill="none" stroke="#111" stroke-width="1.6" class="path"/>')
        if r["z"] is not None: o.append(f'<circle cx="580" cy="{Y(S0 + r["move"]):.1f}" r="4" fill="{"#c0392b" if r["broke1"] else "#27ae60"}"/><text x="578" y="248" text-anchor="end">15:15 close {S0 + r["move"]:.0f}</text>')
        o.append(f'<text x="50" y="248">09:46</text><text x="4" y="{Y(hi):.0f}">{hi:.0f}</text><text x="4" y="{Y(lo):.0f}">{lo:.0f}</text></g>')
    return "".join(o) + "</svg>"


def run_forward(arg):
    days = sorted(p.name for p in TAPE.iterdir() if (p / "quote_snapshots.jsonl").is_file()) if arg == "all" and TAPE.is_dir() else [arg]
    for day in days:
        if not (TAPE / day / "quote_snapshots.jsonl").is_file(): print(f"FWD {day}: no tape"); continue
        rows = forward(day, *load(day)); save(rows, FWD)
        FWD_SVG.mkdir(parents=True, exist_ok=True); (FWD_SVG / f"{day}.svg").write_text(svg(rows))
        for r in rows:
            if r["status"] != "OK" or "S0" not in r: print(f"FWD {day} {r['sym']}: {r['status']}"); continue
            act = "FIN1 BUY" if r["fin1_signal"] else "S2 SELL" if r["s2_signal"] else "no signal"
            print(f"FWD {day} {r['sym']}: S0 {r['S0']:.1f} ±1σ {r['sig']:.1f} ({100 * r['sig'] / r['S0']:.2f}%) ratio {r['ratio']:.2f} -> {act} | "
                  + (f"close z={r['z']:+.2f} broke1={r['broke1']}" if r["z"] is not None else "close: not yet"))
    print(calibration(read_log(FWD)))
    if days and (FWD_SVG / f"{days[-1]}.svg").is_file(): print(f"SVG: {FWD_SVG}/{days[-1]}.svg")


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
    # forward view: flat 22700 to 09:46, then +0.5 pt/min (z known); no 15:15 -> null realized fields
    spf = {"NIFTY": dict({f"09:{m:02d}": 22700.0 for m in range(15, 46)}, **{_mm(m): 22700 + 0.5 * m for m in range(NMIN + 1)}), "SENSEX": {}}
    qf = {("NIFTY", 22700.0, s): [("09:45:30", 99.0, 101.0, "2026-10-27"), ("09:46:01", 99.5, 101.5, "2026-10-27"), ("15:15:02", 100.0, 101.0, "2026-10-27")] for s in ("CE", "PE")}
    f = forward("2026-10-22", spf, qf)[0]; iv = (implied_vol(100.5, 22700, 22700, 5.5 / 365, "CE") + implied_vol(100.5, 22700, 22700, 5.5 / 365, "PE")) / 2
    assert _left_min("2026-10-22", "2026-10-27") == 344 + 3 * 375 and _left_min("2026-10-27", "2026-10-27") == 344  # Thu -> Tue: Fri, Mon, Tue
    assert abs(f["iv"] - iv) < 1e-2 and abs(f["sig"] - 22700 * iv / 100 * math.sqrt(5.5 / 365 * 329 / 1469)) < 1e-2, f
    assert f["move"] == 164.5 and abs(f["z"] - 164.5 / f["sig"]) < 1e-3 and f["broke1"] == (abs(f["z"]) > 1) and f["y"] is not None, f
    nf = forward("2026-10-22", {"NIFTY": {k: v for k, v in spf["NIFTY"].items() if k != "15:15"}, "SENSEX": {}}, qf)[0]
    assert nf["z"] is None and nf["move"] is None and nf["broke1"] is None and nf["y"] is None
    late = {k: [x if x[0] != "09:46:01" else ("09:47:05",) + x[1:] for x in v] for k, v in qf.items()}  # first quote after 09:47
    assert forward("2026-10-22", spf, late)[0]["status"] == "IV_NAN"
    gap = {"NIFTY": {k: v for i, (k, v) in enumerate(spf["NIFTY"].items()) if i % 20 or k in ("09:45", "15:15")}, "SENSEX": {}}
    assert forward("2026-10-22", gap, qf)[0]["z"] is None  # too many missing minutes: no realized fields
    assert abs(_auc([0.1, 0.4, 0.4, 0.9], [0, 1, 0, 1]) - 0.875) < 1e-12 and _auc([1, 2], [1, 1]) != _auc([1, 2], [1, 1])
    assert abs(_binom_p(5, 10, 0.5) - 1) < 1e-9 and abs(_binom_p(0, 10, 0.5) - 2 / 1024) < 1e-9
    g = svg([f]); assert g.startswith("<svg") and 'class="band1"' in g and 'class="band2"' in g and "n=1 sym-days" in calibration([f])
    print("fin1_shadow selftest OK")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "day"
    if cmd == "selftest": selftest()
    elif cmd == "forward": run_forward(sys.argv[2] if len(sys.argv) > 2 else datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat())
    elif cmd == "leads": print(leads_report())
    elif cmd == "week": print(week(int(sys.argv[2]) if len(sys.argv) > 2 else 5))
    else:
        day = sys.argv[2] if len(sys.argv) > 2 else datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        if not (TAPE / day / "quote_snapshots.jsonl").is_file():
            print(f"FIN1 {day}: no tape"); sys.exit(0)
        rows = day_rows(day, *load(day), hist={s: _safe_hist(s, day) for s in LOT}); save(rows)
        for r in rows:
            print(f"FIN1 {day} {r['sym']}: {r['status']}" + (f" RV/IV {r['ratio']:.2f} -> {'SIGNAL' if r['signal'] else 'no trade'}, "
                  f"straddle Rs {r['straddle_pnl_inr']:,.0f}, FIN1 Rs {r['pnl_inr']:,.0f}, S2 Rs {r['s2_pnl_inr']:,.0f} ({r['s2_exit']})"
                  if r["status"] == "OK" else ""))
