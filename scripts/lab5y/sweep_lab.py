"""E31: the 1-lakh variant sweep (paper research; no orders). Frozen rules: registry row E31 / side-session note E31_sweep_freeze.md.
Run (from scripts/lab5y, pandas venv):  ~/paper_extra_venv/bin/python sweep_lab.py OUT [count|run|select|placebo|report|selftest] [--round2]

Variant = base cell x gate. base cell = (signal config, structure/strike, exit); gate = ALL | DTE | ORW | GAP | TREND | PRNG | IVR | OPEN | SYM
(scen_lab.dfeat labels + or_iv calm/active + sym, all known before the decision). EVERY price comes from sell_lab.struct, mode "cons":
fills at the next 1m open +- the p75 half-spread, costs config/charges.yaml x1.5, 10 lots, flat at the 15:15 open, off-window legs
priced by bounds and flagged `forced` (D7: never an exit at the first missing bar). The sweep only (1) generates decisions and
(2) aggregates. `selftest` proves sample cells equal book_lab B1, sell_lab S1 / E5a and scen_lab PDB trade-for-trade.
Honest selection: rolling walk-forward per family, Hansen SPA (per family and GLOBAL over every variant of every round), deflated
Sharpe, random-entry placebo. Caches and CSVs go to OUT/sweep (outside the repo).
ponytail: pricing is one struct() call per trade (cached per cell, multiprocessing); vectorisation is at the gate/variant level,
where the work is. Ceiling ~1M struct calls per round (~10 min on 10 cores)."""
import sys, os, time, pickle, hashlib, math, itertools, numpy as np, pandas as pd
from multiprocessing import get_context
import opt1y_lab as L
import sell_lab as S
import book_lab as B
import scen_lab as Z

P, STEP, M0, NB, FLAT = L.P, L.STEP, L.M0, L.NB, L.FLAT
SW = f"{L.OUT}/sweep"; os.makedirs(SW, exist_ok=True)
ROUND2 = "--round2" in sys.argv
KEYS = list(L.ALLK); KI = {k: n for n, k in enumerate(KEYS)}
DAYS = sorted({k[1] for k in KEYS}); DI = {d: n for n, d in enumerate(DAYS)}; ND = len(DAYS)
MONTHS = sorted({L.month(d) for d in DAYS}); DM = np.array([MONTHS.index(L.month(d)) for d in DAYS])
TEST_MONTHS = [m for m in MONTHS if m >= "2026-02"]  # frozen: learn = every month before m
SGN = lambda sd: 1 if sd == "CE" else -1
I_LO, I_HI = 5, 285  # 09:20..14:00 decisions (book/scen convention); ND entries may run to 14:45


# ---------------------------------------------------------------- context per sym-day (built once in the parent, inherited by fork)
_CTX = {}
def ctx():
    if _CTX: return _CTX
    D = B.prep(); A = Z.labs()[0]; V = L.vol_days().set_index(["sym", "day"]); D["nr7"] = False
    for sym, g in D.groupby(level=0):
        r = (g.h - g.l).shift(1); D.loc[g.index, "nr7"] = (r <= r.rolling(7).min()).values  # yesterday narrowest of 7
    bars = {tf: _bars(tf) for tf in (5, 15)}
    H = {sym: g.reset_index(level=0, drop=True)[["o", "h", "l", "c"]] for sym, g in D.groupby(level=0)}
    for k in KEYS:
        s = P[k]["spot"]; f = pd.Series(s).ffill().bfill().values; hh = H[k[0]]; hist = hh[hh.index < k[1]].tail(20).values.tolist()
        _CTX[k] = dict(hist=hist, s=s, f=f, st=STEP[k[0]], d=D.loc[k] if k in D.index else None, a=A.loc[k], orv=V.or_iv.get(k, np.nan),
                       b5=bars[5].get(k), b15=bars[15].get(k), dte=P[k]["dte"])
    return _CTX


def _bars(tf):
    """continuous per-sym bars of `tf` minutes from the panel spot (o/h/l/c of minute closes), with EMA 5/8/9/20/21/34, MACD(12,26,9),
    supertrend (7|10, 2|3), RSI 2/5/14 computed on the continuous series; returned per sym-day (bar b -> decision minute tf*b+tf-1)."""
    out = {}
    for sym in ("NIFTY", "SENSEX"):
        rows = []
        for k in [k for k in KEYS if k[0] == sym]:
            f = pd.Series(P[k]["spot"]).ffill().bfill().values
            for b in range(NB // tf):
                x = f[tf * b:tf * b + tf]; rows.append(dict(day=k[1], b=b, o=x[0], h=x.max(), l=x.min(), c=x[-1]))
        G = pd.DataFrame(rows); c = G.c; h, l = G.h.values, G.l.values; n = len(G)
        for e in (5, 8, 9, 20, 21, 34): G[f"e{e}"] = c.ewm(span=e, adjust=False).mean()
        G["macd"] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); G["sig"] = G.macd.ewm(span=9, adjust=False).mean()
        pc = np.r_[np.nan, c.values[:-1]]; tr = np.nanmax(np.c_[h - l, abs(h - pc), abs(l - pc)], 1)
        for p_, m in itertools.product((7, 10), (2, 3)):
            atr = pd.Series(tr).ewm(alpha=1 / p_, adjust=False).mean().values; hl2 = (h + l) / 2; up, dn = hl2 - m * atr, hl2 + m * atr; t_ = np.ones(n)
            cv = c.values
            for t in range(1, n):
                if cv[t - 1] > up[t - 1]: up[t] = max(up[t], up[t - 1])
                if cv[t - 1] < dn[t - 1]: dn[t] = min(dn[t], dn[t - 1])
                t_[t] = 1 if (t_[t - 1] == -1 and cv[t] > dn[t - 1]) else -1 if (t_[t - 1] == 1 and cv[t] < up[t - 1]) else t_[t - 1]
            G[f"st{p_}_{m}"] = t_
        dl = c.diff()
        for r_ in (2, 5, 14):
            u = dl.clip(lower=0).ewm(alpha=1 / r_, adjust=False).mean(); d_ = (-dl.clip(upper=0)).ewm(alpha=1 / r_, adjust=False).mean()
            G[f"rsi{r_}"] = (100 - 100 / (1 + u / d_.replace(0, np.nan))).fillna(100)
        G["ph"], G["pl"] = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]; G["pr"] = np.r_[np.nan, (h - l)[:-1]]
        G["nr4"] = pd.Series(h - l).shift(1) <= pd.Series(h - l).shift(1).rolling(4).min()
        for d, g in G.groupby("day"): out[(sym, d)] = g.reset_index(drop=True)
    return out


# ---------------------------------------------------------------- directional signal generators: k -> [(i, side, override)]
def _first_cross(s, up, dn, lo, hi):
    for i in range(lo, hi + 1):
        if s[i] >= up: return [(i, "CE", {})]
        if s[i] <= dn: return [(i, "PE", {})]
    return []


def orb(k, W, conf, cut, bias):
    """first close beyond the 09:15..09:15+W range by conf x range; bias: CE only above the running mean (TWAP), PE below."""
    c = ctx()[k]; s = c["s"]; hi, lo = np.nanmax(s[:W + 1]), np.nanmin(s[:W + 1]); r = conf * (hi - lo)
    for i in range(W + 1, cut + 1):
        up, dn = s[i] > hi + r, s[i] < lo - r
        if not (up or dn): continue
        if bias and ((up and s[i] < np.nanmean(s[:i + 1])) or (dn and s[i] > np.nanmean(s[:i + 1]))): return []
        return [(i, "CE" if up else "PE", {})]
    return []


