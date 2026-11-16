"""Spot-fix re-score of the expiry-day strangles + E38w defined-risk wings (paper research; no orders, no broker calls).
Frozen rules: registry rows E39 (spot fix, kill rule) and E38 (section E38w, frozen 2026-11-16 before any wing cell was priced).
Run (from scripts/lab5y):
  LAB_FULL=1 HO=2025-10-27 COSTS=dated ~/paper_extra_venv/bin/python wings_lab.py OUT [selftest|spotcheck|base|e38]
Books, expiry day only, OTM1 strangle (short CE ATM+1, short PE ATM-1), exits = spot 1.5 strikes / credit loss 30% / 15:15:
  XS  = every expiry day, decided at the 10:07 close, filled at the 10:08 open (fin1_shadow XS control)
  IVX = first 1-pt ATM-IV fall over 15 bars after 09:46 (the E42 cell IVS x EXPIRY=0)
  IVS = IVX on a calm open, or_iv <= 1.0042 (the E39 cell = the desk standard)
Fills as every frozen row: sell_lab.struct cons mode, next-minute open +- p75 half-spread, 10 lots, no fill on an untraded bar."""
import sys, os, numpy as np, pandas as pd
import opt1y_lab as L, sell_lab as S

P, M0, NB = L.P, L.M0, L.NB
STR1 = [("CE", 1, -1), ("PE", -1, -1)]; EX = dict(sstop=1.5, stop=0.3); XS_I = 52; CALM = 1.0042
WINGS = (3, 4); KILL = 1500.0; UNTRADED_MAX = 5.0
CELLS = [(b, w) for b in ("XS", "IVS") for w in WINGS]; ALPHA = 0.05 / len(CELLS)
WD = f"{L.OUT}/wings"


def dayboot_p(x, n=4000, seed=39):
    """one-sided p that the mean daily P&L is <= 0 (day bootstrap; same draw as playbook_lab._dayboot_p, kept here so the selftest stays light)."""
    x = np.asarray(x, float); return float((np.random.default_rng(seed).choice(x, (n, len(x))).mean(1) <= 0).mean()) if len(x) > 1 else np.nan


def entries():
    """{book: [(sym-day key, decision bar)]}, expiry days only. Nothing after the decision bar is read."""
    import sweep_lab as W
    orv = L.vol_days().set_index(["sym", "day"]).or_iv; E = dict(XS=[], IVX=[], IVS=[])
    for k in L.ALLK:
        if not P[k]["d0"]: continue
        E["XS"].append((k, XS_I))
        for i, _, _ in W.nd_iv(k, -1.0)[:1]:
            E["IVX"].append((k, i))
            if orv.get(k, np.nan) <= CALM: E["IVS"].append((k, i))
    return E


def price(ents, legs):
    """one row per entry; pnl NaN = no fill (a leg unquoted or untraded at the entry bar: sell_lab.struct refuses it)."""
    rows = []
    for k, i in ents:
        r = S.struct(k, i, legs, mode="cons", **EX)
        rows.append(dict(sym=k[0], day=k[1], i=i, pnl=r["pnl"] if r else np.nan, why=r["why"] if r else "nofill", forced=bool(r and r["forced"]),
                         credit=r["credit"] if r else np.nan, held=r["held"] if r else -1))
    return pd.DataFrame(rows)


def stats(T):
    T = T[T.pnl.notna()]
    if not len(T): return dict(n=0, win=np.nan, total=0, mean=np.nan, p=np.nan, worst=np.nan, maxdd=np.nan)
    g = T.groupby("day").pnl.sum(); c = g.cumsum()
    return dict(n=len(T), win=round((T.pnl > 0).mean() * 100, 1), total=round(T.pnl.sum()), mean=round(T.pnl.mean()), p=round(dayboot_p(g.values), 4),
                worst=round(T.pnl.min()), maxdd=round((c - c.cummax().clip(lower=0)).min()))


def splits(T, ho=None):
    ho = ho or L.HO; return dict(LEARN=stats(T[T.day < ho]), TEST=stats(T[T.day >= ho]), ALL=stats(T))


