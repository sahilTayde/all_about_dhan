"""E32: event playbook (paper research; no orders). Founder ask 2026-11-13: buy AND sell, pairs across NIFTY/SENSEX, check every candle,
run the probabilities, define EVENTS so that when one appears the desk knows which action scores highest, how many lots, where to enter and
when to exit. Frozen rules: registry row E32 / side-session note E32_playbook_freeze.md.
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python playbook_lab.py OUT [candles|outcomes|atlas|policy|selftest]

Layers (each cached in OUT/playbook, outside the repo):
  candles():  one row per (sym, day, 5-minute bar b): spot o/h/l/c, ATM IV and OI (CE, PE) at the bar close, the other index's close at the
              same bar, day labels (scen_lab.dfeat), DTE, scheduled events (RBI / FOMC / expiry).  Only bars <= b are used for a row.
  outcomes(): net Rs of every ACTION decided at the close of bar b (filled at the next 1m open), priced by sell_lab.struct (cons mode,
              p75 half-spread, charges x1.5, 10 lots, flat 15:15, bounds flagged `forced`): the honest "what would have happened".
  atlas():    conditional probabilities of the next 15 / 30 / 60 minute spot move given a candle event, walk-forward (base rates and
              event rates from months < m, tested on m), with binomial tests and a spread-aware magnitude check.
  policy():   the playbook: for each event x action, shrunk expected net Rs from months < m; at each decision candle pick the best action
              if its shrunk EV clears the threshold; quarter-Kelly lots within the ladder; one position per index; benchmarks and verdict.
ponytail: 5m decision candles only (ceiling ~70 decisions per sym-day); pricing reuses struct one call per (candle, action)."""
import sys, os, time, pickle, math, itertools, numpy as np, pandas as pd
from multiprocessing import get_context
import opt1y_lab as L
import sell_lab as S
import scen_lab as Z

P, STEP, M0, NB, FLAT, LOT = L.P, L.STEP, L.M0, L.NB, L.FLAT, L.LOT
PB = f"{L.OUT}/playbook"; os.makedirs(PB, exist_ok=True)
import hashlib  # cached tables keyed by the code that makes them (Fable B-1, 2026-11-13: e33/e36 pickles predating the RBI/FOMC fix were reused)
SRC = hashlib.md5(b"".join(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read()
                           for f in ("playbook_lab.py", "opt1y_lab.py", "sell_lab.py", "scen_lab.py"))).hexdigest()[:8]
KEYS = list(L.ALLK); DAYS = sorted({k[1] for k in KEYS}); MONTHS = sorted({L.month(d) for d in DAYS})
TF = 5; B_LO, B_HI = 1, 66          # decision at the close of 5m bar b (minutes 5b..5b+4): b=1 -> 09:24 close, b=66 -> 14:49
EXT = os.environ.get("EXT", f"{L.OUT}/../ext"); L.EXT = EXT


# ---------------------------------------------------------------- candles
def _iv_oi(k, i):
    K = P[k]["atm"][i]; g = lambda sd, c: L._get(k, sd, K, i, c)
    return np.nanmean([g("CE", 5), g("PE", 5)]), g("CE", 4), g("PE", 4), g("CE", 3) + g("PE", 3)


def candles():
    fp = f"{PB}/candles.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    A = Z.labs()[0]; V = L.vol_days().set_index(["sym", "day"]); rows = []
    days = sorted({k[1] for k in KEYS}); fomc1 = L.fomc_next(days)
    SP = {k: pd.Series(P[k]["spot"]).ffill().bfill().values for k in KEYS}
    for k in KEYS:
        s = SP[k]; o = ("SENSEX" if k[0] == "NIFTY" else "NIFTY", k[1]); so = SP.get(o); a = A.loc[k]
        for b in range(0, NB // TF):
            i = TF * b + TF - 1; x = s[TF * b:i + 1]; iv, oic, oip, strad = _iv_oi(k, i)
            rows.append(dict(sym=k[0], day=k[1], b=b, i=i, o=x[0], h=x.max(), l=x.min(), c=x[-1], iv=iv, oi_ce=oic, oi_pe=oip, straddle=strad,
                             oc=so[i] if so is not None else np.nan, dte=P[k]["dte"], d0=P[k]["d0"],
                             GAP=a.GAP, ORW=a.ORW, TREND=a.TREND, PRNG=a.PRNG, IVR=a.IVR, LOC20=a.LOC20, PDH=a.PDH, PDL=a.PDL,
                             or_iv=V.or_iv.get(k, np.nan), har_iv=V.har_iv.get(k, np.nan), rbi=k[1] in L.RBI, fomc=k[1] in fomc1))
    C = pd.DataFrame(rows); C["mo"] = C.day.map(L.month); C.to_pickle(fp); return C


# ---------------------------------------------------------------- candle features (only bars <= b of the same day, plus prior-day labels)
def features():
    """per candle row: body/range, wick ratios, run of same-direction candles, 15m agreement, position vs opening range (first 6 bars) /
    PDH-PDL / session TWAP, realized vol of the last 6 bars vs ATM IV, IV change over 3 bars, IV vs 09:45 IV, efficiency ratio of the
    day so far, NIFTY-SENSEX 3-bar return divergence, OI flow over 3 bars (PE build minus CE build / total), minutes to 15:15."""
    fp = f"{PB}/features.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    C = candles().sort_values(["sym", "day", "b"]).reset_index(drop=True); out = []
    for (sym, day), g in C.groupby(["sym", "day"], sort=False):
        g = g.copy(); st = STEP[sym]; c, o, h, l = g.c.values, g.o.values, g.h.values, g.l.values; rng = np.maximum(h - l, 1e-9)
        g["body"] = (c - o) / rng; g["uw"] = (h - np.maximum(c, o)) / rng; g["lw"] = (np.minimum(c, o) - l) / rng; g["rng_st"] = (h - l) / st
        d = np.sign(c - o); run = np.zeros(len(g))
        for t in range(len(g)): run[t] = d[t] if t == 0 or d[t] != d[t - 1] else run[t - 1] + d[t]
        g["run"] = run
        r1 = np.diff(np.log(c), prepend=np.log(c[0])); g["ret1"] = r1 / 1.0; g["ret3"] = pd.Series(c).pct_change(3).values; g["ret6"] = pd.Series(c).pct_change(6).values
        orh, orl = h[:6].max(), l[:6].min(); g["vs_or"] = np.where(c > orh, 1, np.where(c < orl, -1, 0)); g["or_w"] = (orh - orl) / st
        g["vs_pd"] = np.where(c > g.PDH.values, 1, np.where(c < g.PDL.values, -1, 0))
        tw = np.cumsum(c) / np.arange(1, len(c) + 1); g["vs_twap"] = (c - tw) / st
        rv = pd.Series(r1).rolling(6).std().values * np.sqrt(252 * 75) * 100; g["rv_iv"] = rv / g.iv.values
        g["div3"] = g.iv - g.iv.shift(3); g["iv_vs_open"] = g.iv - g.iv.iloc[min(6, len(g) - 1)]
        er_num = np.abs(c - c[0]); er_den = np.cumsum(np.abs(np.diff(c, prepend=c[0]))); g["er"] = er_num / np.maximum(er_den, 1e-9)
        oc = g.oc.values; g["diverg"] = (pd.Series(c).pct_change(3).values - pd.Series(oc).pct_change(3).values) * 1e4  # bp, this index minus the other
        tot = g.oi_ce.values + g.oi_pe.values; g["oiflow3"] = ((g.oi_pe - g.oi_pe.shift(3)) - (g.oi_ce - g.oi_ce.shift(3))).values / np.where(tot > 0, tot, np.nan)
        g["to_flat"] = FLAT - M0 - g.i.values; g["day_ret"] = (c / c[0] - 1) * 1e4
        out.append(g)
    F = pd.concat(out, ignore_index=True); F.to_pickle(fp); return F


# ---------------------------------------------------------------- E32 frozen: slots, events, actions, exits
import book_lab as B
SLOTS = {30: "0945", 75: "1030", 135: "1130", 225: "1300", 285: "1400"}
EVENTS = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12", "NONE"]
ACTS = ["L_STRAD", "S_STRANGLE1", "L_DIR"]
DESIGNS = [(k, thr) for k in (15, 30) for thr in (250, 500)]  # exactly 4; Bonferroni 4
MIN_LEARN, OOS_FROM = 30, "2026-02"

_DT = {}
def daytab():
    """per (sym, day): prev close c1, prev open o1, prev H/L, 20-day median daily range (prior days only)."""
    if _DT: return _DT
    D = B.daily()
    for sym, g in D.groupby(level=0):
        g = g.reset_index(level=0, drop=True); r = (g.h - g.l); med = r.shift(1).rolling(20).median()
        for day in g.index:
            if (sym, day) in P:
                j = g.index.get_loc(day); pv = g.iloc[j - 1] if j > 0 else None
                _DT[(sym, day)] = dict(c1=pv.c if pv is not None else np.nan, o1=pv.o if pv is not None else np.nan,
                                       er1=abs(pv.c - pv.o) / (pv.h - pv.l) if pv is not None and pv.h > pv.l else np.nan, med20=med.loc[day])
    return _DT


def _rv(s, i, n=30):
    r = np.diff(np.log(s[i - n:i + 1])); r = r[np.isfinite(r)]; return np.sqrt((r ** 2).mean() * 252 * 375) * 100 if len(r) else np.nan


def _maxoi(k, i):
    p = P[k]; st = STEP[k[0]]; Ks = p["atm"][i] + st * np.arange(-3, 4)
    oi = [np.nansum([L._get(k, "CE", x, i, 4), L._get(k, "PE", x, i, 4)]) for x in Ks]; return Ks[int(np.argmax(oi))]


_SP = {}
def spot(k):
    if k not in _SP: _SP[k] = pd.Series(P[k]["spot"]).ffill().bfill().values
    return _SP[k]


def event(k, i):
    """the first true event at slot i (priority order), with the features behind it. Data up to minute i only."""
    s = spot(k); d = daytab()[k]; sym, day = k; o = ("SENSEX" if sym == "NIFTY" else "NIFTY", day); st = STEP[sym]
    gap = s[0] / d["c1"] - 1 if np.isfinite(d["c1"]) else np.nan; iv = S._iv(k, i); iv15 = S._iv(k, i - 15)
    r30 = s[i] / s[i - 30] - 1; r15 = s[i] / s[i - 15] - 1; rv = _rv(s, i); orh, orl = s[:31].max(), s[:31].min()
    ro = spot(o)[i] / spot(o)[i - 30] - 1 if o in P else np.nan
    f = dict(gap=gap, div=iv - iv15, r30=r30, r15=r15, rv_iv=rv / iv if iv > 0 else np.nan, ro30=ro, rng=(s[:i + 1].max() - s[:i + 1].min()) / d["med20"] if d["med20"] > 0 else np.nan)
    rev = np.isfinite(gap) and abs(gap) > 0.005 and np.sign(s[30] - s[0]) == -np.sign(gap); con = np.isfinite(gap) and abs(gap) > 0.005 and np.sign(s[30] - s[0]) == np.sign(gap)
    ev = ("E1" if rev else "E2" if con else "E3" if f["div"] <= -1 else "E4" if (f["div"] >= 1.5 and abs(r15) < 0.002) else
          "E5" if (s[i] > orh * 1.0015 or s[i] < orl * 0.9985) else "E6" if (i >= 135 and f["rng"] < 0.6) else
          "E7" if (np.isfinite(ro) and abs(r30 - ro) > 0.003) else "E8" if (P[k]["d0"] and i >= 225 and abs(_maxoi(k, i) / s[i] - 1) < 0.003) else
          "E9" if ((day in L.RBI and i == 30) or day in L.FOMC) else "E10" if f["rv_iv"] > 1.5 else "E11" if f["rv_iv"] < 0.5 else
          "E12" if (d["er1"] > 0.6 and np.isfinite(gap) and np.sign(gap) == np.sign(d["c1"] - d["o1"]) and gap != 0) else "NONE")
    return ev, f


def cap(k, i): return float(min(2.5, 0.004 * spot(k)[i] / STEP[k[0]]))


def act(k, i, name):
    """one action at slot i, frozen exits: spot 0.4% (<= 2.5 steps), short premium 1.5x credit, else 15:15."""
    c = cap(k, i); s = spot(k)
    if name == "L_STRAD": return S.struct(k, i, S.LSTRAD, sstop=c, mode="cons")
    if name == "S_STRANGLE1": return S.struct(k, i, [("CE", 1, -1), ("PE", -1, -1)], sstop=c, stop=0.5, mode="cons")
    sd = "CE" if s[i] - s[i - 30] >= 0 else "PE"; return S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, s_stp=c, mode="cons")


def table():
    """one row per (sym, day, slot, action) with the event and the priced outcome; PAIR rows (sym=PAIR) under E7 only."""
    fp = f"{PB}/e32_table.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); rows = []; ev = {}
    for k in KEYS:
        for i in SLOTS:
            e, f = event(k, i); ev[(k, i)] = (e, f)
            for a in ACTS:
                r = act(k, i, a)
                if r: rows.append(dict(sym=k[0], day=k[1], i=i, slot=SLOTS[i], event=e, action=a, pnl=r["pnl"], held=r["held"], forced=r["forced"], why=r["why"], **f))
    T = pd.DataFrame(rows); pr = []
    for (k, i), (e, f) in ev.items():
        if e != "E7" or k[0] != "NIFTY": continue
        o = ("SENSEX", k[1]); 
        if o not in P or not np.isfinite(f["ro30"]): continue
        lead, lag = (k, o) if abs(f["r30"]) >= abs(f["ro30"]) else (o, k)
        a, b = act(lag, i, "L_STRAD"), act(lead, i, "S_STRANGLE1"); vl, vs = S._vega(lag, i), S._vega(lead, i)
        if a and b and np.isfinite(vl) and np.isfinite(vs):
            nl, ns = S._size(vl, vs)
            pr.append(dict(sym="PAIR", day=k[1], i=i, slot=SLOTS[i], event="E7", action="PAIR", pnl=a["pnl"] * nl / 10 + b["pnl"] * ns / 10, held=max(a["held"], b["held"]),
                           forced=a["forced"] or b["forced"], why=a["why"] + "/" + b["why"], lag=lag[0], lots=f"{nl}/{ns}", **f))
    T = pd.concat([T, pd.DataFrame(pr)], ignore_index=True); T["mo"] = T.day.map(L.month); T.to_pickle(fp)
    print(f"E32 table {len(T)} rows {time.time() - t0:.0f}s"); return T