def orb_fade(k, W, N):
    """an ORB break that closes back inside within N bars -> the other side (E5 fade generalised; W=30, N=15 = sell_lab)."""
    s = ctx()[k]["s"]; hi, lo = np.nanmax(s[:W + 1]), np.nanmin(s[:W + 1])
    for i in range(W + 1, 166):
        up, dn = s[i] > hi, s[i] < lo
        if not (up or dn): continue
        for j in range(i + 1, min(i + N + 1, 166)):
            if lo <= s[j] <= hi: return [(j, "PE" if up else "CE", {})]
        return []
    return []


def pdb(k, lvl, by, rej):
    """break of yesterday's high/low (lvl='hl') or close (lvl='c') by `by` steps after 09:45; rej: fade a break that fails within rej bars."""
    c = ctx()[k]; s = c["f"]; a = c["a"]; st = c["st"]
    if lvl == "hl": H, Lo = a.PDH, a.PDL
    else: H = Lo = (c["d"].c1 if c["d"] is not None else np.nan)
    if not (np.isfinite(H) and np.isfinite(Lo)): return []
    H2, L2 = H + by * st, Lo - by * st; okc, okp = s[30] <= H2, s[30] >= L2
    for i in range(31, 286):
        hit = "CE" if okc and s[i - 1] <= H2 < s[i] else "PE" if okp and s[i - 1] >= L2 > s[i] else None
        if not hit: continue
        if not rej: return [(i, hit, {})]
        for j in range(i + 1, min(i + rej, 285) + 1):
            if (hit == "CE" and s[j] <= H) or (hit == "PE" and s[j] >= Lo): return [(j, "PE" if hit == "CE" else "CE", {})]
        return []
    return []


def twap(k, thr, how, fade, start=46):
    """deviation of spot from the running session mean: thr in steps (how='step') or in sigmas of the deviation (how='sd');
    fade -> against the deviation, else with it. First crossing only."""
    c = ctx()[k]; s = c["f"]; st = c["st"]; d = s - np.cumsum(s) / np.arange(1, NB + 1)
    if how == "sd":
        sd = np.array([d[max(0, i - 60):i + 1].std() for i in range(NB)]); z = d / np.where(sd > 0, sd, np.inf)
    else: z = d / st
    for i in range(start, 286):
        if abs(z[i]) >= thr and abs(z[i - 1]) < thr:
            up = z[i] > 0; return [(i, ("PE" if up else "CE") if fade else ("CE" if up else "PE"), {})]
    return []


def crabel(k, filt, kk, exact):
    """Crabel stretch breakout: open +- kk x stretch(10) on NR4 / NR7 / any day. exact: book_lab B1 (NR4, kk=1, stop 2 x stretch)."""
    c = ctx()[k]; d = c["d"]
    if d is None or not np.isfinite(d.stretch): return []
    if filt == "nr4" and not d.nr4: return []
    if filt == "nr7" and not d.nr7: return []
    s = c["s"]; o = B._open(s); x = _first_cross(s, o + kk * d.stretch, o - kk * d.stretch, I_LO, I_HI)
    if x and exact: x = [(x[0][0], x[0][1], B.caps(2 * d.stretch / c["st"]))]
    return x


def williams(k, kk):
    c = ctx()[k]; d = c["d"]
    if d is None or not np.isfinite(d.R1): return []
    s = c["s"]; o = B._open(s); return _first_cross(s, o + kk * d.R1, o - kk * d.R1, I_LO, I_HI)


def momentum(k, h, thr, fade, start=30):
    """first bar where the h-bar spot change reaches thr steps; with it or against it."""
    c = ctx()[k]; s = c["f"]; st = c["st"]
    for i in range(max(start, h), 286):
        m = (s[i] - s[i - h]) / st
        if abs(m) >= thr:
            up = m > 0; return [(i, ("PE" if up else "CE") if fade else ("CE" if up else "PE"), {})]
    return []


def gap(k, g, fade, at):
    """opening gap vs yesterday's close of at least g%: fade (toward the prior close) or go (with the gap), decided at bar `at`."""
    c = ctx()[k]; d = c["d"]
    if d is None or not np.isfinite(d.c1): return []
    s = c["f"]; gp = s[0] / d.c1 - 1
    if abs(gp) < g / 100: return []
    up = gp > 0; return [(at, ("PE" if up else "CE") if fade else ("CE" if up else "PE"), {})]


def ema_x(k, tf, fast, slow):
    g = ctx()[k][f"b{tf}"]
    if g is None: return []
    a, b = g[f"e{fast}"].values, g[f"e{slow}"].values; out = []
    for t in range(1, len(g)):
        if (a[t] > b[t]) != (a[t - 1] > b[t - 1]): out.append((tf * t + tf - 1, "CE" if a[t] > b[t] else "PE", {}))
    return out


def macd_x(k, tf):
    g = ctx()[k][f"b{tf}"]
    if g is None: return []
    a, b = g.macd.values, g.sig.values
    return [(tf * t + tf - 1, "CE" if a[t] > b[t] else "PE", {}) for t in range(1, len(g)) if (a[t] > b[t]) != (a[t - 1] > b[t - 1])]


def supertrend(k, tf, p_, m):
    g = ctx()[k][f"b{tf}"]
    if g is None: return []
    t_ = g[f"st{p_}_{m}"].values
    return [(tf * t + tf - 1, "CE" if t_[t] == 1 else "PE", {}) for t in range(1, len(g)) if t_[t] != t_[t - 1]]


def rsi(k, tf, n, lo, fade):
    """RSI(n) on tf-minute bars crossing below lo / above 100-lo: fade (buy CE at the low) or follow (buy PE at the low)."""
    g = ctx()[k][f"b{tf}"]
    if g is None: return []
    r = g[f"rsi{n}"].values; out = []
    for t in range(1, len(g)):
        if r[t] < lo <= r[t - 1]: out.append((tf * t + tf - 1, "CE" if fade else "PE", {}))
        elif r[t] > 100 - lo >= r[t - 1]: out.append((tf * t + tf - 1, "PE" if fade else "CE", {}))
    return out


def inside15(k, nr):
    """break of an inside 15m bar (or, nr=True, of the narrowest-of-4 15m bar) at the next bar's close beyond it."""
    g = ctx()[k]["b15"]
    if g is None: return []
    h, l, ph, pl, c, nr4 = g.h.values, g.l.values, g.ph.values, g.pl.values, g.c.values, g.nr4.values; out = []
    for t in range(2, len(g)):
        ok = nr4[t] if nr else (h[t - 1] <= ph[t - 1] and l[t - 1] >= pl[t - 1])
        if not ok: continue
        if c[t] > h[t - 1]: out.append((15 * t + 14, "CE", {}))
        elif c[t] < l[t - 1]: out.append((15 * t + 14, "PE", {}))
    return out


def book(k, which):
    """book_lab day-level rules (B3 RSI2, B4 Double 7s, B5 Turtle Soup, B6 squeeze, B10 Fibonacci) with their own stops."""
    c = ctx()[k]; d = c["d"]
    if d is None: return []
    f = {"b3": B.sig_b3, "b4": B.sig_b4, "b5": B.sig_b5, "b6": B.sig_b6, "b10": B.sig_b10}[which]
    return [(i, sd, ex) for i, sd, ex in f(k, d)]


def fib(k):
    c = ctx()[k]; return [(i, sd, {}) for i, sd in Z.fib(c["f"], c["st"])]