def untraded_pct(base, cell):
    """% of the naked book's trades where the wing cell has no clean wing quote: no fill at entry (a wing bar untraded or missing) or a
    bound-priced (forced) exit. The naked book's own forced exits are counted too (conservative)."""
    m = base.pnl.notna(); return float(((cell.pnl.isna() | cell.forced) & m).sum() / max(m.sum(), 1) * 100)


def verdict(b, c, untraded, alpha=ALPHA):
    """frozen E38w rule. b / c = splits() of the naked book / the wing cell."""
    if untraded > UNTRADED_MAX: return "INCONCLUSIVE"
    cut = all(c[s]["worst"] >= 0.5 * b[s]["worst"] and c[s]["maxdd"] >= 0.5 * b[s]["maxdd"] for s in ("LEARN", "ALL"))  # losses are negative
    ok = cut and c["LEARN"]["mean"] >= KILL and c["TEST"]["mean"] >= KILL and c["LEARN"]["p"] < alpha and c["TEST"]["p"] < 0.05
    return "PASS" if ok else "FAIL"


def _show(rows):
    R = pd.DataFrame(rows); pd.set_option("display.width", 300); print(R.to_string(index=False)); return R


def study_base():
    """step 1: the three naked books on this OUT's panel (run once per panel: OLD = median spot, NEW = index spot)."""
    os.makedirs(WD, exist_ok=True); E = entries(); rows = []
    for nm in ("IVS", "IVX", "XS"):
        T = price(E[nm], STR1); T.to_csv(f"{WD}/base_{nm}_{L.COSTS}.csv", index=False)
        for s, st in splits(T).items(): rows.append(dict(book=nm, split=s, **st, forced=round(T.forced.mean() * 100, 1), nofill=int(T.pnl.isna().sum()),
                                                         exits=T[T.pnl.notna() & ((T.day < L.HO) if s == "LEARN" else (T.day >= L.HO) if s == "TEST" else True)].why.value_counts().to_dict()))
    R = _show(rows); R.to_csv(f"{WD}/base_{L.COSTS}.csv", index=False)
    iv = R[(R.book == "IVS") & R.split.isin(["LEARN", "TEST"])].set_index("split")["mean"]
    print(f"kill rule (pre-set): IVS mean < {KILL:.0f}/trade on LEARN or TEST -> PARKED. LEARN {iv['LEARN']:+.0f}, TEST {iv['TEST']:+.0f} ->",
          "PARKED" if (iv < KILL).any() else "stays CANDIDATE (log only)")


def study_e38():
    """step 2 (E38w): XS and IVS with bought wings at OTM3 / OTM4. One run, 4 cells, Bonferroni 4."""
    os.makedirs(WD, exist_ok=True); E = entries(); rows = []
    for nm in ("XS", "IVS"):
        B = price(E[nm], STR1); b = splits(B)
        for s in ("LEARN", "TEST", "ALL"): rows.append(dict(cell=f"{nm} naked", split=s, **b[s], untraded=np.nan, verdict="base"))
        for w in WINGS:
            C = price(E[nm], S.icon(1, w)); C.to_csv(f"{WD}/e38_{nm}_w{w}_{L.COSTS}.csv", index=False); c = splits(C); u = untraded_pct(B, C)
            v = verdict(b, c, u); m = B.pnl.notna() & C.pnl.notna(); bm = splits(B[m])
            for s in ("LEARN", "TEST", "ALL"): rows.append(dict(cell=f"{nm} + OTM{w} wings", split=s, **c[s], untraded=round(u, 1), verdict=v))
            print(f"{nm} w{w}: untraded {u:.1f}% (no fill {int((C.pnl.isna() & B.pnl.notna()).sum())}, forced {int(C.forced.sum())}); matched naked on the cell's own days: "
                  f"worst {bm['ALL']['worst']}, maxdd {bm['ALL']['maxdd']}, mean {bm['ALL']['mean']}; wing cost/trade {c['ALL']['mean'] - bm['ALL']['mean']:+.0f}; "
                  f"mean net credit {C.credit.mean():.1f} vs naked {B.credit.mean():.1f} pts; exits {C[C.pnl.notna()].why.value_counts().to_dict()} vs naked {B[B.pnl.notna()].why.value_counts().to_dict()}", flush=True)
    R = _show(rows); R.to_csv(f"{WD}/e38_{L.COSTS}.csv", index=False)
    print(f"PASS needs: untraded <= {UNTRADED_MAX}%, worst trade and maxdd each cut >= half vs the naked book (LEARN and ALL), mean >= {KILL:.0f}/trade on LEARN and TEST, "
          f"LEARN p < 0.05/{len(CELLS)} = {ALPHA}, TEST p < 0.05")


