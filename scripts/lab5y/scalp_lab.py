"""Scalp lab (registry E44+): 1-30 minute option scalps on the 5-year 1m panel. Paper research only; no orders, no broker calls.
Run (from scripts/lab5y):
  HO=2025-10-27 LAB_FULL=1 COSTS=dated ~/paper_extra_venv/bin/python scalp_lab.py <OUT=data/cache/lab5y_w10> hurdle|selftest|...
Reuses opt1y_lab (panel P, p75 half-spread table hs, dated charges x1.5, untraded-bar guard, 10 lots). Nothing here edits another lab.
Units, always both: PREMIUM points (Rs per point = units traded, 650 NIFTY / 200 SENSEX at 10 lots today) and INDEX points
(premium points / the option's measured delta)."""
import sys, numpy as np, pandas as pd
import opt1y_lab as L

P, STEP, M0, NB = L.P, L.STEP, L.M0, L.NB
HO = L.HO
TBN = ["09:15-09:30", "09:30-11:00", "11:00-14:00", "14:00-15:00", "15:00-15:30"]  # the spread table's time buckets (L.TB)
TBM = [5, 60, 200, 300, 350]  # one representative bar per bucket: 09:20, 10:15, 12:35, 14:15, 15:05


def study_hurdle():
    """Step 0: round-trip cost of ONE long option scalp (buy at open + half-spread, sell at open - half-spread, same price both ways, so
    it is pure friction) by index, expiry / other day, time of day and ATM / OTM1, on the TEST year (today's lots and rates).
    spread = 2 x p75 half-spread; charges = L.cost (x1.5 stress) / units. delta = median over days of the slope of 1m option change on
    1m spot change in the bucket (the option's real index sensitivity), used to restate the hurdle in index points."""
    rows = []
    for k in [k for k in L.ALLK if k[1] >= HO]:
        sym, p = k[0], P[k]; q = L.qty(sym, k if L.COSTS == "dated" else None); ds = np.diff(p["spot"])
        for tb, i in enumerate(TBM):
            for off, nm in ((0, "ATM"), (1, "OTM1")):
                for sd in ("CE", "PE"):
                    K = p["atm"][i] + (off if sd == "CE" else -off) * STEP[sym]; a = p["C"].get((sd, K))
                    if a is None or not np.isfinite(a[i, 0]) or L.stale(a, i): continue
                    px = a[i, 0]; h = L.hs(sym, p["d0"], M0 + i, px); ch = L.cost(px + h, px - h, sym, k if L.COSTS == "dated" else None) / q
                    lo, hi = max(0, i - 15), min(NB - 1, i + 15); dc = np.diff(a[lo:hi + 1, 3]); x = ds[lo:hi]
                    ok = np.isfinite(dc) & np.isfinite(x); dl = abs(np.polyfit(x[ok], dc[ok], 1)[0]) if ok.sum() > 10 and x[ok].std() > 0 else np.nan
                    rows.append(dict(sym=sym, d0=p["d0"], tb=tb, strike=nm, prem=px, spread=2 * h, charges=ch, delta=dl, q=q))
    R = pd.DataFrame(rows); g = R.groupby(["sym", "d0", "strike", "tb"])
    T = pd.DataFrame(dict(n=g.size(), premium=g.prem.median(), spread_rt=g.spread.median(), charges_rt=g.charges.median(), delta=g.delta.median()))
    T["hurdle_prem"] = T.spread_rt + T.charges_rt; T["hurdle_idx"] = T.hurdle_prem / T.delta
    T["hurdle_rs"] = T.hurdle_prem * g.q.median(); T["dead_below_prem"] = 2 * T.hurdle_prem
    T = T.reset_index(); T["tb"] = T.tb.map(dict(enumerate(TBN))); T["d0"] = T.d0.map({0: "other", 1: "expiry"})
    pd.set_option("display.width", 250); print(f"cost hurdle, TEST year (>= {HO}), COSTS={L.COSTS}, charges x{L.CM}, {L.HSCOL} half-spread, 10 lots")
    print(T.round(2).to_string(index=False)); T.round(3).to_csv(f"{L.OUT}/scalp_hurdle.csv", index=False)


def study_costsplit():
    """Founder's cost check (2026-11-16): round-trip cost PER POINT-UNIT of one long option, split into spread / STT / exchange / brokerage /
    GST (+ stamp, SEBI), at 5 and 10 lots, for ITM4..ATM..OTM1, by time of day, TEST year, real rates (x1.0; the tests then stress charges
    x1.5). All in premium points per unit. Only brokerage (Rs 20 x 2 orders) is fixed per order, so only it shrinks with more lots."""
    rows = []; lab = {-4: "ITM4", -3: "ITM3", -2: "ITM2", 0: "ATM", 1: "OTM1"}
    for k in [k for k in L.ALLK if k[1] >= HO and not P[k]["d0"]]:
        sym, p = k[0], P[k]; q10 = L.qty(sym, _kc(k)); tx = TXR[DIX[k]]; stt = STT[DIX[k]]
        for tb, i in enumerate(TBM):
            for off, nm in lab.items():
                for sd in ("CE", "PE"):
                    K = p["atm"][i] + (off if sd == "CE" else -off) * STEP[sym]; a = p["C"].get((sd, K))
                    if a is None or not np.isfinite(a[i, 0]): continue
                    px = a[i, 0]; h = L.hs(sym, 0, M0 + i, px); b, s_ = px + h, px - h; win = a[max(0, i - 15):i + 15, 6]
                    r = dict(sym=sym, tb=tb, strike=nm, prem=px, untraded=float((win == 0).mean()), spread=2 * h, stt=stt * s_, exch=tx * (b + s_),
                             other=1e-6 * (b + s_) + 0.00003 * b)
                    for lots in (5, 10):
                        q = q10 * lots / 10; r[f"brok{lots}"] = 40 / q; r[f"gst{lots}"] = 0.18 * (40 / q + tx * (b + s_) + 1e-6 * (b + s_))
                    rows.append(r)
    R = pd.DataFrame(rows); T = R.groupby(["sym", "strike", "tb"]).median().reset_index()
    for lots in (5, 10):
        T[f"total{lots}"] = T.spread + T.stt + T.exch + T.other + T[f"brok{lots}"] + T[f"gst{lots}"]
        T[f"pct15_{lots}"] = 100 * T[f"total{lots}"] / 15; T[f"pct20_{lots}"] = 100 * T[f"total{lots}"] / 20
    T["tb"] = T.tb.map(dict(enumerate(TBN))); T["untraded_pct"] = 100 * R.groupby(["sym", "strike", "tb"]).untraded.mean().values
    pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)
    print(f"round-trip cost per unit in premium points, non-expiry days of the TEST year, real rates (x1.0), {L.HSCOL} half-spread")
    print(T.drop(columns="untraded").round(2).to_string(index=False)); T.round(3).to_csv(f"{L.OUT}/scalp_costsplit.csv", index=False)


# ================================================================ E44 engine: a dense pool of every possible long-option entry
DAYK = L.ALLK; ND = len(DAYK); DIX = {k: n for n, k in enumerate(DAYK)}; NE, NH = 332, 31   # entry bars e < 332 (last decision 14:45), 31 closes
SYMI = np.array([0 if k[0] == "NIFTY" else 1 for k in DAYK]); D0 = np.array([P[k]["d0"] for k in DAYK]); ISTEST = np.array([k[1] >= HO for k in DAYK])
SPOT = np.array([P[k]["spot"] for k in DAYK])
_kc = lambda k: k if L.COSTS == "dated" else None
Q = np.array([L.qty(k[0], _kc(k)) for k in DAYK], float)
TXR = np.array([L._at(L.TXN_D[k[0]], k[1]) if L.COSTS == "dated" else L.TXN[k[0]] for k in DAYK])
STT = np.array([L._at(L.STT_SELL, k[1]) if L.COSTS == "dated" else 0.0015 for k in DAYK])
HSA = np.array([[L.HS[(s, d)] for d in (0, 1)] for s in ("NIFTY", "SENSEX")])  # [sym, d0, time bucket, premium bucket]
INST = [("CE", 0), ("PE", 0), ("CE", 1), ("PE", -1)]  # ATM CE, ATM PE, OTM1 CE, OTM1 PE
MENU = [(t, s, h) for t in (5, 10, 15, 20, 30, 50, 100) for s in (5, 10, 15, 20, 30) for h in (3, 5, 10, 15, 30)]
ADAPT = [(5, 5, 3), (10, 10, 10), (20, 15, 15), (50, 30, 30)]


def hsv(d, m, p):
    """vector form of L.hs: p75 half-spread for day index d, minute m, premium p."""
    return HSA[SYMI[d], D0[d], np.searchsorted(L.TB, m, "right"), np.searchsorted(L.PB, p, "right")]


def chg(d, b, s, fc=1.0, lf=1.0):
    """vector form of L.cost (round-trip charges x CM for one leg bought at b, sold at s, at the day's units and dated rates).
    lf = lots / 10 (E45: 5 lots -> 0.5); the Rs 40 brokerage does not scale."""
    bt, st = b * Q[d] * lf, s * Q[d] * lf; x = 40 + TXR[d] * (bt + st) + 1e-6 * (bt + st)
    return fc * L.CM * (x + 0.18 * x + 0.00003 * bt + STT[d] * st)