# ---------------------------------------------------------------- stage 1: do the events predict the next 45 minutes at all?
def study_atlas():
    T = table(); E = T[T.action == "L_STRAD"][["sym", "day", "i", "event"]].drop_duplicates(); rows = []
    for r in E.itertuples():
        s = spot((r.sym, r.day)); j = min(r.i + 45, NB - 1); rows.append(dict(sym=r.sym, day=r.day, i=r.i, event=r.event, mv=(s[j] / s[r.i] - 1) * 1e4, up=s[j] > s[r.i]))
    A = pd.DataFrame(rows); days = sorted(A.day.unique()); rg = np.random.default_rng(3); base_abs, base_up = A.mv.abs().mean(), A.up.mean()
    out = []
    for e, g in A.groupby("event"):
        d_abs = g.mv.abs().mean() - base_abs; d_up = g.up.mean() - base_up; bs_abs, bs_up = [], []
        gd = {d: x for d, x in g.groupby("day")}; ad = {d: x for d, x in A.groupby("day")}
        for _ in range(2000):
            pick = rg.choice(days, len(days)); G = pd.concat([gd[d] for d in pick if d in gd]) if any(d in gd for d in pick) else None
            Aa = pd.concat([ad[d] for d in pick])
            if G is None or not len(G): continue
            bs_abs.append(G.mv.abs().mean() - Aa.mv.abs().mean()); bs_up.append(G.up.mean() - Aa.up.mean())
        bs_abs, bs_up = np.array(bs_abs), np.array(bs_up)
        out.append(dict(event=e, n=len(g), days=g.day.nunique(), abs_move_bp=round(g.mv.abs().mean(), 1), base_abs_bp=round(base_abs, 1), p_abs=round(2 * min((bs_abs <= 0).mean(), (bs_abs >= 0).mean()), 3),
                        p_up=round(g.up.mean(), 3), base_up=round(base_up, 3), p_sign=round(2 * min((bs_up <= 0).mean(), (bs_up >= 0).mean()), 3), mean_move_bp=round(g.mv.mean(), 1)))
    R = pd.DataFrame(out).set_index("event").reindex([e for e in EVENTS if e in set(A.event)]).reset_index(); pd.set_option("display.width", 250)
    print("STAGE 1 (no selection): next-45-min move after each event vs the base rate of all slots; p = day-block bootstrap, two-sided")
    print(R.to_string(index=False)); R.to_csv(f"{PB}/e32_atlas.csv", index=False); return R


# ---------------------------------------------------------------- policy, benchmarks, verdict
def _cells(Lr, k):
    """shrunk EV per (event, action, slot) from learn rows; prior = pooled learn mean of the action, weight k; needs MIN_LEARN rows."""
    mu = Lr.groupby("action").pnl.mean(); g = Lr.groupby(["event", "action", "slot"]).pnl.agg(["mean", "size"])
    g = g[g["size"] >= MIN_LEARN]; return {idx: (r["size"] * r["mean"] + k * mu[idx[1]]) / (r["size"] + k) for idx, r in g.iterrows()}


def simulate(T, choose, months):
    """sequential: per sym-day, slots in order, one open position per index. choose(row_group) -> action or None.
    row_group = the rows of that (sym, day, slot). Returns trades DataFrame."""
    out = []
    for (sym, day), g in T[T.mo.isin(months) & (T.sym != "PAIR")].groupby(["sym", "day"], sort=True):
        busy = -1
        for i, h in g.groupby("i", sort=True):
            if i <= busy: continue
            a = choose(h)
            if a is None: continue
            r = h[h.action == a]
            if not len(r): continue
            r = r.iloc[0]; out.append(dict(sym=sym, day=day, i=i, slot=r.slot, event=r.event, action=a, pnl=r.pnl, forced=r.forced, mo=r.mo)); busy = i + 1 + r.held
    return pd.DataFrame(out)


def study_policy():
    T = table(); months = MONTHS; oos = [m for m in months if m >= OOS_FROM]; days_oos = sorted(T[T.mo.isin(oos)].day.unique())
    pd.set_option("display.width", 250); res = []; rg = np.random.default_rng(11)
    def daily(tr): return tr.groupby("day").pnl.sum().reindex(days_oos).fillna(0.0) if len(tr) else pd.Series(0.0, index=days_oos)
    # benchmarks
    b1 = simulate(T, lambda h: "S_STRANGLE1" if h.i.iloc[0] == 30 else None, oos)
    b2 = []
    for m in oos:
        Lr = T[(T.mo < m) & (T.sym != "PAIR")]; best = {}
        for sl, g in Lr.groupby("slot"): mu = g.groupby("action").pnl.mean(); best[sl] = mu.idxmax() if mu.max() > 0 else None
        b2.append(simulate(T, lambda h, best=best: best.get(h.slot.iloc[0]), [m]))
    b2 = pd.concat(b2) if any(len(x) for x in b2) else pd.DataFrame(columns=["day", "pnl", "mo"]); d1, d2 = daily(b1), daily(b2)
    print(f"benchmark (i) always short strangle 09:45: OOS net {d1.sum():,.0f} on {len(b1)} trades; (ii) best unconditional action walk-forward: OOS net {d2.sum():,.0f} on {len(b2)} trades")
    for k, thr in DESIGNS:
        tr = []
        for m in oos:
            C = _cells(T[(T.mo < m) & (T.sym != "PAIR")], k)
            def choose(h, C=C):
                e, sl = h.event.iloc[0], h.slot.iloc[0]; best, ba = thr, None
                for a in ACTS:
                    v = C.get((e, a, sl))
                    if v is not None and v > best: best, ba = v, a
                return ba
            tr.append(simulate(T, choose, [m]))
        tr = pd.concat(tr) if any(len(x) for x in tr) else pd.DataFrame(columns=["day", "pnl", "mo", "forced", "event", "action"]); dp = daily(tr)
        ex = dp - d2; mo = ex.groupby(pd.Series(ex.index, index=ex.index).map(L.month)).sum(); pm = dp.groupby(pd.Series(dp.index, index=dp.index).map(L.month)).sum()
        bs = rg.choice(ex.values, (4000, len(ex))).mean(1); p = float((bs <= 0).mean())
        # random policies: same monthly trade count, random (sym-day, slot, action) rows of that month
        rnd = np.zeros(1000)
        for m in oos:
            n = int((tr.mo == m).sum()) if len(tr) else 0; pool = T[(T.mo == m) & (T.sym != "PAIR")].pnl.values
            if n and len(pool): rnd += np.array([rg.choice(pool, n).sum() for _ in range(1000)])
        pct = float((rnd < dp.sum()).mean()); forced = float(tr.forced.mean() * 100) if len(tr) else 0.0
        verdict = ("INCONCLUSIVE" if forced > 10 else "PASS(CANDIDATE)" if (ex.sum() > 0 and p * 4 < 0.05 and (mo > 0).sum() >= 6 and pct >= 0.95 and dp.sum() > 50000) else "PARKED")
        r = dict(k=k, thr=thr, trades=len(tr), oos_net=round(dp.sum()), excess_vs_bench2=round(ex.sum()), p_excess=round(p, 4), p_bonf4=round(min(1, 4 * p), 4), months_pos=f"{(pm > 0).sum()}/{len(oos)}",
                 excess_months_pos=f"{(mo > 0).sum()}/{len(oos)}", beats_random_pct=round(pct * 100, 1), forced_pct=round(forced, 1), verdict=verdict,
                 by_action=tr.groupby("action").pnl.agg(["size", "sum"]).round(0).to_dict("index") if len(tr) else {})
        res.append(r); print(r, flush=True)
    R = pd.DataFrame(res); R.to_csv(f"{PB}/e32_policy.csv", index=False)
    # the playbook as learned on the whole year (display only): event x action mean, n, win
    Pk = T[T.sym != "PAIR"].groupby(["event", "action"]).pnl.agg(n="size", mean="mean", win=lambda x: (x > 0).mean() * 100, total="sum").round(0)
    print("\nPLAYBOOK on the whole year (in-sample, display only):"); print(Pk.unstack(1).to_string())
    pr = T[T.sym == "PAIR"]; print(f"\nPAIR under E7 (reported separately): n {len(pr)}, mean {pr.pnl.mean() if len(pr) else 0:,.0f}, total {pr.pnl.sum() if len(pr) else 0:,.0f}, win {(pr.pnl > 0).mean() * 100 if len(pr) else 0:.0f}%, forced {pr.forced.mean() * 100 if len(pr) else 0:.0f}%")
    print("\nevents per slot (sym-day counts):"); print(T[T.action == "L_STRAD"].groupby(["event", "slot"]).size().unstack(1).fillna(0).astype(int).to_string())
    Pk.to_csv(f"{PB}/e32_playbook.csv"); return R


def study_selftest():
    """event priority on a synthetic day; simulator busy rule; shrinkage arithmetic."""
    k = KEYS[0]; e, f = event(k, 30); assert e in EVENTS and isinstance(f["r30"], float)
    T = pd.DataFrame([dict(sym="N", day="d", i=30, slot="0945", event="E1", action="L_STRAD", pnl=100.0, held=60, forced=False, why="t", mo="m"),
                      dict(sym="N", day="d", i=75, slot="1030", event="E1", action="L_STRAD", pnl=100.0, held=5, forced=False, why="t", mo="m"),
                      dict(sym="N", day="d", i=135, slot="1130", event="E1", action="L_STRAD", pnl=100.0, held=5, forced=False, why="t", mo="m")])
    tr = simulate(T, lambda h: "L_STRAD", ["m"]); assert list(tr.i) == [30, 135], list(tr.i)  # 10:30 skipped: the 09:45 trade is open until 10:46
    Lr = pd.DataFrame(dict(event=["E1"] * 40 + ["E2"] * 40, action="L_STRAD", slot="0945", pnl=[1000.0] * 40 + [-1000.0] * 40))
    C = _cells(Lr, 40); assert abs(C[("E1", "L_STRAD", "0945")] - 500) < 1e-9 and abs(C[("E2", "L_STRAD", "0945")] + 500) < 1e-9  # pooled mean 0, weight 40 = half-way
    assert cap(k, 30) <= 2.5; print("playbook_lab selftest OK")


def study_candles(): C = candles(); print(C.shape); print(C.head(3).to_string())
def study_features(): F = features(); print(F.shape); print(F[["body", "uw", "lw", "run", "vs_or", "vs_pd", "vs_twap", "rv_iv", "div3", "er", "diverg", "oiflow3"]].describe().round(3).to_string())
def study_outcomes():
    O = outcomes(); print(O.groupby("action").pnl.agg(["size", "mean", lambda x: (x > 0).mean()]).round(2).to_string())




# ================================================================ E33: regime x confirmation raw features (frozen thresholds applied later)
SLOTS33 = list(range(30, 316, 15))  # 09:45 .. 14:30 every 15 min


