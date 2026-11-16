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


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