def oiflow(k, h, thr, against):
    """ATM OI flow over h bars (PE OI build minus CE OI build, / total), same strike: > thr -> CE (writers' convention), against flips."""
    p = P[k]; out = []
    for i in range(max(31, h), 286):
        K = p["atm"][i]; j = i - h
        oc, op, oc0, op0 = (L._get(k, sd, K, b, 4) for sd, b in (("CE", i), ("PE", i), ("CE", j), ("PE", j)))
        if not all(np.isfinite([oc, op, oc0, op0])) or oc + op <= 0: continue
        x = ((op - op0) - (oc - oc0)) / (op + oc)
        if abs(x) >= thr: out.append((i, ("CE" if x > 0 else "PE") if not against else ("PE" if x > 0 else "CE"), {}))
    return out


def tod(k, which):
    """time-of-day rules: first-hour direction (10:15 -> entry at 10:15 / 10:30 / 10:45), lunch reversal (13:00 against the
    morning move), last-hour continuation (14:15 with the day's move)."""
    s = ctx()[k]["f"]
    if which == "lunch": return [(225, "PE" if s[225] > s[0] else "CE", {})]
    if which == "last": return [(300, "CE" if s[300] > s[0] else "PE", {})]
    at = {"fh60": 60, "fh75": 75, "fh90": 90}[which]; return [(at, "CE" if s[60] > s[0] else "PE", {})] if s[60] != s[0] else []


def pm_orb(k, fade):
    """break of the 11:30-13:00 range after 13:00 (afternoon ORB), with it or faded on re-entry within 15 bars."""
    s = ctx()[k]["f"]; hi, lo = s[135:226].max(), s[135:226].min()
    for i in range(226, 331):
        up, dn = s[i] > hi, s[i] < lo
        if not (up or dn): continue
        if not fade: return [(i, "CE" if up else "PE", {})]
        for j in range(i + 1, min(i + 16, 331)):
            if lo <= s[j] <= hi: return [(j, "PE" if up else "CE", {})]
        return []
    return []


# ---------------------------------------------------------------- non-directional entries: k -> [(i, None, {})]
def nd_time(k, i): return [(i, None, {})]


def nd_shock(k, thr):
    """E13 unfiltered: the first thr-step spot move from 09:45 (by 14:00) -> decide on that bar."""
    s = ctx()[k]["f"]; st = ctx()[k]["st"]
    for j in range(31, 286):
        if abs(s[j] - s[30]) >= thr * st: return [(j, None, {})]
    return []


def nd_iv(k, thr):
    """ATM IV change over 15 bars (same strike) crossing thr IV points (thr < 0: a fall) after 09:46, first bar."""
    p = P[k]
    for i in range(46, 286):
        K = p["atm"][i]; v = [L._get(k, sd, K, b, 5) for sd, b in (("CE", i), ("PE", i), ("CE", i - 15), ("PE", i - 15))]
        if not all(np.isfinite(v)): continue
        d = (v[0] + v[1] - v[2] - v[3]) / 2
        if (thr > 0 and d >= thr) or (thr < 0 and d <= thr): return [(i, None, {})]
    return []


def nd_range(k, W, at=135):
    """no break of the 09:15..W opening range by `at` (11:30) -> range day, enter at `at`."""
    s = ctx()[k]["s"]; hi, lo = np.nanmax(s[:W + 1]), np.nanmin(s[:W + 1])
    return [] if (np.nanmax(s[W + 1:at + 1]) > hi or np.nanmin(s[W + 1:at + 1]) < lo) else [(at, None, {})]


def nd_break(k):
    """enter on the first 09:15-09:45 range break (sell / buy the vol after the break)."""
    x = orb(k, 30, 0, 165, False); return [(x[0][0], None, {})] if x else []


# ---------------------------------------------------------------- round 2 (pattern loop, Fable 2026-11-12 after round 1): refinements of the
# only positive regions. Day conditions embedded in the signal so the 22 gates give two-gate combinations. All counted in the global SPA.
def crabel2(k, win, kk, filt):
    """Crabel stretch with a `win`-day stretch window (10 = book) and k; filt any / nr4."""
    c = ctx()[k]; d = c["d"]
    if d is None or (filt == "nr4" and not d.nr4): return []
    h = c["hist"]
    if len(h) < win or any(not np.isfinite(x) for r in h[-win:] for x in r): return []
    stretch = np.mean([min(x[1] - x[0], x[0] - x[2]) for x in h[-win:]])
    if not stretch > 0: return []
    s = c["s"]; o = B._open(s); x = _first_cross(s, o + kk * stretch, o - kk * stretch, I_LO, I_HI)
    return [(x[0][0], x[0][1], B.caps(2 * stretch / c["st"]))] if x else []


def _daycond(k, cond):
    c = ctx()[k]; a = c["a"]
    return {"dte0": c["dte"] == 0, "narrow": a.get("ORW") == "NARROW", "up": a.get("TREND") == "UP", "wr": a.get("PRNG") == "WIDE", "": True}[cond]


def nd2(k, base, cond):
    if not _daycond(k, cond): return []
    return {"t1030": lambda: nd_time(k, 75), "ivfall1.0": lambda: nd_iv(k, -1.0), "ivfall1.5": lambda: nd_iv(k, -1.5), "ivfall2.0": lambda: nd_iv(k, -2.0)}[base]()


def mom2(k, h, thr, cond):
    return momentum(k, h, thr, True) if _daycond(k, cond) else []


