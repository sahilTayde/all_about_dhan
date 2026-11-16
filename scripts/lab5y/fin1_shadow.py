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
  .venv/bin/python scripts/lab5y/fin1_shadow.py leads             # one line per log-only lead (B1, SC1, S1 in a 20-day-range high, IVS, E33 cells + CONF)
  .venv/bin/python scripts/lab5y/fin1_shadow.py selftest

Log-only forward leads (2026-10-29, registry B1 / SC1 / E21; never change FIN1/S2): B1 Crabel NR4 stretch breakout (book_lab.sig_b1
+ sell_lab.struct long, shadow fills), SC1 = S1 (the S2 legs without the RV/IV filter) after a contracting day (prior range < 0.7 x
mean of the 20 before), E21 labels LOC20 / TREND (scen_lab.dfeat). Prior-day bars: 5y idx 1m json (book_lab.daily source), then the
options-panel spot (expired_opts ATM CE spot, as the panel), then this log's own `bar` field for tape days.
IVS (2026-11-13, registry E31 lead -> E39 CANDIDATE, log only, rung 0): on expiry days with a calm opening, sell the OTM1 strangle after a 1-point ATM IV
fall (`ivs_trade`). Each forward trade logs credit, exit reason, net P&L at 10 lots and, per leg at the entry and exit minutes, the modelled p75
half-spread (`hs_model`, the engine's spreads.csv) beside the realised quoted half-spread. `ivs_gate` is the E39 desk standard before 1 lot, enforced
in `decide` (IVS cannot leave rung 0 unless it returns eligible; kill flags are sticky like `halted`; `casino_lab.promote` stays the ladder).
E33 (2026-11-13, registry E33, log only, rung 0): per 15-min slot 09:45..14:30 the REGIME (EVENT > TREND_UP/DN > LEVEL > CHOP) and the CONF votes of
playbook_lab (`e33_state`), the realised next-45-min move, and shadow fills of the three lead cells (TREND_UP x BEAR/NEUT -> sell ATM CE; LEVEL x BEAR
-> long ATM PE and sell ATM CE) with the frozen super-order-style exits. The tape has no OI/volume: those two votes are None, never invented."""
import bisect, json, math, os, random, re, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("FIN1_DATA", ROOT / "data"))  # history (ohlc json, expired_opts); the tape is TAPE
TAPE = Path(os.environ.get("FIN1_TAPE", ROOT / "data" / "tape" / "v2"))
LOG = ROOT / "data" / "recon" / "fin1_shadow.jsonl"
FWD = ROOT / "data" / "recon" / "forward_view.jsonl"; FWD_SVG = ROOT / "data" / "recon" / "forward_view"
DIST = ROOT / "data" / "recon" / "candidate_dist.json"  # E26: 1y P&L distribution per candidate (casino_lab.py dist)
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


def _tape_spot(day):
    spot = {u: {} for u in IDX.values()}  # sym -> {"HH:MM": last ltp in that minute}
    with open(TAPE / day / "depth_quotes.jsonl", encoding="utf-8") as f:
        for ln in f:
            if "_IDX:" not in ln: continue
            try: e = json.loads(ln); p = e["payload"]
            except (ValueError, KeyError): continue
            u = IDX.get(p.get("instrument_id")); t = _hms(e.get("timestamp", ""))
            if u and p.get("ltp") and "09:15:00" <= t < "15:30:00": spot[u][t[:5]] = float(p["ltp"])
    return spot


def _prev_tape_spot(day):
    """spot minutes of the latest taped day before `day` (E33 indicator warm-up), {} if none."""
    prev = sorted(p.name for p in TAPE.iterdir() if p.name < day and (p / "depth_quotes.jsonl").is_file()) if TAPE.is_dir() else []
    return _tape_spot(prev[-1]) if prev else {}


def load(day):
    d = TAPE / day; spot = _tape_spot(day); q = {}  # (sym, strike, side) -> [(hh:mm:ss, bid, ask)]
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


def _mid_at(xs, t):  # mid of the last quote at or before t (HH:MM:SS), None if none
    xs = [x for x in xs if x[0] <= t]; return (xs[-1][1] + xs[-1][2]) / 2 if xs else None


HS_TAB = None  # (sym, dte0) -> 5 time buckets x 6 premium buckets of p75 half-spread (opt1y_lab.HS), loaded lazily from the engine's spreads.csv
PB, TB = (20, 50, 100, 200, 400), (570, 660, 840, 900)  # opt1y_lab premium / minute-of-day bucket edges


def _hs_load(path=None):
    """spreads.csv (opt1y_spread.py: sym,pb,tb,dte0,count,median,p75) -> HS_TAB with opt1y_lab's gap fill: along time, then along premium."""
    import csv; path = path or DATA / "cache" / "lab1y" / "spreads.csv"; tab = {}
    if not Path(path).is_file(): return tab
    with open(path, newline="") as f:
        for r in csv.DictReader(f): tab.setdefault((r["sym"], int(r["dte0"])), [[None] * 6 for _ in range(5)])[int(r["tb"])][int(r["pb"])] = float(r["p75"])
    fill = lambda xs: [next((y for y in xs[i:] if y is not None), None) or next((y for y in reversed(xs[:i]) if y is not None), None) for i in range(len(xs))]
    for k, a in tab.items():
        cols = [fill([a[t][p] for t in range(5)]) for p in range(6)]  # bfill then ffill along time
        tab[k] = [fill([cols[p][t] for p in range(6)]) for t in range(5)]  # then along premium
    return tab


def hs_model(sym, dte0, m, mid):
    """the backtest engine's modelled p75 half-spread (option points) for a leg of premium `mid` at minute-of-day `m` (opt1y_lab.hs); None if no table."""
    global HS_TAB
    if HS_TAB is None: HS_TAB = _hs_load()
    a = HS_TAB.get((sym, int(dte0)))
    return a[bisect.bisect_right(TB, m)][bisect.bisect_right(PB, mid)] if a else None


def _hs_fields(sym, x, hm):  # one leg at one quote x = (t, bid, ask, exp) in minute hm ("HH:MM"): realised and modelled half-spread
    mid = (x[1] + x[2]) / 2; return dict(bid=x[1], ask=x[2], hs_real=round((x[2] - x[1]) / 2, 4), hs_model=hs_model(sym, 1, int(hm[:2]) * 60 + int(hm[3:5]), mid))


def ivs_trade(sym, sp, q, days=0):
    """IVS lead (registry E31, frozen variant ND_STRANGLE1|ivfall1.0_dte0|STRANGLE1|spot1.5_stop0.3|OPEN=calm; the caller checks the expiry-day
    and calm-opening gates): first bar 10:01-14:00 where the ATM CE+PE IV (same strike) fell >= 1.0 IV point over 15 minutes -> SELL 10 lots
    OTM1 CE + OTM1 PE at the bid of the first quote in the next minute; buy back at the ask of the first quote >= the minute after spot moves
    1.5 steps from the entry minute or the mid-marked loss reaches 30% of the credit, else nearest 15:15 (sweep_lab.tape_trade rules).
    IV per bar uses the calendar time left to the 15:30 expiry close: a T fixed for the day would read expiry-day theta as an IV fall.
    ponytail: IV is this file's Black-Scholes on tape mids, not Dhan's IV column the sweep used; upgrade if they disagree."""
    Tb = lambda b: max(days * 1440 + 930 - (M0 + b), 1) / 525600  # minutes to 15:30 on the expiry day, annualised on calendar minutes
    s = []; v = None
    for i in range(375): v = sp.get(_hm(i), v); s.append(v)
    st = STEP[sym]; hit = None
    for i in range(46, 286):
        if s[i] is None: continue
        K = round(s[i] / st) * st; ivs = []
        for b in (i, i - 15):
            for side in ("CE", "PE"):
                m = _mid_at(sorted(q.get((sym, float(K), side), [])), _hm(b) + ":59")
                ivs.append(implied_vol(m, s[b] if s[b] else s[i], K, Tb(b), side) if m else float("nan"))
        d = (ivs[0] + ivs[1] - ivs[2] - ivs[3]) / 2
        if d == d and d <= -1.0: hit = (i, K); break
    if not hit: return ("NO_SIGNAL",)
    i, K = hit; e = i + 1; legs = [("CE", K + st), ("PE", K - st)]; xs = {lg: sorted(q.get((sym, float(lg[1]), lg[0]), [])) for lg in legs}; ent = {}
    for lg in legs:
        x = _first(xs[lg], _hm(e) + ":00")
        if x is None or x[0] >= _hm(e + 1) + ":00" or s[e] is None: return ("NO_QUOTES",)
        ent[lg] = x[1]
    credit = sum(ent.values()); t_exit, why = "15:15:00", "time"
    for j in range(e, 360):
        marks = [_mid_at(xs[lg], _hm(j) + ":59") for lg in legs]
        if None in marks: return ("NO_MARK",)
        if sum(marks) - credit >= 0.3 * credit: t_exit, why = _hm(j + 1) + ":00", "stop"; break
        if s[j] is not None and abs(s[j] - s[e]) >= 1.5 * st: t_exit, why = _hm(j + 1) + ":00", "spot"; break
    pnl, forced, L = 0.0, False, {}
    for lg in legs:
        x, f = _exit_q(xs[lg], "time" if why == "time" else "spot", t_exit); forced = forced or f
        pnl += (ent[lg] - x[2]) * LOT[sym] * LOTS - cost(x[2], ent[lg], sym)
        L[lg[0]] = dict(strike=lg[1], entry=_hs_fields(sym, _first(xs[lg], _hm(e) + ":00"), _hm(e)), exit=dict(_hs_fields(sym, x, x[0][:5]), t=x[0]))
    return ("TRADE", round(pnl, 2), why + ("+forced" if forced else ""), _hm(e), t_exit, K, dict(credit=round(credit, 2), legs=L))


# ---------------------------------------------------------------- E33 state (registry E33, 2026-11-13; log only, rung 0; never read by FIN1/S2/B1/SC1)
SLOTS33 = list(range(30, 316, 15))  # minute index from 09:15: 09:45 .. 14:30 every 15 min, as playbook_lab.SLOTS33
RBI33 = {"2025-12-05", "2026-02-06", "2026-04-08", "2026-06-05", "2026-08-05", "2026-10-07"}  # opt1y_lab.RBI; ponytail: append the Dec-2026 MPC date when RBI publishes it
FOMC33 = {"2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"}  # opt1y_lab.FOMC + the two published 2026 dates
X33 = dict(l_stop=0.30, l_tgt=0.60, l_trail=0.10, s_stop=0.5, s_tgt=0.5, cap=2.5)  # E33 freeze rule 6 (trailing jump 10% of entry per the freeze note and the DESK brief; playbook_lab.X33 carries 0.20)
E33_CELLS = {"S_CE": {"TREND_UP|BEAR", "TREND_UP|NEUT", "LEVEL|BEAR"}, "L_PE": {"LEVEL|BEAR"}}  # the three lead cells (registry E33 "Next")
E33_NOTE = ("votes oiflow/oflow = None: the tape has no OI or volume per minute (3 of 5 votes only, BULL/BEAR still +-2); max-OI level not in near_level; "
            "bars close AT the slot minute (playbook_lab's bar i//5 closes 4 min after it); r60 before 10:15 uses the 09:15 close")


def _spot_path(sp):
    """375 minute closes 09:15..15:29, forward- then back-filled as playbook_lab.spot; None if the tape has no spot."""
    s = []; v = None
    for i in range(375): v = sp.get(_hm(i), v); s.append(v)
    f = next((x for x in s if x is not None), None)
    return None if f is None else [f if x is None else x for x in s]


def _bars5(s):
    """closed 5m bars (o, h, l, c) of minute closes: bar k = minutes 5k+1..5k+5, so bar (i-1)//5 closes AT slot minute i and holds nothing later."""
    return [(s[5 * k + 1], max(s[5 * k + 1:5 * k + 6]), min(s[5 * k + 1:5 * k + 6]), s[5 * k + 5]) for k in range(74)]


def _rma(x, p):  # Wilder smoothing = pandas ewm(alpha=1/p, adjust=False): starts on the first value
    out = []; y = None
    for v in x: y = v if y is None else y + (v - y) / p; out.append(y)
    return out


def _ind5(bars):
    """(ADX14, ER12, CHOP14) per bar, the formulas of playbook_lab._bars5 (ER/CHOP nan until 12/14 bars exist)."""
    o, h, l, c = (list(z) for z in zip(*bars)); n = len(c); nan = float("nan")
    pc, ph, pl = [c[0]] + c[:-1], [h[0]] + h[:-1], [l[0]] + l[:-1]
    tr = [max(h[t] - l[t], abs(h[t] - pc[t]), abs(l[t] - pc[t])) for t in range(n)]
    um, dm = [h[t] - ph[t] for t in range(n)], [pl[t] - l[t] for t in range(n)]
    pdm = [u if u > d and u > 0 else 0.0 for u, d in zip(um, dm)]; mdm = [d if d > u and d > 0 else 0.0 for u, d in zip(um, dm)]
    a14 = [x + 1e-9 for x in _rma(tr, 14)]; pdi = [100 * x / a for x, a in zip(_rma(pdm, 14), a14)]; mdi = [100 * x / a for x, a in zip(_rma(mdm, 14), a14)]
    adx = _rma([100 * abs(p - m) / (p + m + 1e-9) for p, m in zip(pdi, mdi)], 14)
    d1 = [0.0] + [abs(c[t] - c[t - 1]) for t in range(1, n)]
    er = [abs(c[t] - c[max(t - 12, 0)]) / (sum(d1[t - 11:t + 1]) + 1e-9) if t >= 11 else nan for t in range(n)]
    lg = lambda x: math.log10(x) if x > 0 else -math.inf  # numpy log10(0) = -inf: a flat (back-filled) stretch reads as CHOP <= 45, as in the lab
    chop = [100 * lg(sum(tr[t - 13:t + 1]) / max(max(h[t - 13:t + 1]) - min(l[t - 13:t + 1]), 1e-9)) / math.log10(14) if t >= 13 else nan for t in range(n)]
    return list(zip(adx, er, chop))


def _fvg(G, b, look=12):
    """playbook_lab._fvg: unfilled 3-candle fair value gap within the last `look` bars that bar b closed inside: +1 bullish, -1 bearish, else 0."""
    cb = G[b][3]
    for t in range(b, max(2, b - look), -1):
        if G[t - 2][1] < G[t][2]:  # h[t-2] < l[t]: bullish gap
            if t + 1 <= b and min(x[2] for x in G[t + 1:b + 1]) <= G[t - 2][1]: continue  # filled since
            if G[t - 2][1] <= cb <= G[t][2]: return 1
        if G[t - 2][2] > G[t][1]:  # l[t-2] > h[t]: bearish gap
            if t + 1 <= b and max(x[1] for x in G[t + 1:b + 1]) >= G[t - 2][2]: continue
            if G[t][1] <= cb <= G[t - 2][2]: return -1
    return 0


def _cshape(x):
    o, h, l, c = x; rng = max(h - l, 1e-9)
    return 1 if (c - l) / rng >= 0.7 and (c - o) / rng > 0.5 else -1 if (h - c) / rng >= 0.7 and (o - c) / rng > 0.5 else 0


def _quotes_by_min(xs):
    by = {}
    for z in xs: by.setdefault(z[0][:5], []).append(z)
    return by


def _min_idx(t): return int(t[:2]) * 60 + int(t[3:5]) - M0  # "HH:MM[:SS]" -> minute index from 09:15


def e33_short(sym, s, q, i, K, side="CE", X=X33):
    """sell 10 lots of strike K at the bid of the first quote in minute i+1; marks = mid of the last quote at or before each minute's :59
    (ivs_trade convention); exits at the first quote (ask) of the minute after: stop when mark - credit >= X[s_stop] x credit (1.5x),
    target when mark <= (1 - X[s_tgt]) x credit, spot cap min(X[cap], 0.4%) steps (playbook_lab.act33), else nearest 15:15 (_exit_q)."""
    e = i + 1; xs = sorted(q.get((sym, float(K), side), [])); en = _first(xs, _hm(e) + ":00")
    if en is None or en[0] >= _hm(e + 1) + ":00": return None
    credit = en[1]; s0 = s[e]; st = STEP[sym]; capv = min(X["cap"], 0.004 * s0 / st) * st; t_exit, why = "15:15:00", "time"
    for j in range(e, 360):
        m = _mid_at(xs, _hm(j) + ":59")
        if m is not None and m - credit >= X["s_stop"] * credit: t_exit, why = _hm(j + 1) + ":00", "stop"; break
        if m is not None and m <= (1 - X["s_tgt"]) * credit: t_exit, why = _hm(j + 1) + ":00", "tgt"; break
        if abs(s[j] - s0) >= capv: t_exit, why = _hm(j + 1) + ":00", "spot"; break
    x, forced = _exit_q(xs, "time" if why == "time" else "spot", t_exit)
    return dict(action="S_" + side, strike=K, pnl=round((credit - x[2]) * LOT[sym] * LOTS - cost(x[2], credit, sym), 2), why=why + ("+forced" if forced else ""),
                t_entry=en[0], t_exit=x[0], entry=credit, exit=x[2])


def e33_long(sym, s, q, i, K, side="PE", X=X33):
    """buy 10 lots of strike K at the ask of the first quote in minute i+1 (super-order style, playbook_lab.long_leg on tape quotes): SL at
    X[l_stop] below entry, intrabar = the first bid at or below it (SL beats target in a minute); target +X[l_tgt] fills AT the target only when
    a bid in the minute reaches it; trailing: the SL rises one jump (X[l_trail] x entry) per jump of the bid high; adverse spot cap
    min(X[cap], 0.4%) steps -> bid of the first quote of the next minute; else nearest 15:15."""
    e = i + 1; xs = sorted(q.get((sym, float(K), side), [])); en = _first(xs, _hm(e) + ":00")
    if en is None or en[0] >= _hm(e + 1) + ":00": return None
    enp = en[2]; by = _quotes_by_min([z for z in xs if z[0] >= en[0]]); J = X["l_trail"] * enp; sl0 = enp * (1 - X["l_stop"]); tp = enp * (1 + X["l_tgt"])
    s0 = s[e]; st = STEP[sym]; dirn = 1 if side == "CE" else -1; capv = min(X["cap"], 0.004 * s0 / st) * st; sl, hi, x, why, t_exit = sl0, enp, None, "time", "15:15:00"
    for j in range(e, 360):
        qs = by.get(_hm(j), [])
        hit = next((z for z in qs if z[1] <= sl), None)
        if hit: x, why, t_exit = hit[1], "sl", hit[0]; break
        hit = next((z for z in qs if z[1] >= tp), None)
        if hit: x, why, t_exit = tp, "tgt", hit[0]; break
        if qs: hi = max(hi, max(z[1] for z in qs)); sl = max(sl, sl0 + J * math.floor((hi - enp) / J))
        if dirn * (s[j] - s0) <= -capv: why, t_exit = "cap", _hm(j + 1) + ":00"; break
    forced = False
    if x is None: z, forced = _exit_q(xs, "time" if why == "time" else "spot", t_exit); x, t_exit = z[1], z[0]
    return dict(action="L_" + side, strike=K, pnl=round((x - enp) * LOT[sym] * LOTS - cost(enp, x, sym), 2), why=why + ("+forced" if forced else ""),
                t_entry=en[0], t_exit=t_exit, entry=enp, exit=x)


def e33_state(sym, sp, q, hist, day=None, prev=None):
    """E33 REGIME x CONF per slot (playbook_lab.regime_feats / states on tape data up to the slot) and the three lead cells executed sequentially
    per lead (one open position per index per lead, as run33). hist = prior-day bars (bias, PDH/PDL, gap); prev = the previous tape day's
    spot minutes (ADX/ER/CHOP warm-up, as _bars5 uses the previous day); day = the tape date (RBI / FOMC / expiry-day EVENT). Fields that
    the tape cannot supply are None and named in e33_note. Returns dict(e33_slots, e33_trades, e33_warm, e33_note) or dict(e33_status)."""
    s = _spot_path(sp)
    if s is None or len(sp) < 60: return dict(e33_status="NO_SPOT")
    F = lead_feats(hist) if hist and not isinstance(hist, Exception) else None; H = hist[-1] if hist and not isinstance(hist, Exception) else None
    bias = None if F is None else 1 if F["trend"] == "UP" else -1; c1 = H[3] if H and H[3] == H[3] else None
    gap = s[0] / c1 - 1 if c1 else None; pdh, pdl = (H[4], H[5]) if H and H[4] == H[4] else (None, None)
    G = _bars5(s); ps = _spot_path(prev) if prev else None; warm = _bars5(ps) if ps else []
    ind = _ind5(warm + G)[len(warm):]; orh, orl = max(s[:16]), min(s[:16]); lv = [v for v in (pdh, pdl, orh, orl) if v]
    exp = next((z[3] for z in q.get((sym, float(_atm(sym, s[30], q)), "CE"), [])), None); d0 = bool(day and exp == day); slots = []
    for i in SLOTS33:
        if _hm(i) not in sp: slots.append(dict(i=i, t=_hm(i), regime=None, conf=None)); continue  # no spot in the slot minute: no state
        b = (i - 1) // 5; adx, er, chop = ind[b]; x = G[b]
        ev = bool((day in RBI33 and i == 30) or day in FOMC33 or (d0 and i >= 225) or (gap is not None and abs(gap) > 0.005))
        tr = (adx >= 25) + (er >= 0.35) + (chop <= 45) >= 2; r60 = s[i] / s[max(i - 60, 0)] - 1; near = min(abs(s[i] / v - 1) for v in lv)
        regime = "EVENT" if ev else ("TREND_UP" if r60 > 0 else "TREND_DN") if tr else "LEVEL" if near <= 0.0015 else "CHOP"
        fvg, csh = _fvg(G, b), _cshape(x); votes = fvg + csh + (bias or 0); conf = "BULL" if votes >= 2 else "BEAR" if votes <= -2 else "NEUT"
        mv = round((s[i + 45] / s[i] - 1) * 1e4, 1) if _hm(i + 45) in sp else None
        slots.append(dict(i=i, t=_hm(i), regime=regime, conf=conf, cell=f"{regime}|{conf}", votes=votes, oiflow=None, oflow=None, fvg=fvg, cshape=csh, bias=bias,
                          adx=round(adx, 1), er=None if er != er else round(er, 3), chop=None if chop != chop else round(chop, 1), r60=round(r60 * 1e4, 1), near_bp=round(near * 1e4, 1), mv45_bp=mv))
    trades = []
    for lead, fn in (("S_CE", lambda i, K: e33_short(sym, s, q, i, K, "CE")), ("L_PE", lambda i, K: e33_long(sym, s, q, i, K, "PE"))):
        busy = -1
        for z in slots:
            if z.get("cell") not in E33_CELLS[lead] or z["i"] <= busy: continue
            r = fn(z["i"], _atm(sym, s[z["i"]], q)); trades.append(dict(lead=lead, slot=z["t"], cell=z["cell"], **(r or dict(status="NO_QUOTES"))))
            if r: busy = _min_idx(r["t_exit"])
    return dict(e33_slots=slots, e33_trades=trades, e33_warm=bool(warm), e33_note=E33_NOTE)


def _safe_hist(sym, day):
    try: return prior_days(sym, day)
    except Exception as e: return e  # leads() re-raises it inside its own guard


def leads(sym, sp, q, h, day=None, prev=None):
    """log-only fields: B1, SC1, LOC20/TREND labels, S1 (= s2_trade without the RV/IV filter) and the E33 state. Never read by FIN1/S2."""
    if isinstance(h, Exception): raise h
    F = lead_feats(h) if h else None; S = sp.get("09:45"); s1 = None
    if S: K = _atm(sym, S, q); s1 = s2_trade(sym, sp, sorted(q.get((sym, K, "CE"), [])), sorted(q.get((sym, K, "PE"), [])))
    o = dict(lead_hist="OK" if F else "NO_HIST", s1_pnl_inr=s1[0] if s1 else None, s1_exit=s1[1] if s1 else "NO_INPUT", bar=_bar(sp))
    try: o.update(e33_state(sym, sp, q, h, day, prev))
    except Exception as e: o["e33_status"] = "ERROR:" + type(e).__name__  # an E33 failure must never lose the B1/SC1/S1 fields
    if not F: return dict(o, b1_status="NO_HIST")
    sc1 = F["rr1"] < 0.7
    o.update(loc20=F["loc20"], trend=F["trend"], rr1=round(F["rr1"], 4), b1_nr4=F["nr4"], b1_stretch=round(F["stretch"], 2), sc1_signal=sc1,
             sc1_pnl_inr=s1[0] if s1 and sc1 else 0.0, s1_loc20_high_pnl_inr=s1[0] if s1 and F["loc20"] == "HIGH" else 0.0)
    b = b1_trade(sym, sp, q, F["stretch"]) if F["nr4"] else ("NR4_NO",)
    return dict(o, b1_status=b[0], b1_pnl_inr=b[1] if b[0] == "TRADE" else 0.0, **(dict(b1_side=b[2], b1_exit=b[3], b1_entry_t=b[4]) if b[0] == "TRADE" else {}))


def day_rows(day, spot, q, hist=None, prev=None):
    out = []
    for sym in LOT:
        sp = spot.get(sym, {})
        try: ld = leads(sym, sp, q, (hist or {}).get(sym), day, (prev or {}).get(sym))
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
        exp = legs["CE"]["expiry"]  # IVS gates: expiry day AND calm opening (sweep_lab OPEN=calm: or_iv <= 1.0042)
        iv_s = ivs_trade(sym, sp, q) if exp == day and ratio <= 1.0042 else ("GATE_OFF",)
        s2d.update(ivs_status=iv_s[0], ivs_pnl_inr=iv_s[1] if iv_s[0] == "TRADE" else 0.0,
                   **(dict(ivs_exit=iv_s[2], ivs_entry_t=iv_s[3], ivs_exit_t=iv_s[4], ivs_strike=iv_s[5], ivs_credit=iv_s[6]["credit"], ivs_legs=iv_s[6]["legs"]) if iv_s[0] == "TRADE" else {}))
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


def ivs_trades(rows=None):
    """the logged IVS forward trades, in day/sym order, as ivs_gate wants them (net P&L at 10 lots, credit in points, per-leg half-spreads)."""
    R = sorted((r for r in (rows if rows is not None else read_log()) if r.get("ivs_status") == "TRADE" and "ivs_legs" in r), key=lambda r: (r["day"], r["sym"]))
    return [dict(day=r["day"], sym=r["sym"], pnl=r["ivs_pnl_inr"], credit=r["ivs_credit"], exit=r.get("ivs_exit"), legs=r["ivs_legs"]) for r in R]


IVS_STD = dict(n=40, mean=1500.0, p=0.10, maxdd=400000.0, loss_x_credit=2.0, slip_x=1.5, slip_run=10, loss_run=8, cum_after=25, sensex_x=2.0)  # E39 desk standard (frozen 2026-11-13)


def ivs_gate(trades, killed=False, std=IVS_STD, draws=2000):
    """E39 desk standard before 1 lot, pure. trades = ivs_trades(): [{day, sym, pnl (net Rs at 10 lots), credit (points), legs: {CE/PE: {entry: {bid, ask,
    hs_real, hs_model}, exit: {...}}}}]. eligible only when n >= 40, mean >= +1,500/trade, day-bootstrap p < 0.10 (2000 draws, stdlib random),
    max drawdown <= 4.0L, modelled p75 half-spread per leg >= realised median per leg, and no kill flag. Kill flags (sticky: the caller keeps
    `killed` until the founder clears it, as `halted`): a single trade loss > 2x its credit (Rs); realised slippage > 1.5x modelled for 10 consecutive
    trades (trade mean over legs and minutes); 8 consecutive losses; cumulative net < 0 after 25 trades. SENSEX is suspended (reported in metrics,
    the NIFTY leg still eligible) when its realised half-spread relative to premium is > 2x NIFTY's. Legs without a modelled spread count as slippage inf."""
    n = len(trades); P = [t["pnl"] for t in trades]; cum = eq = peak = 0.0; dd = 0.0; losses = run = slip = srun = 0; kills = []
    hs = {"NIFTY": [], "SENSEX": []}; mod, real = [], []
    for i, t in enumerate(trades):
        eq += t["pnl"]; peak = max(peak, eq, 0.0); dd = max(dd, peak - eq)
        if t["pnl"] < -std["loss_x_credit"] * t["credit"] * LOT[t["sym"]] * LOTS and "loss > 2x credit" not in kills: kills.append("loss > 2x credit")
        run = run + 1 if t["pnl"] < 0 else 0
        if run >= std["loss_run"] and f"{std['loss_run']} consecutive losses" not in kills: kills.append(f"{std['loss_run']} consecutive losses")
        if i + 1 == std["cum_after"] and eq < 0: kills.append(f"net < 0 after {std['cum_after']} trades")
        m, r = [], []
        for lg in t["legs"].values():
            for k in ("entry", "exit"):
                h = lg[k]; r.append(h["hs_real"]); m.append(h["hs_model"] if h.get("hs_model") is not None else 0.0)
                hs[t["sym"]].append(h["hs_real"] / ((h["bid"] + h["ask"]) / 2) if h["bid"] + h["ask"] > 0 else float("inf"))
        mod += m; real += r
        srun = srun + 1 if sum(r) > std["slip_x"] * sum(m) else 0
        if srun >= std["slip_run"] and "slippage > 1.5x modelled" not in kills: kills.append(f"slippage > {std['slip_x']}x modelled for {std['slip_run']} trades")
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    by_day = {}
    for t in trades: by_day[t["day"]] = by_day.get(t["day"], 0.0) + t["pnl"]
    D = list(by_day.values()); rnd = random.Random(5)
    p = (sum(sum(rnd.choice(D) for _ in D) <= 0 for _ in range(draws)) + 1) / (draws + 1) if D else None
    mean = sum(P) / n if n else None; mn, rn = hs["NIFTY"], hs["SENSEX"]
    sensex = bool(mn and rn and med(rn) > std["sensex_x"] * med(mn))
    M = dict(n=n, mean=round(mean, 2) if n else None, p_boot=round(p, 4) if D else None, maxdd=round(dd, 2), cum=round(eq, 2), hs_model_med=med(mod), hs_real_med=med(real),
             kills=kills, sensex_suspended=sensex, sensex_rel_hs=med(rn), nifty_rel_hs=med(mn))
    if killed: return dict(eligible=False, why="kill flag sticky until the founder clears it", metrics=M)
    if kills: return dict(eligible=False, why="kill: " + "; ".join(kills), metrics=M)
    fails = ([f"n {n} < {std['n']}"] if n < std["n"] else []) + ([f"mean {mean:,.0f} < {std['mean']:,.0f}"] if n and mean < std["mean"] else []) \
        + ([f"p {p:.3f} >= {std['p']}"] if D and p >= std["p"] else []) + ([f"maxdd {dd:,.0f} > {std['maxdd']:,.0f}"] if dd > std["maxdd"] else []) \
        + ([f"modelled hs {M['hs_model_med']} < realised median {M['hs_real_med']}"] if real and (M["hs_model_med"] is None or M["hs_model_med"] < M["hs_real_med"]) else [])
    return dict(eligible=not fails, why="; ".join(fails) if fails else "E39 desk standard met (ladder decides the rung)", metrics=M)


def leads_report(rows=None):
    """one line: per lead n trades / total paper Rs / wins, and sym-days that lacked inputs (log only)."""
    R = rows if rows is not None else read_log(); parts = []
    for nm, ok, f, fx, lack in (("B1 NR4 stretch", lambda r: r.get("b1_status") == "TRADE", "b1_pnl_inr", "b1_exit", lambda r: r.get("b1_status") in (None, "NO_HIST", "NO_SPOT", "NO_QUOTES")),
                            ("SC1 S1 after contracting day", lambda r: r.get("sc1_signal") and r.get("s1_pnl_inr") is not None, "sc1_pnl_inr", "s1_exit", lambda r: r.get("lead_hist") != "OK" or r.get("s1_pnl_inr") is None),
                            ("S1 in 20d-range HIGH", lambda r: r.get("loc20") == "HIGH" and r.get("s1_pnl_inr") is not None, "s1_loc20_high_pnl_inr", "s1_exit", lambda r: r.get("lead_hist") != "OK" or r.get("s1_pnl_inr") is None),
                            ("IVS strangle after IV fall", lambda r: r.get("ivs_status") == "TRADE", "ivs_pnl_inr", "ivs_exit", lambda r: r.get("status") != "OK" or r.get("ivs_status") in ("NO_QUOTES", "NO_MARK"))):
        T = [r for r in R if ok(r)]; parts.append(f"{nm}: n={len(T)} net Rs {sum(r[f] for r in T):,.0f} wins {sum(r[f] > 0 for r in T)} forced {sum('forced' in r.get(fx, '') for r in T)} (no inputs {sum(lack(r) for r in R)}/{len(R)})")
    for lead, nm in (("S_CE", "E33 S_CE (TREND_UP x BEAR/NEUT, LEVEL x BEAR)"), ("L_PE", "E33 L_PE (LEVEL x BEAR)")):  # several trades per sym-day
        T = [t for r in R for t in r.get("e33_trades", []) if t["lead"] == lead and "pnl" in t]; nq = sum(t.get("status") == "NO_QUOTES" for r in R for t in r.get("e33_trades", []) if t["lead"] == lead)
        parts.append(f"{nm}: n={len(T)} net Rs {sum(t['pnl'] for t in T):,.0f} wins {sum(t['pnl'] > 0 for t in T)} forced {sum('forced' in t['why'] for t in T)} (no quotes {nq}; no state {sum('e33_slots' not in r for r in R)}/{len(R)})")
    g = ivs_gate(ivs_trades(R)); parts.append(f"IVS desk gate: {'ELIGIBLE' if g['eligible'] else 'not eligible'} ({g['why']}; SENSEX {'suspended' if g['metrics']['sensex_suspended'] else 'ok'})")
    Z = [z for r in R for z in r.get("e33_slots", []) if z.get("conf") and z.get("mv45_bp") is not None]; pu = lambda c: [z["mv45_bp"] > 0 for z in Z if z["conf"] == c]
    parts.append("E33 CONF forward check (3 of 5 votes): " + ", ".join(f"P(up45|{c}) {sum(pu(c)) / len(pu(c)):.3f} (n {len(pu(c))})" if pu(c) else f"{c} n 0" for c in ("BULL", "NEUT", "BEAR")) + " [1y lab: BULL 0.522, BEAR 0.442]")
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
                 sc1_signal=r.get("sc1_signal"), b1_nr4=r.get("b1_nr4"), ivs_armed=r.get("ivs_status") != "GATE_OFF",
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


def candidates(r):
    """E26: names of the candidate trades open on this sym-day at 09:46 (B1 = armed on an NR4 day; it triggers later)."""
    c = (["FIN1"] if r.get("fin1_signal") else []) + (["S2"] if r.get("s2_signal") else []) + (["SC1"] if r.get("sc1_signal") else [])
    if r.get("s2_signal") and r.get("sc1_signal") and r.get("sym") == "NIFTY": c.append("SGATE")
    return c + (["B1"] if r.get("b1_nr4") else [])


def dist_lines(r, dist=None):
    """E26 decision chart, text form: each candidate's 1y P&L distribution (10 lots, cons engine) before entry. Not a forecast."""
    if dist is None:
        dist = json.loads(DIST.read_text()) if DIST.is_file() else {}
    out = []
    for n in candidates(r):
        d = dist.get(n)
        if not d: out.append(f"  DIST {n}: no history table (run casino_lab.py OUT dist)"); continue
        warn = " [UNDECIDABLE on history: bounds]" if n == "FIN1" else " [forward-only]" if n in ("S2", "SC1", "SGATE") else ""
        out.append(f"  DIST {n}{warn}: n {d['n']} mean {d['mean']:+,} p10 {d['p10']:+,} p50 {d['p50']:+,} p90 {d['p90']:+,} "
                   f"P(win) {d['p_win']:.0%} | dev mean {d['dev_mean']:+,} holdout mean {d['ho_mean']:+,}")
    return out


LADDER = [0, 1, 2, 5, 10]  # lots per rung; rung 0 = log-only. Every strategy starts at rung 0 (frozen 2026-11-12).
SHORT_GAMMA = {"SGATE", "IVS"}


def decide(row, state=None, dist=None):
    """One sym-day at 09:46 -> list of decisions. row: forward-view fields (sym, status, s2_signal, sc1_signal, b1_nr4, spread_ok).
    state: {"rung": {id: n}, "day_pnl": x, "week_pnl": x, "halted": bool, "recorder_ok": bool, "open_short_gamma": set of syms,
    "ivs_trades": ivs_trades() list, "ivs_killed": bool (sticky, founder clears)}. IVS (expiry day, calm open; armed at 09:46, fires on the
    first 1-pt IV fall) leaves rung 0 only when ivs_gate(ivs_trades, ivs_killed) is eligible, whatever rung the ladder gave it (E39 standard).
    dist: candidate_dist.json (p05 = dev 5th-pct single-trade loss at 10 lots). Order (Fable tree, E27-E30 all killed):
    health -> loss limits -> SGATE (short straddle 09:47, 2-step spot or 15:15) -> B1 (NR4 stretch breakout, armed for 09:20-14:00).
    Returns [{"id", "action": TRADE|LOG_ONLY|NO_TRADE|NO_DATA, "lots", "entry", "exit", "why"}]; LOG_ONLY never sends an order.
    NO_DATA (no tape / failed health) is not a decision and is excluded from forward counts. day_pnl / week_pnl = realised + open
    P&L at cons marks, re-checked every minute by the caller. `halted` is sticky: only the founder clears it. Every TRADE carries a
    hard per-trade flatten at -L (Fable critic 2026-11-12)."""
    st = dict(rung={}, day_pnl=0.0, week_pnl=0.0, halted=False, recorder_ok=True, open_short_gamma=set(), ivs_trades=[], ivs_killed=False); st.update(state or {})
    dist = dist or {}; sym = row.get("sym")
    cand = []
    if row.get("s2_signal") and row.get("sc1_signal") and sym == "NIFTY":
        cand.append(("SGATE", "09:47 sell ATM CE+PE", "spot 2 steps from entry, else 15:15"))
    if row.get("b1_nr4"):
        cand.append(("B1", "first 1m close beyond open +- stretch (09:20-14:00), buy ATM", "opposite trigger / 2.5 steps, else 15:15"))
    if row.get("ivs_armed"):
        cand.append(("IVS", "first 1-pt ATM IV fall over 15 min (10:01-14:00), sell OTM1 CE + PE next minute", "spot 1.5 steps from entry / mark 1.3x credit, else 15:15"))
    gate = ivs_gate(st["ivs_trades"], st["ivs_killed"]) if any(c[0] == "IVS" for c in cand) else None
    if row.get("status") != "OK" or not row.get("spread_ok", True):
        return [dict(id="-", action="NO_DATA", lots=0, entry="", exit="", why="no tape or data health failed (not counted)")]
    if not cand: return [dict(id="-", action="NO_TRADE", lots=0, entry="", exit="", why="no candidate signal")]
    stop = lambda n: abs(dist.get(n, {}).get("p05", 0)) * max(LADDER[st["rung"].get(n, 0)], 1) / 10
    out = []
    for n, en, ex in cand:
        lots = LADDER[st["rung"].get(n, 0)]
        # pre-trade checklist (REPO_HARVEST #4, day-trader-skill trader-risk idea): every gate PASS/BLOCK, in decision order. The
        # action below is unchanged: it is the first BLOCK. Entries only: exits / flatten are never blocked by these gates.
        ck = [("data health", True), ("kill switch", not st["halted"]), ("daily stop 2L", st["day_pnl"] > -2 * stop(n)),
              ("weekly stop 4L", st["week_pnl"] > -4 * stop(n)),
              ("one short-gamma per index", not (n in SHORT_GAMMA and sym in st["open_short_gamma"])),
              ("recorder up", bool(st["recorder_ok"])), (f"ladder rung {st['rung'].get(n, 0)} ({lots} lots)", lots > 0)]
        checks = [f"{g}: {'PASS' if ok else 'BLOCK'}" for g, ok in ck]
        if st["halted"]: why, act = "halted (fill mismatch kill switch)", "NO_TRADE"
        elif st["day_pnl"] <= -2 * stop(n): why, act = "daily stop 2L hit", "NO_TRADE"
        elif st["week_pnl"] <= -4 * stop(n): why, act = "weekly stop 4L hit", "NO_TRADE"
        elif n in SHORT_GAMMA and sym in st["open_short_gamma"]: why, act = "one short-gamma per index", "NO_TRADE"
        elif n == "IVS" and not gate["eligible"]: why, act, lots = "IVS desk standard: " + gate["why"], "LOG_ONLY", 0
        elif n == "IVS" and sym == "SENSEX" and gate["metrics"]["sensex_suspended"]: why, act = "IVS SENSEX leg suspended (realised spread > 2x NIFTY)", "NO_TRADE"
        elif not st["recorder_ok"] or lots == 0: why, act = "log-only rung (needs >= 40 forward trades to promote)" if lots == 0 else "recorder down", "LOG_ONLY"
        else: why, act = "rules pass", "TRADE"
        out.append(dict(id=n, action=act, lots=lots if act == "TRADE" else 0, entry=en,
                        exit=ex + (f"; hard flatten at -{stop(n):,.0f}" if act == "TRADE" else ""), why=why, checks=checks))
    trades = [o for o in out if o["action"] == "TRADE"]
    for o in trades[2:]: o.update(action="NO_TRADE", lots=0, why="max 2 open structures", checks=o["checks"] + ["max 2 open: BLOCK"])
    return out


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
            for ln in dist_lines(r): print(ln)
            dist = json.loads(DIST.read_text()) if DIST.is_file() else {}
            for d in decide(r, dict(ivs_trades=ivs_trades()), dist):
                print(f"  DESK {d['id']}: {d['action']} lots {d['lots']} | {d['entry']} | exit {d['exit']} | {d['why']}")
                if d.get("checks"): print("    checklist: " + "; ".join(d["checks"]))
    print(calibration(read_log(FWD)))
    if days and (FWD_SVG / f"{days[-1]}.svg").is_file(): print(f"SVG: {FWD_SVG}/{days[-1]}.svg")


def selftest():
    D = {"S2": dict(n=10, mean=100, p10=-5, p50=50, p90=300, p_win=0.6, dev_mean=120, ho_mean=-40)}
    ls = dist_lines(dict(sym="NIFTY", fin1_signal=False, s2_signal=True, sc1_signal=True, b1_nr4=False), D)
    assert candidates(dict(sym="NIFTY", s2_signal=True, sc1_signal=True)) == ["S2", "SC1", "SGATE"] and len(ls) == 3
    assert ls[0] == "  DIST S2 [forward-only]: n 10 mean +100 p10 -5 p50 +50 p90 +300 P(win) 60% | dev mean +120 holdout mean -40", ls[0]
    assert "no history table" in ls[1] and candidates(dict(sym="SENSEX", s2_signal=True, sc1_signal=True)) == ["S2", "SC1"]
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
    assert n["ivs_status"] == "GATE_OFF"  # 10-22 is not an expiry day
    # IVS: ATM IV 14 -> 12 between 09:46 and 10:01 (a 2-point fall) -> sell OTM1 22750 CE + 22650 PE at the 10:02 bid; spot +80 at 11:00 -> ask at 11:01
    T0 = lambda hhmm: (930 - (int(hhmm[:2]) * 60 + int(hhmm[3:]))) / 525600  # the bar's minutes to 15:30, as ivs_trade
    P1, P2 = bs(22700, 22700, T0("09:46"), 0.14, 0.065, "CE"), bs(22700, 22700, T0("10:01"), 0.12, 0.065, "CE")
    spi = {f"{9 + (15 + m) // 60:02d}:{(15 + m) % 60:02d}": 22700.0 for m in range(105)}; spi["11:00"] = 22780.0
    qi = {("NIFTY", 22700.0, s): [("09:46:00", P1 - 0.5, P1 + 0.5, "2026-10-27"), ("10:01:00", P2 - 0.5, P2 + 0.5, "2026-10-27")] for s in ("CE", "PE")}
    qi.update({("NIFTY", K, s): [("10:02:00", 40.0, 42.0, "2026-10-27"), ("11:01:00", hi - 2, hi, "2026-10-27")] for K, s, hi in ((22750.0, "CE", 62.0), (22650.0, "PE", 27.0))})
    iv_t = ivs_trade("NIFTY", spi, qi)
    exp3 = (40 - 62) * 650 - cost(62, 40, "NIFTY") + (40 - 27) * 650 - cost(27, 40, "NIFTY")
    assert iv_t[0] == "TRADE" and iv_t[2] == "spot" and iv_t[3] == "10:02" and iv_t[5] == 22700 and abs(iv_t[1] - round(exp3, 2)) < 0.01, iv_t
    hms = [f"{9 + (15 + m) // 60:02d}:{(15 + m) % 60:02d}" for m in range(31, 105)]; px = {t: bs(22700, 22700, T0(t), 0.14, 0.065, "CE") for t in hms}
    flat = {k: [(t + ":00", px[t] - 0.5, px[t] + 0.5, "2026-10-27") for t in hms] for k in qi if k[1] == 22700.0}
    assert ivs_trade("NIFTY", spi, flat) == ("NO_SIGNAL",)  # premium decays with the clock at a constant 14% IV: theta is not an IV fall
    assert "IVS strangle" in leads_report([dict(day="2026-10-27", sym="NIFTY", status="OK", ivs_status="TRADE", ivs_pnl_inr=exp3, ivs_exit="spot")])
    # IVS forward-log fields (E39 standard): credit 80 pts; realised half-spread 1.0 at every leg/minute; modelled p75 from a 3-row spreads.csv
    # (NIFTY expiry day: 0.5 in the first time bucket, 1.5 in the fourth, premium 50-100; gaps filled along time (bfill, ffill) then premium, as opt1y_lab)
    global HS_TAB; import csv, tempfile; _f = Path(tempfile.mkdtemp()) / "spreads.csv"
    with open(_f, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow("sym,pb,tb,dte0,count,median,p75".split(","))
        w.writerows([("NIFTY", 2, 0, 1, 9, 0.4, 0.5), ("NIFTY", 2, 3, 1, 9, 0.9, 1.5), ("SENSEX", 0, 0, 0, 9, 2.0, 3.0)])
    HS_TAB = _hs_load(_f); assert HS_TAB[("NIFTY", 1)] == [[0.5] * 6] + [[1.5] * 6] * 4 and HS_TAB[("SENSEX", 0)] == [[3.0] * 6] * 5, HS_TAB
    assert hs_model("NIFTY", 1, 569, 10) == 0.5 and hs_model("NIFTY", 1, 570, 10) == 1.5 and hs_model("SENSEX", 0, 900, 500) == 3.0 and hs_model("SENSEX", 1, 900, 500) is None
    L = ivs_trade("NIFTY", spi, qi)[6]; assert L["credit"] == 80.0 and L["legs"]["CE"]["strike"] == 22750 and L["legs"]["PE"]["exit"]["t"] == "11:01:00", L
    assert L["legs"]["CE"]["entry"] == dict(bid=40.0, ask=42.0, hs_real=1.0, hs_model=1.5) and L["legs"]["PE"]["exit"] == dict(bid=25.0, ask=27.0, hs_real=1.0, hs_model=1.5, t="11:01:00"), L
    HS_TAB = _hs_load(Path("/nonexistent/spreads.csv")); assert HS_TAB == {} and hs_model("NIFTY", 1, 700, 60) is None  # no table: modelled = None (the gate counts it as slippage)
    assert ivs_trade("NIFTY", spi, qi)[6]["legs"]["CE"]["entry"]["hs_model"] is None
    # ivs_gate known answers. mk(): one trade; credit 40 pts = Rs 26,000 at 10 lots NIFTY; realised hs 0.8 vs modelled 1.0 per leg-minute
    def mk(pnl, i=0, sym="NIFTY", credit=40.0, hr=0.8, hm=1.0, mid=20.0):
        h = lambda: dict(bid=mid - hr, ask=mid + hr, hs_real=hr, hs_model=hm)
        return dict(day=f"2027-01-{1 + i % 28:02d}", sym=sym, pnl=pnl, credit=credit, exit="spot", legs={s: dict(entry=h(), exit=h()) for s in ("CE", "PE")})
    good = [mk(p, i) for i, p in enumerate([5000.0, -2000.0, 3000.0, -1000.0] * 10)]  # 40 trades, mean +1,250 -> fails the mean bar only
    g = ivs_gate(good); assert not g["eligible"] and g["why"] == "mean 1,250 < 1,500" and g["metrics"]["kills"] == [] and g["metrics"]["maxdd"] == 2000.0, g
    good = [mk(p, i) for i, p in enumerate([6000.0, -2000.0, 3000.0, -1000.0] * 10)]  # (a) pass: mean +1,500, p ~ 0, maxdd 2k, hs 1.0 >= 0.8
    g = ivs_gate(good); assert g["eligible"] and g["metrics"]["n"] == 40 and g["metrics"]["mean"] == 1500.0 and g["metrics"]["p_boot"] < 0.1 and g["metrics"]["hs_model_med"] == 1.0 and g["metrics"]["hs_real_med"] == 0.8, g
    assert not g["metrics"]["sensex_suspended"] and g["metrics"]["sensex_rel_hs"] is None
    g = ivs_gate(good[:39]); assert not g["eligible"] and g["why"] == "n 39 < 40" and g["metrics"]["kills"] == [], g            # (b) count
    g = ivs_gate(good, killed=True); assert not g["eligible"] and g["why"].startswith("kill flag sticky"), g                      # sticky
    g = ivs_gate([mk(p, i, hr=1.1) for i, p in enumerate([6000.0, -2000.0, 3000.0, -1000.0] * 10)]); assert not g["eligible"] and g["why"] == "modelled hs 1.0 < realised median 1.1", g
    g = ivs_gate([mk(3000.0, i) if i != 7 else mk(-52001.0, i) for i in range(40)]); assert g["why"] == "kill: loss > 2x credit", g   # (c) 2 x 26,000 + 1
    assert ivs_gate([mk(3000.0, i) if i != 7 else mk(-52000.0, i) for i in range(40)])["metrics"]["kills"] == []                   # exactly 2x is not a kill
    g = ivs_gate([mk(100.0, i, hr=1.6 if 5 <= i < 15 else 0.8) for i in range(40)]); assert g["why"] == "kill: slippage > 1.5x modelled for 10 trades", g
    assert ivs_gate([mk(100.0, i, hr=1.6 if 5 <= i < 14 else 0.8) for i in range(40)])["metrics"]["kills"] == []                  # 9 in a row: no kill
    g = ivs_gate([mk(-1.0 if 10 <= i < 18 else 5000.0, i) for i in range(40)]); assert g["why"] == "kill: 8 consecutive losses", g
    assert ivs_gate([mk(-1.0 if 10 <= i < 17 else 5000.0, i) for i in range(40)])["metrics"]["kills"] == []
    alt = lambda lo, i: mk((lo if i % 2 == 0 else 100.0) if i < 25 else 5000.0, i)  # 13 losses and 12 wins alternate before trade 25, then wins
    g = ivs_gate([alt(-100.0, i) for i in range(40)]); assert g["why"] == "kill: net < 0 after 25 trades", g    # -1,300 + 1,200 = -100 at trade 25
    assert ivs_gate([alt(-90.0, i) for i in range(40)])["metrics"]["kills"] == []                                 # -1,170 + 1,200 = +30 at trade 25
    g = ivs_gate([mk(100.0, i, hm=None) for i in range(5)]); assert g["why"] == "kill: slippage > 1.5x modelled for 10 trades" or g["metrics"]["kills"] == [], g
    assert ivs_gate([mk(100.0, i, hm=None) for i in range(10)])["metrics"]["kills"] == ["slippage > 1.5x modelled for 10 trades"]  # no model = infinite slippage
    sx = good + [mk(p, i, sym="SENSEX", mid=60.0, hr=5.0, hm=6.0) for i, p in enumerate([6000.0, -2000.0, 3000.0, -1000.0] * 3)]  # SENSEX rel hs 0.083 > 2 x 0.04
    g = ivs_gate(sx); assert g["eligible"] and g["metrics"]["sensex_suspended"] and abs(g["metrics"]["sensex_rel_hs"] - 5 / 60) < 1e-9 and g["metrics"]["nifty_rel_hs"] == 0.04, g
    assert not ivs_gate(good + [mk(100.0, i, sym="SENSEX", mid=60.0, hr=4.8, hm=6.0) for i in range(12)])["metrics"]["sensex_suspended"]  # 0.08 = 2x exactly: not suspended
    assert len(ivs_trades([dict(day="2027-01-01", sym="NIFTY", ivs_status="TRADE", ivs_pnl_inr=1.0, ivs_credit=40.0, ivs_legs=good[0]["legs"]), dict(day="2027-01-02", sym="NIFTY", ivs_status="NO_SIGNAL")])) == 1
    assert "IVS desk gate: not eligible (n 0 < 40" in leads_report([])
    g = ivs_gate([]); assert not g["eligible"] and g["metrics"]["p_boot"] is None and g["metrics"]["mean"] is None
    # decide: IVS armed -> LOG_ONLY at rung 0; at rung 2 still LOG_ONLY unless the gate is eligible; SENSEX suspended -> NO_TRADE; sticky kill -> LOG_ONLY
    rI = dict(sym="NIFTY", status="OK", ivs_armed=True); DI = {"IVS": dict(p05=-30000)}
    assert decide(rI, None, DI)[0]["id"] == "IVS" and decide(rI, None, DI)[0]["action"] == "LOG_ONLY"
    d = decide(rI, dict(rung={"IVS": 2}), DI)[0]; assert d["action"] == "LOG_ONLY" and d["lots"] == 0 and d["why"] == "IVS desk standard: n 0 < 40", d
    d = decide(rI, dict(rung={"IVS": 2}, ivs_trades=good), DI)[0]; assert d["action"] == "TRADE" and d["lots"] == 2 and d["exit"].endswith("hard flatten at -6,000"), d
    d = decide(rI, dict(rung={"IVS": 2}, ivs_trades=good, ivs_killed=True), DI)[0]; assert d["action"] == "LOG_ONLY" and "sticky" in d["why"], d
    d = decide(dict(rI, sym="SENSEX"), dict(rung={"IVS": 2}, ivs_trades=sx), DI)[0]; assert d["action"] == "NO_TRADE" and "SENSEX leg suspended" in d["why"], d
    assert decide(rI, dict(rung={"IVS": 2}, ivs_trades=sx), DI)[0]["action"] == "TRADE"  # the NIFTY leg stays eligible
    assert decide(rI, dict(rung={"IVS": 2}, ivs_trades=good, open_short_gamma={"NIFTY"}), DI)[0]["why"] == "one short-gamma per index"
    assert decide(dict(rI, ivs_armed=False), None, DI)[0]["action"] == "NO_TRADE"
    HS_TAB = None
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
    # E33 known answers. (a) TREND_UP day: 09:15-10:15 chop, then +4/min to 10:41, a sharp down candle 10:41-10:45 -> at 10:45 TREND_UP (ER/CHOP votes),
    # cshape -1 + bias +1 (prior closes rising) = NEUT -> sell ATM 22850 CE at the 10:46 bid 100; mid 151 at 11:00 (>= 1.5x credit) -> buy back at the 11:01 ask 157
    assert n["e33_status"] == "NO_SPOT" and _min_idx("11:31:00") == 136 and _hm(136) == "11:31"
    HT = [(22600 + 5 * k, 22650 + 5 * k, 22550 + 5 * k, 22600 + 5 * k, 22650 + 5 * k, 22550 + 5 * k) for k in range(21)]  # last close 22700 > its 20-SMA: bias +1
    pat = [0, 2, -1, 1, -2]; sa = {}
    for m in range(375):
        v = 22700 + pat[m % 5] if m <= 60 else 22700 + 4 * (m - 60) if m <= 85 else {86: 22804, 87: 22790, 88: 22780, 89: 22770, 90: 22760}.get(m, 22760 + 2 * (m - 90))
        sa[_hm(m)] = float(v)
    qa = {("NIFTY", 22850.0, s): [("10:46:00", 100.0, 102.0, "2026-10-27"), ("11:00:30", 150.0, 152.0, "2026-10-27"), ("11:01:00", 155.0, 157.0, "2026-10-27")] for s in ("CE", "PE")}
    A = e33_state("NIFTY", sa, qa, HT, "2026-10-22"); Z = {z["t"]: z for z in A["e33_slots"]}
    assert not A["e33_warm"] and Z["09:45"]["cell"] == "LEVEL|NEUT" and Z["09:45"]["er"] is None and Z["09:45"]["chop"] is None, Z["09:45"]  # ER/CHOP need 12/14 bars
    assert Z["10:30"]["cell"] == "TREND_UP|BULL" and Z["10:45"]["cell"] == "TREND_UP|NEUT" and Z["10:45"]["cshape"] == -1 and Z["10:45"]["fvg"] == 1 and Z["10:45"]["bias"] == 1, (Z["10:30"], Z["10:45"])  # the down candle retraces into the bullish gap of the rise: fvg +1
    assert Z["10:45"]["er"] >= 0.35 and Z["10:45"]["chop"] <= 45 and Z["10:45"]["r60"] > 0 and Z["10:45"]["oiflow"] is None and Z["10:45"]["mv45_bp"] == round((sa["11:30"] / sa["10:45"] - 1) * 1e4, 1)
    ta = A["e33_trades"]; exp_a = (100 - 157) * 650 - cost(157, 100, "NIFTY")
    assert [(x["lead"], x["slot"], x["why"], x["t_exit"], x["strike"]) for x in ta] == [("S_CE", "10:45", "stop", "11:01:00", 22850)] and abs(ta[0]["pnl"] - round(exp_a, 2)) < 0.01, ta
    assert e33_state("NIFTY", {k: v for k, v in sa.items() if k != "12:00"}, qa, HT, "2026-10-22")["e33_slots"][9]["regime"] is None  # no spot in the slot minute: no state
    assert e33_state("NIFTY", sa, qa, HT, "2026-10-22", prev=sa)["e33_warm"] and e33_state("NIFTY", sa, qa, HT, "2026-10-28")["e33_slots"][0]["regime"] == "EVENT"  # FOMC day
    # (b) LEVEL day: 5-minute pattern around 22700 (ADX 0, ER 0, CHOP 100) within 0.15% of PDH 22710 -> LEVEL|NEUT; the 10:56-11:00 bar closes at its low
    # with bias -1 -> LEVEL|BEAR -> long ATM PE at the 11:01 ask 100 (target 160 filled when a bid reaches it) and sell ATM CE at the 11:01 bid 100 (mid 49 at 11:30 -> ask 49 at 11:31)
    HL = [(22700, 22705, 22695, 22700, 22710, 22690)] * 21; sl_ = {_hm(m): 22700.0 + ([3, 0, -2, -6, -10][m - 101] if 101 <= m <= 105 else pat[m % 5]) for m in range(375)}
    ql = {("NIFTY", 22700.0, "PE"): [("11:01:00", 99.0, 100.0, "2026-10-27"), ("11:20:00", 161.0, 163.0, "2026-10-27"), ("15:15:00", 120.0, 122.0, "2026-10-27")],
          ("NIFTY", 22700.0, "CE"): [("11:01:00", 100.0, 102.0, "2026-10-27"), ("11:30:00", 48.0, 50.0, "2026-10-27"), ("11:31:00", 47.0, 49.0, "2026-10-27")]}
    B = e33_state("NIFTY", sl_, ql, HL, "2026-10-22"); Zb = {z["t"]: z for z in B["e33_slots"]}
    assert all(z["regime"] == "LEVEL" for z in B["e33_slots"] if z["i"] <= 105) and Zb["10:45"]["conf"] == "NEUT" and Zb["11:00"]["cell"] == "LEVEL|BEAR" and Zb["11:00"]["votes"] == -2, Zb["11:00"]
    assert Zb["10:45"]["adx"] == 0 and Zb["10:45"]["er"] == 0 and Zb["10:45"]["chop"] == 100, Zb["10:45"]
    tb = {x["lead"]: x for x in B["e33_trades"] if "pnl" in x}; assert len(tb) == 2 and [x["status"] for x in B["e33_trades"] if "pnl" not in x] == ["NO_QUOTES"], B["e33_trades"]  # 12:00 TREND_UP|NEUT (ER 1 after the candle) has no 12:01 quote
    assert tb["L_PE"]["why"] == "tgt" and tb["L_PE"]["t_exit"] == "11:20:00" and abs(tb["L_PE"]["pnl"] - round((160 - 100) * 650 - cost(100, 160, "NIFTY"), 2)) < 0.01, tb["L_PE"]
    assert tb["S_CE"]["why"] == "tgt" and tb["S_CE"]["t_exit"] == "11:31:00" and abs(tb["S_CE"]["pnl"] - round((100 - 49) * 650 - cost(49, 100, "NIFTY"), 2)) < 0.01, tb["S_CE"]
    # long leg trailing: high bid 126 lifts the SL from 70 to 90 (one 10-point jump per jump of the high); the 11:07 bid 89 stops it out at 89 intrabar
    qt = {("NIFTY", 22700.0, "PE"): [("11:01:00", 99.0, 100.0, "2026-10-27"), ("11:05:00", 126.0, 128.0, "2026-10-27"), ("11:06:10", 92.0, 94.0, "2026-10-27"), ("11:07:00", 89.0, 91.0, "2026-10-27")]}
    lt = e33_long("NIFTY", _spot_path(sl_), qt, 105, 22700); assert lt["why"] == "sl" and lt["exit"] == 89.0 and lt["t_exit"] == "11:07:00" and abs(lt["pnl"] - round((89 - 100) * 650 - cost(100, 89, "NIFTY"), 2)) < 0.01, lt
    assert e33_long("NIFTY", _spot_path(sl_), {k: v[:1] for k, v in qt.items()}, 105, 22700)["why"] == "time+forced"  # no later quote: last bid, forced
    rep_ = leads_report([dict(day="2026-10-22", sym="NIFTY", **A), dict(day="2026-10-22", sym="SENSEX", **B)])
    assert "E33 S_CE (TREND_UP x BEAR/NEUT, LEVEL x BEAR): n=2" in rep_ and "E33 L_PE (LEVEL x BEAR): n=1" in rep_ and "P(up45|BEAR)" in rep_, rep_
    # DESK checklist parity: the action is TRADE iff no gate BLOCKs, and the first BLOCK names the same gate as `why`
    Dk = {"SGATE": dict(p05=-20000), "B1": dict(p05=-30000)}; rk = dict(sym="NIFTY", status="OK", s2_signal=True, sc1_signal=True, b1_nr4=True)
    gate = {"halted": "kill switch", "daily stop": "daily stop", "weekly stop": "weekly stop", "one short-gamma": "one short-gamma",
            "log-only rung": "ladder rung", "recorder down": "recorder up"}
    for stt in (None, dict(rung={"SGATE": 2, "B1": 1}), dict(rung={"SGATE": 2}, day_pnl=-8000), dict(rung={"SGATE": 2}, week_pnl=-17000),
                dict(rung={"SGATE": 1}, halted=True), dict(rung={"SGATE": 4}, open_short_gamma={"NIFTY"}), dict(rung={"SGATE": 4, "B1": 1}, recorder_ok=False)):
        for o in decide(rk, stt, Dk):
            blocks = [c for c in o["checks"] if c.endswith("BLOCK")]
            assert (o["action"] == "TRADE") == (not blocks), (stt, o)
            if blocks: assert blocks[0].startswith(next(v for k_, v in gate.items() if o["why"].startswith(k_))), (o["why"], blocks)
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
        rows = day_rows(day, *load(day), hist={s: _safe_hist(s, day) for s in LOT}, prev=_prev_tape_spot(day)); save(rows)
        for r in rows:
            print(f"FIN1 {day} {r['sym']}: {r['status']}" + (f" RV/IV {r['ratio']:.2f} -> {'SIGNAL' if r['signal'] else 'no trade'}, "
                  f"straddle Rs {r['straddle_pnl_inr']:,.0f}, FIN1 Rs {r['pnl_inr']:,.0f}, S2 Rs {r['s2_pnl_inr']:,.0f} ({r['s2_exit']})"
                  if r["status"] == "OK" else ""))
            if "e33_slots" in r: print(f"  E33 {r['sym']} (log only, warm-up {'yes' if r['e33_warm'] else 'no'}): " + " ".join(f"{z['t']}={z.get('cell', '-')}" for z in r["e33_slots"]) + "".join(
                f"\n    {t['lead']} {t['slot']} {t['cell']}: " + (f"Rs {t['pnl']:,.0f} {t['why']} {t['t_entry'][:5]}->{t['t_exit'][:5]} K {t['strike']:.0f}" if "pnl" in t else t["status"]) for t in r["e33_trades"]))