_POOL = {}
def pool():
    """ENT[d, e, inst] = open of bar e of the strike that is ATM / OTM1 at bar e-1, NaN unless that option traded in bars e-1 and e.
    CP[d, e, inst, h] = its 1m close at bar e+h (decisions). XP[.., h] = the open of the first TRADED bar at or after e+h+1 (exit fill)."""
    if not _POOL:
        ENT = np.full((ND, NE, 4), np.nan, np.float32); CP = np.full((ND, NE, 4, NH), np.nan, np.float32); XP = CP.copy()
        sw = np.lib.stride_tricks.sliding_window_view
        for d, k in enumerate(DAYK):
            p = P[k]; st = STEP[k[0]]; atm = p["atm"]
            for n, (sd, off) in enumerate(INST):
                Ke = atm[:NE - 1] + off * st  # strike for entry bar e = 1..NE-1 (decision bar e-1)
                for K in np.unique(Ke[np.isfinite(Ke)]):
                    a = p["C"].get((sd, K))
                    if a is None: continue
                    o, c, v = a[:, 0], a[:, 3], a[:, 6]; tr = np.isfinite(o) & (v > 0)
                    nto = pd.Series(np.where(tr, o, np.nan)).bfill().values
                    cw = sw(np.concatenate([c, np.full(NH, np.nan)]), NH); xw = sw(np.concatenate([nto[1:], np.full(NH + 1, np.nan)]), NH)
                    e = np.flatnonzero(Ke == K) + 1; ok = tr[e] & tr[e - 1]
                    ENT[d, e, n] = np.where(ok, o[e], np.nan); CP[d, e, n] = cw[e]; XP[d, e, n] = xw[e]
        _POOL.update(ENT=ENT, CP=CP, XP=XP)
    return _POOL


KIND = {"ATM": 0, "OTM1": 1, "LSTR": 2, "SSTR": 3}
def price(d, e, kind, dirn, cells=MENU, fs=1.0, fc=1.0):
    """Price trades (arrays: day index, entry bar, kind, direction +1/-1) on every exit cell. Returns dict of (N, len(cells)) arrays:
    pnl (Rs net), pts (premium points after spread, before charges), xb (exit fill bar), and ok (N,) entry valid."""
    Z = pool(); d, e, kind, dirn = (np.asarray(x) for x in (d, e, kind, dirn)); N = len(d); m_e = M0 + e
    legs = [np.where(kind >= 2, 0, kind * 2 + (dirn < 0)), np.where(kind >= 2, 1, -1)]; sgn = np.where(kind == 3, -1.0, 1.0)
    entP = np.zeros(N); path = np.zeros((N, NH)); raw = []; ents = []
    for lg in legs:
        on = lg >= 0; l = np.where(on, lg, 0); o = Z["ENT"][d, e, l].astype(float); h = fs * hsv(d, m_e, np.nan_to_num(o, nan=1.0))
        en = np.where(on, o + sgn * h, 0.0); ents.append((on, en)); entP += en; path += np.where(on[:, None], Z["CP"][d, e, l], 0.0)
        raw.append(np.where(on[:, None], Z["XP"][d, e, l], 0.0))
    ok = np.isfinite(entP); gain = sgn[:, None] * (path - entP[:, None]); C = len(cells)
    pnl = np.full((N, C), np.nan, np.float32); pts = pnl.copy(); xb = np.zeros((N, C), np.int16); r = np.arange(N)
    for ci, (T, S, H) in enumerate(cells):
        hit = (gain >= T) | (gain <= -S); hit[:, H - 1:] = True; jd = hit.argmax(1); exP = np.zeros(N); cost = np.zeros(N)
        for (on, en), rw in zip(ents, raw):
            x = np.nan_to_num(rw[r, jd], nan=0.05); h = fs * hsv(d, m_e + jd + 1, np.maximum(x, 0.05))
            f = np.where(sgn > 0, np.maximum(x - h, 0.05), x + h); f = np.where(on, f, 0.0); exP += f
            cost += np.where(on, np.where(sgn > 0, chg(d, en, f, fc), chg(d, f, en, fc)), 0.0)
        g = sgn * (exP - entP); pts[:, ci] = g; pnl[:, ci] = g * Q[d] - cost; xb[:, ci] = e + jd + 1
    return dict(pnl=pnl, pts=pts, xb=xb, ok=ok)


def greedy(d, e, xb, ok, cap=20):
    """one position at a time, per cell: a trade is taken only if its entry bar is at or after the previous taken trade's exit bar; cap/day.
    Trades must be sorted by (d, e). Returns take (N, C) bool."""
    take = np.zeros(xb.shape, bool); free = np.zeros(xb.shape[1]); cnt = np.zeros(xb.shape[1]); last = -1
    for n in range(len(d)):
        if d[n] != last: free[:] = 0; cnt[:] = 0; last = d[n]
        if not ok[n]: continue
        t = (e[n] >= free) & (cnt < cap); take[n] = t; free = np.where(t, xb[n], free); cnt += t
    return take


# ---------------------------------------------------------------- features (every array index j uses bars <= j only)
def _roll(x, n, f): return getattr(pd.Series(x).rolling(n, min_periods=n), f)().values
def _z(x, n=60):  # z of x_i against x over bars i-n..i-1
    s = pd.Series(x).shift(1).rolling(n, min_periods=n); return (x - s.mean().values) / s.std().values


def day_feats(p, sym, prev=None):
    """p: panel day dict (spot, atm, C). prev: dict(close, iva, hi, lo, orw=[prior days' OR widths]) or None."""
    S = p["spot"]; atm = p["atm"]; st = STEP[sym]; Ks = np.array(sorted({K for _, K in p["C"]})); nK = len(Ks)
    M = {sd: np.full((7, nK, NB), np.nan) for sd in ("CE", "PE")}
    for (sd, K), a in p["C"].items(): M[sd][:, np.searchsorted(Ks, K)] = a.T  # o h l c oi iv vol
    ai = np.searchsorted(Ks, atm); aok = np.isfinite(atm) & (ai < nK) & (Ks[np.minimum(ai, nK - 1)] == atm); ai = np.where(aok, ai, 0); b = np.arange(NB)
    def at(sd, col, off=0):
        j = ai + off; g = (j >= 0) & (j < nK) & aok; return np.where(g, M[sd][col][np.clip(j, 0, nK - 1), b], np.nan)
    V = np.zeros(NB); Dv = np.zeros(NB)
    for off in range(-2, 3):
        for sd, sg in (("CE", 1), ("PE", -1)):
            v = np.nan_to_num(at(sd, 6, off)); V += v; Dv += sg * v * np.nan_to_num(np.sign(at(sd, 3, off) - at(sd, 0, off)))
    c, q = at("CE", 3), at("PE", 3); both = (at("CE", 6) > 0) & (at("PE", 6) > 0) & np.isfinite(c) & np.isfinite(q)
    F = pd.Series(np.where(both, atm + c - q, np.nan)).ffill().values
    fv = np.nan_to_num(F) * V; vw = np.cumsum(np.where(np.isfinite(F), fv, 0)) / np.maximum(np.cumsum(np.where(np.isfinite(F), V, 0)), 1e-9)
    dS = np.diff(S, prepend=np.nan); s1 = pd.Series(dS).shift(1).rolling(30, min_periods=30).std().values
    oi = np.nan_to_num(M["CE"][4]) + np.nan_to_num(M["PE"][4]); w10 = np.abs(np.arange(nK)[:, None] - ai[None, :]) <= 10
    kst = Ks[np.where(w10, oi, -1).argmax(0)]
    return dict(S=S, dS=dS, s1=s1, V=V, D=Dv, F=F, VW=vw, ST=c + q, IV=(at("CE", 5) + at("PE", 5)) / 2, kst=kst, st=st, d0=p["d0"], prev=prev,
                oiC=at("CE", 4), oiC1=at("CE", 4, 1), oiP=at("PE", 4), oiP1=at("PE", 4, -1), M=M, ai=ai, aok=aok, nK=nK)


def _oi_side(f, i, up):
    """summed OI of the ATM and OTM1 options on the broken side, strikes fixed by ATM at bar i, at bars i and i-5."""
    M = f["M"]["CE" if up else "PE"][4]; j = f["ai"][i]; j1 = j + (1 if up else -1)
    if not f["aok"][i] or not 0 <= j1 < f["nK"]: return np.nan, np.nan
    return M[j, i] + M[j1, i], M[j, i - 5] + M[j1, i - 5]


def _cool(idx, dirs, cd, mx):
    out = []; nxt = -1
    for i, s in zip(idx, dirs):
        if i >= nxt and len(out) < mx and s != 0: out.append((int(i), int(s))); nxt = i + cd
    return out


