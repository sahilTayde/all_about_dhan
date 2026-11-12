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
    days = sorted({k[1] for k in KEYS}); fomc1 = {next(d for d in days if d > f) for f in L.FOMC if any(d > f for d in days)}
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


def regime_feats():
    """raw E33 features per (sym, day, slot minute i), data up to minute i only."""
    fp = f"{PB}/e33_feats.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); A = Z.labs()[0]; D = daytab(); rows = []; IVP = L.vol_days().set_index(["sym", "day"]).ivpct.to_dict()
    for k in KEYS:
        s = spot(k); st = STEP[k[0]]; G = _bars5(k); a = A.loc[k]; d = D[k]; p = P[k]; orh, orl = s[:16].max(), s[:16].min()  # OR 09:15-09:30
        for i in SLOTS33:
            b = i // 5; K = p["atm"][i]; j = i - 15; LAG = 3  # OI on Dhan is ~3 min delayed live: lag it
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
            rows.append(dict(sym=k[0], day=k[1], i=i, slot=f"{(M0 + i) // 60:02d}{(M0 + i) % 60:02d}", ampm="AM" if i < 165 else "PM",
                             adx=x.adx, pdi=x.pdi, mdi=x.mdi, er=x.er, chop=x.chop, r60=s[i] / s[i - 60] - 1, r15=s[i] / s[i - 15] - 1, near_level=near,
                             gap=gap, rbi=k[1] in L.RBI, fomc=k[1] in L.FOMC, d0=p["d0"], dte=p["dte"], oiflow=oiflow, oflow=oflow, fvg=_fvg(G, b),
                             cshape=shape, bias=1 if a.TREND == "UP" else -1 if a.TREND == "DN" else 0, gex=_gex(k, i), iv=S._iv(k, i), rv30=_rv(s, i),
                             div15=S._iv(k, i) - S._iv(k, j), maxoi=_maxoi(k, i - 3), day_ret=s[i] / s[0] - 1, ivpct=IVP.get(k, np.nan)))
    F = pd.DataFrame(rows); F["mo"] = F.day.map(L.month); F.to_pickle(fp); print(f"e33 feats {len(F)} rows {time.time() - t0:.0f}s"); return F


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
    if a is None or not np.isfinite(a[e, 0]): return None
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
    return dict(pnl=(x - en) * LOT[sym] * L.LOTS - L.cost(en, x, sym), held=j - e, forced=forced, why=why, credit=-en)


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
    fp = f"{PB}/e33_table.pkl"
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


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
