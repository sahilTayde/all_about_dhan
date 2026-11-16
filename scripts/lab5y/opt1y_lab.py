"""Round-2 options lab on 1y of Dhan rolling expired-option 1m bars (NIFTY + SENSEX nearest weekly, ATM-3..ATM+3).
Needs: opt1y_load.py -> OUT/opt1y.parquet, opt1y_spread.py -> OUT/spreads.csv (both in OUT).
Run:  ~/paper_extra_venv/bin/python scripts/lab5y/opt1y_lab.py OUT [family ...]   (families: see FAM at bottom)

Contract series: rebuilt per (sym, day, side, strike) from all 7 offsets, so a held contract keeps its own price
after the ATM rolls. If the held contract leaves the +-3 window, the trade is force-exited at its last known close
(counted in 'lost%'; the brief's 'drop' option would bias against big winners).
Fills: decide at close of bar i; buy at open of bar i+1 + half-spread; time exits sell at open of the exit bar
- half-spread; stop fills at min(stop, bar open); target fills at the target; stop+target in one bar = stop.
Half-spread = 75th pct from the 13-day tape (spreads.csv) by sym x premium bucket x time bucket x expiry-day.
Costs = config/charges.yaml x1.5, 10 lots (NIFTY 65, SENSEX 20 per lot). Flatten at the 15:15 open (FLAT = minute 915; audit A2: before 2026-10-28 it was 900 = 15:00). Entries 09:20..14:59.
Dev = days < 2026-07-27 (walk-forward by month); HOLDOUT = 2026-07-27..2026-10-23, run only with --holdout."""
import sys, os, pickle, hashlib, numpy as np, pandas as pd

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
HOLDOUT = "--holdout" in sys.argv
LOT = {"NIFTY": 65, "SENSEX": 20}; LOTS = 10; CM = 1.5
TXN = {"NIFTY": 0.000355299, "SENSEX": 0.000325}
STEP = {"NIFTY": 50, "SENSEX": 100}
HO = os.environ.get("HO", "2026-07-27")  # E39: HO=2025-10-27 on the 5-year panel makes dev = 2021-2025 (LEARN) and --holdout = our year (TEST)
M0, NB = 555, 375            # 09:15, bars per day
E_LO, E_HI, FLAT = 560, 899, 915  # decision minutes 09:20..14:59; flatten at 15:15 open (audit A2: was 900 = 15:00)
RNG = np.random.default_rng(11)
NVAR = [0]                   # count of every variant evaluated (for Bonferroni)


# ---------------------------------------------------------------- 5-year cost hygiene (2026-11-13, REPO_HARVEST #2)
# COSTS=today (default; every frozen row up to E39): every day at today's rates and lots, i.e. "what this rule would pay now".
# COSTS=dated: the STT / exchange rates in force on the TRADE day and whole lots at the size in force for the contract's EXPIRY, with
# the quantity kept nearest today's 10 lots (650 NIFTY / 200 SENSEX units) so exposure is comparable across 2021-2026.
# Tables = (effective-from date, value); sources in teams/01_research/docs/REPO_HARVEST.md §5. Unchanged over 2021-10..2026-10 and
# kept as constants: brokerage Rs 20/order (Dhan), stamp 0.003% of buy premium (since 2020-07-01), SEBI Rs 10/crore, GST 18%.
COSTS = os.environ.get("COSTS", "today")
STT_SELL = [("2016-06-01", 0.0005), ("2023-04-01", 0.000625), ("2024-10-01", 0.001), ("2026-04-01", 0.0015)]  # sale of option, on premium
TXN_D = {"NIFTY": [("2021-01-01", 0.00053), ("2023-04-01", 0.0005), ("2024-10-01", 0.0003503), ("2026-03-01", 0.000355299)],
         # ponytail: BSE SENSEX options were slab-priced per member before 2024-10-01 (Rs 500-3,750/crore); the flat 3,250 is used
         # for every day (UNCLEAR before Oct-2024; +-0.005% of premium = about Rs 2 per leg at 10 lots: immaterial)
         "SENSEX": [("2023-01-01", 0.000325)]}
LOT_D = {"NIFTY": [("2021-07-01", 50), ("2024-04-26", 25), ("2024-12-20", 75), ("2025-12-31", 65)],   # by contract EXPIRY date
         "SENSEX": [("2023-01-01", 10), ("2025-01-04", 20)]}
def _at(tab, d): return [v for f, v in tab if f <= d][-1]


def _dated(k):
    if COSTS == "today": return False
    assert COSTS == "dated" and k is not None, "COSTS=dated needs the sym-day key at every cost/qty call (no silent today rates)"
    return True


def qty(sym, k=None, lots=LOTS):
    """units traded for `lots` of today's lot; dated: the same exposure in whole lots of the size in force at the contract's expiry."""
    if not _dated(k): return LOT[sym] * lots
    lt = _at(LOT_D[sym], str(P[k]["exp"])[:10]); return max(1, round(LOT[sym] * lots / lt)) * lt


def cost(b, s, sym, k=None):
    """round-trip charges x CM for one leg bought at b and sold at s (per unit), at LOTS lots (qty)."""
    if _dated(k): q, tx_r, stt = qty(sym, k), _at(TXN_D[sym], k[1]), _at(STT_SELL, k[1])
    else: q, tx_r, stt = LOT[sym] * LOTS, TXN[sym], 0.0015
    bt, st = b * q, s * q; tx = tx_r * (bt + st); se = 1e-6 * (bt + st)
    return CM * (40 + tx + se + 0.18 * (40 + tx + se) + 0.00003 * bt + stt * st)


# untraded bars: a zero-volume 1m bar is a carry-forward print (O=H=L=C, the last trade) — 1% of ATM bars, ~20% at ATM+-10, 28% of
# SENSEX 2023. Never FILL on one (entries refuse, exits are priced by the bound and flagged forced). LAB_STALE=keep restores the old
# behaviour, which reproduces every row up to E39 exactly.
STALE_OK = os.environ.get("LAB_STALE") == "keep"
def stale(a, j): return (not STALE_OK) and a is not None and 0 <= j < len(a) and a[j, 6] == 0


# ---------------------------------------------------------------- spreads
_S = pd.read_csv(f"{OUT}/spreads.csv"); PB = np.array([20, 50, 100, 200, 400]); TB = np.array([570, 660, 840, 900])
HS = {}
for (sym, d0), g in _S.groupby(["sym", "dte0"]):
    a = np.full((5, 6), np.nan)
    for r in g.itertuples(): a[r.tb, r.pb] = r.p75
    # fill gaps along time, then along premium (audit 2026-10-28: SENSEX non-expiry pb=0 was empty -> NaN fills)
    a = pd.DataFrame(a).bfill().ffill().bfill(axis=1).ffill(axis=1).values; HS[(sym, d0)] = a
HSCOL = os.environ.get("HSCOL", "p75")
if HSCOL == "median":
    for (sym, d0), g in _S.groupby(["sym", "dte0"]):
        for r in g.itertuples(): HS[(sym, d0)][r.tb, r.pb] = r.median


