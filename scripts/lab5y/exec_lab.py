"""E23 (frozen in the registry before results): measured execution on the live depth tape. Paper research only; reads
data/tape/v2/<day>/depth_quotes.jsonl, no broker calls.
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python exec_lab.py OUT panel     # 1-second panels, cached per day
                           ~/paper_extra_venv/bin/python exec_lab.py OUT measure   # policies -> OUT/exec_rows.parquet + table
                           ~/paper_extra_venv/bin/python exec_lab.py OUT selftest  # known-answer check (synthetic book)
Panel: per option instrument and second: last bid/ask, max bid, min ask, and NEW trades only (an LTP that differs from
the previous LTP of that instrument): min/max/first new-trade price. Index spot = last LTP per second.
Fill rule (no queue model, conservative): a resting BUY at P is filled at P in the first second s >= t+1 with min ask <= P
or a new trade strictly below P (SELL: max bid >= P or a new trade strictly above P). 'touch' (new trade at P) is reported
as an optimistic bound only. Unfilled at the timeout -> cross at the as-of opposite quote of second t+T."""
import json, os, sys, math
from multiprocessing import Pool
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TAPE = f"{HERE}/../../data/tape/v2"
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
EST_DAYS = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22"]
T0 = 9 * 3600 + 15 * 60; NS = 6 * 3600 + 15 * 60  # seconds 09:15:00 .. 15:30:00
STEP = {"NIFTY": 50, "SENSEX": 100}; TICK = 0.05; STALE = 5
TS = (30,)  # frozen: only M30 is eligible (Fable review); X is the paired reference
QTY = {"NIFTY": 650, "SENSEX": 200}  # 10 lots


def vwap(lv, q):
    """average price to take q from 5 levels [[px, qty], ...]; beyond level 5 the rest is priced at the worst level."""
    if not lv: return np.nan
    left, val = q, 0.0
    for px, qt in lv:
        take = min(left, qt); val += take * px; left -= take
        if left <= 0: break
    return (val + left * lv[-1][0]) / q


def _sec(ts): return int(ts[11:13]) * 3600 + int(ts[14:16]) * 60 + int(ts[17:19]) - T0


COLS = "iid s bid ask bmax amin tmin tmax tfirst vask vbid".split()


def build_panel(day):
    out = f"{OUT}/{day}_x.parquet"
    if os.path.exists(out): return day
    last_ltp, R, spot = {}, {}, {}
    with open(f"{TAPE}/{day}/depth_quotes.jsonl") as f:
        for ln in f:
            i = ln.find('"instrument_id":"'); j = ln.find('"', i + 17); iid = ln[i + 17:j]
            opt = iid.count(":") == 4
            if not opt and "_IDX:" not in iid: continue
            p = json.loads(ln)["payload"]; ts = p.get("exchange_ts") or ""
            if not ts.startswith("2"): continue
            s = _sec(ts)
            if not 0 <= s < NS: continue
            ltp = p.get("ltp")
            if not opt:
                if ltp: spot[(iid.split(":")[1], s)] = ltp
                continue
            new = ltp if (ltp and last_ltp.get(iid) not in (None, ltp)) else None
            if ltp: last_ltp[iid] = ltp
            b, a = p.get("bid") or np.nan, p.get("ask") or np.nan
            lv = p.get("levels") or {}; q = QTY[iid.split(":")[1]]
            va, vb = vwap(lv.get("ask"), q), vwap(lv.get("bid"), q)
            r = R.get((iid, s))
            if r is None: R[(iid, s)] = [b, a, b, a, new, new, new, va, vb]
            else:
                r[0], r[1] = b, a; r[2] = np.fmax(r[2], b); r[3] = np.fmin(r[3], a); r[7], r[8] = va, vb
                if new is not None:
                    r[4] = new if r[4] is None else min(r[4], new); r[5] = new if r[5] is None else max(r[5], new)
                    r[6] = new if r[6] is None else r[6]
    df = pd.DataFrame([(k[0], k[1], *v) for k, v in R.items()], columns=COLS)
    for c in COLS[2:]: df[c] = pd.to_numeric(df[c], errors="coerce")
    V = {}
    with open(f"{TAPE}/{day}/quote_snapshots.jsonl") as f:
        for ln in f:
            if '"volume":null' in ln or ':IDX' in ln: continue
            e = json.loads(ln); p = e["payload"]; sv = _sec(e["timestamp"])
            if p.get("volume") and 0 <= sv < NS: V[(p["instrument_id"], sv)] = p["volume"]
    pd.DataFrame([(k[0], k[1], v) for k, v in V.items()], columns="iid s vol".split()).to_parquet(f"{OUT}/{day}_xv.parquet")
    df.to_parquet(out)
    pd.DataFrame([(k[0], k[1], v) for k, v in spot.items()], columns="sym s spot".split()).to_parquet(f"{OUT}/{day}_xs.parquet")
    return day


