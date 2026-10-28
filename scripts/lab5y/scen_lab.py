"""E21: strategies x scenarios (paper research; no orders). Implements the frozen E21 spec (registry row E21; amendments: FLAT follows main, test cells < 15 days untestable).
Run (cwd scripts/lab5y):  ~/paper_extra_venv/bin/python scen_lab.py OUT <selftest|step0|devA|devB|testA|testB> [--test]
OUT = the round-2 dir (panel.pkl, spreads.csv, voldays.pkl); never pass --holdout (E21 splits are built here from L.ALLK).
testA / testB need --test and read the selected_*.json written by devA / devB; run them ONCE, after review.
Caches and CSVs go to $E21_DIR (outside the repo). Reuses sell_lab (struct, summ, orb_signals, e13_signals) and opt1y_lab."""
import sys, os, json, time, pickle, hashlib, warnings, numpy as np, pandas as pd
import sell_lab as S

warnings.filterwarnings("ignore")
L = S.L; P = L.P; M0, NB, STEP = L.M0, L.NB, L.STEP
E21 = os.environ.get("E21_DIR", f"{L.OUT}/e21")
os.makedirs(E21, exist_ok=True)
IDX = os.environ.get("IDX5Y", f"{L.OUT}/../idx1m.pkl")
_SRC = hashlib.md5(b"".join(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read()
                           for f in ("scen_lab.py", "sell_lab.py", "opt1y_lab.py"))).hexdigest()[:6]  # any engine change -> new caches
STEPB = dict(NIFTY=50, SENSEX=100, BANKNIFTY=100)
ALLD = sorted({k[1] for k in L.ALLK}); DEV_END = ALLD[147]; T1_END = "2026-07-24"; B_CUT, B_END = "2024-02-23", "2025-10-27"
DAYS_A = {"dev": ALLD[:148], "test": ALLD[148:]}; KA = {s: [k for k in L.ALLK if k[1] in set(DAYS_A[s])] for s in DAYS_A}
STR = ["S1", "LS", "E5A", "E5B", "MOM", "E13", "FIB", "PDB", "PDR", "TWAP"]
DIR = {"E5A", "E5B", "MOM", "FIB", "PDB", "PDR", "TWAP"}
V9S = {"E5A", "E5B", "E13", "FIB", "PDB", "PDR", "TWAP"}; V10S = {"E5A", "E5B", "MOM", "FIB", "PDB", "PDR"}
T2S = {"S1", "LS", "E5A", "E5B", "MOM", "E13"}
BK = {"GAP": ["DN", "FLAT", "UP"], "ORW": ["NARROW", "NORMAL", "WIDE"], "TREND": ["UP", "DN"], "MOM5": ["DN", "FLAT", "UP"],
      "LOC20": ["LOW", "MID", "HIGH"], "IVR": ["LOW", "MID", "HIGH"], "PRNG": ["NR", "NORM", "WR"], "DTE": ["0", "1", "2+"],
      "EXT52": ["DEEP", "MID", "TOP"], "TOD": ["EARLY", "MID", "LATE"], "TWS": ["WITH", "AGAINST"]}
DAYA = ["GAP", "ORW", "TREND", "MOM5", "LOC20", "IVR", "PRNG", "DTE"]; DAYB = ["GAP", "ORW", "TREND", "MOM5", "LOC20", "PRNG", "EXT52"]
BSTR = ["E5A", "E5B", "MOM", "FIB", "PDB", "PDR", "TWAP"]
X = lambda i, d: dict(dirn=d, s_tgt=2, s_stp=1, flat=min(L.FLAT, 555 + i + 1 + 60))
SIGN = lambda sd: 1 if sd == "CE" else -1
def vars_for(st, day): return day + (["TOD"] if st in V9S else []) + (["TWS"] if st in V10S else [])
def tod(i): return "EARLY" if i <= 104 else ("MID" if i <= 224 else "LATE")
def tws(s, i, sd): return "WITH" if np.sign(s[i] - s[:i + 1].mean()) == SIGN(sd) else "AGAINST"


# ---------------------------------------------------------------- signals (pure functions of s[0..i]; s = 375 closes, 1 per minute)
def fib(s, st):
    """Fibonacci 61.8-78.6% pullback then 50% re-cross; first trigger; both sides on one bar -> skip the bar."""
    n = min(len(s), 286); cmx, cmn = np.maximum.accumulate(s), np.minimum.accumulate(s); hi = lo = 0
    for i in range(1, n):
        if s[i - 1] > s[hi]: hi = i - 1
        if s[i - 1] < s[lo]: lo = i - 1
        if i < 61: continue
        up = dn = False
        if hi <= i - 5:
            H = s[hi]; A = H - cmn[hi]
            if A >= 3 * st: up = H - 0.786 * A < s[hi:i + 1].min() <= H - 0.618 * A and s[i - 1] <= H - 0.5 * A < s[i]
        if lo <= i - 5:
            Lw = s[lo]; A = cmx[lo] - Lw
            if A >= 3 * st: dn = Lw + 0.618 * A <= s[lo:i + 1].max() < Lw + 0.786 * A and s[i - 1] >= Lw + 0.5 * A > s[i]
        if up != dn: return [(i, "CE" if up else "PE")]
    return []


def pdb(s, pdh, pdl):
    if len(s) < 32 or not (np.isfinite(pdh) and np.isfinite(pdl)): return []
    okc, okp = s[30] <= pdh, s[30] >= pdl  # a side already beyond its level at 09:45 is skipped
    for i in range(31, min(len(s), 286)):
        if okc and s[i - 1] <= pdh < s[i]: return [(i, "CE")]
        if okp and s[i - 1] >= pdl > s[i]: return [(i, "PE")]
    return []


