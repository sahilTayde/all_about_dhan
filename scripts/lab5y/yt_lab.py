"""E51: six frozen rules harvested from popular NIFTY / SENSEX / BANKNIFTY YouTube videos (paper research; no orders).
Frozen text (rules, defaults, verdict): side-session note E51_youtube_freeze.md, written before any P&L. One cell per rule:
  OIX expiry 14:00 change-in-OI imbalance -> buy the ATM option      GB  expiry 14:00 long ATM straddle when both legs are cheap
  SC  5m "super candle" call, strike by premium = 1% of spot          PIV 15m ADX + 5m Supertrend + Fibonacci pivot break, ITM1
  F44 buy the 44% recovery of a 0.5% intraday fall                    OVW sell the ATM option below its own VWAP with rising OI
Run (from scripts/lab5y):  LAB_FULL=1 HO=2025-10-27 [COSTS=dated] ~/paper_extra_venv/bin/python yt_lab.py <OUT=data/cache/lab5y_w10> selftest|lookahead|gross|e51|final

Signals use data up to the decision minute i only (study_lookahead scrambles everything after it). Pricing is sell_lab.struct, unchanged:
entry at the open of minute i+1, exit at the open of minute x+1 where x is the exit-decision minute found here (x = XL = 15:14 -> flat at the
15:15 open), p75 half-spreads, charges x1.5, 10 lots, cons bounds, no fill on an untraded bar.
ponytail: spot is 1m closes only (no index OHLC), so a 5m bar's high/low are the extremes of its five closes; ceiling = wick-based rules."""
import sys, zlib, numpy as np, pandas as pd
from multiprocessing import get_context
import opt1y_lab as L
import sell_lab as S
import playbook_lab as B   # _dayboot_p (day bootstrap), _scr / _undo (scramble after a cut)

P, STEP, M0, NB, HO = L.P, L.STEP, L.M0, L.NB, L.HO
XL = L.FLAT - M0 - 1       # 359: the last exit-decision minute (fill at the 15:15 open)
CELLS = ["OIX", "GB", "SC", "PIV", "F44", "OVW"]; ALPHA = 0.05 / len(CELLS); NPL = 20
WIN = dict(OIX=(225, 315), GB=(225, 315), SC=(4, 344), PIV=(4, 284), F44=(5, 344), OVW=(14, 314))   # placebo entry minutes
LEAK = None                # lookahead positive controls: "centre" (Bollinger sees the future), "dayhigh" (F44 uses the whole-day high)
FE, DIX = {}, {}           # sym -> feats, key -> day index (set by study_e51 before the pool forks)
def keys(sym): return [k for k in L.ALLK if k[0] == sym]


# ---------------------------------------------------------------- indicators (continuous over the index's days; value at a bar uses bars <= it)
def _rma(x, n): return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().values


def supertrend(h, l, c, n=10, m=3.0):
    """Supertrend direction per bar (+1 up, -1 down): bands = hl2 +- m x RMA(TR, n), ratcheted; flips on a close through the active band."""
    pc = np.r_[c[0], c[:-1]]; atr = _rma(np.maximum.reduce([h - l, abs(h - pc), abs(l - pc)]), n)
    ub, lb = (h + l) / 2 + m * atr, (h + l) / 2 - m * atr; d = np.ones(len(c), int); fu, fl = ub[0], lb[0]
    for t in range(1, len(c)):
        fu = ub[t] if ub[t] < fu or c[t - 1] > fu else fu
        fl = lb[t] if lb[t] > fl or c[t - 1] < fl else fl
        d[t] = (1 if c[t] > fu else -1) if d[t - 1] < 0 else (-1 if c[t] < fl else 1)
    return d


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up, dn = _rma(np.maximum(d, 0), n), _rma(np.maximum(-d, 0), n); return 100 * up / (up + dn + 1e-12)


def adx(h, l, c, n=14):
    """Wilder ADX(n, n) (the playbook_lab._bars5 formula, on any bar size)."""
    pc, ph, pl = np.r_[c[0], c[:-1]], np.r_[h[0], h[:-1]], np.r_[l[0], l[:-1]]; um, dm = h - ph, pl - l
    tr = _rma(np.maximum.reduce([h - l, abs(h - pc), abs(l - pc)]), n) + 1e-9
    pdi, mdi = 100 * _rma(np.where((um > dm) & (um > 0), um, 0.0), n) / tr, 100 * _rma(np.where((dm > um) & (dm > 0), dm, 0.0), n) / tr
    return _rma(100 * abs(pdi - mdi) / (pdi + mdi + 1e-9), n)


