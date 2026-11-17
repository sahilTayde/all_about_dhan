"""Expiry-day event bot (registry E54). PAPER RESEARCH ONLY: reads data/tape/v2 (the marketdata recorder's tick tape), never a
broker call, never an order. Founder brief 2026-11-16: on NIFTY / SENSEX expiry days watch for a chain of events, decide in 1-5 s,
buy an option (ATM / OTM1 / OTM2 or the option that moved), take a few points, get out; never hold to 15:15.
FROZEN before any expiry-day number existed (E54 section of the shared note). Everything here is EXPLORATORY: a LEAD at most.
Run (from scripts/lab5y, the pandas venv):
  ~/paper_extra_venv/bin/python expiry_bot.py selftest
  ~/paper_extra_venv/bin/python expiry_bot.py replay [day ...]     # frozen detection + pricing on the cached expiry days -> OUT/e54_*.csv
  ~/paper_extra_venv/bin/python expiry_bot.py live [day]           # in the session: tail today's tape, log every decision BEFORE its outcome exists
  ~/paper_extra_venv/bin/python expiry_bot.py score <day>          # post-market: cache + replay the day, match it to the live log (no look-ahead proof), price it
Fills, charges and the 100 ms as-of grid are tapelib's (E46, frozen): market entry at decision + 500 ms walking two book levels, resting
target, stop on the mid then a market sell 500 ms later, time-out at market, real charges, 10 lots (650 NIFTY / 200 SENSEX units)."""
import sys, os, json, time, warnings, datetime as dt, numpy as np, pandas as pd
warnings.filterwarnings("ignore", "Mean of empty slice")
from tapelib import TAPE, TAPEC, T0MS, NSLOT, LAT, GCOLS, slot_of, TapeDay, study_tapecache, _valid, _walk, _tcharge, tsim

OUT = os.environ.get("EBOT_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/cache/expiry_bot")); os.makedirs(OUT, exist_ok=True)
# DISCOVERY expiry days on the tape (the day IS the nearest weekly expiry of that index). 10-27 was taped 13:14-15:30 only.
EXPIRY_DAYS = {"NIFTY": ["2026-09-29", "2026-10-13", "2026-10-19", "2026-10-27"], "SENSEX": ["2026-10-15", "2026-10-22", "2026-10-29"]}
# cap = max quote spread for a valid decision (E46 froze 0.20 for NIFTY and lost 85% of its moments; E54 freezes 1.00 up front).
# ig = ignition: index points in 10 s; cheap = max ask of a 'cheap' option (V5); m = premium multiplier for targets / stops / ticks.
SYM = {"NIFTY": dict(pre="NSE_FNO:NIFTY", idx="NSE_IDX:NIFTY", step=50, q=650, m=1.0, cap=1.00, tx=0.000355299, ig=12.0, cheap=15.0),
       "SENSEX": dict(pre="BSE_FNO:SENSEX", idx="BSE_IDX:SENSEX", step=100, q=200, m=3.0, cap=3.00, tx=0.000325, ig=40.0, cheap=45.0)}
CELLS = [(3, 2, 600), (5, 3, 1200), (10, 5, 3000)]   # target, stop (premium points x m), max hold in 100 ms slots = 60 s / 120 s / 300 s
DEPTHS = ("ATM", "OTM1", "OTM2")                     # option bought on a directional event: CE at ATM + k steps (up), PE at ATM - k steps (down)
EVENTS = ["V1", "V2", "V3", "V4", "V5", "V6"]
LO, HI = T0MS + 300_000, T0MS + (6 * 3600 + 5 * 60 - 660) * 1000   # decisions 09:20 .. 15:09 on the receipt clock (room for the longest hold)
REARM, WIN, STRIDE = 600, 18000, 10                  # 60 s re-arm per key; 30 min look-back (V4); events are evaluated once per second
LAG_LIVE = 30                                        # live: a slot is evaluated only 3 s after it, so every tick <= slot has been read (live == replay)
TODB = [("09:20-11:00", 1100), ("11:00-12:30", 1230), ("12:30-13:00", 1300), ("13:00-15:10", 1510)]  # founder's windows (HHMM upper bounds)
tod = lambda s: next(n for n, hi in TODB if int(dt.datetime.utcfromtimestamp((T0MS + s * 100) / 1000).strftime("%H%M")) < hi) if (T0MS + s * 100) < 15 * 3600_000 + 10 * 60_000 else "13:00-15:10"


