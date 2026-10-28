"""Round 4: defined-risk option SELLING on the round-2 panel (paper research; no orders).
Run:  ~/paper_extra_venv/bin/python scripts/lab5y/sell_lab.py OUT [grid|selftest] [--holdout]   (run from scripts/lab5y)
Reuses opt1y_lab (panel, half-spreads, costs x1.5, 10 lots, dev < 2026-07-27, holdout once).

Position = legs (side, strike offset in steps from ATM at bar i, sign -1 short / +1 long), entered at the open of bar i+1:
short legs sell at open - half-spread, long legs buy at open + half-spread. Every minute the position is marked at the
1m close; exits (stop / target / spot move) are decided on that close and filled at the NEXT open with half-spreads;
otherwise flat at 15:15 open. Intraday only (no overnight gap risk).
A leg with no quote has left the taped ATM+-3 window (Dhan rollingoption rejects ATM+-4..10 for expiryCode=1, checked
2026-10-28: 728/728 calls refused), so it is further from ATM than every taped strike. Its price is bounded:
  low = intrinsic, high = intrinsic + the smallest extrinsic among taped strikes of that type at that minute.
mode="cons" values shorts at high and longs at low (a rule must pass this); mode="opt" is the reverse.
A short structure's buy-back value is then clamped to [0, widest wing], the hard max loss of an iron fly / condor."""
import sys, numpy as np, pandas as pd
import opt1y_lab as L

P, STEP, LOT, LOTS, M0, NB, FLAT = L.P, L.STEP, L.LOT, L.LOTS, L.M0, L.NB, L.FLAT


_EXT = {}
def _minext(k, side, j, col):
    key = (k, side, j, col)
    if key not in _EXT:
        s = P[k]["spot"][j]; xs = [a[j, col] - (max(0.0, s - K) if side == "CE" else max(0.0, K - s))
                                   for (sd, K), a in P[k]["C"].items() if sd == side and np.isfinite(a[j, col])]
        _EXT[key] = max(0.0, min(xs)) if xs else 0.0
    return _EXT[key]


def _px(k, side, K, j, col, high):
    """quote, or a bound when the strike is off the taped window: high=True -> upper bound, else lower bound."""
    a = P[k]["C"].get((side, K)); j = min(j, NB - 1); s = P[k]["spot"][j]
    v = a[j, col] if a is not None else np.nan
    if np.isfinite(v): return v, False
    intr = max(0.0, s - K) if side == "CE" else max(0.0, K - s)
    return intr + (_minext(k, side, j, col) if high else 0.0), True


def struct(k, i, legs, stop=None, tgt=None, sstop=None, flat=FLAT, mode="cons"):
    """legs: [(side, off, sign)]. stop: exit when buy-back value - credit >= stop * credit. tgt: exit when value <= (1-tgt) * credit.
    sstop: exit when |spot - entry spot| >= sstop * STEP. Returns dict or None."""
    sym = k[0]; p = P[k]; d0 = p["d0"]; e = i + 1; xe = flat - M0
    if e >= xe: return None
    atm = p["atm"][i]; L_ = [(sd, atm + off * STEP[sym], sg) for sd, off, sg in legs]
    ent = []
    for sd, K, sg in L_:
        a = p["C"].get((sd, K))
        if a is None or not np.isfinite(a[e, 0]): return None
        o = a[e, 0]; h = L.hs(sym, d0, M0 + e, o); ent.append(o - h if sg < 0 else o + h)
    credit = sum(-sg * x for (sd, K, sg), x in zip(L_, ent))
    if credit <= 0 and all(sg < 0 for _, _, sg in L_): return None
    shorts = [K for sd, K, sg in L_ if sg < 0]; longs = [(sd, K) for sd, K, sg in L_ if sg > 0]
    W = max(abs(K - min(shorts, key=lambda s: abs(s - K))) for sd, K in longs) if shorts and longs else np.inf
    s0 = p["spot"][e]; hi = lambda sg: (sg < 0) == (mode == "cons")  # cons: shorts high, longs low
    why = "time"; jx = xe; forced = False
    for j in range(e, xe):
        val = 0.0
        for sd, K, sg in L_:
            v, miss = _px(k, sd, K, j, 3, hi(sg)); val += -sg * v
        if np.isfinite(W): val = min(max(val, 0.0), W)
        if stop is not None and val - credit >= stop * credit: why, jx = "stop", j + 1; break
        if tgt is not None and val <= (1 - tgt) * credit: why, jx = "tgt", j + 1; break
        if sstop is not None and abs(p["spot"][j] - s0) >= sstop * STEP[sym]: why, jx = "spot", j + 1; break
    jx = min(jx, NB - 1); out = 0.0; costs = 0.0; q = LOT[sym] * LOTS
    for (sd, K, sg), x in zip(L_, ent):
        v, miss = _px(k, sd, K, jx, 0, hi(sg)); forced = forced or miss
        fill = v + L.hs(sym, d0, M0 + jx, max(v, 0.05)) if sg < 0 else max(v - L.hs(sym, d0, M0 + jx, max(v, 0.05)), 0.05)
        out += -sg * fill
        costs += L.cost(fill, x, sym) if sg < 0 else L.cost(x, fill, sym)
    if forced and np.isfinite(W): out = min(max(out, 0.0), W)  # a bound was used: keep it inside the payoff's limits
    pnl = (credit - out) * q - costs
    return dict(sym=sym, day=k[1], i=i, dte=p["dte"], d0=d0, credit=credit, pnl=pnl, why=why, held=jx - e, forced=forced,
                maxloss=(W - credit) * q if np.isfinite(W) else np.nan)