def hs(sym, d0, m, p):
    return HS[(sym, d0)][np.searchsorted(TB, m, "right"), np.searchsorted(PB, p, "right")]


# ---------------------------------------------------------------- panel
IDX5Y = os.environ.get("IDX5Y", f"{OUT}/../idx1m.pkl")  # lab.py cache of data/recon 5y index 1m
def build():
    X = pd.read_parquet(f"{OUT}/opt1y.parquet")
    X = X[(X.m >= M0) & (X.m < M0 + NB)]
    offmax = int(os.environ.get("OFFMAX", "99")); X = X[X.off.abs() <= offmax]  # E39: OFFMAX=3 keeps the 5-year panel at the 1-year memory footprint
    # 2026-11-13 data hygiene (Fable verification of the 5y ATM+-10 panel): (1) Dhan's SENSEX 2023-24 files carry rows of ANOTHER underlying
    # (spot 20-34% off, own strikes, ~all zero volume): drop every row whose spot is > 1% from the index minute close (idx1m; the row median
    # where idx1m has no minute). (2) spot = per-minute median of the kept rows (was: the last row written). (3) a (side, strike, minute)
    # quoted twice with closes > 1% apart is unknowable: dropped (NaN), else the row nearest ATM wins. (4) ATM is carried forward only
    # (was ffill().bfill(): a leading gap took a LATER strike).
    try:
        I = pd.read_pickle(IDX5Y); I = I[I.sym.isin(X.sym.unique())].drop_duplicates(["sym", "day", "m"], keep="last").set_index(["sym", "day", "m"]).close
    except FileNotFoundError: I = None; print("build: no idx1m, spot reference = row median")
    IK = set(I.index.droplevel(2)) if I is not None else set()
    P = {}; drop = {}
    for (sym, day), g in X.groupby(["sym", "day"]):
        ref = g.groupby("m").spot.transform("median")
        if (sym, day) in IK: ref = g.m.map(I.loc[(sym, day)]).fillna(ref)
        ok = (g.spot / ref - 1).abs() <= 0.01; n0 = len(g); g = g[ok]
        g = g.assign(ao=g.off.abs()).sort_values("ao"); key = ["side", "strike", "m"]; cg = g.groupby(key).c
        g = g[~(cg.transform("max") > cg.transform("min") * 1.01 + 0.05)].drop_duplicates(key, keep="first")
        drop[(sym, day)] = (int(n0 - ok.sum()), int(ok.sum() - len(g)))
        sp = g.groupby("m").spot.median(); i = (sp.index.values - M0).astype(int)
        spot = np.full(NB, np.nan); spot[i] = sp.values; spot = pd.Series(spot).ffill().values
        a0 = g[(g.off == 0) & (g.side == "CE")]; atm = np.full(NB, np.nan); atm[a0.m.values - M0] = a0.strike.values
        atm = pd.Series(atm).ffill().values
        C = {}
        for (side, K), h in g.groupby(["side", "strike"]):
            a = np.full((NB, 7), np.nan); a[h.m.values - M0] = h[["o", "h", "l", "c", "oi", "iv", "vol"]].values; C[(side, K)] = a
        P[(sym, day)] = dict(spot=spot, atm=atm, C=C, exp=g.exp.iloc[0], dte=int(np.busday_count(day, g.exp.iloc[0])),
                             d0=int(day == g.exp.iloc[0]))
    D = pd.DataFrame([(k[0], k[1][:4], a, b) for k, (a, b) in drop.items()], columns=["sym", "yr", "other_underlying", "conflict"])
    print("build: rows dropped per sym-year\n", D.groupby(["sym", "yr"])[["other_underlying", "conflict"]].sum().to_string(), flush=True)
    return P


_OFF = os.environ.get("OFFMAX", "99"); PK = f"{OUT}/panel{'' if _OFF == '99' else '_off' + _OFF + 'h'}.pkl"  # E38/E42: one cached panel per strike window;
# the trailing h = built by the 2026-11-13 hygiene build() above (the pre-hygiene panel_off3/5/10.pkl of E38/E39 are left untouched for reproduction)
if not os.path.exists(PK): pickle.dump(build(), open(PK, "wb"))
P = pickle.load(open(PK, "rb"))
ALLK = sorted(P, key=lambda k: (k[1], k[0]))
KEYS = [k for k in ALLK if (k[1] >= HO) == HOLDOUT]
DAYS = sorted({k[1] for k in KEYS})
def month(d): return d[:7] if os.environ.get("LAB_FULL") else ("2025-11" if d < "2025-11-01" else d[:7])  # 1y panel: 10-27..10-31 join Nov
MONTHS = sorted({month(d) for d in DAYS})


def contract(k, i, side, itm=0):
    """strike `itm` steps in the money for `side` at bar i (ATM from the off-0 series)."""
    p = P[k]; K = p["atm"][i] + (-1 if side == "CE" else 1) * itm * STEP[k[0]]
    return p["C"].get((side, K)), K


# ---------------------------------------------------------------- one trade
def trade(k, i, side, itm=0, hold=15, stop=None, tgt=None, trail=None, atr_k=None, idx_stop=None, flat=FLAT, legs=None):
    """decision at close of bar i (minute M0+i). Returns (net INR, minutes held, forced) or None.
    stop/tgt/trail: fraction of entry premium. atr_k: stop = entry - atr_k * mean 1m range of the contract (15 bars).
    idx_stop: exit (next open) when spot moves idx_stop index points against. legs: list of (side, itm) for spreads."""
    if legs is not None:
        rs = [trade(k, i, s, it, hold, stop, tgt, trail, atr_k, idx_stop, flat) for s, it in legs]
        if any(r is None for r in rs): return None
        return sum(r[0] for r in rs), max(r[1] for r in rs), any(r[2] for r in rs)
    sym = k[0]; p = P[k]; a, K = contract(k, i, side, itm)
    e = i + 1; xe = min(e + hold, flat - M0) if hold else flat - M0
    if a is None or e >= xe or not np.isfinite(a[e, 0]) or stale(a, e): return None
    d0 = p["d0"]; en = a[e, 0] + hs(sym, d0, M0 + e, a[e, 0])
    sp = en * (1 - stop) if stop else None; tp = en * (1 + tgt) if tgt else None
    if atr_k:
        r = a[max(0, i - 14):i + 1, 1] - a[max(0, i - 14):i + 1, 2]; r = r[np.isfinite(r)]
        if not len(r): return None
        sp = en - atr_k * r.mean()
    s0 = p["spot"][i]; dirn = 1 if side == "CE" else -1; hi = en; x = None; forced = False; j = e
    for j in range(e, xe):
        o, h, l, c = a[j, :4]
        if not np.isfinite(o):
            x = a[j - 1, 3]; forced = True; break
        cs = sp
        if trail and j > e: cs = max(cs or 0, hi * (1 - trail))
        if cs is not None and l <= cs:
            x = min(cs, o); break
        if tp is not None and h >= tp:
            x = tp; break
        if trail: hi = max(hi, h)
        if idx_stop and dirn * (p["spot"][j] - s0) <= -idx_stop and j + 1 < xe:
            j += 1; x = a[j, 0] if np.isfinite(a[j, 0]) else c; break
    if x is None:
        j = xe; x = a[j, 0] if j < NB and np.isfinite(a[j, 0]) else a[j - 1, 3]
        if not np.isfinite(x): return None
    x = max(x - hs(sym, d0, M0 + j, x), 0.05)
    return (x - en) * qty(sym, k) - cost(en, x, sym, k), j - e, forced


