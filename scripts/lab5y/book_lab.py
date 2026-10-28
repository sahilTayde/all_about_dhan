"""Round B: classic book / TradingView rules on the round-2 option panel (paper research; no orders).
Rules frozen before results (registry B1-B9): Crabel stretch+NR4, Williams k=0.5, Connors RSI(2) and Double 7s,
Turtle Soup, Bollinger squeeze, Supertrend(10,3) 15m, Holy Grail 15m, sell-after-event straddle.
Execution = sell_lab.struct, mode "cons", costs x1.5, p75 half-spread, buy ATM in the signal direction, spot exits capped
at 2.5 steps (D1), flat 15:15, entries 09:20..14:00. Daily bars from 1m closes (5y idx1m cache before the panel).
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python book_lab.py OUT [run|spot5y|selftest] [--holdout]"""
import sys, numpy as np, pandas as pd
import opt1y_lab as L
import sell_lab as S

P, STEP, M0, NB, FLAT = L.P, L.STEP, L.M0, L.NB, L.FLAT
I_LO, I_HI, CAP = 5, 285, 2.5  # decision bars 09:20..14:00; spot exits capped at 2.5 steps
IDX5Y = L.IDX5Y


# ---------------------------------------------------------------- daily bars (same definition for history and panel)
def _open(s):
    """first finite minute close (critic A2: 2 NIFTY days have a NaN 09:15 spot)."""
    f = s[np.isfinite(s)]; return f[0] if len(f) else np.nan


def daily():
    """per sym: day, o (09:15 close), h/l (max/min of minute closes), c (last close). Panel days from the panel spot."""
    X = pd.read_pickle(IDX5Y); X = X[X.sym.isin(["NIFTY", "SENSEX"]) & (X.m >= M0) & (X.m < M0 + NB)].sort_values(["sym", "day", "m"])
    H = X.groupby(["sym", "day"]).close.agg(o="first", h="max", l="min", c="last").reset_index()
    Pd = pd.DataFrame([dict(sym=k[0], day=k[1], o=_open(P[k]["spot"]), h=np.nanmax(P[k]["spot"]), l=np.nanmin(P[k]["spot"]),
                            c=P[k]["spot"][-1]) for k in L.ALLK])
    H = H[~H.set_index(["sym", "day"]).index.isin(Pd.set_index(["sym", "day"]).index)]
    D = pd.concat([H, Pd]).sort_values(["sym", "day"]).reset_index(drop=True); out = []
    for sym, g in D.groupby("sym"):
        g = g.copy(); r = g.h - g.l; c = g.c
        g["R1"] = r.shift(1)                                                   # yesterday's range
        g["nr4"] = r.shift(1) <= r.shift(1).rolling(4).min()                    # yesterday narrowest of last 4
        g["stretch"] = np.minimum(g.h - g.o, g.o - g.l).shift(1).rolling(10).mean()
        dl = c.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan)); rsi = rsi.fillna(100)
        sma200 = c.rolling(200).mean(); g["rsi2_1"] = rsi.shift(1); g["above_1"] = (c > sma200).astype(float).shift(1); g["below_1"] = (c < sma200).astype(float).shift(1)
        g["low7_1"] = (c <= c.rolling(7).min()).astype(float).shift(1); g["high7_1"] = (c >= c.rolling(7).max()).astype(float).shift(1)
        g["p20L"] = g.l.shift(1).rolling(20).min(); g["p20H"] = g.h.shift(1).rolling(20).max()
        # where in the prior 20 days the extreme was set: sessions before today (>= 4 required)
        g["agoL"] = 20 - g.l.shift(1).rolling(20).apply(np.argmin, raw=True); g["agoH"] = 20 - g.h.shift(1).rolling(20).apply(np.argmax, raw=True)
        m20, s20 = c.rolling(20).mean(), c.rolling(20).std(ddof=0); bw = 4 * s20 / m20
        g["sq_1"] = (bw <= bw.rolling(125).min()).shift(1).fillna(False)
        g["bbU_1"], g["bbL_1"] = (m20 + 2 * s20).shift(1), (m20 - 2 * s20).shift(1)
        out.append(g)
    return pd.concat(out).set_index(["sym", "day"])