def pdr(s, pdh, pdl):
    r = pdb(s, pdh, pdl)
    if not r: return []
    i, sd = r[0]
    for j in range(i + 1, min(i + 15, 285, len(s) - 1) + 1):
        if sd == "CE" and s[j] <= pdh: return [(j, "PE")]
        if sd == "PE" and s[j] >= pdl: return [(j, "CE")]
    return []


def twap(s, st):
    d = (s - np.cumsum(s) / np.arange(1, len(s) + 1)) / st
    for i in range(46, min(len(s), 286)):
        if abs(d[i]) >= 2 and abs(d[i - 1]) < 2: return [(i, "PE" if d[i] > 0 else "CE")]
    return []


def mom(s): return [] if len(s) < 76 or s[75] == s[60] else [(75, "CE" if s[75] > s[60] else "PE")]


def orbs(s, fade):
    """S.orb_signals on an arbitrary close series (temporary panel entry)."""
    k = ("_t", "0"); P[k] = dict(spot=s)
    try: return S.orb_signals(k, fade)
    finally: del P[k]


def sg(st, s, stp, pdh, pdl):
    if not np.isfinite(s[:286]).all(): return []
    return {"E5A": lambda: orbs(s, False), "E5B": lambda: orbs(s, True), "MOM": lambda: mom(s), "FIB": lambda: fib(s, stp),
            "PDB": lambda: pdb(s, pdh, pdl), "PDR": lambda: pdr(s, pdh, pdl), "TWAP": lambda: twap(s, stp)}[st]()


# ---------------------------------------------------------------- daily table and scenario labels
def tri(x, lo, hi, nm):
    return pd.Series(np.where(x.isna(), None, np.where(lo, nm[0], np.where(hi, nm[2], nm[1]))), index=x.index, dtype=object)


def dfeat(d):
    """d: index day, columns O H L C orr (orr = max-min of closes of bars 0..30). Labels use only days < t (orr only its own bars 0..30)."""
    pc = d.C.shift(1); tr = pd.concat([d.H - d.L, (d.H - pc).abs(), (d.L - pc).abs()], axis=1).max(axis=1)
    atr = tr.shift(1).rolling(20).mean(); f = pd.DataFrame(index=d.index)
    g = (d.O - pc) / atr; f["GAP"] = tri(g, g < -0.3, g > 0.3, BK["GAP"])
    w = d.orr / d.orr.shift(1).rolling(20, min_periods=10).median(); f["ORW"] = tri(w, w < 0.7, w > 1.4, BK["ORW"])
    m20 = pc.rolling(20).mean(); f["TREND"] = pd.Series(np.where(m20.isna() | pc.isna(), None, np.where(pc > m20, "UP", "DN")), index=d.index, dtype=object)
    m = (pc - d.C.shift(6)) / atr; f["MOM5"] = tri(m, m < -1, m > 1, BK["MOM5"])
    h20, l20 = d.H.shift(1).rolling(20).max(), d.L.shift(1).rolling(20).min(); x = (pc - l20) / (h20 - l20)
    f["LOC20"] = tri(x, x <= 0.2, x >= 0.8, BK["LOC20"])
    pr = (d.H.shift(1) - d.L.shift(1)) / atr; f["PRNG"] = tri(pr, pr < 0.7, pr > 1.3, BK["PRNG"])
    r = pc / d.H.shift(1).rolling(250).max(); f["EXT52"] = tri(r, r <= 0.90, r >= 0.97, BK["EXT52"])
    f["r52"] = r; f["ATH"] = pc >= 0.99 * d.H.cummax().shift(1); f["PDH"], f["PDL"] = d.H.shift(1), d.L.shift(1)
    return f


def daily():
    """{(sym, day): 375 closes (ffilled)} and per-sym daily O/H/L/C/orr from idx1m minutes 555..929 (days with < 300 bars dropped: special
    sessions); panel days after the last idx1m day come from P spot (O = spot[0])."""
    fp = f"{E21}/idx_daily.pkl"
    if os.path.exists(fp): SP, rows, last = pickle.load(open(fp, "rb"))
    else:
        D = pd.read_pickle(IDX); D = D[(D.m >= M0) & (D.m < M0 + NB)].drop_duplicates(["sym", "day", "m"], keep="last"); SP, rows = {}, []
        for (sym, day), g in D.groupby(["sym", "day"], sort=False):
            if len(g) < 300: continue
            g = g.sort_values("m"); a = np.full(NB, np.nan); a[g.m.values - M0] = g.close.values; a = pd.Series(a).ffill().bfill().values
            SP[(sym, day)] = a; rows.append((sym, day, g.open.iloc[0], g.high.max(), g.low.min(), g.close.iloc[-1], np.ptp(a[:31])))
        last = D.day.max(); pickle.dump((SP, rows, last), open(fp, "wb"))
    rows = list(rows) + [(k[0], k[1], s[0], np.nanmax(s), np.nanmin(s), s[-1], np.ptp(s[:31])) for k in L.ALLK if k[1] > last
                         for s in [P[k]["spot"]]]
    R = pd.DataFrame(rows, columns=["sym", "day", "O", "H", "L", "C", "orr"]); return SP, {s: g.set_index("day").sort_index() for s, g in R.groupby("sym")}


