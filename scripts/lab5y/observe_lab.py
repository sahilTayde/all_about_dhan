"""Observation lab (registry E55+): what moves NIFTY / SENSEX option premiums. Observe first (no rule), then rules (E56+).
Paper research only; no orders, no broker calls; reads the 5-year 1m panel, the tick cache and the cross-market tape.
Run (from scripts/lab5y; OUT = the panel folder, as scalp_lab):
  HO=2025-10-27 LAB_FULL=1 COSTS=dated ~/paper_extra_venv/bin/python observe_lab.py <OUT> table o1 o3 o4 o5 o6 o7     # panel (LEARN only)
  TAPEC=<data/cache/tapetick> CROSS=<data/tape/cross> ~/paper_extra_venv/bin/python observe_lab.py <OUT> t1 t2 t3 t4 t5 x1   # ticks / cross tape
  ~/paper_extra_venv/bin/python observe_lab.py - selftest
Reuses scalp_lab (panel, day_feats, gather / price45 / price52_short, costs), tapelib (tick grids, fills), honest_stats. Every E55
number is LEARN (panel) or OBSERVE days (tape); TEST / HOLDOUT are read only by the frozen rule studies (e56...)."""
import sys, os, json, datetime as dt, numpy as np, pandas as pd
from scipy.special import ndtr

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
OBS = os.path.join(OUT, "observe")
DEPTHS = np.arange(-4, 5)            # strikes in the money (m > 0 ITM, m < 0 OTM)
HZ = (1, 5, 15)
T_OBS = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22"]
T_HOLD = ["2026-10-28", "2026-10-29", "2026-11-13"]
X_OBS = ["2026-10-13", "2026-10-21", "2026-10-22"]; X_HOLD = T_HOLD
_SL = []


def SL():
    """scalp_lab (loads the 5-year panel through opt1y_lab) on first use, so the tick studies and the selftest never load it."""
    if not _SL:
        import scalp_lab; _SL.append(scalp_lab)
    return _SL[0]


# ---------------------------------------------------------------- Black-76 on the synthetic future (no discounting)
def b76(F, K, T, v, call):
    """price and d1. F, K, T, v broadcast; call bool."""
    sq = v * np.sqrt(T)
    with np.errstate(all="ignore"):
        d1 = (np.log(F / K) + 0.5 * sq * sq) / sq; c = F * ndtr(d1) - K * ndtr(d1 - sq)
    return np.where(call, c, c - F + K), d1


def iv76(p, F, K, T, call, it=40):
    """vectorised bisection on [0.005, 5]; NaN where the price is not above intrinsic or the root is not reached."""
    p = np.asarray(p, float); shape = np.broadcast(p, F, K, T).shape; lo = np.full(shape, 0.005); hi = np.full(shape, 5.0)
    for _ in range(it):
        mid = 0.5 * (lo + hi); up = b76(F, K, T, mid, call)[0] < p; lo = np.where(up, mid, lo); hi = np.where(up, hi, mid)
    v = 0.5 * (lo + hi); intr = np.maximum(np.where(call, F - K, K - F), 0)
    with np.errstate(invalid="ignore"): bad = ~np.isfinite(p) | (p <= intr + 1e-9) | (np.abs(b76(F, K, T, v, call)[0] - p) > 0.02 + 0.002 * p)
    return np.where(bad, np.nan, v)


def _sh(X, h):
    """X[..., i] -> X[..., i + h] (NaN beyond the day); h < 0 looks back."""
    Y = np.full(X.shape, np.nan); n = X.shape[-1]
    if h > 0: Y[..., :n - h] = X[..., h:]
    elif h < 0: Y[..., -h:] = X[..., :n + h]
    else: Y[...] = X
    return Y


def decompose(F, K, T, sigK, sigA, price, call, h):
    """the frozen E55 split of a fixed-strike premium change over h bars. Arrays (nK, NB) (F, T, sigA: (NB,)).
    Returns dP, spot (delta dF + 0.5 gamma dF^2), common vol, own-strike vol, theta; residual = dP - the four terms."""
    Kc = K[:, None]; _, d1 = b76(F, Kc, T, sigK, call); sq = sigK * np.sqrt(T); pdf = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi)
    delta = ndtr(d1) - (0.0 if call else 1.0); gamma = pdf / (F * sq); vega = F * pdf * np.sqrt(T)
    dF = _sh(F, h) - F; dsA = _sh(sigA, h) - sigA; dsK = _sh(sigK, h) - sigK; T2 = _sh(T, h)
    theta = b76(F, Kc, T2, sigK, call)[0] - b76(F, Kc, T, sigK, call)[0]
    return _sh(price, h) - price, delta * dF + 0.5 * gamma * dF * dF, vega * dsA, vega * (dsK - dsA), theta, delta, vega


def day_obs(p, sym, day):
    """one sym-day -> dict of float32 arrays. [2 sides (CE, PE), 9 depths, NB] unless noted. Bars <= i only, except the h-forward changes."""
    S_ = SL(); NB = S_.NB; M0 = S_.M0; f = S_.day_feats(p, sym); M = f["M"]; ai, aok, F = f["ai"], f["aok"], f["F"]; nK = f["nK"]
    Ks = np.array(sorted({K for _, K in p["C"]})); b = np.arange(NB)
    cd = (dt.date.fromisoformat(str(p["exp"])[:10]) - dt.date.fromisoformat(day)).days
    T = np.maximum(cd * 1440 + 930 - (M0 + b), 1) / 525600.0
    px = {}; tr = {}
    for sd in ("CE", "PE"): tr[sd] = np.isfinite(M[sd][3]) & (M[sd][6] > 0); px[sd] = np.where(tr[sd], M[sd][3], np.nan)
    ivC = iv76(px["CE"], F, Ks[:, None], T, True); ivP = iv76(px["PE"], F, Ks[:, None], T, False); atm = p["atm"]
    both = np.where(np.isfinite(ivC) & np.isfinite(ivP), 0.5 * (ivC + ivP), np.where(np.isfinite(ivC), ivC, ivP))
    sigK = np.where(Ks[:, None] > atm, ivC, np.where(Ks[:, None] < atm, ivP, both)); sigA = np.where(aok, sigK[ai, b], np.nan)
    def sel(X, side, m):   # side 0 CE: strike index ai - m; side 1 PE: ai + m
        j = ai + (-m if side == 0 else m); g = aok & (j >= 0) & (j < nK); return np.where(g, X[np.clip(j, 0, nK - 1), b], np.nan)
    R = {}
    def put(name, per_side):
        R[name] = np.array([[sel(per_side[s], s, m) for m in DEPTHS] for s in (0, 1)], np.float32)
    for h in HZ:
        D = [decompose(F, Ks, T, sigK, sigA, px[sd], sd == "CE", h) for sd in ("CE", "PE")]
        for n, name in enumerate(("dP", "sp", "cv", "ov", "th")): put(f"{name}{h}", [D[0][n], D[1][n]])
        if h == 1: put("delta", [D[0][5], D[1][5]]); put("vega", [D[0][6], D[1][6]])
    put("P", [px["CE"], px["PE"]]); put("sigK", [sigK, sigK]); oi = [M["CE"][4], M["PE"][4]]
    with np.errstate(all="ignore"):
        put("doi", [_sh(o, -3) / _sh(o, -18) - 1 for o in oi]); put("dpx15", [px[sd] - _sh(px[sd], -15) for sd in ("CE", "PE")])
    # per bar: parity future per strike (ATM-2..ATM+2) against the median of the five; OI walls
    FK = Ks[:, None] + px["CE"] - px["PE"]; g5 = np.array([sel(FK, 1, o) for o in range(-2, 3)])
    with np.errstate(all="ignore"): R["pg"] = (g5 - np.nanmedian(g5, 0)).astype(np.float32)          # [5, NB]
    oc = np.nan_to_num(M["CE"][4]); op = np.nan_to_num(M["PE"][4]); Fb = np.nan_to_num(F)
    wc = np.where(Ks[:, None] > Fb, oc, -1).argmax(0); wp = np.where(Ks[:, None] < Fb, op, -1).argmax(0)
    R["bar"] = np.array([F, sigA, p["spot"], atm, Ks[wc], Ks[wp], T * 525600.0], np.float32)          # [7, NB]
    return R


BARN = ["F", "sigA", "S", "atm", "wallC", "wallP", "Tm"]


def study_table():
    """the observation table: one .npy per column in OUT/observe, indexed by scalp_lab's day index (all days; E55 studies mask LEARN)."""
    S_ = SL(); os.makedirs(OBS, exist_ok=True); mm = {}
    for d, k in enumerate(S_.DAYK):
        R = day_obs(S_.P[k], k[0], k[1])
        for n, a in R.items():
            if n not in mm: mm[n] = np.lib.format.open_memmap(f"{OBS}/{n}.npy", "w+", np.float32, (S_.ND,) + a.shape)
            mm[n][d] = a
        if d % 200 == 0: print("table", d, k, flush=True)
    for a in mm.values(): a.flush()
    print("table done", {n: a.shape for n, a in mm.items()})


def col(n): return np.load(f"{OBS}/{n}.npy", mmap_mode="r")
def bar(n): return np.asarray(col("bar")[:, BARN.index(n)], float)


def _days():
    """day-level arrays from scalp_lab: sym index, LEARN mask, expiry flag, business days to expiry (capped at 2)."""
    S_ = SL(); dte = np.array([min(S_.P[k]["dte"], 2) for k in S_.DAYK]); return S_.SYMI, ~S_.ISTEST, S_.D0, dte


def _tclust(v, day):
    """mean of v, and the t of the per-day means (the day is the unit), n events, n days."""
    v = np.asarray(v, float); ok = np.isfinite(v); v, day = v[ok], np.asarray(day)[ok]
    if len(v) < 5: return np.nan, np.nan, len(v), 0
    m = pd.Series(v).groupby(day).mean().values; return float(v.mean()), float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)) + 1e-12)), len(v), len(m)


SYMN = ["NIFTY", "SENSEX"]