def _bars5(k):
    """5m bars of the day from the spot (o/h/l/c of minute closes) with ADX(14), ER(12), Choppiness(14) computed on the day's own bars
    plus the previous day's bars as warm-up (continuous per sym, as book_lab.bars15)."""
    sym, day = k; prev = [x for x in KEYS if x[0] == sym and x[1] < day]; ks = prev[-1:] + [k]; rows = []
    for kk in ks:
        f = spot(kk)
        for b in range(NB // 5):
            x = f[5 * b:5 * b + 5]; rows.append((kk[1], b, x[0], x.max(), x.min(), x[-1]))
    G = pd.DataFrame(rows, columns=["day", "b", "o", "h", "l", "c"]); h, l, c = G.h.values, G.l.values, G.c.values; n = len(G)
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum.reduce([h - l, abs(h - pc), abs(l - pc)]); rma = lambda x, p: pd.Series(x).ewm(alpha=1 / p, adjust=False).mean().values
    ph, pl = np.r_[h[0], h[:-1]], np.r_[l[0], l[:-1]]; um, dm = h - ph, pl - l
    pdm = np.where((um > dm) & (um > 0), um, 0.0); mdm = np.where((dm > um) & (dm > 0), dm, 0.0); a14 = rma(tr, 14) + 1e-9
    pdi, mdi = 100 * rma(pdm, 14) / a14, 100 * rma(mdm, 14) / a14; G["adx"] = rma(100 * abs(pdi - mdi) / (pdi + mdi + 1e-9), 14); G["pdi"], G["mdi"] = pdi, mdi
    G["er"] = (abs(c - np.r_[[c[0]] * 12, c[:-12]]) / (pd.Series(abs(np.diff(c, prepend=c[0]))).rolling(12).sum().values + 1e-9))
    hh, ll = pd.Series(h).rolling(14).max().values, pd.Series(l).rolling(14).min().values
    G["chop"] = 100 * np.log10(pd.Series(tr).rolling(14).sum().values / np.maximum(hh - ll, 1e-9)) / np.log10(14)
    return G[G.day == day].reset_index(drop=True)


def _fvg(G, b, look=12):
    """unfilled 3-candle fair value gap among bars <= b, within the last `look` bars, that price has retraced INTO at bar b:
    +1 bullish (bar t-2 high < bar t low, close_b inside), -1 bearish, else 0. Latest gap wins."""
    h, l, c = G.h.values, G.l.values, G.c.values; cb = c[b]
    for t in range(b, max(2, b - look), -1):
        if h[t - 2] < l[t]:  # bullish gap between h[t-2] and l[t]
            if l[t + 1:b + 1].min() <= h[t - 2] if t + 1 <= b else False: continue  # filled since
            if h[t - 2] <= cb <= l[t]: return 1
        if l[t - 2] > h[t]:
            if h[t + 1:b + 1].max() >= l[t - 2] if t + 1 <= b else False: continue
            if h[t] <= cb <= l[t - 2]: return -1
    return 0


def _n01(x): return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def _gex(k, i):
    """sign-only gamma exposure proxy over ATM+-3 at minute i: sum OI x gamma x S^2 x 0.01, calls +, puts - (dealer-short-call /
    dealer-short-put convention of the vendor literature). Black-76 gamma from the strike's own IV, T to 15:30 of expiry in trading days."""
    p = P[k]; s = spot(k)[i]; st = STEP[k[0]]; T = max((p["dte"] + (930 - M0 - i) / 375) / 252, 1e-6); g = 0.0
    for off in range(-3, 4):
        K = p["atm"][i] + off * st
        for sd, sg in (("CE", 1), ("PE", -1)):
            iv, oi = L._get(k, sd, K, i, 5), L._get(k, sd, K, i, 4)
            if not (np.isfinite(iv) and np.isfinite(oi) and iv > 0): continue
            v = iv / 100; d1 = (math.log(s / K) + 0.5 * v * v * T) / (v * math.sqrt(T)); gamma = _n01(d1) / (s * v * math.sqrt(T))
            g += sg * oi * gamma * s * s * 0.01
    return g


def _row33(k, i, G, a, d, ivp):
    """one E33 feature row at slot minute i. Look-ahead fixes (2026-11-13, found by the PR #127 session): (a) the 5m bar used is the LAST
    CLOSED bar at or before minute i (bar b closes at minute 5b+4 <= i), not the bar containing i, which closes 4 min later; (b) the
    60-min return is NaN before 10:15 (a negative index would wrap to the end of the day)."""
    s = spot(k); st = STEP[k[0]]; p = P[k]; orh, orl = s[:16].max(), s[:16].min()  # OR 09:15-09:30
    b = (i + 1) // 5 - 1; K = p["atm"][i]; j = i - 15; LAG = 3  # OI on Dhan is ~3 min delayed live: lag it
    oc, op, oc0, op0 = (L._get(k, sd, K, t, 4) for sd, t in (("CE", i - LAG), ("PE", i - LAG), ("CE", j - LAG), ("PE", j - LAG)))
    oiflow = ((op - op0) - (oc - oc0)) / (oc + op) if np.isfinite(oc + op + oc0 + op0) and oc + op > 0 else np.nan
    tv = {}
    for sd in ("CE", "PE"):  # tick rule: sign of the 1m close change x volume, same strike, last 15 bars
        arr = p["C"].get((sd, K)); v = 0.0; tot = 0.0
        if arr is not None:
            cl, vol = arr[j:i + 1, 3], arr[j + 1:i + 1, 6]; dc = np.sign(np.diff(cl)); ok = np.isfinite(dc) & np.isfinite(vol)
            v, tot = float((dc[ok] * vol[ok]).sum()), float(vol[ok].sum())
        tv[sd] = (v, tot)
    oflow = (tv["CE"][0] - tv["PE"][0]) / (tv["CE"][1] + tv["PE"][1]) if tv["CE"][1] + tv["PE"][1] > 0 else np.nan
    x = G.iloc[b]; rng5 = max(x.h - x.l, 1e-9); shape = 1 if (x.c - x.l) / rng5 >= 0.7 and (x.c - x.o) / rng5 > 0.5 else -1 if (x.h - x.c) / rng5 >= 0.7 and (x.o - x.c) / rng5 > 0.5 else 0
    lv = [a.PDH, a.PDL, orh, orl, _maxoi(k, i - 3)]; near = min(abs(s[i] / v - 1) for v in lv if np.isfinite(v))
    gap = s[0] / d["c1"] - 1 if np.isfinite(d["c1"]) else np.nan
    return dict(sym=k[0], day=k[1], i=i, slot=f"{(M0 + i) // 60:02d}{(M0 + i) % 60:02d}", ampm="AM" if i < 165 else "PM", bar5=b,
                adx=x.adx, pdi=x.pdi, mdi=x.mdi, er=x.er, chop=x.chop, r60=(s[i] / s[i - 60] - 1) if i >= 60 else np.nan, r15=s[i] / s[i - 15] - 1, near_level=near,
                gap=gap, rbi=k[1] in L.RBI, fomc=k[1] in L.FOMC, d0=p["d0"], dte=p["dte"], oiflow=oiflow, oflow=oflow, fvg=_fvg(G, b),
                cshape=shape, bias=1 if a.TREND == "UP" else -1 if a.TREND == "DN" else 0, gex=_gex(k, i), iv=S._iv(k, i), rv30=_rv(s, i),
                div15=S._iv(k, i) - S._iv(k, j), maxoi=_maxoi(k, i - 3), day_ret=s[i] / s[0] - 1, ivpct=ivp)


def regime_feats():
    """raw E33 features per (sym, day, slot minute i), data up to minute i only."""
    fp = f"{PB}/e33_feats_{SRC}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); A = Z.labs()[0]; D = daytab(); rows = []; IVP = L.vol_days().set_index(["sym", "day"]).ivpct.to_dict()
    for k in KEYS:
        G = _bars5(k); a = A.loc[k]; d = D[k]
        for i in SLOTS33: rows.append(_row33(k, i, G, a, d, IVP.get(k, np.nan)))
    F = pd.DataFrame(rows); F["mo"] = F.day.map(L.month); F.to_pickle(fp); print(f"e33 feats {len(F)} rows {time.time() - t0:.0f}s"); return F


def study_selftest33():
    """look-ahead check: the E33 row at slot i must be identical after every minute > i (spot and every contract series) is scrambled."""
    import copy
    A = Z.labs()[0]; D = daytab(); rg = np.random.default_rng(7)
    for k, i in ((KEYS[20], 45), (KEYS[21], 30), (KEYS[300], 135)):
        orig = copy.deepcopy(P[k]); _SP.pop(k, None); G = _bars5(k); r0 = _row33(k, i, G, A.loc[k], D[k], 0.5)
        assert 5 * r0["bar5"] + 4 <= i, (r0["bar5"], i)
        P[k]["spot"][i + 1:] *= rg.uniform(0.9, 1.1, NB - i - 1)
        for key, arr in P[k]["C"].items(): arr[i + 1:] *= rg.uniform(0.5, 1.5, (NB - i - 1, 1))
        _SP.pop(k, None); S._EXT.clear(); G2 = _bars5(k); r1 = _row33(k, i, G2, A.loc[k], D[k], 0.5)
        P[k] = orig; _SP.pop(k, None); S._EXT.clear()
        for f in r0:
            a, b = r0[f], r1[f]
            same = (a == b) or (isinstance(a, float) and isinstance(b, float) and (np.isnan(a) and np.isnan(b) or abs(a - b) < 1e-9))
            assert same, f"look-ahead in {f} at {k} slot {i}: {a} vs {b}"
        assert (i < 60) == (not np.isfinite(r0["r60"])), (i, r0["r60"])
    print("E33 look-ahead known answers OK (closed 5m bar, r60 guard; 3 sym-day slots, all fields unchanged after scrambling the future)")


def study_feats33():
    F = regime_feats(); pd.set_option("display.width", 250)
    print(F[["adx", "er", "chop", "near_level", "oiflow", "oflow", "fvg", "cshape", "gex", "div15"]].describe().round(3).to_string())
    print("fvg counts", F.fvg.value_counts().to_dict(), "cshape", F.cshape.value_counts().to_dict(), "gex>0 share", (F.gex > 0).mean().round(3))



# ---------------------------------------------------------------- E33 actions: naked CE/PE buy and sell, strangle, straddle; super-order exits
X33 = dict(l_stop=0.30, l_tgt=0.60, l_trail=0.20, s_stop=0.5, s_tgt=0.5, cap=2.5)  # frozen in E33 rule 6 (critic may set the numbers)
ACTS33 = ["L_CE", "L_PE", "S_CE", "S_PE", "S_STRANGLE1", "L_STRAD"]


def long_leg(k, i, sd, X=X33):
    """E33 rule 6, long single leg on 1-min bars: SL X[l_stop] of the entry premium, intrabar (fill = min(trigger, bar open) - half-spread);
    target +X[l_tgt] fills AT the target only if the bar high >= target + 1 tick + half-spread (a resting limit got hit through);
    trailing = fixed jump X[l_trail] x entry (SL rises one jump per jump of new high, Dhan super-trail semantics); spot adverse cap
    (next open); else the 15:15 open; SL beats target in the same bar; strike leaves the window -> last close, forced (D7: forfeits gains)."""
    sym = k[0]; p = P[k]; a, K = L.contract(k, i, sd, 0); e = i + 1; xe = FLAT - M0
    if a is None or not np.isfinite(a[e, 0]) or L.stale(a, e): return None
    d0 = p["d0"]; en = a[e, 0] + L.hs(sym, d0, M0 + e, a[e, 0]); J = X["l_trail"] * en; sl0 = en * (1 - X["l_stop"]); tp = en * (1 + X["l_tgt"])
    s = spot(k); s0 = s[e]; dirn = 1 if sd == "CE" else -1; capv = min(X["cap"], 0.004 * s0 / STEP[sym]) * STEP[sym]
    sl, hi, x, why, forced, j = sl0, en, None, None, False, e
    for j in range(e, xe):
        o, h, l, c = a[j, :4]
        if not np.isfinite(o): x, forced, why = a[j - 1, 3], True, "window"; break
        if l <= sl: x, why = min(sl, o), "sl"; break
        if h >= tp + 0.05 + L.hs(sym, d0, M0 + j, tp): x, why = tp, "tgt"; break
        hi = max(hi, h); sl = max(sl, sl0 + J * math.floor((hi - en) / J)) if J > 0 else sl
        if dirn * (s[j] - s0) <= -capv and j + 1 < xe: j += 1; x, why = (a[j, 0] if np.isfinite(a[j, 0]) else c), "cap"; break
    if x is None: j = xe; x, why = (a[j, 0] if np.isfinite(a[j, 0]) else a[j - 1, 3]), "time"
    if why != "tgt": x = max(x - L.hs(sym, d0, M0 + min(j, NB - 1), x), 0.05)
    kc = k if L.COSTS == "dated" else None
    return dict(pnl=(x - en) * L.qty(sym, kc) - L.cost(en, x, sym, kc), held=j - e, forced=forced, why=why, credit=-en)


def act33(k, i, name, X=X33):
    """long legs: long_leg (rule 6); short legs and structures: sell_lab.struct (close-based triggers filled at the NEXT open +- half-spread,
    cons bounds). Strangle spot cap 2.0 steps so both legs stay inside the taped window."""
    s = spot(k); st = STEP[k[0]]; c = min(X["cap"], 0.004 * s[i] / st)
    if name in ("L_CE", "L_PE"): return long_leg(k, i, name[2:], X)
    if name in ("S_CE", "S_PE"): return S.struct(k, i, [(name[2:], 0, -1)], stop=X["s_stop"], tgt=X["s_tgt"], sstop=c, mode="cons")
    if name == "S_STRANGLE1": return S.struct(k, i, [("CE", 1, -1), ("PE", -1, -1)], stop=X["s_stop"], tgt=X["s_tgt"], sstop=min(c, 2.0), mode="cons")
    return S.struct(k, i, S.LSTRAD, sstop=c, mode="cons")


def _price33(k):
    return k, [(i, a, r["pnl"], r["held"], r["forced"], r["why"]) for i in SLOTS33 for a in ACTS33 for r in [act33(k, i, a)] if r]


def table33():
    fp = f"{PB}/e33_table_{SRC}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); rows = []
    with get_context("fork").Pool(max(1, os.cpu_count() - 1)) as pool:
        for k, out in pool.imap_unordered(_price33, KEYS, chunksize=4):
            rows += [dict(sym=k[0], day=k[1], i=i, action=a, pnl=p_, held=h, forced=f, why=w) for i, a, p_, h, f, w in out]
    T = pd.DataFrame(rows).merge(regime_feats(), on=["sym", "day", "i"], how="left"); T.to_pickle(fp)
    print(f"e33 table {len(T)} rows {time.time() - t0:.0f}s"); return T


def study_table33():
    T = table33(); pd.set_option("display.width", 250)
    print(T.groupby("action").agg(n=("pnl", "size"), mean=("pnl", "mean"), win=("pnl", lambda x: (x > 0).mean() * 100), forced=("forced", "mean")).round(2).to_string())


# ---------------------------------------------------------------- E33 states, gates, policy
REGIMES = ["EVENT", "TREND_UP", "TREND_DN", "LEVEL", "CHOP"]; CONFS = ["BULL", "NEUT", "BEAR"]; CELLS = [f"{r}|{c}" for r in REGIMES for c in CONFS]
ACTS33N = ACTS33 + ["NONE"]; DESIGNS33 = [(k, thr) for k in (15, 30) for thr in (250, 500)]


def states(F):
    F = F.copy(); ev = (F.rbi & (F.i == 30)) | F.fomc | ((F.d0 == 1) & (F.i >= 225)) | (F.gap.abs() > 0.005)
    tr = ((F.adx >= 25).astype(int) + (F.er >= 0.35).astype(int) + (F.chop <= 45).astype(int)) >= 2
    tr = tr & np.isfinite(F.r60)  # before 10:15 the 60-min return is unavailable: no trend direction, fall through to LEVEL / CHOP
    F["regime"] = np.where(ev, "EVENT", np.where(tr, np.where(F.r60 > 0, "TREND_UP", "TREND_DN"), np.where(F.near_level <= 0.0015, "LEVEL", "CHOP")))
    v = np.sign(F.oiflow.fillna(0)) + np.sign(F.oflow.fillna(0)) + F.fvg + F.cshape + F.bias; F["votes"] = v
    F["conf"] = np.where(v >= 2, "BULL", np.where(v <= -2, "BEAR", "NEUT")); F["cell"] = F.regime + "|" + F.conf
    s_ = {k: spot(k) for k in KEYS}; F["mv45"] = [(s_[(a, b)][min(i + 45, NB - 1)] / s_[(a, b)][i] - 1) * 1e4 for a, b, i in zip(F.sym, F.day, F.i)]
    return F


def _dayboot(F, fn, n=2000, seed=5):
    """day-block bootstrap (both indices of a day = one block) of statistic fn(frame) -> array."""
    rg = np.random.default_rng(seed); days = sorted(F.day.unique()); G = {d: g for d, g in F.groupby("day")}; out = []
    for _ in range(n):
        pick = rg.choice(days, len(days)); out.append(fn(pd.concat([G[d] for d in pick])))
    return np.array(out)


def study_gates33():
    """Q2: does CONF predict the sign of the next 45 min? Q1: does REGIME predict its size? Whole year (no fitted parameter), day-block."""
    F = states(regime_feats()); F = F[np.isfinite(F.mv45)]; up = F.mv45 > 0
    bull, bear = F[F.conf == "BULL"], F[F.conf == "BEAR"]; d_obs = (bull.mv45 > 0).mean() - (bear.mv45 > 0).mean()
    bs = _dayboot(F, lambda G: (G[G.conf == "BULL"].mv45 > 0).mean() - (G[G.conf == "BEAR"].mv45 > 0).mean())
    p2 = 2 * min((bs <= 0).mean(), (bs >= 0).mean()); base = up.mean()
    print(f"Q2 (direction): P(up|BULL) {(bull.mv45 > 0).mean():.3f} (n {len(bull)}), P(up|BEAR) {(bear.mv45 > 0).mean():.3f} (n {len(bear)}), base {base:.3f}, "
          f"diff {d_obs:+.3f}, day-block p {p2:.3f} -> {'CONF PREDICTS DIRECTION: directional actions stay' if p2 < 0.05 else 'NO: L_CE/L_PE/S_CE/S_PE REMOVED from the policy'}")
    print("  mean signed move bp | BULL %.1f  NEUT %.1f  BEAR %.1f" % (bull.mv45.mean(), F[F.conf == "NEUT"].mv45.mean(), bear.mv45.mean()))
    for v_, g in F.groupby("votes"): print(f"  votes {int(v_):+d}: n {len(g)} P(up) {(g.mv45 > 0).mean():.3f} mean {g.mv45.mean():+.1f} bp")
    print("Q1 (size): |45-min move| bp by REGIME vs base %.1f" % F.mv45.abs().mean())
    for r in REGIMES:
        g = F[F.regime == r]
        if not len(g): continue
        bsr = _dayboot(F, lambda G, r=r: G[G.regime == r].mv45.abs().mean() - G.mv45.abs().mean(), n=1000)
        print(f"  {r:9s} n {len(g):5d} |move| {g.mv45.abs().mean():5.1f} P(up) {(g.mv45 > 0).mean():.3f} p_size {2 * min((bsr <= 0).mean(), (bsr >= 0).mean()):.3f}")
    print("cells (sym-day-slot counts):"); print(F.groupby(["regime", "conf"]).size().unstack(1).fillna(0).astype(int).to_string())
    json_ = dict(q2_p=float(p2), directional=bool(p2 < 0.05)); pickle.dump(json_, open(f"{PB}/e33_gate.pkl", "wb")); return json_


def arrays33(T):
    """per sym-day: slots x actions pnl/held matrices and the cell per slot, for fast sequential policy runs."""
    T = T.sort_values(["sym", "day", "i"]); A = {}
    for (sym, day), g in T.groupby(["sym", "day"], sort=False):
        pn = np.full((len(SLOTS33), len(ACTS33N)), np.nan); hd = np.zeros((len(SLOTS33), len(ACTS33N)), int); cell = [None] * len(SLOTS33); fc = np.zeros_like(pn, bool)
        for r in g.itertuples():
            si, ai = SLOTS33.index(r.i), ACTS33N.index(r.action); pn[si, ai] = r.pnl; hd[si, ai] = r.held; cell[si] = r.cell; fc[si, ai] = r.forced
        pn[:, -1] = 0.0; A[(sym, day)] = (pn, hd, cell, fc, L.month(day))
    return A


def run33(A, table_for_month, months):
    """sequential execution: at each slot when flat, action = table_for_month(mo)[cell] (index into ACTS33N) -> trades list."""
    out = []
    for (sym, day), (pn, hd, cell, fc, mo) in A.items():
        if mo not in months: continue
        tbl = table_for_month(mo); busy = -1
        for si, i in enumerate(SLOTS33):
            if i <= busy or cell[si] is None: continue
            ai = tbl.get(cell[si], len(ACTS33N) - 1)
            if ai == len(ACTS33N) - 1 or not np.isfinite(pn[si, ai]): continue
            out.append((sym, day, i, cell[si], ACTS33N[ai], pn[si, ai], fc[si, ai], mo)); busy = i + 1 + hd[si, ai]
    return pd.DataFrame(out, columns=["sym", "day", "i", "cell", "action", "pnl", "forced", "mo"])


def study_policy33():
    gate = pickle.load(open(f"{PB}/e33_gate.pkl", "rb")); acts = ACTS33 if gate["directional"] else ["S_STRANGLE1", "L_STRAD"]
    print(f"Q2 gate: directional actions {'kept' if gate['directional'] else 'REMOVED'} (p {gate['q2_p']:.3f}); actions in play: {acts}")
    T = table33(); F = states(regime_feats())[["sym", "day", "i", "cell"]]; T = T.merge(F, on=["sym", "day", "i"]); T["mo"] = T.day.map(L.month)
    T = T[T.action.isin(acts)]; A = arrays33(T); oos = [m for m in MONTHS if m >= OOS_FROM]; days_oos = sorted(T[T.mo.isin(oos)].day.unique())
    daily = lambda tr: tr.groupby("day").pnl.sum().reindex(days_oos).fillna(0.0) if len(tr) else pd.Series(0.0, index=days_oos)
    NONE = len(ACTS33N) - 1; rg = np.random.default_rng(13); pd.set_option("display.width", 250)
    # benchmarks
    b1 = run33(A, lambda mo: {c: ACTS33N.index("S_STRANGLE1") for c in CELLS}, oos); b1 = b1[b1.i == 30]; d1 = daily(b1)
    best_un = {}
    for m in oos:
        mu = T[T.mo < m].groupby("action").pnl.mean(); best_un[m] = ACTS33N.index(mu.idxmax()) if mu.max() > 0 else NONE
    b2 = run33(A, lambda mo: {c: best_un[mo] for c in CELLS}, oos); d2 = daily(b2)
    print(f"benchmark (i) always short strangle 09:45: OOS {d1.sum():,.0f} on {len(b1)}; (ii) best unconditional action walk-forward: OOS {d2.sum():,.0f} on {len(b2)} "
          f"({ {m: ACTS33N[a] for m, a in best_un.items()} })")
    # random state->action tables (null for the map itself)
    rnd_tbls = [{c: int(rg.integers(0, len(ACTS33N))) for c in CELLS} for _ in range(1000)]
    rnd = np.array([run33(A, lambda mo, t=t: t, oos).pnl.sum() for t in rnd_tbls]); print(f"random state->action tables: median OOS {np.median(rnd):,.0f}, 95th pct {np.percentile(rnd, 95):,.0f}")
    res = []
    for k, thr in DESIGNS33:
        tabs = {}
        for m in oos:
            Lr = T[T.mo < m]; g = Lr.groupby(["cell", "action"]).pnl.agg(["mean", "size"]); g = g[g["size"] >= MIN_LEARN]
            ev = {idx: r["size"] * r["mean"] / (r["size"] + k) for idx, r in g.iterrows()}  # prior 0: a cell earns its trade
            tbl = {}
            for c in CELLS:
                cand = [(v, a) for (cc, a), v in ev.items() if cc == c and v > thr]
                tbl[c] = ACTS33N.index(max(cand)[1]) if cand else NONE
            tabs[m] = tbl
        tr = run33(A, lambda mo: tabs[mo], oos); dp = daily(tr); ex = dp - d2
        mo_ex = ex.groupby(pd.Series(ex.index, index=ex.index).map(L.month)).sum(); mo_p = dp.groupby(pd.Series(dp.index, index=dp.index).map(L.month)).sum()
        bs = rg.choice(ex.values, (4000, len(ex))).mean(1); p = float((bs <= 0).mean()); pct = float((rnd < dp.sum()).mean()); forced = float(tr.forced.mean() * 100) if len(tr) else 0.0
        verdict = "INCONCLUSIVE" if forced > 10 else "PASS(CANDIDATE)" if (ex.sum() > 0 and 4 * p < 0.05 and (mo_ex > 0).sum() >= 6 and pct >= 0.95 and dp.sum() > 50000) else "PARKED"
        r = dict(k=k, thr=thr, trades=len(tr), oos_net=round(dp.sum()), win=round((tr.pnl > 0).mean() * 100, 1) if len(tr) else np.nan, excess_vs_bench=round(ex.sum()), p=round(p, 4), p_bonf4=round(min(1, 4 * p), 4),
                 months_pos=f"{(mo_p > 0).sum()}/9", excess_months_pos=f"{(mo_ex > 0).sum()}/9", beats_random_tables_pct=round(100 * pct, 1), forced_pct=round(forced, 1), verdict=verdict,
                 by_action=tr.groupby("action").pnl.agg(["size", "sum"]).round(0).to_dict("index") if len(tr) else {})
        res.append(r); print(r, flush=True)
    R = pd.DataFrame(res); R.to_csv(f"{PB}/e33_policy.csv", index=False)
    # founder deliverable: per (cell, action) n, EV, P(profit), median, 90% CI (day-block), OOS mean
    rows = []
    for (c, a), g in T.groupby(["cell", "action"]):
        bsm = _dayboot(g, lambda G: G.pnl.mean(), n=500, seed=1); o = g[g.mo >= OOS_FROM]
        rows.append(dict(cell=c, action=a, n=len(g), EV=round(g.pnl.mean()), p_profit=round((g.pnl > 0).mean() * 100, 1), median=round(g.pnl.median()),
                         ci90_lo=round(np.percentile(bsm, 5)), ci90_hi=round(np.percentile(bsm, 95)), oos_n=len(o), oos_EV=round(o.pnl.mean()) if len(o) else np.nan, forced_pct=round(g.forced.mean() * 100, 1)))
    Cc = pd.DataFrame(rows); Cc.to_csv(f"{PB}/e33_cells.csv", index=False)
    print("\nPLAYBOOK TABLE (whole year; EV per trade at 10 lots; 90% CI by day-block bootstrap):"); print(Cc.sort_values(["cell", "action"]).to_string(index=False))
    print("\nsplits (mean P&L per trade): AM/PM, GEX sign, IV-rank tercile"); T["gexs"] = np.where(T.gex > 0, "GEX+", "GEX-"); T["ivr"] = pd.cut(T.ivpct, [-0.01, 0.33, 0.67, 1.01], labels=["IVlow", "IVmid", "IVhigh"])
    for col in ("ampm", "gexs", "ivr"): print(T.groupby([col, "action"], observed=True).pnl.mean().round(0).unstack(1).to_string())
    return R


# ---------------------------------------------------------------- E34: confirmation layer net of drift (frozen; reuses E33 tables)
def _policy_run(T, A, oos, k, thr, cells):
    """E33 EB policy (prior 0, n >= 30) learned on T's `cell` column, executed by run33 on arrays A (whose cell labels must match T)."""
    NONE = len(ACTS33N) - 1; tabs = {}
    for m in oos:
        g = T[T.mo < m].groupby(["cell", "action"]).pnl.agg(["mean", "size"]); g = g[g["size"] >= MIN_LEARN]
        ev = {idx: r["size"] * r["mean"] / (r["size"] + k) for idx, r in g.iterrows()}; tbl = {}
        for c in cells:
            cand = [(v, a) for (cc, a), v in ev.items() if cc == c and v > thr]; tbl[c] = ACTS33N.index(max(cand)[1]) if cand else NONE
        tabs[m] = tbl
    return run33(A, lambda mo: tabs[mo], oos)


def study_e34():
    gate = pickle.load(open(f"{PB}/e33_gate.pkl", "rb")); acts = ACTS33 if gate["directional"] else ["S_STRANGLE1", "L_STRAD"]
    T0 = table33(); F = states(regime_feats())[["sym", "day", "i", "cell", "regime", "conf"]]; T0 = T0.merge(F, on=["sym", "day", "i"]); T0["mo"] = T0.day.map(L.month); T0 = T0[T0.action.isin(acts)]
    oos = [m for m in MONTHS if m >= OOS_FROM]; days_oos = sorted(T0[T0.mo.isin(oos)].day.unique()); rg = np.random.default_rng(34)
    daily = lambda tr: tr.groupby("day").pnl.sum().reindex(days_oos).fillna(0.0) if len(tr) else pd.Series(0.0, index=days_oos)
    def relabel(T, cellcol):
        T = T.copy(); T["cell"] = cellcol; return T
    # shuffled CONF labels per sym-day across its slots (regime and outcomes untouched); the same permutation for every action row of a slot
    slots = F[["sym", "day", "i", "conf"]].drop_duplicates(); shuffles = []
    for _ in range(200):
        parts = []
        for (sym, day), g in slots.groupby(["sym", "day"], sort=False): parts.append(g.assign(conf2=rg.permutation(g.conf.values)))
        shuffles.append(pd.concat(parts)[["sym", "day", "i", "conf2"]])
    res = []
    for k, thr in DESIGNS33:
        full = _policy_run(T0, arrays33(T0), oos, k, thr, CELLS); d_full = daily(full)
        Tr = relabel(T0, T0.regime); reg = _policy_run(Tr, arrays33(Tr), oos, k, thr, REGIMES); d_reg = daily(reg)
        fl = T0.conf.map({"BULL": "BEAR", "BEAR": "BULL", "NEUT": "NEUT"}); Tf = relabel(T0, T0.regime + "|" + fl); flip = _policy_run(Tf, arrays33(Tf), oos, k, thr, CELLS); d_flip = daily(flip)
        sh = []
        for S_ in shuffles:
            Ts = T0.merge(S_, on=["sym", "day", "i"]); Ts = relabel(Ts, Ts.regime + "|" + Ts.conf2); sh.append(daily(_policy_run(Ts, arrays33(Ts), oos, k, thr, CELLS)).sum())
        sh = np.array(sh); ex = d_full - d_reg; mo = ex.groupby(pd.Series(ex.index, index=ex.index).map(L.month)).sum()
        bs = rg.choice(ex.values, (4000, len(ex))).mean(1); p = float((bs <= 0).mean()); pct = float((sh < d_full.sum()).mean())
        ok = ex.sum() > 0 and 4 * p < 0.05 and (mo > 0).sum() >= 6 and pct >= 0.95 and d_flip.sum() < d_full.sum()
        r = dict(k=k, thr=thr, full_oos=round(d_full.sum()), full_trades=len(full), regime_only_oos=round(d_reg.sum()), regime_trades=len(reg), excess=round(ex.sum()),
                 p=round(p, 4), p_bonf4=round(min(1, 4 * p), 4), excess_months_pos=f"{(mo > 0).sum()}/9", shuffle_median=round(float(np.median(sh))), shuffle_p95=round(float(np.percentile(sh, 95))),
                 beats_shuffles_pct=round(100 * pct, 1), flip_oos=round(d_flip.sum()), verdict="PASS" if ok else "LEAD ONLY")
        res.append(r); print(r, flush=True)
    R = pd.DataFrame(res); R.to_csv(f"{PB}/e34.csv", index=False); return R


# ================================================================ E36: candle-sequence atlas (frozen; every closed 5m bar 09:45-14:30)
B36 = list(range(5, 58)); H36 = (15, 30, 45); HALF = "2026-04-24"
PAT_DIR = {"bull_body": 1, "bear_body": -1, "hammer": 1, "star": -1, "up3": 1, "dn3": -1, "engulf_bull": 1, "engulf_bear": -1, "inside_break_up": 1,
           "inside_break_dn": -1, "hl3": 1, "lh3": -1, "new_hi": 1, "new_lo": -1, "or_break_up": 1, "or_break_dn": -1, "failed_up": -1, "failed_dn": 1,
           "pdh_reject": -1, "pdl_reject": 1, "triple_top": -1, "triple_bot": 1, "twap_hi2": -1, "twap_lo2": 1,
           "doji": 0, "outside": 0, "compress": 0, "iv_up_flat": 0, "iv_dn": 0, "oi_wall": 0, "prem_bleed": 0}


def e36_rows(k):
    """pattern flags at every closed 5m bar b (minute i = 5b+4) of one sym-day, data <= i only; forward moves for the atlas."""
    s = spot(k); st = STEP[k[0]]; p = P[k]; a = Z.labs()[0].loc[k]; pdh, pdl = a.PDH, a.PDL
    o = np.array([s[5 * b] for b in range(75)]); c = np.array([s[5 * b + 4] for b in range(75)])
    h = np.array([s[5 * b:5 * b + 5].max() for b in range(75)]); l = np.array([s[5 * b:5 * b + 5].min() for b in range(75)])
    rng = np.maximum(h - l, 1e-9); body = (c - o) / rng; uw = (h - np.maximum(c, o)) / rng; lw = (np.minimum(c, o) - l) / rng
    orh, orl = s[:16].max(), s[:16].min(); out = []; broke_up = broke_dn = None
    tw = np.cumsum(s) / np.arange(1, NB + 1); dev = s - tw
    for b in B36:
        i = 5 * b + 4; med_rng = np.median(rng[:b + 1]); shi, slo = h[:b].max(), l[:b].min()  # session high/low BEFORE this bar
        f = dict(bull_body=body[b] > 0.6 and rng[b] > med_rng, bear_body=body[b] < -0.6 and rng[b] > med_rng, doji=abs(body[b]) < 0.1,
                 hammer=lw[b] >= 0.6, star=uw[b] >= 0.6, up3=all(c[b - t] > o[b - t] for t in range(3)), dn3=all(c[b - t] < o[b - t] for t in range(3)),
                 engulf_bull=c[b] > o[b] and c[b - 1] < o[b - 1] and c[b] > o[b - 1] and o[b] < c[b - 1],
                 engulf_bear=c[b] < o[b] and c[b - 1] > o[b - 1] and c[b] < o[b - 1] and o[b] > c[b - 1],
                 inside_break_up=h[b - 1] <= h[b - 2] and l[b - 1] >= l[b - 2] and c[b] > h[b - 1], inside_break_dn=h[b - 1] <= h[b - 2] and l[b - 1] >= l[b - 2] and c[b] < l[b - 1],
                 outside=h[b] > h[b - 1] and l[b] < l[b - 1], hl3=l[b] > l[b - 1] > l[b - 2], lh3=h[b] < h[b - 1] < h[b - 2],
                 new_hi=c[b] > shi, new_lo=c[b] < slo, or_break_up=False, or_break_dn=False, failed_up=False, failed_dn=False,
                 pdh_reject=np.isfinite(pdh) and abs(h[b] / pdh - 1) < 0.001 and uw[b] >= 0.5 and c[b] < pdh,
                 pdl_reject=np.isfinite(pdl) and abs(l[b] / pdl - 1) < 0.001 and lw[b] >= 0.5 and c[b] > pdl,
                 triple_top=False, triple_bot=False, twap_hi2=False, twap_lo2=False, compress=False, iv_up_flat=False, iv_dn=False, oi_wall=False, prem_bleed=False)
        if c[b] > orh and broke_up is None: f["or_break_up"] = True; broke_up = b
        if c[b] < orl and broke_dn is None: f["or_break_dn"] = True; broke_dn = b
        if broke_up is not None and 0 < b - broke_up <= 3 and orl <= c[b] <= orh: f["failed_up"] = True; broke_up = -99
        if broke_dn is not None and 0 < b - broke_dn <= 3 and orl <= c[b] <= orh: f["failed_dn"] = True; broke_dn = -99
        w = slice(max(0, b - 11), b + 1); hh = h[:b + 1].max(); ll = l[:b + 1].min()
        if (h[w] >= hh * 0.9995).sum() >= 3 and c[b] <= hh and c[b] < o[b]: f["triple_top"] = True
        if (l[w] <= ll * 1.0005).sum() >= 3 and c[b] >= ll and c[b] > o[b]: f["triple_bot"] = True
        sd = dev[max(0, i - 60):i + 1].std()
        if sd > 0: f["twap_hi2"] = dev[i] > 2 * sd; f["twap_lo2"] = dev[i] < -2 * sd
        if b >= 18: f["compress"] = (h[b - 5:b + 1].max() - l[b - 5:b + 1].min()) < 0.5 * (h[b - 17:b - 5].max() - l[b - 17:b - 5].min())
        iv0, iv3 = S._iv(k, i), S._iv(k, i - 15)
        if np.isfinite(iv0) and np.isfinite(iv3):
            f["iv_up_flat"] = iv0 - iv3 >= 1 and abs(s[i] / s[i - 15] - 1) < 0.002; f["iv_dn"] = iv0 - iv3 <= -1
        Km = _maxoi(k, i - 3)
        if abs(Km - s[i]) <= st:
            side = np.sign(Km - s[i]); crosses = sum((side > 0 and h[b - t] >= Km) or (side < 0 and l[b - t] <= Km) for t in range(6))
            f["oi_wall"] = crosses >= 3 and (c[b] < Km if side > 0 else c[b] > Km)
        K0, K6 = p["atm"][i], p["atm"][i - 30]
        st0 = L._get(k, "CE", K0, i, 3) + L._get(k, "PE", K0, i, 3); st6 = L._get(k, "CE", K6, i - 30, 3) + L._get(k, "PE", K6, i - 30, 3)
        if np.isfinite(st0) and np.isfinite(st6) and st6 > 0: f["prem_bleed"] = st0 / st6 - 1 <= -0.10 and abs(s[i] / s[i - 30:i + 1].mean() - 1) < 0.001
        mv = {f"mv{hz}": (s[min(i + hz, NB - 1)] / s[i] - 1) * 1e4 for hz in H36}
        out.append(dict(sym=k[0], day=k[1], b=b, i=i, d0=p["d0"], **{n: bool(v) for n, v in f.items()}, **mv))
    return out


def e36_table():
    fp = f"{PB}/e36_rows_{SRC}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); rows = []
    for k in KEYS: rows += e36_rows(k)
    R = pd.DataFrame(rows); R.to_pickle(fp); print(f"e36 rows {len(R)} {time.time() - t0:.0f}s"); return R


def _bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); q = np.empty(n); r = p[o] * n / (np.arange(n) + 1)
    q[o] = np.minimum.accumulate(r[::-1])[::-1]; return np.minimum(q, 1)