def build(ticks, s0, s1):
    """as-of state of every instrument on absolute slots s0..s1 from tick frames (receipt clock): tapelib.TapeDay.grid's columns over a window."""
    st = T0MS + np.arange(s0, s1 + 1) * 100; out = {}
    for iid, g in ticks.items():
        t = g.t.values; ix = np.searchsorted(t, st, "right") - 1; ok = ix >= 0; ix = np.maximum(ix, 0)
        G = {c: np.where(ok, g[c].values[ix], np.nan).astype(np.float32) for c in GCOLS}; G["age"] = np.where(ok, st - t[ix], 1e9); G["mid"] = (G["bid"] + G["ask"]) / 2
        out[iid] = G
    return out


def _rearm(slots, gap=REARM):
    keep, nxt = [], -1
    for s in np.sort(np.asarray(slots)):
        if s >= nxt: keep.append(int(s)); nxt = s + gap
    return keep


def detect(sym, exp, G, off, s_lo, s_hi, S_full):
    """frozen E54 events for one index on absolute slots s_lo..s_hi (once per second, on slots that are multiples of STRIDE). Every input is as-of
    the slot (ticks received <= slot time). G = option / future grids on absolute slots off..; S_full = the index ltp on absolute slots 0..>=s_hi
    (the whole day so far: the day's range needs it). Returns rows (event, dir, iid, slot, atm): dir = +1 up / -1 down; iid = the option the event names (V3 / V5) else None."""
    c = SYM[sym]; m, step = c["m"], c["step"]; oid = lambda K, side: f"{c['pre']}:{exp}:{int(K)}:{side}"
    start = -(-max(s_lo, WIN + 300) // STRIDE) * STRIDE; SS = np.arange(start, min(s_hi, len(S_full) - 1) + 1, STRIDE); SS = SS[SS - off >= 300]; r = SS - off
    if not len(SS): return []
    S = np.asarray(S_full, float); rows = []
    # 1-second index series from 09:15 (as-of), for the medians / ranges; j = index of each decision slot in it
    s1 = S[::STRIDE]; d10 = s1 - np.concatenate([[np.nan] * 10, s1[:-10]])
    med = pd.Series(np.abs(d10)).rolling(600, min_periods=300).median().shift(1).values        # prior 10 min of 10-s moves
    h30 = pd.Series(s1).rolling(1800, min_periods=1500).max().shift(1).values; l30 = pd.Series(s1).rolling(1800, min_periods=1500).min().shift(1).values
    dmax = pd.Series(s1).expanding(1500).max().shift(1).values; dmin = pd.Series(s1).expanding(1500).min().shift(1).values
    j = SS // STRIDE
    at = lambda a: a[j]
    with np.errstate(invalid="ignore"):
        d, md = at(d10), at(med); v1 = (np.abs(d) >= c["ig"]) & (np.abs(d) >= 3 * md) & np.isfinite(md)
        rng30 = at(h30) - at(l30); dr = at(dmax) - at(dmin); comp = (rng30 <= 0.35 * dr) & (dr >= 3 * c["ig"])
        v4u = comp & (at(s1) > at(h30) + 1.0); v4d = comp & (at(s1) < at(l30) - 1.0)
    for sign, mask in ((1, v1 & (d > 0)), (-1, v1 & (d < 0))):
        rows += [("V1", sign, None, s, None) for s in _rearm(SS[mask])]
    for sign, mask in ((1, v4u), (-1, v4d)):
        rows += [("V4", sign, None, s, None) for s in _rearm(SS[mask])]
    atm = np.round(S / step) * step; K_at = atm[SS]
    for K in np.unique(K_at[np.isfinite(K_at)]):
        sel = K_at == K; ce, pe = G.get(oid(K, "CE")), G.get(oid(K, "PE"))
        if ce is None or pe is None: continue
        rr = r[sel]; ss = SS[sel]
        with np.errstate(invalid="ignore"):
            st_now = ce["mid"][rr] + pe["mid"][rr]; st_old = ce["mid"][rr - 300] + pe["mid"][rr - 300]   # the strikes that are ATM now, against the same strikes 30 s ago
            dce = ce["mid"][rr] - ce["mid"][rr - 300]; dpe = pe["mid"][rr] - pe["mid"][rr - 300]
            v2 = (st_now / st_old - 1 >= 0.06) & (ce["age"][rr] <= 1500) & (pe["age"][rr] <= 1500) & _valid(ce, rr, c["cap"]) & _valid(pe, rr, c["cap"])
        rows += [("V2", 1, None, s, None) for s in _rearm(ss[v2 & (dce > dpe)])] + [("V2", -1, None, s, None) for s in _rearm(ss[v2 & (dce < dpe)])]
        for k in (0, 1):   # V3 sweep on the ATM and OTM1 options of both sides
            for side, sg in (("CE", 1), ("PE", -1)):
                iid = oid(K + sg * k * step, side); g = G.get(iid)
                if g is None: continue
                with np.errstate(invalid="ignore"):
                    v3 = (g["ltp"][rr] >= g["ask"][rr - 10]) & (g["ask"][rr] - g["ask"][rr - 10] >= 0.10 * m - 1e-6) & (g["a5"][rr] <= 0.6 * g["a5"][rr - 20]) & _valid(g, rr, c["cap"])
                rows += [("V3", sg, iid, s, None) for s in _rearm(ss[v3])]
    for iid, g in G.items():   # V5 cheap burst: any option of this index and expiry
        p = iid.split(":")
        if len(p) != 5 or not iid.startswith(c["pre"] + ":") or p[2] != exp: continue
        with np.errstate(invalid="ignore"):
            v5 = (g["ask"][r - 200] <= c["cheap"]) & (g["bid"][r - 200] > 0) & (g["mid"][r] / g["mid"][r - 200] - 1 >= 0.40) & _valid(g, r, c["cap"])
        rows += [("V5", 1 if p[4] == "CE" else -1, iid, s, None) for s in _rearm(SS[v5])]
    pre = [(e, d_, s) for e, d_, _, s, _ in rows if e in ("V2", "V4")]
    for e, d_, _, s, _ in list(rows):   # V6 chain: an ignition within 60 s after a straddle pop or range break in the same direction
        if e == "V1" and any(d2 == d_ and 0 < s - s2 <= 600 for _, d2, s2 in pre): rows.append(("V6", d_, None, s, None))
    out = []
    for e, d_, iid, s, _ in rows:
        K = atm[s]
        out.append((e, d_, iid, int(s), float(K) if np.isfinite(K) else None))
    return sorted(set(out), key=lambda x: (x[3], x[0], x[1], x[2] or ""))   # fully ordered: the placebo draws (and so the ex columns) are reproducible run to run


def _trade_iids(sym, exp, ev):
    """instruments a trade can use for an event row: (depth label, iid) list."""
    c = SYM[sym]; e, d_, iid, s, K = ev
    if iid is not None: return [("SELF", iid)]
    if K is None: return []
    side = "CE" if d_ > 0 else "PE"
    return [(dep, f"{c['pre']}:{exp}:{int(K + d_ * k * c['step'])}:{side}") for k, dep in enumerate(DEPTHS)]


def price(sym, exp, G, evs, day, rg=None, npl=5):
    """price every event x depth x cell under the frozen fills; placebo = npl random slots in the same 15-min bucket of the same instrument."""
    c = SYM[sym]; rows = []; rg = rg or np.random.default_rng(49)
    for ev in evs:
        e, d_, _, s, _ = ev
        for dep, iid in _trade_iids(sym, exp, ev):
            g = G.get(iid)
            if g is None or s + LAT + 3000 + LAT >= len(g["mid"]) or s < 1: continue
            ok = bool(_valid(g, np.array([s]), c["cap"])[0]); base = dict(day=day, sym=sym, event=e, dir=d_, depth=dep, iid=iid, slot=s, tod=tod(s), valid=ok)
            pl = np.clip((s // 9000) * 9000 + rg.integers(0, 9000, npl), 3000, len(g["mid"]) - 3100); pv = _valid(g, pl, c["cap"])
            for lat in (0, 5, 10, LAG_LIVE):
                base[f"mid{lat * 100}"] = float(g["mid"][s + lat + 1200] - g["mid"][s + lat]) if ok else np.nan   # mid-to-mid over 120 s at each latency
                pm = np.where(pv, g["mid"][pl + lat + 1200] - g["mid"][pl + lat], np.nan); base[f"plc{lat * 100}"] = float(np.nanmean(pm)) if np.isfinite(pm).any() else np.nan
            for T, S_, H in CELLS:
                R = tsim(g, np.array([s]), T * c["m"], S_ * c["m"], H, c["q"], c["tx"]) if ok else None
                P = tsim(g, pl[pv], T * c["m"], S_ * c["m"], H, c["q"], c["tx"]) if pv.any() else None
                rows.append(dict(base, cell=f"{T}/{S_}/{H // 10}s", filled=bool(R["filled"][0]) if R else False, out=int(R["out"][0]) if R else -1,
                                 pts=float(R["pts"][0]) if R else np.nan, net=float(R["net"][0]) if R else np.nan, hs=float(R["hs"][0]) if R else np.nan,
                                 plc_net=float(np.nanmean(P["net"])) if P is not None and np.isfinite(P["net"]).any() else np.nan))
    return pd.DataFrame(rows)


def spot_after(sym, G, evs, rg=None):
    """detect-only: index points in the event's direction 30 / 120 / 300 s later, against random moments of the same 15-min bucket."""
    c = SYM[sym]; I = G.get(c["idx"]); rows = []; rg = rg or np.random.default_rng(7)
    if I is None: return pd.DataFrame()
    S = I["ltp"].astype(float)
    for e, d_, iid, s, K in evs:
        pl = np.clip((s // 9000) * 9000 + rg.integers(0, 9000, 5), 3000, len(S) - 3100)
        r = dict(sym=sym, event=e, dir=d_, slot=s, tod=tod(s))
        for h in (300, 1200, 3000):
            r[f"spot{h // 10}"] = d_ * (S[s + h] - S[s]); r[f"plc{h // 10}"] = float(np.nanmean(d_ * (S[pl + h] - S[pl])))
        rows.append(r)
    return pd.DataFrame(rows)


def base_rate(sym, exp, G, day):
    """every-30-s ATM CE / PE buys with the same cells: what an uninformed expiry-day buyer pays on these days (E46-0 convention)."""
    c = SYM[sym]; I = G.get(c["idx"]); rows = []
    if I is None: return pd.DataFrame()
    dec = np.arange(slot_of(LO), slot_of(HI) + 1, 300); atm = np.round(I["ltp"].astype(float) / c["step"]) * c["step"]
    for K in np.unique(atm[dec][np.isfinite(atm[dec])]):
        for side in ("CE", "PE"):
            g = G.get(f"{c['pre']}:{exp}:{int(K)}:{side}")
            if g is None: continue
            s = dec[atm[dec] == K]; s = s[_valid(g, s, c["cap"])]
            for T, S_, H in CELLS:
                if not len(s): continue
                R = tsim(g, s, T * c["m"], S_ * c["m"], H, c["q"], c["tx"]); f = R["filled"]
                rows.append(dict(day=day, sym=sym, cell=f"{T}/{S_}/{H // 10}s", n=int(f.sum()), net=float(np.nansum(R["net"])), p_tgt=float((R["out"] == 0).mean()), p_stop=float((R["out"] == 1).mean())))
    return pd.DataFrame(rows)


def load_day(day):
    """ticks of a cached day (tapelib cache; built on demand) -> (ticks dict, expiry per index)."""
    if not os.path.exists(f"{TAPEC}/{day}.parquet"): study_tapecache([day])
    TD = TapeDay(day); return TD.ticks, TD.exp


def replay_day(day, syms=None, rg=None):
    ticks, exp = load_day(day); G = build(ticks, 0, NSLOT - 1); res = {}
    for sym in (syms or [s for s in SYM if exp.get(s) == day]):
        evs = detect(sym, exp[sym], G, 0, slot_of(LO), slot_of(HI), G[SYM[sym]["idx"]]["ltp"]) if SYM[sym]["idx"] in G else []; res[sym] = dict(events=evs, prices=price(sym, exp[sym], G, evs, day, rg), spot=spot_after(sym, G, evs, rg), base=base_rate(sym, exp[sym], G, day))
        print(f"{day} {sym}: {len(evs)} events", {e: sum(1 for x in evs if x[0] == e) for e in EVENTS}, flush=True)
    del G; return res


def study_replay(days=None, tag=""):
    rg = np.random.default_rng(49); days = days or sorted(set(sum(EXPIRY_DAYS.values(), []))); P, SP, B, EV = [], [], [], []
    for day in days:
        for sym, r in replay_day(day, rg=rg).items():
            P.append(r["prices"]); SP.append(r["spot"].assign(day=day)); B.append(r["base"]); EV += [dict(day=day, sym=sym, event=e, dir=d_, iid=i, slot=s, atm=K, hms=_hms(s)) for e, d_, i, s, K in r["events"]]
    if not P: print(f"no expiring series on {days}: nothing to replay"); return None, None, None
    pd.DataFrame(EV).to_csv(f"{OUT}/e54_events{tag}.csv", index=False); P = pd.concat(P, ignore_index=True); P.to_csv(f"{OUT}/e54_trades{tag}.csv", index=False)
    SP = pd.concat(SP, ignore_index=True); B = pd.concat(B, ignore_index=True)
    report(P, SP, B, pd.DataFrame(EV), tag); return P, SP, B


def _hms(s): x = (T0MS + s * 100) // 1000; return f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}"


def report(P, SP, B, EV, tag=""):
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 500); rg = np.random.default_rng(1)
    print(f"\n== E54 events per day and time window (frozen definitions; {EV.day.nunique()} expiry days)")
    print(EV.assign(tod=EV.slot.map(tod)).groupby(["sym", "event", "day"]).size().unstack("day").fillna(0).astype(int).to_string())
    print(EV.assign(tod=EV.slot.map(tod)).groupby(["sym", "event", "tod"]).size().unstack("tod").fillna(0).astype(int).to_string())
    print("\n== detect-only: index points in the event's direction after 30 / 120 / 300 s, minus the same-bucket placebo (per event, all days)")
    sp = SP.groupby(["sym", "event"]).agg(n=("slot", "size"), s30=("spot30", "mean"), p30=("plc30", "mean"), s120=("spot120", "mean"), p120=("plc120", "mean"), s300=("spot300", "mean"), p300=("plc300", "mean"))
    for h in (30, 120, 300): sp[f"ex{h}"] = sp[f"s{h}"] - sp[f"p{h}"]
    print(sp.round(1).to_string())
    print("\n== base rate on these days: every-30-s ATM buys, net premium points per unit after real charges (10 lots), by cell")
    b = B.groupby(["sym", "cell"]).agg(n=("n", "sum"), net=("net", "sum"), p_tgt=("p_tgt", "mean"), p_stop=("p_stop", "mean")); b["net_per"] = b.net / b.n.clip(lower=1); print(b.round(3).to_string())
    X = P[P.filled].copy(); out = []
    for (sym, e, dep, cell), g in X.groupby(["sym", "event", "depth", "cell"]):
        q = SYM[sym]["q"]; d = g.groupby("day").net.sum(); x = g.net.values; bm = x[rg.integers(0, len(x), (4000, len(x)))].mean(1)
        ex = g.mid500 - g.plc500; ex0 = g.mid0 - g.plc0; ex10 = g.mid1000 - g.plc1000; ex30 = g.mid3000 - g.plc3000
        r = dict(sym=sym, event=e, depth=dep, cell=cell, n=len(g), days=g.day.nunique(), days_pos=int((d > 0).sum()), p_tgt=float((g.out == 0).mean()), p_stop=float((g.out == 1).mean()),
                 net10=float(x.mean()), rs10=float(x.mean() * q), p_boot=float((bm <= 0).mean()), plc_net=float(g.plc_net.mean()),
                 ex0=float(ex0.mean()), ex500=float(ex.mean()), ex1000=float(ex10.mean()), ex3000=float(ex30.mean()))
        lead = r["n"] >= 30 and r["net10"] > 0 and r["days"] >= 3 and r["days_pos"] >= r["days"] - 1 and r["ex500"] > 0 and r["p_boot"] <= 0.10 and r["ex1000"] > 0 and r["ex3000"] > 0
        r["verdict"] = "LEAD" if lead else ("INFO" if r["net10"] > 0 and r["ex500"] > 0 else "nothing"); out.append(r)
    T = pd.DataFrame(out); T.to_csv(f"{OUT}/e54_cells{tag}.csv", index=False)
    print("\n== E54 cells (filled trades; net = premium points per unit after real charges at 10 lots; rs10 = Rs per trade; ex = 120-s mid-to-mid minus placebo at 0 / 500 / 1000 / 3000 ms)")
    print(T.round(dict(p_tgt=2, p_stop=2, net10=3, rs10=0, p_boot=3, plc_net=3, ex0=3, ex500=3, ex1000=3, ex3000=3)).to_string(index=False) if len(T) else "no filled trades")
    print(f"\nverdicts: { T.verdict.value_counts().to_dict() if len(T) else {} }  (LEAD rule frozen: n>=30, net10>0, >=3 days with all but one positive, ex500>0 with bootstrap p<=0.10, ex1000>0 and ex3000>0)")


# ---------------------------------------------------------------- live (shadow) mode: decisions logged before their outcome exists
_COLS = "t xt iid bid ask bq aq ltp oi b5 a5 bid2 ask2".split()
_ms = lambda z: (int(z[11:13]) * 3600 + int(z[14:16]) * 60 + int(z[17:19])) * 1000 + (int(z[20:23]) if len(z) > 20 and z[19] == "." else 0)


def _parse(ln):
    if '"repeat":true' in ln: return None
    try: e = json.loads(ln)
    except Exception: return None
    p = e["payload"]; lv = p.get("levels") or {}; b, a = lv.get("bid") or [], lv.get("ask") or []; xt = p.get("exchange_ts") or e["timestamp"]
    return (_ms(e["timestamp"]), _ms(xt), p["instrument_id"], p.get("bid"), p.get("ask"), p.get("bid_qty"), p.get("ask_qty"), p.get("ltp"), p.get("oi"),
            sum(q for _, q in b) if b else None, sum(q for _, q in a) if a else None, b[1][0] if len(b) > 1 else None, a[1][0] if len(a) > 1 else None)


def _frames(buf):
    df = pd.DataFrame(buf, columns=_COLS)
    for c_ in _COLS[3:]: df[c_] = pd.to_numeric(df[c_], errors="coerce")
    return {k: g.sort_values("t", kind="stable") for k, g in df.groupby("iid", sort=False)}


def _exp_of(ticks, day):
    return {sym: (min(ex) if (ex := {k.split(":")[2] for k in ticks if k.count(":") == 4 and k.startswith(c["pre"] + ":") and k.split(":")[2] >= day}) else None) for sym, c in SYM.items()}


def _trim(buf, t_now):
    """keep 45 min of option / future ticks and the index ticks of the whole day (the day's range feeds V4)."""
    cut = t_now - 45 * 60_000; return [r for r in buf if r[0] >= cut or "_IDX:" in r[2]]


def live_step(buf, day, done, s_last, log, now_ms=None):
    """one evaluation on the buffered ticks: slots s_last+1 .. (latest tick - 3 s). Appends new decisions to `log` (file) and `done` (set). Returns the new s_last."""
    if not buf: return s_last
    ticks = _frames(buf); exp = _exp_of(ticks, day); t_now = now_ms if now_ms is not None else max(g.t.values[-1] for g in ticks.values())
    s_hi = min(slot_of(t_now) - LAG_LIVE, slot_of(HI)); s_lo = max(s_last + 1, slot_of(LO))
    if s_hi < s_lo: return s_last
    off = max(0, s_lo - 400); G = build(ticks, off, s_hi); new = []   # options need 30 s of history; the index keeps the whole day (see _trim)
    for sym in SYM:
        idx = SYM[sym]["idx"]
        if exp.get(sym) != day or idx not in ticks: continue
        S_full = build({idx: ticks[idx]}, 0, s_hi)[idx]["ltp"]
        for e, d_, iid, s, K in detect(sym, exp[sym], G, off, s_lo, s_hi, S_full):
            key = (sym, e, d_, iid, s)
            if key in done: continue
            done.add(key); new.append(dict(day=day, sym=sym, event=e, dir=d_, iid=iid, slot=s, atm=K, hms=_hms(s), trade=_trade_iids(sym, exp[sym], (e, d_, iid, s, K)),
                                           known_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="milliseconds")))
    if new and log is not None:
        with open(log, "a") as f:
            for r in new: f.write(json.dumps(r) + "\n")
        for r in new: print("DECISION", r["hms"], r["sym"], r["event"], "up" if r["dir"] > 0 else "down", r["iid"] or r["trade"][0][1], flush=True)
    return s_hi


def study_live(day=None):
    """tail today's tape every 2 s (file offset, no re-read), keep 45 min of ticks, log decisions as they become knowable. Paper only: nothing is sent anywhere."""
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30)); day = day or dt.datetime.now(IST).date().isoformat(); path = f"{TAPE}/{day}/depth_quotes.jsonl"; log = f"{OUT}/{day}_live.jsonl"
    print(f"expiry_bot live {day}: tape {path} -> {log} (decisions 09:20-15:09 IST, each written the moment it is knowable)", flush=True)
    while not os.path.exists(path):
        if dt.datetime.now(IST).strftime("%H:%M") > "15:30": print("no tape today; exit"); return
        time.sleep(10)
    buf, done, s_last, pos, last_status = [], set(), -1, 0, 0
    with open(path, encoding="utf-8") as f:
        while True:
            f.seek(pos); chunk = f.read(); pos = f.tell()
            if chunk:
                lines = chunk.split("\n")
                if not chunk.endswith("\n"): pos -= len(lines[-1].encode("utf-8")); lines = lines[:-1]
                buf += [r for r in map(_parse, lines) if r is not None]
            if buf:
                buf = _trim(buf, buf[-1][0]); s_last = live_step(buf, day, done, s_last, log)
            now = dt.datetime.now(IST)
            if time.time() - last_status >= 60:
                last_status = time.time(); print(f"{now.strftime('%H:%M:%S')} ticks buffered {len(buf)} decisions {len(done)} evaluated to slot {s_last} ({_hms(max(s_last, 0))})", flush=True)
            if now.strftime("%H:%M") >= "15:31": print(f"session over: {len(done)} decisions in {log}"); return
            time.sleep(2)


def study_score(day):
    """post-market: cache + replay the day, match the live log to the replay (no look-ahead proof), price it."""
    P, SP, B = study_replay([day], tag=f"_{day}"); log = f"{OUT}/{day}_live.jsonl"
    if P is None: return
    EV = pd.read_csv(f"{OUT}/e54_events_{day}.csv")
    if not os.path.exists(log): print(f"\nno live log {log}: replay only"); return
    L = pd.DataFrame([json.loads(l) for l in open(log)]); rk = {(r.sym, r.event, r.dir, r.iid if isinstance(r.iid, str) else None, r.slot) for r in EV.itertuples()}
    lk = {(r.sym, r.event, r.dir, r.iid if isinstance(r.iid, str) else None, r.slot) for r in L.itertuples()}
    near = lambda a, B_: any(a[:4] == b[:4] and abs(a[4] - b[4]) <= 10 for b in B_)
    hit = sum(near(a, rk) for a in lk); miss = sum(not near(a, lk) for a in rk)
    print(f"\n== live vs replay {day}: live decisions {len(lk)}, replay events {len(rk)}, live matched by replay {hit}, replay events the live run never logged {miss}")
    print("(a live decision with no replay twin would mean the live code saw something replay cannot: look-ahead or a buffer bug; a replay event missing live = the live loop was down or late)")


# ---------------------------------------------------------------- selftest: hand-built day, known answers, live == replay
def _synth():
    """one synthetic NIFTY expiry day: spot 25000 -> +60 ramp in the first 10 min, 30 min flat, a +8 break (V4), later a +40 jump in 5 s (V1, and V6 because the jump is itself a second range break 1 s earlier),
    a cheap 5-rupee PE that quadruples in 20 s (V5); options quoted off a toy delta with constant sizes."""
    day = "2026-10-13"; sec = np.arange(0, 6 * 3600 + 15 * 60 + 1); t = T0MS + sec * 1000; S = np.full(len(sec), 25000.0)
    S[:600] += np.linspace(0, 60, 600); S[600:] = 25060 + 2 * np.sin(sec[600:] / 7.0)
    S[2460:] += 8                                        # 09:56:00 (sec 2460): break above the 30-min high by > 1 point
    S[3000:3005] += np.linspace(8, 40, 5); S[3005:] += 40  # 10:05:00: +40 in 5 s -> V1 (10-s move >= 12 one second in); spot ends at 25108, above the 25100 strike that is ATM at the decision
    ticks = {"NSE_IDX:NIFTY": pd.DataFrame(dict(t=t, xt=t, iid="NSE_IDX:NIFTY", bid=np.nan, ask=np.nan, bq=np.nan, aq=np.nan, ltp=S, oi=0, b5=np.nan, a5=np.nan, bid2=np.nan, ask2=np.nan))}
    for K in range(24900, 25251, 50):
        for side, sg in (("CE", 1), ("PE", -1)):
            mid = np.maximum(sg * (S - K), 0) * 0.5 + 20.0; mid = np.round(mid * 20) / 20; bid = mid - 0.05; ask = mid + 0.05   # toy pricing: delta 0.5 in the money, flat 20 otherwise; bid = mid - 0.05; ask = mid + 0.05
            ticks[f"NSE_FNO:NIFTY:{day}:{K}:{side}"] = pd.DataFrame(dict(t=t, xt=t, iid=f"NSE_FNO:NIFTY:{day}:{K}:{side}", bid=bid, ask=ask, bq=2000.0, aq=2000.0, ltp=mid, oi=1000, b5=9000.0, a5=9000.0, bid2=bid - 0.05, ask2=ask + 0.05))
    cheap = np.full(len(sec), 5.0); cheap[4000:4020] = np.linspace(5, 20, 20); cheap[4020:] = 20.0   # 10:21:40 (sec 4000): 5 -> 20 in 20 s
    ticks[f"NSE_FNO:NIFTY:{day}:24500:PE"] = pd.DataFrame(dict(t=t, xt=t, iid=f"NSE_FNO:NIFTY:{day}:24500:PE", bid=cheap - 0.05, ask=cheap + 0.05, bq=5000.0, aq=5000.0, ltp=cheap, oi=1, b5=9e4, a5=9e4, bid2=cheap - 0.1, ask2=cheap + 0.1))
    return day, ticks


def study_selftest():
    day, ticks = _synth(); G = build(ticks, 0, NSLOT - 1); evs = detect("NIFTY", day, G, 0, slot_of(LO), slot_of(HI), G["NSE_IDX:NIFTY"]["ltp"])
    kinds = {e: [(_hms(s), d_) for e2, d_, _, s, _ in evs if e2 == e] for e in EVENTS}
    assert kinds["V4"] == [("09:56:00", 1), ("10:05:00", 1)], kinds["V4"]    # the break fires at the first second above the 30-min high + 1; the 10:05 jump is a second (compressed-range) break
    assert kinds["V1"] and kinds["V1"][0][0] == "10:05:01" and kinds["V1"][0][1] == 1 and len(kinds["V1"]) == 1, kinds["V1"]   # the 10-s move reaches 12 points one second into the jump, once (re-arm)
    assert kinds["V5"] and kinds["V5"][0][0] == "10:21:43" and kinds["V5"][0][1] == -1 and len(kinds["V5"]) == 1, kinds["V5"]  # the as-of mid 20 s earlier is 5.0; +40% = 7.0 is first reached at sec 4003 = 10:21:43
    assert kinds["V6"] == kinds["V1"], kinds                                  # chain: the ignition came within 60 s of the 10:05:00 break in the same direction
    assert kinds["V2"][0] == ("09:56:02", 1) and not kinds["V3"], kinds      # the toy straddle (0.5 |S-K| + 40) rises 9% on the +8 break (the 2-pt sine alone never makes 6%)
    for e2, d_, _, s, K in evs:                                                # every straddle pop satisfies its own definition when recomputed from the grids: >= +6% in 30 s on the strikes that are ATM at the slot
        if e2 == "V2":
            ce, pe = G[f"NSE_FNO:NIFTY:{day}:{int(K)}:CE"], G[f"NSE_FNO:NIFTY:{day}:{int(K)}:PE"]
            assert (ce["mid"][s] + pe["mid"][s]) / (ce["mid"][s - 300] + pe["mid"][s - 300]) - 1 >= 0.06 - 1e-6 and K == round(G["NSE_IDX:NIFTY"]["ltp"][s] / 50) * 50, (e2, s, K)
    # live == replay: sliding 2-s windows over the whole day must reproduce the same event set (the no-look-ahead invariance)
    done, s_last = set(), -1; buf = sorted((tuple(r) for g in ticks.values() for r in g[_COLS].itertuples(index=False)), key=lambda r: r[0])
    for t_now in range(T0MS + 10 * 60_000, T0MS + (6 * 3600 + 15 * 60) * 1000 + 1, 120_000):   # a 2-minute step keeps the test fast; each step evaluates every slot up to t_now - 3 s
        part = _trim([r for r in buf if r[0] <= t_now], t_now); s_last = live_step(part, day, done, s_last, None, now_ms=t_now)
    live = {(e, d_, iid, s) for _, e, d_, iid, s in done}; rep = {(e, d_, iid, s) for e, d_, iid, s, _ in evs}
    assert live == rep, (live ^ rep)
    # pricing: V1 at the ATM CE, cell 3/2/60s: entry = ask at +500 ms (size 2000 >= 650 -> best level), target = resting limit, hit when the bid >= entry + 3 (spot +30 -> CE +27)
    e1 = [x for x in evs if x[0] == "V1"][0]; P = price("NIFTY", day, G, [e1], day); r = P[(P.depth == "ATM") & (P.cell == "3/2/60s")].iloc[0]
    g = G[r.iid]; pe = float(g["ask"][e1[3] + LAT]); assert r.filled and r.out == 0 and abs(r.pts - 3.0) < 1e-6 and abs(r.net - (3.0 - _tcharge(pe, pe + 3, 650, SYM["NIFTY"]["tx"]))) < 1e-6, r
    r2 = P[(P.depth == "OTM2") & (P.cell == "10/5/300s")].iloc[0]; assert r2.iid.endswith(f":{int(e1[4]) + 100}:CE"), r2.iid
    assert set(P.depth) == set(DEPTHS) and len(P) == 9
    # the cheap burst trades the burst option itself; placebo slots stay in the same 15-minute bucket
    e5 = [x for x in evs if x[0] == "V5"][0]; P5 = price("NIFTY", day, G, [e5], day); assert set(P5.depth) == {"SELF"} and P5.iid.iloc[0].endswith(":24500:PE")
    print("expiry_bot selftest OK (V1 / V4 / V5 fire once at the hand-computed second, V2 at the hand-computed second and self-consistent, V3 silent, V6 = the chained V1, sliding-window live == full-day replay, "
          "V1 ATM 3/2/60s hand-priced entry + target + charges, OTM2 strike = ATM + 100, V5 trades its own option)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(0)
    if a[0] == "selftest": study_selftest()
    elif a[0] == "replay": study_replay(a[1:] or None)
    elif a[0] == "live": study_live(a[1] if len(a) > 1 else None)
    elif a[0] == "score": study_score(a[1])
    else: print(__doc__); sys.exit(1)