# ---------------------------------------------------------------- placebo pools
_POOL = {}
_SRC = hashlib.md5(open(__file__, "rb").read()).hexdigest()[:8]
def pool(ex, itm=0, keys=None):
    """outcome of every (sym-day, decision minute, side) for one exit config: dict k -> (NB,2) array (CE, PE)."""
    key = (tuple(sorted(ex.items())), itm, HOLDOUT, HSCOL, CM, _SRC)  # any code/spread/cost change -> new cache file
    if key in _POOL: return _POOL[key]
    fp = f"{OUT}/pool_{hashlib.md5(str(key).encode()).hexdigest()[:10]}.pkl"
    if os.path.exists(fp): _POOL[key] = pickle.load(open(fp, "rb")); return _POOL[key]
    R = {}
    for k in KEYS:
        a = np.full((NB, 2), np.nan)
        for i in range(E_LO - M0, E_HI - M0 + 1):
            for s, side in enumerate(("CE", "PE")):
                r = trade(k, i, side, itm, **ex)
                if r: a[i, s] = r[0]
        R[k] = a
    pickle.dump(R, open(fp, "wb")); _POOL[key] = R; return R


def placebo(T, ex, itm=0, runs=1000):
    """T: list of (k, i, side, pnl). Returns (pct vs random minute+side, p, p_day)."""
    pl = pool(ex, itm); tot = sum(t[3] for t in T)
    byk = {}
    for t in T: byk.setdefault(t[0], []).append(t)
    rnd = np.zeros(runs); flip = np.zeros(runs)
    for k, ts in byk.items():
        a = pl[k]; ok = np.argwhere(np.isfinite(a))
        if not len(ok): continue
        pick = ok[RNG.integers(0, len(ok), (runs, len(ts)))]
        rnd += a[pick[..., 0], pick[..., 1]].sum(1)
        own = sum(t[3] for t in ts)
        opp = sum(a[t[1], 1 if t[2] == "CE" else 0] for t in ts)
        if not np.isfinite(opp): opp = -own
        f = RNG.random(runs) < 0.5; flip += np.where(f, opp, own)
    return (rnd < tot).mean() * 100, (rnd >= tot).mean(), (flip >= tot).mean()


def mom_side(k, i, h):
    s = P[k]["spot"]; return "CE" if s[i] - s[max(0, i - h)] >= 0 else "PE"


# ---------------------------------------------------------------- stats
ROWS = []
def report(name, T, ex, itm=0, mom_h=15, wf_months=None, runs=1000, extra="", day_pool=None):
    """T: list of (k, i, side, pnl, forced)."""
    NVAR[0] += 1
    if not T: ROWS.append(dict(name=name, n=0)); print(name, "no trades"); return
    v = np.array([t[3] for t in T]); cum = np.cumsum(v); dd = (cum - np.maximum.accumulate(np.maximum(cum, 0))).min()  # A2: peak starts at 0
    if day_pool is None:
        pct, p, pday = placebo(T, ex, itm, runs)
    else:  # day-level rule: same number of random days from the same months, same entry minute and exit
        ms = wf_months or MONTHS; cand = np.array([v_ for k_, v_ in day_pool.items() if month(k_[1]) in ms])
        rnd = np.array([RNG.choice(cand, len(T), replace=False).sum() for _ in range(runs)])
        tot_ = sum(t[3] for t in T); pct, p, pday = (rnd < tot_).mean() * 100, (rnd >= tot_).mean(), np.nan
    # momentum control on the same entries, same exit
    mt = [trade(t[0], t[1], mom_side(t[0], t[1], mom_h), itm, **ex) for t in T]
    mom = sum(r[0] for r in mt if r)
    agree = np.array([t[2] == mom_side(t[0], t[1], mom_h) for t in T])
    mo = pd.Series(v, index=[month(t[0][1]) for t in T]).groupby(level=0).sum()
    wm = mo.reindex(wf_months).fillna(0) if wf_months else mo
    sy = pd.Series(v, index=[t[0][0] for t in T]).groupby(level=0).sum()
    r = dict(name=name, n=len(v), win=round((v > 0).mean() * 100), avg=round(v.mean()), total=round(v.sum()), maxdd=round(dd),
             pct=round(pct, 1), p=round(p, 3), p_day=round(pday, 3), mom_same=round(mom), agree=round(agree.mean() * 100),
             tot_agree=round(v[agree].sum()), tot_disagree=round(v[~agree].sum()), n_dis=int((~agree).sum()),
             mpos=f"{(wm > 0).sum()}/{len(wm)}", NIFTY=round(sy.get("NIFTY", 0)), SENSEX=round(sy.get("SENSEX", 0)),
             lost=round(np.mean([t[4] for t in T]) * 100, 1), extra=extra)
    ROWS.append(r); print({k: r[k] for k in r}, flush=True)
    print("   by month:", {m: round(x / 1000) for m, x in mo.items()}, "k", flush=True)
    return r


def run_rule(sig, ex, itm=0, cool=15, keys=None):
    """sig(k) -> iterable of (i, side) candidate decisions in time order; one position per sym, cooldown = hold."""
    T = []
    for k in keys or KEYS:
        busy = -1
        for i, side in sig(k):
            if i < E_LO - M0 or i > E_HI - M0 or i <= busy: continue
            r = trade(k, i, side, itm, **ex)
            if r is None: continue
            T.append((k, i, side, r[0], r[2])); busy = i + max(r[1], cool)
    return T


# ---------------------------------------------------------------- causal per-minute features
def _get(k, side, K, i, col):
    a = P[k]["C"].get((side, K)); return a[i, col] if a is not None and 0 <= i < NB else np.nan