def signals(f):
    """the 12 frozen E44 signals for one sym-day -> {name: [(decision bar i, direction)]}."""
    S, s1, V, d0 = f["S"], f["s1"], f["V"], f["d0"]; out = {}; pv = f["prev"]; i_ = np.arange(NB)
    with np.errstate(invalid="ignore", divide="ignore"):
        hi, lo = S[:5].max(), S[:5].min(); w = hi - lo; brk = np.where(S >= hi + 0.25 * w, 1, np.where(S <= lo - 0.25 * w, -1, 0)) if w > 0 else np.zeros(NB, int)
        # (a) OD-Go
        a = []
        if w > 0 and pv and len(pv["orw"]) >= 20 and w >= np.median(pv["orw"][-20:]):
            m = (brk != 0) & (V >= 1.5 * V[:5].mean()) & (i_ >= 5) & (i_ <= 30); a = _cool(i_[m], brk[m], NB, 1)
        out["a_odgo"] = a
        # (b) OD-Fail: breakout at b, then within 3 bars a close back inside by >= 0.25 w
        bl = []
        if w > 0:
            for i in range(6, 46):
                for sgn in (1, -1):
                    if (brk[max(5, i - 3):i] == sgn).any() and ((S[i] <= hi - 0.25 * w) if sgn > 0 else (S[i] >= lo + 0.25 * w)): bl.append((i, -sgn))
                if bl: break
        out["b_odfail"] = bl[:1]
        # (c) VWAP-Reclaim
        F, VW = f["F"], f["VW"]; medV = pd.Series(V).shift(1).rolling(30, min_periods=30).median().values
        below = (F < VW).astype(int); above = (F > VW).astype(int)
        run = lambda x: pd.Series(x).groupby((pd.Series(x) == 0).cumsum()).cumsum().shift(1).fillna(0).values  # run length ending at i-1
        up = (run(below) >= 20) & (F - VW >= 0.5 * s1) & (V >= 1.5 * medV); dn = (run(above) >= 20) & (VW - F >= 0.5 * s1) & (V >= 1.5 * medV)
        m = (up | dn) & (i_ >= 45) & (i_ <= 330) & (d0 == 0); out["c_vwap"] = _cool(i_[m], np.where(up, 1, -1)[m], 15, 4)
        # (d) Ignition
        s = pd.Series(s1).shift(3).values; r3 = S - pd.Series(S).shift(3).values
        rng = pd.Series(S).shift(4).rolling(30, min_periods=30); rg = rng.max().values - rng.min().values
        m = (np.abs(r3) >= 2.5 * s * np.sqrt(3)) & (V >= 3 * medV) & (rg <= 8 * s) & (i_ >= 30) & (i_ <= 330)
        out["d_ignite"] = _cool(i_[m], np.sign(r3)[m], 15, 5)
        # (e) Stretch-Fade
        r5 = S - pd.Series(S).shift(5).values; ext = np.where(r5 > 0, S >= _roll(S, 60, "max"), S <= _roll(S, 60, "min"))
        m = (np.abs(r5) >= 4 * s1 * np.sqrt(5)) & ext & (V < np.roll(V, 1)) & (i_ >= 45) & (i_ <= 330) & (d0 == 0)
        out["e_fade"] = _cool(i_[m], -np.sign(r5)[m], 20, 3)
        # (f) Unpin-Break (expiry day)
        fl = []
        if d0:
            for i in range(255, 331):
                K = f["kst"][i]; near = (np.abs(S[i - 45:i] - K) <= 0.0015 * K).sum()
                if near >= 30 and abs(S[i] - K) >= 0.35 * f["st"]: fl.append((i, np.sign(S[i] - K)))
        out["f_unpin"] = _cool([x[0] for x in fl], [x[1] for x in fl], 15, 3)
        # (g) Late-Gamma-Straddle (expiry day)
        s60 = pd.Series(f["dS"]).rolling(60, min_periods=60).std().values
        m = (f["ST"] <= 0.64 * s60 * np.sqrt(np.maximum(374 - i_, 1))) & (i_ >= 285) & (i_ <= 330) & (d0 == 1)
        out["g_lategamma"] = _cool(i_[m], np.ones(m.sum()), 20, 2)
        # (h) IV-Pop-Lead
        IV, ST = f["IV"], f["ST"]; dv = IV - pd.Series(IV).shift(3).values
        m = (_z(dv) >= 2.5) & (np.abs(r3) < s1 * np.sqrt(3)) & (ST > pd.Series(ST).shift(3).values) & (i_ >= 30) & (i_ <= 330) & (d0 == 0)
        out["h_ivpop"] = _cool(i_[m], np.ones(m.sum()), 20, 3)
        # (i) Open-Crush (short straddle at the 09:17 open)
        out["i_crush"] = [(1, 1)] if (pv and d0 == 0 and abs(S[0] / pv["close"] - 1) < 0.003 and IV[1] >= pv["iva"]) else []
        # (j) Basis-Lead
        bs = F - S; db = bs - pd.Series(bs).shift(2).values; z = _z(db); r2 = S - pd.Series(S).shift(2).values
        m = (np.abs(z) >= 2.5) & (np.abs(r2) < s1 * np.sqrt(2)) & (i_ >= 15) & (i_ <= 330); out["j_basis"] = _cool(i_[m], np.sign(db)[m], 10, 6)
        # (k) Flow-Tilt
        D5 = pd.Series(f["D"]).rolling(5, min_periods=5).sum().values; z = _z(D5)
        m = (np.abs(z) >= 2.5) & (np.abs(r5) < 1.5 * s1 * np.sqrt(5)) & (i_ >= 30) & (i_ <= 330); out["k_flow"] = _cool(i_[m], np.sign(D5)[m], 15, 5)
        # (l) PDH/PDL-Cover
        ll = []
        if pv:
            ins = (S <= pv["hi"]) & (S >= pv["lo"]); in30 = pd.Series(ins.astype(float)).shift(1).rolling(30, min_periods=30).min().values == 1
            for up, lvl in ((True, pv["hi"]), (False, pv["lo"])):
                cnd = ((S >= lvl * 1.0005) if up else (S <= lvl * 0.9995)) & in30 & (i_ >= 30) & (i_ <= 330)
                for i in i_[cnd]:
                    o1, o0 = _oi_side(f, i, up)
                    if np.isfinite(o1) and o0 > 0 and o1 / o0 - 1 <= -0.01: ll.append((int(i), 1 if up else -1)); break
        out["l_pdhl"] = sorted(ll)
    return out


SIGK = dict(a_odgo="ATM", b_odfail="ATM", c_vwap="ATM", d_ignite="OTM1", e_fade="ATM", f_unpin="OTM1", g_lategamma="LSTR", h_ivpop="LSTR",
            i_crush="SSTR", j_basis="ATM", k_flow="ATM", l_pdhl="ATM")


def _prev_update(pv, f):
    S = f["S"]; orw = (pv["orw"] if pv else []) + [S[:5].max() - S[:5].min()]
    return dict(close=S[374], iva=f["IV"][370], hi=np.nanmax(S), lo=np.nanmin(S), orw=orw)


def all_signals():
    """every signal on every sym-day -> DataFrame(sig, d, i, dirn) + S1 (ND, NB) s1 array for the placebo terciles."""
    rows = []; S1 = np.full((ND, NB), np.nan); prev = {}
    for d, k in enumerate(DAYK):
        f = day_feats(P[k], k[0], prev.get(k[0])); S1[d] = f["s1"]
        for nm, lst in signals(f).items(): rows += [(nm, d, i, s) for i, s in lst]
        prev[k[0]] = _prev_update(prev.get(k[0]), f)
    return pd.DataFrame(rows, columns=["sig", "d", "i", "dirn"]), S1


def study_lookahead(n_days=24, seed=5):
    """look-ahead scan (honest_stats.lookahead idea, on the WHOLE signal chain): scramble every bar after index i (spot, every option
    column, and the ATM strike), recompute features + signals, and require every signal with decision bar <= i to be unchanged."""
    rg = np.random.default_rng(seed); ks = [DAYK[j] for j in rg.choice(ND, n_days, replace=False)]; ks += [k for k in DAYK if P[k]["d0"]][-6:]; bad = 0; n = 0
    pv = dict(close=1.0, iva=0.0, hi=np.inf, lo=-np.inf, orw=[0.0] * 20)
    for k in ks:
        p = P[k]; pv_k = dict(pv, close=p["spot"][0], hi=np.nanpercentile(p["spot"], 80), lo=np.nanpercentile(p["spot"], 20))
        base = signals(day_feats(p, k[0], pv_k))
        for i in (8, 20, 47, 90, 150, 222, 290, 320):
            q = dict(p, spot=p["spot"].copy(), atm=p["atm"].copy(), C={kk: a.copy() for kk, a in p["C"].items()})
            m = NB - i - 1; q["spot"][i + 1:] *= rg.uniform(0.97, 1.03, m); q["atm"][i + 1:] = p["atm"][i] + 2 * STEP[k[0]]
            for a in q["C"].values(): a[i + 1:] *= rg.uniform(0.5, 1.5, (m, 7))
            got = signals(day_feats(q, k[0], pv_k))
            for nm in base:
                n += 1; x, y = [t for t in base[nm] if t[0] <= i], [t for t in got[nm] if t[0] <= i]
                if x != y: bad += 1; print("LOOK-AHEAD", k, nm, i, x[-2:], y[-2:])
    nsig = sum(len(v) for v in base.values())
    print(f"look-ahead scan: {n} (signal, day, cut) checks on {len(ks)} sym-days, {bad} leaks"); assert bad == 0
    # the scanner must catch a planted leak: a feature that peeks one bar ahead
    f = day_feats(P[ks[0]], ks[0][0], pv); leak = lambda p_: np.roll(day_feats(p_, ks[0][0], pv)["S"], -1)[100]
    q = dict(P[ks[0]], spot=P[ks[0]]["spot"].copy()); q["spot"][101:] *= 1.01; assert leak(q) != leak(P[ks[0]])