# ---------------------------------------------------------------- the catalogue
def signals():
    """[(family, name, fn, lo, hi)]; lo/hi = decision window in bars."""
    D = []
    def add(fam, name, fn, lo=I_LO, hi=I_HI): D.append((fam, name, fn, lo, hi))
    for W, conf, cut, bias in itertools.product((15, 30, 45, 60), (0, 0.25), (120, 165, 285), (False, True)):
        add("ORB", f"orb_W{W}_c{conf}_cut{cut}{'_bias' if bias else ''}", lambda k, W=W, conf=conf, cut=cut, bias=bias: orb(k, W, conf, cut, bias))
    for W, N in itertools.product((15, 30, 45, 60), (10, 15, 30)): add("ORBFADE", f"orbfade_W{W}_N{N}", lambda k, W=W, N=N: orb_fade(k, W, N))
    for lvl, by, rej in itertools.product(("hl", "c"), (0, 0.5), (0, 15, 30)): add("PDB", f"pd{lvl}_by{by}_rej{rej}", lambda k, lvl=lvl, by=by, rej=rej: pdb(k, lvl, by, rej))
    for how, thr, fade in itertools.product(("step", "sd"), (1.5, 2, 3), (True, False)): add("TWAP", f"twap_{how}{thr}_{'fade' if fade else 'go'}", lambda k, how=how, thr=thr, fade=fade: twap(k, thr, how, fade))
    for filt, kk in itertools.product(("nr4", "nr7", "any"), (0.5, 1, 1.5)): add("CRABEL", f"crabel_{filt}_k{kk}", lambda k, filt=filt, kk=kk: crabel(k, filt, kk, False))
    add("CRABEL", "crabel_nr4_k1_B1exact", lambda k: crabel(k, "nr4", 1, True))
    for kk in (0.3, 0.5, 0.7, 1.0): add("WILLIAMS", f"williams_k{kk}", lambda k, kk=kk: williams(k, kk))
    for h, thr, fade in itertools.product((5, 15, 30, 60), (1, 2, 3), (False, True)): add("MOM", f"mom_h{h}_t{thr}_{'fade' if fade else 'go'}", lambda k, h=h, thr=thr, fade=fade: momentum(k, h, thr, fade))
    for g, fade, at in itertools.product((0.2, 0.4, 0.7), (True, False), (5, 15, 30)): add("GAP", f"gap{g}_{'fade' if fade else 'go'}_at{at}", lambda k, g=g, fade=fade, at=at: gap(k, g, fade, at))
    for tf, (f_, s_) in itertools.product((5, 15), ((5, 20), (9, 21), (8, 34))): add("EMA", f"ema{tf}m_{f_}x{s_}", lambda k, tf=tf, f_=f_, s_=s_: ema_x(k, tf, f_, s_))
    for tf in (5, 15): add("EMA", f"macd{tf}m", lambda k, tf=tf: macd_x(k, tf))
    for tf, p_, m in itertools.product((5, 15), (7, 10), (2, 3)): add("SUPERTREND", f"st{tf}m_{p_}_{m}", lambda k, tf=tf, p_=p_, m=m: supertrend(k, tf, p_, m))
    for n, lo, fade in itertools.product((2, 5, 14), (10, 20, 30), (True, False)): add("RSI", f"rsi5m_{n}_{lo}_{'fade' if fade else 'go'}", lambda k, n=n, lo=lo, fade=fade: rsi(k, 5, n, lo, fade))
    add("IB15", "inside15", lambda k: inside15(k, False)); add("IB15", "nr4_15m", lambda k: inside15(k, True))
    for w in ("b3", "b4", "b5", "b6", "b10"): add("BOOKDAY", w, lambda k, w=w: book(k, w))
    add("FIB", "fib618", fib)
    for h, thr, ag in itertools.product((15, 30), (0.05, 0.1), (False, True)): add("OIFLOW", f"oiflow_h{h}_t{thr}{'_against' if ag else ''}", lambda k, h=h, thr=thr, ag=ag: oiflow(k, h, thr, ag))
    for w in ("fh60", "fh75", "fh90", "lunch"): add("TOD", w, lambda k, w=w: tod(k, w))
    add("TOD", "last", lambda k: tod(k, "last"), 5, 330)
    add("PMORB", "pm_orb_go", lambda k: pm_orb(k, False), 5, 330); add("PMORB", "pm_orb_fade", lambda k: pm_orb(k, True), 5, 330)
    # non-directional entries (side None); window to 14:45
    for nm, i in (("0920", 5), ("0946", 31), ("1030", 75), ("1130", 135), ("1230", 195), ("1300", 225), ("1345", 270), ("1415", 300)):
        add("ND", f"t{nm}", lambda k, i=i: nd_time(k, i), 5, 330)
    for thr in (1.5, 2, 2.5): add("ND", f"shock{thr}", lambda k, thr=thr: nd_shock(k, thr), 5, 330)
    for thr in (0.5, 1.0, -0.5, -1.0): add("ND", f"iv{'rise' if thr > 0 else 'fall'}{abs(thr)}", lambda k, thr=thr: nd_iv(k, thr), 5, 330)
    for W in (30, 60): add("ND", f"rangeday_W{W}", lambda k, W=W: nd_range(k, W), 5, 330)
    add("ND", "afterbreak", nd_break, 5, 330)
    # round 2
    for win, kk, filt in itertools.product((5, 10, 20), (0.75, 1, 1.25), ("any", "nr4")): add("CRABEL", f"crabel2_w{win}_k{kk}_{filt}", lambda k, win=win, kk=kk, filt=filt: crabel2(k, win, kk, filt))
    for base, cond in itertools.product(("t1030", "ivfall1.0", "ivfall1.5", "ivfall2.0"), ("dte0", "narrow", "up")): add("ND", f"{base}_{cond}", lambda k, base=base, cond=cond: nd2(k, base, cond), 5, 330)
    for h, thr, cond in itertools.product((30, 45, 60), (2.5, 3, 4), ("", "wr")): add("MOM", f"mom2_h{h}_t{thr}_fade{'_' + cond if cond else ''}", lambda k, h=h, thr=thr, cond=cond: mom2(k, h, thr, cond))
    for g, at in itertools.product((0.2, 0.3, 0.4), (30, 45, 60)): add("GAP", f"gap2_{g}_go_at{at}", lambda k, g=g, at=at: gap(k, g, False, at))
    for kk in (0.8, 1.0, 1.2): add("WILLIAMS", f"williams2_k{kk}", lambda k, kk=kk: williams(k, kk))
    return D


STRIKE = {"ATM": 0, "ITM1": 1, "ITM2": 2, "OTM1": -1, "OTM2": -2}
def legs_dir(sd, strike):
    if strike == "CS": return S.e5_legs(sd, "cs")
    m = STRIKE[strike]; return [(sd, -m if sd == "CE" else m, 1)]


ND_LEGS = {"SHORT_STRAD": S.SSTRAD, "STRANGLE1": [("CE", 1, -1), ("PE", -1, -1)], "STRANGLE2": [("CE", 2, -1), ("PE", -2, -1)],
           "IFLY2": S.ifly(2), "IFLY3": S.ifly(3), "ICON12": S.icon(1, 2), "LONG_STRAD": S.LSTRAD, "LONG_STRANGLE1": [("CE", 1, 1), ("PE", -1, 1)]}
ND_SHORT = ["SHORT_STRAD", "STRANGLE1", "STRANGLE2", "IFLY2", "IFLY3", "ICON12"]

# directional exits: (name, s_tgt, s_stp, hold minutes or None, trail)
DX_FULL = [("t1_s0.5", 1, 0.5, None, None), ("t1_s1", 1, 1, None, None), ("t1.5_s1", 1.5, 1, None, None), ("t2_s1", 2, 1, None, None),
           ("t2.5_s1", 2.5, 1, None, None), ("t2_s2", 2, 2, None, None), ("t1_s0.5_h60", 1, 0.5, 60, None), ("t2_s1_h60", 2, 1, 60, None),
           ("trail30", 2.5, 1.5, None, 0.3), ("t2_s1_h120", 2, 1, 120, None), ("t1.5_s1_h60", 1.5, 1, 60, None), ("t3_s1.5", 3, 1.5, None, None)]
DX_SMALL = [DX_FULL[i] for i in (2, 3, 4, 6)]
DX_CS = [DX_FULL[i] for i in (1, 2, 3)]
DX_SIG = [("sig", None, None, None, None)]  # the signal's own stop (book rules)
# non-directional exits
NX_SHORT = [(f"spot{s}{'_stop' + str(x) if x else ''}", dict(sstop=s, **({"stop": x} if x else {}))) for s in (1, 1.5, 2, 2.5) for x in (None, 0.3, 0.6)]
NX_SHORT += [("spot2_tgt0.5", dict(sstop=2, tgt=0.5)), ("spot2.5_trail30", dict(sstop=2.5, trail=0.3))]
NX_LONG = [(f"spot{s}{'_h' + str(h) if h else ''}", dict(sstop=s, **({"hold": h} if h else {}))) for s in (1.5, 2, 2.5) for h in (None, 60, 120)]


def cells():
    """[(cell_id, family, sig_name, struct, exit_name)] = the base grid. Round 2 adds to it (never removes)."""
    out = []
    for fam, nm, fn, lo, hi in signals():
        if any(nm.startswith(x) for x in ("crabel2", "mom2", "gap2", "williams2")) or nm.split("_")[-1] in ("dte0", "narrow", "up"): continue  # round 2
        if fam == "ND":
            for sname in ND_LEGS:
                for xn, _ in (NX_SHORT if sname in ND_SHORT else NX_LONG): out.append((fam + "_" + sname, nm, sname, xn))
            continue
        for strike in ("ATM", "ITM1", "OTM1"):
            for x in DX_FULL: out.append((fam, nm, strike, x[0]))
        for strike in ("ITM2", "OTM2"):
            for x in DX_SMALL: out.append((fam, nm, strike, x[0]))
        for x in DX_CS: out.append((fam, nm, "CS", x[0]))
        if fam in ("CRABEL", "BOOKDAY"): out.append((fam, nm, "ATM", "sig"))
    if ROUND2: out += round2_cells()
    return out