def _e36_price(args):
    k, i, dirn = args; out = {}
    if dirn: r = long_leg(k, i, "CE" if dirn > 0 else "PE"); out["long"] = r["pnl"] if r else np.nan
    r = act33(k, i, "S_STRANGLE1"); out["strangle"] = r["pnl"] if r else np.nan
    r = act33(k, i, "L_STRAD"); out["straddle"] = r["pnl"] if r else np.nan
    return k, i, dirn, out


def study_e36():
    R = e36_table(); days = sorted(R.day.unique()); rg = np.random.default_rng(36); pats = list(PAT_DIR); rows = []
    base_up = {hz: (R[f"mv{hz}"] > 0).mean() for hz in H36}; base_abs = {hz: R[f"mv{hz}"].abs().mean() for hz in H36}
    G = {d: g for d, g in R.groupby("day")}
    def boot(stat, n=2000):
        return np.array([stat(pd.concat([G[d] for d in rg.choice(days, len(days))])) for _ in range(n)])
    for pt in pats:
        g = R[R[pt]]
        if len(g) < 30: rows += [dict(pattern=pt, horizon=hz, n=len(g), verdict="TOO FEW") for hz in H36]; continue
        for hz in H36:
            m = f"mv{hz}"; d_up = (g[m] > 0).mean() - base_up[hz]; d_abs = g[m].abs().mean() - base_abs[hz]
            bs = boot(lambda X, pt=pt, m=m: np.array([(X[X[pt]][m] > 0).mean() - (X[m] > 0).mean(), X[X[pt]][m].abs().mean() - X[m].abs().mean()]) if X[pt].any() else np.array([np.nan, np.nan]), 1000)
            bs = bs[np.isfinite(bs).all(1)]; p_sign = 2 * min((bs[:, 0] <= 0).mean(), (bs[:, 0] >= 0).mean()); p_size = 2 * min((bs[:, 1] <= 0).mean(), (bs[:, 1] >= 0).mean())
            h1, h2 = g[g.day < HALF], g[g.day >= HALF]; R1, R2 = R[R.day < HALF], R[R.day >= HALF]
            d1 = (h1[m] > 0).mean() - (R1[m] > 0).mean() if len(h1) >= 10 else np.nan; d2 = (h2[m] > 0).mean() - (R2[m] > 0).mean() if len(h2) >= 10 else np.nan
            rows.append(dict(pattern=pt, horizon=hz, n=len(g), days=g.day.nunique(), p_up=round((g[m] > 0).mean(), 3), base_up=round(base_up[hz], 3), d_up=round(d_up, 3), p_sign=round(p_sign, 4),
                             mean_bp=round(g[m].mean(), 1), abs_bp=round(g[m].abs().mean(), 1), base_abs=round(base_abs[hz], 1), p_size=round(p_size, 4),
                             d_up_h1=round(d1, 3) if d1 == d1 else np.nan, d_up_h2=round(d2, 3) if d2 == d2 else np.nan, expiry_p_up=round((g[g.d0 == 1][m] > 0).mean(), 3) if (g.d0 == 1).sum() >= 10 else np.nan,
                             nonexp_p_up=round((g[g.d0 == 0][m] > 0).mean(), 3) if (g.d0 == 0).sum() >= 10 else np.nan))
    T = pd.DataFrame(rows); ok = T.p_sign.notna(); T.loc[ok, "q_sign"] = _bh(T.loc[ok, "p_sign"]); T.loc[ok, "q_size"] = _bh(T.loc[ok, "p_size"])
    def verdict(r):
        if not np.isfinite(r.p_sign): return "TOO FEW"
        sign = r.q_sign < 0.10 and np.isfinite(r.d_up_h1) and np.isfinite(r.d_up_h2) and np.sign(r.d_up_h1) == np.sign(r.d_up_h2) == np.sign(r.d_up) and abs(r.d_up_h1) > 0
        size = r.q_size < 0.10
        return "PREDICTS SIGN" + (" + SIZE" if size else "") if sign else "PREDICTS SIZE" if size else "NULL"
    for c in ("p_sign", "q_sign", "q_size", "d_up_h1", "d_up_h2", "d_up"):
        if c not in T: T[c] = np.nan
    T["verdict"] = [verdict(r) for r in T.itertuples()]
    pd.set_option("display.width", 300); pd.set_option("display.max_rows", 200); print(T.to_string(index=False)); T.to_csv(f"{PB}/e36_atlas.csv", index=False)
    study_e36econ(R)
    return T