# ---------------------------------------------------------------- statistics
import honest_stats as HST
def _daily(d, pnl, days):
    x = np.zeros(len(days)); pos = np.searchsorted(days, d); np.add.at(x, pos, pnl); return x
def _t(x): return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)) + 1e-12)
def _pboot(x, B=4000, seed=7):
    I = HST._stat_boot_idx(len(x), B, 0.2, np.random.default_rng(seed)); return float((x[I].mean(1) <= 0).mean())
def _maxdd(x): c = np.cumsum(x); return float((np.maximum.accumulate(np.maximum(c, 0)) - c).max())


def _rc(X, j, B=1000, seed=7):
    """White reality check for column j of X (days, cells): P(max over cells of the centred bootstrap t >= t_j)."""
    n = len(X); mu = X.mean(0); sd = X.std(0, ddof=1) + 1e-12; t = np.sqrt(n) * mu / sd; I = HST._stat_boot_idx(n, B, 0.2, np.random.default_rng(seed))
    mx = np.array([(np.sqrt(n) * (X[I[b]].mean(0) - mu) / sd).max() for b in range(B)]); return float((mx >= t[j]).mean())


def _slot(S1):
    """placebo strata per (day, bar): 30-minute slot x s1 tercile (cuts from LEARN days, per index)."""
    T = np.full((ND, NB), -1, np.int8)
    for s in (0, 1):
        lm = (SYMI == s) & ~ISTEST; c = np.nanquantile(S1[lm], [1 / 3, 2 / 3]); dm = SYMI == s
        T[dm] = np.where(np.isfinite(S1[dm]), np.searchsorted(c, S1[dm]), -1)
    return T


def _placebo(d, i, kind, cell, TER, runs=200, seed=3):
    """totals of `runs` random-entry draws: each real trade is replaced by a random bar on a random day of the same index, split,
    expiry flag, 30-minute slot and s1 tercile, with a random side; same cell, same one-at-a-time rule."""
    rg = np.random.default_rng(seed); key = lambda dd, ii: ((SYMI[dd] * 2 + ISTEST[dd]) * 2 + D0[dd]) * 400 + (ii // 30) * 4 + TER[dd, ii] + 1
    kd, ki = np.meshgrid(np.arange(ND), np.arange(1, NE - 1), indexing="ij"); kk = key(kd, ki).ravel(); o = np.argsort(kk, kind="stable")
    ks = kk[o]; kd, ki = kd.ravel()[o], ki.ravel()[o]; mine = key(d, i); lo = np.searchsorted(ks, mine, "left"); hi = np.searchsorted(ks, mine, "right")
    tot = np.zeros(runs)
    for r in range(runs):
        j = lo + (rg.random(len(d)) * (hi - lo)).astype(int); dd, ii = kd[j], ki[j]; srt = np.lexsort((ii, dd)); dd, ii = dd[srt], ii[srt]
        R = price(dd, ii + 1, kind[srt], rg.choice([-1, 1], len(dd)), [cell]); tk = greedy(dd, ii + 1, R["xb"], R["ok"])[:, 0]
        tot[r] = R["pnl"][tk, 0].sum()
    return tot


def _row(name, sym, split, d, e, kind, dirn, cell, days, pl=None, extra=None):
    """one report row for trades already filtered to (sym, split), sorted by (d, e). pl = placebo totals."""
    R = price(d, e, kind, dirn, [cell]); tk = greedy(d, e, R["xb"], R["ok"])[:, 0]; pnl = R["pnl"][tk, 0].astype(float); dd = d[tk]
    x = _daily(dd, pnl, days); R2 = price(d, e, kind, dirn, [cell], fs=2.0, fc=2.0); tk2 = greedy(d, e, R2["xb"], R2["ok"])[:, 0]
    xb = R["xb"][tk, 0]; idx = dirn[tk] * (SPOT[dd, np.minimum(xb, NB - 1) - 1] - SPOT[dd, e[tk] - 1]); idx = np.where(kind[tk] >= 2, np.nan, idx)
    qn = np.array_split(np.arange(len(days)), 4); qp = [x[q].sum() for q in qn]
    return dict(strategy=name, sym=sym, split=split, cell="/".join(map(str, cell)), trades=int(tk.sum()), per_day=tk.sum() / max(len(days), 1),
                win=float((pnl > 0).mean()) if len(pnl) else np.nan, pts_prem=float(R["pts"][tk, 0].mean()) if len(pnl) else np.nan,
                pts_idx=float(np.nanmean(idx)) if len(pnl) and np.isfinite(idx).any() else np.nan, net=float(pnl.sum()), p=_pboot(x) if len(pnl) else np.nan,
                maxdd=_maxdd(x), net_2x=float(R2["pnl"][tk2, 0].sum()), q_pos=int(sum(v > 0 for v in qp)),
                p_plac=float(((pl >= pnl.sum()).sum() + 1) / (len(pl) + 1)) if pl is not None else np.nan, plac_mean=float(pl.mean()) if pl is not None else np.nan,
                **(extra or {}))


def study_e44():
    """E44: frozen in the registry before pricing. LEARN picks ONE exit cell per signal x index; TEST is scored once."""
    import pickle, os
    cache = f"{L.OUT}/scalp_e44_sigs.pkl"
    if os.path.exists(cache): G, S1 = pickle.load(open(cache, "rb"))
    else: G, S1 = all_signals(); pickle.dump((G, S1), open(cache, "wb"))
    TER = _slot(S1); G = G.sort_values(["d", "i"]).reset_index(drop=True); rows = []; NT = 26; alpha = 0.05 / NT
    print(f"E44: {len(G)} signals on {ND} sym-days; LEARN < {HO} <= TEST; COSTS={L.COSTS}; alpha {alpha:.4f}", flush=True)
    for s, sym in enumerate(("NIFTY", "SENSEX")):
        dl = np.flatnonzero((SYMI == s) & ~ISTEST); dt = np.flatnonzero((SYMI == s) & ISTEST); pooled = []
        for nm, kn in SIGK.items():
            g = G[(G.sig == nm) & (SYMI[G.d.values] == s)]; d, e, dirn = g.d.values, g.i.values + 1, g.dirn.values; kind = np.full(len(g), KIND[kn])
            lm = ~ISTEST[d]
            if kn in ("ATM", "OTM1"): pooled.append((d, e, kind, dirn))
            R = price(d[lm], e[lm], kind[lm], dirn[lm]); tk = greedy(d[lm], e[lm], R["xb"], R["ok"]); n = tk.sum(0)
            if n.max() < 100:
                rows.append(dict(strategy=nm, sym=sym, split="LEARN", trades=int(n.max()), verdict="TOO FEW (< 100 LEARN trades)")); continue
            X = np.stack([_daily(d[lm][tk[:, c]], R["pnl"][tk[:, c], c].astype(float), dl) for c in range(len(MENU))], 1)
            t = np.where(n >= 100, X.mean(0) / (X.std(0, ddof=1) / np.sqrt(len(dl)) + 1e-12), -np.inf); j = int(t.argmax()); cell = MENU[j]
            ex = dict(rc_p=_rc(X, j), cells_pos=int((X.sum(0) > 0).sum()), best_net=float(X.sum(0).max()), med_net=float(np.median(X.sum(0))))
            rl = _row(nm, sym, "LEARN", d[lm], e[lm], kind[lm], dirn[lm], cell, dl, extra=ex)
            pl = _placebo(d[~lm], e[~lm] - 1, kind[~lm], cell, TER); rt = _row(nm, sym, "TEST", d[~lm], e[~lm], kind[~lm], dirn[~lm], cell, dt, pl)
            ok = (rt["net"] > 0 and rl["net"] > 0 and rt["p"] < alpha and rt["p_plac"] < 0.05 and rt["net_2x"] > 0 and rt["q_pos"] >= 3)
            rt["verdict"] = "PASS" if ok else "FAIL"; rl["verdict"] = "-"; rows += [rl, rt]; print(nm, sym, cell, f"LEARN {rl['net']:,.0f} TEST {rt['net']:,.0f}", flush=True)
        # adaptive table: pooled long single-leg signals
        d, e, kind, dirn = (np.concatenate(x) for x in zip(*pooled)); o = np.lexsort((e, d)); d, e, kind, dirn = d[o], e[o], kind[o], dirn[o]
        _, u = np.unique(np.stack([d, e, kind, dirn]), axis=1, return_index=True); u.sort(); d, e, kind, dirn = d[u], e[u], kind[u], dirn[u]
        R = price(d, e, kind, dirn, ADAPT); Z = pool(); inst = kind * 2 + (dirn < 0); prem = Z["ENT"][d, e, inst]
        bk = (D0[d] * 3 + np.maximum(TER[d, e - 1], 0)) * 3 + np.searchsorted([30, 100], np.nan_to_num(prem, nan=50)); lm = ~ISTEST[d] & R["ok"]
        half = np.sort(d[lm])[lm.sum() // 2]; g0 = int(np.nanmean(R["pnl"][lm], 0).argmax()); choice = np.full(18, g0)
        for b_ in range(18):
            mb = lm & (bk == b_)
            if mb.sum() < 200: continue
            best = int(np.nanmean(R["pnl"][mb], 0).argmax())
            if best == g0: continue
            lead = []
            for hm in (mb & (d < half), mb & (d >= half)):
                df = (R["pnl"][hm, best] - R["pnl"][hm, g0]).astype(float); lead.append(len(df) > 1 and df.mean() > df.std(ddof=1) / np.sqrt(len(df)))
            if all(lead): choice[b_] = best
        ch = choice[bk]; r = np.arange(len(d))
        for split, m_, days in (("LEARN", ~ISTEST[d], dl), ("TEST", ISTEST[d], dt)):
            xb = R["xb"][r, ch][:, None]; tk = greedy(d[m_], e[m_], xb[m_], R["ok"][m_])[:, 0]; pnl = R["pnl"][r, ch][m_][tk].astype(float); x = _daily(d[m_][tk], pnl, days)
            qp = [x[q].sum() for q in np.array_split(np.arange(len(days)), 4)]
            rows.append(dict(strategy="adaptive_table", sym=sym, split=split, cell=f"default {ADAPT[g0]}, {int((choice != g0).sum())} overrides", trades=int(tk.sum()),
                             per_day=tk.sum() / len(days), win=float((pnl > 0).mean()), pts_prem=float(R["pts"][r, ch][m_][tk].mean()), net=float(pnl.sum()),
                             p=_pboot(x), maxdd=_maxdd(x), q_pos=int(sum(v > 0 for v in qp)), verdict="-" if split == "LEARN" else ("FAIL" if pnl.sum() <= 0 or _pboot(x) >= alpha else "CHECK")))
    T = pd.DataFrame(rows); T.to_csv(f"{L.OUT}/scalp_e44.csv", index=False); pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)
    print(T.round(dict(per_day=2, win=3, pts_prem=2, pts_idx=2, net=0, p=4, maxdd=0, net_2x=0, p_plac=3, plac_mean=0, rc_p=3, best_net=0, med_net=0)).to_string(index=False))


# ================================================================ E45: ITM depth, intrabar fills, hit rates
MENU45 = [(10, 10, 10), (15, 8, 15), (15, 10, 15), (15, 10, 30), (15, 15, 20), (20, 8, 20), (20, 10, 20), (20, 13, 30), (20, 20, 30), (25, 12, 30), (30, 15, 30), (30, 10, 30)]
BASE45 = [(10, 10, 10), (15, 10, 15), (15, 15, 20), (20, 10, 20), (20, 15, 30), (30, 15, 30)]
PMULT = np.where(SYMI == 0, 1.0, 3.0)  # SENSEX targets and stops x3 (frozen)


def gather(d, e, depth, dirn):
    """paths of the option `depth` strikes in the money at decision bar e-1 (CE for dirn > 0: ATM - depth steps; PE: ATM + depth steps).
    ENT (N,) = open of bar e (NaN unless traded in bars e-1 and e); O/H/Lo/C (N, 31) = that strike's bars e..e+30;
    X = open of the first traded bar at or after e+h+1; FX = bar e+h+1 itself untraded (a forced, delayed exit)."""
    d, e, dirn = np.asarray(d), np.asarray(e), np.asarray(dirn); N = len(d); sw = np.lib.stride_tricks.sliding_window_view
    G = dict(ENT=np.full(N, np.nan), **{n: np.full((N, NH), np.nan, np.float32) for n in ("O", "H", "Lo", "C", "X")}, FX=np.zeros((N, NH), bool))
    pad = lambda x, n=NH + 1: np.concatenate([x, np.full(n, np.nan)])
    o_ = np.lexsort((dirn, d)); bounds = np.flatnonzero(np.diff(d[o_], prepend=-1)); bounds = np.append(bounds, N)
    for a_, b_ in zip(bounds[:-1], bounds[1:]):
        rows = o_[a_:b_]; dd = d[rows[0]]; k = DAYK[dd]; p = P[k]; st = STEP[k[0]]
        Kr = p["atm"][e[rows] - 1] - np.sign(dirn[rows]) * depth * st
        for sg, sd in ((1, "CE"), (-1, "PE")):
            ms = np.sign(dirn[rows]) == sg
            for K in np.unique(Kr[ms & np.isfinite(Kr)]):
                a = p["C"].get((sd, K))
                if a is None: continue
                r = rows[ms & (Kr == K)]; ee = e[r]; o, h, l, c, v = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 6]; tr = np.isfinite(o) & (v > 0)
                nto = pd.Series(np.where(tr, o, np.nan)).bfill().values
                G["ENT"][r] = np.where(tr[ee] & tr[ee - 1], o[ee], np.nan)
                for n, x in (("O", o), ("H", h), ("Lo", l), ("C", c)): G[n][r] = sw(pad(x), NH)[ee]
                G["X"][r] = sw(pad(nto), NH)[ee + 1]; G["FX"][r] = sw(pad((~tr).astype(float)), NH)[ee + 1] != 0
    return G