def round2_cells():
    """pattern-loop refinements (Fable, after round 1); listed here so the global SPA counts them. ~430 cells."""
    out = []; X5 = ["t1_s1", "t1.5_s1", "t2_s1", "t2_s2", "sig"]; X3 = ["t1_s0.5", "t1_s1", "t1.5_s1"]
    for fam, nm, fn, lo, hi in signals():
        if nm.startswith("crabel2"): out += [(fam, nm, st, x) for st in ("ATM", "OTM1") for x in X5]
        elif fam == "ND" and ("_dte0" in nm or "_narrow" in nm or "_up" in nm):
            out += [("ND_" + st, nm, st, x) for st in ("SHORT_STRAD", "STRANGLE1") for x in ("spot1.5", "spot1.5_stop0.3", "spot2", "spot2_stop0.3")]
        elif nm.startswith("mom2"): out += [(fam, nm, st, x) for st in ("ATM", "OTM1") for x in X3]
        elif nm.startswith("gap2"): out += [(fam, nm, st, x) for st in ("ATM", "OTM1") for x in ("t1_s1", "t1.5_s1", "t2_s1")]
        elif nm.startswith("williams2"): out += [(fam, nm, st, x) for st in ("ATM", "OTM1") for x in ("t2_s1", "t2.5_s1", "t3_s1.5")]
    return out


# ---------------------------------------------------------------- pricing of one cell (worker)
_SIG = None
def _sigmap():
    global _SIG
    if _SIG is None: _SIG = {nm: (fn, lo, hi) for fam, nm, fn, lo, hi in signals()}
    return _SIG


def _exit_kw(xn, i, sd, ov):
    if xn == "sig": return dict(dirn=SGN(sd), **ov)
    if sd is None:
        kw = dict(next(v for n, v in NX_SHORT + NX_LONG if n == xn)); h = kw.pop("hold", None)
        if h: kw["flat"] = min(FLAT, M0 + i + 1 + h)
        return kw
    _, t, s_, h, tr = next(x for x in DX_FULL if x[0] == xn)
    kw = dict(dirn=SGN(sd), s_tgt=t, s_stp=s_)
    if h: kw["flat"] = min(FLAT, M0 + i + 1 + h)
    if tr: kw["trail"] = tr
    return kw


def price_cell(cell):
    """-> structured rows (key index, i, side, pnl, held, forced, why) for one base cell; one position at a time per sym-day."""
    fam, nm, struct, xn = cell; fn, lo, hi = _sigmap()[nm]; rows = []
    for k in KEYS:
        busy = -1
        for i, sd, ov in fn(k):
            if i < lo or i > hi or i <= busy: continue
            legs = ND_LEGS[struct] if sd is None else legs_dir(sd, struct)
            r = S.struct(k, i, legs, mode="cons", **_exit_kw(xn, i, sd, ov))
            if r is None: continue
            rows.append((KI[k], i, 0 if sd is None else SGN(sd), r["pnl"], r["held"], r["forced"], r["why"])); busy = i + r["held"] - 1
    return np.array(rows, dtype=[("k", "i2"), ("i", "i2"), ("sd", "i1"), ("pnl", "f8"), ("held", "i2"), ("forced", "?"), ("why", "U6")])


_SRC = hashlib.md5(b"".join(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f), "rb").read()
                            for f in ("sell_lab.py", "opt1y_lab.py")) + f"{L.COSTS}/{L.STALE_OK}".encode()).hexdigest()[:8]  # + cost/guard mode


def _cache(cell):
    return f"{SW}/c_{hashlib.md5(('|'.join(cell) + _SRC).encode()).hexdigest()[:14]}.pkl"


