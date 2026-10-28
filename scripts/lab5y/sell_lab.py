"""Round 4: defined-risk option SELLING on the round-2 panel (paper research; no orders).
Run:  ~/paper_extra_venv/bin/python scripts/lab5y/sell_lab.py OUT [grid|e16e17|selftest] [--holdout]   (run from scripts/lab5y)
Reuses opt1y_lab (panel, half-spreads, costs x1.5, 10 lots, dev < 2026-07-27, holdout once).

Position = legs (side, strike offset in steps from ATM at bar i, sign -1 short / +1 long), entered at the open of bar i+1:
short legs sell at open - half-spread, long legs buy at open + half-spread. Every minute the position is marked at the
1m close; exits (stop / target / spot move) are decided on that close and filled at the NEXT open with half-spreads;
otherwise flat at 15:15 open. Intraday only (no overnight gap risk).
A leg with no quote has left the taped ATM+-3 window (Dhan rollingoption rejects ATM+-4..10 for expiryCode=1, checked
2026-10-28: 728/728 calls refused), so it is further from ATM than every taped strike. Its price is bounded:
  low = intrinsic, high = intrinsic + the extrinsic (clipped at 0) of the nearest taped strike of that type.
mode="cons" values shorts at high and longs at low (a rule must pass this); mode="opt" is the reverse.
A short structure's buy-back value is then clamped to [0, widest wing], the hard max loss of an iron fly / condor."""
import sys, glob, math, os, numpy as np, pandas as pd
import opt1y_lab as L

P, STEP, LOT, LOTS, M0, NB, FLAT = L.P, L.STEP, L.LOT, L.LOTS, L.M0, L.NB, L.FLAT


_EXT = {}
def _nearext(k, side, K, j, col):
    """extrinsic (clipped at 0) of the taped strike of this type nearest to K at minute j: an upper bound for K, which
    is further from ATM (audit 2026-10-28: the old min() over all strikes hit 0 when one stale quote was below intrinsic)."""
    key = (k, side, K, j, col)
    if key not in _EXT:
        s = P[k]["spot"][j]; xs = [(abs(KK - K), a[j, col] - (max(0.0, s - KK) if side == "CE" else max(0.0, KK - s)))
                                   for (sd, KK), a in P[k]["C"].items() if sd == side and np.isfinite(a[j, col])]
        # audit A2: a tie in distance (a data hole with taped strikes on both sides) takes the LARGER extrinsic
        _EXT[key] = max(0.0, max(e for d, e in xs if d == min(xs)[0])) if xs else 0.0
    return _EXT[key]


def _px(k, side, K, j, col, high):
    """quote, or a bound when the strike is off the taped window: high=True -> upper bound, else lower bound."""
    a = P[k]["C"].get((side, K)); j = min(j, NB - 1); s = P[k]["spot"][j]
    v = a[j, col] if a is not None else np.nan
    if np.isfinite(v): return v, False
    intr = max(0.0, s - K) if side == "CE" else max(0.0, K - s)
    return intr + (_nearext(k, side, K, j, col) if high else 0.0), True


def _cost(b, s, sym, lots):
    """L.cost is for LOTS lots; its 40/order brokerage (x1.18 GST x CM) is fixed, the rest scales with lots."""
    fx = L.CM * 1.18 * 40; return fx + (L.cost(b, s, sym) - fx) * lots / LOTS


def struct(k, i, legs, stop=None, tgt=None, sstop=None, flat=FLAT, mode="cons", dirn=0, s_tgt=None, s_stp=None, trail=None,
           lots=LOTS):
    """legs: [(side, off, sign)]. stop: exit when buy-back value - credit >= stop * credit. tgt: exit when value <= (1-tgt) * credit.
    sstop: exit when |spot - entry spot| >= sstop * STEP. Directional (dirn=+1 up / -1 down): exit when the signed spot
    move reaches +s_tgt steps or -s_stp steps. trail (E14): m = |marked value|; a credit position exits when m >= its
    lowest m since entry * (1+trail), a debit position when m <= its highest m * (1-trail). flat: exit at the open of
    minute `flat` (time exit). Returns dict or None."""
    sym = k[0]; p = P[k]; d0 = p["d0"]; e = i + 1; xe = flat - M0
    if e >= xe: return None
    atm = p["atm"][i]; L_ = [(sd, atm + off * STEP[sym], sg) for sd, off, sg in legs]
    ent = []
    for sd, K, sg in L_:
        a = p["C"].get((sd, K))
        if a is None or not np.isfinite(a[e, 0]): return None
        o = a[e, 0]; h = L.hs(sym, d0, M0 + e, o); ent.append(o - h if sg < 0 else o + h)
    credit = sum(-sg * x for (sd, K, sg), x in zip(L_, ent))
    if credit <= 0 and all(sg < 0 for _, _, sg in L_): return None
    shorts = [K for sd, K, sg in L_ if sg < 0]; longs = [(sd, K) for sd, K, sg in L_ if sg > 0]
    W = max(abs(K - min(shorts, key=lambda s: abs(s - K))) for sd, K in longs) if shorts and longs else np.inf
    s0 = p["spot"][e]; hi = lambda sg: (sg < 0) == (mode == "cons")  # cons: shorts high, longs low
    why = "time"; jx = xe; forced = False; best = None
    for j in range(e, xe):
        val = 0.0
        for sd, K, sg in L_:
            v, miss = _px(k, sd, K, j, 3, hi(sg)); val += -sg * v
        if np.isfinite(W): val = min(max(val, 0.0), W)
        if stop is not None and val - credit >= stop * credit: why, jx = "stop", j + 1; break
        if tgt is not None and val <= (1 - tgt) * credit: why, jx = "tgt", j + 1; break
        if sstop is not None and abs(p["spot"][j] - s0) >= sstop * STEP[sym]: why, jx = "spot", j + 1; break
        mv = dirn * (p["spot"][j] - s0) / STEP[sym]
        if dirn and s_tgt is not None and mv >= s_tgt: why, jx = "s_tgt", j + 1; break
        if dirn and s_stp is not None and mv <= -s_stp: why, jx = "s_stp", j + 1; break
        if trail is not None:
            m = abs(val); best = m if best is None else (min(best, m) if credit > 0 else max(best, m))
            if (m >= best * (1 + trail)) if credit > 0 else (m <= best * (1 - trail)): why, jx = "trail", j + 1; break
    jx = min(jx, NB - 1); out = 0.0; costs = 0.0; q = LOT[sym] * lots
    for (sd, K, sg), x in zip(L_, ent):
        v, miss = _px(k, sd, K, jx, 0, hi(sg)); forced = forced or miss
        fill = v + L.hs(sym, d0, M0 + jx, max(v, 0.05)) if sg < 0 else max(v - L.hs(sym, d0, M0 + jx, max(v, 0.05)), 0.05)
        out += -sg * fill
        costs += _cost(fill, x, sym, lots) if sg < 0 else _cost(x, fill, sym, lots)
    if forced and np.isfinite(W): out = min(max(out, 0.0), W)  # a bound was used: keep it inside the payoff's limits
    pnl = (credit - out) * q - costs
    if not np.isfinite(pnl): return None  # spot or quote missing at entry/exit
    return dict(sym=sym, day=k[1], i=i, dte=p["dte"], d0=d0, credit=credit, pnl=pnl, why=why, held=jx - e, forced=forced,
                maxloss=(W - credit) * q if np.isfinite(W) else np.nan)