def feats(k, h=15):
    """one row per decision bar i (E_LO..E_HI). Only bars <= i are used. Same-instrument deltas over h bars."""
    p = P[k]; s = p["spot"]; st = STEP[k[0]]; rows = []
    for i in range(E_LO - M0, E_HI - M0 + 1):
        K = p["atm"][i]; j = max(0, i - h)  # clamp: a negative index would wrap to end-of-day (look-ahead)
        oc, op = _get(k, "CE", K, i, 4), _get(k, "PE", K, i, 4)
        oc0, op0 = _get(k, "CE", K, j, 4), _get(k, "PE", K, j, 4)
        pc, pp = _get(k, "CE", K, i, 3), _get(k, "PE", K, i, 3); pc0, pp0 = _get(k, "CE", K, j, 3), _get(k, "PE", K, j, 3)
        ic, ip = _get(k, "CE", K, i, 5), _get(k, "PE", K, i, 5); ic0, ip0 = _get(k, "CE", K, j, 5), _get(k, "PE", K, j, 5)
        Ks = K + st * np.arange(-3, 4)
        wc = np.array([_get(k, "CE", x, i, 4) - _get(k, "CE", x, j, 4) for x in Ks])
        wp = np.array([_get(k, "PE", x, i, 4) - _get(k, "PE", x, j, 4) for x in Ks])
        tc = np.nansum([_get(k, "CE", x, i, 4) for x in Ks]); tp = np.nansum([_get(k, "PE", x, i, 4) for x in Ks])
        vc = np.nansum(P[k]["C"].get(("CE", K), np.full((NB, 7), np.nan))[j + 1:i + 1, 6])
        vp = np.nansum(P[k]["C"].get(("PE", K), np.full((NB, 7), np.nan))[j + 1:i + 1, 6])
        dpc, dpp, doc, dop = pc - pc0, pp - pp0, oc - oc0, op - op0
        rows.append(dict(
            sym=k[0], day=k[1], i=i, m=M0 + i, dte=p["dte"], d0=p["d0"],
            r5=s[i] / s[max(0, i - 5)] - 1, r15=s[i] / s[j] - 1, r30=s[i] / s[max(0, i - 30)] - 1, r60=s[i] / s[max(0, i - 60)] - 1,
            rday=s[i] / s[0] - 1, rolled=float(p["atm"][j] != K),
            oi_flow=(dop - doc) / (op + oc),
            oi_flow_w=(np.nansum(wp) - np.nansum(wc)) / (tc + tp),
            pcr=np.log(tp / tc) if tc > 0 and tp > 0 else np.nan,
            skew=_get(k, "PE", K - 2 * st, i, 5) - _get(k, "CE", K + 2 * st, i, 5),
            dskew=(_get(k, "PE", K - 2 * st, i, 5) - _get(k, "CE", K + 2 * st, i, 5)) - (_get(k, "PE", K - 2 * st, j, 5) - _get(k, "CE", K + 2 * st, j, 5)),
            div_iv=(ic - ic0) - (ip - ip0),  # calls' IV rising vs puts' IV
            d_ivatm=(ic + ip - ic0 - ip0) / 2, ivatm=(ic + ip) / 2,
            lb=float(dpc > 0 and doc > 0) - float(dpp > 0 and dop > 0),     # long buildup CE minus PE
            sc=float(dpc > 0 and doc < 0) - float(dpp > 0 and dop < 0),     # short covering CE minus PE
            sb=float(dpc < 0 and doc > 0) - float(dpp < 0 and dop > 0),     # short buildup (writing) CE minus PE
            vratio=np.log(vc / vp) if vc > 0 and vp > 0 else np.nan,
            straddle=pc + pp, fwd15=s[min(i + 15, NB - 1)] / s[i] - 1, fwd30=s[min(i + 30, NB - 1)] / s[i] - 1,
            fwd60=s[min(i + 60, NB - 1)] / s[i] - 1))
    return rows


def feat_table():
    fp = f"{OUT}/feats.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    F = pd.DataFrame([r for k in ALLK for r in feats(k)]); F.to_pickle(fp); return F


# ---------------------------------------------------------------- daily vol table (realized vs implied)
def day_table():
    """per sym-day: iv at 09:30 (ATM CE/PE mean), intraday RV, straddle P&L 09:20->15:15, hold-to-expiry straddle."""
    rows = []
    for k in ALLK:
        p = P[k]; s = p["spot"]; i0 = 15; K = p["atm"][i0]
        ic, ip = _get(k, "CE", K, i0, 5), _get(k, "PE", K, i0, 5)
        lr = np.diff(np.log(s[i0:FLAT - M0 + 1])); rv = np.sqrt((lr ** 2).sum() * 375 / len(lr) * 252) * 100
        st0 = _get(k, "CE", K, i0, 3) + _get(k, "PE", K, i0, 3)
        e = [kk for kk in ALLK if kk[0] == k[0] and kk[1] == p["exp"]]
        sT = P[e[0]]["spot"][-1] if e else np.nan
        rows.append(dict(sym=k[0], day=k[1], dte=p["dte"], d0=p["d0"], S=s[i0], iv=np.nanmean([ic, ip]), rv=rv,
                         rng=(np.nanmax(s) - np.nanmin(s)) / s[i0], gap=np.nan, st0=st0, expiry_payoff=abs(sT - K) if e else np.nan,
                         open=s[0], close=s[-1]))
    D = pd.DataFrame(rows).sort_values(["sym", "day"])
    D["gap"] = D.groupby("sym").open.transform(lambda x: x) / D.groupby("sym").close.shift(1) - 1
    D["prev_rng"] = D.groupby("sym").rng.shift(1)
    D["rv_iv"] = D.rv / D.iv; D["exp_ratio"] = D.expiry_payoff / D.st0
    return D


# ---------------------------------------------------------------- generic feature rules
_F = None
def FT():
    global _F
    if _F is None:
        _F = feat_table(); _F = _F[(_F.day >= HO) == HOLDOUT].copy(); _F["mo"] = _F.day.map(month)
    return _F


def sig_from(mask_ce, mask_pe):
    """build sig(k) from boolean Series over FT() rows."""
    F = FT(); d = {}
    for r in F[mask_ce | mask_pe].itertuples():
        d.setdefault((r.sym, r.day), []).append((r.i, "CE" if mask_ce[r.Index] else "PE"))
    return lambda k: d.get(k, [])


def wf_thresh(col, q=0.8, sign=None, mlo=None, extra_mask=None):
    """walk-forward: for test month m, threshold = q-quantile of |col| over months < m (and sign = IC sign over months < m
    vs fwd30 unless given). Month 1 is training only. Returns (mask_ce, mask_pe, test months)."""
    F = FT(); ce = pd.Series(False, F.index); pe = pd.Series(False, F.index); ms = sorted(F.mo.unique())
    ok = extra_mask if extra_mask is not None else pd.Series(True, F.index)
    for n, m in enumerate(ms):
        if n == 0 and not HOLDOUT: continue
        tr = F[(F.mo < m) & ok] if not HOLDOUT else _dev_rows(col, ok)
        thr = min(tr[col].abs().quantile(q), 0.999 if set(tr[col].dropna().unique()) <= {-1.0, 0.0, 1.0} else np.inf)
        sg = sign if sign is not None else np.sign(tr[[col, "fwd30"]].corr(method="spearman").iloc[0, 1])
        te = (F.mo == m) & ok
        ce |= te & (sg * F[col] > thr); pe |= te & (sg * F[col] < -thr)
    return ce, pe, ms[1:] if not HOLDOUT else ms