def run_cells(cs, procs=None):
    """price every cell not yet cached (fork pool); returns {cell: rows}."""
    ctx(); todo = [c for c in cs if not os.path.exists(_cache(c))]
    print(f"cells {len(cs)}, to price {len(todo)}", flush=True); t0 = time.time()
    if todo:
        with get_context("fork").Pool(procs or max(1, os.cpu_count() - 1)) as pool:
            for n, (c, r) in enumerate(zip(todo, pool.imap(price_cell, todo, chunksize=4))):
                pickle.dump(r, open(_cache(c), "wb"))
                if n % 200 == 0: print(f"  {n}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    return {c: pickle.load(open(_cache(c), "rb")) for c in cs}


# ---------------------------------------------------------------- gates and variants
GATES = [("ALL", None, None)] + [(f"DTE={v}", "DTE", v) for v in ("0", "1", "2+")] + [(f"ORW={v}", "ORW", v) for v in Z.BK["ORW"]] \
    + [(f"GAP={v}", "GAP", v) for v in Z.BK["GAP"]] + [(f"TREND={v}", "TREND", v) for v in Z.BK["TREND"]] + [(f"PRNG={v}", "PRNG", v) for v in Z.BK["PRNG"]] \
    + [(f"IVR={v}", "IVR", v) for v in Z.BK["IVR"]] + [("OPEN=calm", "OPEN", "calm"), ("OPEN=active", "OPEN", "active")] + [("SYM=NIFTY", "SYM", "NIFTY"), ("SYM=SENSEX", "SYM", "SENSEX")]


LATE = [n for n, g in enumerate(GATES) if g[1] in ("ORW", "OPEN")]  # gates that need the 09:15-09:45 bars


def gate_matrix():
    """(n_keys, n_gates) bool."""
    C = ctx(); G = np.zeros((len(KEYS), len(GATES)), bool)
    for n, k in enumerate(KEYS):
        a = C[k]["a"]; lab = dict(a.to_dict(), OPEN="calm" if C[k]["orv"] <= 1.0042 else "active" if np.isfinite(C[k]["orv"]) else None, SYM=k[0])
        for g, (gn, col, v) in enumerate(GATES): G[n, g] = True if col is None else lab.get(col) == v
    return G


def variants(R):
    """R: {cell: rows}. -> (table DataFrame, daily P&L float32 (V, ND), trade-day lists for placebo). One row per cell x gate with >= 1 trade."""
    G = gate_matrix(); kd = np.array([DI[k[1]] for k in KEYS]); rows = []; daily = []; tk = []
    for cell, r in R.items():
        if not len(r): continue
        gm = G[r["k"]].copy(); pnl = r["pnl"]; d = kd[r["k"]]; m = DM[d]; isn = np.array([KEYS[x][0] == "NIFTY" for x in r["k"]])
        gm[np.ix_(r["i"] < 30, LATE)] = False  # ORW / OPEN are known at 09:45: a decision before bar 30 cannot use them (causality fix)
        n = gm.sum(0); ok = n > 0
        for g in np.flatnonzero(ok):
            mk = gm[:, g]; v = pnl[mk]; dd_ = np.bincount(d[mk], weights=v, minlength=ND)
            cum = np.cumsum(dd_); mdd = (cum - np.maximum.accumulate(np.maximum(cum, 0))).min()
            w = v[v > 0]; l_ = v[v <= 0]
            rows.append(dict(family=cell[0], signal=cell[1], struct=cell[2], exit=cell[3], gate=GATES[g][0], n=len(v), win=(v > 0).mean() * 100,
                             total=v.sum(), avg=v.mean(), payoff=(w.mean() / -l_.mean()) if len(w) and len(l_) and l_.mean() < 0 else np.nan,
                             maxdd=mdd, forced=r["forced"][mk].mean() * 100, late5=v[m[mk] >= MONTHS.index("2026-06")].sum(),
                             NIFTY=v[isn[mk]].sum()))
            daily.append(dd_.astype(np.float32)); tk.append(r["k"][mk])
    T = pd.DataFrame(rows); X = np.stack(daily) if daily else np.zeros((0, ND), np.float32)
    T["id"] = T.family + "|" + T.signal + "|" + T.struct + "|" + T.exit + "|" + T.gate
    return T, X, tk


# ---------------------------------------------------------------- honest selection
def tstat(X, cols):
    """daily t-stat over a day subset: mean / se (days with no trade count as 0 P&L)."""
    Y = X[:, cols]; n = Y.shape[1]; mu = Y.mean(1); sd = Y.std(1, ddof=1) + 1e-9; return mu / sd * np.sqrt(n)


def walk_forward(T, X):
    """per family: for each test month pick the learn-best variant (daily t-stat; >= 20 learn trades, forced <= 5%) -> its test P&L."""
    out = {}; T["wf_oos"] = 0.0; T["wf_picks"] = 0
    for fam, idx in T.groupby("family").indices.items():
        idx = np.asarray(idx); oos = np.zeros(ND, np.float32); picks = []
        for m in TEST_MONTHS:
            mi = MONTHS.index(m); learn = np.flatnonzero(DM < mi); test = np.flatnonzero(DM == mi)
            nl = (X[idx][:, learn] != 0).sum(1); ok = (nl >= 20) & (T.forced.values[idx] <= 5)
            if not ok.any(): picks.append(None); continue
            ts = np.where(ok, tstat(X[idx], learn), -np.inf); b = idx[int(np.argmax(ts))]
            oos[test] += X[b, test]; picks.append(b); T.loc[b, "wf_oos"] += float(X[b, test].sum()); T.loc[b, "wf_picks"] += 1
        g = oos[DM >= MONTHS.index(TEST_MONTHS[0])]; mo = [float(oos[DM == MONTHS.index(m)].sum()) for m in TEST_MONTHS]
        bs = np.random.default_rng(5).choice(g, (5000, len(g))).mean(1)
        out[fam] = dict(oos=float(oos.sum()), oos_p=float((bs <= 0).mean()), oos_mpos=int(sum(x > 0 for x in mo)), picks=picks,
                        oos_trades=int(sum((X[b][DM == MONTHS.index(m)] != 0).sum() for b, m in zip(picks, TEST_MONTHS) if b is not None)))
    return out


def spa(X, B_=1000, q=0.2, seed=7, chunk=20000):
    """Hansen (2005) SPA consistent p-value for 'the best of these variants has mean daily P&L > 0' (benchmark 0): stationary bootstrap
    (mean block 1/q days). Returns (p, T, best index). X: (V, n)."""
    V, n = X.shape
    if V == 0: return 1.0, 0.0, -1
    rg = np.random.default_rng(seed); C = np.zeros((B_, n), np.float32)
    for b in range(B_):
        idx = np.empty(n, int); idx[0] = rg.integers(n)
        for t in range(1, n): idx[t] = rg.integers(n) if rg.random() < q else (idx[t - 1] + 1) % n
        C[b] = np.bincount(idx, minlength=n)
    C /= n; d = X.mean(1).astype(np.float64); Tmax = np.full(B_, -np.inf); tk = np.full(V, -np.inf); rn = math.sqrt(n)
    for a in range(0, V, chunk):
        Y = X[a:a + chunk].astype(np.float32); M = C @ Y.T  # (B, v) bootstrap means
        dev = rn * (M - d[a:a + chunk][None, :]); w = np.sqrt((dev ** 2).mean(0)) + 1e-12
        t = rn * d[a:a + chunk] / w; tk[a:a + chunk] = t
        mu_c = np.where(t <= -math.sqrt(2 * math.log(math.log(n))), d[a:a + chunk], 0.0)
        Zb = rn * (M - d[a:a + chunk][None, :] + mu_c[None, :]) / w[None, :]; Tmax = np.maximum(Tmax, Zb.max(1))
    T_ = tk.max(); return (float((Tmax >= T_).mean()) if T_ > 0 else 1.0), float(T_), int(np.argmax(tk))


def dsr_family(X, idx, best, N):
    """deflated Sharpe ratio (Bailey & Lopez de Prado 2014): P(the best variant's daily SR beats the expected max of N noise trials)."""
    from statistics import NormalDist
    nd = NormalDist(); srs = X[idx].mean(1) / (X[idx].std(1, ddof=1) + 1e-12); v = srs.std() ** 2 + 1e-18
    sr0 = math.sqrt(v) * ((1 - 0.5772) * nd.inv_cdf(1 - 1 / N) + 0.5772 * nd.inv_cdf(1 - 1 / (N * math.e)))
    x = X[best].astype(np.float64); n = len(x); sr = x.mean() / (x.std(ddof=1) + 1e-12); z = (x - x.mean()) / (x.std(ddof=1) + 1e-12)
    g3, g4 = (z ** 3).mean(), (z ** 4).mean(); den = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr * sr, 1e-9))
    return float(nd.cdf((sr - sr0) * math.sqrt(n - 1) / den)), float(sr), float(sr0)


# ---------------------------------------------------------------- placebo (random entries, same structure / exit / sym-days / count)
_POOL = {}
def pool(struct, xn, n=12, seed=3):
    key = (struct, xn)
    if key in _POOL: return _POOL[key]
    fp = f"{SW}/pool_{struct}_{xn}_{_SRC}.pkl"
    if os.path.exists(fp): _POOL[key] = pickle.load(open(fp, "rb")); return _POOL[key]
    rg = np.random.default_rng(seed); out = {}
    for k in KEYS:
        v = []
        for i, sd in zip(rg.integers(I_LO, I_HI + 1, n), rg.integers(0, 2, n)):
            sd = None if struct in ND_LEGS else ("CE" if sd == 0 else "PE"); legs = ND_LEGS[struct] if sd is None else legs_dir(sd, struct)
            r = S.struct(k, int(i), legs, mode="cons", **_exit_kw(xn if xn != "sig" else "t2.5_s1", int(i), sd, {}))
            if r: v.append(r["pnl"])
        out[KI[k]] = np.array(v if v else [0.0])
    pickle.dump(out, open(fp, "wb")); _POOL[key] = out; return out


def placebo(T, tk, rows, runs=2000, seed=9):
    rg = np.random.default_rng(seed); out = {}
    for b in rows:
        r = T.loc[b]; pl = pool(r.struct, r.exit); ks = tk[b]
        rnd = np.zeros(runs)
        for kk in ks: rnd += rg.choice(pl[kk], runs)
        out[b] = dict(p_vs_rand=float((rnd >= r.total).mean()), rand_avg=float(rnd.mean() / max(len(ks), 1)))
    return out


# ---------------------------------------------------------------- driver
def study_count():
    cs = cells(); G = gate_matrix(); print(f"base cells {len(cs)}, gates {len(GATES)}, max variants {len(cs) * len(GATES)}")
    print(pd.Series([c[0] for c in cs]).value_counts().to_string())


def study_run():
    cs = cells(); R = run_cells(cs); T, X, tk = variants(R); print(f"variants with >= 1 trade: {len(T)}")
    pickle.dump((T, X, tk), open(f"{SW}/variants{'_r2' if ROUND2 else ''}.pkl", "wb"))