# ---------------------------------------------------------------- policies on dense per-second arrays of one instrument
def dense(g, v=None, qty=0):
    """g: panel rows of one instrument -> dict of arrays length NS. bid/ask/vwap as-of (<= STALE s old), events NaN-filled.
    v: (seconds, cumulative volume) from quote_snapshots, as-of without limit; None -> volume never confirms a passive fill."""
    A = {c: np.full(NS, np.nan) for c in COLS[2:]}
    s = g.s.values
    for c in A: A[c][s] = g[c].values
    for c in ("bid", "ask", "vask", "vbid"):
        A[c] = pd.Series(A[c]).ffill(limit=STALE).values
    A["vol"] = np.full(NS, np.nan)
    if v is not None: A["vol"][v[0]] = v[1]; A["vol"] = pd.Series(A["vol"]).ffill().values
    A["qty"] = qty
    A["bad"] = ~((A["bid"] > 0) & (A["ask"] > A["bid"]))
    return A


def _cross(A, s, buy):
    """take full size from the book (5-level VWAP), as of second s."""
    v = A["vask"][s] if buy else A["vbid"][s]; return v if np.isfinite(v) else np.nan


def fill(A, t, buy, P, T, touch=False):
    """resting order at P from t+1 to t+T; returns (price, filled_passively, seconds to fill)."""
    for s in range(t + 1, min(t + T, NS - 1) + 1):
        if buy:
            hit = A["amin"][s] <= P or A["tmin"][s] < P or (touch and A["tmin"][s] <= P)
        else:
            hit = A["bmax"][s] >= P or A["tmax"][s] > P or (touch and A["tmax"][s] >= P)
        if hit and A["vol"][s] - A["vol"][t] >= A["qty"]: return P, True, s - t  # enough volume traded for our size
    return _cross(A, min(t + T, NS - 1), buy), False, T


def policies(A, t, buy):
    """per-leg results at decision second t (quote as of t). Sign: cost > 0 = worse than the decision mid."""
    if A["bad"][t]: return None
    b, a = A["bid"][t], A["ask"][t]; mid = (b + a) / 2; sg = 1 if buy else -1
    mp = math.ceil(mid / TICK - 1e-9) * TICK if buy else math.floor(mid / TICK + 1e-9) * TICK  # mid rounded against us
    res = {"X": (_cross(A, t + 1, buy), False, 1)}
    for T in TS:
        res[f"M{T}"] = fill(A, t, buy, mp, T)
        res[f"M{T}t"] = fill(A, t, buy, mp, T, touch=True)  # optimistic bound, report only
    out = {}
    for k, (px, ok, dt) in res.items():
        if not np.isfinite(px): return None
        mk = t + dt + 60
        mo = (A["bid"][mk] + A["ask"][mk]) / 2 if mk < NS and not A["bad"][mk] else np.nan
        out[k] = (sg * (px - mid), ok, dt, sg * (mo - px))
    return mid, (a - b) / 2, out


def selftest():
    """known answers on a synthetic book: bid 100 / ask 101 (qty 100 each level, 5 levels 1 apart), our qty 300."""
    n = 200; lv_a = [[101.0 + i, 100] for i in range(5)]
    g = pd.DataFrame(dict(s=np.arange(n), bid=100.0, ask=101.0, bmax=100.0, amin=101.0, tmin=np.nan, tmax=np.nan, tfirst=np.nan,
                          vask=vwap(lv_a, 300), vbid=vwap([[100.0 - i, 100] for i in range(5)], 300)))
    assert vwap(lv_a, 300) == 102.0 and vwap(lv_a, 600) == (101 + 102 + 103 + 104 + 105 + 105) * 100 / 600
    A = dense(g, (np.arange(0, n, 5), np.arange(0, n, 5) * 100.0), qty=300)   # 100 contracts traded per second
    m, hs, r = policies(A, 10, True)
    assert m == 100.5 and hs == 0.5 and r["X"][0] == 1.5                      # full-size cross walks the book: 102 - 100.5
    assert r["M30"][:3] == (1.5, False, 30)                                   # nothing through 100.5 -> cross at timeout
    A["tmin"][12] = 100.5; assert fill(A, 10, True, 100.5, 30)[1] is False    # a trade AT our price: queue, not a fill
    assert fill(A, 10, True, 100.5, 30, touch=True)[:3] == (102.0, False, 30)  # touch at s=12 but volume 200 < 300 then
    A["tmin"][20] = 100.45                                                    # through our price, volume +1000 by s=20
    m, hs, r = policies(A, 10, True)
    assert r["M30"][:3] == (0.0, True, 10)                                    # filled at mid: cost 0
    A2 = dense(g, None, qty=300); A2["tmin"][20] = 100.0
    assert fill(A2, 10, True, 100.5, 30)[1] is False                          # no volume data -> never a passive fill
    A["vbid"][41:] = 99.0; A["bid"][41:] = 99.5; A["ask"][41:] = 100.5        # SELL mirror: price falls away, no fill
    assert fill(A, 30, False, 101.0, 30) == (99.0, False, 30)                  # cross at timeout: 5-level VWAP of the bid
    print("exec_lab selftest OK")