# ---------------------------------------------------------------- 15m indicators (continuous over panel days)
def bars15():
    """per sym: 15m bars from the panel spot (bar b of a day = minutes 15b..15b+14), Supertrend(10,3), ADX(14), EMA20."""
    out = {}
    for sym in ("NIFTY", "SENSEX"):
        rows = []
        for k in [k for k in L.ALLK if k[0] == sym]:
            s = P[k]["spot"]
            for b in range(NB // 15):
                x = s[15 * b:15 * b + 15]; rows.append(dict(day=k[1], b=b, h=np.nanmax(x), l=np.nanmin(x), c=x[-1]))
        B = pd.DataFrame(rows); h, l, c = B.h.values, B.l.values, B.c.values; n = len(B)
        pc = np.r_[np.nan, c[:-1]]; tr = np.nanmax(np.c_[h - l, abs(h - pc), abs(l - pc)], 1)
        rma = lambda x, p: pd.Series(x).ewm(alpha=1 / p, adjust=False).mean().values
        atr = rma(tr, 10); hl2 = (h + l) / 2; upb, dnb = hl2 - 3 * atr, hl2 + 3 * atr; tr_ = np.ones(n)
        for t in range(1, n):
            if c[t - 1] > upb[t - 1]: upb[t] = max(upb[t], upb[t - 1])
            if c[t - 1] < dnb[t - 1]: dnb[t] = min(dnb[t], dnb[t - 1])
            tr_[t] = 1 if (tr_[t - 1] == -1 and c[t] > dnb[t - 1]) else -1 if (tr_[t - 1] == 1 and c[t] < upb[t - 1]) else tr_[t - 1]
        ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]; um, dm = h - ph, pl - l
        pdm = np.where((um > dm) & (um > 0), um, 0.0); mdm = np.where((dm > um) & (dm > 0), dm, 0.0)
        a14 = rma(tr, 14); pdi, mdi = 100 * rma(pdm, 14) / a14, 100 * rma(mdm, 14) / a14
        adx = rma(100 * abs(pdi - mdi) / (pdi + mdi), 14)
        B["st"] = tr_; B["adx"], B["pdi"], B["mdi"] = adx, pdi, mdi; B["ema"] = pd.Series(c).ewm(span=20, adjust=False).mean().values
        B["adx_1"] = np.r_[np.nan, adx[:-1]]; B["st_1"] = np.r_[np.nan, tr_[:-1]]
        out[sym] = {d: g.reset_index(drop=True) for d, g in B.groupby("day")}
    return out


# ---------------------------------------------------------------- frozen signals: k -> list of (i, side, ex)
def caps(stop_steps=CAP):
    return dict(s_tgt=CAP, s_stp=float(min(CAP, max(0.5, stop_steps))))


def first_cross(s, up_lvl, dn_lvl, lo=I_LO, hi=I_HI):
    for i in range(lo, hi + 1):
        if s[i] >= up_lvl: return i, "CE"
        if s[i] <= dn_lvl: return i, "PE"
    return None


def sig_b1(k, d):
    if not d.nr4 or not np.isfinite(d.stretch): return []
    s = P[k]["spot"]; o = _open(s); x = first_cross(s, o + d.stretch, o - d.stretch)
    return [(x[0], x[1], caps(2 * d.stretch / STEP[k[0]]))] if x else []


def sig_b2(k, d):
    if not np.isfinite(d.R1): return []
    s = P[k]["spot"]; o = _open(s); x = first_cross(s, o + 0.5 * d.R1, o - 0.5 * d.R1)
    return [(x[0], x[1], caps())] if x else []


def sig_b3(k, d):
    if d.above_1 == 1 and d.rsi2_1 < 10: return [(I_LO, "CE", caps())]
    if d.below_1 == 1 and d.rsi2_1 > 90: return [(I_LO, "PE", caps())]
    return []


def sig_b4(k, d):
    if d.above_1 == 1 and d.low7_1 == 1: return [(I_LO, "CE", caps())]
    if d.below_1 == 1 and d.high7_1 == 1: return [(I_LO, "PE", caps())]
    return []


def sig_b5(k, d):
    if not np.isfinite(d.p20L): return []
    s = P[k]["spot"]; st = STEP[k[0]]; brokeL = brokeH = False; lo, hi = np.inf, -np.inf
    for i in range(0, I_HI + 1):
        lo, hi = min(lo, s[i]), max(hi, s[i])
        if d.agoL >= 4 and s[i] < d.p20L: brokeL = True
        if d.agoH >= 4 and s[i] > d.p20H: brokeH = True
        if i < I_LO: continue
        if brokeL and s[i] > d.p20L: return [(i, "CE", caps((s[i] - lo) / st))]
        if brokeH and s[i] < d.p20H: return [(i, "PE", caps((hi - s[i]) / st))]
    return []