def study_select():
    T, X, tk = pickle.load(open(f"{SW}/variants{'_r2' if ROUND2 else ''}.pkl", "rb")); t0 = time.time()
    WF = walk_forward(T, X); print(f"walk-forward {time.time() - t0:.0f}s", flush=True)
    fam_rows = []; T["spa_fam_p"] = np.nan
    for fam, idx in T.groupby("family").indices.items():
        idx = np.asarray(idx); p, Ts, bi = spa(X[idx]); best = idx[bi]; d, sr, sr0 = dsr_family(X, idx, best, len(idx))
        T.loc[idx, "spa_fam_p"] = p; w = WF[fam]; r = T.loc[best]
        fam_rows.append(dict(family=fam, variants=len(idx), best_id=r.id, best_n=int(r.n), best_win=round(r.win, 1), best_total=round(r.total),
                             best_avg=round(r.avg), best_payoff=round(r.payoff, 2) if r.payoff == r.payoff else np.nan, best_maxdd=round(r.maxdd),
                             best_forced=round(r.forced, 1), spa_p=p, spa_T=round(Ts, 2), dsr=round(d, 3), sr=round(sr, 3), sr0=round(sr0, 3),
                             wf_oos=round(w["oos"]), wf_oos_p=w["oos_p"], wf_mpos=w["oos_mpos"], wf_trades=w["oos_trades"], best=best))
        print(fam_rows[-1], flush=True)
    F = pd.DataFrame(fam_rows); gp, gT, gb = spa(X); print(f"GLOBAL SPA over {len(T)} variants: p {gp:.3f} T {gT:.2f} best {T.id[gb]}", flush=True)
    F["spa_global_p"] = gp; T["spa_global_p"] = gp
    # placebo: each family's best + the top 20 and bottom 10 by in-sample t
    T["t"] = tstat(X, np.arange(ND)); top = list(T.sort_values("t", ascending=False).index[:20]); bot = list(T.sort_values("t").index[:10])
    pb = placebo(T, tk, sorted(set(list(F.best) + top + bot))); T["p_vs_rand"] = np.nan; T["rand_avg"] = np.nan
    for b, v in pb.items(): T.loc[b, "p_vs_rand"] = v["p_vs_rand"]; T.loc[b, "rand_avg"] = v["rand_avg"]
    F["p_vs_rand"] = [pb[b]["p_vs_rand"] for b in F.best]; F["rand_avg"] = [round(pb[b]["rand_avg"]) for b in F.best]
    F["verdict"] = [verdict(r) for r in F.itertuples()]
    F.to_csv(f"{SW}/families{'_r2' if ROUND2 else ''}.csv", index=False); T.to_csv(f"{SW}/variants{'_r2' if ROUND2 else ''}.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    print(F.drop(columns=["best"]).to_string(index=False))
    cols = ["id", "n", "win", "total", "avg", "payoff", "maxdd", "forced", "wf_oos", "spa_fam_p", "p_vs_rand", "t"]
    print("TOP 20 (in-sample t; selected = inflated):"); print(T.loc[top, cols].round(2).to_string(index=False))
    print("BOTTOM 10:"); print(T.loc[bot, cols].round(2).to_string(index=False))


def verdict(r):
    if (r.spa_p < 0.05 and r.spa_global_p < 0.10 and r.wf_oos > 0 and r.wf_oos_p < 0.10 and r.p_vs_rand < 0.05 and r.best_forced <= 5
            and r.wf_mpos >= 5): return "DESK"
    if r.wf_oos > 0 and r.spa_p < 0.20 and r.p_vs_rand < 0.20 and r.best_forced <= 5: return "LOG-ONLY"
    return "PARKED"


# ---------------------------------------------------------------- known answers: sample cells == the existing engines, trade for trade
def study_selftest():
    ctx(); ok = 0
    def same(a, b, name, tol=1e-6):
        nonlocal ok
        assert len(a) == len(b), f"{name}: {len(a)} vs {len(b)} trades"
        for x, y in zip(a, b): assert x[0] == y[0] and x[1] == y[1] and abs(x[2] - y[2]) < tol, f"{name}: {x} vs {y}"
        ok += 1; print(f"  {name}: {len(a)} trades identical")
    # 1. B1 exact == book_lab.run_dir(sig_b1) on all days (same busy rule, same caps)
    D = B.prep(); T = []
    for k in KEYS:
        if k not in D.index: continue
        d = D.loc[k]; busy = -1
        for i, sd, ex in B.sig_b1(k, d):
            if i <= busy: continue
            r = S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **ex)
            if r: T.append((KI[k], i, r["pnl"])); busy = i + r["held"] - 1
    r = price_cell(("CRABEL", "crabel_nr4_k1_B1exact", "ATM", "sig")); same([(x["k"], x["i"], x["pnl"]) for x in r], T, "B1 == book_lab B1")
    # 2. S1 == sell_lab.run(SSTRAD, 31, sstop=2)
    D1 = S.run(KEYS, S.SSTRAD, 31, dict(sstop=2)); T = [(KI[(a, b)], 31, p) for a, b, p in zip(D1.sym, D1.day, D1.pnl)]
    r = price_cell(("ND_SHORT_STRAD", "t0946", "SHORT_STRAD", "spot2")); same([(x["k"], x["i"], x["pnl"]) for x in r], T, "S1 == sell_lab S1")
    # 3. E5a ORB (W30, cut 165) with t1.5_s1 == sell_lab.e5 trades
    T = []
    for k in KEYS:
        for i, sd in S.orb_signals(k, False):
            x = S.struct(k, i, [(sd, 0, 1)], dirn=1 if sd == "CE" else -1, mode="cons", **S.E5X["t1.5_s1"])
            if x: T.append((KI[k], i, x["pnl"]))
    r = price_cell(("ORB", "orb_W30_c0_cut165", "ATM", "t1.5_s1")); same([(x["k"], x["i"], x["pnl"]) for x in r], T, "E5a == sell_lab e5")
    # 4. E21 PDB == scen_lab sigsA('PDB') with X(i) (2-step target, 1-step stop, 60 min)
    T = []
    for k in KEYS:
        a = ctx()[k]["a"]
        for i, sd in Z.pdb(ctx()[k]["f"], a.PDH, a.PDL):
            x = S.struct(k, i, [(sd, 0, 1)], mode="cons", **Z.X(i, SGN(sd)))
            if x: T.append((KI[k], i, x["pnl"]))
    r = price_cell(("PDB", "pdhl_by0_rej0", "ATM", "t2_s1_h60")); same([(x["k"], x["i"], x["pnl"]) for x in r], T, "PDB == scen_lab PDB")
    # 5. gates: SYM=NIFTY + SYM=SENSEX == ALL; DTE gates partition the days
    G = gate_matrix(); gi = {g[0]: n for n, g in enumerate(GATES)}
    assert (G[:, gi["SYM=NIFTY"]] | G[:, gi["SYM=SENSEX"]]).all() and not (G[:, gi["SYM=NIFTY"]] & G[:, gi["SYM=SENSEX"]]).any()
    assert (G[:, gi["DTE=0"]].astype(int) + G[:, gi["DTE=1"]] + G[:, gi["DTE=2+"]] == 1).all(); ok += 1
    # 6. SPA: pure noise -> p is not small; a strong signal -> p small
    rg = np.random.default_rng(1); Xn = rg.normal(0, 1, (300, 200)).astype(np.float32); p0 = spa(Xn, B_=300)[0]
    Xs = Xn.copy(); Xs[0] += 0.5; p1 = spa(Xs, B_=300)[0]; assert p0 > 0.05 and p1 < 0.05, (p0, p1); ok += 1
    print(f"sweep_lab selftest OK ({ok} checks; SPA noise p {p0:.2f}, signal p {p1:.3f})")