WIN = {"entry": [9 * 3600 + 45 * 60 + 60 * i - T0 for i in range(5)],      # 09:45..09:49 minute boundaries
       "exit": [15 * 3600 + 11 * 60 + 60 * i - T0 for i in range(5)],      # 15:11..15:15
       "allday": list(range(5 * 60, 23 * 60 * 15 + 1, 300))[:71]}           # every 5 min 09:20..15:10 (diagnostic)


_SP = None
def eng_hs(sym, d0, t, mid):
    """the backtest engine's p75 half-spread (opt1y_lab.hs: spreads.csv by sym x premium x time bucket x expiry day)."""
    global _SP
    if _SP is None: _SP = pd.read_csv(os.environ.get("SPREADS", f"{HERE}/../../data/cache/lab1y/spreads.csv"))
    m = 555 + t // 60; pb = int(np.searchsorted([20, 50, 100, 200, 400], mid, "right")); tb = int(np.searchsorted([570, 660, 840, 900], m, "right"))
    g = _SP[(_SP.sym == sym) & (_SP.dte0 == int(d0)) & (_SP.pb == pb) & (_SP.tb == tb)]
    return float(g.p75.iloc[0]) if len(g) else np.nan


def measure_day(day):
    X = pd.read_parquet(f"{OUT}/{day}_x.parquet"); SP = pd.read_parquet(f"{OUT}/{day}_xs.parquet")
    V = pd.read_parquet(f"{OUT}/{day}_xv.parquet"); Vg = {k: g for k, g in V.groupby("iid")}
    parts = X.iid.str.split(":", expand=True); X = X.assign(sym=parts[1], exp=parts[2], K=parts[3].astype(float), side=parts[4])
    rows = []
    for sym, G in X.groupby("sym"):
        exp = min(e for e in G.exp.unique() if e >= day); G = G[G.exp == exp]
        sp = np.full(NS, np.nan); g = SP[SP.sym == sym]; sp[g.s.values] = g.spot.values; sp = pd.Series(sp).ffill().values
        cache = {}
        def arr(K, side):
            if (K, side) not in cache:
                gi = G[(G.K == K) & (G.side == side)]
                if not len(gi): cache[(K, side)] = None
                else:
                    iid = gi.iid.iloc[0]; v = Vg.get(iid)
                    cache[(K, side)] = dense(gi, None if v is None else (v.s.values, v.vol.values.astype(float)), QTY[sym])
            return cache[(K, side)]
        for win, ts in WIN.items():
            for t in ts:
                if not np.isfinite(sp[t]): continue
                K = round(sp[t] / STEP[sym]) * STEP[sym]
                mv = abs(sp[t] - sp[max(t - 60, 0)]) / STEP[sym]
                for buy in (True, False):
                    L = [arr(K, sd) for sd in ("CE", "PE")]
                    if any(a is None for a in L): continue
                    R = [policies(a, t, buy) for a in L]
                    if any(r is None for r in R): continue
                    u = t + 1; hq = sum((a["ask"][u] - a["bid"][u]) / 2 for a in L)        # quoted half-spreads at the fill second
                    sur = sum((a["vask"][u] - a["ask"][u]) if buy else (a["bid"][u] - a["vbid"][u]) for a in L)  # depth walk for full size
                    eng = sum(eng_hs(sym, day == exp, t, (a["bid"][u] + a["ask"][u]) / 2) for a in L)
                    for pol in R[0][2]:
                        c = [r[2][pol][0] for r in R]; ok = [r[2][pol][1] for r in R]; mk = [r[2][pol][3] for r in R]
                        rows.append(dict(day=day, sym=sym, win=win, t=t, buy=buy, pol=pol, mv1=mv, hs=R[0][1] + R[1][1],
                                         cost=sum(c), cost_fl=sum(max(x, 0.0) for x in c), nfill=sum(ok), legout=ok[0] != ok[1],
                                         markout=np.nanmean(mk), prem=R[0][0] + R[1][0], hq=hq, sur=sur, eng=eng))
    return pd.DataFrame(rows)