_LAB = {}
def labs():
    """LABA: (sym, day) of the panel; LABB: Tier B index days < 2025-10-27; SP: idx closes."""
    if _LAB: return _LAB["A"], _LAB["B"], _LAB["SP"]
    SP, DT = daily(); F = pd.concat({s: dfeat(d) for s, d in DT.items()}, names=["sym", "day"])
    A = F.reindex(pd.MultiIndex.from_tuples(L.ALLK, names=["sym", "day"])).copy()
    iv = L.vol_days().set_index(["sym", "day"]).ivpct.reindex(A.index)
    A["IVR"] = tri(iv, iv < 0.33, iv > 0.67, BK["IVR"]).values
    A["DTE"] = [str(min(P[k]["dte"], 2)) if min(P[k]["dte"], 2) < 2 else "2+" for k in A.index]
    B = F[[(s, d) in SP and d < B_END for s, d in F.index]]
    _LAB.update(A=A, B=B, SP=SP); return A, B, SP


def codes(col, v):
    m = {n: i for i, n in enumerate(BK[v])}; return np.array([m.get(x, -1) if isinstance(x, str) else -1 for x in col], dtype=np.int8)


def SLd(split):
    """day-level label codes of the Tier A split: v -> (2 syms, ndays), -1 = no label."""
    A = labs()[0]; days = DAYS_A[split]; out = {}
    for v in DAYA + ["EXT52"]:
        out[v] = np.stack([codes(A[v].reindex(pd.MultiIndex.from_product([[sym], days])).values, v) for sym in ("NIFTY", "SENSEX")])
    return out


# ---------------------------------------------------------------- Tier A trades (struct once per (strategy, split); cons + opt)
_SG = {}
def sigsA(st, split):
    """[(key, i, side, TOD, TWS)] for the split (signals only, no P&L)."""
    if (st, split) in _SG: return _SG[st, split]
    keys = KA[split]; A = labs()[0]
    if st in ("S1", "LS"): out = [(k, 31, None, None, None) for k in keys]
    elif st == "E13": out = [(r.key, int(r.j), None, tod(int(r.j)), None) for r in S.e13_signals(keys).itertuples()]
    else:
        out = []
        for k in keys:
            s = P[k]["spot"]; pdh, pdl = A.PDH[k], A.PDL[k]
            out += [(k, i, sd, tod(i), tws(s, i, sd)) for i, sd in sg(st, s, STEP[k[0]], pdh, pdl)]
    _SG[st, split] = out; return out


def _tr(k, i, legs, ex):
    c = S.struct(k, i, legs, mode="cons", **ex)
    if not c: return None
    o = S.struct(k, i, legs, mode="opt", **ex); return dict(c, key=k, opt=o["pnl"] if o else np.nan)


def tradesA(st, split):
    fp = f"{E21}/trA_{st}_{split}_{_SRC}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    t0 = time.time(); R = []
    for k, i, sd, td, tw in sigsA(st, split):
        if st in DIR: r = _tr(k, i, [(sd, 0, 1)], X(i, SIGN(sd)))
        else: r = _tr(k, i, S.LSTRAD if st == "LS" else S.SSTRAD, dict(sstop=2, **(dict(stop=0.3) if st == "E13" else {})))
        if r: R.append(dict(r, side=sd, TOD=td, TWS=tw))
    T = pd.DataFrame(R); T.to_pickle(fp); print(f"  trades A {st} {split}: {len(T)} ({time.time() - t0:.0f}s)", flush=True); return T


def randA(split):
    """directional random control: 12 entries per sym-day, bar U[31..285], side U, exit X, seed 3 -> {key: (pnl, why)}."""
    fp = f"{E21}/randA_{split}_{_SRC}.pkl"
    if os.path.exists(fp): return pickle.load(open(fp, "rb"))
    rg = np.random.default_rng(3); out = {}
    for k in KA[split]:
        v, w = [], []
        for i, sd in zip(rg.integers(31, 286, 12), rg.integers(0, 2, 12)):
            sd = "CE" if sd == 0 else "PE"; r = S.struct(k, int(i), [(sd, 0, 1)], mode="cons", **X(int(i), SIGN(sd)))
            if r: v.append(r["pnl"]); w.append(r["why"])
        out[k] = (np.array(v), np.array(w))
    pickle.dump(out, open(fp, "wb")); print(f"  random control A {split} done", flush=True); return out


# ---------------------------------------------------------------- statistics (arrays; same definitions as S.summ)
def mkQ(T, days, sl=None, rand=None):
    """arrays for one strategy's trades. sl: day-label codes of the split (v -> (2, nd))."""
    dix = {d: i for i, d in enumerate(days)}; mos = sorted({L.month(d) for d in days}); mix = {m: i for i, m in enumerate(mos)}
    Q = dict(T=T, n=len(T), nd=len(days), nm=len(mos), pnl=T.pnl.values.astype(float), di=T.day.map(dix).values.astype(int),
             si=(T.sym == "SENSEX").values.astype(int), forced=T.forced.values.astype(float), moi=T.day.map(lambda d: mix[L.month(d)]).values.astype(int),
             opt=T.opt.values.astype(float) if "opt" in T else np.full(len(T), np.nan), lab={})
    if sl is not None:
        for v, a in sl.items(): Q["lab"][v] = a[Q["si"], Q["di"]]
        for v in ("TOD", "TWS"): Q["lab"][v] = codes(T[v].values, v)
    if rand is not None: Q["pool"] = [rand[k][0] for k in T.key]
    return Q


def stat(Q, ix):
    pn, di = Q["pnl"][ix], Q["di"][ix]; sm = np.bincount(di, pn, Q["nd"]); g = sm[np.bincount(di, minlength=Q["nd"]) > 0]
    mi = Q["moi"][ix]; ms, mc = np.bincount(mi, pn, Q["nm"]), np.bincount(mi, minlength=Q["nm"]); sy = Q["si"][ix]
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    return dict(n=len(ix), n_days=len(g), mean=pn.mean(), total=pn.sum(), t=t, nm=int((mc > 0).sum()), mp=int((ms[mc > 0] > 0).sum()),
                forced=Q["forced"][ix].mean() * 100, NIFTY=pn[sy == 0].sum(), SENSEX=pn[sy == 1].sum(), g=g)


