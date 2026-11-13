"""E24-E26 (frozen in the registry before results; Fable design review 2026-11-12). Paper research only, no orders.
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python casino_lab.py OUT [streams|book|exits|dist|selftest]
OUT = the opt1y_lab cache dir (opt1y.parquet, spreads.csv, voldays.pkl). Engine = sell_lab.struct, mode cons (the evidence),
costs x1.5, p75 half-spread (E23: the engine spread is within the measured full-size crossing cost), flatten 15:15.
Streams (one per sym-day each): FIN1 long ATM straddle 09:46 on walk-forward or_iv > q0.7 days, held to 15:15;
B1 Crabel NR4 stretch breakout (book_lab); SGATE = S1 on S2-calm AND SC1-contracting days, NIFTY only (failed holdout:
forward-only, size 0 in the book); info only: S1, S2, SC1, S1 x LOC20-high."""
import sys, os, json, math, numpy as np, pandas as pd
import opt1y_lab as L
import sell_lab as S
import book_lab as B

OUT = L.OUT; HO = L.HO; M0 = L.M0
FROZEN_EXIT = {"FIN1": {}, "B1": None, "SGATE": dict(sstop=2)}  # B1 keeps its own signal exits


# ---------------------------------------------------------------- E24 streams
def fin1_days():
    """FIN1 days exactly as opt1y_lab.fam_final: dev walk-forward by month, holdout thresholds from all dev days."""
    out = []
    for ho in (False, True):
        L.HOLDOUT = ho; V = L.vol_days(); V = V[(V.day >= HO) == ho]; c, _ = L.wf_day(V, "or_iv", 0.7); out.append(c)
    L.HOLDOUT = False
    return {(r.sym, r.day) for r in pd.concat(out).itertuples()}


def gates():
    V = L.vol_days(); D = B.prep()
    calm = {(r.sym, r.day) for r in V.itertuples() if r.or_iv <= 1.0042}                       # S2 (registry E3)
    con = {k for k, r in D.iterrows() if np.isfinite(r.rr1) and r.rr1 < 0.7}                    # SC1
    loc = (D.c1 - D.p20L) / (D.p20H - D.p20L)
    hi20 = {k for k, v in loc.items() if np.isfinite(v) and v >= 0.8}                            # E21 LOC20 HIGH
    return calm, con, hi20, D


def trades(keys, i, legs, ex, mode="cons"):
    R = [dict(r, key=k) for k in keys for r in [S.struct(k, i, legs, mode=mode, **ex)] if r]
    return pd.DataFrame(R)


def streams(ex=None):
    """per-trade frames (sym, day, pnl, ...) of every stream on the whole year. ex overrides a stream's exit (E25)."""
    ex = ex or {}; K = L.ALLK; f1 = fin1_days(); calm, con, hi20, D = gates()
    s1k = [k for k in K]
    T = {"FIN1": trades([k for k in K if k in f1], 30, S.LSTRAD, ex.get("FIN1", {})),
         "S1": trades(s1k, 31, S.SSTRAD, dict(sstop=2))}
    T["S2"] = T["S1"][T["S1"].key.isin(calm)].copy(); T["SC1"] = T["S1"][T["S1"].key.isin(con)].copy()
    T["S1xLOC20H"] = T["S1"][T["S1"].key.isin(hi20)].copy()
    sg = [k for k in K if k in calm and k in con and k[0] == "NIFTY"]
    T["SGATE"] = trades(sg, 31, S.SSTRAD, ex.get("SGATE", dict(sstop=2)))
    if "B1" in ex:
        def g(k):
            if k not in D.index: return []
            return [(i, [(sd, 0, 1)], dict(dirn=1 if sd == "CE" else -1, **ex["B1"](e))) for i, sd, e in B.sig_b1(k, D.loc[k])]
        T["B1"] = B.run_specs(g, K)
    else:
        T["B1"] = B.run_specs(B._long(B.sig_b1, D), K)
    for t in T.values():
        if len(t): t["dev"] = t.day < HO
    return T