def _dev_rows(col, ok):
    """holdout: fit on all dev months (frozen before looking)."""
    G = feat_table(); G = G[G.day < HO]
    return G


def fam_oi():
    F = FT(); thr = 0.1095; ex = dict(hold=15)
    ce, pe = F.oi_flow > thr, F.oi_flow < -thr
    report("F1a oi_flow frozen thr ATM h15", run_rule(sig_from(ce, pe), ex), ex)
    report("F1b oi_flow frozen thr ITM1 h15", run_rule(sig_from(ce, pe), ex, itm=1), ex, itm=1)
    nr = F.rolled == 0
    report("F1c oi_flow frozen, ATM not rolled", run_rule(sig_from(ce & nr, pe & nr), ex), ex)
    report("F1d oi_flow frozen, ATM rolled", run_rule(sig_from(ce & ~nr, pe & ~nr), ex), ex)
    c, p_, ms = wf_thresh("oi_flow", 0.8, sign=1)
    report("F1e oi_flow WF q0.8 ATM h15", run_rule(sig_from(c, p_), ex), ex, wf_months=ms)
    c, p_, ms = wf_thresh("r15", 0.8, sign=1)
    report("C1 momentum r15 WF q0.8 ATM h15", run_rule(sig_from(c, p_), ex), ex, wf_months=ms)
    c, p_, ms = wf_thresh("oi_flow_w", 0.8, sign=1)
    report("F1f oi_flow over ATM+-3 WF q0.8 h15", run_rule(sig_from(c, p_), ex), ex, wf_months=ms)


# ---------------------------------------------------------------- F2 volatility timing (buyers)


def vol_days(i0=30):
    """per sym-day features known at bar i0 (09:45) + HAR-RV forecast fitted on 5y index days before 2025-10-27."""
    fp = f"{OUT}/voldays{'' if i0 == 30 else i0}_{_SRC}.pkl"  # keyed by this file's hash (Fable B-1: stale caches survived code changes)
    if os.path.exists(fp): return pd.read_pickle(fp)
    D = pd.read_pickle(IDX5Y); D = D[D.sym.isin(["NIFTY", "SENSEX"]) & (D.day < "2025-10-27")]
    hist = D.groupby(["sym", "day"]).close.apply(lambda c: np.sqrt((np.diff(np.log(c.values)) ** 2).sum() * 252) * 100)
    rows = []
    for k in ALLK:
        p = P[k]; s = p["spot"]; K = p["atm"][i0]
        rows.append(dict(sym=k[0], day=k[1], dte=p["dte"], d0=p["d0"],
                         rvd=np.sqrt((np.diff(np.log(s)) ** 2).sum() * 252) * 100,
                         rv_or=np.sqrt((np.diff(np.log(s[:i0 + 1])) ** 2).sum() * 252 * 375 / i0) * 100,
                         orw=(s[:i0 + 1].max() - s[:i0 + 1].min()) / s[i0], open=s[0], close=s[-1],
                         iv=np.nanmean([_get(k, "CE", K, i0, 5), _get(k, "PE", K, i0, 5)]),
                         st=_get(k, "CE", K, i0, 3) + _get(k, "PE", K, i0, 3), S=s[i0], dirn=np.sign(s[i0] - s[0])))
    V = pd.DataFrame(rows).sort_values(["sym", "day"]); out = []
    for sym, g in V.groupby("sym"):
        h = hist.loc[sym]; h = h[(h > 0.5) & ~h.index.isin(g.day)]  # 5y panel (E39): panel days override the index history (no duplicate days)
        rv = pd.concat([h, g.set_index("day").rvd]).dropna()
        rv = rv[~rv.index.duplicated(keep="last")].sort_index(); lr = np.log(rv)
        X = pd.DataFrame({"d1": lr.shift(1), "w": lr.shift(1).rolling(5).mean(), "m": lr.shift(1).rolling(22).mean(), "y": lr}).dropna()
        tr = X[X.index < "2025-10-27"]; A = np.c_[np.ones(len(tr)), tr[["d1", "w", "m"]].values]
        b = np.linalg.lstsq(A, tr.y.values, rcond=None)[0]; print(sym, "HAR b", b.round(3), "n", len(tr))
        f = np.exp(np.c_[np.ones(len(X)), X[["d1", "w", "m"]].values] @ b)
        g = g.assign(har=pd.Series(f, X.index).reindex(g.day).values,
                     prev_rng=pd.Series(rv.values, rv.index).shift(1).reindex(g.day).values,
                     gap=(g.open / g.close.shift(1) - 1).abs(),
                     ivpct=g.iv.rolling(40, min_periods=10).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True))
        out.append(g)
    V = pd.concat(out)
    V["har_iv"] = V.har / V.iv; V["or_iv"] = V.rv_or / V.iv; V["prev_iv"] = V.prev_rng / V.iv
    V["gap_iv"] = V.gap * np.sqrt(252) * 100 / V.iv; V["cheap"] = -V.ivpct
    V["mo"] = V.day.map(month); V.to_pickle(fp); return V


def day_rule(cond, i0=30, side_col=None):
    d = {}
    for r in cond.itertuples():
        d[(r.sym, r.day)] = [(i0, ("CE" if getattr(r, side_col) >= 0 else "PE") if side_col else "CE")]
    return lambda k: d.get(k, [])


def wf_day(V, col, q=0.7, i0=30):
    """walk-forward: trade days with col > q-quantile of col over prior months (dev months for holdout)."""
    out = []; ms = sorted(V.mo.unique())
    G = vol_days(i0); G = G[G.day < HO]
    for n, m in enumerate(ms):
        tr = G if HOLDOUT else V[V.mo < m]
        if not HOLDOUT and n == 0: continue
        out.append(V[(V.mo == m) & (V[col] > tr[col].quantile(q))])
    return pd.concat(out), (ms if HOLDOUT else ms[1:])


def fam_vol():
    V = vol_days(); V = V[(V.day >= HO) == HOLDOUT]
    strad = dict(hold=None, legs=(("CE", 0), ("PE", 0)))
    print("realized/implied (rv full day / iv 09:45) by sym x dte:")
    print(V.assign(r=V.rvd / V.iv).groupby(["sym", "dte"]).r.agg(["count", "median", "mean"]).round(2).unstack(0).to_string())
    T0 = run_rule(day_rule(V), strad); DP = {t[0]: t[3] for t in T0}
    report("F2a straddle 09:46->15:15 every day", T0, strad)
    for d in range(5):
        report(f"F2a straddle every day, DTE={d}", run_rule(day_rule(V[V.dte == d]), strad), strad, day_pool=DP)
    for col in ["har_iv", "or_iv", "prev_iv", "gap_iv", "cheap"]:
        c, ms = wf_day(V, col, 0.7)
        report(f"F2b straddle if {col} > WF q0.7", run_rule(day_rule(c), strad), strad, wf_months=ms, day_pool=DP)
    c, ms = wf_day(V, "or_iv", 0.7); ex = dict(hold=None)
    report("F2c ATM in 09:15-09:45 direction if or_iv > WF q0.7, to 15:15", run_rule(day_rule(c, side_col="dirn"), ex), ex, wf_months=ms)
    print(V[["har_iv", "or_iv", "prev_iv", "gap_iv", "ivpct"]].corrwith(V.rvd / V.iv, method="spearman").round(3).to_dict(), "<- Spearman with realized/implied")