def bars(ks, tf):
    """o, h, l, c of tf-minute bars over the days ks, flattened (NB // tf bars per day), from the 1m spot closes."""
    X = np.array([P[k]["spot"] for k in ks]).reshape(len(ks), NB // tf, tf); return X[:, :, 0].ravel(), X.max(2).ravel(), X.min(2).ravel(), X[:, :, -1].ravel()


def feats(ks):
    """per (day index, 5m bar): close c, previous 5m close pc, Supertrend(10,3) direction, RSI(14), upper Bollinger(20,2), ADX(14) of the last
    COMPLETED 15m bar; per day: the previous day's high / low / close (pH, pL, pC)."""
    o, h, l, c = bars(ks, 5); n = len(ks); r = pd.Series(c).rolling(20, center=LEAK == "centre"); sh = lambda v: v.reshape(n, 75)
    a15 = adx(*bars(ks, 15)[1:]); g = np.arange(n * 75); q = (g // 75) * 25 + (g % 75 + 1) // 3 - 1   # 5m bar b ends at minute 5b+4; 15m bars ending by then
    X = np.array([P[k]["spot"] for k in ks]); pH, pL, pC = (np.r_[np.nan, v[:-1]] for v in (X.max(1), X.min(1), X[:, -1]))
    return dict(c=sh(c), pc=sh(np.r_[np.nan, c[:-1]]), st=sh(supertrend(h, l, c)), rsi=sh(rsi(c)), bbu=sh((r.mean() + 2 * r.std(ddof=0)).values),
                adx=sh(np.where(q >= 0, a15[q], np.nan)), pH=pH, pL=pL, pC=pC)


# ---------------------------------------------------------------- shared helpers
def _can(k, i, legs):
    """the entry order fills: every leg has a traded quote at the open of minute i+1 (what struct requires)."""
    p = P[k]; A = [p["C"].get((sd, p["atm"][i] + off * STEP[k[0]])) for sd, off, sg in legs]
    return all(a is not None and np.isfinite(a[i + 1, 0]) and not L.stale(a, i + 1) for a in A)


def _oi(a, t):
    """last OI print at or before minute t."""
    v = a[:t + 1, 4]; v = v[np.isfinite(v)]; return v[-1] if len(v) else np.nan


def x_levels(sp, i, dirn, stop, tgt, tgt5=False):
    """exit-decision minute: the first minute j > i whose close is at / through the stop, or at / through the target (5m closes only if tgt5)."""
    for j in range(i + 1, XL):
        if dirn * (sp[j] - stop) <= 0 or ((not tgt5 or j % 5 == 4) and dirn * (sp[j] - tgt) >= 0): return j
    return XL


# ---------------------------------------------------------------- OIX
def doi(p, pp, sd, K, t):
    """change in OI of (side, strike) at minute t versus the same contract's last print of the previous day."""
    a, b = p["C"].get((sd, K)), pp["C"].get((sd, K)); return _oi(a, t) - _oi(b, NB - 1) if a is not None and b is not None else np.nan


def oix_pick(p, pp, i, sym, ratio=2.0, gate="slope"):
    """side to BUY at the ATM strike, or None. Strike rule: calls written `ratio` x more than puts -> PE; mirror -> CE.
    gate: 'slope' = aggregate change-in-OI PCR over ATM+-5 now vs 120 minutes ago (falling -> PE only), 'level' = vs 1, 'none'."""
    K = p["atm"][i]; dC, dP = doi(p, pp, "CE", K, i), doi(p, pp, "PE", K, i)
    side = "PE" if dC > 0 and dP <= dC / ratio else "CE" if dP > 0 and dC <= dP / ratio else None
    if side is None or gate == "none": return side
    def A(t):
        D = [(doi(p, pp, "CE", K + o * STEP[sym], t), doi(p, pp, "PE", K + o * STEP[sym], t)) for o in range(-5, 6)]
        D = [x for x in D if np.isfinite(x[0] + x[1])]; sc = sum(x[0] for x in D); return sum(x[1] for x in D) / sc if D and sc > 0 else np.nan
    a1, a0 = A(i), (A(i - 120) if gate == "slope" else 1.0)
    return side if (a1 < a0 if side == "PE" else a1 > a0) else None


def sig_oix(ks, D=None, i=285, ratio=2.0, gate="slope"):
    out = []
    for d in (D or range(1, len(ks))):
        k, p, pp = ks[d], P[ks[d]], P[ks[d - 1]]
        if d and p["d0"] and str(pp["exp"]) == str(p["exp"]):
            sd = oix_pick(p, pp, i, k[0], ratio, gate)
            if sd: out.append(dict(k=k, i=i, legs=[(sd, 0, 1)], x=XL))
    return out


# ---------------------------------------------------------------- GB
def gb_pick(p, i, sym, cap=0.00065, oig=True):
    """strike offset (steps from ATM) of the long straddle, or None: the strike among ATM-1..+1 with the closest CE / PE closes; both legs
    <= cap x spot; CE OI at K+1 and PE OI at K-1 each in the top 3 of their side."""
    st = STEP[sym]; C = p["C"]; atm = p["atm"][i]
    c = [(abs(C[("CE", K)][i, 3] - C[("PE", K)][i, 3]), abs(K - atm), K) for K in (atm - st, atm, atm + st) if ("CE", K) in C and ("PE", K) in C]
    c = [x for x in c if np.isfinite(x[0])]
    if not c: return None
    K = min(c)[2]   # a tie goes to the ATM strike
    if cap and not max(C[("CE", K)][i, 3], C[("PE", K)][i, 3]) <= cap * p["spot"][i]: return None
    for sd, Kn in ((("CE", K + st), ("PE", K - st)) if oig else ()):
        top = sorted((v for v in (_oi(a, i) for (s_, _), a in C.items() if s_ == sd) if np.isfinite(v)), reverse=True); a = C.get((sd, Kn))
        if a is None or len(top) < 3 or not _oi(a, i) >= top[2]: return None
    return int(round((K - atm) / st))


def sig_gb(ks, D=None, i=285, cap=0.00065, oig=True):
    out = []
    for d in (D or range(len(ks))):
        k = ks[d]; off = gb_pick(P[k], i, k[0], cap, oig) if P[k]["d0"] else None
        if off is not None: out.append(dict(k=k, i=i, legs=[("CE", off, 1), ("PE", off, 1)], x=XL))
    return out


# ---------------------------------------------------------------- SC
def sc_strike(p, i, sym):
    """offset of the CE whose close at i is nearest 1% of spot (traded bar at i); None if the nearest is > 0.3% of spot from the target."""
    s = p["spot"][i]; c = [(abs(a[i, 3] - 0.01 * s), K) for (sd, K), a in p["C"].items() if sd == "CE" and a[i, 6] > 0 and np.isfinite(a[i, 3])]
    return int(round((min(c)[1] - p["atm"][i]) / STEP[sym])) if c and min(c)[0] <= 0.003 * s and np.isfinite(p["atm"][i]) else None   # ATM is NaN before its first print


def x_st(F, d, i):
    """exit-decision minute: the first 5m close after minute i with Supertrend down."""
    for b in range((i + 1) // 5, 72):
        if F["st"][d, b] < 0: return min(5 * b + 4, XL)
    return XL


def sig_sc(ks, F, D=None):
    out = []
    for d in (D or range(1, len(ks))):
        if not d: continue
        k = ks[d]; R1 = 2 * (F["pH"][d] + F["pL"][d] + F["pC"][d]) / 3 - F["pL"][d]; x = -1
        for b in range(69):
            i = 5 * b + 4; c = F["c"][d, b]
            if i > x and F["st"][d, b] > 0 and F["rsi"][d, b] > 70 and c > R1 and c > F["bbu"][d, b]:
                off = sc_strike(P[k], i, k[0])
                if off is not None and _can(k, i, [("CE", off, 1)]): x = x_st(F, d, i); out.append(dict(k=k, i=i, legs=[("CE", off, 1)], x=x))
    return out


# ---------------------------------------------------------------- PIV
def piv_pick(pc, c, dirn, lv):
    """lv = [S3, S2, S1, P, R1, R2, R3]. A 5m close c beyond a level the previous close pc was not beyond, in direction dirn -> (stop, target)
    or None: the furthest crossed level is the broken one (never R3 / S3); stop = broken -+ 0.05% of spot (skip if > 0.40% away);
    target = the next level, or the one after when half the way is already covered (skip if none)."""
    V = lv if dirn > 0 else [-v for v in lv[::-1]]; pc, c, s = dirn * pc, dirn * c, abs(c)   # shorts mirrored into longs
    cr = [t for t, v in enumerate(V) if pc <= v < c]
    if not cr or cr[-1] == 6: return None
    t = cr[-1]; br = V[t]; t += 1 + (c - br >= 0.5 * (V[t + 1] - br)); stop = br - 0.0005 * s
    return None if t > 6 or c - stop > 0.004 * s else (dirn * stop, dirn * V[t])


def sig_piv(ks, F, D=None):
    out = []
    for d in (D or range(1, len(ks))):
        if not d: continue
        k = ks[d]; pp = (F["pH"][d] + F["pL"][d] + F["pC"][d]) / 3; r = F["pH"][d] - F["pL"][d]; sp = P[k]["spot"]; x = -1; n = 0
        lv = [pp + m * r for m in (-1, -0.618, -0.382, 0, 0.382, 0.618, 1)]
        for b in range(57):
            i = 5 * b + 4; dirn = int(F["st"][d, b]); c = F["c"][d, b]; legs = [("CE" if dirn > 0 else "PE", -dirn, 1)]
            pk = piv_pick(F["pc"][d, b], c, dirn, lv) if i > x and n < 2 and F["adx"][d, b] > 20 else None
            if pk and _can(k, i, legs):
                x = x_levels(sp, i, dirn, pk[0], pk[1], True); n += 1
                out.append(dict(k=k, i=i, legs=legs, x=x, dirn=dirn, ds=dirn * (c - pk[0]), dt=dirn * (pk[1] - c)))
    return out


# ---------------------------------------------------------------- F44
def sig_f44(ks, D=None):
    out = []
    for d in (D or range(len(ks))):
        k = ks[d]; sp = P[k]["spot"]; H = Lo = sp[0]; x = -1; n = 0
        if LEAK == "dayhigh": H = sp.max()
        for j in range(1, 345):
            s = sp[j]
            if s > H: H = Lo = s
            elif s < Lo: Lo = s
            R = H - Lo
            if j >= 5 and j > x and n < 3 and R >= 0.005 * H and s >= Lo + 0.44 * R and _can(k, j, [("CE", 0, 1)]):
                st, tg = Lo + 0.22 * R, Lo + 0.77 * R; x = x_levels(sp, j, 1, st, tg); n += 1
                out.append(dict(k=k, i=j, legs=[("CE", 0, 1)], x=x, dirn=1, ds=s - st, dt=tg - s)); H = Lo = s
    return out


# ---------------------------------------------------------------- OVW
def _vwap(a):
    """session VWAP of one contract per minute: cumulative (h + l + c) / 3 x volume over cumulative volume (0 before the first trade)."""
    v = np.nan_to_num(a[:, 6]); return np.cumsum(np.nan_to_num(a[:, 1:4].mean(1)) * v) / np.maximum(np.cumsum(v), 1e-9)


def x_ovw(k, i, a, vw):
    """exit-decision minute of the short: a 1m close >= entry open + 0.068% of spot, or a 5m close above the option's VWAP."""
    lim = a[i + 1, 0] + 0.00068 * P[k]["spot"][i]
    for j in range(i + 1, XL):
        if a[j, 3] >= lim or (j % 5 == 4 and a[j, 3] > vw[j]): return j
    return XL


def sig_ovw(ks, D=None):
    out = []
    for d in (D or range(len(ks))):
        k = ks[d]; p = P[k]; x = -1; stops = 0; vw = {}
        if k[1] in L.RBI: continue
        for b in range(6, 63):   # decision minutes 34..314 (the 30-minute OI look-back needs i >= 30)
            i = 5 * b + 4; K = p["atm"][i]; sg = []
            if i <= x or stops >= 3: continue
            for sd, od in (("CE", "PE"), ("PE", "CE")):
                a, o = p["C"].get((sd, K)), p["C"].get((od, K))
                if a is None or o is None: continue
                w = vw.setdefault((sd, K), _vwap(a))
                if a[i, 3] < w[i] and a[i - 5, 3] < w[i - 5] and _oi(a, i) > _oi(a, i - 30) and _oi(o, i) < _oi(o, i - 30): sg.append((sd, a, w))
            if len(sg) == 1 and _can(k, i, [(sg[0][0], 0, -1)]):
                sd, a, w = sg[0]; x = x_ovw(k, i, a, w); stops += x < XL; out.append(dict(k=k, i=i, legs=[(sd, 0, -1)], x=x))
    return out


def all_signals(ks, F, D=None):
    return dict(OIX=sig_oix(ks, D), GB=sig_gb(ks, D), SC=sig_sc(ks, F, D), PIV=sig_piv(ks, F, D), F44=sig_f44(ks, D), OVW=sig_ovw(ks, D))


# ---------------------------------------------------------------- pricing, placebo, stats
def gross(k, i, legs, x):
    """Rs at 10 lots of today's lot, open of minute i+1 to open of minute x+1, no spread, no charges (NaN if a quote is missing)."""
    A = [(sg, P[k]["C"].get((sd, P[k]["atm"][i] + off * STEP[k[0]]))) for sd, off, sg in legs]
    return sum(sg * (a[x + 1, 0] - a[i + 1, 0]) if a is not None else np.nan for sg, a in A) * L.LOT[k[0]] * L.LOTS


def plc(cell, t, i2):
    """the placebo twin of trade t at minute i2 (same sym-day, side and strike rule, same exit rule): (legs, exit minute) or None."""
    k = t["k"]; p = P[k]; sym = k[0]
    if cell == "OIX": return t["legs"], XL
    if cell == "GB": off = gb_pick(p, i2, sym, None, False); return None if off is None else ([("CE", off, 1), ("PE", off, 1)], XL)
    if cell == "SC": off = sc_strike(p, i2, sym); return None if off is None else ([("CE", off, 1)], x_st(FE[sym], DIX[k], i2))
    if cell in ("PIV", "F44"): s = p["spot"][i2]; d = t["dirn"]; return t["legs"], x_levels(p["spot"], i2, d, s - d * t["ds"], s + d * t["dt"], cell == "PIV")
    a = p["C"].get((t["legs"][0][0], p["atm"][i2])); return None if a is None or not np.isfinite(a[i2 + 1, 0]) else (t["legs"], x_ovw(k, i2, a, _vwap(a)))


def _work(a):
    cell, t = a; k, i = t["k"], t["i"]; r = S.struct(k, i, t["legs"], flat=M0 + t["x"] + 1)
    if r is None: return None
    rg = np.random.default_rng(zlib.crc32(repr((cell, k, i)).encode())); pl = []
    for i2 in rg.integers(WIN[cell][0], WIN[cell][1] + 1, NPL):
        q = plc(cell, t, int(i2)); r2 = S.struct(k, int(i2), q[0], flat=M0 + q[1] + 1) if q else None; pl.append(r2["pnl"] if r2 else np.nan)
    return dict(cell=cell, sym=k[0], day=k[1], i=i, x=t["x"], side=t["legs"][0][0], off=t["legs"][0][1], pnl=r["pnl"], forced=r["forced"],
                gross=gross(k, i, t["legs"], t["x"]), pl=pl)


def plac_p(T, n=2000, seed=51):
    """share of n re-draws (one random-minute twin per trade) whose total >= the real total, over the trades that have a twin."""
    rg = np.random.default_rng(seed); tot = np.zeros(n); real = 0.0
    for pnl, pl in zip(T.pnl, T.pl):
        v = np.asarray(pl, float); v = v[np.isfinite(v)]
        if len(v): tot += v[rg.integers(len(v), size=n)]; real += pnl
    return float((tot >= real).mean())


def verdict(r, dated=None):
    """the frozen rule (freeze file section 3). dated: the same cell's row under COSTS=dated (signs must agree) or None."""
    if r["learn_n"] < 30 or r["test_n"] < 10: return "UNTESTABLE"
    if r["forced_pct"] > 10: return "INCONCLUSIVE"
    ok = (r["learn_mean"] > 0 and r["learn_p"] < 0.05 and r["test_total"] > 0 and r["test_p"] < ALPHA and int(str(r["test_q_pos"]).split("/")[0]) >= 3
          and r["plac_p_test"] < 0.05 and (dated is None or (dated["learn_mean"] > 0 and dated["test_mean"] > 0)))
    return "PASS" if ok else "FAIL"


def stats(cell, T):
    r = dict(cell=cell, learn_n=int((T.day < HO).sum()) if len(T) else 0, test_n=int((T.day >= HO).sum()) if len(T) else 0)
    if not len(T): return dict(r, forced_pct=0.0, verdict="UNTESTABLE")
    r.update(forced_pct=round(T.forced.mean() * 100, 1), worst=round(T.pnl.min()), best=round(T.pnl.max()), plac_p_all=round(plac_p(T), 3))
    for nm, G in (("learn", T[T.day < HO]), ("test", T[T.day >= HO])):
        if len(G): r.update({f"{nm}_mean": round(G.pnl.mean()), f"{nm}_gross": round(G.gross.mean()), f"{nm}_win": round((G.pnl > 0).mean() * 100, 1),
                             f"{nm}_total": round(G.pnl.sum()), f"{nm}_p": round(B._dayboot_p(G.groupby("day").pnl.sum().values), 4)})
    Te = T[T.day >= HO]
    if len(Te): qs = Te.groupby(pd.to_datetime(Te.day).dt.to_period("Q").astype(str)).pnl.sum(); r.update(test_q_pos=f"{(qs > 0).sum()}/{len(qs)}", plac_p_test=round(plac_p(Te), 3))
    return dict(r, verdict=verdict(r))


def study_e51():
    """the six frozen cells, both indices pooled, LEARN and TEST in one pass (TEST is scored once: run this once per cost mode)."""
    sig = {c: [] for c in CELLS}
    for sym in ("NIFTY", "SENSEX"):
        ks = keys(sym); FE[sym] = feats(ks); DIX.update({k: d for d, k in enumerate(ks)})
        for c, v in all_signals(ks, FE[sym]).items(): sig[c] += v
    rows, TT = [], []
    with get_context("fork").Pool(8) as pool:
        for c in CELLS:
            T = pd.DataFrame([r for r in pool.map(_work, [(c, t) for t in sig[c]], chunksize=16) if r]); rows.append(stats(c, T)); TT.append(T)
            print(c, "signals", len(sig[c]), "priced", len(T), flush=True)
    R = pd.DataFrame(rows); pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40); print(R.to_string(index=False))
    T = pd.concat(TT); T.drop(columns="pl").to_csv(f"{L.OUT}/yt_e51_trades_{L.COSTS}.csv", index=False); R.to_csv(f"{L.OUT}/yt_e51_{L.COSTS}.csv", index=False)
    print("by index and part (n, mean, total):"); print(T.assign(part=np.where(T.day < HO, "LEARN", "TEST")).groupby(["cell", "sym", "part"]).pnl.agg(["size", "mean", "sum"]).round(0).to_string())
    print(f"COSTS={L.COSTS}; alpha = 0.05 / {len(CELLS)} = {ALPHA:.5f}; the final verdict needs both cost modes: yt_lab.py OUT final")


def study_final():
    """join the COSTS=today and COSTS=dated rows; the verdict uses today's row plus the dated sign check."""
    A, Dt = (pd.read_csv(f"{L.OUT}/yt_e51_{c}.csv").set_index("cell") for c in ("today", "dated")); out = []
    for c in CELLS:
        a, d = A.loc[c].to_dict(), Dt.loc[c].to_dict(); f = lambda r, n: r.get(n, np.nan)
        out.append(dict(cell=c, learn_n=a["learn_n"], learn_mean=f(a, "learn_mean"), learn_win=f(a, "learn_win"), learn_p=f(a, "learn_p"), test_n=a["test_n"], test_mean=f(a, "test_mean"),
                        test_p=f(a, "test_p"), test_q_pos=f(a, "test_q_pos"), plac_p_test=f(a, "plac_p_test"), forced_pct=a["forced_pct"], worst=f(a, "worst"),
                        dated_learn_mean=f(d, "learn_mean"), dated_test_mean=f(d, "test_mean"), verdict=a["verdict"] if a["verdict"] != "PASS" else verdict(a, d)))
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40); print(pd.DataFrame(out).to_string(index=False)); print(f"alpha = {ALPHA:.5f}")


def study_gross():
    """E48 lesson: gross-expectancy maps of the two expiry long-option families on LEARN only (freeze file section 4). Can only CLOSE a family."""
    ks = {s: [k for k in keys(s) if k[1] < HO] for s in ("NIFTY", "SENSEX")}; pd.set_option("display.width", 250)
    def pt(fam, name, sigs):
        R = [(gross(t["k"], t["i"], t["legs"], t["x"]), r["pnl"]) for t in sigs for r in [S.struct(t["k"], t["i"], t["legs"], flat=M0 + t["x"] + 1)] if r]
        R = np.array([x for x in R if np.isfinite(x[0])]).reshape(-1, 2); n = len(R); g, h = (R[:, 0].mean(), (R[:, 0] - R[:, 1]).mean()) if n else (np.nan, np.nan)
        return dict(fam=fam, point=name, n=n, gross=round(g) if n else np.nan, hurdle=round(h) if n else np.nan, net=round(g - h) if n else np.nan, win_gross=round((R[:, 0] > 0).mean() * 100, 1) if n else np.nan, open=bool(n >= 30 and g > h))
    rows = [pt("OIX", f"{sd} every expiry 14:00", [dict(k=k, i=285, legs=[(sd, 0, 1)], x=XL) for s in ks for k in ks[s] if P[k]["d0"]]) for sd in ("CE", "PE")]
    rows += [pt("OIX", f"ratio {r} gate {g} {t}", [x for s in ks for x in sig_oix(ks[s], None, i, r, g)]) for r in (1.5, 2.0, 3.0) for g in ("none", "slope", "level") for t, i in (("13:00", 225), ("14:00", 285))]
    rows += [pt("GB", f"cap {c} oi {o} {t}", [x for s in ks for x in sig_gb(ks[s], None, i, c, o)]) for c in (0.00065, 0.001, 0.0015, None) for o in (True, False) for t, i in (("13:00", 225), ("14:00", 285))]
    R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv(f"{L.OUT}/yt_e51_gross_{L.COSTS}.csv", index=False)
    for fam in ("OIX", "GB"):
        G = R[(R.fam == fam) & ~R.point.str.contains("every expiry")]; print(f"family {fam}: {'OPEN' if G.open.any() else 'CLOSED'} ({int(G.open.sum())} of {len(G)} map points with n >= 30 have LEARN gross > hurdle)")


# ---------------------------------------------------------------- look-ahead scan
def _la(sym, samples, rg):
    """for each (day index d, cut minute): scramble day d after the cut and the next two days entirely, rebuild everything, and list what
    changed among: features of bars closed by the cut, entries decided by the cut, exits decided by the cut."""
    ks = keys(sym); F0 = feats(ks); bad = []; seen = dict.fromkeys(CELLS + ["GBx"], 0)
    def sigs(F, d):   # GBx = the GB picker with the loosest map cap (the frozen 0.065% cap fires too rarely to be sampled)
        return {c: [(t["i"], tuple(t["legs"]), t["x"]) for t in v] for c, v in dict(all_signals(ks, F, [d]), GBx=sig_gb(ks, [d], 285, 0.0015)).items()}
    for d, cut in samples:
        s0 = sigs(F0, d); undo = B._scr([(ks[d], cut)] + [(k, -1) for k in ks[d + 1:d + 3]], rg)
        try: F1 = feats(ks); s1 = sigs(F1, d)
        finally: B._undo(undo)
        g = d * 75 + (cut - 4) // 5 + 1   # 5m bars closed by the cut (flattened index, exclusive)
        for nm in ("c", "pc", "st", "rsi", "bbu", "adx"):
            if not np.array_equal(F0[nm].ravel()[:g], F1[nm].ravel()[:g], equal_nan=True): bad.append((sym, ks[d][1], cut, "feat " + nm))
        for c in seen:
            a, b = [t for t in s0[c] if t[0] <= cut], [t for t in s1[c] if t[0] <= cut]; seen[c] += len(a)
            if [t[:2] for t in a] != [t[:2] for t in b]: bad.append((sym, ks[d][1], cut, c + " entry"))
            elif any((x0 != x1) if x0 <= cut else (x1 <= cut) for (_, _, x0), (_, _, x1) in zip(a, b)): bad.append((sym, ks[d][1], cut, c + " exit"))
    return bad, seen


def study_lookahead(n_days=16, seed=51):
    """scramble-after-the-decision scan on sampled days (half of them expiry days cut at 14:00 / 14:30 for OIX and GB), then two planted leaks
    (a centred Bollinger window, a whole-day high in F44) that the same scan must catch."""
    global LEAK
    rg = np.random.default_rng(seed); bad = []; n = 0; S_ = {}; seen = {}
    for sym in ("NIFTY", "SENSEX"):
        ks = keys(sym); ex = [d for d in range(30, len(ks) - 3) if P[ks[d]]["d0"]]
        S_[sym] = [(int(d), int(rg.choice([285, 315]))) for d in rg.choice(ex, n_days // 2, replace=False)] + \
                  [(int(d), int(c)) for d, c in zip(rg.choice(range(30, len(ks) - 3), n_days, replace=False), rg.integers(20, 345, n_days))]
        b, sn = _la(sym, S_[sym], rg); bad += b; n += len(S_[sym]); seen = {c: seen.get(c, 0) + sn[c] for c in sn}
    print(f"lookahead: {n} (day, cut) samples, both indices, 6 cells + 6 feature columns: {len(bad)} changes; real entries checked per cell {seen}", bad[:10]); assert not bad and all(v > 0 for c, v in seen.items() if c != "GB"), (bad, seen)
    for leak, want in (("centre", "feat bbu"), ("dayhigh", "F44 entry")):
        LEAK = leak
        try: got = {b[3] for b in _la("NIFTY", S_["NIFTY"], rg)[0]}
        finally: LEAK = None
        print(f"planted leak '{leak}': caught as {sorted(got)}"); assert want in got, (leak, got)
    print("lookahead OK (no feature, entry or exit decided by the cut changed; both planted leaks caught)")


# ---------------------------------------------------------------- selftest (hand-computed known answers on synthetic days)
def _syn(day, spot, px, oi=lambda sd, off, j: 1000.0, d0=0, exp="2021-08-02"):
    """synthetic NIFTY day (dated 2021-08, before the panel starts): spot array, ATM fixed at 20000, strikes ATM+-10; px(side, off, j) and
    oi(side, off, j) per minute; volume 1."""
    C = {}; assert ("NIFTY", day) not in P, "synthetic days must sit outside the panel (they are deleted afterwards)"
    for sd in ("CE", "PE"):
        for off in range(-10, 11):
            a = np.full((NB, 7), np.nan); a[:, :4] = np.array([px(sd, off, j) for j in range(NB)])[:, None]; a[:, 4] = [oi(sd, off, j) for j in range(NB)]
            a[:, 5], a[:, 6] = 15.0, 1.0; C[(sd, 20000.0 + off * 50)] = a
    P[("NIFTY", day)] = dict(spot=np.asarray(spot, float), atm=np.full(NB, 20000.0), C=C, exp=exp, dte=0 if d0 else 1, d0=d0); return ("NIFTY", day)


def study_selftest():
    ap = lambda a, b: abs(a - b) < 1e-6; flat = np.full(NB, 20000.0); syn = []
    try:
        # indicators. Supertrend(2, 1) on closes 10 11 12 13 9 (h = l = c): TR 0 1 1 1 4, RMA 0 .5 .75 .875 2.4375; lower band ratchets
        # 10 10.5 11.25 12.125 12.125; the close 9 < 12.125 flips it down on the last bar only.
        c = np.array([10.0, 11, 12, 13, 9]); assert supertrend(c, c, c, 2, 1.0).tolist() == [1, 1, 1, 1, -1]
        up = np.arange(1.0, 301); assert rsi(up)[-1] > 99.99 and adx(up, up, up)[-1] > 99 and rsi(up[::-1].copy())[-1] < 0.01
        # Fibonacci pivots of H 25100 L 24900 C 25000: P 25000, R1 25076.4, R2 25123.6, R3 25200 (S mirrored)
        lv = [25000 + m * 200 for m in (-1, -0.618, -0.382, 0, 0.382, 0.618, 1)]
        s, t = piv_pick(25070, 25080, 1, lv); assert ap(s, 25076.4 - 12.54) and ap(t, 25123.6)           # R1 broken, stop 0.05% below, target R2
        s, t = piv_pick(25070, 25105, 1, lv); assert ap(s, 25076.4 - 12.5525) and ap(t, 25200)           # 28.6 of 47.2 already covered -> R3
        s, t = piv_pick(24930, 24920, -1, lv); assert ap(s, 24923.6 + 12.46) and ap(t, 24876.4)          # short: S1 broken, target S2
        s, t = piv_pick(25070, 25130, 1, lv); assert ap(s, 25123.6 - 12.565) and ap(t, 25200)            # R1 and R2 crossed -> R2 is the broken one
        assert piv_pick(25190, 25210, 1, lv) is None and piv_pick(24810, 24790, -1, lv) is None          # R3 / S3 break: no trade
        assert piv_pick(25080, 25090, 1, lv) is None and piv_pick(25070, 25080, -1, lv) is None          # no cross / wrong direction
        assert piv_pick(24990, 25190, 1, lv) is None                                                    # R2 broken, more than half way to R3 -> nothing beyond
        s, t = piv_pick(24900, 25070, 1, lv); assert ap(s, 25000 - 12.535) and ap(t, 25123.6)           # S1 and P crossed -> P broken; 70 of 76.4 covered -> R2; stop 82.5 pts < 0.40%
        assert piv_pick(24900, 25070, 1, lv[:3] + [24960.0] + lv[4:]) is None      # the same with the broken level at 24960: stop 122.5 pts > 0.40% (100.3) -> skip
        sp = np.r_[np.full(10, 100.0), 101, 99, 104, 96, np.full(NB - 14, 100.0)]
        assert x_levels(sp, 5, 1, 97, 103) == 12 and x_levels(sp, 5, 1, 97, 105) == 13 and x_levels(sp, 5, -1, 105, 97) == 13 and x_levels(sp, 13, 1, 90, 110) == XL
        assert x_levels(sp, 5, 1, 95, 103, True) == XL and x_levels(np.r_[sp[:14], 104, sp[15:]], 5, 1, 95, 103, True) == 14   # 5m-close target: minute 12 is not a 5m close, 14 is
        # feats alignment on two ramp days: 5m close = the minute close at 5b+4; pivots inputs = the previous day; ADX = the last COMPLETED 15m bar
        k0 = _syn("2021-08-01", 20000 + np.arange(NB) * 1.0, lambda sd, off, j: 100.0); k1 = _syn("2021-08-02", 20400 - np.arange(NB) * 1.0, lambda sd, off, j: 100.0); syn += [k0, k1]
        F = feats([k0, k1]); a15 = adx(*bars([k0, k1], 15)[1:])
        assert F["c"][1, 3] == P[k1]["spot"][19] and F["pc"][1, 0] == P[k0]["spot"][374] and F["pH"][1] == 20374 and F["pL"][1] == 20000 and F["pC"][1] == 20374 and np.isnan(F["pH"][0])
        assert F["adx"][1, 0] == a15[24] and F["adx"][1, 1] == a15[24] and F["adx"][1, 2] == a15[25] and F["adx"][1, 5] == a15[26] and np.isnan(F["adx"][0, 0]) and F["adx"][0, 2] == a15[0]
        # day 2 gaps up 26 then falls 5 per bar: ATR 5 -> 7.1, lower band 20398 - 21.3 = 20376.7; the bar-4 close 20376 is the first below it -> flip at minute 24
        assert F["st"][0, 74] == 1 and F["st"][1, 3] == 1 and F["st"][1, 74] == -1 and x_st(F, 1, 4) == 24 and x_st(F, 0, 100) == XL
        # F44: 20000, high 20100 at minute 10, low 19980 at minute 20 (fall 0.6%): entry level 20032.8, stop 20006.4, target 20072.4
        sp = flat.copy(); sp[10] = 20100; sp[11:21] = np.linspace(20088, 19980, 10); sp[21] = 20000; sp[22] = 20040; sp[23] = 20050; sp[24:] = 20080
        k = _syn("2021-08-03", sp, lambda sd, off, j: 100.0); syn.append(k); T = sig_f44([k])
        assert len(T) == 1 and T[0]["i"] == 22 and T[0]["x"] == 24 and ap(T[0]["ds"], 20040 - 20006.4) and ap(T[0]["dt"], 20072.4 - 20040), T
        P[k]["spot"][24:] = 20000.0; T = sig_f44([k]); assert len(T) == 1 and T[0]["i"] == 22 and T[0]["x"] == 24                       # 20000 <= 20006.4: the stop
        P[k]["spot"][12:] = 20050.0; assert sig_f44([k]) == []                                                                         # fall of 50 < 0.5%: never armed
        # SC strike: CE premium = 50 + 50 per strike in the money; 1% of 20000 = 200 -> 3 strikes ITM; all premiums 1000 -> none within 0.3%
        k = _syn("2021-08-04", flat, lambda sd, off, j: 50.0 + 50 * max(0, -off if sd == "CE" else off)); syn.append(k); assert sc_strike(P[k], 50, "NIFTY") == -3
        k = _syn("2021-08-05", flat, lambda sd, off, j: 1000.0); syn.append(k); assert sc_strike(P[k], 50, "NIFTY") is None
        # OVW: CE 100 until minute 39 then 90 (volume 1): VWAP 100 at 39, 98.89 at 44; two 5m closes below it at 44 and 49; CE OI rising, PE OI falling,
        # PE price 100 -> 110 (above its VWAP: no PE signal) -> sell the CE at minute 49. CE back to 100 from minute 60: under the 103.6 points stop,
        # the 5m close at 64 (100 > VWAP 96.9) exits. After that the CE stays above its VWAP: one trade.
        px = lambda sd, off, j: (100.0 if j < 40 or j >= 60 else 90.0) if sd == "CE" else (100.0 if j < 40 else 110.0)
        oi = lambda sd, off, j: 1000.0 + j if sd == "CE" else 5000.0 - j
        k = _syn("2021-08-06", flat, px, oi); syn.append(k); a = P[k]["C"][("CE", 20000.0)]; vw = _vwap(a)
        assert ap(vw[39], 100) and ap(vw[44], (4000 + 450) / 45) and ap(vw[64], (4000 + 1800 + 500) / 65)
        T = sig_ovw([k]); assert len(T) == 1 and T[0]["i"] == 49 and T[0]["legs"] == [("CE", 0, -1)] and T[0]["x"] == 64, T
        a[55, :4] = 105.0; assert x_ovw(k, 49, a, _vwap(a)) == 55                                                                     # 105 >= 90 + 13.6: the points stop
        for q in P[k]["C"].values(): q[:, 4] = 1000.0
        assert sig_ovw([k]) == []                                                                                                     # flat OI: no confirmation, no trade
        # OIX: previous day OI 1000 everywhere. Expiry day: CE OI 2000 (dCE 1000), PE OI 1400 until minute 199 then 1300 (dPE 300 <= 500): bearish;
        # aggregate PCR 0.4 at 12:00 -> 0.3 at 14:00 (falling) -> buy the PE. PE OI 1600 (dPE 600 > 500): no trade. Rising PCR: gate blocks the PE.
        kp = _syn("2021-08-07", flat, lambda sd, off, j: 100.0, exp="2021-08-08")
        k = _syn("2021-08-08", flat, lambda sd, off, j: 100.0, lambda sd, off, j: 2000.0 if sd == "CE" else (1400.0 if j < 200 else 1300.0), d0=1, exp="2021-08-08"); syn += [kp, k]
        assert oix_pick(P[k], P[kp], 285, "NIFTY") == "PE" and [t["legs"] for t in sig_oix([kp, k])] == [[("PE", 0, 1)]]
        assert oix_pick(P[k], P[kp], 285, "NIFTY", ratio=4.0) is None and oix_pick(P[k], P[kp], 285, "NIFTY", gate="level") == "PE"
        for (sd, K), q in P[k]["C"].items():
            if sd == "PE" and K != 20000.0: q[200:, 4] = 1500.0
        assert oix_pick(P[k], P[kp], 285, "NIFTY") is None and oix_pick(P[k], P[kp], 285, "NIFTY", gate="none") == "PE"               # PCR 0.4 -> (300 + 10 x 500) / 11000 = 0.48 rising
        P[k]["C"][("PE", 20000.0)][:, 4] = 1600.0; assert oix_pick(P[k], P[kp], 285, "NIFTY", gate="none") is None
        P[k]["exp"] = "2021-08-09"; assert sig_oix([kp, k]) == []                                                                     # previous day is another contract
        # GB: CE = PE = 10 at every strike (cap 0.065% of 20000 = 13), CE OI biggest at K+1 and PE OI biggest at K-1 -> ATM straddle; premium 20 -> none
        oi = lambda sd, off, j: 9000.0 if (sd, off) in (("CE", 1), ("PE", -1)) else 1000.0 + abs(off)
        k = _syn("2021-08-10", flat, lambda sd, off, j: 10.0, oi, d0=1); syn.append(k)
        assert gb_pick(P[k], 285, "NIFTY") == 0 and [t["legs"] for t in sig_gb([k])] == [[("CE", 0, 1), ("PE", 0, 1)]]
        P[k]["C"][("CE", 20050.0)][:, 4] = 1000.5; assert gb_pick(P[k], 285, "NIFTY") is None and gb_pick(P[k], 285, "NIFTY", oig=False) == 0   # CE OI next door is now the 11th biggest
        for q in P[k]["C"].values(): q[:, :4] = 20.0
        assert gb_pick(P[k], 285, "NIFTY", oig=False) is None and gb_pick(P[k], 285, "NIFTY", None, False) == 0
        # pricing: long CE 100 -> 110 and short CE 100 -> 110 through struct with the exit minute, against the cost functions by hand
        k = _syn("2021-08-11", flat, lambda sd, off, j: 100.0 if j < 100 else 110.0); syn.append(k); kc = k if L.COSTS == "dated" else None; q = L.qty("NIFTY", kc)
        h1, h2 = L.hs("NIFTY", 0, M0 + 51, 100.0), L.hs("NIFTY", 0, M0 + 121, 110.0)
        r = S.struct(k, 50, [("CE", 0, 1)], flat=M0 + 120 + 1); assert ap(r["pnl"], (110 - h2 - 100 - h1) * q - S._cost(100 + h1, 110 - h2, "NIFTY", L.LOTS, kc)) and not r["forced"] and r["held"] == 70
        r = S.struct(k, 50, [("CE", 0, -1)], flat=M0 + 120 + 1); assert ap(r["pnl"], (100 - h1 - 110 - h2) * q - S._cost(110 + h2, 100 - h1, "NIFTY", L.LOTS, kc))
        assert gross(k, 50, [("CE", 0, 1)], 120) == 10 * 650 and gross(k, 50, [("CE", 0, 1), ("PE", 0, 1)], 120) == 20 * 650 and gross(k, 50, [("CE", 0, -1)], 60) == 0
        P[k]["C"][("CE", 20000.0)][51, 6] = 0.0; assert not _can(k, 50, [("CE", 0, 1)]) and _can(k, 49, [("CE", 0, 1)]) and S.struct(k, 50, [("CE", 0, 1)], flat=M0 + 121) is None   # untraded entry bar
        # placebo twins: same side / strike rule / exit rule at another minute
        t = dict(k=k, i=50, legs=[("CE", 0, 1)], x=XL, dirn=1, ds=30.0, dt=40.0); assert plc("OIX", t, 240) == (t["legs"], XL) and plc("F44", t, 240) == (t["legs"], XL)
        P[k]["spot"][250] = 19960.0; assert plc("F44", t, 240)[1] == 250 and plc("PIV", t, 240)[1] == 250; P[k]["spot"][250] = 20000.0
        # stats: placebo p and the verdict rule
        T = pd.DataFrame(dict(pnl=[100.0] * 5, pl=[[0.0, np.nan]] * 5)); assert plac_p(T) == 0.0 and plac_p(T.assign(pnl=-1.0)) == 1.0
        r = dict(learn_n=100, test_n=40, forced_pct=2.0, learn_mean=500, learn_p=0.01, test_total=9000, test_p=0.004, test_q_pos="4/5", plac_p_test=0.01)
        assert verdict(r) == "PASS" and verdict(r, dict(learn_mean=10, test_mean=-5)) == "FAIL" and verdict(dict(r, test_p=0.01)) == "FAIL" and verdict(dict(r, forced_pct=11)) == "INCONCLUSIVE"
        assert verdict(dict(r, test_n=9)) == "UNTESTABLE" and verdict(dict(r, plac_p_test=0.2)) == "FAIL" and verdict(dict(r, test_q_pos="2/5")) == "FAIL" and abs(ALPHA - 0.05 / 6) < 1e-12
    finally:
        for k in syn: P.pop(k, None)
        S._EXT.clear()
    print(f"yt_lab selftest OK (COSTS={L.COSTS}): indicators, pivot picker, level exits, feature alignment, F44 / SC / OVW / OIX / GB signals, struct pricing, placebo twins, verdict rule")


# ================================================================ E53 (YouTube wave 2): seven frozen cells, one per rule. Frozen text: side-session
# note E53_youtube_freeze.md. Nothing above this line is changed by E53 (E51 runs as before). Run: yt_lab.py OUT selftest53|lookahead53|count53|gross53|e53|final53
#   GS   09:30 sell one 1-1.5% OTM option on the side of the overnight move     PR   09:25 premium race: buy the ITM option that crosses a level first
#   A220 break of the 14:20 five-minute bar, buy ATM                            PCR  11:00 change-in-OI PCR, buy an OTM option near its own VWAP
#   OIC  09:30 OI-wall asymmetry, credit spread                                 ORS  30-minute opening range, sell the opposite ATM option
#   BBH  first-hour Bollinger lower band + Heikin Ashi turn on the option's 1m chart (half out at 2R, runner at cost)
CELLS53 = ["GS", "PR", "A220", "PCR", "OIC", "ORS", "BBH"]; ALPHA53 = 0.05 / len(CELLS53)
WIN53 = dict(GS=(5, 105), GSm=(5, 105), PR=(5, 105), A220=(225, 334), PCR=(105, 284), OIC=(5, 105), ORS=(30, 344), BBH=(2, 61))   # placebo entry minutes
EVENTS = L.RBI | {"2022-02-01", "2023-02-01", "2024-02-01", "2024-07-23", "2025-02-01", "2026-02-01", "2024-06-04"}   # RBI, Union Budget, election result
LEAK53 = None              # lookahead53 positive controls: "bar" (A220 reads a bar 20 minutes ahead), "centre" (BBH band), "range" (ORS range = the day's last close)


def _off(p, i, K, sym):
    """K as a strike offset from the ATM of minute i (struct's leg format)."""
    return int(round((K - p["atm"][i]) / STEP[sym]))


def x_opt(a, i, up=None, dn=None, end=XL):
    """exit-decision minute on one contract's 1m closes: the first j in (i, end) with close >= up or close <= dn; else end."""
    for j in range(i + 1, end):
        if (up is not None and a[j, 3] >= up) or (dn is not None and a[j, 3] <= dn): return j
    return end


# ---------------------------------------------------------------- GS
def gs_pick(p, i, side):
    """the strike of `side` 1.0-1.5% of spot out of the money whose close at i is in 0.122-0.170% of spot, nearest 0.146%; None if none."""
    s = p["spot"][i]; sg = 1 if side == "CE" else -1
    c = [(abs(a[i, 3] - 0.00146 * s), K) for (sd, K), a in p["C"].items() if sd == side and 0.01 * s <= sg * (K - s) <= 0.015 * s and 0.00122 * s <= a[i, 3] <= 0.0017 * s]
    return min(c)[1] if c else None


def x_gs(p, i, a): return x_opt(a, i, up=a[i + 1, 0] + 0.00073 * p["spot"][i])


def sig_gs(ks, D=None, flip=False, i=14):
    out = []
    for d in (D or range(1, len(ks))):
        if not d: continue
        k, p = ks[d], P[ks[d]]; s0, s = P[ks[d - 1]]["spot"][359], p["spot"][i]
        if not np.isfinite(s0 + s + p["atm"][i]) or s == s0: continue
        side = "CE" if (s < s0) != flip else "PE"; K = gs_pick(p, i, side)
        if K is None: continue
        legs = [(side, _off(p, i, K, k[0]), -1)]
        if _can(k, i, legs): out.append(dict(k=k, i=i, legs=legs, x=x_gs(p, i, p["C"][(side, K)])))
    return out


# ---------------------------------------------------------------- PR
def pr_pick(p, i0=9, lv=0.00735):
    """(level, {side: strike}): per side the strike with the highest close at i0 that is <= level (and >= 0.85 x level)."""
    Lv = lv * p["spot"][i0]; out = {}
    for sd in ("CE", "PE"):
        c = [(a[i0, 3], K) for (s_, K), a in p["C"].items() if s_ == sd and 0.85 * Lv <= a[i0, 3] <= Lv]
        if c: out[sd] = max(c)[1]
    return Lv, out


def sig_pr(ks, D=None, lv=0.00735, bracket=True, xt=29):
    out = []
    for d in (D or range(len(ks))):
        k, p = ks[d], P[ks[d]]; Lv, c = pr_pick(p, 9, lv)
        for j in range(10, 20):
            hit = [sd for sd, K in c.items() if p["C"][(sd, K)][j, 3] > Lv]
            if not hit: continue
            if len(hit) == 1 and np.isfinite(p["atm"][j]):
                sd = hit[0]; a = p["C"][(sd, c[sd])]; legs = [(sd, _off(p, j, c[sd], k[0]), 1)]
                if _can(k, j, legs): out.append(dict(k=k, i=j, legs=legs, K=c[sd], x=x_opt(a, j, Lv * (1 + 40 / 180), Lv * (1 - 20 / 180), xt) if bracket else xt))
            break   # the race is over at the first cross, traded or not
    return out


# ---------------------------------------------------------------- A220
def x_a220(sp, i, dirn, stop, cap):
    """exit-decision minute: a spot close at / through the stop, or the first 09:15-aligned 5m bar ending after i that closes against dirn; else cap."""
    for j in range(i + 1, cap):
        if dirn * (sp[j] - stop) <= 0 or (j % 5 == 4 and dirn * (sp[j] - sp[j - 4]) < 0): return j
    return cap


def sig_a220(ks, D=None, b0=305, hold=False, counter=False):
    out = []
    for d in (D or range(len(ks))):
        k, p = ks[d], P[ks[d]]; sp = p["spot"]; w = sp[b0 + 20:b0 + 25] if LEAK53 == "bar" else sp[b0:b0 + 5]; H, Lo = w.max(), w.min(); cap = b0 + 37
        for j in range(b0 + 5, b0 + 30):
            dirn = 1 if sp[j] > H else -1 if sp[j] < Lo else 0
            if not dirn: continue
            legs = [("CE" if dirn > 0 else "PE", 0, 1)]; stop = Lo if dirn > 0 else H
            if not (counter and dirn * (sp[b0 + 4] - sp[0]) >= 0) and _can(k, j, legs):
                out.append(dict(k=k, i=j, legs=legs, x=XL if hold else x_a220(sp, j, dirn, stop, cap), dirn=dirn, ds=dirn * (sp[j] - stop), cap=cap - j))
            break   # one break a day
    return out


# ---------------------------------------------------------------- PCR
def pcr_val(p, pp, i, sym):
    """change-in-OI PCR at minute i over B +- N strikes: B = the day's first ATM, N = business days to expiry clipped to 1..5; NaN unless both sums > 0."""
    at = p["atm"][:i + 1]; at = at[np.isfinite(at)]
    if not len(at): return np.nan
    N = min(max(int(p["dte"]), 1), 5); D = [(doi(p, pp, "CE", at[0] + o * STEP[sym], i), doi(p, pp, "PE", at[0] + o * STEP[sym], i)) for o in range(-N, N + 1)]
    D = [x for x in D if np.isfinite(x[0] + x[1])]; sc, sq = sum(x[0] for x in D), sum(x[1] for x in D)
    return sq / sc if D and sc > 0 and sq > 0 else np.nan


def pcr_strike(p, i, sym, side):
    """the strike among OTM1..OTM6 of `side` (from the ATM at i) whose close at i is nearest 0.27% of spot."""
    s = p["spot"][i]; sg = 1 if side == "CE" else -1; c = []
    for n in range(1, 7):
        a = p["C"].get((side, p["atm"][i] + sg * n * STEP[sym]))
        if a is not None and np.isfinite(a[i, 3]): c.append((abs(a[i, 3] - 0.0027 * s), n))
    return p["atm"][i] + sg * min(c)[1] * STEP[sym] if c else None


def x_pcr(p, a, j): return x_opt(a, j, up=a[j, 3] + 0.0012 * p["spot"][j], dn=np.nanmin(a[:j + 1, 2]))


def sig_pcr(ks, D=None, i0=105, hi=1.25, lo=0.75, plain=False):
    out = []
    for d in (D or range(1, len(ks))):
        if not d: continue
        k, p, pp = ks[d], P[ks[d]], P[ks[d - 1]]; sym = k[0]
        if p["d0"] or str(pp["exp"]) != str(p["exp"]) or not np.isfinite(p["atm"][i0]): continue
        v = pcr_val(p, pp, i0, sym); side = "CE" if v > hi else "PE" if v < lo else None; K = pcr_strike(p, i0, sym, side) if side else None
        if K is None: continue
        a = p["C"][(side, K)]; x = -1; n = 0
        if plain:
            legs = [(side, _off(p, i0, K, sym), 1)]
            if _can(k, i0, legs): out.append(dict(k=k, i=i0, legs=legs, x=XL, K=K))
            continue
        vw = _vwap(a)
        for j in range(i0, 285):
            if j > x and n < 2 and a[j, 6] > 0 and abs(a[j, 3] / vw[j] - 1) <= 0.03 and np.isfinite(p["atm"][j]):
                legs = [(side, _off(p, j, K, sym), 1)]
                if _can(k, j, legs): x = x_pcr(p, a, j); n += 1; out.append(dict(k=k, i=j, legs=legs, x=x, K=K))
    return out


# ---------------------------------------------------------------- OIC
def oic_pick(p, i, sym, thr=0.85):
    """None, or dict(dirn, tgt, stop, legs): OI walls (>= thr x the side's largest OI) among CE ATM+1..+5 and PE ATM-1..-5 at minute i.
    >= 2 put walls and exactly 1 call wall -> bullish put credit spread at the put wall nearest spot (long two strikes below); mirror."""
    st = STEP[sym]; atm = p["atm"][i]; s = p["spot"][i]; C = p["C"]
    oc = [_oi(C[("CE", atm + n * st)], i) if ("CE", atm + n * st) in C else np.nan for n in range(1, 6)]
    op = [_oi(C[("PE", atm - n * st)], i) if ("PE", atm - n * st) in C else np.nan for n in range(1, 6)]
    if not np.isfinite(sum(oc) + sum(op)): return None
    wc = [n for n in range(1, 6) if oc[n - 1] >= thr * max(oc)]; wp = [n for n in range(1, 6) if op[n - 1] >= thr * max(op)]
    if len(wp) >= 2 and len(wc) == 1 and atm + wc[0] * st - 0.004 * s > s:
        return dict(dirn=1, tgt=atm + wc[0] * st - 0.004 * s, stop=atm - wp[0] * st, Ks=("PE", atm - wp[0] * st, atm - (wp[0] + 2) * st))
    if len(wc) >= 2 and len(wp) == 1 and atm - wp[0] * st + 0.004 * s < s:
        return dict(dirn=-1, tgt=atm - wp[0] * st + 0.004 * s, stop=atm + wc[0] * st, Ks=("CE", atm + wc[0] * st, atm + (wc[0] + 2) * st))
    return None


def x_oic(sp, i, dirn, stop, tgt):
    """exit-decision minute: the first spot 5m close at / beyond the target or strictly through the stop."""
    for j in range(i + 1, XL):
        if j % 5 == 4 and (dirn * (sp[j] - tgt) >= 0 or dirn * (sp[j] - stop) < 0): return j
    return XL


def oic_legs(p, i, sym, Ks): return [(Ks[0], _off(p, i, Ks[1], sym), -1), (Ks[0], _off(p, i, Ks[2], sym), 1)]


def sig_oic(ks, D=None, i=14):
    out = []
    for d in (D or range(len(ks))):
        k, p = ks[d], P[ks[d]]; q = oic_pick(p, i, k[0]) if np.isfinite(p["atm"][i]) else None
        if q and _can(k, i, oic_legs(p, i, k[0], q["Ks"])):
            out.append(dict(k=k, i=i, legs=oic_legs(p, i, k[0], q["Ks"]), x=x_oic(p["spot"], i, q["dirn"], q["stop"], q["tgt"]), **q))
    return out


# ---------------------------------------------------------------- ORS
def x_ors(p, a, i, dirn, edge):
    """exit-decision minute of the short option a: its 1m close <= entry open - 0.065% of spot, or a spot 3m close through `edge` against dirn."""
    tg = a[i + 1, 0] - 0.00065 * p["spot"][i]; sp = p["spot"]
    for j in range(i + 1, XL):
        if a[j, 3] <= tg or (j % 3 == 2 and dirn * (sp[j] - edge) < 0): return j
    return XL


def sig_ors(ks, D=None):
    out = []
    for d in (D or range(len(ks))):
        k, p = ks[d], P[ks[d]]; sp = p["spot"]; RH, RL = (sp[-1], sp[-1]) if LEAK53 == "range" else (sp[:30].max(), sp[:30].min()); x = -1; done = set()
        for j in range(32, 345, 3):
            dirn = 1 if sp[j] > RH else -1 if sp[j] < RL else 0
            if dirn and dirn not in done and j >= x:   # j == x: the stop bar of the first trade is the signal of the second
                sd = "PE" if dirn > 0 else "CE"; legs = [(sd, 0, -1)]
                if _can(k, j, legs):
                    edge = RL if dirn > 0 else RH; x = x_ors(p, p["C"][(sd, p["atm"][j])], j, dirn, edge); done.add(dirn)
                    out.append(dict(k=k, i=j, legs=legs, x=x, dirn=dirn, edge=edge))
    return out


# ---------------------------------------------------------------- BBH
def ha_bb(a, warm=None, n=20, m=2.0):
    """(H, w0): H[w0 + minute] = Heikin Ashi open, high, low, close and the lower Bollinger(n, m) of the HA close, built over the traded bars of
    `warm` (the same contract's previous day, or None) followed by today's `a`; NaN on untraded bars and before n bars exist."""
    A = a if warm is None else np.vstack([warm, a]); idx = np.flatnonzero(np.isfinite(A[:, :4]).all(1) & (A[:, 6] > 0)); H = np.full((len(A), 5), np.nan)
    if len(idx):
        o, h, l, c = A[idx, :4].T; hc = (o + h + l + c) / 4; ho = np.empty(len(idx)); ho[0] = (o[0] + c[0]) / 2
        for t in range(1, len(idx)): ho[t] = (ho[t - 1] + hc[t - 1]) / 2
        r = pd.Series(hc).rolling(n, center=LEAK53 == "centre")
        H[idx] = np.c_[ho, np.maximum.reduce([h, ho, hc]), np.minimum.reduce([l, ho, hc]), hc, (r.mean() - m * r.std(ddof=0)).values]
    return H, len(A) - len(a)


def x_bbh(a, i, E_, R, full=False):
    """(x1, x2) exit-decision minutes of the first half and of the runner; touch triggers on the real 1m low / high, the stop wins a tie.
    Before the target (E + 2R) is touched a low <= E - R closes both; after it the runner's stop is E (cost); full=True: all out at the target."""
    for j in range(i + 1, XL):
        if a[j, 2] <= E_ - R: return j, j
        if a[j, 1] >= E_ + 2 * R:
            return (j, j) if full else (j, next((q for q in range(j + 1, XL) if a[q, 2] <= E_), XL))
    return XL, XL


def bbh_parts(x1, x2): return [(x1, L.LOTS // 2), (x2, L.LOTS - L.LOTS // 2)]


def sig_bbh(ks, D=None, touch=True, full=False, hold=None):
    out = []
    for d in (D or range(len(ks))):
        k, p = ks[d], P[ks[d]]; sym = k[0]; K0 = p["atm"][0]; HH = {}; pv = P[ks[d - 1]] if d and str(P[ks[d - 1]]["exp"]) == str(p["exp"]) else None
        for sd in ("CE", "PE"):
            a = p["C"].get((sd, K0)) if np.isfinite(K0) else None
            if a is not None: HH[sd] = (a,) + ha_bb(a, pv["C"].get((sd, K0)) if pv else None)
        if len(HH) < 2: continue
        free = -1; n = 0
        for s in range(1, 61):
            sg = []
            for sd, (a, h, w0) in HH.items():
                g = w0 + s; red = lambda t: h[t, 3] < h[t, 0]
                if g >= 3 and h[g, 3] > h[g, 0] and red(g - 1) and red(g - 2) and (not touch or any(h[t, 2] <= h[t, 4] for t in range(g - 3, g + 1))):
                    buf = 0.00004 * p["spot"][s]; E_ = h[g, 1] + buf; r0 = s - 1
                    while r0 > 0 and red(w0 + r0 - 1): r0 -= 1
                    R = E_ - (np.nanmin(a[r0:s + 1, 2]) - buf)
                    if 0 < R <= 0.00077 * p["spot"][s] and a[s + 1, 1] >= E_: sg.append((sd, a, E_, R))
            i = s + 1
            if len(sg) == 1 and n < 2 and i > free and np.isfinite(p["atm"][i]):
                sd, a, E_, R = sg[0]; legs = [(sd, _off(p, i, K0, sym), 1)]
                if _can(k, i, legs):
                    x1, x2 = (min(i + hold, XL),) * 2 if hold else x_bbh(a, i, E_, R, full); free = x1; n += 1
                    out.append(dict(k=k, i=i, legs=legs, x=x2, parts=bbh_parts(x1, x2), R=R, K=K0))
    return out


def all_signals53(ks, D=None):
    return dict(GS=sig_gs(ks, D), GSm=sig_gs(ks, D, flip=True), PR=sig_pr(ks, D), A220=sig_a220(ks, D), PCR=sig_pcr(ks, D), OIC=sig_oic(ks, D), ORS=sig_ors(ks, D), BBH=sig_bbh(ks, D))


# ---------------------------------------------------------------- E53 pricing, placebo, stats
def price53(k, i, legs, parts):
    """(pnl, forced, gross) of one trade whose lots leave in `parts` = [(exit-decision minute, lots)], each priced by struct."""
    pnl = g = 0.0; forced = False
    for x, lots in parts:
        r = S.struct(k, i, legs, flat=M0 + x + 1, lots=lots)
        if r is None: return None
        pnl += r["pnl"]; forced |= r["forced"]; g += gross(k, i, legs, x) * lots / L.LOTS
    return pnl, forced, g


def plc53(cell, t, i2):
    """the placebo twin of trade t at minute i2: (legs, parts) or None (see the freeze file, 'Placebo window' of each cell)."""
    k = t["k"]; p = P[k]; sym = k[0]; sd = t["legs"][0][0]; one = lambda legs, x: (legs, [(x, L.LOTS)])
    if not np.isfinite(p["atm"][i2]): return None
    if cell in ("GS", "GSm"):
        K = gs_pick(p, i2, sd); a = p["C"].get((sd, K)); return None if K is None or not np.isfinite(a[i2 + 1, 0]) else one([(sd, _off(p, i2, K, sym), -1)], x_gs(p, i2, a))
    if cell == "A220": s = p["spot"][i2]; return one(t["legs"], x_a220(p["spot"], i2, t["dirn"], s - t["dirn"] * t["ds"], min(i2 + t["cap"], XL)))
    if cell == "OIC": return one(oic_legs(p, i2, sym, t["Ks"]), x_oic(p["spot"], i2, t["dirn"], t["stop"], t["tgt"]))
    if cell == "ORS": a = p["C"].get((sd, p["atm"][i2])); return None if a is None or not np.isfinite(a[i2 + 1, 0]) else one(t["legs"], x_ors(p, a, i2, t["dirn"], t["edge"]))
    a = p["C"][(sd, t["K"])]; c = a[i2, 3]; legs = [(sd, _off(p, i2, t["K"], sym), 1)]   # PR, PCR, BBH: the same contract
    if not np.isfinite(c): return None
    if cell == "PR": return one(legs, x_opt(a, i2, c * (1 + 40 / 180), c * (1 - 20 / 180), min(i2 + 15, XL)))
    if cell == "PCR": return one(legs, x_pcr(p, a, i2))
    return legs, bbh_parts(*x_bbh(a, i2, c, t["R"]))


def _work53(a):
    cell, t = a; k, i = t["k"], t["i"]; parts = t.get("parts") or [(t["x"], L.LOTS)]; r = price53(k, i, t["legs"], parts)
    if r is None: return None
    rg = np.random.default_rng(zlib.crc32(repr((cell, k, i)).encode())); pl = []
    for i2 in rg.integers(WIN53[cell][0], WIN53[cell][1] + 1, NPL):
        q = plc53(cell, t, int(i2)); r2 = price53(k, int(i2), q[0], q[1]) if q else None; pl.append(r2[0] if r2 else np.nan)
    return dict(cell=cell, sym=k[0], day=k[1], i=i, x=t["x"], side=t["legs"][0][0], off=t["legs"][0][1], pnl=r[0], forced=r[1], gross=r[2], pl=pl)


def verdict53(r, dated=None):
    """the frozen E53 rule (freeze file section 3): the E51 rule at alpha 0.05 / 7, plus placebo p < 0.05 on LEARN+TEST."""
    if r["learn_n"] < 30 or r["test_n"] < 10: return "UNTESTABLE"
    if r["forced_pct"] > 10: return "INCONCLUSIVE"
    ok = (r["learn_mean"] > 0 and r["learn_p"] < 0.05 and r["test_total"] > 0 and r["test_p"] < ALPHA53 and int(str(r["test_q_pos"]).split("/")[0]) >= 3
          and r["plac_p_test"] < 0.05 and r["plac_p_all"] < 0.05 and (dated is None or (dated["learn_mean"] > 0 and dated["test_mean"] > 0)))
    return "PASS" if ok else "FAIL"


def stats53(cell, T):
    """E51's stats row plus: placebo p on LEARN, totals without the 10 best days, means without the fixed public event days."""
    r = stats(cell, T)
    if not len(T): return r
    for nm, G in (("learn", T[T.day < HO]), ("test", T[T.day >= HO])):
        if len(G):
            dd = G.groupby("day").pnl.sum(); X = G[~G.day.isin(EVENTS)]
            r.update({f"{nm}_ex10": round(dd.sum() - dd.nlargest(10).sum()), f"{nm}_mean_xev": round(X.pnl.mean()) if len(X) else np.nan})
            if nm == "learn": r["plac_p_learn"] = round(plac_p(G), 3)
    r["verdict"] = "CONTROL" if cell not in CELLS53 else verdict53(r) if r["verdict"] != "UNTESTABLE" else "UNTESTABLE"
    return r


def study_count53():
    """signal counts only (no prices): LEARN / TEST per cell and index."""
    for sym in ("NIFTY", "SENSEX"):
        ks = keys(sym)
        for c, v in all_signals53(ks).items(): print(sym, c, "LEARN", sum(t["k"][1] < HO for t in v), "TEST", sum(t["k"][1] >= HO for t in v), flush=True)


def study_e53():
    """the seven frozen cells + the GSm control, both indices pooled, LEARN and TEST in one pass (TEST is scored once: run this once per cost mode)."""
    order = CELLS53 + ["GSm"]; sig = {c: [] for c in order}
    for sym in ("NIFTY", "SENSEX"):
        for c, v in all_signals53(keys(sym)).items(): sig[c] += v
    rows, TT = [], []
    with get_context("fork").Pool(8) as pool:
        for c in order:
            T = pd.DataFrame([r for r in pool.map(_work53, [(c, t) for t in sig[c]], chunksize=16) if r]); rows.append(stats53(c, T)); TT.append(T)
            print(c, "signals", len(sig[c]), "priced", len(T), flush=True)
    R = pd.DataFrame(rows); pd.set_option("display.width", 320); pd.set_option("display.max_columns", 50); print(R.to_string(index=False))
    T = pd.concat(TT); T.drop(columns="pl").to_csv(f"{L.OUT}/yt_e53_trades_{L.COSTS}.csv", index=False); R.to_csv(f"{L.OUT}/yt_e53_{L.COSTS}.csv", index=False)
    T = T.assign(part=np.where(T.day < HO, "LEARN", "TEST"), hour=9 + (T.i + 15) // 60)
    print("by index and part (n, mean, total):"); print(T.groupby(["cell", "sym", "part"]).pnl.agg(["size", "mean", "sum"]).round(0).to_string())
    print("by entry hour and part (n, mean, total):"); print(T.groupby(["cell", "part", "hour"]).pnl.agg(["size", "mean", "sum"]).round(0).to_string())
    print(f"COSTS={L.COSTS}; alpha = 0.05 / {len(CELLS53)} = {ALPHA53:.5f}; GSm is a control row; the final verdict needs both cost modes: yt_lab.py OUT final53")


def study_final53():
    """join the COSTS=today and COSTS=dated rows; the verdict uses today's row plus the dated sign check."""
    A, Dt = (pd.read_csv(f"{L.OUT}/yt_e53_{c}.csv").set_index("cell") for c in ("today", "dated")); out = []
    cols = ["learn_n", "learn_mean", "learn_win", "learn_p", "test_n", "test_mean", "test_p", "test_q_pos", "plac_p_learn", "plac_p_test", "plac_p_all", "forced_pct", "worst",
            "learn_ex10", "test_ex10", "learn_mean_xev", "test_mean_xev"]
    for c in CELLS53 + ["GSm"]:
        a, d = A.loc[c].to_dict(), Dt.loc[c].to_dict()
        out.append(dict(cell=c, **{n: a.get(n, np.nan) for n in cols}, dated_learn_mean=d.get("learn_mean", np.nan), dated_test_mean=d.get("test_mean", np.nan),
                        verdict=a["verdict"] if a["verdict"] != "PASS" else verdict53(a, d)))
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 50); print(pd.DataFrame(out).to_string(index=False)); print(f"alpha = {ALPHA53:.5f}")


def study_gross53():
    """gross-expectancy maps of the four long-option families on LEARN only (freeze file section 4). Can only CLOSE a family."""
    ks = {s: [k for k in keys(s) if k[1] < HO] for s in ("NIFTY", "SENSEX")}; pd.set_option("display.width", 250)
    def pt(fam, name, fn):
        R = [(r[2], r[0]) for s in ks for t in fn(ks[s]) for r in [price53(t["k"], t["i"], t["legs"], t.get("parts") or [(t["x"], L.LOTS)])] if r]
        R = np.array([x for x in R if np.isfinite(x[0])]).reshape(-1, 2); n = len(R); g, h = (R[:, 0].mean(), (R[:, 0] - R[:, 1]).mean()) if n else (np.nan, np.nan)
        print(fam, name, n, flush=True)
        return dict(fam=fam, point=name, n=n, gross=round(g) if n else np.nan, hurdle=round(h) if n else np.nan, net=round(g - h) if n else np.nan, win_gross=round((R[:, 0] > 0).mean() * 100, 1) if n else np.nan, open=bool(n >= 30 and g > h))
    rows = [pt("PR", "FROZEN 0.735% bracket 09:45", sig_pr)]
    rows += [pt("PR", f"level {lv:.5f} no bracket exit {nm}", lambda K, lv=lv, xt=xt: sig_pr(K, None, lv, False, xt)) for lv in (0.005, 0.00735, 0.01) for nm, xt in (("09:45", 29), ("10:00", 44), ("15:15", XL))]
    rows += [pt("A220", f"bar {nm} {'hold 15:15' if h else 'frozen exits'}", lambda K, b0=b0, h=h: sig_a220(K, None, b0, h)) for nm, b0 in (("14:00", 285), ("14:20", 305), ("14:40", 325)) for h in (False, True)]
    rows += [pt("A220", "bar 14:20 frozen exits, counter-trend only", lambda K: sig_a220(K, None, 305, False, True))]
    rows += [pt("PCR", "FROZEN 11:00 1.25/0.75 VWAP entry", sig_pcr)]
    rows += [pt("PCR", f"read {nm} band {hi}/{lo} buy at read, hold 15:15", lambda K, i0=i0, hi=hi, lo=lo: sig_pcr(K, None, i0, hi, lo, True)) for nm, i0 in (("10:00", 45), ("11:00", 105), ("12:00", 165)) for hi, lo in ((1.25, 0.75), (1.5, 0.67))]
    rows += [pt("BBH", f"touch {tc} exit {'all at 2R' if fu else 'half 2R + runner'}", lambda K, tc=tc, fu=fu: sig_bbh(K, None, tc, fu)) for tc in (True, False) for fu in (False, True)]
    rows += [pt("BBH", "frozen signal, 15-minute hold", lambda K: sig_bbh(K, None, True, False, 15))]
    R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv(f"{L.OUT}/yt_e53_gross_{L.COSTS}.csv", index=False)
    for fam in ("PR", "A220", "PCR", "BBH"):
        G = R[R.fam == fam]; print(f"family {fam}: {'OPEN' if G.open.any() else 'CLOSED'} ({int(G.open.sum())} of {len(G)} map points with n >= 30 have LEARN gross > hurdle)")


# ---------------------------------------------------------------- E53 look-ahead scan
def _la53(sym, samples, rg):
    """for each (day index d, cut minute): scramble day d after the cut and the next two days, rebuild every E53 signal of day d, and list the
    entries decided by the cut that changed and the exits decided by the cut that changed."""
    ks = keys(sym); bad = []; seen = dict.fromkeys(CELLS53 + ["GSm"], 0)
    def sigs(d): return {c: [(t["i"], tuple(t["legs"]), tuple(x for x, _ in t["parts"]) if "parts" in t else (t["x"],)) for t in v] for c, v in all_signals53(ks, [d]).items()}
    for d, cut in samples:
        s0 = sigs(d); undo = B._scr([(ks[d], cut)] + [(k, -1) for k in ks[d + 1:d + 3]], rg)
        try: s1 = sigs(d)
        finally: B._undo(undo)
        for c in seen:
            a, b = [t for t in s0[c] if t[0] <= cut], [t for t in s1[c] if t[0] <= cut]; seen[c] += len(a)
            if [t[:2] for t in a] != [t[:2] for t in b]: bad.append((sym, ks[d][1], cut, c + " entry"))
            elif any((x0 != x1) if x0 <= cut else (x1 <= cut) for t0, t1 in zip(a, b) for x0, x1 in zip(t0[2], t1[2])): bad.append((sym, ks[d][1], cut, c + " exit"))
    return bad, seen


def study_lookahead53(n_days=60, seed=53):
    """scramble-after-the-decision scan on sampled (day, cut) pairs of both indices, then three planted leaks the same scan must catch
    (A220 reading a bar 20 minutes ahead, a centred Bollinger window in BBH, an ORS range set to the day's last close)."""
    global LEAK53
    rg = np.random.default_rng(seed); bad = []; n = 0; S_ = {}; seen = {}
    for sym in ("NIFTY", "SENSEX"):
        ks = keys(sym); dd = rg.choice(range(30, len(ks) - 3), n_days, replace=False)
        S_[sym] = [(int(d), int(c)) for d, c in zip(dd, rg.choice([14, 16, 20, 30, 45, 62, 110, 160, 240, 311, 316, 322, 335, 344], n_days))]
        b, sn = _la53(sym, S_[sym], rg); bad += b; n += len(S_[sym]); seen = {c: seen.get(c, 0) + sn[c] for c in sn}
    print(f"lookahead53: {n} (day, cut) samples, both indices, 7 cells + control: {len(bad)} changes; real entries checked per cell {seen}", bad[:10]); assert not bad, bad
    for leak, want in (("bar", "A220 entry"), ("centre", "BBH entry"), ("range", "ORS entry")):
        LEAK53 = leak
        try: got = {b[3] for s in S_ for b in _la53(s, S_[s], rg)[0]}
        finally: LEAK53 = None
        print(f"planted leak '{leak}': caught as {sorted(got)}"); assert want in got, (leak, got)
    print("lookahead53 OK (no entry or exit decided by the cut changed; the three planted leaks are caught)")


# ---------------------------------------------------------------- E53 selftest (hand-computed known answers on synthetic days dated 2021-09)
def study_selftest53():
    ap = lambda a, b: abs(a - b) < 1e-6; flat = np.full(NB, 20000.0); syn = []; c100 = lambda sd, off, j: 100.0
    def col(k, sd, off): return P[k]["C"][(sd, 20000.0 + off * 50)]
    try:
        # ---- GS. Yesterday 15:15 = 20000, today 09:30 = 19990 (lower -> sell a call). Calls: 20200 at 40, 20250 at 30, 20300 at 26. Distance band
        # 1.0-1.5% of 19990 = 199.9..299.85 -> 20200 and 20250 only; premium band 24.39..33.98 -> 20250 (30). Stop = 30 + 0.073% x 19990 = 44.59.
        kp = _syn("2021-09-01", flat, c100); px = lambda sd, off, j: {4: 40.0, 5: 30.0, 6: 26.0}.get(off, 100.0) if sd == "CE" else 100.0
        k = _syn("2021-09-02", flat - 10, px); syn += [kp, k]; ks = [kp, k]
        assert gs_pick(P[k], 14, "CE") == 20250.0 and gs_pick(P[k], 14, "PE") is None
        T = sig_gs(ks); assert len(T) == 1 and T[0]["i"] == 14 and T[0]["legs"] == [("CE", 5, -1)] and T[0]["x"] == XL, T
        col(k, "CE", 5)[100, :4] = 44.0; assert sig_gs(ks)[0]["x"] == XL
        col(k, "CE", 5)[100, :4] = 45.0; assert sig_gs(ks)[0]["x"] == 100                                     # 45 >= 44.59: the stop
        assert sig_gs(ks, flip=True) == []                                                                   # flipped side: no put in the band
        col(k, "PE", -5)[:, :4] = 28.0; T = sig_gs(ks, flip=True); assert T[0]["legs"] == [("PE", -5, -1)]   # 19750 is 1.2% away at 28
        q = plc53("GS", sig_gs(ks)[0], 50); assert q == ([("CE", 5, -1)], [(100, L.LOTS)]) and plc53("GS", sig_gs(ks)[0], 120)[1] == [(XL, L.LOTS)]
        P[k]["spot"][14] = 20000.0; assert sig_gs(ks) == []; P[k]["spot"][14] = 19990.0                        # unchanged overnight: no trade
        col(k, "CE", 5)[14, 3] = 35.0; assert sig_gs(ks) == []                                               # 35 > 33.98: outside the premium band
        # ---- PR. Level = 0.735% x 20000 = 147. Calls: 19900 at 140 (candidate), 19850 at 150 (above the level), 19950 at 120 (< 0.85 x 147).
        # Put 20100 at 130 (candidate). The call closes at 148 from minute 12 -> buy it. Stop 130.67, target 179.67, time exit minute 29.
        px = lambda sd, off, j: ({-2: 140.0 if j < 12 else 148.0, -3: 150.0, -1: 120.0}.get(off, 10.0) if sd == "CE" else {2: 130.0}.get(off, 10.0))
        k = _syn("2021-09-03", flat, px); syn.append(k); Lv, c = pr_pick(P[k]); assert ap(Lv, 147.0) and c == {"CE": 19900.0, "PE": 20100.0}
        T = sig_pr([k]); assert len(T) == 1 and T[0]["i"] == 12 and T[0]["legs"] == [("CE", -2, 1)] and T[0]["x"] == 29 and T[0]["K"] == 19900.0, T
        col(k, "CE", -2)[20, :4] = 180.0; assert sig_pr([k])[0]["x"] == 20                                    # 180 >= 179.67: target
        col(k, "CE", -2)[15, :4] = 130.0; assert sig_pr([k])[0]["x"] == 15 and sig_pr([k], bracket=False, xt=44)[0]["x"] == 44   # 130 <= 130.67: stop
        t = sig_pr([k])[0]; assert plc53("PR", t, 60) == ([("CE", -2, 1)], [(75, L.LOTS)])                    # twin at 148: no 131.6 / 180.9 touch in 15 minutes
        col(k, "PE", 2)[12, :4] = 148.0; assert sig_pr([k]) == []                                             # both cross in the same minute: no trade
        col(k, "PE", 2)[12, :4] = 130.0; col(k, "CE", -2)[10:20, :4] = 140.0; assert sig_pr([k]) == []        # nobody crosses by 09:35
        # ---- A220. Bar 305..309 closes 20000 20010 20005 19995 20002 -> H 20010, L 19995. 20012 at minute 312 -> call, stop 19995 (17 away).
        # Bar 315..319 opens 20020, closes 20018 (against) -> exit decision 319. A close of 19990 at 316 -> stop. No adverse bar -> cap 342.
        sp = flat.copy(); sp[305:310] = [20000, 20010, 20005, 19995, 20002]; sp[310:312] = 20003; sp[312] = 20012; sp[313] = 20015; sp[314:316] = 20020
        sp[316:320] = [20025, 20022, 20021, 20018]; sp[320:] = 20018
        k = _syn("2021-09-04", sp, c100); syn.append(k); T = sig_a220([k])
        assert len(T) == 1 and T[0]["i"] == 312 and T[0]["legs"] == [("CE", 0, 1)] and T[0]["x"] == 319 and ap(T[0]["ds"], 17) and T[0]["cap"] == 30, T
        assert sig_a220([k], hold=True)[0]["x"] == XL and sig_a220([k], counter=True) == []                  # 09:15 -> 14:24 is up: a call is with the move
        assert plc53("A220", T[0], 240) == ([("CE", 0, 1)], [(270, L.LOTS)])                                  # flat spot: no stop, no adverse bar, 30-minute cap
        P[k]["spot"][316] = 19990.0; assert sig_a220([k])[0]["x"] == 316
        P[k]["spot"][316:343] = 20025.0 + np.arange(27); assert sig_a220([k])[0]["x"] == 342
        P[k]["spot"][312:] = 19990.0; T = sig_a220([k]); assert T[0]["legs"] == [("PE", 0, 1)] and T[0]["dirn"] == -1 and ap(T[0]["ds"], 20) and len(sig_a220([k], counter=True)) == 1
        P[k]["spot"][310:] = 20003.0; assert sig_a220([k]) == []                                             # no break by 14:49
        # ---- PCR. Yesterday's OI 1000 everywhere, dte 1 -> strikes 19950..20050. Today PE OI 2000, CE OI 1500: PCR = 3000 / 1500 = 2 -> call.
        # Calls 100 - 15n: OTM3 (20150) = 55, nearest 0.27% x 20000 = 54. That call trades 50 (minutes 0-49), 60 (50-104), 56 from 105:
        # VWAP(105) = (2500 + 3300 + 56) / 106 = 55.245 -> 1.4% away -> buy. Day low 50 = stop, target 56 + 24 = 80. 81 at minute 150 -> exit.
        kp = _syn("2021-09-05", flat, c100, exp="2021-09-07"); oi = lambda sd, off, j: 2000.0 if sd == "PE" else 1500.0
        px = lambda sd, off, j: ((50.0 if j < 50 else 60.0 if j < 105 else 56.0 if j < 150 else 81.0) if off == 3 else 100.0 - 15 * off) if sd == "CE" and off > 0 else 100.0
        k = _syn("2021-09-06", flat, px, oi, exp="2021-09-07"); syn += [kp, k]; ks = [kp, k]
        assert ap(pcr_val(P[k], P[kp], 105, "NIFTY"), 2.0) and pcr_strike(P[k], 104, "NIFTY", "CE") == 20150.0 and ap(_vwap(col(k, "CE", 3))[105], 5856 / 106)
        T = sig_pcr(ks); assert len(T) == 1 and T[0]["i"] == 105 and T[0]["legs"] == [("CE", 3, 1)] and T[0]["x"] == 150 and T[0]["K"] == 20150.0, T
        assert sig_pcr(ks, plain=True)[0]["x"] == XL and plc53("PCR", T[0], 200) == ([("CE", 3, 1)], [(XL, L.LOTS)])   # twin at 81: target 105 never, low 50 never
        col(k, "CE", 3)[120, :4] = 50.0; assert [(t["i"], t["x"]) for t in sig_pcr(ks)] == [(105, 120), (121, 150)]   # 50 <= the day low 50: stop; 56 at 121 is again within 3% of VWAP (55.3): second and last entry
        for q in P[k]["C"].values():
            if np.isfinite(q[0, 4]) and q[0, 4] == 2000.0: q[:, 4] = 1600.0
        assert ap(pcr_val(P[k], P[kp], 105, "NIFTY"), 1.2) and sig_pcr(ks) == []                              # 1800 / 1500 = 1.2: no-trade zone
        for q in P[k]["C"].values():
            if q[0, 4] == 1600.0: q[:, 4] = 900.0
        assert np.isnan(pcr_val(P[k], P[kp], 105, "NIFTY")) and sig_pcr(ks) == []                             # put OI fell: sum of put changes <= 0 -> no read
        for q in P[k]["C"].values():
            if q[0, 4] == 900.0: q[:, 4] = 1300.0
        T = sig_pcr(ks, plain=True); assert ap(pcr_val(P[k], P[kp], 105, "NIFTY"), 0.6) and T[0]["legs"][0][0] == "PE"   # 900 / 1500 = 0.6 -> put
        P[k]["exp"] = "2021-09-08"; assert sig_pcr(ks) == []; P[k]["exp"] = "2021-09-07"; P[k]["d0"] = 1; assert sig_pcr(ks) == []   # new series / expiry day
        # ---- OIC. Call OI: one wall at 20150 (1000 vs 100 100 200 300). Put OI: 19950 at 900 and 19900 at 1000 (two walls). Bullish: target
        # 20150 - 0.4% x 20000 = 20070, stop under 19950, sell the 19950 put, buy the 19850 put. Spot 20075 from minute 22 -> 5m close 24.
        oi = lambda sd, off, j: {("CE", 3): 1000.0, ("CE", 4): 200.0, ("CE", 5): 300.0, ("PE", -1): 900.0, ("PE", -2): 1000.0}.get((sd, off), 100.0)
        sp = flat.copy(); sp[22:] = 20075.0; k = _syn("2021-09-09", sp, c100, oi); syn.append(k); q = oic_pick(P[k], 14, "NIFTY")
        assert q["dirn"] == 1 and ap(q["tgt"], 20070) and q["stop"] == 19950.0 and q["Ks"] == ("PE", 19950.0, 19850.0)
        T = sig_oic([k]); assert len(T) == 1 and T[0]["legs"] == [("PE", -1, -1), ("PE", -3, 1)] and T[0]["x"] == 24, T
        assert plc53("OIC", T[0], 50) == ([("PE", -1, -1), ("PE", -3, 1)], [(54, L.LOTS)])
        P[k]["spot"][20:] = 19950.0; assert sig_oic([k])[0]["x"] == XL; P[k]["spot"][20:] = 19949.0; assert sig_oic([k])[0]["x"] == 24   # at the wall: no stop; through it: stop
        col(k, "PE", -1)[:, 4] = 800.0; assert oic_pick(P[k], 14, "NIFTY") is None                           # 800 < 0.85 x 1000: one put wall only
        col(k, "PE", -1)[:, 4] = 900.0; P[k]["spot"][14] = 20100.0; assert oic_pick(P[k], 14, "NIFTY") is None   # target 20069.6 is below spot
        oi2 = lambda sd, off, j: oi("PE" if sd == "CE" else "CE", -off, j); k = _syn("2021-09-10", flat, c100, oi2); syn.append(k); q = oic_pick(P[k], 14, "NIFTY")
        assert q["dirn"] == -1 and ap(q["tgt"], 19930) and q["stop"] == 20050.0 and q["Ks"] == ("CE", 20050.0, 20150.0)   # mirror
        # ---- ORS. Range of minutes 0..29 = 19990..20010. 3m close 20011 at minute 35 -> sell the ATM put; target = 100 - 0.065% x 20011 = 86.99:
        # put at 86 from minute 50 -> exit 50. 3m close 19989 at 62 -> sell the ATM call (edge 20010); 3m close 20012 at 80 -> its stop.
        sp = flat.copy(); sp[5] = 20010; sp[10] = 19990; sp[35:62] = 20011; sp[62:80] = 19989; sp[80:] = 20012
        k = _syn("2021-09-11", sp, lambda sd, off, j: 86.0 if sd == "PE" and off == 0 and j >= 50 else 100.0); syn.append(k); T = sig_ors([k])
        assert [(t["i"], t["legs"], t["x"], t["edge"]) for t in T] == [(35, [("PE", 0, -1)], 50, 19990.0), (62, [("CE", 0, -1)], 80, 20010.0)], T
        assert plc53("ORS", T[1], 100) == ([("CE", 0, -1)], [(101, L.LOTS)])                                  # twin at 100: the 3m close 20012 at 101 is through the edge
        col(k, "PE", 0)[:, :4] = 100.0; T = sig_ors([k]); assert [(t["i"], t["x"]) for t in T] == [(35, 62), (62, 80)]   # no target: the stop bar 62 is also the second signal
        P[k]["spot"][30:] = 20000.0; assert sig_ors([k]) == []
        # ---- BBH. Call 20000: flat 100 for 25 bars; bar 25 (100,100,96,96) HA close 98 open 100 red; bar 26 (96,96,92,92) HA close 94 open 99 red;
        # bar 27 (92,102,92,102) HA close 97 open 96.5 green, HA high 102. Band at 26: mean 99.6, sd 1.3565 -> 96.887 >= HA low 92: touch.
        # E = 102 + 0.8, SL = 92 - 0.8, R = 11.6 (<= 15.4), target 126. Bar 28 high 104 >= 102.8 -> decision 28. High 127 at 60 -> half out;
        # low 102 at 90 -> the runner out at cost.
        k = _syn("2021-09-12", flat, c100); syn.append(k); a = col(k, "CE", 0)
        a[25, :4] = [100, 100, 96, 96]; a[26, :4] = [96, 96, 92, 92]; a[27, :4] = [92, 102, 92, 102]; a[28, :4] = [102, 104, 101, 103]; a[29:, :4] = 103.0; a[60, 1] = 127.0; a[90, 2] = 102.0
        H, w0 = ha_bb(a); assert w0 == 0 and H[25, :4].tolist() == [100, 100, 96, 98] and H[26, :4].tolist() == [99, 99, 92, 94] and H[27, :4].tolist() == [96.5, 102, 92, 97]
        assert abs(H[26, 4] - (99.6 - 2 * 1.84 ** 0.5)) < 1e-9 and np.isnan(H[18, 4]) and ap(H[19, 4], 100)
        T = sig_bbh([k]); assert len(T) == 1 and T[0]["i"] == 28 and T[0]["legs"] == [("CE", 0, 1)] and T[0]["parts"] == [(60, 5), (90, 5)] and ap(T[0]["R"], 11.6) and T[0]["x"] == 90, T
        assert sig_bbh([k], full=True)[0]["parts"] == [(60, 5), (60, 5)] and sig_bbh([k], hold=15)[0]["parts"] == [(43, 5), (43, 5)]
        assert x_bbh(a, 28, 102.8, 11.6) == (60, 90) and plc53("BBH", T[0], 40) == ([("CE", 0, 1)], [(60, 5), (61, 5)])   # twin: E' 103, target 126.2 at 60, cost stop 103 at 61
        a[90, 2] = 103.0; assert sig_bbh([k])[0]["parts"] == [(60, 5), (XL, 5)]                               # the runner is never back at 102.8: held to 15:15
        a[40, 2] = 91.0; assert sig_bbh([k])[0]["parts"] == [(40, 5), (40, 5)]                                # 91 <= 91.2 before the target: all out
        a[60, 2] = 91.0; a[40, 2] = 103.0; assert sig_bbh([k])[0]["parts"] == [(60, 5), (60, 5)]              # stop and target in one bar: the stop wins
        a[28, 1] = 102.5; assert sig_bbh([k]) == []; a[28, 1] = 104.0                                         # bar 28 never trades 102.8: the order lapses
        P[k]["C"][("PE", 20000.0)][:] = a; assert sig_bbh([k]) == []                                          # both options signal on the same bar: no trade
        P[k]["C"][("PE", 20000.0)][:, :4] = 100.0; a[26, 2] = 80.0; assert sig_bbh([k]) == [] and len(sig_bbh([k], touch=False)) == 0   # SL 79.2, R 23.6 > 15.4: skip
        # no touch: 25 bars alternating 120 / 80 (band about 99.65 - 2 x 19 = 62; HA open cycles 93.3 / 106.7), dip (100,100,96,96), (96,96,94,94), then
        # (94,106,94,106): HA close 100 > HA open 98.67 green; every HA low of bars 24..27 (93.3, 96, 94, 94) is above the band. R = 106.8 - 93.2 = 13.6.
        k = _syn("2021-09-17", flat, c100); syn.append(k); a = col(k, "CE", 0); a[:25, :4] = np.where(np.arange(25) % 2, 80.0, 120.0)[:, None]
        a[25, :4] = [100, 100, 96, 96]; a[26, :4] = [96, 96, 94, 94]; a[27, :4] = [94, 106, 94, 106]; a[28, :4] = [106, 108, 105, 107]; a[29:, :4] = 107.0
        T = sig_bbh([k], touch=False); assert sig_bbh([k]) == [] and len(T) == 1 and T[0]["i"] == 28 and ap(T[0]["R"], 13.6) and T[0]["parts"] == [(XL, 5), (XL, 5)], T
        # warm-up: with yesterday's bars of the same contract the band exists from the first minute
        kp = _syn("2021-09-13", flat, c100, exp="2021-09-15"); k = _syn("2021-09-14", flat, c100, exp="2021-09-15"); syn += [kp, k]
        H, w0 = ha_bb(col(k, "CE", 0), col(kp, "CE", 0)); assert w0 == NB and ap(H[NB, 4], 100) and np.isnan(ha_bb(col(k, "CE", 0))[0][0, 4])
        # ---- pricing in two halves: long CE 100 -> 110 from minute 100; 5 lots out at 120, 5 lots at 200, against the cost functions by hand
        k = _syn("2021-09-16", flat, lambda sd, off, j: 100.0 if j < 100 else 110.0); syn.append(k); kc = k if L.COSTS == "dated" else None; q = L.qty("NIFTY", kc, 5)
        h1 = L.hs("NIFTY", 0, M0 + 51, 100.0); want = sum((110 - L.hs("NIFTY", 0, M0 + x + 1, 110.0) - 100 - h1) * q - S._cost(100 + h1, 110 - L.hs("NIFTY", 0, M0 + x + 1, 110.0), "NIFTY", 5, kc) for x in (120, 200))
        r = price53(k, 50, [("CE", 0, 1)], [(120, 5), (200, 5)]); assert ap(r[0], want) and not r[1] and r[2] == 10 * 650 and price53(k, 50, [("CE", 0, 1)], [(50, 10)]) is None
        r1 = price53(k, 50, [("CE", 0, 1)], [(120, 10)]); r0 = S.struct(k, 50, [("CE", 0, 1)], flat=M0 + 121); assert ap(r1[0], r0["pnl"])
        # ---- verdict rule (alpha 0.05 / 7) and the stats row
        r = dict(learn_n=100, test_n=40, forced_pct=2.0, learn_mean=500, learn_p=0.01, test_total=9000, test_p=0.004, test_q_pos="4/5", plac_p_test=0.01, plac_p_all=0.01)
        assert verdict53(r) == "PASS" and verdict53(dict(r, test_p=0.008)) == "FAIL" and verdict53(dict(r, plac_p_all=0.2)) == "FAIL" and verdict53(r, dict(learn_mean=1, test_mean=-1)) == "FAIL"
        assert verdict53(dict(r, forced_pct=11)) == "INCONCLUSIVE" and verdict53(dict(r, learn_n=29)) == "UNTESTABLE" and abs(ALPHA53 - 0.05 / 7) < 1e-12 and verdict(dict(r, test_p=0.008)) == "PASS"
        T = pd.DataFrame(dict(cell="X", day=["2024-06-04"] * 2 + ["2024-06-05"] * 38 + ["2026-10-20"] * 12, pnl=[1000.0] * 2 + [100.0] * 50, forced=False, gross=0.0, pl=[[0.0]] * 52))
        r = stats53("GSm", T); assert r["verdict"] == "CONTROL" and r["learn_ex10"] == 0 and r["learn_mean_xev"] == 100 and r["plac_p_learn"] == 0.0 and r["learn_n"] == 40
    finally:
        for k in syn: P.pop(k, None)
        S._EXT.clear()
    print(f"yt_lab selftest53 OK (COSTS={L.COSTS}): GS / PR / A220 / PCR / OIC / ORS / BBH signals and exits, Heikin Ashi + band, placebo twins, half-lot pricing, verdict rule")


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