def price45(G, d, e, T, S, H, conv="intrabar", fs=1.0, fc=1.0):
    """one exit cell. T, S premium points (scalars or per-row arrays), H minutes. Returns pts (premium points after spread), pnl10 / pnl5
    (Rs net at 10 / 5 lots), out (0 target, 1 stop, 2 time), xb (first bar a new entry may fill), forced, ok."""
    d, e = np.asarray(d), np.asarray(e); N = len(d); r = np.arange(N); o = G["ENT"]; ok = np.isfinite(o)
    ent = o + fs * hsv(d, M0 + e, np.nan_to_num(o, nan=1.0)); T = np.broadcast_to(np.asarray(T, float), (N,)); S = np.broadcast_to(np.asarray(S, float), (N,))
    with np.errstate(invalid="ignore"):
        if conv == "intrabar":
            th = G["H"][:, :H] >= (ent + T + 0.05)[:, None]; sh = G["Lo"][:, :H] <= (ent - S)[:, None]
            ti = np.where(th.any(1), th.argmax(1), 99); si = np.where(sh.any(1), sh.argmax(1), 99)
            out = np.where((si <= ti) & (si < 99), 1, np.where(ti < 99, 0, 2)); hx = np.where(out == 1, si, np.where(out == 0, ti, H - 1))
            stp = np.minimum(ent - S, G["O"][r, hx].astype(float)); xt = np.nan_to_num(G["X"][r, H - 1].astype(float), nan=0.05)
            px = np.where(out == 1, stp, xt); hh = fs * hsv(d, M0 + e + hx + (out == 2), np.maximum(px, 0.05))
            fill = np.where(out == 0, ent + T, np.maximum(px - hh, 0.05)); xb = e + hx + 1; forced = (out == 2) & G["FX"][r, H - 1]
        else:
            gain = G["C"][:, :H].astype(float) - ent[:, None]; hit = (gain >= T[:, None]) | (gain <= -S[:, None]); hit[:, H - 1] = True; hx = hit.argmax(1)
            g = gain[r, hx]; out = np.where(g >= T, 0, np.where(g <= -S, 1, 2)); x = np.nan_to_num(G["X"][r, hx].astype(float), nan=0.05)
            fill = np.maximum(x - fs * hsv(d, M0 + e + hx + 1, np.maximum(x, 0.05)), 0.05); xb = e + hx + 1; forced = G["FX"][r, hx]
    pts = fill - ent
    return dict(pts=pts, pnl10=pts * Q[d] - chg(d, ent, fill, fc), pnl5=pts * Q[d] * 0.5 - chg(d, ent, fill, fc, 0.5), out=out, xb=xb, forced=forced, ok=ok)


def _delta45(G, d, e, dirn):
    """LEARN slope of the 5-minute premium change on the 5-minute signed spot change (the option's index sensitivity at this depth)."""
    y = G["C"][:, 5].astype(float) - G["C"][:, 0]; x = dirn * (SPOT[d, e + 5] - SPOT[d, e]); m = np.isfinite(x) & np.isfinite(y) & ~ISTEST[d]
    return float(np.cov(x[m], y[m])[0, 1] / x[m].var())


