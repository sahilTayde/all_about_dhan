"""Round B: classic book / TradingView rules on the round-2 option panel (paper research; no orders).
Rules frozen before results (registry B1-B9): Crabel stretch+NR4, Williams k=0.5, Connors RSI(2) and Double 7s,
Turtle Soup, Bollinger squeeze, Supertrend(10,3) 15m, Holy Grail 15m, sell-after-event straddle.
Execution = sell_lab.struct, mode "cons", costs x1.5, p75 half-spread, buy ATM in the signal direction, spot exits capped
at 2.5 steps (D1), flat 15:15, entries 09:20..14:00. Daily bars from 1m closes (5y idx1m cache before the panel).
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python book_lab.py OUT [run|spot5y|selftest] [--holdout]"""
import sys, zlib, numpy as np, pandas as pd
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
        g["c1"] = c.shift(1); g["h250"] = g.h.shift(1).rolling(250).max(); g["l250"] = g.l.shift(1).rolling(250).min()
        g["ret1"] = c.pct_change().shift(1); g["rr1"] = r.shift(1) / r.shift(2).rolling(20).mean()
        s50 = c.rolling(50).mean(); g["tr_up"] = ((c > s50) & (s50 > s50.shift(5))).astype(float).shift(1)
        g["tr_dn"] = ((c < s50) & (s50 < s50.shift(5))).astype(float).shift(1)
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


def sig_b10(k, d):
    """Fibonacci pullback near the 52-week extreme (registry SC/B10): 61.8% pullback of today's swing, then a close back
    through 50% in the swing's direction; stop beyond 78.6%."""
    if not (np.isfinite(d.h250) and np.isfinite(d.l250) and np.isfinite(d.c1)): return []
    up, dn = d.c1 >= d.h250 * 0.985, d.c1 <= d.l250 * 1.015
    if up == dn: return []
    s = P[k]["spot"]; st = STEP[k[0]]; a = b = s[0]; pulled = False  # up: a = low, b = high since that low; dn: mirror
    for i in range(1, I_HI + 1):
        x = s[i]
        if not np.isfinite(x): continue
        if up:
            if x < a: a = b = x; pulled = False
            elif x > b: b = x; pulled = False
            w = b - a
            if w < 2 * st: continue
            if x <= b - 0.618 * w: pulled = True
            elif pulled and x > b - 0.5 * w and i >= 15: return [(i, "CE", caps((x - (b - 0.786 * w)) / st))]
        else:
            if x > a: a = b = x; pulled = False
            elif x < b: b = x; pulled = False
            w = a - b
            if w < 2 * st: continue
            if x >= b + 0.618 * w: pulled = True
            elif pulled and x < b + 0.5 * w and i >= 15: return [(i, "PE", caps(((b + 0.786 * w) - x) / st))]
    return []


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


def prep():
    D = daily()
    act = []  # B6: the squeeze flag stays on for 10 sessions, until the first band break (panel: 1m closes; history: daily h/l)
    for sym, g in D.groupby(level=0):
        cnt = 0
        for k, r in g.iterrows():
            if r.sq_1: cnt = 10
            on = cnt > 0; act.append(on); cnt = max(0, cnt - 1)
            if on and ((first_cross(P[k]["spot"], r.bbU_1, r.bbL_1) is not None) if k in P else (r.h > r.bbU_1 or r.l < r.bbL_1)): cnt = 0
    D["sq_act"] = act; return D


