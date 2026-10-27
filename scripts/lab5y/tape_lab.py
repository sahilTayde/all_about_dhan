"""Round-1 options-tape lab (EXPLORATORY, ~13 tape days). Needs tape_cache.py output first.
Fills: decide at a 5s snapshot, buy at the ASK of the NEXT snapshot, sell at the BID of the snapshot after the
exit trigger (so stops gap through at the real bid). Costs = config/charges.yaml x1.5 (COST_MULT), 10 lots.
Run: ~/paper_extra_venv/bin/python scripts/lab5y/tape_lab.py CACHE_DIR
Families: F1 vol timing (straddle), F2 microstructure IC + trade, F3 exits on same entries, F4 walk-forward ridge.
Placebo = same entries-per-day at random minutes/sides with the same exit (from a precomputed pool)."""
import sys, os, json, glob, pickle, numpy as np, pandas as pd

C = sys.argv[1] if len(sys.argv) > 1 else "cache"
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
LOT = {"NIFTY": 65, "SENSEX": 20}; LOTS = 10; COST_MULT = 1.5
TXN = {"NIFTY": 0.000355299, "SENSEX": 0.000325}
HOL = ["2026-10-02", "2026-10-20"]  # NSE/BSE holidays in window (NIFTY expired Mon 10-19 => Tue 10-20 shut)
SKIP = {"2026-09-28", "2026-10-06"}  # 1h tape / 59% stale
RNG = np.random.default_rng(7)


def cost(buy, sell, sym):
    q = LOT[sym] * LOTS; bt, st = buy * q, sell * q; tx = TXN[sym] * (bt + st); sebi = 1e-6 * (bt + st)
    return COST_MULT * (40 + tx + sebi + 0.18 * (40 + tx + sebi) + 0.00003 * bt + 0.0015 * st)


def tmin_to_expiry(day, minute, exp):
    """trading minutes from day/minute to expiry 15:30 (causal calendar arithmetic)."""
    nd = np.busday_count(day, exp, holidays=HOL)
    return (930 - minute) + 375 * nd


# ---------------------------------------------------------------- panel
def build():
    P = {}
    for f in sorted(glob.glob(f"{C}/*_q.parquet")):
        day = os.path.basename(f)[:10]
        if day in SKIP: continue
        q = pd.read_parquet(f); u = pd.read_parquet(f"{C}/{day}_u.parquet")
        q["sym"] = q.iid.str.split(":").str[1]
        for sym, g in q.groupby("sym"):
            g = g[g.rule != "HELD"]
            ts = np.array(sorted(g.ts.unique())); n = len(ts)
            T = pd.DataFrame({"ts": ts})
            sp = u[u.iid.str.contains("_IDX:" + sym)].sort_values("ts")[["ts", "ltp"]].dropna()
            T = pd.merge_asof(T, sp.rename(columns={"ltp": "S"}), on="ts", direction="backward")
            fu = u[(u.iid.str.count(":") == 2) & u.iid.str.contains(sym)].sort_values("ts")
            if len(fu):
                T = pd.merge_asof(T, fu[["ts", "bid", "ask", "bq5", "aq5", "oi"]].add_prefix("f_").rename(columns={"f_ts": "ts"}), on="ts")
            ix = {t: i for i, t in enumerate(ts)}
            gi = g.assign(k=g.ts.map(ix))
            ok = ~gi.stale.fillna(True).astype(bool) & gi.bid.notna() & gi.ask.notna() & (gi.bid > 0)
            gi.loc[~ok, ["bid", "ask"]] = np.nan
            # prices from depth (all subscribed strikes, all day). A depth bucket [t-5s, t) is "known" at grid t.
            o = pd.read_parquet(f"{C}/{day}_o.parquet"); o = o[o.iid.str.split(":").str[1] == sym]
            o = o.assign(k=(o.ts + pd.Timedelta(seconds=5)).map({pd.Timestamp(t).floor("5s"): i for i, t in enumerate(ts)}))
            o = o[o.k.notna() & (o.bid > 0) & (o.ask > 0) & (o.ask >= o.bid)]
            Q = {}
            for iid, h in o.groupby("iid"):
                a = np.full((n, 3), np.nan); a[h.k.values.astype(int)] = h[["bid", "ask", "oi"]].values; Q[iid] = a
            R = {}
            for (rule, side), h in gi.groupby(["rule", "side"]):
                a = np.full(n, None, dtype=object); a[h.k.values] = h.iid.values; R[(rule, side)] = a
            m = (pd.to_datetime(ts).hour * 60 + pd.to_datetime(ts).minute).values
            exp = g.iid.str.split(":").str[2].iloc[0]
            P[(sym, day)] = dict(ts=ts, m=m, T=T, Q=Q, R=R, exp=exp)
    return P