def study_e36econ(R=None):
    R = e36_table() if R is None else R; rg = np.random.default_rng(36); pats = list(PAT_DIR)
    # economics (secondary): aligned long / strangle / straddle at the next open for every occurrence of patterns with n >= 30
    need = sorted({(r.sym, r.day, int(r.i), PAT_DIR[pt]) for pt in pats for r in R[R[pt]].itertuples()} if True else [])
    jobs = sorted({((sm, dy), i, d) for sm, dy, i, d in need}); t0 = time.time()
    with get_context("fork").Pool(max(1, os.cpu_count() - 1)) as pool: pr = {(k, i, d): o for k, i, d, o in pool.imap_unordered(_e36_price, jobs, chunksize=50)}
    print(f"priced {len(pr)} pattern occurrences {time.time() - t0:.0f}s"); eco = []
    for pt in pats:
        g = R[R[pt]]
        if len(g) < 30: continue
        d = PAT_DIR[pt]; vals = {a: np.array([pr[((r.sym, r.day), int(r.i), d)].get(a, np.nan) for r in g.itertuples()]) for a in ("long", "strangle", "straddle")}
        row = dict(pattern=pt, n=len(g))
        for a, v in vals.items():
            v = v[np.isfinite(v)]
            if not len(v): continue
            gd = pd.DataFrame(dict(day=g.day.values[:len(v)] if len(v) == len(g) else g.day.values[np.isfinite(vals[a])], pnl=v)); dd = {dy: x.pnl.values for dy, x in gd.groupby("day")}; ds = list(dd)
            bm = np.array([np.concatenate([dd[x] for x in rg.choice(ds, len(ds))]).mean() for _ in range(500)])
            row[f"{a}_EV"] = round(v.mean()); row[f"{a}_win"] = round((v > 0).mean() * 100, 1); row[f"{a}_ci90"] = f"[{np.percentile(bm, 5):,.0f}, {np.percentile(bm, 95):,.0f}]"
        eco.append(row)
    E = pd.DataFrame(eco); print("\nECONOMICS (counterfactual, every occurrence, 10 lots, E33 exits; in-sample, no selection claim):"); print(E.to_string(index=False)); E.to_csv(f"{PB}/e36_econ.csv", index=False)
    return E