def daily(T, names, lots=None):
    """day x stream P&L (0 on no-trade days), scaled to `lots` per stream (P&L is at 10 lots; brokerage scaling ignored:
    ponytail - fixed brokerage is ~2% of a 10-lot round trip, so smaller sizes are slightly flattered; noted in the registry)."""
    days = sorted({k[1] for k in L.ALLK}); out = pd.DataFrame(index=days)
    for n in names:
        s = T[n].groupby("day").pnl.sum() if len(T[n]) else pd.Series(dtype=float)
        out[n] = s.reindex(days).fillna(0.0) * ((lots or {}).get(n, 10) / 10)
    return out


def kelly_lots(T, n, C, frac=0.25, shrink=0.5):
    """quarter Kelly on the 50%-shrunk dev mean per trade: m* = C mu / var for a bet whose 10-lot P&L is X; lots 1..10."""
    x = T[n][T[n].dev].pnl.values; mu = shrink * x.mean()
    if mu <= 0: return 1
    return int(np.clip(round(10 * frac * C * mu / x.var(ddof=1)), 1, 10))


def ruin(day_pnl, C, mu_day, tail=0.0, paths=10000, days=250, block=5, seed=1):
    """stationary block bootstrap of the daily book P&L, de-meaned to mu_day; ruin = drawdown >= 50% of C within `days`.
    tail: one extra loss of this size with probability 1/250 per day."""
    rg = np.random.default_rng(seed); x = np.asarray(day_pnl, float); x = x - x.mean() + mu_day; n = len(x)
    ruined = 0; dd_all = []
    for _ in range(paths):
        idx = np.empty(days, int); j = rg.integers(n)
        for t in range(days):
            idx[t] = j; j = rg.integers(n) if rg.random() < 1 / block else (j + 1) % n
        p = x[idx] - (tail * (rg.random(days) < 1 / 250))
        eq = C + np.cumsum(p); dd = (np.maximum.accumulate(np.maximum(eq, C)) - eq).max()
        dd_all.append(dd); ruined += dd >= 0.5 * C
    return ruined / paths, np.percentile(dd_all, 99)


def summ(t):
    if not len(t): return dict(n=0)
    g = t.groupby("day").pnl.sum(); b = np.random.default_rng(5).choice(g.values, (4000, len(g))).mean(1)
    return dict(n=len(t), total=round(t.pnl.sum()), avg=round(t.pnl.mean()), win=round((t.pnl > 0).mean() * 100),
                p_boot=round((b <= 0).mean(), 3), worst=round(t.pnl.min()))


def study_book():
    T = streams(); pd.to_pickle(T, f"{OUT}/e24_streams.pkl")
    print("E24 streams (cons, 10 lots):  dev | holdout")
    for n, t in T.items():
        print(f"  {n:10s} {summ(t[t.dev])} | {summ(t[~t.dev])}")
    f1 = T["FIN1"]; lt = []
    for k in f1.key:  # FIN1 under its original convention (opt1y_lab.trade: a strike leaving ATM+-3 exits at its last close)
        r = L.trade(k, 30, "CE", hold=None, legs=(("CE", 0), ("PE", 0))); lt.append(r[0] if r else np.nan)
    f1 = f1.assign(legacy=lt)
    print(f"  FIN1 legacy last-close convention: dev {f1[f1.dev].legacy.sum():,.0f} / holdout {f1[~f1.dev].legacy.sum():,.0f}; "
          f"forced (bound used) {f1.forced.mean() * 100:.0f}% of trades")
    names = ["FIN1", "B1", "SGATE", "S1", "S2", "SC1", "S1xLOC20H"]; Dd = daily(T, names)
    tr = Dd.ne(0)
    print("daily P&L correlation (all days, 0 = no trade):"); print(Dd.corr().round(2).to_string())
    print("same-day overlap (days both trade / days the row trades):")
    print(pd.DataFrame({a: {b: round((tr[a] & tr[b]).sum() / max(tr[a].sum(), 1), 2) for b in names} for a in names}).T.to_string())
    book = ["FIN1", "B1"]  # SGATE size 0 (forward-only); info streams are not in the book
    worst = Dd[book].sum(1).min()
    print("Book = FIN1 + B1 (SGATE forward-only, size 0). Quarter Kelly on 50%-shrunk dev mean; ruin = drawdown >= 50% of capital in 250 days")
    for C in (5e5, 10e5, 20e5):
        lots = {n: kelly_lots(T, n, C) for n in book}; Db = daily(T, book, lots).sum(1)
        dev = Db[Db.index < HO]; mu = 0.5 * dev.mean()
        r0, q0 = ruin(Db.values, C, mu); r1, q1 = ruin(Db.values, C, mu, tail=3 * abs(worst) * max(lots.values()) / 10)
        print(f"  capital {C / 1e5:.0f}L lots {lots}: shrunk mean/day {mu:,.0f} | ruin {r0:.4f} (p99 dd {q0:,.0f}) | "
              f"with tail day ruin {r1:.4f} (p99 dd {q1:,.0f}) | expected 250-day P&L {250 * mu:,.0f}")