PK = f"{C}/panel.pkl"
if not os.path.exists(PK): pickle.dump(build(), open(PK, "wb"))
P = pickle.load(open(PK, "rb")); KEYS = sorted(P, key=lambda k: (k[1], k[0])); DAYS = sorted({k[1] for k in KEYS})


def nxt(a, j):
    """first index >= j with finite a."""
    w = np.flatnonzero(np.isfinite(a[j:]))
    return j + w[0] if len(w) else None


# ---------------------------------------------------------------- one trade
def trade(k, i, side, rule="ITM200", hold=15, stop=None, tgt=None, trail=None, atr_k=None, flat=915):
    """k sym-day, i decision snapshot index. stop/tgt/trail = fraction of entry premium; atr_k: stop at
    atr_k * (index 15-min range) * 0.7 premium points. Returns (net INR, hold_min) or None."""
    p = P[k]; iid = p["R"].get((rule, side), [None] * len(p["ts"]))[i] if i < len(p["ts"]) else None
    if iid is None: return None
    a = p["Q"][iid]; bid, ask = a[:, 0], a[:, 1]
    e = nxt(ask, i + 1)
    if e is None or e > i + 3: return None
    E = ask[e]; m = p["m"]
    endm = min(m[e] + hold if hold else 9999, flat)
    last = np.searchsorted(m, endm)  # first snapshot at/after time exit
    if last >= len(m): last = len(m) - 1
    seg = bid[e + 1:last + 1]; x = None
    if len(seg) == 0: return None
    trig = np.zeros(len(seg), bool)
    st = None
    if stop is not None: st = E * (1 - stop)
    if atr_k is not None:
        S = p["T"].S.values; w = S[max(0, i - 180):i + 1]
        st = E - atr_k * (np.nanmax(w) - np.nanmin(w)) * 0.7
    fs = np.where(np.isfinite(seg), seg, np.inf)
    if st is not None: trig |= fs <= st
    if tgt is not None: trig |= np.where(np.isfinite(seg), seg, -np.inf) >= E * (1 + tgt)
    if trail is not None:
        hi = np.fmax.accumulate(np.where(np.isfinite(seg), seg, E)); hi = np.maximum(hi, E)
        trig |= fs <= hi * (1 - trail)
    j = np.argmax(trig) if trig.any() else None
    if j is not None:
        jj = nxt(bid, e + 1 + j + 1)  # fill at bid of the NEXT snapshot after trigger
    else:
        jj = nxt(bid, last)
    if jj is None: jj = nxt(bid[::-1], 0); jj = len(bid) - 1 - jj if jj is not None else None
    if jj is None: return None
    X = bid[jj]
    return (X - E) * LOT[k[0]] * LOTS - cost(E, X, k[0]), (m[jj] - m[e])


def minute_idx(k, lo=560, hi=900):
    """first snapshot index of each minute in [lo, hi)."""
    m = P[k]["m"]; _, first = np.unique(m, return_index=True)
    return [i for i in first if lo <= m[i] < hi]


# ---------------------------------------------------------------- placebo pool
def pool(exit_kw, rule="ITM200", lo=560, hi=900):
    key = f"{C}/pool_{rule}_{lo}_{hi}_" + "_".join(f"{a}{b}" for a, b in sorted(exit_kw.items())) + ".pkl"
    if os.path.exists(key): return pickle.load(open(key, "rb"))
    out = {}
    for k in KEYS:
        rows = []
        for i in minute_idx(k, lo, hi):
            for s in ("CE", "PE"):
                r = trade(k, i, s, rule, **exit_kw)
                if r: rows.append((i, s, r[0]))
        out[k] = rows
    pickle.dump(out, open(key, "wb")); return out


def placebo(entries, pl, runs=1000):
    """entries: list of (k, pnl). Same count per sym-day drawn at random from the pool (random minute & side)."""
    cnt = pd.Series([e[0] for e in entries]).value_counts()
    tot = np.zeros(runs)
    for k, c in cnt.items():
        v = np.array([r[2] for r in pl[k]])
        if len(v): tot += RNG.choice(v, size=(runs, c)).sum(1)
    return tot


