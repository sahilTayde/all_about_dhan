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


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