# ---------------------------------------------------------------- forward tape (run ONCE on the frozen top 5; shadow fills)
def _tape_ctx(sym, day, s_raw, F):
    """a ctx entry for a tape day: spot path, yesterday's bar features (fin1_shadow.prior_days) and scen labels (orr unknown -> ORW None)."""
    h = F.prior_days(sym, day); f = pd.Series(s_raw).ffill().bfill().values
    D = pd.DataFrame([dict(O=x[0], H=x[4], L=x[5], C=x[3], orr=np.nan) for x in h] + [dict(O=f[0], H=np.nan, L=np.nan, C=np.nan, orr=np.ptp(f[:31]))],
                     index=[f"h{n}" for n in range(len(h))] + [day])
    a = Z.dfeat(D).iloc[-1]; r = [x[4] - x[5] for x in h]; st = STEP[sym]
    d = None
    if len(h) >= 11 and all(x == x for x in h[-1]):
        d = pd.Series(dict(c1=h[-1][3], R1=r[-1], nr4=r[-1] <= min(r[-4:]), nr7=r[-1] <= min(r[-7:]),
                           stretch=sum(min(x[1] - x[0], x[0] - x[2]) for x in h[-10:]) / 10))
    return dict(s=s_raw, f=f, st=st, d=d, a=a, orv=np.nan, b5=None, b15=None, dte=None)


def _mid(q, sym, K, side, m):
    """mid of the last quote at or before minute m (HH:MM) on the tape; None if none."""
    xs = [x for x in q.get((sym, K, side), []) if x[0] <= f"{m}:59"]; return (xs[-1][1] + xs[-1][2]) / 2 if xs else None


def tape_trade(sym, day, s, q, i, legs, kw, F):
    """one variant trade on the tape with shadow fills: legs at the first quote >= minute i+1 (ask long / bid short), exits by the
    struct rules on the tape spot and quote mids, flat at the 15:15 quote. Returns dict or a reason string."""
    hm = lambda b: f"{(M0 + b) // 60:02d}:{(M0 + b) % 60:02d}"; e = i + 1; K0 = round(s[i] / STEP[sym]) * STEP[sym]
    L_ = [(sd, K0 + off * STEP[sym], sg) for sd, off, sg in legs]; ent = []
    for sd, K, sg in L_:
        x = F._first(sorted(q.get((sym, K, sd), [])), hm(e) + ":00")
        if x is None or x[0] >= hm(e + 1) + ":00": return f"no quote {sd} {K} at {hm(e)}"
        ent.append(x[2] if sg > 0 else x[1])
    credit = sum(-sg * x for (sd, K, sg), x in zip(L_, ent)); s0 = s[e]; flat = kw.get("flat", FLAT); jx, why = flat - M0, "time"
    dirn = kw.get("dirn", 0); best = None
    for j in range(e, flat - M0):
        val = 0.0
        for sd, K, sg in L_:
            v = _mid(q, sym, K, sd, hm(j))
            if v is None: return f"no mark {sd} {K} at {hm(j)}"
            val += -sg * v
        if kw.get("stop") is not None and val - credit >= kw["stop"] * credit: why, jx = "stop", j + 1; break
        if kw.get("tgt") is not None and val <= (1 - kw["tgt"]) * credit: why, jx = "tgt", j + 1; break
        if kw.get("sstop") is not None and abs(s[j] - s0) >= kw["sstop"] * STEP[sym]: why, jx = "spot", j + 1; break
        mv = dirn * (s[j] - s0) / STEP[sym]
        if dirn and kw.get("s_tgt") is not None and mv >= kw["s_tgt"]: why, jx = "s_tgt", j + 1; break
        if dirn and kw.get("s_stp") is not None and mv <= -kw["s_stp"]: why, jx = "s_stp", j + 1; break
        if kw.get("trail") is not None:
            m_ = abs(val); best = m_ if best is None else (min(best, m_) if credit > 0 else max(best, m_))
            if (m_ >= best * (1 + kw["trail"])) if credit > 0 else (m_ <= best * (1 - kw["trail"])): why, jx = "trail", j + 1; break
    out = 0.0; costs = 0.0; qn = LOT[sym] * L.LOTS; LOT_ = LOT
    for (sd, K, sg), x in zip(L_, ent):
        xs = sorted(q.get((sym, K, sd), [])); xq, forced = F._exit_q(xs, "time" if why == "time" else "spot", hm(jx) + ":00")
        if xq is None: return f"no exit quote {sd} {K}"
        fill = xq[2] if sg < 0 else xq[1]; out += -sg * fill
        costs += F.cost(fill, x, sym) if sg < 0 else F.cost(x, fill, sym)
    return dict(pnl=(credit - out) * qn - costs, why=why, i=i, held=jx - e, K=K0)


LOT = L.LOT


def study_forward():
    """frozen top-5 ids in OUT/sweep/frozen_top5.txt (written by `select`, before this runs); tape days >= 2026-10-26, once."""
    import fin1_shadow as F
    from pathlib import Path
    F.TAPE = Path(os.environ.get("FIN1_TAPE", f"{L.OUT}/../../tape/v2")); F.DATA = Path(os.environ.get("FIN1_DATA", f"{L.OUT}/../.."))
    ids = [x.strip() for x in open(f"{SW}/frozen_top5.txt") if x.strip()]; sm = _sigmap(); G = {g[0]: g for g in GATES}
    days = sorted(p.name for p in F.TAPE.iterdir() if p.name >= "2026-10-26" and (p / "quote_snapshots.jsonl").is_file())
    print("forward tape days:", days); rows = []
    for day in days:
        spot, q = F.load(day)
        for sym in ("NIFTY", "SENSEX"):
            sp = spot.get(sym, {}); s = np.full(NB, np.nan)
            for m, v in sp.items():
                b = int(m[:2]) * 60 + int(m[3:]) - M0
                if 0 <= b < NB: s[b] = v
            if np.isfinite(s).sum() < 300 or not np.isfinite(s[:31]).all():
                print(f"{day} {sym}: NO_DATA ({int(np.isfinite(s).sum())} spot minutes)"); continue
            c = _tape_ctx(sym, day, pd.Series(s).ffill().values, F); _CTX[(sym, day)] = c
            fr = next((r for r in F.day_rows(day, spot, q) if r["sym"] == sym), {}); c["orv"] = fr.get("ratio", np.nan) if fr.get("status") == "OK" else np.nan
            for vid in ids:
                fam, nm, struct, xn, gate = vid.split("|"); gn, col, gv = G[gate]
                if col == "SYM" and gv != sym: continue
                lab = dict(c["a"].to_dict(), SYM=sym, OPEN=("calm" if c["orv"] <= 1.0042 else "active") if np.isfinite(c["orv"]) else None, DTE=None)
                if col is not None and lab.get(col) != gv:
                    rows.append(dict(day=day, sym=sym, id=vid, status="GATE_OFF" if lab.get(col) is not None else "GATE_UNKNOWN")); continue
                fn, lo, hi = sm[nm]
                try: sig = fn((sym, day))
                except Exception as e_: rows.append(dict(day=day, sym=sym, id=vid, status="SIG_ERR " + type(e_).__name__)); continue
                sig = [x for x in sig if lo <= x[0] <= hi]
                if not sig: rows.append(dict(day=day, sym=sym, id=vid, status="NO_SIGNAL")); continue
                i, sd, ov = sig[0]; legs = ND_LEGS[struct] if sd is None else legs_dir(sd, struct)
                r = tape_trade(sym, day, c["f"], q, i, legs, _exit_kw(xn, i, sd, ov), F)
                rows.append(dict(day=day, sym=sym, id=vid, status="OK" if isinstance(r, dict) else r, **(r if isinstance(r, dict) else {})))
            del _CTX[(sym, day)]
    R = pd.DataFrame(rows); pd.set_option("display.width", 250); print(R.to_string(index=False)); R.to_csv(f"{SW}/forward.csv", index=False)
    ok = R[R.status == "OK"] if "pnl" in R else R.iloc[0:0]
    print(f"forward: {len(ok)} trades, net Rs {ok.pnl.sum() if len(ok) else 0:,.0f} on {len(days)} tape days (cannot decide anything at this size)")


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
