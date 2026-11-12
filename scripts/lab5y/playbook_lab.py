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


# ---------------------------------------------------------------- actions (both sides) and their fixed exits
def pair_legs(short_sym):
    """placeholder: pairs are priced by two single-index structs (vega-matched lots) in outcomes(); see ACTIONS."""
    return short_sym


ACTIONS = {  # name: (legs or 'PAIR', exit kw). Directional actions get dirn from the side; exits are the frozen few.
    "L_CE": ([("CE", 0, 1)], dict(dirn=1, s_tgt=2, s_stp=1)), "L_PE": ([("PE", 0, 1)], dict(dirn=-1, s_tgt=2, s_stp=1)),
    "L_CE_tight": ([("CE", 0, 1)], dict(dirn=1, s_tgt=1, s_stp=0.5)), "L_PE_tight": ([("PE", 0, 1)], dict(dirn=-1, s_tgt=1, s_stp=0.5)),
    "S_STRAD": (S.SSTRAD, dict(sstop=2, stop=0.3)), "S_STRANGLE1": ([("CE", 1, -1), ("PE", -1, -1)], dict(sstop=1.5, stop=0.3)),
    "L_STRAD": (S.LSTRAD, dict(sstop=2)), "CS_UP": ("CS", dict(dirn=1, s_stp=1)), "CS_DN": ("CS", dict(dirn=-1, s_stp=1)),
}
PAIRS = ["PAIR_LN_SS", "PAIR_LS_SN"]  # long NIFTY straddle + short SENSEX straddle (vega-matched whole lots), and the reverse


def _legs(name, k):
    legs, kw = ACTIONS[name]
    if legs == "CS": return S.e5_legs("CE" if kw["dirn"] > 0 else "PE", "cs"), kw
    return legs, kw


def price_candle(k):
    """all actions at every decision bar of one sym-day -> rows (b, action, pnl, held, forced, why)."""
    out = []
    for b in range(B_LO, B_HI + 1):
        i = TF * b + TF - 1
        for name in ACTIONS:
            legs, kw = _legs(name, k); r = S.struct(k, i, legs, mode="cons", **kw)
            if r: out.append((b, name, r["pnl"], r["held"], r["forced"], r["why"], r.get("credit", np.nan)))
    return k, out


def outcomes():
    fp = f"{PB}/outcomes.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); rows = []
    with get_context("fork").Pool(max(1, os.cpu_count() - 1)) as pool:
        for n, (k, out) in enumerate(pool.imap_unordered(price_candle, KEYS, chunksize=2)):
            rows += [dict(sym=k[0], day=k[1], b=b, action=a, pnl=p, held=h, forced=f, why=w) for b, a, p, h, f, w, _ in out]
            if n % 50 == 0: print(f"  {n}/{len(KEYS)} {time.time() - t0:.0f}s", flush=True)
    O = pd.DataFrame(rows)
    # pairs: vega-matched whole lots (sell_lab._size on the ATM straddle vega at the bar), priced from the two single-index straddles
    V = {}
    for k in KEYS:
        for b in range(B_LO, B_HI + 1): V[(k[0], k[1], b)] = S._vega(k, TF * b + TF - 1)
    ss = O[O.action == "S_STRAD"].set_index(["sym", "day", "b"]); ls = O[O.action == "L_STRAD"].set_index(["sym", "day", "b"])
    pr = []
    for (sym, day, b), r in ls.iterrows():
        if sym != "NIFTY" or ("SENSEX", day, b) not in ss.index or ("SENSEX", day, b) not in ls.index or ("NIFTY", day, b) not in ss.index: continue
        vN, vS = V[("NIFTY", day, b)], V[("SENSEX", day, b)]
        if not (np.isfinite(vN) and np.isfinite(vS)): continue
        nN, nS = S._size(vN, vS)  # lots 1..10 each; pnl at 10 lots scales by n/10 (ponytail: brokerage share ignored, < Rs 50)
        a = ls.loc[("NIFTY", day, b)]; c = ss.loc[("SENSEX", day, b)]; d = ss.loc[("NIFTY", day, b)]; e = ls.loc[("SENSEX", day, b)]
        pr.append(dict(sym="PAIR", day=day, b=b, action="PAIR_LN_SS", pnl=a.pnl * nN / 10 + c.pnl * nS / 10, held=max(a.held, c.held), forced=a.forced or c.forced, why=a.why + "/" + c.why))
        pr.append(dict(sym="PAIR", day=day, b=b, action="PAIR_LS_SN", pnl=e.pnl * nS / 10 + d.pnl * nN / 10, held=max(e.held, d.held), forced=e.forced or d.forced, why=e.why + "/" + d.why))
    O = pd.concat([O, pd.DataFrame(pr)], ignore_index=True); O.to_pickle(fp); print(f"outcomes {len(O)} rows {time.time() - t0:.0f}s"); return O


def study_candles(): C = candles(); print(C.shape); print(C.head(3).to_string())
def study_features(): F = features(); print(F.shape); print(F[["body", "uw", "lw", "run", "vs_or", "vs_pd", "vs_twap", "rv_iv", "div3", "er", "diverg", "oiflow3"]].describe().round(3).to_string())
def study_outcomes():
    O = outcomes(); print(O.groupby("action").pnl.agg(["size", "mean", lambda x: (x > 0).mean()]).round(2).to_string())


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