def stats(name, entries, pl=None, runs=1000):
    if not entries: return dict(name=name, n=0)
    v = np.array([e[1] for e in entries]); days = [e[0][1] for e in entries]
    dd = np.min(np.cumsum(v) - np.maximum.accumulate(np.cumsum(v)))
    half = DAYS[len(DAYS) // 2]
    late = v[np.array([d >= half for d in days])]
    r = dict(name=name, n=len(v), win=round((v > 0).mean() * 100), avg=round(v.mean()), tot=round(v.sum()),
             maxdd=round(dd), ndays=len(set(days)), late_n=len(late), late_tot=round(late.sum()))
    if pl is not None:
        pt = placebo(entries, pl, runs); r["pct"] = round((pt < v.sum()).mean() * 100, 1); r["p"] = round((pt >= v.sum()).mean(), 3)
        r["plac_med"] = round(np.median(pt))
    if len(entries[0]) == 3:  # side placebo: same times, random CE/PE
        alt = np.array([e[2] for e in entries]); flip = RNG.random((runs, len(v))) < 0.5
        ps = np.where(flip, alt, v).sum(1); r["p_side"] = round((ps >= v.sum()).mean(), 3)
        # day-cluster side placebo: flip ALL trades of a sym-day together (trades in one day are not independent)
        ks = [e[0] for e in entries]; u = sorted(set(ks)); ix = np.array([u.index(k) for k in ks])
        fl = RNG.random((runs, len(u))) < 0.5; pdy = np.where(fl[:, ix], alt, v).sum(1); r["p_day"] = round((pdy >= v.sum()).mean(), 3)
        r["pos_days"] = f"{int((pd.Series(v).groupby([str(k) for k in ks]).sum() > 0).sum())}/{len(u)}"
    return r


def show(rows):
    df = pd.DataFrame(rows); print(df.to_string(index=False), flush=True); return df


# ---------------------------------------------------------------- features (1-min, causal)
def feats(k):
    p = P[k]; T = p["T"]; S = T.S.values; m = p["m"]; Rm = p["R"]; Q = p["Q"]
    rows = []
    for i in minute_idx(k, 556, 916):
        def mid(rule, side, j):
            iid = Rm.get((rule, side), [None] * len(m))[j]
            if iid is None: return np.nan, np.nan, np.nan, None
            b, a, oi = Q[iid][j]; return (b + a) / 2, a - b, oi, iid
        cm, csp, coi, ciid = mid("ATM", "CE", i); pm, psp, poi, piid = mid("ATM", "PE", i)
        j15 = max(0, i - 180); j5 = max(0, i - 60)
        f = dict(k=k, i=i, m=m[i], S=S[i], strad=cm + pm, sprd=(csp + psp) / (cm + pm) if cm + pm > 0 else np.nan,
                 r5=S[i] / S[j5] - 1, r15=S[i] / S[j15] - 1, rng15=(np.nanmax(S[j15:i + 1]) - np.nanmin(S[j15:i + 1])) / S[i])
        # OI change on the SAME ATM instruments over 15 min (OI is ~1-min cadence)
        if ciid and piid:
            c0, p0 = Q[ciid][j15, 2], Q[piid][j15, 2]
            f["doi_ce"] = coi / c0 - 1 if c0 else np.nan; f["doi_pe"] = poi / p0 - 1 if p0 else np.nan
            f["oi_flow"] = ((poi - p0) - (coi - c0)) / (poi + coi) if (poi + coi) else np.nan
            # premium momentum vs index: CE-PE mid change minus what index move explains (delta~0.5 each)
            cb = np.nanmean(Q[ciid][j5, :2]); pb = np.nanmean(Q[piid][j5, :2])
            f["div"] = (((cm - cb) - (pm - pb)) - (S[i] - S[j5])) / S[i]
            f["dstrad"] = (cm + pm) / (cb + pb) - 1
            # long buildup: price up & CE OI up; short covering: price up & CE OI down  -> sign(r15)*sign(doi_ce)
            f["build"] = np.sign(f["r15"]) * np.sign(f["doi_ce"] - f["doi_pe"])
            f["noroll"] = Rm[("ATM", "CE")][j15] == ciid
        if "f_bq5" in T:
            w = slice(max(0, i - 12), i + 1); b5, a5 = T.f_bq5.values[w], T.f_aq5.values[w]
            f["imb"] = np.nanmean((b5 - a5) / (b5 + a5))
            f["basis"] = (T.f_bid.values[i] + T.f_ask.values[i]) / 2 / S[i] - 1
            f["dbasis"] = f["basis"] - ((T.f_bid.values[j5] + T.f_ask.values[j5]) / 2 / S[j5] - 1)
        # vol timing: realized 1-min sigma last 30 min vs implied sigma from straddle to expiry
        j30 = max(0, i - 360); s1 = S[j30:i + 1:12]; rv = np.nanstd(np.diff(np.log(s1))) if len(s1) > 10 else np.nan
        tm = tmin_to_expiry(k[1], m[i], p["exp"]); iv = (cm + pm) / (0.8 * S[i] * np.sqrt(tm)) if tm > 0 else np.nan
        f["rv_iv"] = rv / iv if iv else np.nan; f["iv1m"] = iv
        # forward index returns (targets only)
        for h in (5, 15, 30):
            jh = min(len(S) - 1, i + 12 * h); f[f"fw{h}"] = S[jh] / S[i] - 1 if m[jh] - m[i] >= h - 1 else np.nan
        rows.append(f)
    return pd.DataFrame(rows)


FK = f"{C}/feats.pkl"
if not os.path.exists(FK): pd.concat([feats(k) for k in KEYS]).to_pickle(FK)
F = pd.read_pickle(FK).reset_index(drop=True); F["sym"] = F.k.str[0]; F["day"] = F.k.str[1]
_K = lambda iid: float(iid.split(":")[3]) if iid else np.nan
# ATM strike roll over the last 15 min (+1 up, -1 down, 0 none): known at decision time
F["roll"] = np.sign([_K(P[k]["R"][("ATM", "CE")][i]) - _K(P[k]["R"][("ATM", "CE")][max(0, i - 180)]) for k, i in zip(F.k, F.i)])
F["oi_conf"] = np.where(np.sign(F.oi_flow) == F.roll, F.oi_flow, 0.0)
FEATS = ["r5", "r15", "imb", "basis", "dbasis", "doi_ce", "doi_pe", "oi_flow", "div", "dstrad", "build", "sprd", "rv_iv"]
TRIED = 0


def ic_table():
    global TRIED
    rows = []
    for f in FEATS:
        for h in (5, 15, 30):
            ics = F.dropna(subset=[f, f"fw{h}"]).groupby("k").apply(lambda g: g[f].corr(g[f"fw{h}"], method="spearman") if len(g) > 30 else np.nan).dropna()
            if len(ics) < 4: continue
            TRIED += 1
            d = ics.index.map(lambda k: k[1]); half = DAYS[len(DAYS) // 2]
            rows.append(dict(feat=f, h=h, n_sd=len(ics), ic=round(ics.mean(), 3), t=round(ics.mean() / ics.std() * np.sqrt(len(ics)), 2),
                             ic_early=round(ics[d < half].mean(), 3), ic_late=round(ics[d >= half].mean(), 3)))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- F2 walk-forward signal trades
def wf_signal(feat, h=15, q=0.8, cool=15, exit_kw=None, mind=3, rule="ITM200", syms=("NIFTY", "SENSEX"), m_lo=0, slip=0.0, need=None, sign=None):
    """for each day d (after `mind` training days): sign from prior-day mean IC, threshold = q-quantile of |feat|
    on prior days; trade ITM200 in the predicted direction when |feat|>thr, one position at a time (cooldown)."""
    exit_kw = exit_kw or dict(hold=h); ent = []
    for n, d in enumerate(DAYS):
        tr = F[F.day < d].dropna(subset=[feat, f"fw{h}"])
        if tr.day.nunique() < mind: continue
        ics = tr.groupby("k").apply(lambda g: g[feat].corr(g[f"fw{h}"], method="spearman")).dropna()
        sg = sign if sign is not None else np.sign(ics.mean()); thr = tr[feat].abs().quantile(q) if q > 0 else 0
        for k in [k for k in KEYS if k[1] == d and k[0] in syms]:
            g = F[(F.k == k)].dropna(subset=[feat]); nextok = 0; sl = slip * LOT[k[0]] * LOTS * 2
            for _, r in g.iterrows():
                if r.m < nextok or r.m > 900 or r.m < m_lo or abs(r[feat]) <= thr: continue
                if need is not None and not r[need]: continue
                side = "CE" if sg * np.sign(r[feat]) > 0 else "PE"
                t = trade(k, int(r.i), side, rule, **exit_kw); o = trade(k, int(r.i), "PE" if side == "CE" else "CE", rule, **exit_kw)
                if t: ent.append((k, t[0] - sl, (o[0] - sl) if o else t[0] - sl)); nextok = r.m + max(cool, t[1])
    return ent


def f1_straddle(entry_m=586, thr_q=None, hold=None, flat=915):
    """buy ATM CE + ATM PE at entry_m; exit both at flat (or hold min). thr_q: only if rv_iv > prior-days quantile."""
    ent = []; rows = []
    for k in KEYS:
        g = F[(F.k == k) & (F.m == entry_m)]
        if g.empty: continue
        r = g.iloc[0]
        if thr_q is not None:
            pr = F[(F.day < k[1]) & (F.m == entry_m)].rv_iv.dropna()
            if len(pr) < 3 or not (r.rv_iv > pr.quantile(thr_q)): continue
        a = trade(k, int(r.i), "CE", "ATM", hold=hold, flat=flat); b = trade(k, int(r.i), "PE", "ATM", hold=hold, flat=flat)
        if a and b: ent.append((k, a[0] + b[0])); rows.append(dict(k=k, rv_iv=r.rv_iv, pnl=a[0] + b[0]))
    return ent, pd.DataFrame(rows)


def straddle_pool(entry_lo=946, entry_hi=1200, flat=915):
    key = f"{C}/spool_{entry_lo}_{flat}.pkl"
    if os.path.exists(key): return pickle.load(open(key, "rb"))
    out = {}
    for k in KEYS:
        rows = []
        for i in minute_idx(k, 560, 900):
            a = trade(k, i, "CE", "ATM", hold=None, flat=flat); b = trade(k, i, "PE", "ATM", hold=None, flat=flat)
            if a and b: rows.append((i, "X", a[0] + b[0]))
        out[k] = rows
    pickle.dump(out, open(key, "wb")); return out


if __name__ == "__main__":
    print("sym-days:", len(KEYS), "days:", len(DAYS), DAYS)
    # ---- F1: implied vs realized, straddle buys
    print("\n== F1 vol timing ==")
    tm = F[F.m == 586][["k", "S", "strad", "iv1m", "rv_iv"]].copy()
    print("rv/iv at 09:46 per sym-day (median):", round(tm.rv_iv.median(), 2))
    ratio = F.groupby("k").apply(lambda g: pd.Series(dict(rv_iv_med=g.rv_iv.median())))
    print(ratio.round(2).to_string())
    sp = straddle_pool()
    res = []
    e, df = f1_straddle(586); res.append(stats("F1a straddle 09:46->15:15 all", e, sp))
    for q in (0.5,):
        e, df = f1_straddle(586, thr_q=q); res.append(stats(f"F1b straddle 09:46 if rv/iv>prior q{q}", e, sp))
    # intraday: buy straddle when rv/iv > prior-day 80th pct, hold 30 min, cooldown 30
    for thr in (0.8, 0.9):
        ent = []
        for k in KEYS:
            pr = F[F.day < k[1]].rv_iv.dropna()
            if F[F.day < k[1]].day.nunique() < 3: continue
            t0 = pr.quantile(thr); nxt_ok = 0
            for _, r in F[F.k == k].iterrows():
                if r.m < nxt_ok or r.m > 885 or not (r.rv_iv > t0): continue
                a = trade(k, int(r.i), "CE", "ATM", hold=30); b = trade(k, int(r.i), "PE", "ATM", hold=30)
                if a and b: ent.append((k, a[0] + b[0])); nxt_ok = r.m + 30
        res.append(stats(f"F1c straddle when rv/iv>q{thr} hold30", ent, None))
        pl30 = {}
        for k in KEYS:
            rows = []
            for i in minute_idx(k, 560, 886)[::3]:
                a = trade(k, i, "CE", "ATM", hold=30); b = trade(k, i, "PE", "ATM", hold=30)
                if a and b: rows.append((i, "X", a[0] + b[0]))
            pl30[k] = rows
        pt = placebo(ent, pl30); v = sum(p for _, p in ent); res[-1].update(pct=round((pt < v).mean() * 100, 1), p=round((pt >= v).mean(), 3), plac_med=round(np.median(pt)))
    show(res)

    # ---- F2: IC table
    print("\n== F2 IC (spearman, per sym-day, vs fwd index return) ==")
    ic = ic_table(); print(ic.sort_values("t", key=abs, ascending=False).to_string(index=False))
    print("IC variants tried:", TRIED)
    pl15 = pool(dict(hold=15))
    rows = []
    for f in ["imb", "oi_flow", "div", "r15", "dbasis", "dstrad"]:
        rows.append(stats(f"F2 {f} wf q0.8 hold15", wf_signal(f, 15), pl15))
    df2 = show(rows)

    # ---- F2 robustness of the best signal (same walk-forward rule, one knob at a time)
    print("\n== F2 robustness: oi_flow ==")
    rob = [("base ITM200 hold15", {}), ("ATM strike", dict(rule="ATM")), ("ITM100 strike", dict(rule="ITM100")),
           ("NIFTY only", dict(syms=("NIFTY",))), ("SENSEX only", dict(syms=("SENSEX",))), ("after 10:00", dict(m_lo=600)),
("+1 extra tick slip each side", dict(slip=0.05)),
           ("+1 point slip each side", dict(slip=1.0)), ("q0.7", dict(q=0.7)), ("q0.9", dict(q=0.9)), ("hold5", dict(exit_kw=dict(hold=5))),
           ("hold30", dict(exit_kw=dict(hold=30)))]
    show([stats(f"oi_flow {nm}", wf_signal("oi_flow", 15, **kw), pl15) for nm, kw in rob])

    print("\n== F2 controls: is oi_flow just momentum? ==")
    show([stats("C1 r15 momentum (sign forced +) q0.8", wf_signal("r15", 15, sign=1), pl15),
          stats("C2 roll momentum (every ATM roll, buy roll dir)", wf_signal("roll", 15, q=0, sign=1), pl15),
          stats("C3 oi_flow only if it agrees with roll", wf_signal("oi_conf", 15, q=0.8), pl15),
          stats("C4 oi_flow when NO roll", wf_signal("oi_flow", 15, need="noroll"), pl15)])

    # ---- F3 exits on SAME entries: all-minute random pool and best F2 signal
    print("\n== F3 exits (same entries) ==")
    EX = {"time15": dict(hold=15), "time30": dict(hold=30), "time60": dict(hold=60), "eod": dict(hold=None),
          "sl10_tp20_60": dict(hold=60, stop=.10, tgt=.20), "sl05_tp10_30": dict(hold=30, stop=.05, tgt=.10),
          "sl15_tp30_eod": dict(hold=None, stop=.15, tgt=.30), "trail08_60": dict(hold=60, trail=.08),
          "trail15_eod": dict(hold=None, trail=.15), "atr1_60": dict(hold=60, atr_k=1.0), "atr2_tp_eod": dict(hold=None, atr_k=2.0, tgt=.3)}
    best = df2.sort_values("tot").iloc[-1]["name"].split()[1]
    rows = []
    for nm, kw in EX.items():
        pl = pool(kw)
        allv = [r[2] for k in KEYS for r in pl[k]]
        e = wf_signal(best, 15, exit_kw=kw)
        r = stats(f"F3 {best}+{nm}", e, pl); r["rand_avg_all"] = round(np.mean(allv)); rows.append(r)
    show(rows)

    # ---- F4: walk-forward ridge on all features, by day
    print("\n== F4 walk-forward ridge (exploratory) ==")
    X = ["r5", "r15", "imb", "dbasis", "oi_flow", "div", "dstrad", "sprd", "rv_iv"]
    G = F.copy(); G[X] = G[X].fillna(0)
    ent = []
    for d in DAYS:
        tr = G[(G.day < d)].dropna(subset=["fw15"])
        if tr.day.nunique() < 4: continue
        mu, sd = tr[X].mean(), tr[X].std() + 1e-12
        A = ((tr[X] - mu) / sd).values; y = tr.fw15.values / tr.fw15.std()
        w = np.linalg.solve(A.T @ A + 100 * np.eye(len(X)), A.T @ y)
        thr = np.quantile(np.abs(A @ w), 0.8)
        for k in [k for k in KEYS if k[1] == d]:
            g = G[G.k == k]; nextok = 0
            for _, r in g.iterrows():
                s = (((r[X] - mu) / sd).values.astype(float)) @ w
                if r.m < nextok or r.m > 900 or abs(s) <= thr: continue
                t = trade(k, int(r.i), "CE" if s > 0 else "PE", hold=15); o = trade(k, int(r.i), "PE" if s > 0 else "CE", hold=15)
                if t: ent.append((k, t[0], o[0] if o else t[0])); nextok = r.m + 15
    show([stats("F4 ridge wf q0.8 hold15", ent, pl15)])

    # per-day for the best F2 signal
    e = wf_signal(best, 15)
    print("\nper-day", best)
    print(pd.DataFrame([x[:2] for x in e], columns=["k", "pnl"]).groupby("k").pnl.agg(["count", "sum"]).round(0).to_string())