# ---------------------------------------------------------------- structures (offsets in strike steps)
def ifly(w): return [("CE", 0, -1), ("PE", 0, -1), ("CE", w, 1), ("PE", -w, 1)]
def icon(s, w): return [("CE", s, -1), ("PE", -s, -1), ("CE", w, 1), ("PE", -w, 1)]
SSTRAD = [("CE", 0, -1), ("PE", 0, -1)]; LSTRAD = [("CE", 0, 1), ("PE", 0, 1)]
STRUCTS = {"short_strad": SSTRAD, "ifly3": ifly(3), "long_strad": LSTRAD}
ENTRY = {"09:20": 5, "09:46": 31, "10:30": 75, "11:30": 135, "13:00": 225, "14:00": 285}
# spot stops <= 2.5 steps keep ATM legs inside the taped +-3 window (no bounds needed for straddles)
EXITS = {f"spot{s}": dict(sstop=s) for s in (1, 1.5, 2, 2.5)}
EXITS.update({f"spot2_stop{x}": dict(sstop=2, stop=x) for x in (0.3, 0.6)})
EXITS.update({f"spot2_tgt{x}": dict(sstop=2, tgt=x) for x in (0.3, 0.5)})


def run(keys, legs, i, ex, mode="cons"):
    R = [struct(k, i, legs, mode=mode, **ex) for k in keys]; return pd.DataFrame([r for r in R if r])


def summ(D):
    if not len(D): return dict(n=0)
    g = D.groupby("day").pnl.sum(); mo = D.groupby(D.day.map(L.month)).pnl.sum()
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    b = np.random.default_rng(5).choice(g.values, (5000, len(g))).mean(1)
    return dict(n=len(D), win=round((D.pnl > 0).mean() * 100), avg=round(D.pnl.mean()), total=round(D.pnl.sum()),
                worst=round(D.pnl.min()), maxdd=round((g.cumsum() - g.cumsum().cummax().clip(lower=0)).min()), t=round(t, 2),
                p_boot=round((b <= 0).mean(), 4), mpos=f"{(mo > 0).sum()}/{len(mo)}",
                NIFTY=round(D[D.sym == "NIFTY"].pnl.sum()), SENSEX=round(D[D.sym == "SENSEX"].pnl.sum()),
                ret_ml=round(D.pnl.sum() / D.maxloss.mean() * 100, 1), forced=round(D.forced.mean() * 100, 1))