# ---------------------------------------------------------------- F3 expiry-day (gamma) dynamics
def fam_exp():
    K0 = [k for k in KEYS if P[k]["d0"]]; strad = dict(hold=None, legs=(("CE", 0), ("PE", 0)))
    at = lambda m: m - M0
    T = run_rule(lambda k: [(at(810), "CE")], strad, keys=K0); DP = {t[0]: t[3] for t in T}
    report("F3a expiry straddle 13:30->15:15", T, strad, day_pool=DP)
    report("F3a expiry straddle 14:15->15:15", run_rule(lambda k: [(at(855), "CE")], strad, keys=K0), strad)
    # b) only if morning realized vol / IV at 13:30 is high (WF q0.7 over prior months' expiry days)
    rows = []
    for k in K0:
        s = P[k]["spot"]; i = at(810); K = P[k]["atm"][i]
        rv = np.sqrt((np.diff(np.log(s[:i + 1])) ** 2).sum() * 252 * 375 / i) * 100
        rows.append(dict(sym=k[0], day=k[1], mo=month(k[1]), r=rv / np.nanmean([_get(k, "CE", K, i, 5), _get(k, "PE", K, i, 5)])))
    E = pd.DataFrame(rows); c, ms = wf_day(E, "r", 0.7) if not HOLDOUT else (E[E.r > _EXP_THR[0]], MONTHS)
    report("F3b expiry straddle 13:30 if morning RV/IV > WF q0.7", run_rule(day_rule(c, i0=at(810)), strad, keys=K0), strad,
           wf_months=ms, day_pool=DP)
    # c) gamma breakout of the 12:00-13:00 range after 13:00 (first break), ATM, 30 min and to 15:15
    def brk(k):
        s = P[k]["spot"]; a, b = at(720), at(780); hi, lo = s[a:b].max(), s[a:b].min()
        for i in range(b, at(900)):
            if s[i] > hi: return [(i, "CE")]
            if s[i] < lo: return [(i, "PE")]
        return []
    for h in (30, None):
        ex = dict(hold=h); report(f"F3c expiry breakout 12-13h range, ATM, hold {h or 'EOD'}", run_rule(brk, ex, keys=K0), ex, mom_h=60)
    # d) pin to the max-OI strike (CE+PE OI, ATM+-3) at 13:30: buy ATM toward it if > 1 step away, to 15:15
    def pin(k):
        i = at(810); p = P[k]; st = STEP[k[0]]; Ks = p["atm"][i] + st * np.arange(-3, 4)
        oi = [np.nansum([_get(k, "CE", x, i, 4), _get(k, "PE", x, i, 4)]) for x in Ks]; Km = Ks[int(np.argmax(oi))]
        d = Km - p["spot"][i]
        return [(i, "CE" if d > 0 else "PE")] if abs(d) > st else []
    ex = dict(hold=None); report("F3d expiry pin: ATM toward max-OI strike 13:30->15:15", run_rule(pin, ex, keys=K0), ex, mom_h=60)
    def unpin(k):
        r = pin(k); return [(i, "PE" if sd == "CE" else "CE") for i, sd in r]
    report("F3e expiry anti-pin: ATM away from max-OI strike", run_rule(unpin, ex, keys=K0), ex, mom_h=60)


_EXP_THR = [np.nan]


# ---------------------------------------------------------------- F4 OI + IV + price structure
F4COLS = ["oi_flow", "oi_flow_w", "pcr", "skew", "dskew", "div_iv", "d_ivatm", "lb", "sc", "sb", "vratio", "r15", "rday"]


def ic_table(F, y="fwd30"):
    """monthly Spearman IC (raw and after removing a within-month OLS fit on r5, r15, r60 = partial-out momentum)."""
    out = []
    for c in F4COLS:
        raw, part = [], []
        for m, g in F.groupby("mo"):
            g = g[list(dict.fromkeys([c, y, "r5", "r15", "r60"]))].dropna()
            if len(g) < 500: continue
            raw.append(g[c].corr(g[y], method="spearman"))
            A = np.c_[np.ones(len(g)), g[["r5", "r15", "r60"]].values]
            res = g[c].values - A @ np.linalg.lstsq(A, g[c].values, rcond=None)[0]
            part.append(pd.Series(res).corr(pd.Series(g[y].values), method="spearman"))
        raw, part = np.array(raw), np.array(part)
        out.append(dict(feat=c, ic=raw.mean().round(4), t=(raw.mean() / raw.std(ddof=1) * np.sqrt(len(raw))).round(2),
                        pos_m=f"{(raw > 0).sum()}/{len(raw)}", ic_partial=part.mean().round(4),
                        t_partial=(part.mean() / part.std(ddof=1) * np.sqrt(len(part))).round(2)))
    return pd.DataFrame(out)


def fam_f4():
    F = FT()
    for y in ("fwd15", "fwd30", "fwd60"):
        print("IC vs", y); print(ic_table(F, y).to_string(index=False))
    E = F[F.d0 == 1]; print("IC vs fwd30, expiry days only"); print(ic_table(E, "fwd30").to_string(index=False))
    ex = dict(hold=30)
    for c in F4COLS:
        ce, pe, ms = wf_thresh(c, 0.8)
        report(f"F4 {c} WF sign+q0.8 ATM h30", run_rule(sig_from(ce, pe), ex, cool=30), ex, wf_months=ms)


# ---------------------------------------------------------------- F5 walk-forward ML (predictions from opt1y_ml.py)
def fam_ml():
    Q = pd.read_csv(f"{OUT}/preds_{'ho' if HOLDOUT else 'dev'}.csv"); ex = dict(hold=30)
    for nm, g in Q.groupby("model"):
        d = {}
        for r in g.itertuples():
            if r.p > r.thr_hi or r.p < r.thr_lo: d.setdefault((r.sym, r.day), []).append((r.i, "CE" if r.p > r.thr_hi else "PE"))
        ms = sorted({month(x) for x in g.day})
        report(f"F5 ML {nm} top/bottom decile, ATM h30", run_rule(lambda k: d.get(k, []), ex, cool=30), ex, wf_months=ms)


