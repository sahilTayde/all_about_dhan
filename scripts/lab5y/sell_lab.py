"""Round 4: defined-risk option SELLING on the round-2 panel (paper research; no orders).
Run:  ~/paper_extra_venv/bin/python scripts/lab5y/sell_lab.py OUT [grid|selftest] [--holdout]   (run from scripts/lab5y)
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
import sys, numpy as np, pandas as pd
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
        _EXT[key] = max(0.0, min(xs)[1]) if xs else 0.0
    return _EXT[key]


def _px(k, side, K, j, col, high):
    """quote, or a bound when the strike is off the taped window: high=True -> upper bound, else lower bound."""
    a = P[k]["C"].get((side, K)); j = min(j, NB - 1); s = P[k]["spot"][j]
    v = a[j, col] if a is not None else np.nan
    if np.isfinite(v): return v, False
    intr = max(0.0, s - K) if side == "CE" else max(0.0, K - s)
    return intr + (_nearext(k, side, K, j, col) if high else 0.0), True


def struct(k, i, legs, stop=None, tgt=None, sstop=None, flat=FLAT, mode="cons", dirn=0, s_tgt=None, s_stp=None):
    """legs: [(side, off, sign)]. stop: exit when buy-back value - credit >= stop * credit. tgt: exit when value <= (1-tgt) * credit.
    sstop: exit when |spot - entry spot| >= sstop * STEP. Directional (dirn=+1 up / -1 down): exit when the signed spot
    move reaches +s_tgt steps or -s_stp steps. Returns dict or None."""
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
    why = "time"; jx = xe; forced = False
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
    jx = min(jx, NB - 1); out = 0.0; costs = 0.0; q = LOT[sym] * LOTS
    for (sd, K, sg), x in zip(L_, ent):
        v, miss = _px(k, sd, K, jx, 0, hi(sg)); forced = forced or miss
        fill = v + L.hs(sym, d0, M0 + jx, max(v, 0.05)) if sg < 0 else max(v - L.hs(sym, d0, M0 + jx, max(v, 0.05)), 0.05)
        out += -sg * fill
        costs += L.cost(fill, x, sym) if sg < 0 else L.cost(x, fill, sym)
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
                worst=round(D.pnl.min()), maxdd=round((g.cumsum() - g.cumsum().cummax()).min()), t=round(t, 2),
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


def rand_pool(keys, ex, n=12, seed=3):
    """per day: n random (minute 31..165, side) entries with the same exits -> list of pnl per day key."""
    rg = np.random.default_rng(seed); out = {}
    for k in keys:
        v = []
        for i, sd in zip(rg.integers(OR_END + 1, LAST + 1, n), rg.integers(0, 2, n)):
            r = struct(k, int(i), [("CE" if sd == 0 else "PE", 0, 1)], dirn=1 if sd == 0 else -1, **ex)
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
        D = pd.DataFrame(T); rp = rand_pool(L.KEYS, ex); flat = np.concatenate([v for v in rp.values() if v])
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
    del P[k]; print("sell_lab selftest OK")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