def study_run():
    D = prep(); B = bars15()
    rows = [run_dir("B1 Crabel stretch breakout, NR4 days", sig_b1, D), run_dir("B2 Williams open +- 0.5 x prior range", sig_b2, D),
            run_dir("B3 Connors RSI(2) one-day", sig_b3, D), run_dir("B4 Double 7s one-day", sig_b4, D),
            run_dir("B5 Turtle Soup 20-day", sig_b5, D), run_dir("B6 Bollinger squeeze breakout", sig_b6, D),
            run_dir("B7 Supertrend(10,3) 15m", sig_b7, D, B), run_dir("B8 Holy Grail 15m", sig_b8, D, B), run_b9()]
    R = pd.DataFrame(rows); R.to_csv(f"{L.OUT}/book_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["cell", "n", "win", "avg", "total", "maxdd", "t", "p_boot", "mpos", "p_vs_rand", "rand_avg", "NIFTY", "SENSEX"]].to_string(index=False))
    print("Bonferroni: 9 cells -> pass needs p_boot and p_vs_rand < 0.0056")


# ---------------------------------------------------------------- SC: scenario buckets, learn 60% / test 40% (registry SC)
def run_specs(gen, keys):
    """gen(k) -> (i, legs, kw) in time order; one position at a time; keeps (legs, kw) for the cost split."""
    T = []
    for k in keys:
        busy = -1
        for i, legs, kw in gen(k):
            if i <= busy: continue
            r = S.struct(k, i, legs, mode="cons", **kw)
            if r is None: continue
            T.append(dict(r, key=k, legs=legs, kw=kw)); busy = i + r["held"] - 1
    return pd.DataFrame(T)


def _long(sig, D, B=None):
    def g(k):
        if k not in D.index: return []
        d = D.loc[k]; xs = sig(k, d, B) if B is not None else sig(k, d)
        return [(i, [(sd, 0, 1)], dict(dirn=1 if sd == "CE" else -1, **ex)) for i, sd, ex in xs]
    return g


def strategies(D, B):
    days = sorted({k[1] for k in L.ALLK}); fomc1 = {next(d for d in days if d > f) for f in L.FOMC if any(d > f for d in days)}
    ex5 = S.E5X["t1.5_s1"]; dr = lambda sd: 1 if sd == "CE" else -1
    def e5g(fade, how):
        return lambda k: [(i, S.e5_legs(sd, how), dict(dirn=dr(sd), **ex5)) for i, sd in S.orb_signals(k, fade)]
    def rnd(k):
        rg = np.random.default_rng(zlib.crc32(repr(k).encode())); sd = "CE" if rg.integers(0, 2) == 0 else "PE"
        return [(int(rg.integers(I_LO, I_HI + 1)), [(sd, 0, 1)], dict(dirn=dr(sd), **caps()))]
    return {"S1 short straddle": lambda k: [(31, S.SSTRAD, dict(sstop=2))],
            "long straddle": lambda k: [(30, S.LSTRAD, dict(sstop=2.5))],
            "E5a ORB": e5g(False, "atm"), "E5 fade ATM": e5g(True, "atm"), "E5b fade credit spread": e5g(True, "cs"),
            "B1 Crabel": _long(sig_b1, D), "B2 Williams": _long(sig_b2, D), "B3 RSI2": _long(sig_b3, D),
            "B4 Double7": _long(sig_b4, D), "B5 Turtle Soup": _long(sig_b5, D), "B6 BB squeeze": _long(sig_b6, D),
            "B7 Supertrend": _long(sig_b7, D, B), "B8 Holy Grail": _long(sig_b8, D, B),
            "B9 sell after event": lambda k: [(60, S.SSTRAD, dict(sstop=2))] if k[1] in L.RBI else [(31, S.SSTRAD, dict(sstop=2))] if k[1] in fomc1 else [],
            "B10 Fibonacci 52w": _long(sig_b10, D), "RANDOM control": rnd}


def scen_table(D):
    """per sym-day scenario labels, all known before the decision (daily ones from prior days)."""
    V = L.vol_days().set_index(["sym", "day"]).or_iv; rows = []
    for sym in ("NIFTY", "SENSEX"):
        ks = [k for k in L.ALLK if k[0] == sym]; iv = np.array([S._iv(k, 1) for k in ks])
        for n, k in enumerate(ks):
            d = D.loc[k]; pr = iv[max(0, n - 60):n]; pr = pr[np.isfinite(pr)]
            q = (pr < iv[n]).mean() if len(pr) >= 20 and np.isfinite(iv[n]) else np.nan
            gp = d.o / d.c1 - 1
            rows.append(dict(key=k, gap="down" if gp < -0.003 else "up" if gp > 0.003 else "flat",
                             prevmove="big" if abs(d.ret1) > 0.01 else "small",
                             range="expand" if d.rr1 > 1.3 else "contract" if d.rr1 < 0.7 else "normal",
                             trend="up" if d.tr_up == 1 else "down" if d.tr_dn == 1 else "mixed",
                             hilo="near_high" if d.c1 >= d.h250 * 0.985 else "near_low" if d.c1 <= d.l250 * 1.015 else "mid",
                             iv="na" if q != q else "low" if q < 1 / 3 else "high" if q > 2 / 3 else "mid",
                             dte=str(min(P[k]["dte"], 2)).replace("2", "2+"), orv_day="calm" if V.get(k, np.nan) <= 1.0042 else "active"))
    return {r.pop("key"): r for r in rows}  # (sym, day) -> labels


def _pb(x, n=4000):
    return float((np.random.default_rng(5).choice(x, (n, len(x))).mean(1) <= 0).mean()) if len(x) > 1 else np.nan


def _cell(G):
    if not len(G): return dict(n=0, total=0, mean=np.nan, p=np.nan)
    g = G.groupby("day").pnl.sum().values; return dict(n=len(G), total=round(G.pnl.sum()), mean=round(G.pnl.mean()), p=_pb(g))


def cost_split(T):
    """per trade: gross (no spread, no charges), spread cost, charges at x1, by re-running the same trade."""
    hs0 = {kk: v.copy() for kk, v in L.HS.items()}; cm0 = L.CM; out = []
    def run(cm, hs_on):
        L.CM = cm
        for kk in L.HS: L.HS[kk][:] = hs0[kk] if hs_on else 0.0
        return np.array([S.struct(r.key, r.i, r.legs, mode="cons", **r.kw)["pnl"] for r in T.itertuples()])
    try:
        g, sp, c1 = run(0.0, False), run(0.0, True), run(1.0, True)
    finally:
        L.CM = cm0
        for kk in L.HS: L.HS[kk][:] = hs0[kk]
    return dict(gross=round(g.mean()), spread=round((g - sp).mean()), charges_x1=round((sp - c1).mean()),
                net_x1=round(c1.mean()), net_x15=round(T.pnl.mean()))


def study_scen():
    D = prep(); B = bars15(); SC = scen_table(D); COLS = list(next(iter(SC.values())))
    days = sorted({k[1] for k in L.ALLK}); cut = days[int(0.6 * len(days))]
    print(f"LEARN {days[0]}..{days[days.index(cut) - 1]} ({days.index(cut)} days), TEST {cut}..{days[-1]} ({len(days) - days.index(cut)} days)")
    ALL, CS = {}, []
    for nm, gen in strategies(D, B).items():
        T = run_specs(gen, L.ALLK)
        if not len(T): print(nm, "no trades"); continue
        for c in COLS: T[c] = [SC[k][c] for k in T.key]
        T["orv"] = np.where(T.i >= 30, T.orv_day, None)
        T["tod"] = np.where(T.i < 75, "morning", np.where(T.i < 195, "midday", "afternoon"))
        T["part"] = np.where(T.day < cut, "learn", "test"); ALL[nm] = T
        CS.append(dict(strategy=nm, n=len(T), **cost_split(T), learn=_cell(T[T.part == "learn"])["total"], test=_cell(T[T.part == "test"])["total"]))
        print(CS[-1], flush=True)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    print("\nCOST SPLIT per trade (Rs; 10 lots; all days):"); print(pd.DataFrame(CS).to_string(index=False))
    scs = [c for c in COLS if c != "orv_day"] + ["orv", "tod"]; rows = []
    for nm, T in ALL.items():
        for c in scs:
            for b, G in T.dropna(subset=[c]).groupby(c):
                lr, te = G[G.part == "learn"], G[G.part == "test"]
                if not len(lr): continue
                a = _cell(lr); z = _cell(te) if len(te) else dict(n=0, total=0, mean=np.nan, p=np.nan)
                rows.append(dict(strategy=nm, scen=c, bucket=b, ln=a["n"], lmean=a["mean"], ltot=a["total"], lp=round(a["p"], 3),
                                 tn=z["n"], tmean=z["mean"], ttot=z["total"], tp=round(z["p"], 3) if z["p"] == z["p"] else np.nan))
    C = pd.DataFrame(rows); C["sel"] = (C.ln >= 12) & (C.lmean > 0) & (C.lp < 0.10)
    C.to_csv(f"{L.OUT}/scen_cells.csv", index=False)
    Sel = C[C.sel]; ns = len(Sel); bon = 0.05 / max(ns, 1)
    print(f"\n{len(C)} cells; {ns} selected on LEARN (n>=12, mean>0, p<0.10); TEST pass needs total>0 and p<{bon:.4f}")
    print(Sel.drop(columns="sel").to_string(index=False))
    Sel_t, Rest = Sel[Sel.tn >= 5], C[~C.sel & (C.tn >= 5)]
    print(f"\nSKILL: selected cells positive on TEST {(Sel_t.ttot > 0).mean() * 100:.0f}% of {len(Sel_t)}; "
          f"not-selected cells positive on TEST {(Rest.ttot > 0).mean() * 100:.0f}% of {len(Rest)}")
    print("PASS:", Sel[(Sel.ttot > 0) & (Sel.tp < bon)][["strategy", "scen", "bucket", "tn", "ttot", "tp"]].to_string(index=False) or "none")
    print("\nUNION FILTER per strategy (TEST trades in any selected bucket) vs random TEST trades of that strategy:")
    rg = np.random.default_rng(21)
    for nm, T in ALL.items():
        s = Sel[Sel.strategy == nm]
        if not len(s): continue
        te = T[T.part == "test"]; m = np.zeros(len(te), bool)
        for r in s.itertuples(): m |= (te[r.scen] == r.bucket).values
        if not m.any(): continue
        tot = te.pnl[m].sum(); rnd = np.array([rg.choice(te.pnl.values, m.sum(), replace=False).sum() for _ in range(2000)])
        print(f"  {nm}: {len(s)} buckets, TEST kept {m.sum()}/{len(te)} trades, total {tot:,.0f} (all TEST {te.pnl.sum():,.0f}), "
              f"p vs random same-size {(rnd >= tot).mean():.3f}, p_boot {_pb(te[m].groupby('day').pnl.sum().values):.3f}")


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