def study_e45base():
    """E45-0 exit physics: unconditional entries every 5th bar 09:20-14:45, CE and PE, depth ATM / ITM2 / ITM3 / ITM4. Descriptive."""
    bars = np.arange(5, 331, 5); dd, ii, sg = np.meshgrid(np.arange(ND), bars, [1, -1], indexing="ij"); d, e, dirn = dd.ravel(), ii.ravel() + 1, sg.ravel()
    rows = []; dec = []; reg = {}; pm = PMULT[d]
    for depth in (0, 2, 3, 4):
        G = gather(d, e, depth, dirn); nm = "ATM" if depth == 0 else f"ITM{depth}"; ok = np.isfinite(G["ENT"])
        for s, sym in enumerate(("NIFTY", "SENSEX")):
            ms = (SYMI[d] == s) & ok; dl = _delta45({k: v[ms] for k, v in G.items()}, d[ms], e[ms], dirn[ms])
            for d0 in (0, 1):
                m = ms & (D0[d] == d0)
                dec.append(dict(sym=sym, day="expiry" if d0 else "other", depth=nm, n=int(m.sum()), premium=float(np.nanmedian(G["ENT"][m])), delta=dl, untraded_entry_pct=100 * float(1 - ok[(SYMI[d] == s) & (D0[d] == d0)].mean()),
                                chg15=float(np.nanmean(G["C"][m, 15] - G["ENT"][m])), chg30=float(np.nanmean(G["C"][m, 30] - G["ENT"][m]))))
            cells = [(T, S, H, f"{T}/{S}/{H}") for T, S, H in BASE45] + [(dl * 30, dl * 20, 15, "idx30/20/15"), (dl * 40, dl * 20, 20, "idx40/20/20")]
            for T, S, H, cn in cells:
                for conv in ("intrabar", "close"):
                    R = price45({k: v[ms] for k, v in G.items()}, d[ms], e[ms], T * PMULT[d[ms]], S * PMULT[d[ms]], H, conv)
                    if cn == "idx30/20/15" and conv == "intrabar" and depth in (0, 3):
                        t_ = ISTEST[d[ms]]; reg[(sym, depth)] = pd.Series(R["pnl10"][t_]).groupby(d[ms][t_]).mean()
                    for split, tm in (("LEARN", ~ISTEST[d[ms]]), ("TEST", ISTEST[d[ms]])):
                        for d0 in (0, 1):
                            m = tm & (D0[d[ms]] == d0); o = R["out"][m]; pts = R["pts"][m]; q = Q[d[ms]][m]; Tm = (T * PMULT[d[ms]])[m].mean(); Sm = (S * PMULT[d[ms]])[m].mean()
                            c10 = float(np.mean(pts - R["pnl10"][m] / q))
                            rows.append(dict(sym=sym, day="expiry" if d0 else "other", depth=nm, cell=cn, conv=conv, split=split, n=int(m.sum()), T=Tm, S=Sm,
                                             p_tgt=float((o == 0).mean()), p_stop=float((o == 1).mean()), p_time=float((o == 2).mean()),
                                             driftless=Sm / (Tm + Sm), breakeven=(Sm + c10) / (Tm + Sm), loss_on_stop=float(pts[o == 1].mean()) if (o == 1).any() else np.nan,
                                             pts_on_time=float(pts[o == 2].mean()) if (o == 2).any() else np.nan, exp_gross=float(pts.mean()),
                                             exp_net10=float(np.mean(R["pnl10"][m] / q)), exp_net5=float(np.mean(R["pnl5"][m] / (q * 0.5))),
                                             rs10=float(R["pnl10"][m].mean()), rs5=float(R["pnl5"][m].mean()), forced_pct=100 * float(R["forced"][m].mean())))
        print("depth", nm, "done", flush=True)
    T_ = pd.DataFrame(rows); T_.to_csv(f"{L.OUT}/scalp_e45base.csv", index=False); Dc = pd.DataFrame(dec); pd.set_option("display.width", 330); pd.set_option("display.max_columns", 40)
    print("\nE45-0 decay / delta by depth (all days; chg15 / chg30 = mean premium change over 15 / 30 min, CE and PE averaged = direction-neutral)"); print(Dc.round(3).to_string(index=False))
    for conv in ("intrabar", "close"):
        print(f"\nE45-0 exit physics, TEST year, {conv} fills (premium points per unit; rs = Rs per trade)")
        print(T_[(T_.split == "TEST") & (T_.conv == conv)].drop(columns=["conv", "split"]).round(dict(T=1, S=1, p_tgt=3, p_stop=3, p_time=3, driftless=3, breakeven=3, loss_on_stop=2, pts_on_time=2, exp_gross=2, exp_net10=2, exp_net5=2, rs10=0, rs5=0, forced_pct=2)).to_string(index=False))
    g = T_[(T_.conv == "intrabar")]; lift = (g.p_tgt - g.driftless) * 100
    print(f"\nstop condition 1: target-first share minus driftless S/(T+S), intrabar, all rows: min {lift.min():.1f} max {lift.max():.1f} median {lift.median():.1f} percentage points")
    print("\nregistered test: TEST daily mean net Rs per trade (10 lots, intrabar, same index move 30/20/15), ITM3 minus ATM")
    for sym in ("NIFTY", "SENSEX"):
        x = (reg[(sym, 3)] - reg[(sym, 0)]).dropna().values; I = HST._stat_boot_idx(len(x), 4000, 0.2, np.random.default_rng(7)); bm = x[I].mean(1)
        print(f"  {sym}: ITM3 {reg[(sym, 3)].mean():,.0f}  ATM {reg[(sym, 0)].mean():,.0f}  diff {x.mean():,.0f} Rs/trade over {len(x)} days, two-sided p {2 * min((bm <= 0).mean(), (bm >= 0).mean()):.4f}")


def feats45(p, sym, prev):
    """E45 features, all causal. prev = list of the prior days' F range-so-far arrays (same index)."""
    f = day_feats(p, sym); F = f["F"]; dF = np.diff(F, prepend=np.nan); sF = pd.Series(dF).shift(1).rolling(30, min_periods=30).std().values
    Fs = pd.Series(F); rng = (Fs.cummax() - Fs.cummin()).values
    f.update(dF=dF, sF=sF, e20=Fs.ewm(span=20, adjust=False, ignore_na=True).mean().values, e60=Fs.ewm(span=60, adjust=False, ignore_na=True).mean().values, rng=rng,
             prng=np.median(prev[-20:], 0) if len(prev) >= 20 else None)
    return f


def signals45(f):
    """the 8 frozen E45 rules for one sym-day -> {name: [(decision bar i, direction)]}."""
    F, sF, d0 = f["F"], f["sF"], f["d0"]; i_ = np.arange(NB); win = (i_ >= 30) & (i_ <= 330); out = {}; Fs = pd.Series(F); sh = lambda n: Fs.shift(n).values
    with np.errstate(invalid="ignore", divide="ignore"):
        m15 = F - sh(15); m = win & ((i_ - 30) % 15 == 0) & (np.abs(m15) >= sF * np.sqrt(15)); out["R1_tsmom"] = _cool(i_[m], np.sign(m15)[m], 1, 20)
        up = (f["e20"] > f["e60"]) & (sh(1) < sh(2)) & (sh(2) < sh(3)) & (F > sh(1)) & (F > f["e60"])
        dn = (f["e20"] < f["e60"]) & (sh(1) > sh(2)) & (sh(2) > sh(3)) & (F < sh(1)) & (F < f["e60"]); m = win & (up | dn)
        out["R2_pullback"] = _cool(i_[m], np.where(up, 1, -1)[m], 10, 20)
        dFs = pd.Series(f["dF"]); ratio = dFs.rolling(10, min_periods=10).std().values / dFs.rolling(60, min_periods=60).std().values; m5 = F - sh(5)
        m = win & (ratio >= 1.5); out["R3_volexp"] = _cool(i_[m], np.sign(m5)[m], 10, 20)
        F0 = F[np.isfinite(F)][0] if np.isfinite(F).any() else np.nan; day = F / F0 - 1
        up = (day >= 0.004) & (F >= Fs.rolling(15, min_periods=15).max().values); dn = (day <= -0.004) & (F <= Fs.rolling(15, min_periods=15).min().values)
        m = win & (up | dn); out["R4_donchian"] = _cool(i_[m], np.where(up, 1, -1)[m], 10, 20)
        # R5: ITM2 CE at its own 20-bar closing high while ITM2 PE at its 20-bar low (strikes fixed by ATM at bar i), volume above its prior 30-bar median
        M, ai, nK = f["M"], f["ai"], f["nK"]; jc, jp = ai - 2, ai + 2; g = f["aok"] & (jc >= 0) & (jp < nK); jc, jp = np.clip(jc, 0, nK - 1), np.clip(jp, 0, nK - 1)
        def ext(sd, col, how, n, lag=0): return getattr(pd.DataFrame(M[sd][col].T).shift(lag).rolling(n, min_periods=n), how)().values
        cC, cP = M["CE"][3].T, M["PE"][3].T; vC, vP = M["CE"][6].T, M["PE"][6].T; pk = lambda A, j: A[i_, j]
        up = g & (pk(cC, jc) >= pk(ext("CE", 3, "max", 20), jc)) & (pk(cP, jp) <= pk(ext("PE", 3, "min", 20), jp)) & (pk(vC, jc) > pk(ext("CE", 6, "median", 30, 1), jc))
        dn = g & (pk(cP, jp) >= pk(ext("PE", 3, "max", 20), jp)) & (pk(cC, jc) <= pk(ext("CE", 3, "min", 20), jc)) & (pk(vP, jp) > pk(ext("PE", 6, "median", 30, 1), jp))
        m = win & (up | dn) & ~(up & dn); out["R5_prembreak"] = _cool(i_[m], np.where(up, 1, -1)[m], 10, 20)
        # R6: straddle of the bar-i ATM strike above its own level 10 bars ago, and a 5-bar F move >= sF sqrt(5)
        st_now = pk(cC, ai) + pk(cP, ai); st_old = pk(pd.DataFrame(cC).shift(10).values, ai) + pk(pd.DataFrame(cP).shift(10).values, ai)
        m = win & f["aok"] & (st_now > st_old) & (np.abs(m5) >= sF * np.sqrt(5)); out["R6_volbid"] = _cool(i_[m], np.sign(m5)[m], 10, 20)
        m3 = F - sh(3); m = (i_ >= 225) & (i_ <= 330) & (d0 == 1) & (np.abs(m3) >= 1.5 * sF * np.sqrt(3)); out["R7_expgamma"] = _cool(i_[m], np.sign(m3)[m], 5, 20)
        r8 = []
        if f["prng"] is not None and d0 == 0:
            rl = Fs.shift(1).rolling(30, min_periods=30); z = (F - rl.mean().values) / rl.std().values
            hi = F >= Fs.rolling(31, min_periods=31).max().values; lo = F <= Fs.rolling(31, min_periods=31).min().values
            m = win & (f["rng"] <= 0.5 * f["prng"]) & ((hi & (z >= 2)) | (lo & (z <= -2))); r8 = _cool(i_[m], np.where(hi, -1, 1)[m], 10, 20)
        out["R8_rangefade"] = r8
    return out