# ================================================================ E37: defined-risk selling inside the window (frozen)
E37_STR = {"IFLY1": S.ifly(1), "ICON12": S.icon(1, 2)}; E37_ENT = {"0946": 31, "1130": 135}; E37_EX = {"spot1": dict(sstop=1, stop=0.5, tgt=0.5), "spot1.5": dict(sstop=1.5, stop=0.5, tgt=0.5)}


def study_e37():
    V = L.vol_days().set_index(["sym", "day"]); gates = {"ALL": lambda k: True, "calm": lambda k: V.or_iv.get(k, np.nan) <= 1.0042, "ivr_high": lambda k: V.ivpct.get(k, np.nan) > 0.67}
    rg = np.random.default_rng(37); rows = []; pd.set_option("display.width", 300)
    pools = {}
    for sn, legs in E37_STR.items():
        for xn, ex in E37_EX.items():
            pool = {}
            for k in KEYS:
                v = [r["pnl"] for i in rg.integers(31, 286, 12) for r in [S.struct(k, int(i), legs, mode="cons", **ex)] if r]; pool[k] = np.array(v if v else [0.0])
            pools[(sn, xn)] = pool
    for sn, legs in E37_STR.items():
        for en, i in E37_ENT.items():
            T = pd.DataFrame([dict(r, key=k) for k in KEYS for r in [S.struct(k, i, legs, mode="cons", **{})] if False])  # placeholder to keep structure simple
            for xn, ex in E37_EX.items():
                D = pd.DataFrame([dict(S.struct(k, i, legs, mode="cons", **ex), key=k) for k in KEYS if S.struct(k, i, legs, mode="cons", **ex)])
                for gn, gf in gates.items():
                    d = D[[gf(k) for k in D.key]]
                    if len(d) < 20: rows.append(dict(struct=sn, entry=en, exit=xn, gate=gn, n=len(d), verdict="TOO FEW")); continue
                    g = d.groupby("day").pnl.sum(); bs = rg.choice(g.values, (4000, len(g))).mean(1); p = float((bs <= 0).mean())
                    h1, h2 = d[d.day < HALF].pnl.sum(), d[d.day >= HALF].pnl.sum(); pl = pools[(sn, xn)]
                    rnd = np.array([sum(rg.choice(pl[k]) for k in d.key) for _ in range(2000)]); pvr = float((rnd >= d.pnl.sum()).mean()); forced = d.forced.mean() * 100
                    ok = p < 0.05 / 24 and h1 > 0 and h2 > 0 and pvr < 0.05 and forced <= 5
                    rows.append(dict(struct=sn, entry=en, exit=xn, gate=gn, n=len(d), win=round((d.pnl > 0).mean() * 100, 1), total=round(d.pnl.sum()), avg=round(d.pnl.mean()), credit=round(d.credit.mean(), 1),
                                     maxloss=round(d.maxloss.mean()), p_boot=round(p, 4), half1=round(h1), half2=round(h2), p_vs_rand=round(pvr, 3), rand_avg=round(rnd.mean() / len(d)), forced=round(forced, 1),
                                     why=d.why.value_counts().to_dict(), verdict="PASS" if ok else "PARKED"))
                    print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv(f"{PB}/e37.csv", index=False); print(R.drop(columns=["why"]).to_string(index=False)); return R


# ================================================================ E39: frozen candidates, LEARN (before HO) vs TEST (from HO), scored once
def _dayboot_p(x, n=4000, seed=39):
    """one-sided p that the mean of daily P&L x is <= 0 (day bootstrap)."""
    x = np.asarray(x, float); return float((np.random.default_rng(seed).choice(x, (n, len(x))).mean(1) <= 0).mean()) if len(x) > 1 else np.nan


def _cell_stats(name, T, learn_days, test_days, base=None, rg=None):
    """T: DataFrame with day, sym, pnl (one row per trade). base: DataFrame of the unconditional same-structure trades on the same days
    (day, pnl) for the same-count random-day placebo on TEST. Returns the frozen E39 row."""
    Lr, Te = T[T.day.isin(learn_days)], T[T.day.isin(test_days)]; r = dict(cell=name, learn_n=len(Lr), test_n=len(Te))
    if len(Lr): g = Lr.groupby("day").pnl.sum(); r.update(learn_total=round(g.sum()), learn_mean=round(Lr.pnl.mean()), learn_win=round((Lr.pnl > 0).mean() * 100, 1), learn_p=round(_dayboot_p(g.values), 4))
    if len(Te):
        g = Te.groupby("day").pnl.sum(); q = pd.to_datetime(Te.day).dt.to_period("Q").astype(str); qs = Te.groupby(q).pnl.sum()
        r.update(test_total=round(g.sum()), test_mean=round(Te.pnl.mean()), test_win=round((Te.pnl > 0).mean() * 100, 1), test_p=round(_dayboot_p(g.values), 4), test_q_pos=f"{(qs > 0).sum()}/{len(qs)}")
        if base is not None and len(base):
            b = base[base.day.isin(test_days)]; rg = rg or np.random.default_rng(3); days = b.day.unique()
            if len(days) >= len(g):
                rnd = np.array([b[b.day.isin(rg.choice(days, len(g), replace=False))].pnl.sum() for _ in range(1000)]); r["p_vs_rand"] = round(float((rnd >= g.sum()).mean()), 3)
    ok = r.get("learn_mean", -1) > 0 and r.get("learn_p", 1) < 0.05 and r.get("test_total", -1) > 0 and r.get("test_p", 1) < 0.005 and r.get("p_vs_rand", 1) < 0.05 and int(r.get("test_q_pos", "0/4").split("/")[0]) >= 3
    r["verdict"] = "PASS" if ok else "FAIL"; return r


def study_e39():
    """registry E39: 10 frozen cells on the 5-year panel (OUT=lab5y_full, HO=2025-10-27, LAB_FULL=1). Smoke-testable on the 1y panel."""
    import book_lab as B
    HO = L.HO; days = sorted({k[1] for k in KEYS}); learn = [d for d in days if d < HO]; test = [d for d in days if d >= HO]
    print(f"E39 panel {days[0]}..{days[-1]}: LEARN {len(learn)} days (< {HO}), TEST {len(test)} days"); rows = []; rg = np.random.default_rng(39)
    V = L.vol_days().set_index(["sym", "day"]); D = B.prep()
    # S1 / S2 / SGATE (short straddle 09:47, 2-step spot exit); S2 threshold = LEARN q0.7 of or_iv (frozen on LEARN only)
    s1 = pd.DataFrame([dict(r, key=k) for k in KEYS for r in [S.struct(k, 31, S.SSTRAD, sstop=2, mode="cons")] if r]); s1["orv"] = [V.or_iv.get(k, np.nan) for k in s1.key]
    thr = float(np.nanquantile([V.or_iv.get(k, np.nan) for k in KEYS if k[1] < HO], 0.7)); s1["rr1"] = [D.rr1.get(k, np.nan) if k in D.index else np.nan for k in s1.key]
    rows.append(_cell_stats("S1 short straddle 09:47 spot2", s1, learn, test))
    s2 = s1[s1.orv <= thr]; rows.append(_cell_stats(f"S2 = S1 if or_iv <= LEARN q0.7 ({thr:.4f})", s2, learn, test, base=s1, rg=rg))
    sg = s2[(s2.rr1 < 0.7) & (s2.sym == "NIFTY")]; rows.append(_cell_stats("SGATE = S2 & prior range < 0.7x, NIFTY", sg, learn, test, base=s1[s1.sym == "NIFTY"], rg=rg))
    # B1 Crabel NR4 (book_lab rule, long ATM, own caps)
    b1 = []
    for k in KEYS:
        if k not in D.index: continue
        for i, sd, ex in B.sig_b1(k, D.loc[k]):
            r = S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **ex)
            if r: b1.append(dict(r, key=k)); break
    b1 = pd.DataFrame(b1); rows.append(_cell_stats("B1 Crabel NR4 stretch breakout", b1, learn, test))
    # E33-derived cells on this panel: LEVEL|BEAR -> S_CE (first qualifying slot per sym-day); regime-only policy learned on LEARN
    T33 = table33(); F33 = states(regime_feats())[["sym", "day", "i", "cell", "regime"]]; T33 = T33.merge(F33, on=["sym", "day", "i"]); T33["mo"] = T33.day.map(L.month)
    lb = T33[(T33.cell == "LEVEL|BEAR") & (T33.action == "S_CE")].sort_values("i").groupby(["sym", "day"]).head(1)
    sce = T33[T33.action == "S_CE"].sort_values("i").groupby(["sym", "day"]).head(1)
    rows.append(_cell_stats("E33 LEVEL|BEAR -> sell ATM CE (first slot)", lb, learn, test, base=sce, rg=rg))
    Tr = T33.copy(); Tr["cell"] = Tr.regime; A = arrays33(Tr[Tr.day >= HO]); Lr = Tr[Tr.day < HO]; NONE = len(ACTS33N) - 1
    g = Lr.groupby(["cell", "action"]).pnl.agg(["mean", "size"]); g = g[g["size"] >= MIN_LEARN]; ev = {idx: r["size"] * r["mean"] / (r["size"] + 15) for idx, r in g.iterrows()}
    tbl = {c: (ACTS33N.index(max([(v, a) for (cc, a), v in ev.items() if cc == c and v > 500])[1]) if any(cc == c and v > 500 for (cc, a), v in ev.items()) else NONE) for c in REGIMES}
    pol = run33(A, lambda mo: tbl, sorted({L.month(d) for d in test})); pol_learn = run33(arrays33(Lr), lambda mo: tbl, sorted({L.month(d) for d in learn}))
    rows.append(_cell_stats(f"E33 regime-only policy (table {{{', '.join(f'{c}:{ACTS33N[a]}' for c, a in tbl.items())}}})", pd.concat([pol_learn, pol]), learn, test))
    # E36 iv_dn -> short OTM1 strangle (first occurrence per sym-day, E33 exits)
    R36 = e36_table(); occ = R36[R36.iv_dn].sort_values("i").groupby(["sym", "day"]).head(1); ivd = []
    for r in occ.itertuples():
        x = act33((r.sym, r.day), int(r.i), "S_STRANGLE1")
        if x: ivd.append(dict(sym=r.sym, day=r.day, pnl=x["pnl"]))
    strg = T33[T33.action == "S_STRANGLE1"].sort_values("i").groupby(["sym", "day"]).head(1)
    rows.append(_cell_stats("E36 IV drop 1pt -> short OTM1 strangle (first)", pd.DataFrame(ivd), learn, test, base=strg, rg=rg))
    # sweep cells: IVS (strangle after IV fall, expiry day, calm open) and GAP-go 0.2% at 09:45 ATM t1_s1 on GAP=FLAT days
    import sweep_lab as W
    G = W.gate_matrix(); gi = {g_[0]: n for n, g_ in enumerate(W.GATES)}
    def sweep_cell(cell, gate_cols):
        r = W.price_cell(cell); m = np.ones(len(r), bool)
        for gc in gate_cols: m &= G[r["k"], gi[gc]]
        return pd.DataFrame(dict(sym=[W.KEYS[x][0] for x in r["k"][m]], day=[W.KEYS[x][1] for x in r["k"][m]], pnl=r["pnl"][m]))
    ivs = sweep_cell(("ND_STRANGLE1", "ivfall1.0", "STRANGLE1", "spot1.5_stop0.3"), ["DTE=0", "OPEN=calm"]); ivs_base = sweep_cell(("ND_STRANGLE1", "t0946", "STRANGLE1", "spot1.5_stop0.3"), [])
    rows.append(_cell_stats("IVS: OTM1 strangle after 1-pt IV fall, expiry day, calm open", ivs, learn, test, base=ivs_base, rg=rg))
    gap = sweep_cell(("GAP", "gap0.2_go_at30", "ATM", "t1_s1"), ["GAP=FLAT"]); gap_base = sweep_cell(("GAP", "gap0.2_go_at30", "ATM", "t1_s1"), [])
    rows.append(_cell_stats("GAP-go 0.2% at 09:45, ATM, t1_s1, GAP=FLAT", gap, learn, test, base=gap_base, rg=rg))
    # placebo cell: random short straddle days (same count as S2) - must FAIL
    rows.append(_cell_stats("PLACEBO random S1 days (S2 count)", s1[s1.day.isin(rg.choice(s1.day.unique(), min(len(s2.day.unique()), s1.day.nunique()), replace=False))], learn, test))
    R = pd.DataFrame(rows); pd.set_option("display.width", 300); print(R.to_string(index=False)); R.to_csv(f"{PB}/e39.csv", index=False)
    print("Bonferroni 10: PASS needs learn_p < 0.05, test_p < 0.005, p_vs_rand < 0.05, >= 3/4 TEST quarters positive"); return R


# ================================================================ E40 / E41 decision inputs (frozen rules in the registry; no pricing here)
def e41_pick(k, i=5):
    """E41 inputs at the 09:20 close (minute 5): ATM strike K and, per side, the OTM strike within ATM+-10 whose close is nearest one third of
    the same-side ATM close. None = skip the day (ATM or every candidate missing)."""
    p = P[k]; K = p["atm"][i]; st = STEP[k[0]]; out = dict(K=float(K))
    for sd, sg in (("CE", 1), ("PE", -1)):
        a0 = L._get(k, sd, K, i, 3); best = None
        if not (np.isfinite(a0) and a0 > 0): return None
        for n in range(1, 11):
            x = L._get(k, sd, K + sg * n * st, i, 3)
            if np.isfinite(x) and (best is None or abs(x - a0 / 3) < best[0]): best = (abs(x - a0 / 3), float(K + sg * n * st))
        if best is None: return None
        out[sd] = best[1]
    return out


def e40_events(sym):
    """E40 event list: for each scheduled MPC day T on the panel, (T-2 key, T-1 key) of the same sym; skipped when T-2 or T-1 is the
    near-expiry day or the near expiry is before T (the panel holds the near weekly only). Calendar facts only (RBI list, expiry dates)."""
    days = sorted(k[1] for k in KEYS if k[0] == sym); out = []
    for T in sorted(L.RBI):
        if T not in days: continue
        j = days.index(T)
        if j < 2: continue
        k2, k1 = (sym, days[j - 2]), (sym, days[j - 1])
        if P[k2]["d0"] or P[k1]["d0"] or P[k2]["exp"] < T: out.append((T, None, None)); continue
        out.append((T, k2, k1))
    return out