def pboot(g): return round((np.random.default_rng(5).choice(g, (5000, len(g))).mean(1) <= 0).mean(), 4)


def pdiff(Q, ix, io):
    """day-cluster bootstrap (5000, seed 5) of mean(cell) - mean(other buckets), one-sided P(diff <= 0); undefined draws count against."""
    if not len(io): return np.nan
    nd = Q["nd"]; f = lambda a: (np.bincount(Q["di"][a], Q["pnl"][a], nd), np.bincount(Q["di"][a], minlength=nd))
    (sc, nc), (so, no) = f(ix), f(io); u = (nc + no) > 0; sc, nc, so, no = sc[u], nc[u], so[u], no[u]
    j = np.random.default_rng(5).integers(0, len(sc), (5000, len(sc)))
    d = sc[j].sum(1) / nc[j].sum(1) - so[j].sum(1) / no[j].sum(1)
    return round((~(d > 0)).mean(), 4)


def pvr(Q, ix):
    """P(random-control sum >= cell total): one random draw per trade from its own sym-day's pool, 2000 draws, seed 9."""
    rg = np.random.default_rng(9); rnd = np.zeros(2000)
    for a in (Q["pool"][i] for i in ix):
        if len(a): rnd += a[rg.integers(0, len(a), 2000)]
    return round((rnd >= Q["pnl"][ix].sum()).mean(), 4)


def evalcell(Q, ix, io, full, dirn):
    if not full and len(ix) < 20: return None
    r = stat(Q, ix); g = r.pop("g"); r["elig"] = bool(r["n"] >= 20 and r["n_days"] >= 15)
    r["diff"] = r["mean"] - Q["pnl"][io].mean() if len(io) else np.nan
    ok = r["elig"] and r["mean"] > 0 and r["nm"] >= 4 and r["mp"] >= 0.6 * r["nm"] and r["forced"] <= 10 and r["diff"] > 0
    r.update(p_boot=np.nan, p_diff=np.nan, p_vs_rand=np.nan, opt_mean=np.nan, mpos=f"{r['mp']}/{r['nm']}")
    if full or ok: r["p_boot"] = pboot(g); ok = ok and r["p_boot"] < 0.05
    if (full and r["elig"]) or ok: r["p_diff"] = pdiff(Q, ix, io); ok = ok and r["p_diff"] < 0.10
    if dirn and ((full and r["elig"]) or ok): r["p_vs_rand"] = pvr(Q, ix); ok = ok and r["p_vs_rand"] < 0.10
    if full and np.isfinite(Q["opt"][ix]).any(): r["opt_mean"] = np.nanmean(Q["opt"][ix])
    r["pass"] = bool(ok); return r


def screen(PS, lab, desc, full):
    out = []
    for st, Q in PS.items():
        if not Q["n"]: continue
        for v in vars_for(st, DAYA):
            c = lab[st][v]
            for b, nm in enumerate(BK[v]):
                ds = (st, v, nm) in desc or (v, nm) in desc
                if ds and not full: continue
                ix = np.nonzero(c == b)[0]
                if not len(ix): continue
                r = evalcell(Q, ix, np.nonzero((c >= 0) & (c != b))[0], full, st in DIR)
                if r is None: continue
                if ds: r["pass"] = False
                out.append(dict(strategy=st, var=v, bucket=nm, desc=ds, **r))
    return out


def null_labels(PS, SL, u):
    """each variable's dev day-label sequence circularly shifted by u (same u, both syms); trade-level labels (TOD/TWS) shifted along the
    strategy's trade list per sym by u mod n."""
    lab = {}
    for st, Q in PS.items():
        lab[st] = {}
        if not Q["n"]: continue
        for v in vars_for(st, DAYA):
            if v in DAYA: lab[st][v] = np.roll(SL[v], u, axis=1)[Q["si"], Q["di"]]
            else:
                c = Q["lab"][v].copy()
                for s in (0, 1):
                    ix = np.nonzero(Q["si"] == s)[0]
                    if len(ix): c[ix] = np.roll(Q["lab"][v][ix], u % len(ix))
                lab[st][v] = c
    return lab


def desc_set(SLs):
    """Tier A buckets with < 15 distinct days in DEV or TEST -> DESCRIPTIVE; same rule for strategy-level TOD/TWS buckets (signal days)."""
    d = set()
    for v in DAYA:
        for b, nm in enumerate(BK[v]):
            if min(int((SLs[s][v] == b).any(0).sum()) for s in ("dev", "test")) < 15: d.add((v, nm))
    for st in STR:
        for v in ("TOD", "TWS"):
            if v not in vars_for(st, []): continue
            idx = 3 if v == "TOD" else 4
            for nm in BK[v]:
                if min(len({x[0][1] for x in sigsA(st, s) if x[idx] == nm}) for s in ("dev", "test")) < 15: d.add((st, v, nm))
    return d


def PSA(split, rand):
    sl = SLd(split)
    return {st: mkQ(tradesA(st, split), DAYS_A[split], sl, rand) for st in STR}, sl


CSV = ["strategy", "var", "bucket", "n", "n_days", "mean", "total", "p_boot", "mpos", "diff", "p_diff", "p_vs_rand", "forced", "opt_mean",
       "NIFTY", "SENSEX", "t", "elig", "desc", "pass"]