def sig_b6(k, d):
    if not d.sq_act: return []
    s = P[k]["spot"]; x = first_cross(s, d.bbU_1, d.bbL_1)
    return [(x[0], x[1], caps())] if x else []


def sig_b7(k, d, B):
    """flip at 15m bar b close (minute 15b+14) -> entry decision there; flat at the next minute after the opposite flip."""
    g = B[k[0]].get(k[1]); out = []
    if g is None: return out
    fl = [(15 * b + 14, int(r.st)) for b, r in g.iterrows() if r.st != r.st_1 and np.isfinite(r.st_1)]
    for n, (i, t) in enumerate(fl):
        if not (I_LO <= i <= I_HI): continue
        nxt = next((j for j, t2 in fl[n + 1:] if t2 != t), None)
        out.append((i, "CE" if t == 1 else "PE", dict(caps(), flat=min(FLAT, M0 + nxt + 1) if nxt else FLAT)))
    return out


def sig_b8(k, d, B):
    g = B[k[0]].get(k[1]); s = P[k]["spot"]; st = STEP[k[0]]; out = []
    if g is None: return out
    for b, r in g.iterrows():
        if not (r.adx > 30 and r.adx > r.adx_1): continue
        up = r.pdi > r.mdi and r.l <= r.ema; dn = r.mdi > r.pdi and r.h >= r.ema
        if not (up or dn): continue
        for i in range(15 * b + 15, min(15 * b + 30, NB)):
            if not (I_LO <= i <= I_HI): continue
            if up and s[i] > r.h: out.append((i, "CE", caps((s[i] - r.l) / st))); break
            if dn and s[i] < r.l: out.append((i, "PE", caps((r.h - s[i]) / st))); break
    return out


# ---------------------------------------------------------------- runner + placebo
def run_dir(name, sig, D, B=None, keys=None, nrand=20, seed=13):
    rg = np.random.default_rng(seed); T, R = [], []
    for k in keys or L.KEYS:
        if k not in D.index: continue
        d = D.loc[k]; busy = -1
        for i, sd, ex in (sig(k, d, B) if B is not None else sig(k, d)):
            if i <= busy: continue
            r = S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **ex)
            if r is None: continue
            T.append(dict(r, key=k, side=sd)); busy = i + r["held"] - 1  # next fill may be this exit's open (stop-and-reverse)
            rel = (ex.get("flat", FLAT) - M0 - i) if "flat" in ex else None; v = []
            for ri, rs in zip(rg.integers(I_LO, I_HI + 1, nrand), rg.integers(0, 2, nrand)):
                ex2 = dict(ex); sd2 = "CE" if rs == 0 else "PE"
                if rel is not None: ex2["flat"] = min(FLAT, M0 + int(ri) + rel)
                x = S.struct(k, int(ri), [(sd2, 0, 1)], dirn=1 if rs == 0 else -1, mode="cons", **ex2)
                if x: v.append(x["pnl"])
            R.append(v if v else [0.0])
    return finish(name, pd.DataFrame(T), R)


def finish(name, Dt, R):
    if not len(Dt): print(name, "no trades", flush=True); return dict(cell=name, n=0)
    rg = np.random.default_rng(9); tot = Dt.pnl.sum()
    rnd = np.array([sum(rg.choice(v) for v in R) for _ in range(2000)])
    r = dict(cell=name, **S.summ(Dt), p_vs_rand=round((rnd >= tot).mean(), 4), rand_avg=round(rnd.mean() / len(Dt)),
             why=Dt.why.value_counts().to_dict())
    print(r, flush=True); print("   by month (k):", (Dt.groupby(Dt.day.map(L.month)).pnl.sum() / 1000).round(0).to_dict(), flush=True)
    return r