def e40_wing(k, i=359):
    """E40 inputs at the T-2 15:14 close (filled at the 15:15 open): ATM K, straddle EM = ATM CE + PE close, wing = min(round(3 EM / step), 10)."""
    K = P[k]["atm"][i]; em = L._get(k, "CE", K, i, 3) + L._get(k, "PE", K, i, 3)
    return dict(K=float(K), em=float(em), wing=int(min(round(3 * em / STEP[k[0]]), 10)) if np.isfinite(em) else -1)


# ================================================================ E39-E41 look-ahead scan (registry rule: before any verdict)
def _scr(keys_cut, rg):
    """in place: for each (key, cut) scramble every minute > cut of spot, ATM index and every contract series; returns the undo list."""
    undo = []
    for k, c in keys_cut:
        c0 = c + 1
        if c0 >= NB: continue
        p = P[k]; m = NB - c0; undo.append((k, p["spot"].copy(), p["atm"].copy(), {q: a.copy() for q, a in p["C"].items()}))
        p["spot"][c0:] *= rg.uniform(0.9, 1.1, m); p["atm"][c0:] += STEP[k[0]] * rg.integers(-2, 3, m)
        for a in p["C"].values(): a[c0:] *= rg.uniform(0.5, 1.5, (m, a.shape[1]))
    return undo


def _undo(undo):
    for k, sp, at, C in undo:
        P[k]["spot"][:], P[k]["atm"][:] = sp, at
        for q, a in C.items(): P[k]["C"][q][:] = a


def _clear():
    _SP.clear(); S._EXT.clear(); _DT.clear(); Z._LAB.clear()
    import sweep_lab as W; W._CTX.clear()


def _same(a, b):
    try:
        if isinstance(a, (float, np.floating)) and isinstance(b, (float, np.floating)) and np.isnan(a) and np.isnan(b): return True
        return bool(a == b) or abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError): return a == b


def _diff(r0, r1, skip=()):
    if r0 is None or r1 is None: return [] if r0 is r1 else ["<row>"]
    return [f for f in r0 if f not in skip and not _same(r0[f], r1.get(f))]


def _day_feats(sym, day, tmp):
    """every day-level E39-E41 input of (sym, day), rebuilt from scratch (all caches off, vol_days / idx_daily caches in `tmp`)."""
    import sweep_lab as W, book_lab as B
    _clear(); L.OUT = tmp; Z.E21 = tmp
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    k = (sym, day); V = L.vol_days().set_index(["sym", "day"]); D = B.prep(); A = Z.labs()[0]; dt = daytab()[k]; C = W.ctx()[k]
    d = D.loc[k]; a = A.loc[k]
    f0 = dict(nr4=bool(d.nr4), stretch=d.stretch, rr1=d.rr1, c1=d.c1, R1=d.R1, dt_c1=dt["c1"], dt_o1=dt["o1"], dt_er1=dt["er1"], dt_med20=dt["med20"],
              PDH=a.PDH, PDL=a.PDL, TREND=a.TREND, GAP=a.GAP, DTE=a.DTE, PRNG=a.PRNG, hist=str(C["hist"]))
    f30 = dict(or_iv=V.or_iv.get(k, np.nan), ivpct=V.ivpct.get(k, np.nan), ORW=a.ORW, OPEN=W.gate_matrix()[W.KEYS.index(k), [g[0] for g in W.GATES].index("OPEN=calm")],
               gap_go=str(W.gap(k, 0.2, False, 30)))
    ds = sorted(d_ for s_, d_ in P if s_ == sym); nk = (sym, ds[ds.index(day) + 1]) if ds.index(day) + 1 < len(ds) else None
    plant = dict(B_c_today=D.loc[k].c, Z_nextPDH=A.loc[nk].PDH if nk else np.nan, W_close=float(C["f"][-1]), V_close=V.close.get(k, np.nan))
    return f0, f30, dict(har=V.har.get(k, np.nan), rvd=V.rvd.get(k, np.nan)), plant  # [2]: whole-day/sample columns no cell uses; [3]: planted leaks  # last dict: known whole-day / whole-sample columns, NOT used by any cell


def study_scan39():
    """registry E39-E41 rule: scramble everything after each decision point and assert no E39-E41 input changed.
    (1) day level: for sampled days, scramble the day after 09:15 (cut 0) or after 09:45 (cut 30) AND the next 25 panel days of both syms,
        rebuild every day-level table from scratch, compare. (2) intraday: per sampled key, scramble the day after the decision minute only and
        re-run the real feature function (E33 rows + regime/cell at every slot, E36 flags at every bar, B1 and IVS first signals, E41 picker,
        E40 wing). (3) calendar: the 5-year loader infers expiry days from the 15:29 extrinsic (after the fact): check them against the
        exchange weekday rules with holiday roll-back. Known answer first: a planted leak must be caught."""
    import tempfile, sweep_lab as W, book_lab as B
    rg = np.random.default_rng(39); tmp = tempfile.mkdtemp(prefix="scan39_"); out0 = L.OUT; e21 = Z.E21; bad = []
    ix0 = Z.IDX; IX = pd.read_pickle(ix0); ixs = os.path.join(tempfile.mkdtemp(prefix="scan39ix_"), "idx1m.pkl")
    def _ix(path): Z.IDX = L.IDX5Y = B.IDX5Y = path   # the 5y index minutes (scen_lab / vol_days / book_lab history days)
    try:
        days = sorted({k[1] for k in KEYS}); sd = [days[j] for j in rg.choice(range(30, len(days) - 30), int(os.environ.get("SCAN_DAYS", 10)), replace=False)]
        nanday = [k[1] for k in KEYS if not np.isfinite(P[k]["spot"][:31]).all()][:1]; expday = [k[1] for k in KEYS if P[k]["d0"]][len(days) // 10:][:1]
        print("day-level sample", sorted(sd + nanday + expday), flush=True); t0 = time.time()
        for day in sorted(sd + nanday + expday):
            j = days.index(day); later = days[j + 1:j + 26]
            for sym in ("NIFTY", "SENSEX"):
                if (sym, day) not in P: continue
                r0 = _day_feats(sym, day, tmp)
                for cut, which in ((0, 0), (30, 1)):
                    X2 = IX.copy(); m = X2.day.isin(later) | ((X2.day == day) & (X2.m > M0 + cut)); pc = ["open", "high", "low", "close"]
                    X2.loc[m, pc] = X2.loc[m, pc].values * rg.uniform(0.9, 1.1, (int(m.sum()), 1)); X2.to_pickle(ixs); _ix(ixs)
                    U = _scr([((s, day), cut) for s in ("NIFTY", "SENSEX") if (s, day) in P] + [((s, d), -1) for d in later for s in ("NIFTY", "SENSEX") if (s, d) in P], rg)
                    try: r1 = _day_feats(sym, day, tmp)
                    finally: _undo(U); _ix(ix0)
                    lk = _diff(r0[0], r1[0]) + (_diff(r0[1], r1[1]) if which else []); info = _diff(r0[2], r1[2]); pl = _diff(r0[3], r1[3])
                    if len(pl) < 4: bad.append((sym, day, cut, "positive control not caught", sorted(set(r0[3]) - set(pl))))
                    print(f"  {sym} {day} cut {cut}: {'LEAK ' + str(lk) if lk else 'clean'}; unused whole-day/sample columns changed: {info}; planted leaks caught {len(pl)}/4 ({time.time() - t0:.0f}s)", flush=True)
                    if lk: bad.append((sym, day, cut, lk))
        _clear(); L.OUT = out0; Z.E21 = e21
        # (2) intraday, real functions, day context from the unscrambled panel
        A = Z.labs()[0]; D = daytab(); IVP = L.vol_days().set_index(["sym", "day"]).ivpct.to_dict(); DB = B.prep()
        ks = [KEYS[j] for j in rg.choice(len(KEYS), int(os.environ.get("SCAN_KEYS", 120)), replace=False)] + [k for k in KEYS if not np.isfinite(P[k]["spot"][:31]).all()][:3] + [k for k in KEYS if P[k]["d0"]][::60][:6]
        def one(k, i, fn, skip=()):
            r0 = fn(); U = _scr([(k, i)], rg); _SP.pop(k, None); S._EXT.clear()
            try: r1 = fn()
            finally: _undo(U); _SP.pop(k, None); S._EXT.clear()
            lk = _diff(r0, r1, skip)
            if lk: bad.append((k, i, fn.__name__ if hasattr(fn, "__name__") else "?", lk))
            return lk
        n = 0; n41 = 0
        # known answer: a planted next-minute read must be caught by the same harness
        nb = len(bad); assert one(ks[0], 100, lambda: dict(x=float(spot(ks[0])[101]))) == ["x"]; del bad[nb:]  # drop only the planted one
        assert one(ks[0], 100, lambda: dict(x=float(spot(ks[0])[100]))) == []
        for k in ks:
            for i in SLOTS33:
                def r33(k=k, i=i):
                    r = _row33(k, i, _bars5(k), A.loc[k], D[k], IVP.get(k, np.nan)); F = states(pd.DataFrame([r]))
                    return dict(r, regime=F.regime.iloc[0], cell=F.cell.iloc[0])
                one(k, i, r33); n += 1
            R = e36_rows(k)
            for t, b in enumerate(B36):
                one(k, 5 * b + 4, lambda k=k, t=t: {f: v for f, v in e36_rows(k)[t].items() if not f.startswith("mv")}); n += 1
            if k in DB.index:
                sb = B.sig_b1(k, DB.loc[k])
                if sb: one(k, sb[0][0], lambda k=k: dict(sig=str(B.sig_b1(k, DB.loc[k])))); n += 1
            iv = W.nd_iv(k, -1.0)
            if iv: one(k, iv[0][0], lambda k=k: dict(sig=str(W.nd_iv(k, -1.0)))); n += 1
            one(k, 5, lambda k=k: e41_pick(k)); one(k, 359, lambda k=k: e40_wing(k)); n += 2; n41 += e41_pick(k) is not None
        print(f"intraday: {n} decision points on {len(ks)} sym-days (E41 pick defined on {n41}), leaks {len(bad)}", flush=True)
        # (3) expiry calendar vs exchange weekday rules (holiday -> previous trading day)
        def rule(sym, d):  # weekday of the weekly expiry in force on day d (Mon=0)
            if sym == "NIFTY": return 3 if d < "2025-09-01" else 1
            return 4 if d < "2025-01-01" else 1 if d < "2025-09-01" else 3
        mism = []
        for sym in ("NIFTY", "SENSEX"):
            sd_ = sorted(k[1] for k in KEYS if k[0] == sym); S_ = set(sd_); exps = sorted({P[(sym, d)]["exp"] for d in sd_})
            first = pd.Timestamp(sd_[0]); last = pd.Timestamp(sd_[-1])
            for wk in pd.date_range(first - pd.Timedelta(days=first.weekday()), last, freq="7D"):
                t = wk + pd.Timedelta(days=rule(sym, str(wk.date())))
                while str(t.date()) not in S_ and t > wk: t -= pd.Timedelta(days=1)   # holiday: roll back inside the week
                ts = str(t.date())
                if ts not in S_ or str((wk + pd.Timedelta(days=6)).date()) > sd_[-1]: continue  # last, partial week: not checkable
                got = [e for e in exps if str(wk.date()) <= e < str((wk + pd.Timedelta(days=7)).date())]
                if got != [ts]: mism.append((sym, str(wk.date()), ts, got))
            print(f"calendar {sym}: {len(exps)} inferred expiries, mismatches vs weekday rule {len([m for m in mism if m[0] == sym])}", flush=True)
        for m in mism[:40]: print("   ", m)
        bad += [("calendar",) + tuple(m) for m in mism]
        pd.DataFrame(mism, columns=["sym", "week", "rule_day", "inferred"]).to_csv(f"{PB}/scan39_calendar.csv", index=False)
    finally:
        _clear(); L.OUT = out0; Z.E21 = e21; _ix(ix0)
    for b in bad: print("LEAK", b)
    print(f"scan39: {'NO look-ahead in any E39-E41 input' if not bad else str(len(bad)) + ' LEAKS'}"); return bad


# ================================================================ E42: scenario-bucket atlas (frozen: registry row E42, side-session note
# E42_atlas_freeze.md, committed before any cell was priced). 8 scenario variables x 8 strategies, LEARN < HO, TEST >= HO scored once.
E42_BUDGET = {"2022-02-01", "2023-02-01", "2024-02-01", "2024-07-23", "2025-02-01", "2026-02-01"}  # Union Budget days (absent days do not count)
E42_STRATS = ["SS", "SG", "IVS", "LS", "LD", "ORB", "GAPGO", "GAPFADE"]
E42_FH_OK = {"LD", "IVS", "ORB"}                     # FH (10:15 close) is known only for decisions at i >= 60
E42_SCEN = ["EXPIRY", "GAP", "TREND", "EVENT", "ORW", "IVR", "OPEN", "FH"]
E42_MIN_N, E42_MIN_DAYS = 30, 20
STR1 = [("CE", 1, -1), ("PE", -1, -1)]


def _e42_key(k, D):
    """one sym-day: every E42 strategy at its frozen entry (one trade per strategy) + the FH inputs at the 10:15 close (i=60)."""
    import sweep_lab as W
    out = []
    def add(nm, i, r):
        if r: out.append((nm, int(i), float(r["pnl"]), bool(r["forced"]), r["why"]))
    add("SS", 31, S.struct(k, 31, S.SSTRAD, sstop=2, mode="cons"))
    add("SG", 31, S.struct(k, 31, STR1, sstop=1.5, stop=0.3, mode="cons"))
    for i, _, _ in W.nd_iv(k, -1.0)[:1]: add("IVS", i, S.struct(k, i, STR1, sstop=1.5, stop=0.3, mode="cons"))
    add("LS", 30, S.struct(k, 30, S.LSTRAD, sstop=2.5, mode="cons"))
    s = P[k]["spot"]
    if np.isfinite(s[0]) and np.isfinite(s[60]) and s[60] != s[0]: add("LD", 60, long_leg(k, 60, "CE" if s[60] > s[0] else "PE"))
    for i, sd in S.orb_signals(k, False)[:1]: add("ORB", i, S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **S.E5X["t1.5_s1"]))
    d = D.loc[k] if k in D.index else None
    if d is not None and np.isfinite(d.c1):
        f = pd.Series(s).ffill().bfill().values; gp = f[0] / d.c1 - 1   # sweep_lab.gap(k, 0.2, fade, 30), inlined (no ctx build)
        if abs(gp) >= 0.002:
            for nm, sd in (("GAPGO", "CE" if gp > 0 else "PE"), ("GAPFADE", "PE" if gp > 0 else "CE")):
                add(nm, 30, S.struct(k, 30, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **S.E5X["t1_s1"]))
    try: r = _row33(k, 60, _bars5(k), Z.labs()[0].loc[k], daytab()[k], np.nan); fh = (r["adx"], r["er"], r["chop"], r["r60"])
    except Exception: fh = (np.nan,) * 4
    return k, out, fh