def all_signals45():
    rows = []; prev = {"NIFTY": [], "SENSEX": []}
    for d, k in enumerate(DAYK):
        f = feats45(P[k], k[0], prev[k[0]])
        for nm, lst in signals45(f).items(): rows += [(nm, d, i, s) for i, s in lst]
        prev[k[0]].append(np.nan_to_num(f["rng"], nan=np.inf))
    return pd.DataFrame(rows, columns=["sig", "d", "i", "dirn"])


def study_lookahead45(n_days=24, seed=5):
    """the E44 look-ahead scan on the E45 rules: scramble everything after bar i, every signal at or before i must be unchanged."""
    rg = np.random.default_rng(seed); ks = [DAYK[j] for j in rg.choice(ND, n_days, replace=False)] + [k for k in DAYK if P[k]["d0"]][-6:]; bad = n = 0
    for k in ks:
        p = P[k]; prev = [np.full(NB, 1e9)] * 20; base = signals45(feats45(p, k[0], prev))
        for i in (35, 47, 90, 150, 222, 290, 320):
            q = dict(p, spot=p["spot"].copy(), atm=p["atm"].copy(), C={kk: a.copy() for kk, a in p["C"].items()})
            m = NB - i - 1; q["spot"][i + 1:] *= rg.uniform(0.97, 1.03, m); q["atm"][i + 1:] = p["atm"][i] + 2 * STEP[k[0]]
            for a in q["C"].values(): a[i + 1:] *= rg.uniform(0.5, 1.5, (m, 7))
            got = signals45(feats45(q, k[0], prev))
            for nm in base:
                n += 1; x, y = [t for t in base[nm] if t[0] <= i], [t for t in got[nm] if t[0] <= i]
                if x != y: bad += 1; print("LOOK-AHEAD", k, nm, i, x[-2:], y[-2:])
    print(f"E45 look-ahead scan: {n} (rule, day, cut) checks on {len(ks)} sym-days, {bad} leaks; signals on the last day: { {a: len(b) for a, b in base.items()} }"); assert bad == 0


def _eval45(G, d, e, dirn, cell, days, conv="intrabar", fs=1.0, fc=1.0):
    """one cell with the one-at-a-time rule -> dict of taken-trade arrays + daily Rs."""
    T, S, H = cell; R = price45(G, d, e, T * PMULT[d], S * PMULT[d], H, conv, fs, fc); tk = greedy(d, e, R["xb"][:, None], R["ok"])[:, 0]
    return dict(tk=tk, R=R, x10=_daily(d[tk], R["pnl10"][tk], days), x5=_daily(d[tk], R["pnl5"][tk], days))


def _stats45(name, sym, split, depth, cell, G, d, e, dirn, days, extra=None):
    E = _eval45(G, d, e, dirn, cell, days); tk, R = E["tk"], E["R"]; o = R["out"][tk]; pts = R["pts"][tk]; n = int(tk.sum()); dd = d[tk]
    idx = dirn[tk] * (SPOT[dd, np.minimum(R["xb"][tk], NB - 1) - 1] - SPOT[dd, e[tk] - 1]); E2 = _eval45(G, d, e, dirn, cell, days, fs=2.0, fc=2.0); Ec = _eval45(G, d, e, dirn, cell, days, "close")
    qp = [E["x10"][q].sum() for q in np.array_split(np.arange(len(days)), 4)]; q = Q[dd]
    return dict(strategy=name, sym=sym, split=split, depth="ATM" if depth == 0 else f"ITM{depth}", cell="/".join(map(str, cell)), trades=n, per_day=n / len(days),
                win=float((R["pnl10"][tk] > 0).mean()) if n else np.nan, p_tgt=float((o == 0).mean()) if n else np.nan, p_stop=float((o == 1).mean()) if n else np.nan,
                p_time=float((o == 2).mean()) if n else np.nan, loss_on_stop=float(pts[o == 1].mean()) if (o == 1).any() else np.nan,
                pts_prem=float(pts.mean()) if n else np.nan, pts_net=float((R["pnl10"][tk] / q).mean()) if n else np.nan, pts_idx=float(np.nanmean(idx)) if n else np.nan,
                net10=float(E["x10"].sum()), net5=float(E["x5"].sum()), p=_pboot(E["x10"]) if n else np.nan, maxdd=_maxdd(E["x10"]), net_2x=float(E2["x10"].sum()),
                net_close=float(Ec["x10"].sum()), q_pos=int(sum(v > 0 for v in qp)), forced_pct=100 * float(R["forced"][tk].mean()) if n else np.nan, **(extra or {})), E


def study_e45():
    """E45: 8 rules x 2 indices; LEARN picks (depth in ITM2/3/4, cell) of 36 under intrabar fills; TEST scored once; ATM same cell = control."""
    import pickle, os
    cache = f"{L.OUT}/scalp_e45_sigs.pkl"
    if os.path.exists(cache): G_ = pickle.load(open(cache, "rb"))
    else: G_ = all_signals45(); pickle.dump(G_, open(cache, "wb"))
    G_ = G_.sort_values(["d", "i"]).reset_index(drop=True); rows = []; alpha = 0.05 / 16; rg = np.random.default_rng(3)
    print(f"E45: {len(G_)} signals; alpha {alpha:.4f}", flush=True)
    for s, sym in enumerate(("NIFTY", "SENSEX")):
        dl = np.flatnonzero((SYMI == s) & ~ISTEST); dt = np.flatnonzero((SYMI == s) & ISTEST)
        for nm in sorted(G_.sig.unique()):
            g = G_[(G_.sig == nm) & (SYMI[G_.d.values] == s)]; d, e, dirn = g.d.values, g.i.values + 1, g.dirn.values; lm = ~ISTEST[d]; sub = lambda G, m: {k: v[m] for k, v in G.items()}
            GD = {dep: gather(d, e, dep, dirn) for dep in (0, 2, 3, 4)}; X = []; keys = []
            for dep in (2, 3, 4):
                for cell in MENU45:
                    E = _eval45(sub(GD[dep], lm), d[lm], e[lm], dirn[lm], cell, dl); X.append(E["x10"] if E["tk"].sum() >= 100 else np.full(len(dl), np.nan)); keys.append((dep, cell))
            X = np.stack(X, 1); val = np.isfinite(X[0])
            if not val.any(): rows.append(dict(strategy=nm, sym=sym, split="LEARN", verdict="TOO FEW (< 100 LEARN trades)")); continue
            Xv = X[:, val]; t = Xv.mean(0) / (Xv.std(0, ddof=1) / np.sqrt(len(dl)) + 1e-12); j = int(t.argmax()); dep, cell = [k for k, v in zip(keys, val) if v][j]
            ex = dict(rc_p=_rc(Xv, j), cells_pos=int((Xv.sum(0) > 0).sum()), n_cells=int(val.sum()))
            rl, _ = _stats45(nm, sym, "LEARN", dep, cell, sub(GD[dep], lm), d[lm], e[lm], dirn[lm], dl, ex)
            rt, Et = _stats45(nm, sym, "TEST", dep, cell, sub(GD[dep], ~lm), d[~lm], e[~lm], dirn[~lm], dt)
            rc, _ = _stats45(nm + " [ATM control]", sym, "TEST", 0, cell, sub(GD[0], ~lm), d[~lm], e[~lm], dirn[~lm], dt)
            # placebo: same sym-days, same number of entries per day, random bars of the rule's window, random side
            lo_, hi_ = (225, 330) if nm.startswith("R7") else (30, 330); dT = d[~lm]; tot = np.zeros(200)
            for r_ in range(200):
                ii = rg.integers(lo_, hi_ + 1, len(dT)); o_ = np.lexsort((ii, dT)); dd, ee = dT[o_], ii[o_] + 1; sg = rg.choice([-1, 1], len(dd))
                tot[r_] = _eval45(gather(dd, ee, dep, sg), dd, ee, sg, cell, dt)["x10"].sum()
            rt["p_plac"] = float(((tot >= rt["net10"]).sum() + 1) / 201); rt["plac_mean"] = float(tot.mean())
            ok = (rt["net10"] > 0 and rt["net5"] > 0 and rl["net10"] > 0 and ex["rc_p"] < 0.10 and rt["p"] < alpha and rt["p_plac"] < 0.05 and rt["net_2x"] > 0 and rt["q_pos"] >= 3
                  and rt["trades"] >= 500 and rt["per_day"] >= 3 and rt["net_close"] > 0 and (sym != "NIFTY" or rt["pts_net"] >= 1.0))
            rt["verdict"] = "PASS" if ok else "FAIL"; rl["verdict"] = "-"; rc["verdict"] = "control"; rows += [rl, rt, rc]
            print(nm, sym, dep, cell, f"LEARN {rl['net10']:,.0f} TEST {rt['net10']:,.0f} ATM {rc['net10']:,.0f}", flush=True)
    T = pd.DataFrame(rows); T.to_csv(f"{L.OUT}/scalp_e45.csv", index=False); pd.set_option("display.width", 400); pd.set_option("display.max_columns", 50)
    rd = {c: 0 for c in ("net10", "net5", "maxdd", "net_2x", "net_close", "plac_mean")}; rd.update({c: 3 for c in ("win", "p_tgt", "p_stop", "p_time", "p_plac", "rc_p")}); rd.update(per_day=2, loss_on_stop=2, pts_prem=2, pts_net=2, pts_idx=2, p=4, forced_pct=2)
    print(T.round(rd).to_string(index=False))