def tbound(x, q=0.975):
    """mean and upper one-sided 95% t-bound of a vector of day means."""
    from scipy import stats
    x = np.asarray(x, float); n = len(x); m = x.mean(); se = x.std(ddof=1) / np.sqrt(n)
    return m, m + stats.t.ppf(0.95, n - 1) * se, se


def measure(days, tag):
    with Pool(4) as p: D = pd.concat(p.map(measure_day, days))
    D["k"] = D.cost_fl / D.hs; D["k_raw"] = D.cost / D.hs
    D.to_parquet(f"{OUT}/exec_rows_{tag}.parquet")
    return D


def report(D):
    from scipy import stats
    pd.set_option("display.width", 220); out = []
    for (win, sym, buy), g in D[D.win != "allday"].groupby(["win", "sym", "buy"]):
        dm = g.groupby(["day", "pol"]).k.mean().unstack()
        mX, uX, _ = tbound(dm["X"]); mM, uM, _ = tbound(dm["M30"])
        d = dm["M30"] - dm["X"]; tt = stats.ttest_1samp(d, 0, alternative="less")
        gm = g[g.pol == "M30"]
        out.append(dict(win=win, sym=sym, side="BUY" if buy else "SELL", n=len(gm), days=len(dm), hs_rs=round(gm.hs.mean(), 2),
                        kX=round(mX, 3), kX_up=round(uX, 3), kM30=round(mM, 3), kM30_up=round(uM, 3),
                        kM30t=round(g[g.pol == "M30t"].groupby("day").k.mean().mean(), 3), p_M30_lt_X=round(tt.pvalue, 4),
                        fill2=round((gm.nfill == 2).mean(), 2), legout=round(gm.legout.mean(), 2),
                        markout=round(gm[gm.nfill > 0].markout.mean(), 2), adopt=bool(tt.pvalue < 0.05)))
    T = pd.DataFrame(out); print(T.to_string(index=False))
    A = D[(D.win == "allday") & D.pol.isin(["X", "M30"])].assign(fast=lambda x: x.mv1 >= 0.5)
    print("Engine check, policy X (cross at full size), per straddle in option points: engine p75 half-spreads vs measured quoted")
    print("half-spread + depth walk at the fill second; ratio = measured / engine, per-day mean and upper 95% t-bound")
    x = D[D.pol == "X"].assign(meas=lambda d: d.hq + d.sur)
    for (win, sym), g in x.groupby(["win", "sym"]):
        sm = g.groupby("day")[["meas", "eng"]].sum(); r = sm.meas / sm.eng
        m, u, _ = tbound(r)
        print(f"  {win:6s} {sym:6s} engine {g.eng.mean():.3f} quoted {g.hq.mean():.3f} walk {g.sur.mean():.3f} ratio {m:.2f} (up95 {u:.2f}) days {len(r)}")
    print("all-day diagnostic: mean k by |1m spot move| >= 0.5 step (fast) vs not")
    print(A.groupby(["sym", "pol", "fast"]).k.agg(["count", "mean"]).round(3).unstack(["pol", "fast"]).to_string())
    return T


if __name__ == "__main__":
    what = sys.argv[2] if len(sys.argv) > 2 else "selftest"
    if what == "selftest": selftest()
    elif what == "panel":
        days = sys.argv[3].split(",") if len(sys.argv) > 3 else EST_DAYS
        with Pool(4) as p:
            for d in p.imap_unordered(build_panel, days): print("panel", d, flush=True)
    elif what == "measure":
        T = report(measure(EST_DAYS, "est")); T.to_csv(f"{OUT}/exec_table_est.csv", index=False)
    elif what == "fresh":  # once, at the end: forward days 10-28, 10-29 (10-27 excluded: partial tape). Kill-only check.
        report(measure(["2026-10-28", "2026-10-29"], "fresh"))
