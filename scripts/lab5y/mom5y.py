"""5y check of the tape-round winner (15-min momentum, |r15| > causal 80th pct of prior 10 days, hold 15 min,
one trade at a time) on Dhan index 1m, using lab.py's cost model (RT 0.0133% + theta). Question: are the
13 tape days (2026-09-29..10-22) a typical 13-day window, or a lucky momentum regime?
Run: LAB5Y_CACHE=<dir> ~/paper_extra_venv/bin/python scripts/lab5y/mom5y.py"""
import os, sys, numpy as np, pandas as pd
sys.argv = sys.argv[:1]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab as L

rows = []
for sym in ("NIFTY", "SENSEX"):
    ks = [k for k in L.KEYS if k[0] == sym]; hist = []
    for k in ks:
        m, o, h, l, c = L.DAYS[k]
        r15 = np.full(len(m), np.nan); r15[16:] = c[15:-1] / c[:-16] - 1   # known at open of bar j
        thr = np.quantile(np.abs(np.concatenate(hist[-10:])), 0.8) if len(hist) >= 5 else None
        hist.append(r15[np.isfinite(r15)])
        if thr is None: continue
        nxt = 0
        for j in range(16, len(m)):
            if m[j] < 570 or m[j] > 900 or m[j] < nxt or not abs(r15[j]) > thr: continue
            t = L.trade(k, j, 1 if r15[j] > 0 else -1, exit_m=m[j] + 15)
            if t: rows.append((sym, k[1], t[0])); nxt = m[j] + 15
D = pd.DataFrame(rows, columns=["sym", "day", "r"])
D["yr"] = D.day.str[:4]
print(D.groupby(["sym", "yr"]).r.agg(n="size", avg_bps=lambda x: x.mean() * 1e4, t=lambda x: x.mean() / x.std() * np.sqrt(len(x))).round(2))
for sym in ("NIFTY", "SENSEX"):
    d = D[D.sym == sym].groupby("day").r.sum()
    w = d.rolling(13).sum().dropna()
    print(sym, "days", len(d), "13-day windows: median %.2f%%  share>0 %.2f  p90 %.2f%%" % (w.median() * 100, (w > 0).mean(), w.quantile(.9) * 100))