def study_spotcheck():
    """known answers on the REAL panel: (1) wherever idx1m has the minute the panel spot IS the index close; (2) the SENSEX 2024-06-04 12:29
    stale-stamp minute reads 70,271.06; (3) expiry-day ATM put-call parity gap (K + C - P - spot) on traded bars, a sanity level not a test:
    two 1-minute closes that last traded at different seconds cannot agree better than a few points."""
    I = pd.read_pickle(L.IDX5Y); I = I[I.sym.isin(["NIFTY", "SENSEX"])].drop_duplicates(["sym", "day", "m"], keep="last")
    I = I[(I.m >= M0) & (I.m < M0 + NB)]; I = I[[k in P for k in zip(I.sym, I.day)]]
    sp = np.array([P[(s, d)]["spot"][m - M0] for s, d, m in zip(I.sym, I.day, I.m)]); e = np.abs(sp - I.close.values)
    print(f"panel spot vs idx1m close on {len(I)} minutes: exact {np.mean(e < 0.011) * 100:.3f}%, > 5 pts {int((e > 5).sum())}, max {np.nanmax(e):.2f}")
    k = ("SENSEX", "2024-06-04"); v = P[k]["spot"][749 - M0]; print("SENSEX 2024-06-04 12:29 panel spot", v, "(index close 70271.06; pre-fix median 71538.83)")
    rows = []
    for k in L.ALLK:
        p = P[k]
        if not p["d0"]: continue
        for j in range(5, 360):
            K = p["atm"][j]; c, q = p["C"].get(("CE", K)), p["C"].get(("PE", K))
            if c is None or q is None or not (c[j, 6] > 0 and q[j, 6] > 0): continue
            rows.append((k[0], k[1][:4], K + c[j, 3] - q[j, 3] - p["spot"][j]))
    G = pd.DataFrame(rows, columns=["sym", "yr", "gap"]); G["a"] = G.gap.abs()
    print(G.groupby("sym").agg(n=("a", "size"), bias=("gap", "mean"), mean_abs=("a", "mean"), p90=("a", lambda x: x.quantile(0.9)), p99=("a", lambda x: x.quantile(0.99)),
                               over_1step=("a", lambda x: (x > 50).mean() * 100)).round(2).to_string())
    if "--old" not in sys.argv:
        assert np.mean(e < 0.011) == 1.0 and abs(v - 70271.06) < 0.011, "spot is not the index minute close where idx1m has it"
        print("spotcheck OK")