# ---------------------------------------------------------------- robustness of the two dev survivors
def fam_rob():
    F = FT()
    for q in (0.7, 0.8, 0.9):
        for h in (15, 30, 60):
            ce, pe, ms = wf_thresh("r15", q, sign=-1); ex = dict(hold=h)
            report(f"R fade r15 q{q} ATM h{h}", run_rule(sig_from(ce, pe), ex, cool=h), ex, wf_months=ms)
    ce, pe, ms = wf_thresh("r15", 0.8, sign=-1); ex = dict(hold=30)
    report("R fade r15 q0.8 ITM1 h30", run_rule(sig_from(ce, pe), ex, itm=1, cool=30), ex, itm=1, wf_months=ms)
    report("R fade r15 q0.8 OTM1 h30", run_rule(sig_from(ce, pe), ex, itm=-1, cool=30), ex, itm=-1, wf_months=ms)
    n0 = F.d0 == 0
    report("R fade r15 q0.8 h30 non-expiry days", run_rule(sig_from(ce & n0, pe & n0), ex, cool=30), ex, wf_months=ms)
    am = F.m < 720
    report("R fade r15 q0.8 h30 before 12:00", run_rule(sig_from(ce & am, pe & am), ex, cool=30), ex, wf_months=ms)
    report("R fade r15 q0.8 h30 after 12:00", run_rule(sig_from(ce & ~am, pe & ~am), ex, cool=30), ex, wf_months=ms)
    for c in ("r5", "r30", "r60"):
        ce2, pe2, ms2 = wf_thresh(c, 0.8, sign=-1)
        report(f"R fade {c} q0.8 ATM h30", run_rule(sig_from(ce2, pe2), ex, cool=30), ex, wf_months=ms2)
    strad = dict(hold=None, legs=(("CE", 0), ("PE", 0)))
    V = vol_days(); V = V[(V.day >= HO) == HOLDOUT]; DP = {t[0]: t[3] for t in run_rule(day_rule(V), strad)}
    for q in (0.5, 0.6, 0.8, 0.9):
        c, ms = wf_day(V, "or_iv", q)
        report(f"R straddle or_iv q{q} 09:46->15:15", run_rule(day_rule(c), strad), strad, wf_months=ms, day_pool=DP)
    c, ms = wf_day(V, "or_iv", 0.7)
    for h in (60, 120, 210):
        sx = dict(hold=h, legs=strad["legs"])
        report(f"R straddle or_iv q0.7 hold {h}m", run_rule(day_rule(c), sx), sx, wf_months=ms)
    report("R straddle or_iv q0.7 non-expiry", run_rule(day_rule(c[c.d0 == 0]), strad), strad, wf_months=ms, day_pool=DP)
    for i0 in (15, 60):
        W = vol_days(i0); W = W[(W.day >= HO) == HOLDOUT]; DPi = {t[0]: t[3] for t in run_rule(day_rule(W, i0=i0), strad)}
        c, ms = wf_day(W, "or_iv", 0.7, i0=i0)
        report(f"R straddle or_iv q0.7 opening window {i0}m", run_rule(day_rule(c, i0=i0), strad), strad, wf_months=ms, day_pool=DPi)
    c, ms = wf_day(V, "or_iv", 0.7); sg = dict(hold=None, legs=(("CE", -1), ("PE", -1)))
    report("R strangle (OTM1 each) or_iv q0.7", run_rule(day_rule(c), sg), sg, wf_months=ms)


# ---------------------------------------------------------------- exits on identical entries (fade r15 q0.8)
EXITS = {"time15": dict(hold=15), "time30": dict(hold=30), "time60": dict(hold=60), "EOD": dict(hold=None),
         "SL15/TP30 (60m cap)": dict(hold=60, stop=0.15, tgt=0.30), "SL20/TP40 (60m)": dict(hold=60, stop=0.2, tgt=0.4),
         "SL30/TP60 (EOD)": dict(hold=None, stop=0.3, tgt=0.6), "trail15 (60m)": dict(hold=60, trail=0.15),
         "trail25 (EOD)": dict(hold=None, trail=0.25), "ATRx3 (60m)": dict(hold=60, atr_k=3), "ATRx6 (60m)": dict(hold=60, atr_k=6),
         "ATRx3+TP30 (60m)": dict(hold=60, atr_k=3, tgt=0.3)}


def fam_exit():
    ce, pe, ms = wf_thresh("r15", 0.8, sign=-1); d = {}
    for r in FT()[ce | pe].itertuples(): d.setdefault((r.sym, r.day), []).append((r.i, "CE" if ce[r.Index] else "PE"))
    ent = run_rule(lambda k: d.get(k, []), dict(hold=30), cool=30)  # fixed entry set (base rule)
    for nm, ex in list(EXITS.items()) + [("index stop 0.15% (60m)", "idx")]:
        T = []
        for k, i, side, _, _ in ent:
            e2 = ex if ex != "idx" else dict(hold=60, idx_stop=P[k]["spot"][i] * 0.0015)
            r = trade(k, i, side, 0, **e2)
            if r: T.append((k, i, side, r[0], r[2]))
        e2 = ex if ex != "idx" else dict(hold=60)
        rp = pool(e2); rnd = np.nanmean(np.concatenate([a[E_LO - M0:E_HI - M0 + 1].ravel() for a in rp.values()]))
        report(f"X fade entries, exit {nm}", T, e2, wf_months=ms, extra=f"random-entry avg {rnd:.0f}")
        print("   random-entry avg/trade with this exit:", round(rnd))


# ---------------------------------------------------------------- R3 new information sources (scripts/lab5y/ext_fetch.py)
EXT = os.environ.get("EXT", os.path.join(os.path.dirname(__file__), "../../data/cache/ext"))
# E39-E41 (2026-11-13, before any LEARN-year result): the 5-year panel needs the LEARN-year events too (before this the lists held our year
# only, so E33's EVENT regime and E40 saw no RBI / FOMC day in 2021-2025). SCHEDULED MPC decision days only (rbi.org.in calendars and
# reschedule notices: Feb-2022 moved to the 10th, Aug-2022 to the 5th); the unscheduled 2022-05-04 hike was announced intraday without
# notice, so it is NOT a pre-known event and is left out on purpose. FOMC = statement day (federalreserve.gov, US date, ~23:30 IST).
RBI_LEARN = {"2021-12-08", "2022-02-10", "2022-04-08", "2022-06-08", "2022-08-05", "2022-09-30", "2022-12-07", "2023-02-08", "2023-04-06",
             "2023-06-08", "2023-08-10", "2023-10-06", "2023-12-08", "2024-02-08", "2024-04-05", "2024-06-07", "2024-08-08", "2024-10-09",
             "2024-12-06", "2025-02-07", "2025-04-09", "2025-06-06", "2025-08-06", "2025-10-01"}
FOMC_LEARN = ["2021-11-03", "2021-12-15", "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02",
              "2022-12-14", "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
              "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18", "2025-01-29",
              "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17"]
RBI = RBI_LEARN | {"2025-12-05", "2026-02-06", "2026-04-08", "2026-06-05", "2026-08-05", "2026-10-07"}  # rbi.org.in, 10:00 IST
def fomc_next(days, F=None):
    """first panel day after each FOMC statement day inside the panel (an FOMC before the first panel day maps to nothing, not to day 1)."""
    return {next(d for d in days if d > f) for f in (FOMC if F is None else F) if days[0] <= f < days[-1]}