# ---------------------------------------------------------------- E25 exits on surviving entries, walk-forward by month
MENU = {"FIN1": {"hold": {}, "spot2.5": dict(sstop=2.5), "trail30": dict(sstop=2.5, trail=0.3), "time120": dict(flat=M0 + 31 + 120)},
        "SGATE": {"spot2": dict(sstop=2), "spot1.5": dict(sstop=1.5), "spot2_tgt0.5": dict(sstop=2, tgt=0.5), "spot2_stop0.6": dict(sstop=2, stop=0.6)},
        "B1": {"default": lambda e: e, "tgt1.5": lambda e: dict(e, s_tgt=1.5), "trail30": lambda e: dict(e, trail=0.3),
               "time120": lambda e: e}}  # B1 time120 is set per entry below


def wf_pick(P, default, burn=3):
    """P: day x exit P&L. Each month after `burn`, use the exit with the best cumulative P&L over all prior months."""
    mo = P.index.map(L.month); ms = sorted(set(mo)); out = []
    for n, m in enumerate(ms):
        if n < burn: continue
        best = P[mo < m].sum().idxmax(); cur = P[mo == m]
        out.append(pd.DataFrame(dict(pick=cur[best], base=cur[default], ex=best), index=cur.index))
    return pd.concat(out)


def study_exits():
    from scipy import stats
    res = {}
    for n, menu in MENU.items():
        cols = {}
        for nm, ex in menu.items():
            if n == "B1":
                if nm == "time120":
                    D = gates()[3]
                    def g(k, D=D):
                        if k not in D.index: return []
                        return [(i, [(sd, 0, 1)], dict(dirn=1 if sd == "CE" else -1, flat=min(L.FLAT, M0 + i + 1 + 120), **e))
                                for i, sd, e in B.sig_b1(k, D.loc[k])]
                    t = B.run_specs(g, L.ALLK)
                else:
                    t = streams({"B1": ex})["B1"]
            else:
                t = streams({n: ex})[n]
            cols[nm] = t.groupby("day").pnl.sum()
        P = pd.DataFrame(cols).fillna(0.0); default = list(menu)[0]
        W = wf_pick(P, default); d = W.pick - W.base; tt = stats.ttest_1samp(d, 0, alternative="greater")
        res[n] = (P.sum().round(0).to_dict(), W.ex.value_counts().to_dict(), round(W.pick.sum()), round(W.base.sum()), round(tt.pvalue, 4))
        print(f"E25 {n}: whole-year totals by exit {res[n][0]}\n    walk-forward picks {res[n][1]}; OOS months: picked {res[n][2]:,} vs "
              f"default {res[n][3]:,}; paired day t p {res[n][4]} (pass < 0.0167: {res[n][4] < 0.0167})")
    return res


# ---------------------------------------------------------------- E26 candidate P&L distributions (read by fin1_shadow forward)
def study_dist(path=None):
    T = pd.read_pickle(f"{OUT}/e24_streams.pkl"); out = {}
    for n in ("FIN1", "B1", "SGATE", "S1", "S2", "SC1", "S1xLOC20H"):
        x = T[n].pnl.values
        if not len(x): continue
        out[n] = dict(n=int(len(x)), mean=round(float(x.mean())), p05=round(float(np.percentile(x[T[n].dev.values], 5))), p10=round(float(np.percentile(x, 10))), p50=round(float(np.median(x))),
                      p90=round(float(np.percentile(x, 90))), p_win=round(float((x > 0).mean()), 3),
                      dev_mean=round(float(T[n][T[n].dev].pnl.mean())), ho_mean=round(float(T[n][~T[n].dev].pnl.mean())) if (~T[n].dev).any() else None)
    out["_note"] = "1y history 2025-10-27..2026-10-23, cons engine, 10 lots, costs x1.5, p75 half-spread (E23-checked). Not a forecast."
    path = path or f"{L.ROOT if hasattr(L, 'ROOT') else os.path.dirname(os.path.abspath(__file__)) + '/../..'}/data/recon/candidate_dist.json"
    json.dump(out, open(path, "w"), indent=1); print(json.dumps(out, indent=1)); return out