def study_selftest():
    """known answers on a synthetic day: hand-computed fills, charges equal L.cost, the greedy one-at-a-time rule, exits."""
    k = next(k for k in DAYK if k[1] >= HO and k[0] == "NIFTY"); d = DIX[k]; Z = pool(); keep = {n: Z[n][d].copy() for n in Z}
    try:
        e = 100; Z["ENT"][d, e, 0] = 100.0; path = np.array([101, 103, 106, 104] + [104] * 27, np.float32); nxt = np.array([102, 104, 107, 105] + [105] * 27, np.float32)
        Z["CP"][d, e, 0] = path; Z["XP"][d, e, 0] = nxt
        R = price([d], [e], [0], [1], [(5, 5, 30), (10, 2, 30), (100, 30, 3), (100, 30, 30)])
        h = L.hs("NIFTY", P[k]["d0"], M0 + e, 100.0); ent = 100 + h
        # (5,5,30): gain 101-ent < 5, 103-ent < 5, 106-ent >= 5 at h=2 -> fill XP[2] = 107 - hs
        f = 107 - L.hs("NIFTY", P[k]["d0"], M0 + e + 3, 107.0); want = (f - ent) * L.qty("NIFTY", _kc(k)) - L.cost(ent, f, "NIFTY", _kc(k))
        assert abs(R["pnl"][0, 0] - want) < 0.01 and R["xb"][0, 0] == e + 3, (R["pnl"][0, 0], want)
        assert R["xb"][0, 2] == e + 3 and R["xb"][0, 3] == e + 30          # time-stop 3: decided at the close of bar e+2; 30: bar e+29
        Z["CP"][d, e, 0, 0] = 97.0; R = price([d], [e], [0], [1], [(10, 2, 30)]); assert R["xb"][0, 0] == e + 1  # stop on the first close
        f = 102 - L.hs("NIFTY", P[k]["d0"], M0 + e + 1, 102.0); assert abs(R["pts"][0, 0] - (f - ent)) < 1e-4
        Z["ENT"][d, e, 0] = np.nan; assert not price([d], [e], [0], [1], [(5, 5, 3)])["ok"][0]                   # untraded entry bar: no trade
        tk = greedy(np.array([d, d, d]), np.array([10, 12, 20]), np.array([[15], [30], [25]]), np.array([True, True, True])); assert tk[:, 0].tolist() == [True, False, True]
        assert abs(chg(np.array([d]), np.array([100.0]), np.array([120.0]))[0] - L.cost(100.0, 120.0, "NIFTY", _kc(k))) < 1e-9
        assert abs(hsv(np.array([d]), np.array([700]), np.array([150.0]))[0] - L.hs("NIFTY", P[k]["d0"], 700, 150.0)) < 1e-12
    finally:
        for n in Z: Z[n][d] = keep[n]
    # pool against the raw panel on a real day
    p = P[k]; e = 120; K = p["atm"][e - 1]; a = p["C"][("CE", K)]
    if a[e, 6] > 0 and a[e - 1, 6] > 0: assert Z["ENT"][d, e, 0] == np.float32(a[e, 0]) and Z["CP"][d, e, 0, 5] == np.float32(a[e + 5, 3])
    # E45 intrabar convention, hand-priced on a synthetic path: entry open 100; bar highs/lows decide
    G = dict(ENT=np.array([100.0, 100.0, 100.0]), O=np.tile(np.float32([100, 101, 103, 99] + [99] * 27), (3, 1)), H=np.tile(np.float32([101, 104, 112, 100] + [100] * 27), (3, 1)),
             Lo=np.tile(np.float32([99.5, 100.5, 96, 98] + [98] * 27), (3, 1)), C=np.tile(np.float32([100.5, 103, 97, 99] + [99] * 27), (3, 1)),
             X=np.tile(np.float32([101, 103, 99, 99] + [99] * 27), (3, 1)), FX=np.zeros((3, NH), bool))
    dd = np.array([d, d, d]); ee = np.array([100, 100, 100]); R = price45(G, dd, ee, np.array([3.0, 10.0, 50.0]), np.array([10.0, 3.0, 50.0]), 2); ent = 100 + h
    # row 0: T=3 -> limit ent+3; bar 1 high 104 >= limit + 0.05 -> filled AT the limit: +3.00 points, no exit spread
    assert R["out"][0] == 0 and abs(R["pts"][0] - 3.0) < 1e-9 and R["xb"][0] == 102
    # row 1: T=10, S=3, H=2: no stop/target in bars 0-1 (low 99.5 > ent-3) -> time exit at X[1] = 103 - hs
    assert R["out"][1] == 2 and abs(R["pts"][1] - (103 - L.hs("NIFTY", P[k]["d0"], M0 + 102, 103.0) - ent)) < 1e-6 and R["xb"][1] == 102
    R = price45(G, dd, ee, np.array([11.0, 10.0, 50.0]), np.array([3.0, 3.0, 50.0]), 5)
    # H=5, T=11, S=3: bar 2 has high 112 (target) AND low 96 (stop) -> the stop wins; fill = min(ent-3, open 103) - hs
    stp = ent - 3; assert R["out"][0] == 1 and abs(R["pts"][0] - (stp - L.hs("NIFTY", P[k]["d0"], M0 + 102, stp) - ent)) < 1e-6
    Rc = price45(G, dd, ee, 2.0, 2.0, 5, "close")  # close convention: bar 1 close 103 - ent >= 2 -> sell at X[1] = 103 - hs
    assert Rc["out"][0] == 0 and abs(Rc["pts"][0] - (103 - L.hs("NIFTY", P[k]["d0"], M0 + 102, 103.0) - ent)) < 1e-6
    assert abs(R["pnl5"][0] - (R["pts"][0] * Q[d] * 0.5 - (L.cost(ent, ent + R["pts"][0], "NIFTY", _kc(k)) - L.CM * 1.18 * 40) * 0.5 - L.CM * 1.18 * 40)) < 0.01  # 5 lots: only brokerage stays whole
    # gather against the raw panel: ITM2 CE = ATM - 2 steps
    e2 = 120; Gg = gather([d], [e2], 2, [1]); a2 = p["C"].get(("CE", p["atm"][e2 - 1] - 2 * STEP["NIFTY"]))
    if a2 is not None and a2[e2, 6] > 0 and a2[e2 - 1, 6] > 0: assert Gg["ENT"][0] == a2[e2, 0] and Gg["H"][0, 3] == np.float32(a2[e2 + 3, 1]) and Gg["Lo"][0, 0] == np.float32(a2[e2, 2])
    print("scalp_lab selftest OK (E45: limit target at the limit, stop wins a tie, time exit, close convention, 5-lot charges, ITM gather == panel; hand-priced target / stop / time exits, charges == L.cost, half-spread == L.hs, no entry on an untraded bar, one position at a time, pool == panel)")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