def run_b9():
    """short ATM straddle after RBI (10:15 decision, RBI day) and FOMC (09:46, first Indian day after)."""
    days = sorted({k[1] for k in L.ALLK}); fomc1 = {next(d for d in days if d > f) for f in L.FOMC if any(d > f for d in days)}
    ev = [(k, 60) for k in L.KEYS if k[1] in L.RBI] + [(k, 31) for k in L.KEYS if k[1] in fomc1]
    T, R = [], []
    for k, i in ev:
        r = S.struct(k, i, S.SSTRAD, sstop=2, mode="cons")
        if r is None: continue
        T.append(dict(r, key=k))
        pool = [S.struct(kk, i, S.SSTRAD, sstop=2, mode="cons") for kk in L.KEYS if kk[0] == k[0] and L.month(kk[1]) == L.month(k[1])]
        R.append([x["pnl"] for x in pool if x] or [0.0])
    return finish("B9 short straddle after RBI / FOMC", pd.DataFrame(T), R)


def study_run():
    D = daily(); B = bars15()
    act = []  # B6: the squeeze flag stays on for 10 sessions, until the first band break (panel: 1m closes; history: daily h/l)
    for sym, g in D.groupby(level=0):
        cnt = 0
        for k, r in g.iterrows():
            if r.sq_1: cnt = 10
            on = cnt > 0; act.append(on); cnt = max(0, cnt - 1)
            if on and ((first_cross(P[k]["spot"], r.bbU_1, r.bbL_1) is not None) if k in P else (r.h > r.bbU_1 or r.l < r.bbL_1)): cnt = 0
    D["sq_act"] = act
    rows = [run_dir("B1 Crabel stretch breakout, NR4 days", sig_b1, D), run_dir("B2 Williams open +- 0.5 x prior range", sig_b2, D),
            run_dir("B3 Connors RSI(2) one-day", sig_b3, D), run_dir("B4 Double 7s one-day", sig_b4, D),
            run_dir("B5 Turtle Soup 20-day", sig_b5, D), run_dir("B6 Bollinger squeeze breakout", sig_b6, D),
            run_dir("B7 Supertrend(10,3) 15m", sig_b7, D, B), run_dir("B8 Holy Grail 15m", sig_b8, D, B), run_b9()]
    R = pd.DataFrame(rows); R.to_csv(f"{L.OUT}/book_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["cell", "n", "win", "avg", "total", "maxdd", "t", "p_boot", "mpos", "p_vs_rand", "rand_avg", "NIFTY", "SENSEX"]].to_string(index=False))
    print("Bonferroni: 9 cells -> pass needs p_boot and p_vs_rand < 0.0056")


def study_spot5y():
    """B3s/B4s context: the books' multi-day exits on the 5y daily index (close-to-close, gross bp; no option costs)."""
    D = daily().reset_index()
    for sym, g in D.groupby("sym"):
        g = g.reset_index(drop=True); c = g.c.values; sma5 = g.c.rolling(5).mean().values
        hi7, lo7 = g.c.rolling(7).max().values, g.c.rolling(7).min().values
        for nm, ent, ext in (("B3s RSI2", lambda t: g.rsi2_1[t + 1] < 10 and g.above_1[t + 1] == 1, lambda t: c[t] > sma5[t]),
                             ("B4s Double7", lambda t: g.low7_1[t + 1] == 1 and g.above_1[t + 1] == 1, lambda t: c[t] >= hi7[t])):
            out, t = [], 200
            while t < len(g) - 2:
                if ent(t):
                    u = t + 1
                    while u < len(g) - 1 and not ext(u): u += 1
                    out.append((g.day[t], (c[u] / c[t] - 1) * 1e4, u - t)); t = u
                t += 1
            O = pd.DataFrame(out, columns=["day", "bp", "days"])
            for h, G in (("2021-24", O[O.day < "2025-01-01"]), ("2025-26", O[O.day >= "2025-01-01"])):
                print(f"{nm} {sym} {h}: n {len(G)} avg {G.bp.mean():.1f}bp t {G.bp.mean() / (G.bp.std() / np.sqrt(len(G))):.2f} "
                      f"hold {G.days.mean():.1f}d win {(G.bp > 0).mean() * 100:.0f}%")


def study_selftest():
    """first_cross, caps bounds, _open skips a NaN 09:15."""
    s = np.full(NB, 100.0); s[50:] = 120.0
    assert first_cross(s, 110, 90) == (50, "CE") and first_cross(s, 130, 90) is None
    assert caps(9)["s_stp"] == 2.5 and caps(0.1)["s_stp"] == 0.5 and caps()["s_tgt"] == 2.5
    assert _open(np.r_[np.nan, 5.0, 6.0]) == 5.0
    print("book_lab selftest OK")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