# ================================================================ (1) premium decomposition
def study_o1():
    S_ = SL(); SYMI, LRN, D0, DTE = _days(); NB = S_.NB; tb = np.searchsorted(S_.L.TB, S_.M0 + np.arange(NB), "right"); rows = []
    P = col("P")
    for h in HZ:
        X = {n: col(f"{n}{h}") for n in ("dP", "sp", "cv", "ov", "th")}
        for s in (0, 1):
            dm = np.flatnonzero(LRN & (SYMI == s)); A = {n: np.asarray(x[dm], np.float64) for n, x in X.items()}; A["res"] = A["dP"] - A["sp"] - A["cv"] - A["ov"] - A["th"]
            ok = np.all([np.isfinite(a) for a in A.values()], 0) & (np.asarray(P[dm]) >= 1.0); ok[..., NB - 15 - h:] = False   # no change ends after 15:14
            gid = (np.arange(9)[None, None, :, None] * 3 + DTE[dm][:, None, None, None]) * 5 + tb[None, None, None, :] + np.zeros(ok.shape, int)
            g = gid[ok]; n = np.bincount(g, minlength=135); dP = A["dP"][ok]; vP = np.bincount(g, dP * dP, 135) / np.maximum(n, 1) - (np.bincount(g, dP, 135) / np.maximum(n, 1)) ** 2
            for name, a in A.items():
                a = a[ok]; m = np.bincount(g, a, 135) / np.maximum(n, 1); sd = np.sqrt(np.maximum(np.bincount(g, a * a, 135) / np.maximum(n, 1) - m * m, 0))
                cv = np.bincount(g, a * dP, 135) / np.maximum(n, 1) - m * np.bincount(g, dP, 135) / np.maximum(n, 1)
                for q in np.flatnonzero(n >= 200):
                    rows.append(dict(sym=SYMN[s], h=h, depth=DEPTHS[q // 15], dte=(q // 5) % 3, tb=S_.TBN[q % 5], term=name, n=int(n[q]), mean=m[q], sd=sd[q], share=cv[q] / vP[q]))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o1_decomp.csv", index=False)
    w = lambda g, c: np.average(g[c], weights=g.n)
    for s in SYMN:
        for h in (1, 15):
            G = T[(T.sym == s) & (T.h == h)]
            print(f"\n(1) {s} {h}-min premium change: share of variance by term, per depth (m > 0 = in the money), LEARN, all times")
            print(G.groupby(["depth", "term"]).apply(lambda g: w(g, "share"), include_groups=False).unstack().round(3)[["sp", "cv", "ov", "th", "res"]].to_string())
        G = T[(T.sym == s) & (T.h == 5) & T.term.isin(["th", "cv", "ov", "res", "dP", "sp"])]
        Z = G.groupby(["dte", "tb", "depth", "term"]).apply(lambda g: w(g, "mean") * 12, include_groups=False).unstack()   # premium points per HOUR
        Z["nonspot"] = Z["dP"] - Z["sp"]; Z["excess"] = Z["nonspot"] - Z["th"]
        print(f"\n(1) {s} drift in premium points per HOUR (5-min changes x 12): model theta, actual non-spot drift, excess = actual - theta; depths 2 / 0 / -2")
        print(Z.loc[(slice(None), slice(None), [2, 0, -2]), ["th", "nonspot", "excess"]].unstack("depth").round(2).to_string())
    # persistence of the non-spot change (skip-one: the past window ends one bar before the forward window starts, so no shared print)
    ns5 = np.asarray(col("dP5"), np.float64) - col("sp5"); ns15 = np.asarray(col("dP15"), np.float64) - col("sp15"); atm = bar("atm"); rows = []
    same = lambda k: (_sh(atm, -k) == atm)[:, None, None, :]
    for s in (0, 1):
        for d0 in (0, 1):
            dm = np.flatnonzero(LRN & (SYMI == s) & (D0 == d0)); day = np.broadcast_to(dm[:, None, None, None], ns5[dm].shape)
            xs = np.where(same(6)[dm], _sh(ns5[dm], -6), np.nan); x0 = np.where(same(5)[dm], _sh(ns5[dm], -5), np.nan); y5, y15 = ns5[dm], ns15[dm]
            for q, m in enumerate(DEPTHS):
                a, a0, b5, b15, dd = xs[:, :, q].ravel(), x0[:, :, q].ravel(), y5[:, :, q].ravel(), y15[:, :, q].ravel(), day[:, :, q].ravel()
                ok = np.isfinite(a) & np.isfinite(b5) & np.isfinite(b15) & np.isfinite(a0)
                if ok.sum() < 2000: continue
                a, a0, b5, b15, dd = a[ok], a0[ok], b5[ok], b15[ok], dd[ok]; lo, hi = np.quantile(a, [0.1, 0.9])
                r = dict(sym=SYMN[s], d0=d0, depth=m, n=int(ok.sum()), corr_touch=np.corrcoef(a0, b5)[0, 1], corr_skip=np.corrcoef(a, b5)[0, 1], sd_past=a.std())
                for nm, y in (("5", b5), ("15", b15)):
                    r[f"lo_fwd{nm}"], r[f"lo_t{nm}"] = _tclust(y[a <= lo], dd[a <= lo])[:2]; r[f"hi_fwd{nm}"], r[f"hi_t{nm}"] = _tclust(y[a >= hi], dd[a >= hi])[:2]
                r["all_fwd5"] = b5.mean(); r["all_fwd15"] = b15.mean(); rows.append(r)
    T2 = pd.DataFrame(rows); T2.to_csv(f"{OBS}/o1_persist.csv", index=False)
    print("\n(1) persistence of the NON-SPOT premium change (premium points): past = minutes i-6..i-1; forward = i..i+5 / i..i+15, same strike.")
    print("    lo / hi = bottom / top decile of the past change; lo_fwd = mean forward change after a bottom-decile past (t by day)")
    print(T2.round(3).to_string(index=False))


# ================================================================ (4) IV and Greeks
def study_o4():
    S_ = SL(); SYMI, LRN, D0, DTE = _days(); NB = S_.NB; sA = bar("sigA"); F = bar("F"); sK = col("sigK"); dP15 = col("dP15"); dP5 = col("dP5"); rows = []
    with np.errstate(all="ignore"):
        ratio = sA / sA[:, [5]]; skew = np.asarray(sK[:, 1, 2], float) - np.asarray(sK[:, 0, 2], float)   # sigma(put m=-2) - sigma(call m=-2)
    mins = [5, 15, 30, 45, 75, 105, 165, 225, 285, 315, 330, 345, 360]
    for s in (0, 1):
        for dte in (0, 1, 2):
            dm = LRN & (SYMI == s) & (DTE == dte)
            rows.append(dict(sym=SYMN[s], dte=dte, days=int(dm.sum()), what="sigA / sigA(09:20), median", **{f"{9 + (15 + m) // 60:02d}:{(15 + m) % 60:02d}": np.nanmedian(ratio[dm, m]) for m in mins}))
            rows.append(dict(sym=SYMN[s], dte=dte, days=int(dm.sum()), what="sigA level, median (vol pts)", **{f"{9 + (15 + m) // 60:02d}:{(15 + m) % 60:02d}": 100 * np.nanmedian(sA[dm, m]) for m in mins}))
            rows.append(dict(sym=SYMN[s], dte=dte, days=int(dm.sum()), what="skew put-call at 2 OTM, median (vol pts)", **{f"{9 + (15 + m) // 60:02d}:{(15 + m) % 60:02d}": 100 * np.nanmedian(skew[dm, m]) for m in mins}))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o4_iv_clock.csv", index=False); print("\n(4) IV through the day, LEARN"); print(T.round(3).to_string(index=False))
    # lead-lag: per-day correlation of the 1-min sigA change with the 1-min F return at lags -5..+5 (lag > 0: sigma change comes AFTER the F move)
    with np.errstate(all="ignore"): ds = np.diff(sA, axis=1, prepend=np.nan); rf = np.diff(np.log(F), axis=1, prepend=np.nan)
    ds[:, :10] = np.nan; ds[:, 360:] = np.nan; rows = []
    def daycorr(x, y, dm):
        out = []
        for d in np.flatnonzero(dm):
            ok = np.isfinite(x[d]) & np.isfinite(y[d])
            if ok.sum() > 100 and x[d][ok].std() > 0 and y[d][ok].std() > 0: out.append(np.corrcoef(x[d][ok], y[d][ok])[0, 1])
        o = np.array(out); return (o.mean(), o.mean() / (o.std(ddof=1) / np.sqrt(len(o))), len(o)) if len(o) > 5 else (np.nan, np.nan, len(o))
    for s in (0, 1):
        for d0 in (0, 1):
            dm = LRN & (SYMI == s) & (D0 == d0); r = dict(sym=SYMN[s], d0=d0)
            for lag in (-5, -3, -2, -1, 0, 1, 2, 3, 5): c, t, n = daycorr(_sh(ds, lag), rf, dm); r[f"lag{lag:+d}"] = c; r["days"] = n
            rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o4_iv_spot_leadlag.csv", index=False)
    print("\n(4) per-day corr of d sigA(i + lag) with the F return at bar i (lag > 0 = the IV change FOLLOWS the spot move)"); print(T.round(3).to_string(index=False))
    # does an IV change lead the premium? past 3-min sigA change (ending one bar before) against the forward ATM straddle change, fixed strikes
    st5 = np.asarray(dP5[:, 0, 4], float) + dP5[:, 1, 4]; st15 = np.asarray(dP15[:, 0, 4], float) + dP15[:, 1, 4]; atm = bar("atm"); rows = []
    with np.errstate(all="ignore"): x = np.where(_sh(atm, -4) == atm, _sh(sA, -1) - _sh(sA, -4), np.nan)
    for s in (0, 1):
        for d0 in (0, 1):
            dm = LRN & (SYMI == s) & (D0 == d0); xx, y5, y15 = x[dm].ravel(), st5[dm].ravel(), st15[dm].ravel(); dd = np.repeat(np.flatnonzero(dm), NB)
            ok = np.isfinite(xx) & np.isfinite(y5) & np.isfinite(y15); xx, y5, y15, dd = xx[ok], y5[ok], y15[ok], dd[ok]; lo, hi = np.quantile(xx, [0.1, 0.9])
            r = dict(sym=SYMN[s], d0=d0, n=int(ok.sum()), corr5=np.corrcoef(xx, y5)[0, 1], corr15=np.corrcoef(xx, y15)[0, 1], all15=y15.mean())
            r["ivdown_fwd15"], r["ivdown_t"] = _tclust(y15[xx <= lo], dd[xx <= lo])[:2]; r["ivup_fwd15"], r["ivup_t"] = _tclust(y15[xx >= hi], dd[xx >= hi])[:2]; rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o4_iv_leads_premium.csv", index=False)
    print("\n(4) past 3-min ATM IV change (skip one bar) against the forward ATM straddle change (premium points, fixed strikes)"); print(T.round(3).to_string(index=False))


# ================================================================ (3) cross-instrument links on the panel
def study_o3():
    S_ = SL(); SYMI, LRN, D0, DTE = _days(); F = bar("F"); days = [k[1] for k in S_.DAYK]; ix = {(SYMI[d], days[d]): d for d in range(S_.ND)}; rows = []
    pairs = [(ix[(0, dy)], ix[(1, dy)]) for dy in sorted(set(days)) if (0, dy) in ix and (1, dy) in ix and LRN[ix[(0, dy)]]]
    for h in (1, 5, 15):
        with np.errstate(all="ignore"): R = np.log(F) - np.log(_sh(F, -h))
        R[:, :10 + h] = np.nan; r = dict(what=f"NIFTY F {h}-min return vs SENSEX F {h}-min return (lag in units of {h} min; lag > 0 = SENSEX later)")
        for lag in (-3, -2, -1, 0, 1, 2, 3):
            cs = []
            for a, b_ in pairs:
                x, y = R[a], _sh(R[b_], lag * h); ok = np.isfinite(x) & np.isfinite(y)
                if ok.sum() > 60: cs.append(np.corrcoef(x[ok][::h], y[ok][::h])[0, 1])
            cs = np.array(cs); r[f"lag{lag:+d}"] = np.nanmean(cs); r["days"] = len(cs)
        rows.append(r)
    dP1 = col("dP1"); ov5 = col("ov5"); vg = col("vega")
    for s in (0, 1):
        dm = np.flatnonzero(LRN & (SYMI == s)); c, p_ = np.asarray(dP1[dm, 0, 4], float), np.asarray(dP1[dm, 1, 4], float); ok = np.isfinite(c) & np.isfinite(p_)
        rows.append(dict(what=f"{SYMN[s]} ATM CE vs ATM PE 1-min change", **{"lag+0": np.corrcoef(c[ok], p_[ok])[0, 1]}, days=len(dm)))
        for side, nm in ((0, "call"), (1, "put")):
            with np.errstate(all="ignore"): a = np.asarray(ov5[dm, side, 3], float) / vg[dm, side, 3]; b_ = np.asarray(ov5[dm, side, 1], float) / vg[dm, side, 1]
            ok = np.isfinite(a) & np.isfinite(b_) & (np.abs(a) < 0.05) & (np.abs(b_) < 0.05)
            rows.append(dict(what=f"{SYMN[s]} own-strike vol change (5 min), {nm} OTM1 vs OTM3", **{"lag+0": np.corrcoef(a[ok], b_[ok])[0, 1]}, days=len(dm)))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o3_cross.csv", index=False); print("\n(3) cross-instrument links, LEARN panel"); print(T.round(3).to_string(index=False))


# ================================================================ (5) OI
def study_o5():
    S_ = SL(); SYMI, LRN, D0, DTE = _days(); NB = S_.NB; F = bar("F"); doi = col("doi"); dpx = col("dpx15"); dP15 = col("dP15"); rows = []
    st15 = np.asarray(dP15[:, 0, 4], float) + dP15[:, 1, 4]; bars = np.arange(30, 315, 5)   # 09:45..14:30, every 5th bar
    for s in (0, 1):
        dm = np.flatnonzero(LRN & (SYMI == s)); base = {h: (_sh(F, h) - F)[dm][:, bars] for h in (15, 30, 60)}; dd = np.repeat(dm, len(bars)); sv = st15[dm][:, bars].ravel()
        for side, nm, sg in ((0, "CE", 1), (1, "PE", -1)):
            o = np.nanmean(np.asarray(doi[dm, side, 2:5], float), 1)[:, bars].ravel(); px = np.nansum(np.asarray(dpx[dm, side, 2:5], float), 1)[:, bars].ravel()
            lab = np.where(~np.isfinite(o) | (np.abs(o) < 0.005) | (px == 0), -1, (px < 0) * 2 + (o < 0))   # 0 long build-up, 1 short covering, 2 short build-up, 3 long unwinding
            for l, ln in enumerate(("long build-up (price up, OI up)", "short covering (price up, OI down)", "short build-up (price down, OI up)", "long unwinding (price down, OI down)")):
                r = dict(sym=SYMN[s], side=nm, label=ln, n=int((lab == l).sum()))
                for h in (15, 30, 60):
                    v = base[h].ravel(); m, t, _, _ = _tclust(v[lab == l], dd[lab == l]); r[f"F_move_{h}"] = m; r[f"t{h}"] = t; r[f"all_{h}"] = np.nanmean(v)
                r["straddle15"], r["t_st"] = _tclust(sv[lab == l], dd[lab == l])[:2]; r["straddle15_all"] = np.nanmean(sv); rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o5_oi_labels.csv", index=False)
    print("\n(5) OI build-up labels (15-min OI change lagged 3 min, ATM..OTM2 of one side) against the forward F move (index points) and the ATM straddle (premium points)")
    print(T.round(2).to_string(index=False))
    # walls: first approach within 0.10% of the highest-OI strike (call wall above / put wall below) against the next strike beyond... a non-wall strike at the same test
    wC, wP, st = bar("wallC"), bar("wallP"), np.where(SYMI == 0, 50, 100); rows = []
    for s in (0, 1):
        for nm, up in (("call wall above", True), ("put wall below", False)):
            res = {"wall": [], "other": []}
            for d in np.flatnonzero(LRN & (SYMI == s)):
                f = F[d]; w = (wC if up else wP)[d]
                for kind in ("wall", "other"):
                    for i in range(30, 300):
                        if not np.isfinite(f[i]): continue
                        K = w[i] if kind == "wall" else (np.ceil(f[i - 15] / st[d]) * st[d] if up else np.floor(f[i - 15] / st[d]) * st[d])
                        if kind == "wall" and not (w[i - 30:i + 1] == K).all(): continue
                        if kind == "other" and K == w[i]: continue
                        near = abs(f[i] - K) / K <= 0.001; far = (np.abs(f[i - 15:i] - K) / K > 0.001).all(); side_ok = (f[i] < K) if up else (f[i] > K)
                        if near and far and side_ok:
                            br = lambda h: bool(((f[i + 1:i + h + 1] > K) if up else (f[i + 1:i + h + 1] < K)).any())
                            res[kind].append((d, br(30), br(60), (f[i + 30] - f[i]) * (1 if up else -1))); break
            for kind, v in res.items():
                v = np.array(v, float)
                rows.append(dict(sym=SYMN[s], level=nm, kind=kind, n=len(v), days=len(set(v[:, 0])), p_break30=v[:, 1].mean(), p_break60=v[:, 2].mean(), move30_toward=np.nanmean(v[:, 3])))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o5_oi_walls.csv", index=False)
    print("\n(5) OI walls: first approach to within 0.10% (first per day), P(F trades beyond it within 30 / 60 min), wall against a non-wall strike"); print(T.round(3).to_string(index=False))


# ================================================================ (6) levels (frozen mechanical definitions, E55 row)
def _bars5(S):
    """5-minute OHLC of the 1m spot closes: arrays (75,) o h l c; bar j covers 1m bars 5j..5j+4 and is known at 1m bar 5j+4."""
    X = S[:375].reshape(75, 5); return X[:, 0], np.nanmax(X, 1), np.nanmin(X, 1), X[:, 4]


def level_events(S, F, VW, V, prev, sym):
    """one day's events: list of (type, 1m decision bar i, theory direction +1 / -1). Uses bars <= i only. prev = (high, low, close) or None."""
    ev = []; n = len(S); ok = np.isfinite(S); lo_i, hi_i = 15, 330
    def first_cross(level, need_inside=30):   # first 1m close beyond `level` after >= need_inside bars on the other side
        for i in range(max(lo_i, need_inside), hi_i):
            if S[i] > level and (S[i - need_inside:i] <= level).all(): return i, 1
            if S[i] < level and (S[i - need_inside:i] >= level).all(): return i, -1
        return None
    if prev is not None:
        for nm, lv in (("L1_PDH", prev[0]), ("L1_PDL", prev[1]), ("L1_PDC", prev[2])):
            c = first_cross(lv)
            if c: ev.append((nm, c[0], c[1]))
    for nm, stp in (("L2_round_major", 500 if sym == "NIFTY" else 1000), ("L2_round_minor", 100 if sym == "NIFTY" else 500)):
        seen = set()
        for i in range(lo_i, hi_i):
            a, b_ = S[i - 1], S[i]
            if not (np.isfinite(a) and np.isfinite(b_)) or a == b_: continue
            lv = np.floor(max(a, b_) / stp) * stp
            if min(a, b_) < lv <= max(a, b_) and lv not in seen and not (nm == "L2_round_minor" and lv % (500 if sym == "NIFTY" else 1000) == 0):
                seen.add(lv); ev.append((nm, i, -1 if b_ > a else 1))                      # theory: rejection = fade the approach
    orh, orl = np.nanmax(S[:15]), np.nanmin(S[:15])
    for i in range(15, hi_i):
        if S[i] > orh: ev.append(("L3_OR_break", i, 1)); break
        if S[i] < orl: ev.append(("L3_OR_break", i, -1)); break
    d = np.sign(F - VW); run = 0
    for i in range(1, hi_i):
        if d[i] == d[i - 1]: run += 1
        else:
            if run >= 20 and i >= 45 and d[i] != 0: ev.append(("L4_VWAP_cross", i, int(d[i])))
            run = 1
    o, h, l, c = _bars5(S); body = np.abs(c - o)
    # L5 sweep: swing high = 5m high above the 3 highs each side (known at bar j+3); plus the previous day's high / low
    sh_ = [(j + 3, h[j]) for j in range(3, 72) if h[j] > max(h[j - 3:j].max(), h[j + 1:j + 4].max())]; sl_ = [(j + 3, l[j]) for j in range(3, 72) if l[j] < min(l[j - 3:j].min(), l[j + 1:j + 4].min())]
    if prev is not None: sh_.append((0, prev[0])); sl_.append((0, prev[1]))
    taken_h, taken_l = set(), set()
    for j in range(3, 66):
        cand = [(kn, lv) for kn, lv in sh_ if kn < j and lv not in taken_h and lv >= h[max(0, kn - 3):j].max() - 1e-9]   # untaken: no bar since has traded above it
        if cand:
            lv = max(cand, key=lambda x: x[0])[1]
            if h[j] >= lv * 1.0002:
                taken_h.add(lv)
                if c[j] < lv: ev.append(("L5_sweep", 5 * j + 4, -1))
        cand = [(kn, lv) for kn, lv in sl_ if kn < j and lv not in taken_l and lv <= l[max(0, kn - 3):j].min() + 1e-9]
        if cand:
            lv = max(cand, key=lambda x: x[0])[1]
            if l[j] <= lv * 0.9998:
                taken_l.add(lv)
                if c[j] > lv: ev.append(("L5_sweep", 5 * j + 4, 1))
    # L6 fair value gap: bars a, b, c with low(c) > high(a) by >= 0.03%; event = first later bar whose low trades back to <= low(c)
    for j in range(2, 64):
        if l[j] > h[j - 2] * 1.0003:
            for q in range(j + 1, 66):
                if l[q] <= l[j]: ev.append(("L6_FVG", 5 * q + 4, 1)); break
        if h[j] < l[j - 2] * 0.9997:
            for q in range(j + 1, 66):
                if h[q] >= h[j]: ev.append(("L6_FVG", 5 * q + 4, -1)); break
    # L7 order block: displacement bar (body >= 2 x mean of the prior 20 bodies, close beyond the prior 10-bar extreme); OB = last opposite bar before it
    for j in range(20, 62):
        mb = body[j - 20:j].mean()
        for sg in (1, -1):
            disp = body[j] >= 2 * mb and ((c[j] > o[j] and c[j] > h[j - 10:j].max()) if sg > 0 else (c[j] < o[j] and c[j] < l[j - 10:j].min()))
            if not disp: continue
            ob = next((q for q in range(j - 1, max(j - 11, -1), -1) if (c[q] < o[q] if sg > 0 else c[q] > o[q])), None)
            if ob is None: continue
            for q in range(j + 2, 66):
                if l[q] <= h[ob] and h[q] >= l[ob]: ev.append(("L7_order_block", 5 * q + 4, sg)); break
    return [(t, i, s) for t, i, s in ev if lo_i <= i < hi_i and ok[i]]


def all_levels():
    """events on every day (LEARN and TEST; E55 reads the LEARN rows only). DataFrame: type, d (scalp_lab day index), i, dirn."""
    S_ = SL(); pk = f"{OBS}/o6_events.pkl"
    if os.path.exists(pk): return pd.read_pickle(pk)
    prev = {}; rows = []
    for d, k in enumerate(S_.DAYK):
        p = S_.P[k]; f = S_.day_feats(p, k[0]); S = p["spot"]
        for t, i, s in level_events(S, f["F"], f["VW"], f["V"], prev.get(k[0]), k[0]): rows.append((t, d, i, s))
        if np.isfinite(S).any(): prev[k[0]] = (np.nanmax(S), np.nanmin(S), S[np.isfinite(S)][-1])
    E = pd.DataFrame(rows, columns=["type", "d", "i", "dirn"]).sort_values(["d", "i"]).reset_index(drop=True); E.to_pickle(pk); return E


def level_table(E, mask_days, tag, seed=6):
    """per event type: signed F move in the theory direction (minus a same-bar random-day placebo) and the gross premium change of the
    ITM2 and ATM option in the theory direction, entered at the next bar's open (scalp_lab.gather), no costs."""
    S_ = SL(); SYMI = S_.SYMI; F = bar("F"); rg = np.random.default_rng(seed); rows = []; E = E[mask_days[E.d.values]]
    pools = {s: np.flatnonzero(mask_days & (SYMI == s)) for s in (0, 1)}
    for (typ, s), g in E.groupby(["type", SYMI[E.d.values]]):
        d, i, sg = g.d.values, g.i.values, g.dirn.values; r = dict(type=typ, sym=SYMN[s], n=len(g), days=g.d.nunique(), up_share=(sg > 0).mean())
        pl = rg.choice(pools[s], (len(g), 20))
        for h in (5, 15, 30, 60):
            mv = sg * (F[d, np.minimum(i + h, 374)] - F[d, i]); pm = sg[:, None] * (F[pl, np.minimum(i + h, 374)[:, None]] - F[pl, i[:, None]])
            ex = mv - np.nanmean(pm, 1); m, t, _, _ = _tclust(ex, d); r[f"F{h}"] = m; r[f"t{h}"] = t
        for depth, nm in ((2, "ITM2"), (0, "ATM")):
            G = S_.gather(d, i + 1, depth, sg); Gp = S_.gather(pl[:, 0], i + 1, depth, sg)
            for h in (15, 30):
                x = G["C"][:, h - 1].astype(float) - G["ENT"]; xp = Gp["C"][:, h - 1].astype(float) - Gp["ENT"]
                r[f"{nm}_{h}"], r[f"{nm}_{h}_t"] = _tclust(x, d)[:2]; r[f"{nm}_{h}_rand"] = np.nanmean(xp)
            if depth == 2: r["half1"], r["half2"] = (np.nanmean((G["C"][:, 14].astype(float) - G["ENT"])[hh]) for hh in (d < np.median(d), d >= np.median(d)))
        rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o6_levels_{tag}.csv", index=False); return T


def study_o6():
    S_ = SL(); E = all_levels(); T = level_table(E, ~S_.ISTEST, "learn")
    print("\n(6) levels, LEARN. F{h} = index points in the THEORY direction after h min minus a same-minute random-day placebo (t by day).")
    print("    ITM2_15 = gross premium points of the ITM2 option bought in the theory direction, 15 min (no costs); _rand = the same on a random LEARN day")
    c1 = ["type", "sym", "n", "days", "up_share", "F5", "t5", "F15", "t15", "F30", "t30", "F60", "t60"]; print(T[c1].round(2).to_string(index=False))
    c2 = ["type", "sym", "n", "ITM2_15", "ITM2_15_t", "ITM2_15_rand", "ITM2_30", "ITM2_30_t", "ITM2_30_rand", "ATM_15", "ATM_15_rand", "ATM_30", "ATM_30_rand", "half1", "half2"]
    print(T[c2].round(2).to_string(index=False))


# ================================================================ (7) pricing: parity gaps, stale bars, disagreeing moves
def study_o7():
    S_ = SL(); SYMI, LRN, D0, DTE = _days(); NB = S_.NB; pg = col("pg"); atm = bar("atm"); P = col("P"); dP1 = col("dP1"); F = bar("F"); dl = col("delta"); rows = []
    for s in (0, 1):
        dm = np.flatnonzero(LRN & (SYMI == s)); g = np.asarray(pg[dm], float); g[:, :, :5] = np.nan; g[:, :, 360:] = np.nan
        for o in range(5):
            x = g[:, o]; x1 = np.where((_sh(atm[dm], 1) == atm[dm]), _sh(x, 1), np.nan); x5 = np.where((_sh(atm[dm], 5) == atm[dm]), _sh(x, 5), np.nan); a = np.abs(x[np.isfinite(x)])
            k1 = np.isfinite(x) & np.isfinite(x1); k5 = np.isfinite(x) & np.isfinite(x5)
            big = k1 & (np.abs(x) >= np.nanquantile(np.abs(x), 0.9))
            rows.append(dict(sym=SYMN[s], strike=f"ATM{o - 2:+d}", n=len(a), abs_med=np.median(a), abs_p75=np.quantile(a, 0.75), abs_p90=np.quantile(a, 0.9), abs_p99=np.quantile(a, 0.99),
                             ar1=np.corrcoef(x[k1], x1[k1])[0, 1], ar5=np.corrcoef(x[k5], x5[k5])[0, 1], big_gap_next_change=np.mean((x1[big] - x[big]) * -np.sign(x[big])), big_gap_size=np.mean(np.abs(x[big]))))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o7_parity.csv", index=False)
    print("\n(7) parity gap g_K = (K + CE - PE) - median over ATM+-2, index / premium points, LEARN 1m closes; big = top decile of abs(g): how much of it closes by the next bar")
    print(T.round(3).to_string(index=False))
    rows = []; s1 = pd.DataFrame(np.diff(F, axis=1, prepend=np.nan)).T.shift(1).rolling(30, min_periods=30).std().T.values; dF = _sh(F, 1) - F
    for s in (0, 1):
        dm = np.flatnonzero(LRN & (SYMI == s)); same = (_sh(atm[dm], 1) == atm[dm])
        for q, m in enumerate(DEPTHS):
            for side in (0, 1):
                p_ = np.asarray(P[dm, side, q], float); d1_ = np.asarray(dP1[dm, side, q], float); d2_ = np.where(same, _sh(d1_, 1), np.nan); sg = 1 if side == 0 else -1
                mv = np.abs(dF[dm]) >= 0.5 * s1[dm]; ok = mv & np.isfinite(d1_); wrong = ok & (d1_ * sg * dF[dm] < 0); k2 = wrong & np.isfinite(d2_); r2 = ok & ~wrong & np.isfinite(d2_)
                rows.append(dict(sym=SYMN[s], depth=m, side="CE" if side == 0 else "PE", untraded_share=1 - np.isfinite(p_[:, 5:360]).mean(), n_moves=int(ok.sum()), wrong_way_share=wrong.sum() / max(ok.sum(), 1),
                                 wrong_size=np.mean(np.abs(d1_[wrong])) if wrong.any() else np.nan, next_bar_catchup=np.mean(d2_[k2] * sg * np.sign(dF[dm][k2])) if k2.any() else np.nan,
                                 next_bar_after_right=np.mean(d2_[r2] * sg * np.sign(dF[dm][r2])) if r2.any() else np.nan))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/o7_disagree.csv", index=False)
    print("\n(7) stale bars and 'wrong-way' option moves (F moved >= 0.5 s1 in the bar and the option closed AGAINST its delta sign); catch-up = next-bar change in the direction F had moved, premium points")
    print(T.groupby(["sym", "depth"]).agg(untraded_share=("untraded_share", "mean"), n_moves=("n_moves", "sum"), wrong_way_share=("wrong_way_share", "mean"), wrong_size=("wrong_size", "mean"),
                                           next_bar_catchup=("next_bar_catchup", "mean"), next_bar_after_right=("next_bar_after_right", "mean")).round(3).to_string())


# ================================================================ tick tape (OBSERVE days only; tapelib grids, receipt clock)
_TL = []
def TLm():
    if not _TL:
        import tapelib; _TL.append(tapelib)
    return _TL[0]
S0, S1 = 3000, 219000                 # 09:20:00 .. 15:20:00 in 100 ms slots
CAPV = {"NIFTY": 1.00, "SENSEX": 3.00}   # quote-validity spread cap (E54's, frozen up front there)


def _opts(TD, sym):
    """nearest-expiry options on the day's tape: list of (iid, side, K)."""
    pre = TLm().TSYM[sym]["pre"] + ":" + str(TD.exp[sym]) + ":"; return [(k, k.split(":")[4], float(k.split(":")[3])) for k in TD.ticks if k.startswith(pre)]


def _vmid(TD, iid, sym):
    """mid on the 100 ms grid, NaN where the quote is not valid (older than 1.5 s, one-sided or wider than the cap)."""
    G = TD.grid(iid)
    if G is None: return None
    return np.where(TLm()._valid(G, slice(None), CAPV[sym]), G["mid"], np.nan).astype(float)


def study_t1(days=None):
    """(2) per instrument class: ticks per second, spread, sizes, share of ticks that change the ltp (trade proxy), receipt - exchange lag."""
    TL = TLm(); acc = {}
    for day in (days or T_OBS):
        TD = TL.TapeDay(day)
        def add(key, g, secs):
            t = g.t.values; m = (t >= TL.T0MS + S0 * 100) & (t < TL.T0MS + S1 * 100)
            a = acc.setdefault(key, dict(n=0, secs=0.0, sp=[], sz=[], z5=[], tr=0, lag=[]))
            a["n"] += int(m.sum()); a["secs"] += secs; a["sp"].append((g.ask.values - g.bid.values)[m]); a["sz"].append(((g.bq.values + g.aq.values) / 2)[m]); a["z5"].append(((g.b5.values + g.a5.values) / 2)[m])
            a["tr"] += int((np.diff(g.ltp.values, prepend=np.nan) != 0)[m].sum()); a["lag"].append((g.t.values - g.xt.values)[m])
        for sym, c in TL.TSYM.items():
            add((sym, "index", 0), TD.ticks[c["idx"]], (S1 - S0) / 10)
            atm = TD.atm(sym)
            for iid, side, K in _opts(TD, sym):
                g = TD.ticks[iid]; sl = np.clip(TL.slot_of(g.t.values), 0, TL.NSLOT - 1); dep = np.round((atm[sl] - K) / c["step"]) * (1 if side == "CE" else -1)
                dgrid = np.round((atm[S0:S1] - K) / c["step"]) * (1 if side == "CE" else -1)
                for m_ in DEPTHS:
                    k = dep == m_
                    if k.any(): add((sym, side, int(m_)), g[k], float((dgrid == m_).sum()) / 10)
        if TD.fut: add(("NIFTY", "future", 0), TD.ticks[TD.fut], (S1 - S0) / 10)
        print("t1", day, flush=True)
    rows = []
    for (sym, cls, m_), a in sorted(acc.items()):
        sp = np.concatenate(a["sp"]); sp = sp[np.isfinite(sp)]; sz = np.concatenate(a["sz"]); z5 = np.concatenate(a["z5"]); lag = np.concatenate(a["lag"])
        rows.append(dict(sym=sym, cls=cls, depth=m_, ticks=a["n"], ticks_per_s=a["n"] / max(a["secs"], 1), spread_med=np.median(sp) if len(sp) else np.nan, spread_p75=np.quantile(sp, 0.75) if len(sp) else np.nan,
                         best_size_med=np.nanmedian(sz) if len(sz) else np.nan, size5_med=np.nanmedian(z5) if len(z5) else np.nan, ltp_change_share=a["tr"] / max(a["n"], 1), lag_ms_med=np.median(lag), lag_ms_p90=np.quantile(lag, 0.9)))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/t1_tape_classes.csv", index=False); print("\n(2) tape by instrument class, OBSERVE days (depth > 0 = in the money)"); print(T.round(3).to_string(index=False))


def study_t2(days=None):
    """(2) how a 1-minute candle forms: share of the bar's range made after 5 / 15 / 30 s (a random walk gives sqrt(t/60) = 0.29 / 0.50 / 0.71),
    and where in the minute the high and the low print."""
    TL = TLm(); rows = []
    for day in (days or T_OBS):
        TD = TL.TapeDay(day)
        for sym, c in TL.TSYM.items():
            atm = TD.atm(sym); series = {"index": [(None, TD.grid(c["idx"])["ltp"].astype(float))]}
            for side in ("CE", "PE"): series["ATM " + side] = [(K, _vmid(TD, TD.oid(sym, K, side), sym)) for K in np.unique(atm[S0:S1][np.isfinite(atm[S0:S1])])]
            for name, lst in series.items():
                for K, x in lst:
                    if x is None: continue
                    for st in range(S0, S1, 600):
                        if K is not None and atm[st] != K: continue
                        W = x[st:st + 601]
                        if np.isfinite(W).mean() < 0.9: continue
                        W = pd.Series(W).ffill().bfill().values; rg = W.max() - W.min()
                        if rg <= 0: continue
                        rows.append((day, sym, name, rg, *[(W[:n + 1].max() - W[:n + 1].min()) / rg for n in (50, 150, 300)], W.argmax() // 10, W.argmin() // 10, abs(W[-1] - W[0]) / rg))
        print("t2", day, flush=True)
    T = pd.DataFrame(rows, columns=["day", "sym", "series", "range", "r5", "r15", "r30", "hi_s", "lo_s", "body_share"])
    T["ext_first5"] = ((T.hi_s < 5) | (T.lo_s < 5)); T["ext_last5"] = ((T.hi_s >= 55) | (T.lo_s >= 55))
    Z = T.groupby(["sym", "series"]).agg(bars=("range", "size"), range_med=("range", "median"), r5=("r5", "mean"), r15=("r15", "mean"), r30=("r30", "mean"), ext_first5=("ext_first5", "mean"), ext_last5=("ext_last5", "mean"), body_share=("body_share", "mean"))
    Z.to_csv(f"{OBS}/t2_candle.csv"); print("\n(2) candle formation (random walk benchmark: r5 0.29, r15 0.50, r30 0.71; an extreme in the first or last 5 s has chance 1 - (50/60)^2 = 0.31 each way under uniform timing)"); print(Z.round(3).to_string())


LAGS = [-50, -30, -20, -10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 20, 30, 50]


def _syn(TD, sym):
    """ATM synthetic (CE mid - PE mid) 1-s change on the grid, strike fixed over the second; NaN elsewhere."""
    atm = TD.atm(sym); r = np.full(TLm().NSLOT, np.nan)
    for K in np.unique(atm[S0:S1][np.isfinite(atm[S0:S1])]):
        c, p_ = _vmid(TD, TD.oid(sym, K, "CE"), sym), _vmid(TD, TD.oid(sym, K, "PE"), sym)
        if c is None or p_ is None: continue
        x = c - p_; d = x - np.roll(x, 10); k = (atm == K) & (np.roll(atm, 10) == K); k[:10] = False; r[k] = d[k]
    return r


def study_t3(days=None):
    """(2) who moves first: cross-correlation of 1-s changes at lags of 0.1-5 s (lag > 0: the SECOND series moves later)."""
    TL = TLm(); acc = {}
    for day in (days or T_OBS):
        TD = TL.TapeDay(day); d1 = lambda x: x - np.roll(x, 10)
        X = dict(N_fut=d1(TD.grid(TD.fut)["mid"].astype(float)) if TD.fut else None, N_idx=d1(TD.grid("NSE_IDX:NIFTY")["ltp"].astype(float)), N_syn=_syn(TD, "NIFTY"),
                 S_idx=d1(TD.grid("BSE_IDX:SENSEX")["ltp"].astype(float)), S_syn=_syn(TD, "SENSEX"))
        for a, b_ in (("N_fut", "N_idx"), ("N_fut", "N_syn"), ("N_syn", "N_idx"), ("N_fut", "S_idx"), ("N_idx", "S_idx"), ("N_syn", "S_syn"), ("N_fut", "S_syn"), ("S_syn", "S_idx")):
            if X[a] is None or X[b_] is None: continue
            for L in LAGS:
                x = X[a][S0:S1]; y = X[b_][S0 + L:S1 + L]; ok = np.isfinite(x) & np.isfinite(y)
                if ok.sum() > 5000: acc.setdefault((a, b_), {}).setdefault(L, []).append(np.corrcoef(x[ok], y[ok])[0, 1])
        print("t3", day, flush=True)
    rows = []
    for (a, b_), dct in acc.items():
        m = {L: float(np.mean(v)) for L, v in dct.items()}; pk = max(m, key=lambda L: m[L])
        rows.append(dict(first=a, second=b_, days=len(dct[0]), peak_lag_s=pk / 10, peak_corr=m[pk], **{f"{L / 10:+.1f}s": m[L] for L in LAGS if L in m},
                         asym=sum(m[L] for L in LAGS if L > 0) - sum(m[L] for L in LAGS if L < 0)))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/t3_leadlag.csv", index=False)
    print("\n(2) lead-lag of 1-s changes; column = lag of the SECOND series (positive: it moves later = the first one leads)"); print(T.round(3).to_string(index=False))


def study_t4(days=None, tag="obs"):
    """(1, 7) tick decomposition: option mid change over w seconds = beta x NIFTY-future mid change + residual. Residual size against the
    spread, whether the residual reverses in the next window, and how much of a future move the option still owes (catch-up)."""
    TL = TLm(); rec = []
    for day in (days or T_OBS):
        TD = TL.TapeDay(day)
        if not TD.fut: continue
        fm = TD.grid(TD.fut)["mid"].astype(float)
        for sym, c in TL.TSYM.items():
            atm = TD.atm(sym); d0 = int(TD.exp[sym] == day)
            for m_ in (-2, 0, 2):
                for side, sg in (("CE", 1), ("PE", -1)):
                    grids = {}
                    for w in (1, 5, 30, 60):
                        st = np.arange(S0, S1 - 3 * w * 10, w * 10); K = atm[st] - sg * m_ * c["step"]
                        for Ku in np.unique(K[np.isfinite(K)]):
                            iid = TD.oid(sym, Ku, side)
                            if iid not in grids: grids[iid] = (_vmid(TD, iid, sym), TD.grid(iid))
                            x, G = grids[iid]
                            if x is None: continue
                            s = st[K == Ku]; a, b_, e = x[s], x[s + w * 10], x[s + 2 * w * 10]; sp = (G["ask"] - G["bid"])[s].astype(float)
                            rec.append(pd.DataFrame(dict(day=day, sym=sym, d0=d0, depth=m_, side=side, w=w, dO=b_ - a, dO2=e - b_, dF=fm[s + w * 10] - fm[s], dF2=fm[s + 2 * w * 10] - fm[s + w * 10], sp=sp)))
        print("t4", day, flush=True)
    R = pd.concat(rec).dropna(); R.to_pickle(f"{OBS}/t4_rec_{tag}.pkl"); rows = []
    for (sym, d0, depth, side, w), g in R.groupby(["sym", "d0", "depth", "side", "w"]):
        if len(g) < 500: continue
        beta = np.cov(g.dO, g.dF)[0, 1] / g.dF.var(); res = g.dO - beta * g.dF; res2 = g.dO2 - beta * g.dF2; lo, hi = np.quantile(res, [0.1, 0.9])
        rows.append(dict(sym=sym, d0=d0, depth=depth, side=side, w=w, n=len(g), beta=beta, r2=1 - res.var() / g.dO.var(), res_sd=res.std(), spread_med=g.sp.median(),
                         ar=np.cov(res, res2)[0, 1] / res.var(), catchup=np.cov(g.dO2, g.dF)[0, 1] / g.dF.var() / beta,
                         cheap_next=res2[res <= lo].mean(), rich_next=res2[res >= hi].mean(), cheap_size=res[res <= lo].mean(), days=g.day.nunique()))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/t4_tickdecomp_{tag}.csv", index=False)
    print(f"\n(1/7) tick decomposition against the NIFTY future ({tag}): res_sd and spread in premium points; ar = next-window residual per unit of this one;")
    print("      catchup = share of this window's future move the option makes in the NEXT window; cheap_next = next-window residual after a bottom-decile residual")
    print(T.round(3).to_string(index=False))


def study_t5(days=None):
    """(7) tick pricing: parity gap across strikes at mids against the spread, executable boxes, and stale-quote time by depth."""
    TL = TLm(); rows = []; st_rows = []
    for day in (days or T_OBS):
        TD = TL.TapeDay(day)
        for sym, c in TL.TSYM.items():
            atm = TD.atm(sym); s = np.arange(S0, S1, 10); FK = np.full((5, len(s)), np.nan); HS = FK.copy(); AK = FK.copy(); BK = FK.copy()
            for o in range(-2, 3):
                K = atm[s] + o * c["step"]
                for Ku in np.unique(K[np.isfinite(K)]):
                    gc, gp = TD.grid(TD.oid(sym, Ku, "CE")), TD.grid(TD.oid(sym, Ku, "PE"))
                    if gc is None or gp is None: continue
                    k = K == Ku; sk = s[k]; v = TL._valid(gc, sk, CAPV[sym]) & TL._valid(gp, sk, CAPV[sym])
                    FK[o + 2, k] = np.where(v, Ku + gc["mid"][sk] - gp["mid"][sk], np.nan); HS[o + 2, k] = np.where(v, (gc["ask"][sk] - gc["bid"][sk] + gp["ask"][sk] - gp["bid"][sk]) / 2, np.nan)
                    AK[o + 2, k] = np.where(v, Ku + gc["ask"][sk] - gp["bid"][sk], np.nan); BK[o + 2, k] = np.where(v, Ku + gc["bid"][sk] - gp["ask"][sk], np.nan)   # buy / sell the synthetic at the touch
            with np.errstate(all="ignore"):
                g = FK - np.nanmedian(FK, 0); ok = np.isfinite(g); box = np.nanmax(BK, 0) - np.nanmin(AK, 0)   # sell the dearest synthetic at its bid, buy the cheapest at its ask
            a = np.abs(g[ok]); n5 = ok.sum(0) >= 2
            rows.append(dict(day=day, sym=sym, n=int(ok.sum()), gap_med=np.median(a), gap_p90=np.quantile(a, 0.9), gap_p99=np.quantile(a, 0.99), halfspread_sum_med=np.nanmedian(HS),
                             gap_gt_spread=float((a > HS[ok]).mean()), box_gt0_share=float((box[n5] > 0).mean()), box_gt_cost_share=float((box[n5] > 4 * c["m"] * 0.2).mean()), box_p99=np.nanquantile(box[n5], 0.99)))
            for iid, side, K in _opts(TD, sym):
                G = TD.grid(iid); dep = np.round((atm[S0:S1] - K) / c["step"]) * (1 if side == "CE" else -1); age = G["age"][S0:S1]
                for m_ in DEPTHS:
                    k = dep == m_
                    if k.sum() > 600: st_rows.append((sym, int(m_), k.sum(), (age[k] > 1500).sum(), (age[k] > 5000).sum()))
        print("t5", day, flush=True)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/t5_parity_ticks.csv", index=False)
    print("\n(7) tick parity: gap of each strike's synthetic future (at mids) from the 5-strike median; box = best synthetic bid - best synthetic ask across strikes (> 0 = a free box before charges)")
    print(T.groupby("sym").mean(numeric_only=True).round(3).to_string())
    Z = pd.DataFrame(st_rows, columns=["sym", "depth", "slots", "old1.5", "old5"]).groupby(["sym", "depth"]).sum(); Z["share_older_1.5s"] = Z["old1.5"] / Z.slots; Z["share_older_5s"] = Z["old5"] / Z.slots
    Z.to_csv(f"{OBS}/t5_stale.csv"); print("\n(7) stale quotes: share of session time an option's last tick is older than 1.5 s / 5 s"); print(Z[["share_older_1.5s", "share_older_5s"]].round(3).to_string())


def _cross_day(day):
    """1-minute closes per cross-market instrument (minute of day -> close) from the cross tape."""
    root = os.environ.get("CROSS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/tape/cross")); out = {}
    for name in sorted(os.listdir(root)):
        fp = f"{root}/{name}/{day}.jsonl"
        if not os.path.exists(fp): continue
        r = [json.loads(l) for l in open(fp)]; out[name] = pd.Series({int(x["ts"][11:13]) * 60 + int(x["ts"][14:16]): x["c"] for x in r})
    return out


def study_x1(days=None):
    """(3) cross-market tape (1-minute bars): correlation of each instrument's 1-min return with NIFTY's at lags -3..+3 min."""
    TL = TLm(); acc = {}
    for day in (days or X_OBS):
        TD = TL.TapeDay(day); ltp = TD.grid("NSE_IDX:NIFTY")["ltp"].astype(float); mins = np.arange(560, 920)
        nif = pd.Series(ltp[(mins - 555 + 1) * 600 - 1], index=mins); rn = np.log(nif).diff()
        atm = TD.atm("NIFTY"); st = pd.Series(np.nan, index=mins)
        for K in np.unique(atm[S0:S1][np.isfinite(atm[S0:S1])]):
            c, p_ = _vmid(TD, TD.oid("NIFTY", K, "CE"), "NIFTY"), _vmid(TD, TD.oid("NIFTY", K, "PE"), "NIFTY")
            if c is None or p_ is None: continue
            x = c + p_; e = (mins - 555 + 1) * 600 - 1; k = (atm[e] == K) & (atm[e - 600] == K); st[k] = (x[e] - x[e - 600])[k]
        for name, sr in _cross_day(day).items():
            rx = np.log(sr.reindex(mins)).diff() if name != "INDIAVIX" else sr.reindex(mins).diff()
            for lag in range(-3, 4):
                a = pd.concat([rx.shift(-lag), rn], axis=1).dropna()
                if len(a) > 100 and a.iloc[:, 0].std() > 0: acc.setdefault((name, "NIFTY return"), {}).setdefault(lag, []).append(a.corr().iloc[0, 1])
                if name == "INDIAVIX":
                    a = pd.concat([rx.shift(-lag), st], axis=1).dropna()
                    if len(a) > 100: acc.setdefault((name, "NIFTY ATM straddle change"), {}).setdefault(lag, []).append(a.corr().iloc[0, 1])
    rows = [dict(instrument=n, against=ag, days=len(d[0]), **{f"lag{l:+d}m": float(np.mean(v)) for l, v in sorted(d.items())}) for (n, ag), d in acc.items()]
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/x1_cross_tape.csv", index=False)
    print("\n(3) cross-market tape, 1-min returns; lag > 0 = the cross instrument moves AFTER NIFTY (lag < 0 = it moves first). 3 observe days only.")
    print(T.round(3).to_string(index=False))



# ================================================================ rules from the observations (E56+): pure time-exit trades, scored honestly
def wall_event(f, w, up):
    """first bar (30..299) where F is within 0.10% of the OI wall (same wall for the last 30 bars), on its inner side, after 15 bars further away."""
    for i in range(30, 300):
        K = w[i]
        if not np.isfinite(f[i]) or not (w[i - 30:i + 1] == K).all(): continue
        if abs(f[i] - K) / K <= 0.001 and (np.abs(f[i - 15:i] - K) / K > 0.001).all() and ((f[i] < K) if up else (f[i] > K)): return i
    return None


def wall_events():
    S_ = SL(); F = bar("F"); W = {True: bar("wallC"), False: bar("wallP")}; rows = []
    for d in range(S_.ND):
        for up in (True, False):
            i = wall_event(F[d], W[up][d], up)
            if i is not None: rows.append(("W_call" if up else "W_put", d, i, -1))
    return pd.DataFrame(rows, columns=["type", "d", "i", "dirn"])


def _price(d, i, sg, depth, short, H, fs=1.0, fc=1.0):
    """net Rs at 10 lots per trade (NaN = no valid entry): buy / sell the option `depth` strikes in the money on side sg, time exit after H min."""
    S_ = SL(); G = S_.gather(d, i + 1, depth, sg)
    if short: R = S_.price52_short(G, d, i + 1, 1e9, 1e9, H, fs, fc); x = R["net"] * S_.Q[d]
    else: R = S_.price45(G, d, i + 1, 1e9, 1e9, H, "intrabar", fs, fc); x = R["pnl10"]
    return np.where(R["ok"], x, np.nan), np.where(R["ok"], R["pts"], np.nan)


def score(name, d, i, sg, depth, short, H, runs=200, seed=56, legs2=False, plac="day", fs0=1.0):
    """LEARN and TEST rows for one (rule, index) cell. Trades = arrays (day index, decision bar, option side). Placebo: the same option kind
    and side at the same minute on a random day of the same index, split and expiry flag."""
    S_ = SL(); rows = []; rg = np.random.default_rng(seed); s = S_.SYMI[d[0]]
    for split, tm in (("LEARN", ~S_.ISTEST), ("TEST", S_.ISTEST)):
        k = tm[d]; dd, ii, gg = d[k], i[k], sg[k]; days = np.flatnonzero(tm & (S_.SYMI == s))
        if not len(dd): continue
        def px_(a_, b_, c_, fs=fs0, fc=1.0):   # legs2: the same trade on both sides (a straddle), NaN unless both legs are valid
            x_, p_ = _price(a_, b_, c_, depth, short, H, fs, fc)
            if legs2: y_, q_ = _price(a_, b_, -c_, depth, short, H, fs, fc); x_, p_ = x_ + y_, p_ + q_
            return x_, p_
        x, pts = px_(dd, ii, gg); ok = np.isfinite(x); x2, _ = px_(dd, ii, gg, 2.0 * fs0, 2.0)
        daily = S_._daily(dd[ok], x[ok], days); q = [daily[c].sum() for c in np.array_split(np.arange(len(days)), 4)]
        pool = {e: days[S_.D0[days] == e] for e in (0, 1)}; pd_ = np.array([rg.choice(pool[S_.D0[a]], runs) for a in dd])      # (n, runs)
        if plac == "minute": pd_ = np.repeat(dd[:, None], runs, 1); pi_ = rg.integers(30, 300, pd_.shape).ravel()   # same day, random minute 09:45-14:14
        else: pi_ = np.repeat(ii, runs)
        px, _ = px_(pd_.ravel(), pi_, np.repeat(gg, runs)); pl = np.nansum(px.reshape(len(dd), runs), 0) * (ok.sum() / np.maximum(np.isfinite(px.reshape(len(dd), runs)).sum(0), 1))
        rows.append(dict(rule=name, sym=SYMN[s], split=split, trades=int(ok.sum()), days=len(set(dd[ok])), win=float((x[ok] > 0).mean()), pts=float(np.nanmean(pts)), per_trade=float(x[ok].mean()), net=float(x[ok].sum()),
                         p=S_._pboot(daily), plac_mean=float(pl.mean() / max(ok.sum(), 1)), p_plac=float(((pl >= x[ok].sum()).sum() + 1) / (runs + 1)), net_2x=float(np.nansum(x2)), q_pos=int(sum(v > 0 for v in q)),
                         worst=float(x[ok].min()), maxdd=S_._maxdd(daily)))
    return rows


def _show(T, alpha, title):
    T = T.copy(); L_ = T[T.split == "LEARN"].set_index(["rule", "sym"]).net; T["learn_net"] = [L_.get((r, s_), np.nan) for r, s_ in zip(T.rule, T.sym)]
    T["verdict"] = np.where(T.split != "TEST", "", np.where((T.net > 0) & (T.learn_net > 0) & (T.p < alpha) & (T.p_plac < 0.05) & (T.net_2x > 0) & (T.q_pos >= 3), "PASS", "FAIL"))
    print(title); print(T.drop(columns="learn_net").round({"win": 3, "pts": 2, "per_trade": 0, "net": 0, "p": 4, "plac_mean": 0, "p_plac": 3, "net_2x": 0, "worst": 0, "maxdd": 0}).to_string(index=False)); return T


def lookahead_events(n_days=30, seed=5):
    """perturb every bar after an event's bar and re-detect: the events up to that bar must not change (levels and walls)."""
    S_ = SL(); rg = np.random.default_rng(seed); bad = 0; chk = 0; F = bar("F"); W = {True: bar("wallC"), False: bar("wallP")}
    for d in rg.choice(S_.ND, n_days, replace=False):
        k = S_.DAYK[d]; p = S_.P[k]; f = S_.day_feats(p, k[0]); prev = (np.nanmax(p["spot"]) * 1.001, np.nanmin(p["spot"]) * 0.999, np.nanmean(p["spot"]))
        A = (p["spot"].copy(), f["F"].copy(), f["VW"].copy()); ev = level_events(*A, f["V"], prev, k[0])
        for t, i, sg in ev[::max(1, len(ev) // 6)]:
            B = [a.copy() for a in A]
            for a in B: a[i + 1:] *= rg.uniform(0.98, 1.02, len(a) - i - 1)
            ev2 = level_events(*B, f["V"], prev, k[0]); chk += 1; bad += [e for e in ev if e[1] <= i] != [e for e in ev2 if e[1] <= i]
        for up in (True, False):
            i = wall_event(F[d], W[up][d], up)
            if i is not None:
                f2, w2 = F[d].copy(), W[up][d].copy(); f2[i + 1:] *= 1.01; w2[i + 1:] += 500; chk += 1; bad += wall_event(f2, w2, up) != i
    print(f"look-ahead check on the event detectors: {chk} checks, {bad} changed"); return bad


def e56_cells():
    S_ = SL(); E = all_levels(); W = wall_events(); SYMI = S_.SYMI; cells = []
    def ev(types, s, flip=1):
        g = E[E.type.isin(types) & (SYMI[E.d.values] == s)]; return g.d.values, g.i.values, flip * g.dirn.values
    def wv(types, s):
        g = W[W.type.isin(types) & (SYMI[W.d.values] == s)].sort_values(["d", "i"]); return g.d.values, g.i.values, g.dirn.values
    for s in (0, 1):
        d, i, sg = ev(["L1_PDH", "L1_PDL"], s); cells += [("R1 PDX-BUY ITM2 15m", d, i, sg, 2, False, 15), ("R1c PDX-BUY ATM 15m (control)", d, i, sg, 0, False, 15), ("R2 PDX-SELL opp ATM 15m", d, i, -sg, 0, True, 15)]
    d, i, sg = ev(["L2_round_major"], 0, -1); cells += [("R3 RND-BUY ITM2 15m", d, i, sg, 2, False, 15), ("R3c RND-BUY ATM 15m (control)", d, i, sg, 0, False, 15), ("R4 RND-SELL opp ATM 15m", d, i, -sg, 0, True, 15)]
    for s in (0, 1):
        d, i, sg = wv(["W_call", "W_put"], s); cells += [("R5 WALL-PE ITM2 30m", d, i, sg, 2, False, 30), ("R5c WALL-PE ATM 30m (control)", d, i, sg, 0, False, 30)]
        d, i, sg = wv(["W_call", "W_put"] if s == 0 else ["W_put"], s); cells.append(("R6 WALL-SELL-CE ATM 30m", d, i, -sg, 0, True, 30))
    return cells


def study_e56():
    assert lookahead_events() == 0
    rows = []
    for c in e56_cells(): rows += score(*c)
    T = _show(pd.DataFrame(rows), 0.005, "\nE56: six rules from the E55 observations; Rs at 10 lots, dated costs x1.5; p = day-block bootstrap; alpha 0.005 (controls not counted)")
    T.to_csv(f"{OBS}/e56.csv", index=False)



# ================================================================ loop 2 (E57): deeper looks and their rules
def study_d1():
    """is the previous-day level special? the same first-cross detector on shifted pseudo-levels; ITM2 gross over 15 min, LEARN."""
    S_ = SL(); Sp = bar("S"); LRN = ~S_.ISTEST; PH = np.full(S_.ND, np.nan); PL = PH.copy(); PC = PH.copy(); prev = {}; rows = []
    for d, k in enumerate(S_.DAYK):
        if k[0] in prev: PH[d], PL[d], PC[d] = prev[k[0]]
        if np.isfinite(Sp[d]).any(): prev[k[0]] = (np.nanmax(Sp[d]), np.nanmin(Sp[d]), Sp[d][np.isfinite(Sp[d])][-1])
    def fc(x, lv):
        for i in range(30, 330):
            if x[i] > lv and (x[i - 30:i] <= lv).all(): return i, 1
            if x[i] < lv and (x[i - 30:i] >= lv).all(): return i, -1
    L_ = {"REAL previous-day high / low": lambda d: [PH[d], PL[d]], "previous close": lambda d: [PC[d]], "first-30-min high / low": lambda d: [np.nanmax(Sp[d][:30]), np.nanmin(Sp[d][:30])]}
    for sh in (0.0015, 0.003, 0.005): L_[f"pseudo: outside by {sh * 100:.2f}%"] = lambda d, sh=sh: [PH[d] * (1 + sh), PL[d] * (1 - sh)]; L_[f"pseudo: inside by {sh * 100:.2f}%"] = lambda d, sh=sh: [PH[d] * (1 - sh), PL[d] * (1 + sh)]
    for sh in (0.004, 0.007): L_[f"open +-{sh * 100:.2f}%"] = lambda d, sh=sh: [Sp[d][0] * (1 + sh), Sp[d][0] * (1 - sh)]
    for s in (0, 1):
        for nm, fn in L_.items():
            ev = np.array([(d, *c) for d in np.flatnonzero(LRN & (S_.SYMI == s) & np.isfinite(PH)) for lv in fn(d) for c in [fc(Sp[d], lv)] if c])
            G = S_.gather(ev[:, 0], ev[:, 1] + 1, 2, ev[:, 2]); g = G["C"][:, 14].astype(float) - G["ENT"]; m, t, n, _ = _tclust(g, ev[:, 0])
            rows.append(dict(sym=SYMN[s], level=nm, n=n, ITM2_gross15=m, t=t, win=float(np.nanmean(g[np.isfinite(g)] > 0))))
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/d1_pseudo_levels.csv", index=False); print("\n(D1) real against pseudo levels, LEARN, ITM2 gross premium points over 15 min"); print(T.round(2).to_string(index=False))


def study_d2():
    """how much of the opening crush is left at a real open? seller's gross on a short ATM straddle by entry minute and hold, LEARN."""
    S_ = SL(); LRN = ~S_.ISTEST; dte = _days()[3]; rows = []
    for s in (0, 1):
        for dt_ in (0, 1, 2):
            d = np.flatnonzero(LRN & (S_.SYMI == s) & (dte == dt_))
            for e in (1, 2, 3, 5, 10, 15, 30):
                ee = np.full(len(d), e); Gc = S_.gather(d, ee, 0, np.ones(len(d))); Gp = S_.gather(d, ee, 0, -np.ones(len(d))); cr = Gc["ENT"] + Gp["ENT"]
                r = dict(sym=SYMN[s], dte=dt_, entry=f"{9 + (15 + e) // 60:02d}:{(15 + e) % 60:02d}", n=int(np.isfinite(cr).sum()), credit=np.nanmean(cr))
                for H in (5, 15, 30):
                    g = cr - (Gc["C"][:, H - 1].astype(float) + Gp["C"][:, H - 1]); r[f"g{H}"], r[f"t{H}"] = _tclust(g, d)[:2]
                    if H == 15: r["half1"], r["half2"] = np.nanmean(g[d < np.median(d)]), np.nanmean(g[d >= np.median(d)])
                rows.append(r)
    T = pd.DataFrame(rows); T.to_csv(f"{OBS}/d2_open_crush.csv", index=False); print("\n(D2) seller's gross on a short ATM straddle (premium points, both legs), by entry open and hold, LEARN"); print(T.round(2).to_string(index=False))


BOX_CHG = 0.90   # ponytail: round-number charges for a four-leg box held to expiry (E57 row); replace with the contract-note figure if it ever goes forward


def study_t6(days=None, tag="obs", sym="NIFTY", thr=1.5, fresh=300):
    """(D3 / E57 T1) parity boxes with a full-size walk and latency. Per second: box = max_K synthetic bid - min_K synthetic ask over ATM+-2;
    all cases (box >= thr) and the fresh ones (all four legs <= `fresh` ms old); value 500 / 1,000 ms later on the same two strikes."""
    TL = TLm(); c = TL.TSYM[sym]; q = c["q"]; rows = []
    for day in (days or T_OBS):
        TD = TL.TapeDay(day); atm = TD.atm(sym); s = np.arange(S0, S1 - 20, 10); r = np.arange(len(s))
        def legs(sl):
            B = np.full((5, len(sl)), np.nan); A = B.copy(); AG = B.copy()
            for o in range(-2, 3):
                K = atm[s] + o * c["step"]                      # strikes fixed at the decision slot
                for Ku in np.unique(K[np.isfinite(K)]):
                    gc, gp = TD.grid(TD.oid(sym, Ku, "CE")), TD.grid(TD.oid(sym, Ku, "PE"))
                    if gc is None or gp is None: continue
                    k = K == Ku; sk = sl[k]; v = TL._valid(gc, sk, CAPV[sym]) & TL._valid(gp, sk, CAPV[sym])
                    B[o + 2, k] = np.where(v, Ku + TL._walk(gc, sk, q, False) - TL._walk(gp, sk, q, True), np.nan); A[o + 2, k] = np.where(v, Ku + TL._walk(gc, sk, q, True) - TL._walk(gp, sk, q, False), np.nan)
                    AG[o + 2, k] = np.where(v, np.maximum(gc["age"][sk], gp["age"][sk]), np.nan)
            return B, A, AG
        B0, A0, AG0 = legs(s); ok = np.isfinite(B0).sum(0) >= 2; ib = np.argmax(np.where(np.isfinite(B0), B0, -1e18), 0); ia = np.argmin(np.where(np.isfinite(A0), A0, 1e18), 0)
        box0 = B0[ib, r] - A0[ia, r]; age = np.maximum(AG0[ib, r], AG0[ia, r]); after = {}
        for lat in (5, 10): B1, A1, _ = legs(s + lat); after[lat] = B1[ib, r] - A1[ia, r]
        for kind, m in (("all", ok & (box0 >= thr)), ("fresh", ok & (box0 >= thr) & (age <= fresh))):
            m = m & np.isfinite(after[5]) & np.isfinite(after[10]); keep = []; last = -10 ** 9
            for j in np.flatnonzero(m):
                if j - last >= 30: keep.append(j); last = j
            for j in keep: rows.append((day, kind, s[j], box0[j], after[5][j], after[10][j], age[j]))
        print("t6", day, flush=True)
    T = pd.DataFrame(rows, columns=["day", "kind", "slot", "box", "a500", "a1000", "age"]); T.to_csv(f"{OBS}/t6_box_{tag}.csv", index=False)
    Z = T.groupby(["kind", "day"]).agg(n=("box", "size"), box=("box", "mean"), after_500ms=("a500", "mean"), after_1000ms=("a1000", "mean"), share_above_charges=("a500", lambda x: (x > BOX_CHG).mean()))
    Z["net_500"] = Z.after_500ms - BOX_CHG; Z["net_1000"] = Z.after_1000ms - BOX_CHG
    print(f"\n(E57 T1) {sym} parity box >= {thr} ({tag} days); charges taken as {BOX_CHG} per unit"); print(Z.round(3).to_string())
    P_ = T.groupby("kind").agg(n=("box", "size"), box=("box", "mean"), after_500ms=("a500", "mean"), after_1000ms=("a1000", "mean"), share_above_charges=("a500", lambda x: (x > BOX_CHG).mean())); print(P_.round(3).to_string()); return T


def open_cost(days=None):
    """E57 tape action rule: measured entry cost per ATM leg at 09:16:00-09:16:05 (half-spread and the 10-lot walk for a SALE)."""
    TL = TLm(); rows = []
    for day in (days or T_OBS):
        TD = TL.TapeDay(day)
        for sym, c in TL.TSYM.items():
            K = TD.atm(sym)[600]
            for side in ("CE", "PE"):
                G = TD.grid(TD.oid(sym, K, side)) if np.isfinite(K) else None
                if G is None: continue
                sl = np.arange(600, 651); v = TL._valid(G, sl, 1e9)
                if v.sum() < 5: continue
                rows.append(dict(day=day, sym=sym, d0=int(TD.exp[sym] == day), side=side, mid=float(np.nanmedian(G["mid"][sl][v])), half_spread=float(np.nanmedian((G["ask"] - G["bid"])[sl][v]) / 2),
                                 walk_cost=float(np.nanmedian((G["mid"][sl] - TL._walk(G, sl, c["q"], False))[v]))))
    return pd.DataFrame(rows)


def study_e57():
    S_ = SL(); dte = np.array([S_.P[k]["dte"] for k in S_.DAYK]); rows = []
    C = open_cost(); print("\nE57 tape action rule: ATM legs at 09:16:00-09:16:05 on the OBSERVE days (premium points per leg)"); print(C.round(3).to_string(index=False))
    for name, s, dm in (("S1 OPEN-CRUSH NIFTY dte<=1", 0, dte <= 1), ("S2 OPEN-CRUSH SENSEX dte>=2", 1, dte >= 2)):
        d = np.flatnonzero((S_.SYMI == s) & dm); i = np.zeros(len(d), int); sg = np.ones(len(d), int)
        Gc = S_.gather(d[S_.ISTEST[d]], np.ones(int(S_.ISTEST[d].sum()), int), 0, np.ones(int(S_.ISTEST[d].sum()))); model = float(np.nanmean(S_.hsv(d[S_.ISTEST[d]], S_.M0 + 1, np.nan_to_num(Gc["ENT"], nan=1.0))))
        cs = C[(C.sym == SYMN[s]) & ((C.d0 == 1) if s == 0 else (C.d0 == 0))]; meas = float(cs.walk_cost.mean()) if len(cs) else np.nan; lim = 0.25 if s == 0 else 0.75
        print(f"{name}: modelled p75 half-spread per leg at 09:16 (TEST year) {model:.2f}; measured 10-lot sale cost per leg on the tape {meas:.2f} ({len(cs)} legs); re-price if measured - model > {lim}")
        rows += score(name, d, i, sg, 0, True, 15, legs2=True, plac="minute", seed=57)
        if np.isfinite(meas) and meas - model > lim: rows += score(name + f" RE-PRICED x{meas / model:.1f} spread", d, i, sg, 0, True, 15, legs2=True, plac="minute", seed=57, fs0=meas / model)
    T = _show(pd.DataFrame(rows), 0.025, "\nE57 S1 / S2: short ATM straddle at the 09:16 open, bought back after 15 min; Rs at 10 lots; placebo = the same straddle at a random minute of the same day")
    T.to_csv(f"{OBS}/e57.csv", index=False)



# ================================================================ selftest
def selftest():
    # Black-76 round trip and put-call parity
    F, K, T = 25000.0, np.array([24800.0, 25000.0, 25300.0]), 3 * 1440 / 525600.0
    c, _ = b76(F, K, T, 0.14, True); p, _ = b76(F, K, T, 0.14, False); assert np.allclose(c - p, F - K) and np.allclose(iv76(c, F, K, T, True), 0.14, atol=1e-5) and np.allclose(iv76(p, F, K, T, False), 0.14, atol=1e-5)
    assert np.isnan(iv76(np.array([150.0]), F, np.array([24800.0]), T, True))[0]                                     # below intrinsic -> NaN
    # decomposition known answer: a pure time step (F and sigma fixed) is all theta; a pure small F step is all spot (to second order)
    NB = 20; Fv = np.full(NB, 25000.0); Tv = (3 * 1440 - np.arange(NB)) / 525600.0; sK = np.full((3, NB), 0.14); sA = np.full(NB, 0.14)
    px = b76(Fv, K[:, None], Tv, sK, True)[0]; dP, sp, cv, ov, th, de, ve = decompose(Fv, K, Tv, sK, sA, px, True, 5)
    assert np.allclose(dP[:, :15], th[:, :15], atol=1e-9) and np.allclose(sp[:, :15], 0) and np.allclose(cv[:, :15], 0) and (th[:, :15] < 0).all()
    Fv2 = 25000.0 + 2.0 * np.arange(NB); Tc = np.full(NB, 3 * 1440 / 525600.0); px2 = b76(Fv2, K[:, None], Tc, sK, True)[0]; dP, sp, cv, ov, th, de, ve = decompose(Fv2, K, Tc, sK, sA, px2, True, 1)
    assert np.abs(dP[:, :19] - sp[:, :19]).max() < 1e-3 and np.allclose(th[:, :19], 0) and 0.45 < de[1, 0] < 0.56
    sA2 = 0.14 + 0.001 * np.arange(NB); sK2 = np.tile(sA2, (3, 1)); px3 = b76(Fv, K[:, None], Tc, sK2, True)[0]; dP, sp, cv, ov, th, de, ve = decompose(Fv, K, Tc, sK2, sA2, px3, True, 1)
    assert np.abs(dP[:, :19] - cv[:, :19]).max() < 0.02 and np.allclose(ov[:, :19], 0, atol=1e-9)                     # a parallel vol move is all common vol
    # level events on a hand-built day (NIFTY, 1m closes): flat 25,040, rally through 25,100 at bar 100 (round-number touch from below -> theory -1),
    S = np.full(375, 25040.0); S[100:] = 25110.0; ev = level_events(S, S, S - 1, np.ones(375), (25300.0, 24900.0, 25050.0), "NIFTY")
    assert ("L2_round_minor", 100, -1) in ev and ("L3_OR_break", 100, 1) in ev and ("L1_PDC", 100, 1) in ev, ev
    # sweep: swing high 25,060 at 5m bar 10 (1m bars 50-54), later bar 30 spikes to 25,070 and closes back at 25,040 -> short reversal at 1m bar 154
    S = np.full(375, 25040.0); S[52] = 25060.0; S[151] = 25070.0; ev = level_events(S, S, S - 1, np.ones(375), None, "NIFTY"); assert ("L5_sweep", 154, -1) in ev, ev
    # fair value gap: 5m bars 20, 21, 22 step up 25,000 -> 25,020 -> 25,040 (bar 22's low is above bar 20's high), then 25,050; price returns to 25,035 in bar 30 -> long at 1m bar 154
    S = np.full(375, 25000.0); S[105:110] = 25020.0; S[110:115] = 25040.0; S[115:] = 25050.0; S[150:155] = 25035.0; ev = level_events(S, S, S - 1, np.ones(375), None, "NIFTY"); assert ("L6_FVG", 154, 1) in ev, ev
    # order block: small bodies, a down bar at 5m bar 39, a displacement up bar at 40 (new 10-bar high), price returns into bar 39's range at bar 45 -> long at 1m bar 229
    S = 25000.0 + np.tile([0, 1, 0, 1, 0], 75).astype(float); S[195:200] = [25000, 24999, 24998, 24997, 24996]; S[200:205] = [24996, 25010, 25020, 25030, 25040]; S[205:] = 25040.0; S[225:230] = 24998.0
    ev = level_events(S, S, S - 1, np.ones(375), None, "NIFTY"); assert ("L7_order_block", 229, 1) in ev, ev
    assert _tclust([1.0, 1.0, 3.0, 3.0, 2.0, 2.0], [0, 0, 1, 1, 2, 2])[0] == 2.0
    # OI wall approach: wall 25,100 all day; F sits 60 points below, then walks to 25,080 (within 0.10%) at bar 120 -> event at 120; a wall that changed 10 bars ago does not fire
    f = np.full(375, 25040.0); f[120:] = 25080.0; w = np.full(375, 25100.0); assert wall_event(f, w, True) == 120 and wall_event(f, w, False) is None
    w2 = w.copy(); w2[:110] = 25200.0; assert wall_event(f, w2, True) is None
    print("observe_lab selftest OK (Black-76 round trip, decomposition known answers, level / ICT detectors on hand-built days)")


if __name__ == "__main__":
    for s_ in [a for a in sys.argv[2:] if not a.startswith("-")]: (selftest if s_ == "selftest" else globals()["study_" + s_])()