def selftest():
    """known answers: ruin() on a constant series, wf_pick on a toy table, kelly_lots clipping."""
    r, q = ruin(np.full(50, 1000.0), 1e5, 1000.0, paths=200); assert r == 0 and q == 0
    r, q = ruin(np.full(50, -1000.0), 1e5, -1000.0, paths=200, days=60); assert r == 1.0 and q == 60000  # 60 x 1000 >= 50k
    idx = pd.Index([f"2026-0{m}-1{d}" for m in range(1, 6) for d in range(2)])
    P = pd.DataFrame(dict(a=[1.0] * 6 + [5.0] * 4, b=[2.0] * 6 + [0.0] * 4), index=idx)
    W = wf_pick(P, "a", burn=3); assert list(W.ex) == ["b", "b", "a", "a"] and W.pick.sum() == 10 and W.base.sum() == 20  # b led, then a overtook
    T = {"X": pd.DataFrame(dict(pnl=[1000.0, -500.0, 1500.0, 0.0], dev=True))}
    assert kelly_lots(T, "X", 1e5) == 10 and kelly_lots({"Y": pd.DataFrame(dict(pnl=[-1.0, -2.0], dev=True))}, "Y", 1e5) == 1
    print("casino_lab selftest OK"); desk_selftest()


# ---------------------------------------------------------------- E27-E30 (Fable catalogue review; frozen in the registry first)
def metrics(t, rnd=None):
    """win rate, payoff ratio and expectancy after costs (the founder's three numbers) + p_boot, halves, p_vs_rand.
    rnd: per-trade lists of placebo P&Ls (same day, same legs/exit, random minute and side)."""
    if not len(t): return dict(n=0)
    x = t.pnl.values; w, l = x[x > 0], x[x <= 0]; g = t.groupby("day").pnl.sum()
    b = np.random.default_rng(5).choice(g.values, (4000, len(g))).mean(1); ds = sorted(g.index); h = len(ds) // 2
    o = dict(n=len(x), win=round((x > 0).mean() * 100, 1), avg_win=round(w.mean()) if len(w) else 0, avg_loss=round(l.mean()) if len(l) else 0,
             payoff=round(w.mean() / -l.mean(), 2) if len(w) and len(l) and l.mean() < 0 else np.nan, exp=round(x.mean()), total=round(x.sum()),
             p_boot=round((b <= 0).mean(), 4), half1=round(g[ds[:h]].sum()), half2=round(g[ds[h:]].sum()))
    if rnd is not None:
        rg = np.random.default_rng(9); R = [np.asarray(v) for v in rnd]
        sims = np.array([sum(rg.choice(v) for v in R if len(v)) for _ in range(2000)]); o["p_vs_rand"] = round((sims >= x.sum()).mean(), 4)
    return o


def placebo(rows, legs_fn, lo, hi, n=20, seed=27):
    """per real trade: n random (minute lo..hi, side) entries on the same day with the same legs builder and exit kwargs."""
    rg = np.random.default_rng(seed); out = []
    for r in rows.itertuples():
        v = []
        for i, sd in zip(rg.integers(lo, hi + 1, n), rg.integers(0, 2, n)):
            side = "CE" if sd == 0 else "PE"; kw = dict(r.kw); kw["dirn"] = 1 if side == "CE" else -1
            x = S.struct(r.key, int(i), legs_fn(side), mode="cons", **kw)
            if x: v.append(x["pnl"])
        out.append(v)
    return out


def _go(keys_sigs, legs_fn):
    """keys_sigs: [(key, i, side, exit kwargs)] -> trades frame (one per sym-day, first signal)."""
    T = []
    for k, i, sd, kw in keys_sigs:
        r = S.struct(k, i, legs_fn(sd), mode="cons", **kw)
        if r: T.append(dict(r, key=k, side=sd, kw=kw))
    t = pd.DataFrame(T)
    if len(t): t["dev"] = t.day < HO
    return t