# ---------------------------------------------------------------- structures (offsets in strike steps)
def ifly(w): return [("CE", 0, -1), ("PE", 0, -1), ("CE", w, 1), ("PE", -w, 1)]
def icon(s, w): return [("CE", s, -1), ("PE", -s, -1), ("CE", w, 1), ("PE", -w, 1)]
SSTRAD = [("CE", 0, -1), ("PE", 0, -1)]; LSTRAD = [("CE", 0, 1), ("PE", 0, 1)]
STRUCTS = {"short_strad": SSTRAD, "ifly3": ifly(3), "long_strad": LSTRAD}
ENTRY = {"09:20": 5, "09:46": 31, "10:30": 75, "11:30": 135, "13:00": 225, "14:00": 285}
# spot stops <= 2.5 steps keep ATM legs inside the taped +-3 window (no bounds needed for straddles)
EXITS = {f"spot{s}": dict(sstop=s) for s in (1, 1.5, 2, 2.5)}
EXITS.update({f"spot2_stop{x}": dict(sstop=2, stop=x) for x in (0.3, 0.6)})
EXITS.update({f"spot2_tgt{x}": dict(sstop=2, tgt=x) for x in (0.3, 0.5)})


def run(keys, legs, i, ex, mode="cons"):
    R = [struct(k, i, legs, mode=mode, **ex) for k in keys]; return pd.DataFrame([r for r in R if r])


def summ(D):
    if not len(D): return dict(n=0)
    g = D.groupby("day").pnl.sum(); mo = D.groupby(D.day.map(L.month)).pnl.sum()
    t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 2 else np.nan
    b = np.random.default_rng(5).choice(g.values, (5000, len(g))).mean(1)
    return dict(n=len(D), win=round((D.pnl > 0).mean() * 100), avg=round(D.pnl.mean()), total=round(D.pnl.sum()),
                worst=round(D.pnl.min()), maxdd=round((g.cumsum() - g.cumsum().cummax()).min()), t=round(t, 2),
                p_boot=round((b <= 0).mean(), 4), mpos=f"{(mo > 0).sum()}/{len(mo)}",
                NIFTY=round(D[D.sym == "NIFTY"].pnl.sum()), SENSEX=round(D[D.sym == "SENSEX"].pnl.sum()),
                ret_ml=round(D.pnl.sum() / D.maxloss.mean() * 100, 1), forced=round(D.forced.mean() * 100, 1))


def study_grid():
    """every structure x entry x exit on dev, all days. The point is the SURFACE (robust region), not the max cell."""
    rows = []
    for sn, legs in STRUCTS.items():
        for en, i in ENTRY.items():
            for xn, ex in EXITS.items():
                if sn == "long_strad" and ("stop" in xn or "tgt" in xn): continue  # credit-based exits are for sellers
                D = run(L.KEYS, legs, i, ex); r = dict(struct=sn, entry=en, exit=xn, **summ(D)); rows.append(r)
                print(r, flush=True)
    R = pd.DataFrame(rows); R.to_csv(f"{L.OUT}/sell_grid_{'ho' if L.HOLDOUT else 'dev'}.csv", index=False)
    pd.set_option("display.width", 250); print(R.to_string(index=False))


def study_selftest():
    """synthetic day: flat option prices except a 2-step spot jump at bar 100 -> spot exit at bar 101 open."""
    k = ("NIFTY", "1999-01-01"); spot = np.full(NB, 20000.0); spot[100:] = 20100.0
    C = {}
    for sd in ("CE", "PE"):
        for off in range(-3, 4):
            a = np.full((NB, 7), np.nan); a[:, :4] = 50.0 if off == 0 else 20.0; C[(sd, 20000.0 + off * 50)] = a
    C[("CE", 20000.0)][101:, :4] = 120.0; C[("PE", 20000.0)][101:, :4] = 10.0
    P[k] = dict(spot=spot, atm=np.full(NB, 20000.0), C=C, exp="1999-01-01", dte=0, d0=1)
    h = lambda m, v: L.hs("NIFTY", 1, M0 + m, v)
    r = struct(k, 31, SSTRAD, sstop=2)
    e1, x1, x2 = 50 - h(32, 50), 120 + h(101, 120), 10 + h(101, 10)
    exp = (2 * e1 - x1 - x2) * 650 - L.cost(x1, e1, "NIFTY") - L.cost(x2, e1, "NIFTY")
    assert r["why"] == "spot" and r["held"] == 69 and abs(r["pnl"] - exp) < 1e-6, (r, exp)
    del C[("PE", 20000.0 - 150)]  # a wing off the tape: cons values it at intrinsic (0), opt at the smallest taped extrinsic
    rc, ro = struct(k, 31, ifly(3), mode="cons"), struct(k, 31, ifly(3), mode="opt")
    assert rc is None and ro is None  # cannot enter a leg with no quote
    del P[k]; print("sell_lab selftest OK")


if __name__ == "__main__":
    for s in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + s]()