def show(rows, cols=CSV):
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    R = pd.DataFrame(rows)[cols]; print(R.round(3).to_string(index=False)); return R


# ---------------------------------------------------------------- studies
def study_step0():
    """data sufficiency: distinct dates (sym-days) per bucket x split x tier; printed before any P&L."""
    A, B, SP = labs(); SLs = {s: SLd(s) for s in DAYS_A}
    print("STEP 0: distinct dates (sym-days) per bucket. Tier A: DEV 148 d / TEST 98 d (panel). Tier B: DEV < 2024-02-23 / TEST to 2025-10-24 (idx1m)")
    ds = desc_set(SLs); bd = {"dev": B.index.get_level_values("day") < B_CUT, "test": B.index.get_level_values("day") >= B_CUT}
    for v in DAYA + ["EXT52"]:
        for b, nm in enumerate(BK[v]):
            a = [f"{int((SLs[s][v] == b).any(0).sum())} ({int((SLs[s][v] == b).sum())})" for s in ("dev", "test")]
            bb = [f"{B[v][bd[s]].eq(nm).groupby('day').any().sum() if v in DAYB else '-'} ({int(B[v][bd[s]].eq(nm).sum()) if v in DAYB else '-'})" for s in ("dev", "test")]
            print(f"  {v:6s} {nm:7s} A dev {a[0]:>9s} test {a[1]:>9s} | B dev {bb[0]:>11s} test {bb[1]:>11s}" + ("   DESCRIPTIVE (A)" if (v, nm) in ds or v == "EXT52" else ""))
    for s in ("dev", "test"):
        ix = A.index.get_level_values("day").isin(DAYS_A[s]); a = A[ix]
        print(f"  Tier A {s}: sym-days {len(a)}; C_t-1 within 1% of 52w high {int((a.r52 >= 0.99).sum())}, within 3% {int((a.r52 >= 0.97).sum())}, "
              f"ATH flag {int(a.ATH.sum())}; r52 defined {int(a.r52.notna().sum())}")
    for s, m in bd.items():
        b = B[m]; print(f"  Tier B {s}: sym-days {len(b)}; within 1% {int((b.r52 >= 0.99).sum())}, within 3% {int((b.r52 >= 0.97).sum())}, ATH flag {int(b.ATH.sum())}")
    print("  signal days per strategy x TOD/TWS bucket (A dev | A test); DESCRIPTIVE if < 15 in either:")
    for st in STR:
        for v in ("TOD", "TWS"):
            if v in vars_for(st, []):
                print(f"    {st:5s} {v}: " + ", ".join(f"{nm} {len({x[0][1] for x in sigsA(st, 'dev') if x[3 if v == 'TOD' else 4] == nm})}|"
                      f"{len({x[0][1] for x in sigsA(st, 'test') if x[3 if v == 'TOD' else 4] == nm})}" + ("*" if (st, v, nm) in ds else "") for nm in BK[v]))
    print("  descriptive-only Tier A buckets:", sorted(map(str, ds)))