def study_grid():
    """every structure x entry x exit on dev, all days. The point is the SURFACE (robust region), not the max cell."""
    rows = []
    for sn, legs in STRUCTS.items():
        for en, i in ENTRY.items():
            for xn, ex in EXITS.items():
                if sn == "long_strad" and ("stop" in xn or "tgt" in xn): continue  # credit-based exits are for sellers
                D = run(L.KEYS, legs, i, ex); r = dict(struct=sn, entry=en, exit=xn, **summ(D)); rows.append(r)
                print(r, flush=True)
    R = pd.DataFrame(rows); R.to_csv(f"{L.OUT}/sell_grid_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250); print(R.to_string(index=False))


# ---------------------------------------------------------------- E5 directional buying with spot exits (registry E5)
OR_END, LAST = 30, 165  # opening range 09:15-09:45; signals 09:46..12:00
E5X = {f"t{t}_s{st}": dict(s_tgt=t, s_stp=st) for t in (1, 1.5, 2) for st in (0.5, 1)}


def orb_signals(k, fade=False):
    """first close outside the 09:15-09:45 range (bars 0..30) from bar 31 to 165 -> (i, side). fade: that break
    closes back inside within 15 bars -> the other side at the close that re-enters. One signal per day."""
    s = P[k]["spot"]; hi, lo = np.nanmax(s[:OR_END + 1]), np.nanmin(s[:OR_END + 1])
    for i in range(OR_END + 1, LAST + 1):
        up, dn = s[i] > hi, s[i] < lo
        if not (up or dn): continue
        if not fade: return [(i, "CE" if up else "PE")]
        for j in range(i + 1, min(i + 16, LAST + 1)):
            if lo <= s[j] <= hi: return [(j, "PE" if up else "CE")]
        return []
    return []


def rand_pool(keys, ex, n=12, seed=3, how="atm", mode="cons"):
    """per day: n random (minute 31..165, side) entries with the same legs (e5_legs how), mode and exits -> pnl per day key
    (audit A2: was always a long ATM option in cons, even for the itm1 / credit-spread / opt rules)."""
    rg = np.random.default_rng(seed); out = {}
    for k in keys:
        v = []
        for i, sd in zip(rg.integers(OR_END + 1, LAST + 1, n), rg.integers(0, 2, n)):
            r = struct(k, int(i), e5_legs("CE" if sd == 0 else "PE", how), dirn=1 if sd == 0 else -1, mode=mode, **ex)
            if r: v.append(r["pnl"])
        out[k] = v
    return out


def e5_legs(sd, how):
    """sd = the side the fade bets on (CE = up). how: atm (buy ATM), itm1 (buy 1 step ITM), cs (sell a credit spread
    on the OTHER side: short ATM of the breakout side + long 2 steps further out)."""
    if how == "atm": return [(sd, 0, 1)]
    if how == "itm1": return [(sd, -1 if sd == "CE" else 1, 1)]
    o = "PE" if sd == "CE" else "CE"; w = 2 if o == "CE" else -2
    return [(o, 0, -1), (o, w, 1)]


def e5(fade, how="atm", mode="cons"):
    rows = []
    for xn, ex in E5X.items():
        T = []
        for k in L.KEYS:
            for i, sd in orb_signals(k, fade):
                r = struct(k, i, e5_legs(sd, how), dirn=1 if sd == "CE" else -1, mode=mode, **ex)
                if r: T.append(dict(r, key=k))
        D = pd.DataFrame(T); rp = rand_pool(L.KEYS, ex, how=how, mode=mode); flat = np.concatenate([v for v in rp.values() if v])
        rg = np.random.default_rng(9); tot = D.pnl.sum()
        rnd = np.array([sum(rg.choice(rp[k]) if rp[k] else 0 for k in D.key) for _ in range(2000)])
        r = dict(rule=("fade" if fade else "orb") + "_" + how + ("" if mode == "cons" else "_opt"), exit=xn, **summ(D), rand_avg=round(flat.mean()), p_vs_rand=round((rnd >= tot).mean(), 4),
                 why=D.why.value_counts().to_dict())
        rows.append(r); print(r, flush=True)
    return rows


def study_e5b():
    R = pd.DataFrame(e5(True, "itm1") + e5(True, "cs") + e5(True, "cs", "opt")); R.to_csv(f"{L.OUT}/e5b_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["rule", "exit", "n", "win", "avg", "total", "t", "p_boot", "mpos", "p_vs_rand", "NIFTY", "SENSEX", "worst", "forced"]].to_string(index=False))


def study_e5():
    R = pd.DataFrame(e5(False) + e5(True)); R.to_csv(f"{L.OUT}/e5_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["rule", "exit", "n", "win", "avg", "total", "t", "p_boot", "mpos", "rand_avg", "p_vs_rand", "NIFTY", "SENSEX", "forced"]].to_string(index=False))


# ---------------------------------------------------------------- E6 can the regime be predicted before 09:46? (registry E6)
E6F = ["or_iv", "gap_iv", "prev_iv", "har_iv", "ivpct", "dte", "orw", "vix", "aspx", "ainr", "a_fii_fut", "a_fii_opt", "spx", "fii_fut"]


def e6_table():
    V = L.vol_days().merge(L.ext_table(), on="day", how="left")
    V["a_fii_fut"], V["a_fii_opt"] = V.fii_fut.abs(), V.fii_opt.abs()
    rest = {}
    for k in L.ALLK:  # realized vol 09:46 -> 15:15 on spot, annualised like rv_or
        sp = P[k]["spot"][31:FLAT - M0 + 1]; r = np.diff(np.log(sp)); r = r[np.isfinite(r)]
        rest[k] = np.sqrt((r ** 2).sum() * 252 * 375 / max(len(r), 1)) * 100
    V["rv_rest"] = [rest.get((a, b), np.nan) for a, b in zip(V.sym, V.day)]
    V["y_ratio"] = V.rv_rest / V.iv
    return V


def _auc(y, s):
    o = np.argsort(s); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan


def study_e6():
    V = e6_table().dropna(subset=["y_ratio"]); V["mo"] = V.day.map(L.month)
    dev, ho = V[V.day < L.HO].copy(), V[V.day >= L.HO].copy()
    print("rest-of-day RV/IV median dev %.2f holdout %.2f" % (dev.y_ratio.median(), ho.y_ratio.median()))
    med = dev.y_ratio.median()  # y = 1 when the rest of the day moves more than the dev median of RV/IV
    for D in (dev, ho): D["y"] = (D.y_ratio > med).astype(int)
    print("share of moving days: dev %.2f holdout %.2f" % (dev.y.mean(), ho.y.mean()))
    print("single-feature AUC (dev | holdout), Spearman with RV/IV (dev | holdout):")
    for f in E6F:
        a, b = dev.dropna(subset=[f]), ho.dropna(subset=[f])
        print(f"  {f:10s} AUC {_auc(a.y.values, a[f].values):.3f} | {_auc(b.y.values, b[f].values):.3f}   rho "
              f"{a[f].corr(a.y_ratio, method='spearman'):+.3f} | {b[f].corr(b.y_ratio, method='spearman'):+.3f}")
    # walk-forward logistic (standardised, L2) on all features: train on prior months, score the next month
    from numpy.linalg import solve
    def fit(X, y, lam=1.0):
        w = np.zeros(X.shape[1])
        for _ in range(50):
            pr = 1 / (1 + np.exp(-X @ w)); g = X.T @ (pr - y) + lam * w; Hs = X.T @ (X * (pr * (1 - pr))[:, None]) + lam * np.eye(len(w))
            w -= solve(Hs, g)
        return w
    F = [f for f in E6F if f != "dte"] ; Z = V.dropna(subset=F).copy()
    sc = []
    for m in sorted(Z.mo.unique())[2:]:
        tr = Z[(Z.mo < m) & (Z.day < L.HO)]; te = Z[Z.mo == m]
        mu, sd = tr[F].mean(), tr[F].std() + 1e-9
        X = np.c_[np.ones(len(tr)), ((tr[F] - mu) / sd).values]; w = fit(X, (tr.y_ratio > med).astype(int).values)
        te = te.assign(score=np.c_[np.ones(len(te)), ((te[F] - mu) / sd).values] @ w); sc.append(te)
    S = pd.concat(sc); S["y"] = (S.y_ratio > med).astype(int); S.to_pickle(f"{L.OUT}/e6_scores.pkl")
    for nm, G in (("dev (walk-forward)", S[S.day < L.HO]), ("holdout (trained on dev only)", S[S.day >= L.HO])):
        print(f"logistic all features AUC {nm}: {_auc(G.y.values, G.score.values):.3f}  n={len(G)}")
    print("logistic weights (last fit):", dict(zip(["c"] + F, np.round(w, 2))))


# ---------------------------------------------------------------- E7 short-straddle P&L by regime score (registry E7)
def study_e7():
    """S1 trade (short ATM straddle 09:47, 2-step spot exit, else 15:15) on every day, all months, both bound modes;
    bucket by the E6 walk-forward score: quintile cut points from DEV scores only, applied to dev and holdout."""
    S = pd.read_pickle(f"{L.OUT}/e6_scores.pkl")
    keys = [(a, b) for a, b in zip(S.sym, S.day) if (a, b) in P]
    out = {}
    for mode in ("cons", "opt"):
        R = pd.DataFrame([r for r in (struct(k, 31, SSTRAD, sstop=2, mode=mode) for k in keys) if r])
        out[mode] = R.set_index(["sym", "day"]).pnl
    S = S.set_index(["sym", "day"]).assign(cons=out["cons"], opt=out["opt"]).dropna(subset=["cons"]).reset_index()
    cuts = S[S.day < L.HO].score.quantile([0.2, 0.4, 0.6, 0.8]).values
    S["q"] = np.searchsorted(cuts, S.score) + 1
    for nm, G in (("DEV", S[S.day < L.HO]), ("HOLDOUT", S[S.day >= L.HO])):
        t = G.groupby("q").agg(n=("cons", "size"), avg_cons=("cons", "mean"), avg_opt=("opt", "mean"), total=("cons", "sum"),
                               win=("cons", lambda x: (x > 0).mean() * 100), rv_iv=("y_ratio", "median"))
        print(nm, "(q1 = calmest predicted, q5 = most moving)"); print(t.round(0).to_string())
        lo = G[G.q == 1]; print(f"  q1 only: {summ(lo.assign(pnl=lo.cons, why='', forced=False, maxloss=np.nan))}")
    S.to_pickle(f"{L.OUT}/e7_days.pkl")


# ---------------------------------------------------------------- E8 predict the short-straddle P&L itself (registry E8)
def study_e8():
    S = pd.read_pickle(f"{L.OUT}/e7_days.pkl"); F = [f for f in E6F if f != "dte"] + ["dte", "iv"]
    S = S.dropna(subset=F + ["cons"]).copy(); S["mo"] = S.day.map(L.month); S["y"] = (S.cons > 0).astype(int)
    print("single-feature AUC for 'S1 wins' (dev | holdout):")
    dv, ho = S[S.day < L.HO], S[S.day >= L.HO]
    print("  " + "  ".join(f"{f} {_auc(dv.y.values, dv[f].values):.2f}|{_auc(ho.y.values, ho[f].values):.2f}" for f in F))
    from numpy.linalg import solve
    sc = []
    for m in sorted(S.mo.unique())[2:]:
        tr = S[(S.mo < m) & (S.day < L.HO)]; te = S[S.mo == m]; mu, sd = tr[F].mean(), tr[F].std() + 1e-9
        X = np.c_[np.ones(len(tr)), ((tr[F] - mu) / sd).values]; y = tr.y.values; w = np.zeros(X.shape[1])
        for _ in range(50):
            pr = 1 / (1 + np.exp(-X @ w)); w -= solve(X.T @ (X * (pr * (1 - pr))[:, None]) + 3 * np.eye(len(w)), X.T @ (pr - y) + 3 * w)
        sc.append(te.assign(p=np.c_[np.ones(len(te)), ((te[F] - mu) / sd).values] @ w))
    Z = pd.concat(sc)
    for nm, G in (("dev walk-forward", Z[Z.day < L.HO]), ("holdout (dev-trained)", Z[Z.day >= L.HO])):
        top = G[G.p > G.p.median()]
        print(f"logistic AUC {nm}: {_auc(G.y.values, G.p.values):.3f} n={len(G)} | trade top half: n={len(top)} total {top.cons.sum():,.0f} "
              f"vs all {G.cons.sum():,.0f}")


# ---------------------------------------------------------------- E12-E14 (registry; rules frozen before any result)
def _iv(k, b):
    """mean ATM CE/PE implied vol at bar b (ATM of that bar)."""
    K = P[k]["atm"][b]; return np.nanmean([L._get(k, "CE", K, b, 5), L._get(k, "PE", K, b, 5)])


def _vega(k, b):
    """ATM straddle vega per lot per IV point at bar b: 2 * S * sqrt(T) * phi(0) / 100, T to 15:30 of expiry."""
    p = P[k]; T = (p["dte"] + (930 - M0 - b) / 375) / 252; return 2 * p["spot"][b] * np.sqrt(T) * 0.3989 / 100 * LOT[k[0]]


def _size(vN, vS):
    """whole lots 1..10 each, closest vega match; ties -> more lots."""
    return min((abs(a * vN - b * vS) / max(a * vN, b * vS), -(a + b), a, b) for a in range(1, 11) for b in range(1, 11))[2:]


def _pboot(g, n=20000):
    return round((np.random.default_rng(5).choice(g, (n, len(g))).mean(1) <= 0).mean(), 4)


E12_I = 31  # decide at 09:46 close, fill 09:47 open (same as S1)


def e12_table():
    """per day with both panels: x = log(IV_S / IV_N); r = x minus the mean x of ALL PRIOR days with the same
    (dte_N, dte_S) pair (>= 4 obs: NIFTY expires Tue, SENSEX Thu); z = r vs the prior 20 r. Strictly prior data."""
    days = sorted({d for s, d in L.ALLK if ("NIFTY", d) in P and ("SENSEX", d) in P})
    V = pd.DataFrame([dict(day=d, x=np.log(_iv(("SENSEX", d), E12_I) / _iv(("NIFTY", d), E12_I)),
                           pair=(P[("NIFTY", d)]["dte"], P[("SENSEX", d)]["dte"]),
                           vN=_vega(("NIFTY", d), E12_I), vS=_vega(("SENSEX", d), E12_I)) for d in days])
    V["r"] = V.x - V.groupby("pair").x.transform(lambda x: x.shift(1).expanding(4).mean())
    V = V.dropna(subset=["r"]).reset_index(drop=True); pr = V.r.shift(1).rolling(20)
    V["z"] = (V.r - pr.mean()) / pr.std(); return V.dropna(subset=["z"])


def e12_pair(d, short_s, nN, nS, mode="cons"):
    """short the rich index's ATM straddle, long the cheap one's; both exit at the next open after the first close
    where EITHER spot moved >= 2 steps from its entry spot, else 15:15."""
    n, s = ("NIFTY", d), ("SENSEX", d); e = E12_I + 1; jx = FLAT - M0
    for j in range(e, FLAT - M0):
        if any(abs(P[k]["spot"][j] - P[k]["spot"][e]) >= 2 * STEP[k[0]] for k in (n, s)): jx = j + 1; break
    rs = struct(s, E12_I, SSTRAD if short_s else LSTRAD, flat=M0 + jx, mode=mode, lots=nS)
    rn = struct(n, E12_I, LSTRAD if short_s else SSTRAD, flat=M0 + jx, mode=mode, lots=nN)
    if not (rn and rs): return None
    rn["why"] = rs["why"] = "spot" if jx < FLAT - M0 else "time"; return rn, rs


def study_e12():
    V = e12_table(); V = V[(V.day >= L.HO) == L.HOLDOUT]
    print(f"E12 eligible days {len(V)}, |z|>1.5 on {(V.z.abs() > 1.5).sum()} (z>1.5 {(V.z > 1.5).sum()})")
    pool = {}
    for r in V.itertuples():
        nN, nS = _size(r.vN, r.vS); pool[r.day] = {ss: e12_pair(r.day, ss, nN, nS) for ss in (True, False)}
    for mode in ("cons", "opt"):
        T, legs = [], []
        for r in V[V.z.abs() > 1.5].itertuples():
            nN, nS = _size(r.vN, r.vS); x = e12_pair(r.day, r.z > 0, nN, nS, mode)
            if not x: continue
            rn, rs = x; legs += [rn, rs]
            T.append(dict(sym="SENSEX" if r.z > 0 else "NIFTY", day=r.day, pnl=rn["pnl"] + rs["pnl"], forced=rn["forced"] or rs["forced"],
                          maxloss=np.nan, why=rn["why"], held=rn["held"], nN=nN, nS=nS, z=round(r.z, 2), N=round(rn["pnl"]), S=round(rs["pnl"])))
        D, Lg = pd.DataFrame(T), pd.DataFrame(legs)
        if not len(D): print(mode, "no trades"); continue
        rg = np.random.default_rng(9)  # placebo: random (eligible day of the same month, random direction), cons pool
        cand = {}
        for d, pv in pool.items(): cand.setdefault(L.month(d), []).extend(x[0]["pnl"] + x[1]["pnl"] for x in pv.values() if x)
        rnd = np.array([sum(rg.choice(cand[L.month(d)]) for d in D.day) for _ in range(2000)])
        print(f"E12 pair [{mode}] (sym = short side):", dict(summ(D), p_vs_rand=round((rnd >= D.pnl.sum()).mean(), 4), rand_avg=round(rnd.mean() / len(D))))
        print(f"  legs [{mode}] short:", summ(Lg[Lg.credit > 0]), "\n  long:", summ(Lg[Lg.credit < 0]))
        if mode == "cons": print(D[["day", "z", "sym", "nN", "nS", "N", "S", "pnl", "why", "held"]].round(0).to_string(index=False))


def e13_signals(keys):
    """first close in 31..285 (09:46-14:00) with |spot - spot at 09:45 close| >= 2 steps; rise = ATM IV there - at 09:45."""
    out = []
    for k in keys:
        s = P[k]["spot"]; hit = np.nonzero(np.abs(s[31:286] - s[30]) >= 2 * STEP[k[0]])[0]
        if len(hit): j = 31 + int(hit[0]); out.append(dict(key=k, sym=k[0], day=k[1], j=j, rise=_iv(k, j) - _iv(k, 30)))
    S = pd.DataFrame(out); S["mo"] = S.day.map(L.month); return S.dropna(subset=["rise"])


E13X = dict(sstop=2, stop=0.3)


def study_e13():
    A = e13_signals(L.ALLK); dev = A[A.day < L.HO]
    if L.HOLDOUT: S = A[A.day >= L.HO].assign(X=dev.rise.median())
    else: S = dev.assign(X=[dev[dev.mo < m].rise.median() if (dev.mo < m).any() else np.nan for m in dev.mo]).dropna(subset=["X"])
    print(f"E13 shock days {len(S)}; X (IV pts) {S.X.min():.2f}..{S.X.max():.2f}; rise median {S.rise.median():.2f}")
    rg = np.random.default_rng(3); rp = {}
    for k in S.key:
        rp[k] = [r["pnl"] for r in (struct(k, int(i), SSTRAD, **E13X) for i in rg.integers(31, 286, 12)) if r]
    for nm, G in (("E13 shock+IV rise > X", S[S.rise > S.X]), ("E13 control: every shock", S)):
        for mode in ("cons", "opt"):
            T = [dict(r, key=k) for k, j in zip(G.key, G.j) for r in [struct(k, int(j), SSTRAD, mode=mode, **E13X)] if r]
            D = pd.DataFrame(T); rgr = np.random.default_rng(9)
            rnd = np.array([sum(rgr.choice(rp[k]) if rp[k] else 0 for k in D.key) for _ in range(2000)])
            print(f"{nm} [{mode}]:", dict(summ(D), p_vs_rand=round((rnd >= D.pnl.sum()).mean(), 4), rand_avg=round(rnd.mean() / len(D)),
                                          why=D.why.value_counts().to_dict()))


E14X = {f"spot{s}": dict(sstop=s) for s in (1, 1.5, 2, 2.5)}
E14X.update({f"time{h}": dict(hold=h) for h in (15, 30, 60, 120)})
E14X.update({f"trail{int(x * 100)}": dict(trail=x, sstop=2.5) for x in (0.2, 0.3, 0.5)})
E14E = {"long_atm": lambda sd: [(sd, 0, 1)], "short_strad": lambda sd: SSTRAD, "fade_cs": lambda sd: e5_legs(sd, "cs")}


def e14_run(ent, lf, ex, mode):
    out = {}
    for k, i, sd in ent:
        ex2 = dict(ex); h = ex2.pop("hold", None)
        if h: ex2["flat"] = min(FLAT, M0 + i + 1 + h)
        r = struct(k, i, lf(sd), mode=mode, **ex2)
        if r: out[(k, i, sd)] = r
    return out


def study_e14():
    """random entries (4 per sym-day, 09:20-14:00, random side); each exit vs holding to 15:15 on the SAME entries.
    Evidence: per-day diff exit(cons) - hold(opt), so the off-tape bound can only favour the hold."""
    rg = np.random.default_rng(21)
    ent = [(k, int(i), "CE" if sd == 0 else "PE") for k in L.KEYS for i, sd in zip(rg.integers(5, 286, 4), rg.integers(0, 2, 4))]
    rows = []; nc = len(E14E) * len(E14X)
    for en, lf in E14E.items():
        Bo, Bc = e14_run(ent, lf, {}, "opt"), e14_run(ent, lf, {}, "cons")
        print(f"{en} hold to 15:15: cons {summ(pd.DataFrame(Bc.values()))}\n   opt {summ(pd.DataFrame(Bo.values()))}", flush=True)
        for xn, ex in E14X.items():
            C = e14_run(ent, lf, ex, "cons"); ks = [t for t in C if t in Bo and t in Bc]
            D = pd.DataFrame([C[t] for t in ks]).assign(ds=[C[t]["pnl"] - Bo[t]["pnl"] for t in ks], dc=[C[t]["pnl"] - Bc[t]["pnl"] for t in ks])
            g = D.groupby("day").ds.sum(); mo = D.groupby(D.day.map(L.month)).ds.sum(); s = summ(D)
            rows.append(dict(entry=en, exit=xn, n=s["n"], total=s["total"], avg=s["avg"], p_boot=s["p_boot"], mpos=s["mpos"],
                             diff_strict=round(D.ds.sum()), diff_avg=round(D.ds.mean()), t_diff=round(g.mean() / (g.std(ddof=1) / np.sqrt(len(g))), 2),
                             p_diff=_pboot(g.values), mpos_diff=f"{(mo > 0).sum()}/{len(mo)}", diff_same_cons=round(D.dc.sum()),
                             forced=s["forced"], pass_bonf=_pboot(g.values) < 0.05 / nc))
            print(rows[-1], flush=True)
    R = pd.DataFrame(rows); pd.set_option("display.width", 250); print(f"E14 ({nc} cells, Bonferroni alpha {0.05 / nc:.4f})")
    print(R.to_string(index=False))
    ok = R.groupby("exit").pass_bonf.all(); print("exit families passing for ALL entry types:", list(ok[ok].index))


# ---------------------------------------------------------------- E18 the E6 score as a tail-risk gate for S1 (registry E18)
def e18_metrics(D):
    """D: per-trade rows (day, pnl). CVaR5 = mean of the worst ceil(5%) trades; worst day / maxdd on per-day sums."""
    x = np.sort(D.pnl.values); g = D.groupby("day").pnl.sum().sort_index(); c = g.cumsum()
    return dict(cvar5=x[:max(1, math.ceil(0.05 * len(x)))].mean(), worst_day=g.min(), maxdd=(c - c.cummax().clip(lower=0)).min(),  # peak starts at 0
                mean=x.mean(), total=x.sum(), n=len(x))


def study_e18():
    """frozen before results (side-session notes E18_freeze.md): skip S1 when the E6 walk-forward score > dev q0.8; tail
    metrics vs 1000 random skips of the same count; adopt only if p(CVaR5) and p(maxdd) < 0.05 and mean >= no-skip mean,
    on dev AND holdout (cons)."""
    S = pd.read_pickle(f"{L.OUT}/e7_days.pkl"); c = S[S.day < L.HO].score.quantile(0.8)
    for nm, G in (("DEV", S[S.day < L.HO]),) + ((("HOLDOUT", S[S.day >= L.HO]),) if L.HOLDOUT else ()):
        for mode in ("cons", "opt"):
            A = G.dropna(subset=[mode]).assign(pnl=lambda d: d[mode]); skip = A.score > c; k = int(skip.sum())
            base, rule = e18_metrics(A), e18_metrics(A[~skip]); rng = np.random.default_rng(18)
            pl = [e18_metrics(A.drop(A.index[rng.choice(len(A), k, replace=False)])) for _ in range(1000)]
            p = {m: (sum(q[m] >= rule[m] for q in pl) + 1) / 1001 for m in ("cvar5", "worst_day", "maxdd", "mean")}
            ok = p["cvar5"] < 0.05 and p["maxdd"] < 0.05 and rule["mean"] >= base["mean"]
            print(f"{nm} {mode}: cut {c:.3f}, skip {k}/{len(A)} sym-days")
            for lab, r in (("all", base), ("rule", rule), ("rand median", {m: np.median([q[m] for q in pl]) for m in rule})):
                print(f"  {lab:12s} " + "  ".join(f"{m} {r[m]:,.0f}" for m in ("n", "cvar5", "worst_day", "maxdd", "mean", "total")))
            print("  p_vs_rand " + "  ".join(f"{m} {v:.3f}" for m, v in p.items()) + f"  -> {'PASS' if ok else 'fail'}")


# ---------------------------------------------------------------- E16-E17 full option chain of T-1 (NSE/BSE bhavcopy, ext_fetch.py)
EX_OF = {"NIFTY": "NSE", "SENSEX": "BSE"}
_N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs(F, K, T, v, cp):
    """Black-76 price, r = 0 (forward F, vol v, years T)."""
    d1 = (math.log(F / K) + v * v * T / 2) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return F * _N(d1) - K * _N(d2) if cp == "CE" else K * _N(-d2) - F * _N(-d1)


def _impv(px, F, K, T, cp):
    """implied vol by bisection on 0.01..5; NaN when the price is outside the model's range."""
    lo, hi = 0.01, 5.0
    if not (_bs(F, K, T, lo, cp) < px < _bs(F, K, T, hi, cp)): return np.nan
    for _ in range(60):
        m = (lo + hi) / 2; lo, hi = (m, hi) if _bs(F, K, T, m, cp) < px else (lo, m)
    return (lo + hi) / 2


def chain_feats(C, exp, d1):
    """C: one T-1 bhavcopy (one symbol) restricted to expiry `exp`; d1 = T-1 date. Returns (max pain strike, rr)."""
    ce, pe = C[C.OptnTp == "CE"].set_index("StrkPric"), C[C.OptnTp == "PE"].set_index("StrkPric")
    Ks = np.array(sorted(set(ce.index) | set(pe.index)), float)
    oc, op = ce.OpnIntrst.reindex(Ks).fillna(0).values, pe.OpnIntrst.reindex(Ks).fillna(0).values
    pain = [(oc * np.maximum(0, k - Ks)).sum() + (op * np.maximum(0, Ks - k)).sum() for k in Ks]
    mp = Ks[int(np.argmin(pain))] if (oc + op).sum() > 0 else np.nan
    F = float(C.UndrlygPric.iloc[0]); T = np.busday_count(d1, exp) / 252
    both = [k for k in Ks if k in ce.index and k in pe.index and ce.ClsPric[k] > 0 and pe.ClsPric[k] > 0]
    if not both or T <= 0: return mp, np.nan
    ka = min(both, key=lambda k: abs(k - F)); sd = 1.25 * (ce.ClsPric[ka] + pe.ClsPric[ka])
    kp, kc = Ks[np.argmin(abs(Ks - (F - sd)))], Ks[np.argmin(abs(Ks - (F + sd)))]
    if kp not in pe.index or kc not in ce.index or pe.TtlTradgVol[kp] <= 0 or ce.TtlTradgVol[kc] <= 0: return mp, np.nan
    return mp, _impv(pe.ClsPric[kp], F, kp, T, "PE") - _impv(ce.ClsPric[kc], F, kc, T, "CE")


def chain_table():
    """per panel sym-day T: features from the LAST bhavcopy dated before T, on the expiry the panel trades on T.
    g = (max pain - spot at 09:45 close) / step; z = rr vs the prior 20 rr of that symbol (strictly prior)."""
    files = {ex: sorted(glob.glob(f"{L.EXT}/bhav/{ex}_*.csv")) for ex in ("NSE", "BSE")}
    fd = {ex: [os.path.basename(f)[4:14] for f in fs] for ex, fs in files.items()}; cache, rows = {}, []
    for k in L.ALLK:
        sym, day = k; ex = EX_OF[sym]; j = np.searchsorted(fd[ex], day) - 1
        if j < 0: continue
        f = files[ex][j]
        if f not in cache: cache[f] = pd.read_csv(f)
        X = cache[f]; C = X[X.XpryDt == P[k]["exp"]]
        if not len(C): continue
        mp, rr = chain_feats(C, P[k]["exp"], fd[ex][j])
        rows.append(dict(sym=sym, day=day, key=k, d1=fd[ex][j], dte=P[k]["dte"], mp=mp, rr=rr, g=(mp - P[k]["spot"][30]) / STEP[sym]))
    V = pd.DataFrame(rows).sort_values(["sym", "day"]); V["mo"] = V.day.map(L.month)
    pr = V.groupby("sym").rr.transform(lambda x: x.shift(1).rolling(20).mean())
    ps = V.groupby("sym").rr.transform(lambda x: x.shift(1).rolling(20).std())
    V["z"] = (V.rr - pr) / ps; V["ag"], V["az"] = V.g.abs(), V.z.abs(); return V


E16I = 30  # decide at the 09:45 close, fill 09:46 open (as R3)
LONG = lambda sd: [(sd, 0, 1)]


def e_cell(name, sel, legs_fn, ex, side_col=None, sign=1, pool_keys=None):
    """sel: chosen rows (key, side from sign(side_col)*sign). p_vs_rand: same legs/exit/mode on random panel days of the
    same symbol and month (random side if directional), 2000 draws."""
    Ks = pool_keys if pool_keys is not None else L.KEYS; out = {}
    for mode in ("cons", "opt"):
        pool = {}  # critic 2026-10-28: the pool was cons-only and mixed symbols
        for k in Ks:
            for sd in (("CE", "PE") if side_col else ("CE",)):
                r = struct(k, E16I, legs_fn(sd), mode=mode, **ex)
                if r: pool.setdefault((k[0], L.month(k[1])), []).append(r["pnl"])
        T = []
        for r in sel.itertuples():
            sd = ("CE" if sign * getattr(r, side_col) > 0 else "PE") if side_col else "CE"
            x = struct(r.key, E16I, legs_fn(sd), mode=mode, **ex)
            if x: T.append(dict(x, key=r.key, side=sd))
        D = pd.DataFrame(T)
        if not len(D): print(name, mode, "no trades"); continue
        rg = np.random.default_rng(9); rnd = np.array([sum(rg.choice(pool[(sy, L.month(d))]) for sy, d in zip(D.sym, D.day)) for _ in range(2000)])
        out[mode] = dict(summ(D), p_vs_rand=round((rnd >= D.pnl.sum()).mean(), 4), rand_avg=round(rnd.mean() / len(D)),
                         why=D.why.value_counts().to_dict())
        print(f"{name} [{mode}]:", out[mode], flush=True)
        if mode == "cons": print("   by month (k):", (D.groupby(D.day.map(L.month)).pnl.sum() / 1000).round(0).to_dict(), flush=True)
    return out


def study_e16e17():
    """E16 max pain / E17 smile skew from the T-1 full chain (rules frozen before results; 4 cells, Bonferroni 0.0125)."""
    VA = chain_table(); V = VA[(VA.day >= L.HO) == L.HOLDOUT]
    print(f"chain rows {len(V)} (mp {V.mp.notna().sum()}, rr {V.rr.notna().sum()}, z {V.z.notna().sum()}); "
          f"g median {V.ag.median():.2f} steps; Spearman g vs 09:45->close move "
          f"{V.g.corr(pd.Series([(P[k]['spot'][-1] - P[k]['spot'][30]) / STEP[k[0]] for k in V.key], V.index), method='spearman'):.3f}", flush=True)
    d16 = dict(sstop=2.5); d16b = dict(sstop=2)
    s, _ = L.wf_ext(VA.dropna(subset=["g"]), "ag"); s = s[s.ag > 0]
    e_cell("E16a ATM toward max pain if |g| > WF q0.7", s, LONG, d16, side_col="g")
    pin = V[(V.ag <= 1) & (V.dte <= 1)]; pk = [k for k in L.KEYS if P[k]["dte"] <= 1]
    e_cell("E16b short straddle if |g| <= 1 and dte <= 1", pin, lambda sd: SSTRAD, d16b, pool_keys=pk)
    s, _ = L.wf_ext(VA.dropna(subset=["z"]), "az")
    e_cell("E17a ATM against skew (z>0 -> PE) if |z| > WF q0.7", s, LONG, d16, side_col="z", sign=-1)
    s, _ = L.wf_ext(VA.dropna(subset=["z"]), "z")
    e_cell("E17b long straddle if z > WF q0.7", s, lambda sd: LSTRAD, d16)


def _syn(k, spot, st, a0, px0=50.0, px1=20.0, iv=15.0):
    """synthetic panel (strikes ATM +-3, flat prices) for selftests; returns the C dict."""
    C = {}
    for sd in ("CE", "PE"):
        for off in range(-3, 4):
            a = np.full((NB, 7), np.nan); a[:, :4] = px0 if off == 0 else px1
            a[:, 5] = iv; C[(sd, a0 + off * st)] = a
    P[k] = dict(spot=spot, atm=np.full(NB, float(a0)), C=C, exp=k[1], dte=0, d0=1); return C


def study_selftest():
    """synthetic day: flat option prices except a 2-step spot jump at bar 100 -> spot exit at bar 101 open."""
    k = ("NIFTY", "1999-01-01"); spot = np.full(NB, 20000.0); spot[100:] = 20100.0
    C = {}
    for sd in ("CE", "PE"):
        for off in range(-3, 4):
            a = np.full((NB, 7), np.nan); a[:, :4] = 50.0 if off == 0 else 20.0; C[(sd, 20000.0 + off * 50)] = a
    C[("CE", 20000.0)][101:, :4] = 120.0; C[("PE", 20000.0)][101:, :4] = 10.0
    P[k] = dict(spot=spot, atm=np.full(NB, 20000.0), C=C, exp="1999-01-01", dte=0, d0=1)
    h = lambda m, v: L.hs("NIFTY", 1, M0 + m, v)
    r = struct(k, 31, SSTRAD, sstop=2)
    e1, x1, x2 = 50 - h(32, 50), 120 + h(101, 120), 10 + h(101, 10)
    exp = (2 * e1 - x1 - x2) * 650 - L.cost(x1, e1, "NIFTY") - L.cost(x2, e1, "NIFTY")
    assert r["why"] == "spot" and r["held"] == 69 and abs(r["pnl"] - exp) < 1e-6, (r, exp)
    del C[("PE", 20000.0 - 150)]  # a wing off the tape: cons values it at intrinsic (0), opt at the smallest taped extrinsic
    rc, ro = struct(k, 31, ifly(3), mode="cons"), struct(k, 31, ifly(3), mode="opt")
    assert rc is None and ro is None  # cannot enter a leg with no quote
    C[("PE", 20000.0 - 150)] = np.full((NB, 7), np.nan); C[("PE", 20000.0 - 150)][:60, :4] = 5.0  # wing quoted only until bar 59
    rc, ro = struct(k, 31, ifly(3), mode="cons"), struct(k, 31, ifly(3), mode="opt")
    assert rc["forced"] and ro["forced"] and ro["pnl"] > rc["pnl"], (rc, ro)  # opt values the off-tape wing higher
    # ---- E12-E14 paths
    b1, s1 = 60.0, 20.0; fx = L.CM * 1.18 * 40
    assert abs(_cost(b1, s1, "NIFTY", LOTS) - L.cost(b1, s1, "NIFTY")) < 1e-9  # lots == LOTS is L.cost
    for n in (1, 5, 20):
        assert abs(_cost(b1, s1, "NIFTY", n) - (fx + (L.cost(b1, s1, "NIFTY") - fx) * n / LOTS)) < 1e-9
    assert abs((_cost(b1, s1, "NIFTY", 2 * LOTS) - fx) - 2 * (L.cost(b1, s1, "NIFTY") - fx)) < 1e-9
    r5 = struct(k, 31, SSTRAD, sstop=2, lots=5)  # k still holds the spot-jump day (the ifly edits only touched the PE wing)
    exp5 = (2 * e1 - x1 - x2) * 65 * 5 - _cost(x1, e1, "NIFTY", 5) - _cost(x2, e1, "NIFTY", 5)
    assert r5["why"] == "spot" and abs(r5["pnl"] - exp5) < 1e-6, (r5, exp5)
    # time exit via flat: exits at the open of bar 60
    kt = ("NIFTY", "1999-01-02"); _syn(kt, np.full(NB, 20000.0), 50, 20000)
    rt = struct(kt, 31, SSTRAD, flat=M0 + 60); assert rt["why"] == "time" and rt["held"] == 60 - 32, rt
    # trail, credit position: straddle 100 -> 80 (low) -> 90 (+12.5%, no fire) -> 97 at bar 55 (>= 96) -> exit at bar 56
    c = np.full(NB, 100.0); c[40:] = 80.0; c[50:] = 90.0
    _syn(kt, np.full(NB, 20000.0), 50, 20000); [P[kt]["C"][(sd, 20000.0)].__setitem__((slice(None), slice(0, 4)), (c / 2)[:, None]) for sd in ("CE", "PE")]
    rn = struct(kt, 31, SSTRAD, trail=0.2); assert rn["why"] == "time" and rn["held"] == FLAT - M0 - 32, rn  # 90 < 96: no trail
    c[55:] = 97.0; [P[kt]["C"][(sd, 20000.0)].__setitem__((slice(None), slice(0, 4)), (c / 2)[:, None]) for sd in ("CE", "PE")]
    rt = struct(kt, 31, SSTRAD, trail=0.2); assert rt["why"] == "trail" and rt["held"] == 56 - 32, rt
    # trail, debit position (long ATM CE): 50 -> 100 (peak) -> 85 (no fire) -> 79 at bar 55 (<= 80) -> exit at bar 56
    dp = np.full(NB, 50.0); dp[40:] = 100.0; dp[50:] = 85.0; _syn(kt, np.full(NB, 20000.0), 50, 20000)
    P[kt]["C"][("CE", 20000.0)][:, :4] = dp[:, None]; LC = [("CE", 0, 1)]
    rn = struct(kt, 31, LC, trail=0.2); assert rn["why"] == "time" and rn["held"] == FLAT - M0 - 32, rn
    dp[55:] = 79.0; P[kt]["C"][("CE", 20000.0)][:, :4] = dp[:, None]; rt = struct(kt, 31, LC, trail=0.2); assert rt["why"] == "trail" and rt["held"] == 56 - 32, rt
    # _size: vega-matched whole lots, ties -> more lots, within 1..10
    assert _size(100, 250) == (10, 4) and _size(100, 100) == (10, 10)
    for vN, vS in ((65, 20), (3, 400), (400, 3), (123, 77)): assert all(1 <= x <= 10 for x in _size(vN, vS))
    # e12_pair: SENSEX (step 100) jumps 2 steps at bar 100, NIFTY flat -> both legs exit at bar 101 open
    d = "1999-01-03"; kn, ks = ("NIFTY", d), ("SENSEX", d); sp = np.full(NB, 80000.0); sp[100:] = 80200.0
    _syn(kn, np.full(NB, 20000.0), 50, 20000); _syn(ks, sp, 100, 80000, 150.0, 60.0)
    for ss in (True, False):
        rn, rs = e12_pair(d, ss, 3, 7)
        assert rn["held"] == rs["held"] == 101 - 32 and rn["why"] == rs["why"] == "spot", (rn, rs)
        assert (rs["credit"] > 0 and rn["credit"] < 0) if ss else (rs["credit"] < 0 and rn["credit"] > 0), (ss, rn, rs)
    _syn(ks, np.full(NB, 80000.0), 100, 80000, 150.0, 60.0)  # no 2-step move on either: hold to 15:15
    rn, rs = e12_pair(d, True, 3, 7); assert rn["held"] == rs["held"] == FLAT - M0 - 32, (rn, rs)
    # e13_signals: 2 steps vs bar 30 at bar 100 -> j == 100, rise = IV(100) - IV(30); 1-step move and flat day give no row
    ka, kb, kc = [("NIFTY", f"1999-02-0{i}") for i in (1, 2, 3)]
    ivv = np.full(NB, 15.0); ivv[100:] = 18.0
    _syn(ka, spot, 50, 20000, iv=ivv); _syn(kb, np.full(NB, 20000.0), 50, 20000)
    sp1 = np.full(NB, 20000.0); sp1[100:] = 20050.0; _syn(kc, sp1, 50, 20000)
    S = e13_signals([ka, kb, kc]); assert len(S) == 1 and S.j[0] == 100 and abs(S.rise[0] - 3.0) < 1e-9 and S.key[0] == ka, S
    for kk in (k, kt, kn, ks, ka, kb, kc): del P[kk]
    # ---- E16/E17 paths: implied vol round trip; max pain; skew from a synthetic chain (puts 30 vol, calls 20 vol)
    for cp in ("CE", "PE"):
        for v in (0.12, 0.2, 0.6): assert abs(_impv(_bs(20000, 20300, 3 / 252, v, cp), 20000, 20300, 3 / 252, cp) - v) < 1e-6
    assert np.isnan(_impv(0.0, 20000, 20300, 3 / 252, "CE"))
    Ks = np.arange(19000, 21001, 50.0); T3 = np.busday_count("1999-01-04", "1999-01-07") / 252
    ch = pd.DataFrame([dict(StrkPric=K, OptnTp=cp, UndrlygPric=20000.0, TtlTradgVol=1, OpnIntrst=0,
                            ClsPric=_bs(20000, K, T3, 0.3 if K < 20000 else 0.2, cp)) for K in Ks for cp in ("CE", "PE")])
    ch.loc[(ch.StrkPric == 20500) & (ch.OptnTp == "CE"), "OpnIntrst"] = 1000  # all OI on 20500 CE and 19700 PE ->
    ch.loc[(ch.StrkPric == 19700) & (ch.OptnTp == "PE"), "OpnIntrst"] = 1000  # holders' payout is 0 anywhere in between
    ch.loc[(ch.StrkPric == 20000) & (ch.OptnTp == "CE"), "OpnIntrst"] = 1     # a tiny CE OI at 20000 -> min pain at <= 20000
    mp, rr = chain_feats(ch, "1999-01-07", "1999-01-04")
    assert mp == 19700 and abs(rr - 0.1) < 1e-3, (mp, rr)
    sd = 1.25 * ch[ch.StrkPric == 20000].ClsPric.sum(); kp = Ks[np.argmin(abs(Ks - (20000 - sd)))]
    ch.loc[(ch.StrkPric == kp) & (ch.OptnTp == "PE"), "TtlTradgVol"] = 0  # untraded wing strike -> no skew
    assert np.isnan(chain_feats(ch, "1999-01-07", "1999-01-04")[1])
    # ---- E18 metrics: 21 trades on 11 days -> CVaR5 = mean of the worst ceil(1.05) = 2 trades; dd on day sums
    D = pd.DataFrame(dict(day=[f"d{i // 2:02d}" for i in range(21)], pnl=[-100.0, -50.0] + [10.0] * 19))
    m = e18_metrics(D)
    assert m["cvar5"] == -75 and m["worst_day"] == -150 and m["maxdd"] == -150 and m["n"] == 21 and m["total"] == 40, m
    D.loc[2:3, "pnl"] = -20.0; m = e18_metrics(D); assert m["maxdd"] == -190 and m["worst_day"] == -150, m  # d00 -150, d01 -40
    print("sell_lab selftest OK")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