def study_selftest():
    """known answers, synthetic only (no real cell is priced here)."""
    # ---- spot_series: index close first, then traded rows, then all rows
    g = pd.DataFrame(dict(m=[600, 600, 600, 601, 601, 602, 602, 602], spot=[100.0, 100, 130, 90, 90, 100, 110, 140], vol=[5, 0, 0, 0, 0, 0, 7, 0]))
    s = L.spot_series(g); assert s[600] == 100 and s[601] == 90 and s[602] == 110, s        # 602: the one traded row beats the stale median (110, not 110-by-luck: median of all = 110 too)
    g2 = g.copy(); g2.loc[5, "spot"] = 140.0; assert L.spot_series(g2)[602] == 110             # all-row median would be 140; the traded row says 110
    ix = pd.Series({600: 101.0, 601: 95.0, 603: 99.0, 100: 1.0, 602: np.nan})                  # 603 only in the index; 100 is outside the session; 602 index hole
    s = L.spot_series(g, ix); assert s[600] == 101 and s[601] == 95 and s[602] == 110 and s[603] == 99 and 100 not in s.index, s
    # ---- condor = naked + the two bought wings when both exit at the same bar (2-step spot jump at bar 100 -> exit at the bar-101 open)
    k = ("NIFTY", "2030-01-01"); sp = np.full(NB, 20000.0); sp[100:] = 20100.0; C = S._syn(k, sp, 50, 20000); kc = k if L.COSTS == "dated" else None
    for (sd, off), (a, b) in {("CE", 1): (20, 90), ("PE", -1): (20, 5), ("CE", 3): (6, 25), ("PE", -3): (6, 2)}.items():
        x = C[(sd, 20000.0 + off * 50)]; x[:, :4] = a; x[101:, :4] = b; x[:, 6] = 10
    rn, rc = S.struct(k, XS_I, STR1, mode="cons", **EX), S.struct(k, XS_I, S.icon(1, 3), mode="cons", **EX)
    assert rn["why"] == rc["why"] == "spot" and rn["held"] == rc["held"] == 101 - (XS_I + 1), (rn, rc)
    h = lambda m, v: L.hs("NIFTY", 1, M0 + m, v); q = L.qty("NIFTY", kc); wing = 0.0
    for a, b in ((6, 25), (6, 2)):
        fi, fo = a + h(XS_I + 1, a), max(b - h(101, b), 0.05); wing += (fo - fi) * q - S._cost(fi, fo, "NIFTY", L.LOTS, kc)
    assert abs(rc["pnl"] - (rn["pnl"] + wing)) < 1e-6, (rc["pnl"], rn["pnl"], wing)
    assert abs(rc["maxloss"] - (100 - rc["credit"]) * q) < 1e-6 and rc["credit"] < rn["credit"]   # wing width 2 strikes = 100 points
    C[("CE", 20150.0)][XS_I + 1, 6] = 0                                                           # the CE wing did not trade at the entry bar
    assert L.STALE_OK or S.struct(k, XS_I, S.icon(1, 3), mode="cons", **EX) is None
    B = pd.DataFrame(dict(day=list("abcdefghij"), pnl=[1.0] * 10, forced=False)); Cc = B.copy(); Cc.loc[0, "pnl"] = np.nan; Cc.loc[1, "forced"] = True
    assert untraded_pct(B, Cc) == 20.0 and untraded_pct(B, B) == 0.0
    # ---- verdict rule
    st = lambda mean, p, worst, dd: dict(mean=mean, p=p, worst=worst, maxdd=dd)
    b = dict(LEARN=st(4000, 0.0, -80000, -200000), TEST=st(4000, 0.0, -60000, -100000), ALL=st(4000, 0.0, -80000, -200000))
    good = dict(LEARN=st(2000, 0.001, -40000, -100000), TEST=st(1500, 0.04, -50000, -90000), ALL=st(1900, 0.001, -40000, -100000))
    assert verdict(b, good, 5.0) == "PASS" and verdict(b, good, 5.1) == "INCONCLUSIVE"
    for split, key, val in (("LEARN", "worst", -40001), ("ALL", "maxdd", -100001), ("LEARN", "mean", 1499), ("TEST", "mean", 1499), ("LEARN", "p", ALPHA), ("TEST", "p", 0.05)):
        bad = {s_: dict(v) for s_, v in good.items()}; bad[split][key] = val; assert verdict(b, bad, 0.0) == "FAIL", (split, key)
    T = pd.DataFrame(dict(day=["2025-01-01", "2025-01-02", "2025-01-03", "2026-01-01"], pnl=[100.0, -300.0, 50.0, np.nan]))
    x = stats(T); assert (x["n"], x["total"], x["worst"], x["maxdd"], x["win"]) == (3, -150, -300, -300, 66.7), x
    assert splits(T, "2025-01-03")["LEARN"]["n"] == 2 and ALPHA == 0.0125
    print("wings_lab selftest OK (spot_series index > traded rows > all rows; condor = naked + wings; untraded wing refused; verdict rule; stats)")


if __name__ == "__main__":
    for a in [a for a in sys.argv[2:] if not a.startswith("-")]: globals()["study_" + a]()
