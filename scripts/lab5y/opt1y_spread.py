"""Measure real option half-spreads from the 13-day tick tape cache (tape_cache.py depth_opts output) for the
round-2 bar backtest (bars have no bid/ask). Half-spread = (ask-bid)/2 at each 5s depth bucket, valid quotes only.
Buckets: sym, premium (mid), time of day, expiry-day flag; moneyness reported for audit.
Run: ~/paper_extra_venv/bin/python scripts/lab5y/opt1y_spread.py TAPE_CACHE_DIR OUTDIR -> OUTDIR/spreads.csv"""
import sys, glob, os, numpy as np, pandas as pd
C, OUT = sys.argv[1], sys.argv[2]
SKIP = {"2026-09-28", "2026-10-06"}
PB = [0, 20, 50, 100, 200, 400, 1e9]; TB = [0, 570, 660, 840, 900, 931]
STEP = {"NIFTY": 50, "SENSEX": 100}

def pbucket(p): return np.digitize(p, PB[1:-1])
def tbucket(m): return np.digitize(m, TB[1:-1])

if __name__ == "__main__":
    rows = []
    for f in sorted(glob.glob(f"{C}/*_o.parquet")):
        day = os.path.basename(f)[:10]
        if day in SKIP: continue
        o = pd.read_parquet(f); u = pd.read_parquet(f"{C}/{day}_u.parquet")
        o = o[(o.bid > 0) & (o.ask >= o.bid)]
        p = o.iid.str.split(":", expand=True); o = o.assign(sym=p[1], exp=p[2], K=p[3].astype(float), side=p[4])
        o = o[o.exp == o.groupby("sym").exp.transform("min")]  # nearest weekly only, like the bar data
        for sym, g in o.groupby("sym"):
            s = u[u.iid == ("NSE_IDX:" if sym == "NIFTY" else "BSE_IDX:") + sym][["ts", "ltp"]].dropna().sort_values("ts")
            g = pd.merge_asof(g.sort_values("ts"), s, on="ts", direction="backward").dropna(subset=["ltp"])
            mny = np.where(g.side == "CE", g.K - g.ltp, g.ltp - g.K) / STEP[sym]
            g = g.assign(mny=np.clip(np.round(mny), -4, 4), mid=(g.bid + g.ask) / 2, hs=(g.ask - g.bid) / 2,
                         m=g.ts.dt.hour * 60 + g.ts.dt.minute, dte0=int(g.exp.iloc[0] == day), day=day)
            rows.append(g[["day", "sym", "side", "mny", "mid", "hs", "m", "dte0"]])
    A = pd.concat(rows); A = A[(A.m >= 555) & (A.m < 930) & (A.hs < 0.25 * A.mid + 5)]
    A["pb"], A["tb"] = pbucket(A.mid), tbucket(A.m)
    q = lambda x: x.quantile(0.75)
    T = A.groupby(["sym", "pb", "tb", "dte0"]).hs.agg(["count", "median", q]).rename(columns={"<lambda_0>": "p75"}).reset_index()
    T.to_csv(f"{OUT}/spreads.csv", index=False)
    pd.set_option("display.width", 200)
    print("days", A.day.nunique(), "rows", len(A))
    print(A.groupby(["sym", "pb"]).hs.agg(["count", "median", q]).round(2))
    print(A[A.mny.abs() <= 3].groupby(["sym", "mny"]).hs.agg(["median", q]).round(2).unstack(0))
    print(A.groupby(["sym", "tb"]).hs.agg(["median", q]).round(2).unstack(0))
    print(A.groupby(["sym", "dte0"]).hs.agg(["median", q]).round(2).unstack(0))
    print("half-spread as % of mid, median:", A.assign(r=A.hs / A.mid).groupby(["sym", "pb"]).r.median().round(4).to_dict())