FOMC = FOMC_LEARN + ["2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]  # federalreserve.gov
DIRC = ["fii_fut", "fii_opt", "spx", "inr", "oil"]  # sign fixed a priori: + -> CE (oil = -Brent: India imports oil)
VOLC = ["vix", "aspx", "ainr", "aoil"]


def ext_table():
    """per day T: values known before 09:15 IST. NSE participant OI as on the last 2 NSE days before T; FRED last 2 US dates < T."""
    import glob
    R = []
    for f in sorted(glob.glob(f"{EXT}/nse_poi/*.csv")):
        x = pd.read_csv(f, skiprows=1); x.columns = [c.strip() for c in x.columns]; x = x.set_index(x.columns[0]).loc["FII"].astype(float)
        R.append(dict(d=os.path.basename(f)[:10],
                      fut=(x["Future Index Long"] - x["Future Index Short"]) / (x["Future Index Long"] + x["Future Index Short"]),
                      opt=((x["Option Index Call Long"] - x["Option Index Call Short"]) - (x["Option Index Put Long"] - x["Option Index Put Short"]))
                      / x[["Option Index Call Long", "Option Index Call Short", "Option Index Put Long", "Option Index Put Short"]].sum()))
    N = pd.DataFrame(R).set_index("d").sort_index().diff()
    F = {s: pd.read_csv(f"{EXT}/{s}.csv", index_col=0, na_values=".").iloc[:, 0].dropna() for s in ("SP500", "VIXCLS", "DEXINUS", "DCOILBRENTEU")}
    F = {s: np.log(v).diff().dropna() for s, v in F.items()}
    days = sorted({k[1] for k in ALLK}); fomc1 = fomc_next(days); out = []
    for d in days:
        prev = lambda s: s[s.index < d].iloc[-1] if (s.index < d).any() else np.nan
        out.append(dict(day=d, fii_fut=prev(N.fut), fii_opt=prev(N.opt), spx=prev(F["SP500"]), vix=prev(F["VIXCLS"]),
                        inr=-prev(F["DEXINUS"]), oil=-prev(F["DCOILBRENTEU"]), rbi=d in RBI, fomc=d in fomc1))
    E = pd.DataFrame(out); E["aspx"], E["ainr"], E["aoil"] = E.spx.abs(), E.inr.abs(), E.oil.abs(); return E


def wf_ext(V, col, q=0.7):
    """trade days with col > q-quantile over prior months (all dev months for the holdout)."""
    out, ms = [], sorted(V[(V.day >= HO) == HOLDOUT].mo.unique())
    for n, m in enumerate(ms):
        tr = V[V.day < HO] if HOLDOUT else V[V.mo < m]
        if not HOLDOUT and n == 0: continue
        cur = V[V.mo == m]; out.append(cur[cur[col] > tr[col].quantile(q)])
    return pd.concat(out), (ms if HOLDOUT else ms[1:])


def fam_ext():
    VA = vol_days().merge(ext_table(), on="day", how="left")
    VA["rev_fii_fut"] = -VA.fii_fut  # added after dev showed fii_fut worse than a coin flip (post-hoc, 10th variant)
    for c in DIRC + ["rev_fii_fut"]: VA["a_" + c] = VA[c].abs()
    V = VA[(VA.day >= HO) == HOLDOUT]
    print("coverage (non-null days):", V[DIRC + VOLC].notna().sum().to_dict(), "rbi", int(V.rbi.sum()), "fomc", int(V.fomc.sum()))
    y_dir = np.log(V.close / V.S); y_vol = V.rvd / V.iv
    print("Spearman with 09:45->close spot move:", V[DIRC].corrwith(y_dir, method="spearman").round(3).to_dict())
    print("Spearman with realized/implied:", V[VOLC + ["a_fii_fut", "a_fii_opt"]].corrwith(y_vol, method="spearman").round(3).to_dict())
    strad = dict(hold=None, legs=(("CE", 0), ("PE", 0))); DP = {t[0]: t[3] for t in run_rule(day_rule(V), strad)}; ex = dict(hold=None)
    for c in DIRC + ["rev_fii_fut"]:  # ATM in the sign's direction 09:46->15:15 on days with a big |move|; p_day = same days, coin-flip side
        d, ms = wf_ext(VA.dropna(subset=[c]), "a_" + c)
        report(f"R3 dir ATM 09:46->15:15 by sign({c}) if |{c}| > WF q0.7", run_rule(day_rule(d, side_col=c), ex), ex, wf_months=ms)
    for c in VOLC:
        d, ms = wf_ext(VA.dropna(subset=[c]), c)
        report(f"R3 straddle 09:46->15:15 if {c} > WF q0.7", run_rule(day_rule(d), strad), strad, wf_months=ms, day_pool=DP)
    for c in ("rbi", "fomc"):
        report(f"R3 straddle 09:46->15:15 on {c} days", run_rule(day_rule(V[V[c]]), strad), strad, day_pool=DP)


# ---------------------------------------------------------------- pre-named finalists (frozen on dev; run with --holdout ONCE)
def fam_final():
    strad = dict(hold=None, legs=(("CE", 0), ("PE", 0)))
    V = vol_days(); V = V[(V.day >= HO) == HOLDOUT]; DP = {t[0]: t[3] for t in run_rule(day_rule(V), strad)}
    report("FIN0 reference: straddle 09:46->15:15 every day", list(DP and [(k, 30, "CE", v, False) for k, v in DP.items()]), strad, day_pool=DP)
    c, ms = wf_day(V, "or_iv", 0.7)
    report("FIN1 straddle 09:46->15:15 if or_iv > q0.7", run_rule(day_rule(c), strad), strad, wf_months=ms, day_pool=DP)
    report("FIN2 same, non-expiry days only", run_rule(day_rule(c[c.d0 == 0]), strad), strad, wf_months=ms, day_pool=DP)
    F = FT(); ce, pe, ms = wf_thresh("r15", 0.8, sign=-1); am = F.m < 720; ex = dict(hold=30)
    report("FIN3 fade r15 q0.8 ATM h30, decisions before 12:00", run_rule(sig_from(ce & am, pe & am), ex, cool=30), ex, wf_months=ms)


def show():
    if not ROWS: return
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    R = pd.DataFrame(ROWS); print(R.drop(columns=["extra"]).to_string(index=False)); print("variants so far:", NVAR[0])
    R.to_csv(f"{OUT}/rows_{'ho' if HOLDOUT else 'dev'}_{'_'.join(a for a in sys.argv[2:] if not a.startswith('-'))}.csv", index=False)


FAM = {"oi": fam_oi, "vol": fam_vol, "exp": fam_exp, "f4": fam_f4, "ml": fam_ml, "rob": fam_rob, "exit": fam_exit, "final": fam_final, "ext": fam_ext}
if __name__ == "__main__":
    for f in [a for a in sys.argv[2:] if not a.startswith("-")]: FAM[f]()
    show()
