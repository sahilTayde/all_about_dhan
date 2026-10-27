"""5y index check of the 15-min fade found in round 2: at a decision minute 09:20..14:59, if |r15| > threshold, trade
AGAINST the 15-min move; enter next 1m open, exit the open `hold` bars later (<=15:15), one trade at a time.
Threshold = 80th pct of |r15| (decision minutes only) over the previous 6 months, refit monthly (same as opt1y_lab WF).
Reports GROSS index bps per trade (no costs) by year, t-stat on day sums. Same code on the 1y option-data spot (dev
months only, < 2026-07-27, so the holdout stays unseen).
Run: ~/paper_extra_venv/bin/python scripts/lab5y/fade5y.py IDX1M_PKL OPT1Y_PARQUET"""
import sys, numpy as np, pandas as pd

HO = "2026-07-27"


def r15_table(D):
    D = D.sort_values(["sym", "day", "m"]).copy()
    D["r15"] = D.groupby(["sym", "day"]).close.transform(lambda c: c / c.shift(15) - 1)
    D["mo"] = D.day.str[:7]; return D


def run(D, hold=30, q=0.8, look=6):
    D = r15_table(D); dec = D[(D.m >= 560) & (D.m <= 899)]
    mos = sorted(D.mo.unique()); out = []
    for n, mo in enumerate(mos):
        if n < look: continue
        tr = dec[dec.mo.isin(mos[n - look:n])]
        thr = tr.groupby("sym").r15.apply(lambda x: x.abs().quantile(q)).to_dict()
        for (sym, day), g in D[D.mo == mo].groupby(["sym", "day"]):
            if len(g) < 300: continue
            m, o, r = g.m.values, g.open.values, g.r15.values; busy = -1; jf = int(np.searchsorted(m, 900))
            for i in range(15, len(m) - 1):
                if m[i] < 560 or m[i] > 899 or i <= busy or not abs(r[i]) > thr[sym]: continue
                j = min(i + 1 + hold, jf, len(m) - 1)
                if j <= i + 1: continue
                out.append((sym, day, -np.sign(r[i]) * (o[j] / o[i + 1] - 1) * 1e4)); busy = j - 1
    return pd.DataFrame(out, columns=["sym", "day", "bps"])


if __name__ == "__main__":
    D = pd.read_pickle(sys.argv[1]); D = D[D.sym.isin(["NIFTY", "SENSEX"])]
    X = pd.read_parquet(sys.argv[2], columns=["sym", "side", "off", "day", "m", "spot"])
    X = X[(X.side == "CE") & (X.off == 0) & (X.day < HO)].rename(columns={"spot": "close"}).sort_values(["sym", "day", "m"])
    X["open"] = X.groupby(["sym", "day"]).close.shift(1); X = X.dropna()
    # option-spot series needs 6 months of history for the threshold: prepend index 1m before 2025-10-27
    X = pd.concat([D[D.day < "2025-10-27"][["sym", "day", "m", "open", "close"]], X[["sym", "day", "m", "open", "close"]]])
    for hold in (15, 30, 60):
        print(f"hold {hold}: fade gross index bps/trade (t on day sums)")
        for nm, src, lo, hi in (("5y index", D, "2000", "2099"), ("1y option spot, dev", X, "2025-11", HO)):
            R = run(src, hold); R = R[(R.day >= lo) & (R.day < hi)]; R["y"] = R.day.str[:4] if nm == "5y index" else "dev"
            for (y, s), g in R.groupby(["y", "sym"]):
                dm = g.groupby("day").bps.sum()
                print(f"  {nm} {y} {s}: n {len(g)} mean {g.bps.mean():+.2f} bps  t_day {dm.mean() / dm.std() * np.sqrt(len(dm)):+.2f}")