def e42_fh(adx, er, chop, r60):
    """FH label from the E33 2-of-3 vote at the 10:15 close; direction = sign of the 60-min return; CHOP otherwise (NA if the inputs are missing)."""
    if not all(np.isfinite(x) for x in (adx, er, chop, r60)): return None
    tr = int(adx >= 25) + int(er >= 0.35) + int(chop <= 45) >= 2
    return ("TREND_UP" if r60 > 0 else "TREND_DN" if r60 < 0 else "CHOP") if tr else "CHOP"


def e42_trades():
    """per-trade frame with the scenario labels (cached by source hash; the labels use nothing after the decision minute)."""
    fp = f"{PB}/e42_trades_{SRC}_{L.COSTS}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    import book_lab as B
    t0 = time.time(); D = B.prep(); A = Z.labs()[0]; V = L.vol_days().set_index(["sym", "day"]); days = sorted({k[1] for k in KEYS})
    Z.labs(); daytab(); _E42["D"] = D  # build the shared day tables in the parent before forking (workers read them copy-on-write)
    rows = []; FH = {}
    with get_context("fork").Pool(max(1, os.cpu_count() - 1)) as pool:
        for k, out, fh in pool.imap_unordered(_e42_worker, KEYS, chunksize=8):
            FH[k] = e42_fh(*fh); rows += [dict(sym=k[0], day=k[1], strat=nm, i=i, pnl=p_, forced=f, why=w) for nm, i, p_, f, w in out]
    T = pd.DataFrame(rows); thr = float(np.nanquantile([V.or_iv.get(k, np.nan) for k in KEYS if k[1] < L.HO], 0.7))
    fomc1 = L.fomc_next(days); ev = {d for d in days if d in L.RBI or d in fomc1 or d in E42_BUDGET}
    key = list(zip(T.sym, T.day))
    T["EXPIRY"] = np.where([P[k]["d0"] for k in key], "0", "1+")
    for c in ("GAP", "TREND", "ORW", "IVR"): T[c] = [A[c].get(k, None) if k in A.index else None for k in key]
    T["EVENT"] = np.where(T.day.isin(ev), "EVENT", "NONE")
    orv = np.array([V.or_iv.get(k, np.nan) for k in key]); T["OPEN"] = np.where(np.isfinite(orv), np.where(orv <= thr, "CALM", "ACTIVE"), None)
    T["FH"] = [FH.get(k) if (st in E42_FH_OK and i >= 60) else None for k, st, i in zip(key, T.strat, T.i)]
    rg = np.random.default_rng(42); coin = {d: ("RND_A" if rg.integers(0, 2) else "RND_B") for d in days}; T["PLACEBO"] = T.day.map(coin)
    T.attrs["open_thr"] = thr; T.to_pickle(fp); print(f"e42 trades {len(T)} rows, OPEN thr (LEARN q0.7 or_iv) {thr:.4f}, {time.time() - t0:.0f}s", flush=True); return T


_E42 = {}
def _e42_worker(k): return _e42_key(k, _E42["D"])


def _e42_pvr(cell, base, days, rg, n=1000):
    """share of n draws of the same number of random trade-days from the strategy's own trades (on `days`) whose total >= the cell's total."""
    c = cell[cell.day.isin(days)]; b = base[base.day.isin(days)]
    if not len(c): return np.nan
    g = c.groupby("day").pnl.sum(); bd = b.day.unique()
    if len(bd) <= len(g): return np.nan
    tot = g.sum(); rnd = np.array([b[b.day.isin(rg.choice(bd, len(g), replace=False))].pnl.sum() for _ in range(n)]); return float((rnd >= tot).mean())


def _e42_cell(name, T, base, learn, test, half, alpha, rg):
    """frozen E42 row for one cell. T: the cell's trades; base: the strategy's unconditional trades (placebo)."""
    Lr, Te = T[T.day.isin(learn)], T[T.day.isin(test)]; r = dict(cell=name, learn_n=len(Lr), learn_days=Lr.day.nunique(), test_n=len(Te))
    r["forced"] = round(T.forced.mean() * 100, 1) if len(T) else np.nan
    if len(Lr):
        g = Lr.groupby("day").pnl.sum(); h1, h2 = Lr[Lr.day < half], Lr[Lr.day >= half]
        r.update(learn_total=round(g.sum()), learn_mean=round(Lr.pnl.mean()), learn_win=round((Lr.pnl > 0).mean() * 100, 1), learn_p=round(_dayboot_p(g.values), 5),
                 h1_mean=round(h1.pnl.mean()) if len(h1) else np.nan, h2_mean=round(h2.pnl.mean()) if len(h2) else np.nan, pvr_learn=_e42_pvr(T, base, learn, rg))
    if len(Te):
        g = Te.groupby("day").pnl.sum(); q = pd.to_datetime(Te.day).dt.to_period("Q").astype(str); qs = Te.groupby(q).pnl.sum()
        r.update(test_total=round(g.sum()), test_mean=round(Te.pnl.mean()), test_win=round((Te.pnl > 0).mean() * 100, 1), test_p=round(_dayboot_p(g.values), 4),
                 test_q_pos=f"{(qs > 0).sum()}/{len(qs)}", pvr_test=_e42_pvr(T, base, test, rg))
    testable = r["learn_n"] >= E42_MIN_N and r["learn_days"] >= E42_MIN_DAYS
    core = (testable and r.get("learn_mean", -1) > 0 and r.get("learn_p", 1) < alpha and r.get("h1_mean", -1) > 0 and r.get("h2_mean", -1) > 0
            and r.get("test_total", -1) > 0 and r.get("test_p", 1) < 0.05 and r.get("pvr_learn", 1) < 0.05 and r.get("pvr_test", 1) < 0.05)
    r["verdict"] = "UNTESTABLE" if not testable else "PASS" if core and r["forced"] <= 5 else "INCONCLUSIVE" if core else "FAIL"; return r


def e42_table(T, learn, test, scen=E42_SCEN, strats=E42_STRATS):
    """the frozen atlas from a per-trade frame: (rows, N_cells, alpha). PLACEBO and ALL rows are reported, never counted."""
    half = learn[len(learn) // 2]; rg = np.random.default_rng(42); rows = []
    cells = [(st, c, b) for st in strats for c in scen for b in sorted(T[c].dropna().unique()) if not (c == "FH" and st not in E42_FH_OK)]
    tl = T[T.day.isin(learn)]; n_cells = sum(len(g := tl[(tl.strat == st) & (tl[c] == b)]) >= E42_MIN_N and g.day.nunique() >= E42_MIN_DAYS for st, c, b in cells)
    alpha = 0.05 / max(n_cells, 1)
    for st in strats:
        base = T[T.strat == st]; rows.append(dict(_e42_cell(f"{st} ALL", base, base, learn, test, half, alpha, rg), strat=st, scen="ALL", bucket="ALL", counted=False))
        for c in scen + ["PLACEBO"]:
            if c == "FH" and st not in E42_FH_OK: continue
            for b in sorted(T[c].dropna().unique()):
                r = _e42_cell(f"{st} {c}={b}", base[base[c] == b], base, learn, test, half, alpha, rg)
                rows.append(dict(r, strat=st, scen=c, bucket=b, counted=c != "PLACEBO"))
    return pd.DataFrame(rows), n_cells, alpha


def study_e42():
    """registry E42: run every cell on LEARN, score TEST once, one table. OUT=lab5y_full, HO=2025-10-27, LAB_FULL=1, COSTS=dated, OFFMAX=10."""
    HO = L.HO; days = sorted({k[1] for k in KEYS}); learn = [d for d in days if d < HO]; test = [d for d in days if d >= HO]
    print(f"E42 panel {days[0]}..{days[-1]}: LEARN {len(learn)} days (< {HO}; halves split at {learn[len(learn) // 2]}), TEST {len(test)} days, COSTS={L.COSTS}", flush=True)
    T = e42_trades(); T.to_csv(f"{PB}/e42_trades.csv", index=False)
    print("trades per strategy:", T.strat.value_counts().to_dict(), "| forced %:", T.groupby("strat").forced.mean().mul(100).round(1).to_dict())
    print("LEARN days per bucket:", {c: T[T.day.isin(learn)].drop_duplicates(["day"] if c != "FH" else ["day", "strat"])[c].value_counts().to_dict() for c in E42_SCEN})
    R, n_cells, alpha = e42_table(T, learn, test); R.to_csv(f"{PB}/e42_cells.csv", index=False)
    pd.set_option("display.width", 400); pd.set_option("display.max_rows", 1000)
    cols = ["cell", "learn_n", "learn_days", "learn_win", "learn_mean", "learn_p", "h1_mean", "h2_mean", "pvr_learn", "test_n", "test_win", "test_mean", "test_p", "test_q_pos", "pvr_test", "forced", "verdict"]
    print(f"\nN_cells (testable) = {n_cells}; LEARN alpha = 0.05 / {n_cells} = {alpha:.6f}; TEST p < 0.05; p_vs_rand < 0.05 on both; forced <= 5%")
    print(R[cols].to_string(index=False))
    C = R[R.counted & (R.verdict != "UNTESTABLE")]
    print(f"\nraw LEARN p < 0.05: {(C.learn_p < 0.05).sum()} of {len(C)} testable cells (null ~{0.05 * len(C):.1f}); LEARN mean > 0: {(C.learn_mean > 0).sum()}")
    print("PASS:", R[R.verdict == "PASS"].cell.tolist() or "none", "| INCONCLUSIVE:", R[R.verdict == "INCONCLUSIVE"].cell.tolist() or "none")
    pl = R[R.scen == "PLACEBO"]; print("PLACEBO control verdicts:", pl.verdict.value_counts().to_dict(), "(must contain no PASS)")
    M = R[R.scen != "PLACEBO"].assign(txt=lambda x: x.learn_mean.map(lambda v: f"{v:+.0f}" if v == v else "-") + " p" + x.learn_p.map(lambda v: f"{v:.3f}" if v == v else "-") + " " + x.verdict.str[0])
    print("\nMATRIX (LEARN per trade, LEARN p, verdict letter P/F/U/I):"); print(M.pivot_table(index=["scen", "bucket"], columns="strat", values="txt", aggfunc="first").reindex(columns=E42_STRATS).to_string())
    return R


def study_selftest42():
    """known answers for the frozen E42 rule on synthetic trades: a planted edge in one cell passes, the same strategy's other cells and the random
    label fail, an FH label before 10:15 is NA, a cell with < 30 LEARN trades is UNTESTABLE, forced > 5% turns a pass into INCONCLUSIVE."""
    rg = np.random.default_rng(1); days = [str(d.date()) for d in pd.bdate_range("2021-11-01", periods=600)]; learn, test = days[:480], days[480:]
    rows = []
    for d in days:
        for sym in ("NIFTY", "SENSEX"):
            gap = rg.choice(["DN", "FLAT", "UP"]); lab = dict(EXPIRY=rg.choice(["0", "1+"]), GAP=gap, TREND=rg.choice(["UP", "DN"]), EVENT="NONE", ORW="NORMAL", IVR="MID", OPEN="CALM")
            for st in E42_STRATS:
                i = 60 if st == "LD" else 31; e = 4000 if (st == "SS" and gap == "UP") else 0
                rows.append(dict(sym=sym, day=d, strat=st, i=i, pnl=rg.normal(e, 6000), forced=False, why="time", FH=("CHOP" if st in E42_FH_OK and i >= 60 else None),
                                 PLACEBO="RND_A" if rg.integers(0, 2) else "RND_B", **lab))
    T = pd.DataFrame(rows); R, n, alpha = e42_table(T, learn, test)
    v = R.set_index("cell").verdict
    assert v["SS GAP=UP"] == "PASS", R[R.cell == "SS GAP=UP"].to_dict("records")
    assert v["SS GAP=DN"] == "FAIL" and v["SG GAP=UP"] == "FAIL" and (R[R.scen == "PLACEBO"].verdict == "PASS").sum() == 0
    assert T[(T.strat == "SS")].FH.isna().all() and T[(T.strat == "LD")].FH.notna().all()
    assert "SS FH=CHOP" not in v.index and alpha == 0.05 / n and n > 0
    T2 = T[~((T.strat == "SG") & (T.GAP == "DN") & (T.day.isin(learn[40:])))]; R2, _, _ = e42_table(T2, learn, test); assert R2.set_index("cell").verdict["SG GAP=DN"] == "UNTESTABLE"
    T3 = T.copy(); T3.loc[(T3.strat == "SS") & (T3.GAP == "UP") & (rg.random(len(T3)) < 0.1), "forced"] = True
    R3, _, _ = e42_table(T3, learn, test); assert R3.set_index("cell").verdict["SS GAP=UP"] == "INCONCLUSIVE"
    assert e42_fh(30, 0.4, 40, 0.01) == "TREND_UP" and e42_fh(30, 0.4, 40, -0.01) == "TREND_DN" and e42_fh(10, 0.1, 60, 0.01) == "CHOP" and e42_fh(np.nan, 0.4, 40, 0.01) is None
    print(f"E42 selftest OK (planted SS x GAP=UP passes at alpha {alpha:.5f} over {n} cells; siblings, random label fail; FH NA before 10:15; UNTESTABLE; INCONCLUSIVE on forced)")


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