def study_devA():
    t0 = time.time(); rand = randA("dev"); PS, SL = PSA("dev", rand); SLs = {s: SLd(s) for s in DAYS_A}; desc = desc_set(SLs)
    print("DESCRIPTIVE buckets (excluded from selection):", sorted(map(str, desc)))
    print("UNCONDITIONAL DEV rows (cons; opt avg):")
    for st, Q in PS.items():
        if Q["n"]: print(f"  {st:5s}", S.summ(Q["T"]), "opt_avg", round(np.nanmean(Q["opt"])), flush=True)
    real = {st: Q["lab"] for st, Q in PS.items()}; rows = screen(PS, real, desc, True); R = show(rows)
    R.to_csv(f"{E21}/e21_cells_A_dev.csv", index=False)
    for r in rows:  # cross-check the array stats against S.summ on every passing cell
        if r["pass"]:
            Q = PS[r["strategy"]]; m = (Q["lab"][r["var"]] == BK[r["var"]].index(r["bucket"])); sm = S.summ(Q["T"][m])
            assert sm["p_boot"] == r["p_boot"] and sm["mpos"] == r["mpos"] and sm["n"] == r["n"], (sm, r)
    npass = sum(r["pass"] for r in rows); print(f"\nREAL screen passes: {npass} of {sum(r['elig'] and not r['desc'] for r in rows)} eligible cells ({len(rows)} cells)  [{time.time() - t0:.0f}s]", flush=True)
    rg = np.random.default_rng(5); null = []
    for n in range(200):
        u = int(rg.integers(20, 129)); null.append(sum(r["pass"] for r in screen(PS, null_labels(PS, SL, u), desc, False)))
        if n % 20 == 19: print(f"  null run {n + 1}/200  [{time.time() - t0:.0f}s]", flush=True)
    null = np.array(null); q = np.percentile(null, [50, 90, 95, 99])
    print(f"NULL passes: mean {null.mean():.2f} p50 {q[0]:.0f} p90 {q[1]:.0f} p95 {q[2]:.0f} p99 {q[3]:.0f} max {null.max()}; real {npass}; "
          f"share of null runs >= real {(null >= npass).mean():.3f}" + ("  -> SCREEN = LUCK" if npass <= q[2] else ""))
    ps = sorted([r for r in rows if r["pass"]], key=lambda r: -r["t"])[:5]; K = len(ps)
    print(f"SELECTED K={K}:"); [print("  ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}) for r in ps]
    json.dump(dict(K=K, passes=int(npass), null_p95=float(q[2]), null=null.tolist(), luck=bool(npass <= q[2]),
                   cells=[{k: (float(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v))
                           for k, v in r.items() if k in ("strategy", "var", "bucket", "n", "n_days", "mean", "t", "diff", "p_boot", "p_diff", "p_vs_rand")} for r in ps]),
              open(f"{E21}/selected_A.json", "w"), indent=1)
    print(f"devA done [{time.time() - t0:.0f}s]")


# ---------------------------------------------------------------- Tier B (index only; outcome in steps)
def race(s, i, sd, stp):
    """from s0 = close[i+1]: +2 steps target, -1 stop, else signed steps at the 60-minute cap (close of the last held bar)."""
    e = i + 1; xe = min(L.FLAT - M0, i + 61)
    if e >= xe or not np.isfinite(s[e]): return None
    s0, d = s[e], SIGN(sd)
    for j in range(e, xe):
        mv = d * (s[j] - s0) / stp
        if mv >= 2: return 2.0, "t"
        if mv <= -1: return -1.0, "s"
    return d * (s[xe - 1] - s0) / stp, "c"


BD = {"dev": lambda d: d < B_CUT, "test": lambda d: B_CUT <= d < B_END}


def tradesB(st, split):
    fp = f"{E21}/trB_{st}_{split}_{_SRC}.pkl"
    if os.path.exists(fp): return pd.read_pickle(fp)
    B, SP = labs()[1:]; R = []
    for (sym, day), r in B.iterrows():
        if not BD[split](day): continue
        s = SP[sym, day]; stp = STEPB[sym]
        for i, sd in sg(st, s, stp, r.PDH, r.PDL):
            x = race(s, i, sd, stp)
            if x: R.append(dict(sym=sym, day=day, i=i, side=sd, y=x[0], kind=x[1], TOD=tod(i), TWS=tws(s, i, sd), **{v: r[v] for v in DAYB}))
    T = pd.DataFrame(R); T.to_pickle(fp); print(f"  trades B {st} {split}: {len(T)}", flush=True); return T


def randB(split):
    fp = f"{E21}/randB_{split}_{_SRC}.pkl"
    if os.path.exists(fp): return pickle.load(open(fp, "rb"))
    B, SP = labs()[1:]; rg = np.random.default_rng(3); out = {}
    for (sym, day) in B.index:
        if not BD[split](day): continue
        v = []
        for i, sd in zip(rg.integers(31, 286, 12), rg.integers(0, 2, 12)):
            x = race(SP[sym, day], int(i), "CE" if sd == 0 else "PE", STEPB[sym])
            if x: v.append(x[0])
        out[sym, day] = np.array(v)
    pickle.dump(out, open(fp, "wb")); return out


def pstar():
    """breakeven target-hit share per sym from Tier A DEV random entries: |mean pnl on stop| / (mean on target + |mean on stop|)."""
    R = randA("dev"); out = {}
    for sym in ("NIFTY", "SENSEX"):
        v = np.concatenate([R[k][0] for k in R if k[0] == sym]); w = np.concatenate([R[k][1] for k in R if k[0] == sym])
        a, b = v[w == "s_tgt"].mean(), abs(v[w == "s_stp"].mean()); out[sym] = b / (a + b)
    out["BANKNIFTY"] = (out["NIFTY"] + out["SENSEX"]) / 2; return out


def cellB(T, rp, ps, alpha=None):
    """T: one cell's trades (y, kind, sym, day). Paired day-cluster bootstrap of y - mean(random pool of the same sym-day)."""
    d = np.array([y - rp[s, k].mean() if len(rp.get((s, k), [])) else np.nan for s, k, y in zip(T.sym, T.day, T.y)])
    ok = np.isfinite(d); g = pd.Series(d[ok]).groupby(T.day.values[ok]).sum().values; nt, ns = (T.kind == "t").sum(), (T.kind == "s").sum()
    pst = float(np.mean([ps[s] for s in T.sym])); hit = nt / max(nt + ns, 1)
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    p = round((np.random.default_rng(5).choice(g, (5000, len(g))).mean(1) <= 0).mean(), 4) if len(g) else np.nan
    return dict(n=len(T), n_days=T.day.nunique(), mean=T.y.mean(), total=T.y.sum(), hit=hit, pstar=pst, p_boot=p, t=t, diff=d[ok].mean() if ok.any() else np.nan,
                cap=(T.kind == "c").mean())


def study_devB():
    t0 = time.time(); ps = pstar(); print("p* (breakeven target-hit share) from Tier A DEV random entries:", {k: round(v, 4) for k, v in ps.items()})
    rp = randB("dev"); rows = []
    for st in BSTR:
        T = tradesB(st, "dev")
        if not len(T): print(" ", st, "no trades"); continue
        r = cellB(T, rp, ps); rows.append(dict(strategy=st, var="ALL", bucket="ALL", **r, **{"elig": True, "pass": False}))
        for v in vars_for(st, DAYB):
            for nm in BK[v]:
                C = T[T[v] == nm]
                if not len(C): continue
                r = cellB(C, rp, ps); el = r["n_days"] >= 30
                rows.append(dict(strategy=st, var=v, bucket=nm, **r, elig=bool(el), **{"pass": bool(el and r["hit"] > r["pstar"] and r["p_boot"] < 0.05 and r["diff"] > 0)}))
    pd.set_option("display.width", 250); R = pd.DataFrame(rows); print(R.round(3).to_string(index=False)); R.to_csv(f"{E21}/e21_cells_B_dev.csv", index=False)
    ok = R[R["pass"]].sort_values("t", ascending=False).head(5); K = len(ok)
    print(f"Tier B DEV passes: {int(R['pass'].sum())}; SELECTED K={K}"); print(ok.round(3).to_string(index=False))
    json.dump(dict(K=K, passes=int(R["pass"].sum()), pstar=ps, cells=[dict(strategy=r.strategy, var=r.var, bucket=r.bucket, t=float(r.t), hit=float(r.hit), p_boot=float(r.p_boot))
                                                                    for r in ok.itertuples()]), open(f"{E21}/selected_B.json", "w"), indent=1)
    print(f"devB done [{time.time() - t0:.0f}s]")


# ---------------------------------------------------------------- TEST (run once; --test required)
def _need_test():
    if "--test" not in sys.argv: sys.exit("TEST studies need --test (run once, after review)")


MIN_TEST_DAYS = 15
FOUND_A = [("FIB", "LOC20", "HIGH"), ("FIB", "LOC20", "LOW")]


def cellA_test(PS, st, v, nm, alpha):
    Q = PS[st]; c = Q["lab"][v]; b = BK[v].index(nm); ix = np.nonzero(c == b)[0]; io = np.nonzero((c >= 0) & (c != b))[0]
    if not len(ix): return dict(strategy=st, var=v, bucket=nm, n=0, alpha=alpha, **{"pass": False})
    r = evalcell(Q, ix, io, True, st in DIR); g = stat(Q, ix)["g"]; d = Q["T"].day.values[ix]; p = Q["pnl"][ix]
    t1, t2 = p[d <= T1_END], p[d > T1_END]; r.update(strategy=st, var=v, bucket=nm, alpha=alpha, T1_n=len(t1), T1_mean=t1.mean() if len(t1) else np.nan,
                                                   T2_n=len(t2), T2_mean=t2.mean() if len(t2) else np.nan,
                                                   mde=2.33 * g.std(ddof=1) * np.sqrt(len(g)) / len(ix) if len(g) > 2 else np.nan)
    r["pass"] = bool(r["mean"] > 0 and r["p_boot"] < alpha and r["diff"] > 0 and (st not in T2S or t2.mean() > 0))
    if r["n_days"] < MIN_TEST_DAYS: r["pass"] = False; r["untestable"] = True  # amendment A2: tiny cells pass trivially
    return r


def study_testA():
    _need_test(); sel = json.load(open(f"{E21}/selected_A.json")); K = sel["K"]; cells = [(c["strategy"], c["var"], c["bucket"], 0.05 / K) for c in sel["cells"]]
    cells += [(*f, 0.025) for f in FOUND_A]; sts = {c[0] for c in cells}; rand = randA("test"); sl = SLd("test")
    PS = {st: mkQ(tradesA(st, "test"), DAYS_A["test"], sl, rand) for st in sts}
    rows = [cellA_test(PS, *c) for c in cells]
    cols = CSV + ["alpha", "T1_n", "T1_mean", "T2_n", "T2_mean", "mde", "untestable"]; R = pd.DataFrame(rows); R = R.reindex(columns=cols); pd.set_option("display.width", 300)
    print(R.round(3).to_string(index=False)); R.to_csv(f"{E21}/e21_cells_A_test.csv", index=False)


def study_testB():
    _need_test(); sel = json.load(open(f"{E21}/selected_B.json")); K = sel["K"]; ps = sel["pstar"]
    cells = [(c["strategy"], c["var"], c["bucket"], 0.05 / max(K, 1)) for c in sel["cells"]] + [("FIB", "EXT52", "TOP", 0.05)]
    rp = randB("test"); rows = []; ra = randA("test"); PA = {}
    sl = SLd("test")
    for st, v, nm, al in cells:
        T = tradesB(st, "test"); C = T[T[v] == nm] if len(T) else T
        if not len(C): rows.append(dict(strategy=st, var=v, bucket=nm, n=0, alpha=al, **{"pass": False})); continue
        r = cellB(C, rp, ps); r.update(strategy=st, var=v, bucket=nm, alpha=al); r["pass"] = bool(r["hit"] > r["pstar"] and r["p_boot"] < al and r["diff"] > 0)
        if r["pass"]:  # survivors: confirm on Tier A TEST at 0.05/K
            if st not in PA: PA[st] = mkQ(tradesA(st, "test"), DAYS_A["test"], sl, ra)
            a = cellA_test(PA, st, v, nm, 0.05 / max(K, 1)); r.update(A_n=a["n"], A_mean=a.get("mean"), A_p_boot=a.get("p_boot"), confirmed=bool(a["pass"]))
        rows.append(r)
    pd.set_option("display.width", 300); R = pd.DataFrame(rows); print(R.round(3).to_string(index=False)); R.to_csv(f"{E21}/e21_cells_B_test.csv", index=False)


# ---------------------------------------------------------------- selftest (synthetic; checks use only data up to t-1 / bar i)
def study_selftest():
    rg = np.random.default_rng(1)
    def nolook(f, s, r, *a):
        """same result on the series truncated at the signal bar, and with noise after it (no look-ahead)."""
        i = r[0][0]; assert f(s[:i + 1], *a) == r, ("truncated", f(s[:i + 1], *a), r)
        z = s.copy(); z[i + 1:] += rg.normal(0, 500, len(z) - i - 1); assert f(z, *a) == r, ("noisy future", f(z, *a), r)
    kn = lambda *p: np.interp(np.arange(375), *zip(*p))
    # FIB up: rise 20000 -> 20400 (bar 40), pullback to 20120 (bar 70; inside 61.8-78.6% of 400), recover; trigger = first close above the 50% line 20200
    s = kn((0, 20000), (40, 20400), (70, 20120), (90, 20300), (374, 20300)); i = next(i for i in range(61, 286) if s[i - 1] <= 20200 < s[i])
    r = fib(s, 50); assert r == [(i, "CE")] and 61 <= i, (r, i); nolook(fib, s, r, 50)
    m = 40000 - s; r2 = fib(m, 50); assert r2 == [(i, "PE")], r2; nolook(fib, m, r2, 50)  # FIB down = mirror
    assert fib(kn((0, 20000), (40, 20400), (70, 20050), (90, 20300), (374, 20300)), 50) == []  # retrace 87.5% > 78.6%: no setup
    assert fib(kn((0, 20000), (40, 20100), (70, 20010), (90, 20060), (374, 20060)), 50) == []  # swing 100 < 3 steps
    # PDB / PDR
    base = np.full(375, 20000.0); a = base.copy(); a[50:] = 20060; r = pdb(a, 20050, 19950); assert r == [(50, "CE")], r; nolook(pdb, a, r, 20050, 19950)
    b = base.copy(); b[50:] = 19940; r = pdb(b, 20050, 19950); assert r == [(50, "PE")], r; nolook(pdb, b, r, 20050, 19950)
    c = base.copy(); c[30:] = 20060; c[40:50] = 20040; assert pdb(c, 20050, 19950) == []  # already beyond at 09:45: side skipped
    d = a.copy(); d[60:] = 20040; r = pdr(d, 20050, 19950); assert r == [(60, "PE")], r; nolook(pdr, d, r, 20050, 19950)
    d = a.copy(); d[65:] = 20040; assert pdr(d, 20050, 19950) == [(65, "PE")]
    d = a.copy(); d[66:] = 20040; assert pdr(d, 20050, 19950) == []  # back inside after 15 bars: no PDR
    e = b.copy(); e[58:] = 19960; r = pdr(e, 20050, 19950); assert r == [(58, "CE")], r
    # TWAP: jump at bar 50 -> d = 2.9 steps; fade it; a jump before bar 46 that persists never re-crosses
    t = base.copy(); t[50:] = 20150; r = twap(t, 50); assert r == [(50, "PE")], r; nolook(twap, t, r, 50)
    t = base.copy(); t[50:] = 19850; r = twap(t, 50); assert r == [(50, "CE")], r; nolook(twap, t, r, 50)
    t = base.copy(); t[40:] = 20150; assert twap(t, 50) == []
    # MOM, race, TOD/TWS labels
    m = base.copy(); m[75] = 20010; assert mom(m) == [(75, "CE")] and mom(base) == [] and mom(40000 - m + 0) == [(75, "PE")]
    r = 20000 + 5.0 * np.arange(375); assert race(r, 100, "CE", 50)[1] == "t" and race(r, 100, "PE", 50) == (-1.0, "s")
    assert race(base, 100, "CE", 50) == (0.0, "c") and race(base, 300, "CE", 50)[1] == "c" and tod(31) == "EARLY" and tod(105) == "MID" and tod(285) == "LATE"
    assert tws(a, 60, "CE") == "WITH" and tws(a, 60, "PE") == "AGAINST"
    # scenario labels: C_t = 100 + t, H = C + 1, L = C - 1, O_30 = C_29 + 1 -> ATR 2, gap 0.5 (UP), x = (129 - 109) / (130 - 109) = 0.95 (HIGH)
    n = 40; C = 100.0 + np.arange(n); df = pd.DataFrame(dict(O=C - 1, H=C + 1, L=C - 1, C=C, orr=np.full(n, 10.0)), index=[f"d{j:02d}" for j in range(n)])
    df.loc["d30", "O"] = C[29] + 1; f = dfeat(df); assert f.GAP["d30"] == "UP" and f.LOC20["d30"] == "HIGH" and f.TREND["d30"] == "UP", f.loc["d30"]
    assert f.PDH["d30"] == C[29] + 1 and f.PDL["d30"] == C[29] - 1 and f.ORW["d30"] == "NORMAL"
    g = df.copy(); g.loc["d30", ["H", "L", "C"]] = [500, -500, 400]; f2 = dfeat(g)  # day t's own H/L/C must not move day t's labels
    assert all(f2[c]["d30"] == f[c]["d30"] for c in ("GAP", "LOC20", "TREND", "MOM5", "PRNG", "EXT52", "ORW")), f2.loc["d30"]
    assert f2.GAP["d31"] != f.GAP["d31"] or f2.LOC20["d31"] != f.LOC20["d31"]  # but it does move the next day's labels
    g = df.copy(); g.loc["d30", "orr"] = 100.0; assert dfeat(g).ORW["d30"] == "WIDE" and dfeat(g).ORW["d29"] == f.ORW["d29"]
    # stat / pboot / pdiff against S.summ on a synthetic trade table
    days = [d for d in ALLD[:148]]; rs = np.random.default_rng(2); T = pd.DataFrame([dict(sym=s, day=d, pnl=float(rs.normal(300, 5000)), forced=bool(rs.random() < .05),
            maxloss=np.nan, key=(s, d)) for d in days[::2] for s in ("NIFTY", "SENSEX")]); T["opt"] = T.pnl
    Q = mkQ(T, days); ix = np.arange(len(T)); sm = S.summ(T); st_ = stat(Q, ix)
    assert sm["p_boot"] == pboot(st_["g"]) and sm["mpos"] == f"{st_['mp']}/{st_['nm']}" and abs(sm["t"] - st_["t"]) < 0.006 and sm["n"] == st_["n"]
    assert abs(pdiff(Q, ix[:60], ix[60:]) - pdiff(Q, ix[:60], ix[60:])) == 0 and 0 <= pdiff(Q, ix[:60], ix[60:]) <= 1
    print("scen_lab selftest OK")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