def e27():
    sig = [(k, i, sd, dict(dirn=1 if sd == "CE" else -1, s_stp=1)) for k in L.ALLK for i, sd in S.orb_signals(k, fade=True)]
    legs = lambda sd: S.e5_legs(sd, "cs"); return _go(sig, legs), legs, (S.OR_END + 1, S.LAST)


def e29():
    D = gates()[3]; sig = []
    for k in L.ALLK:
        if k not in D.index: continue
        for i, sd, e in B.sig_b1(k, D.loc[k]): sig.append((k, i, sd, dict(dirn=1 if sd == "CE" else -1, **e)))
    itm = lambda sd: [(sd, -1 if sd == "CE" else 1, 1)]; atm = lambda sd: [(sd, 0, 1)]
    return _go(sig, itm), itm, (B.I_LO, B.I_HI), _go(sig, atm)


def e30():
    sig = [(k, 270, "CE", dict(sstop=1)) for k in L.ALLK if P_(k)["d0"]]
    return _go(sig, lambda sd: S.ifly(2))


def P_(k): return L.P[k]


def _ncdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def hedge_pnl(k, e, jx, every=15, band=0.15):
    """E28(a): P&L of an index-print delta hedge (zero cost: the diagnostic ceiling) of a short ATM straddle held from bar e to
    bar jx. Net option delta per unit = 1 - 2 N(d1) (Black-76 on spot, panel IV of the two legs). Re-hedge to zero when
    |book delta| > band. ponytail: T = (dte + rest of today) / 365 with dte as given by the panel; delta near ATM is insensitive to it."""
    p = L.P[k]; sym = k[0]; q = L.qty(sym, k if L.COSTS == "dated" else None); K = p["atm"][e - 1]; h = 0.0; pnl = 0.0
    js = list(range(e, jx, every)) + [jx]
    for a, b in zip(js[:-1], js[1:]):
        Sx = p["spot"][a]; iv = np.nanmean([p["C"][(sd, K)][a, 5] for sd in ("CE", "PE") if (sd, K) in p["C"]])
        if np.isfinite(Sx) and np.isfinite(iv) and iv > 0:
            T = (p["dte"] + max(930 - (M0 + a), 1) / 375) / 365; v = iv / 100
            d1 = (math.log(Sx / K) + 0.5 * v * v * T) / (v * math.sqrt(T)); od = q * (1 - 2 * _ncdf(d1))
            if abs(od + h) > band * q: h = -od
        pnl += h * (p["spot"][min(b, L.NB - 1)] - Sx)
    return pnl


def e28():
    Sc = pd.read_pickle(f"{OUT}/e7_days.pkl"); cut = Sc[Sc.day < HO].score.quantile(1 / 3)
    keys = [(a, b) for a, b, s in zip(Sc.sym, Sc.day, Sc.score) if s <= cut and (a, b) in L.P]
    T = []
    for k in keys:
        r = S.struct(k, 31, S.SSTRAD, sstop=3, mode="cons")
        if r: T.append(dict(r, key=k, unhedged=r["pnl"], hedge=hedge_pnl(k, 32, 32 + r["held"])))
    t = pd.DataFrame(T); t["dev"] = t.day < HO; t["pnl"] = t.unhedged + t.hedge; return t, cut


def study_cand():
    pd.set_option("display.width", 250); out = []
    def show(name, t, rnd=None):
        for smp, m in (("dev", t.dev), ("holdout(seen-again)", ~t.dev)):
            r = None if rnd is None else [v for v, ok in zip(rnd, m) if ok]
            out.append(dict(id=name, sample=smp, **metrics(t[m], r)))
    t, lf, (lo, hi) = e27(); show("E27 fade credit spread in-window", t, placebo(t, lf, lo, hi))
    t, lf, (lo, hi), ta = e29(); show("E29 B1-ITM", t, placebo(t, lf, lo, hi)); show("  B1-ATM reference (same signals)", ta)
    t, cut = e28(); show("E28a hedged short straddle (index-print hedge, 0 cost)", t)
    show("  E28 same days unhedged", t.assign(pnl=t.unhedged))
    show("E30 expiry-day 13:45 iron fly +-2", e30())
    R = pd.DataFrame(out); print(R.to_string(index=False)); R.to_csv(f"{OUT}/e27_e30.csv", index=False)
    print(f"E28 gate: E6 walk-forward score <= dev q1/3 = {cut:.4f}")
    return R


# ---------------------------------------------------------------- autonomous desk (paper/shadow): deterministic daily decision
from fin1_shadow import decide, LADDER  # noqa: E402  (stdlib; the shadow prints DESK lines)


CHECKPOINTS = (40, 80, 120)  # promotion is tested ONLY at these forward trade counts, once each (no optional stopping)


def promote(fwd, dev_mean, dev_maxdd, rung):
    """ladder step from forward trades (P&L list at 10-lot scale, NO_DATA days excluded). Up one rung only when the count is a
    checkpoint and: shrunk mean > 0, forward mean >= 50% of dev mean, p_boot < 0.10. To rung 0 if the rolling-30 mean < 0 or
    drawdown > 1.5x dev max drawdown. -1 = RETIRED for good: shrunk mean <= 0 at the 80-trade checkpoint."""
    x = np.asarray(fwd, float)
    if len(x) == 80 and 0.5 * x.mean() <= 0: return -1
    if len(x) >= 30 and x[-30:].mean() < 0: return 0
    eq = np.cumsum(x) if len(x) else np.zeros(1)
    if (np.maximum.accumulate(np.maximum(eq, 0)) - eq).max() > 1.5 * abs(dev_maxdd): return 0
    if len(x) in CHECKPOINTS:
        b = np.random.default_rng(5).choice(x, (4000, len(x))).mean(1)
        if 0.5 * x.mean() > 0 and x.mean() >= 0.5 * dev_mean and (b <= 0).mean() < 0.10: return min(rung + 1, len(LADDER) - 1)
    return rung


def desk_selftest():
    D = {"SGATE": dict(p05=-20000), "B1": dict(p05=-30000)}
    r = dict(sym="NIFTY", status="OK", s2_signal=True, sc1_signal=True, b1_nr4=True)
    a = decide(r, None, D); assert [(o["id"], o["action"], o["lots"]) for o in a] == [("SGATE", "LOG_ONLY", 0), ("B1", "LOG_ONLY", 0)]
    a = decide(r, dict(rung={"SGATE": 2, "B1": 1}), D); assert [(o["action"], o["lots"]) for o in a] == [("TRADE", 2), ("TRADE", 1)]
    a = decide(r, dict(rung={"SGATE": 2}, day_pnl=-8000), D)       # 2L at 2 lots = 2 x 20000 x 2/10 = 8000 -> stop
    assert a[0]["action"] == "NO_TRADE" and a[0]["why"].startswith("daily stop")
    assert decide(dict(r, sym="SENSEX", b1_nr4=False), None, D)[0]["action"] == "NO_TRADE"      # SGATE is NIFTY only
    assert decide(dict(r, status="NO_DATA"), dict(rung={"SGATE": 4}), D)[0]["action"] == "NO_DATA"  # missing tape is not a decision
    assert decide(r, dict(rung={"SGATE": 1}), D)[0]["exit"].endswith("hard flatten at -2,000")       # L = 20000 x 1/10
    assert decide(r, dict(rung={"SGATE": 4}, open_short_gamma={"NIFTY"}), D)[0]["why"] == "one short-gamma per index"
    assert decide(r, dict(rung={"SGATE": 4}, recorder_ok=False), D)[0]["action"] == "LOG_ONLY"
    assert promote([1000.0] * 40, 1500.0, -50000, 0) == 1 and promote([1000.0] * 39, 1500.0, -50000, 0) == 0
    assert promote([1000.0] * 41, 1500.0, -50000, 0) == 0          # between checkpoints: no test
    assert promote([10.0, -20.0] * 40, 0.0, -1e9, 0) == -1          # shrunk mean <= 0 at 80 trades: retired
    assert promote([500.0] * 40, 1500.0, -50000, 1) == 1          # forward mean < 50% of dev mean: no promotion
    assert promote([100.0] * 10 + [-200.0] * 30, 0.0, -1e9, 3) == 0  # rolling-30 mean < 0: demote to log-only
    print("desk selftest OK")


if __name__ == "__main__":
    what = sys.argv[2] if len(sys.argv) > 2 else "selftest"
    {"selftest": selftest, "book": study_book, "exits": study_exits, "dist": study_dist, "cand": study_cand, "desk": desk_selftest}[what]()
