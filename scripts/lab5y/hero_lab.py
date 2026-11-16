"""E43 hero-zero lab (registry E43, FROZEN 2026-11-16 in E43_hero_zero_freeze.md + the Opus critic decisions there; paper only, no Dhan API).

Expiry-day cheap-OTM option spikes on NIFTY / SENSEX from the 5-year hygiene panel (panel_off10h.pkl: 1m o/h/l/c/OI/IV/vol, ATM+-10).
Phase 1 = atlas + replay + OI cadence on LEARN expiry days only (descriptive; the spike label is look-ahead by design; no P&L).
TEST (day >= HO) never enters memory in phase 1: `load(learn=True)` drops it before anything is read.

Strict definition (critic items 1, 6, 11, 16): decision at the close of bar t (Dhan bars are stamped at the bar start, so bar t is closed at
t+1:00); fill = bar t+1 OPEN + half-spread (1 tick = 0.05 for premium <= 20 on expiry day: spreads_fine.csv p75 <= 0.05), rounded to 0.05;
candidate only if bar t traded (vol > 0), 1 <= fill <= pmax, >= 1 step OTM; a spike = a later CLOSE minus half-spread >= k x fill, counted only on
bars whose volume >= 5 x our quantity (10 lots), inside the window and never after bar 360 (15:15).

  OUT=data/cache/lab5y_full HO=2025-10-27 ~/paper_extra_venv/bin/python scripts/lab5y/hero_lab.py atlas      # phase 1 (LEARN)
  ... hero_lab.py oicad                                                                                      # OI update cadence (critic 5)
  ~/paper_extra_venv/bin/python scripts/lab5y/hero_lab.py selftest                                            # known answers
"""
import collections, math, os, pickle, sys
import numpy as np, pandas as pd

OUT = os.environ.get("OUT", "/Users/sahiltayde/Documents/all_about_dhan/data/cache/lab5y_full"); HO = os.environ.get("HO", "2025-10-27")
STEP = {"NIFTY": 50, "SENSEX": 100}; LOT = {"NIFTY": 65, "SENSEX": 20}; LOTS = 10; M0, NB, LAST = 555, 375, 360   # LAST = 15:15 bar
TICK, HS = 0.05, 0.05                        # half-spread for premium <= 20 on expiry day: spreads_fine.csv p75 is 0.025-0.05 in every time bucket
SLOTS = list(range(5, 346, 5))               # 09:20 .. 15:00 every 5 min (minute index from 09:15); exits by 15:15
PMAX, KS, WS = (5, 10, 20), (3, 5, 10, 20), {"30": 30, "60": 60, "120": 120, "close": None}
VOLX = 5                                     # a spike bar must have traded >= VOLX x our quantity
SENSEX_OK = "2023-05-15"                     # SENSEX weekly relaunch; earlier SENSEX sym-days are flagged (critic 10)
HALF = "2024-11-20"                          # LEARN halves split: SEBI one weekly expiry per exchange (critic 10)
hm = lambda i: f"{(M0 + i) // 60:02d}:{(M0 + i) % 60:02d}"
rnd = lambda x: np.round(np.asarray(x, float) / TICK) * TICK


def _events():
    """RBI / FOMC-next / Budget dates from the engine (opt1y_lab, playbook_lab); empty set if the engine cannot be imported here."""
    try:
        argv = sys.argv; sys.argv = ["x", OUT]; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import opt1y_lab as O, playbook_lab as W; sys.argv = argv
        nxt = lambda d: (pd.Timestamp(d) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")       # FOMC lands after the Indian close: the next session reacts
        ev = set(O.RBI) | set(O.FOMC) | {nxt(d) for d in O.FOMC} | set(W.E42_BUDGET)
        return ev
    except Exception as e:
        print("events: engine import failed,", type(e).__name__, e, "-> no event flag", flush=True); return set()


def load(learn=True, path=None):
    """expiry sym-days only; learn=True keeps day < HO (TEST never enters memory in phase 1). Adds monthly, prev_close, weekday, event, sensex_pre."""
    P = pickle.load(open(path or f"{OUT}/panel_off10h.pkl", "rb"))
    days = collections.defaultdict(list)
    for (s, d) in P: days[s].append(d)
    for s in days: days[s].sort()
    E = {k: v for k, v in P.items() if v["d0"] == 1 and ((k[1] < HO) if learn else (k[1] >= HO))}
    by = collections.defaultdict(list)
    for (s, d) in E: by[(s, d[:7])].append(d)
    mon = {(s, max(ds)) for (s, _), ds in by.items()}                 # monthly expiry = the last expiry of its month per sym
    ev = _events()
    for (s, d), v in E.items():
        i = days[s].index(d); pc = P[(s, days[s][i - 1])]["spot"] if i > 0 else None
        v["monthly"] = (s, d) in mon; v["prev_close"] = float(pc[LAST + 14]) if pc is not None and pc[LAST + 14] == pc[LAST + 14] else np.nan
        v["weekday"] = pd.Timestamp(d).day_name()[:3]; v["event"] = d in ev; v["sensex_pre"] = s == "SENSEX" and d < SENSEX_OK
    del P
    return E


# ---- Black-Scholes on calendar minutes to the 15:30 close (expiry day: T is tiny and matters minute by minute)
_N = lambda x: 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))
T_min = lambda i: np.maximum(930 - (M0 + np.asarray(i)), 1) / 525600.0      # minutes left to 15:30, annualised


def bs(S, K, T, v, cp, r=0.065):
    S, K, T, v = (np.asarray(x, float) for x in (S, K, T, v))
    d1 = (np.log(S / K) + (r + 0.5 * v * v) * T) / (v * np.sqrt(T)); d2 = d1 - v * np.sqrt(T)
    return np.where(np.asarray(cp) == "CE", S * _N(d1) - K * np.exp(-r * T) * _N(d2), K * np.exp(-r * T) * _N(-d2) - S * _N(-d1))


def implied_vol(p, S, K, T, cp, lo=0.01, hi=5.0, it=40):
    """vectorised bisection; NaN where the price is below intrinsic / above the bound."""
    p, S, K, T = (np.asarray(x, float) for x in (p, S, K, T)); lo = np.full(p.shape, lo); hi = np.full(p.shape, hi)
    for _ in range(it):
        mid = 0.5 * (lo + hi); up = bs(S, K, T, mid, cp) < p; lo = np.where(up, mid, lo); hi = np.where(up, hi, mid)
    v = 0.5 * (lo + hi); bad = np.abs(bs(S, K, T, v, cp) - p) > 0.05 + 0.01 * p
    return np.where(bad, np.nan, v)


def candidates(E, pmax=20, slots=SLOTS, volx=VOLX):
    """one row per (sym, day, side, K, slot t): strict definition (module docstring). Look-ahead columns (atlas only): ratio_<w> = best
    (close - HS) / fill on qualifying bars in (t+1, min(t+1+w, LAST)], tmax, zero flag (a close <= 20% of the fill), steps the spot moved toward
    the strike by the max, the BS re-price at the ENTRY implied vol (description only), window-edge flags."""
    rows = []
    for (sym, day), v in E.items():
        st = STEP[sym]; spot = v["spot"]; minvol = volx * LOTS * LOT[sym]
        base = dict(sym=sym, day=day, yr=day[:4], monthly=v["monthly"], weekday=v["weekday"], event=v["event"], sensex_pre=v["sensex_pre"],
                    gap=(spot[0] / v["prev_close"] - 1) * 100 if v["prev_close"] == v["prev_close"] and spot[0] == spot[0] else np.nan)
        for (side, K), a in v["C"].items():
            o, c, oi, iv, vol = a[:, 0], a[:, 3], a[:, 4], a[:, 5], a[:, 6]; sgn = 1 if side == "CE" else -1
            good = np.isfinite(c) & (vol >= minvol)                       # bars where a spike print is fillable at our size
            for t in slots:
                if t + 1 >= LAST or not (vol[t] > 0) or not np.isfinite(o[t + 1]) or spot[t] != spot[t]: continue
                fill = float(rnd(o[t + 1] + HS))
                if fill < 1.0 or fill > pmax: continue
                dist = sgn * (K - spot[t]) / st
                if dist < 1: continue
                r = dict(base, side=side, K=K, t=t, p0=fill, c_t=c[t], dist=dist, oi0=oi[t], vol0=vol[t], iv_dhan=iv[t],
                         new_in_window=not np.isfinite(c[max(t - 15, 0)]))
                hz = c[t + 2:LAST + 1]; g = good[t + 2:LAST + 1]
                r["nan_share_h"] = float(np.mean(~np.isfinite(hz))) if len(hz) else np.nan
                for nm, w in WS.items():
                    seg = hz[:w] if w else hz; gg = g[:w] if w else g
                    if gg.sum() == 0: r[f"ratio_{nm}"] = np.nan; r[f"zero_{nm}"] = bool(np.nanmin(seg) <= 0.2 * fill) if np.isfinite(seg).any() else np.nan; continue
                    q = np.where(gg, seg, -np.inf); j = int(np.argmax(q)); r[f"ratio_{nm}"] = (seg[j] - HS) / fill; r[f"tmax_{nm}"] = j + 2
                    r[f"zero_{nm}"] = bool(np.nanmin(seg) <= 0.2 * fill)
                    if nm == "close":
                        tm = t + 2 + j; r["tm"] = tm; r["spot_tm"] = spot[tm]
                        r["steps_at_max"] = sgn * (spot[tm] - spot[t]) / st if spot[tm] == spot[tm] else np.nan
                        r["above3_min"] = int(np.sum(np.where(gg, seg, 0) - HS >= 3 * fill))
                rows.append(r)
    R = pd.DataFrame(rows)
    if len(R) and "tm" in R:
        S0 = np.array([E[(s, d)]["spot"][t] for s, d, t in zip(R.sym, R.day, R.t)])
        R["iv0"] = implied_vol(R.p0.values, S0, R.K.values, T_min(R.t.values), R.side.values)
        ok = R.tm.notna()
        R["ratio_bs"] = np.nan
        R.loc[ok, "ratio_bs"] = bs(R.spot_tm[ok].values, R.K[ok].values, T_min(R.tm[ok].values), R.iv0[ok].values, R.side[ok].values) / R.p0[ok].values
        R["iv_share"] = (np.log(R.ratio_close) - np.log(R.ratio_bs.clip(lower=1e-6))) / np.log(R.ratio_close.clip(lower=1.0001))
    return R


def atlas(R, E):
    """phase-1 tables (LEARN); prints and returns {name: DataFrame}."""
    T = {}; p = lambda s: print(s, flush=True)
    R = R.copy(); R["slot"] = R.t.map(hm); R["dist_b"] = pd.cut(R.dist, [0.99, 2, 4, 7, 10.5], labels=["1-2", "3-4", "5-7", "8-10"])
    R["p_b"] = pd.cut(R.p0, [0.99, 2, 5, 10, 20.01], labels=["1-2", "2-5", "5-10", "10-20"]); R["hour"] = (R.t + M0) // 60
    R["gap_b"] = pd.cut(R.gap.abs(), [-0.01, 0.2, 0.5, 100], labels=["<0.2", "0.2-0.5", ">0.5"])
    def rates(g):
        d = dict(n=len(g), days=g.day.nunique(), p0_med=g.p0.median(), dist_med=g.dist.median())
        for nm in WS:
            for k in KS: d[f"P{k}x_{nm}"] = (g[f"ratio_{nm}"] >= k).mean()
            d[f"Pzero_{nm}"] = g[f"zero_{nm}"].astype(float).mean()
        d["ratio_med_close"] = g.ratio_close.median(); d["ratio_mean_close"] = g.ratio_close.mean(); d["nofill"] = g.ratio_close.isna().mean(); return pd.Series(d)
    p(f"\n== E43 atlas STRICT (LEARN expiry days: {R.day.nunique()} days, {len(R)} cheap-OTM candidate strike-slots, fill 1..{R.p0.max():.0f}, spike bars need vol >= {VOLX} x {LOTS} lots) ==")
    p(f"   window-edge: new_in_window {R.new_in_window.mean():.3f}; NaN share inside the horizon median {R.nan_share_h.median():.3f} mean {R.nan_share_h.mean():.3f}; no fillable spike bar at all {R.ratio_close.isna().mean():.3f}")
    cols = ["n", "days", "p0_med", "P3x_60", "P5x_60", "P10x_60", "P5x_close", "P10x_close", "P20x_close", "Pzero_60", "Pzero_close", "ratio_med_close", "ratio_mean_close", "nofill"]
    for nm, key in (("by_pmax", "p_b"), ("by_dist", "dist_b"), ("by_sym_monthly", ["sym", "monthly"]), ("by_year", "yr"), ("by_side", "side"),
                    ("by_hour", "hour"), ("by_weekday", ["sym", "weekday"]), ("by_event", "event"), ("by_gap", "gap_b"), ("by_sensex_pre", ["sym", "sensex_pre"])):
        T[nm] = R.groupby(key, observed=True).apply(rates); p(f"\n-- {nm}\n" + T[nm][cols].round(3).to_string())
    T["by_slot"] = R.groupby("slot").apply(rates); p("\n-- by_slot (entry minute)\n" + T["by_slot"][["n", "p0_med", "P3x_60", "P5x_60", "P5x_close", "P10x_close", "Pzero_60", "Pzero_close", "ratio_med_close", "ratio_mean_close"]].round(3).to_string())
    # per expiry sym-day: the best fillable ratio over all cheap strike-slots; how many distinct strikes made 5x
    D = R.groupby(["sym", "day", "monthly", "yr", "weekday", "event"]).agg(best=("ratio_close", "max"), n5=("ratio_close", lambda x: int((x >= 5).sum())), n_cand=("p0", "size")).reset_index()
    T["by_day"] = D; agg = dict(n="size", P3=lambda x: (x >= 3).mean(), P5=lambda x: (x >= 5).mean(), P10=lambda x: (x >= 10).mean(), P20=lambda x: (x >= 20).mean(), med=lambda x: x.median())
    p("\n-- per expiry sym-day: P(some cheap strike-slot reaches k x, fillable)\n" + D.groupby(["sym", "monthly"]).best.agg(**agg).round(3).to_string())
    p("   by year\n" + D.groupby("yr").best.agg(**agg).round(3).to_string()); p("   by event flag\n" + D.groupby("event").best.agg(**agg).round(3).to_string())
    S = R[R.ratio_close >= 5].sort_values("ratio_close", ascending=False).drop_duplicates(["sym", "day", "side", "K"])
    S = S.assign(slot_max=S.tm.map(lambda i: hm(int(i))), hr_max=((S.tm + M0) // 60).astype(int)); T["spikes"] = S
    p(f"\n-- anatomy of {len(S)} distinct fillable >= 5x spikes (one per sym-day-side-strike; best entry slot)")
    p("   entry hour of the best slot: " + S.hour.value_counts().sort_index().to_dict().__repr__() + "   hour of the max: " + S.hr_max.value_counts().sort_index().to_dict().__repr__())
    p("   steps the spot moved toward the strike by the max: " + S.steps_at_max.describe().round(2).to_dict().__repr__())
    p("   minutes above 3x (fillable bars): " + S.above3_min.describe().round(1).to_dict().__repr__())
    p("   IV-expansion share of the log spike (description only): " + S.iv_share.describe().round(2).to_dict().__repr__())
    p("   side: " + S.side.value_counts().to_dict().__repr__() + "  monthly: " + S.monthly.value_counts().to_dict().__repr__() + "  dist: " + S.dist_b.value_counts().sort_index().to_dict().__repr__() + "  premium: " + S.p_b.value_counts().sort_index().to_dict().__repr__())
    return T


def oi_cadence(E):
    """critic 5: is the 1-min OI field live? share of traded bars with OI unchanged, run lengths, and corr(dOI_t, vol_t) vs corr(dOI_t, vol_{t-1}) vs corr(dOI_{t+1}, vol_t)."""
    same = tot = 0; runs = []; X = []
    for (sym, day), v in E.items():
        for (side, K), a in v["C"].items():
            oi, vol = a[:, 4], a[:, 6]; d = np.diff(oi); tr = (vol[1:] > 0) & np.isfinite(d)
            tot += int(tr.sum()); same += int((tr & (d == 0)).sum())
            r = 0
            for x, ok in zip(d, tr):
                if ok and x == 0: r += 1
                elif r: runs.append(r); r = 0
            if tr.sum() > 30: X.append((d[1:-1], vol[2:-1], vol[1:-2], np.r_[d[2:], np.nan][:len(d) - 2][:len(d[1:-1])]))
    print(f"OI cadence (LEARN expiry days, {len(E)} sym-days): traded bars {tot}, OI unchanged on {same / max(tot, 1):.3f} of them; unchanged-run length median {np.median(runs) if runs else np.nan:.0f} p90 {np.percentile(runs, 90) if runs else np.nan:.0f} max {max(runs) if runs else 0}")
    dO = np.concatenate([x[0] for x in X]); v0 = np.concatenate([x[1] for x in X]); v1 = np.concatenate([x[2] for x in X])
    ok = np.isfinite(dO) & np.isfinite(v0) & np.isfinite(v1); a, b, c = np.abs(dO[ok]), v0[ok], v1[ok]
    print(f"   corr(|dOI_t|, vol_t) {np.corrcoef(a, b)[0, 1]:.3f}  corr(|dOI_t|, vol_(t-1)) {np.corrcoef(a, c)[0, 1]:.3f}  (if the second is larger, OI lags volume by a bar)")
    print(f"   share of bars with vol > 0: {np.mean(np.concatenate([x[1] for x in X]) > 0):.3f}; share of |dOI| > 0 among vol == 0 bars: {np.mean(a[b == 0] > 0) if (b == 0).any() else np.nan:.3f}")


def oi_class(dp, doi):
    """the founder's four: price up + OI up = LONG_BUILD, price down + OI up = SHORT_BUILD, price up + OI down = SHORT_COVER, price down + OI down = LONG_UNWIND."""
    if not (dp == dp and doi == doi): return "NA"
    return ("LONG_BUILD" if doi > 0 else "SHORT_COVER") if dp > 0 else ("SHORT_BUILD" if doi > 0 else "LONG_UNWIND") if dp < 0 else "FLAT"


def replay(S, E, n=20, path=None):
    """minute timelines of the n largest fillable spikes per sym (LEARN), 5-min steps from 30 min before the entry slot to 15 min after the max."""
    out = ["# E43 replay: the largest fillable cheap-OTM spikes on LEARN expiry days (descriptive, look-ahead by construction, no P&L)\n",
           "Columns: time, spot, steps OTM, option close, OI, 1-min volume, Dhan IV, 15-min OI class (price/OI move over the prior 15 min), ATM straddle close.\n"]
    for sym in sorted(S.sym.unique()):
        for _, r in S[S.sym == sym].head(n).iterrows():
            v = E[(r.sym, r.day)]; a = v["C"][(r.side, r.K)]; spot = v["spot"]; st = STEP[sym]; sgn = 1 if r.side == "CE" else -1; tm = int(r.tm)
            out.append(f"\n## {sym} {r.day} {v['weekday']}{' (monthly)' if r.monthly else ''}{' (event)' if r.event else ''} {r.side} {r.K:.0f}: filled Rs {r.p0:.2f} at {hm(r.t + 1)} open -> Rs {r.p0 * r.ratio_close:.2f} net at {hm(tm)} (x{r.ratio_close:.1f}; spot moved {r.steps_at_max:.1f} steps; BS at entry IV explains x{r.ratio_bs:.1f}; {r.above3_min} fillable min above 3x)\n")
            out.append("| time | spot | steps | opt | OI | vol | IV | 15m OI class | straddle |\n|---|---|---|---|---|---|---|---|---|")
            for i in range(max(0, r.t - 30), min(NB, tm + 16), 5):
                atm = v["atm"][i]; sd = np.nan
                if atm == atm:
                    ce, pe = v["C"].get(("CE", atm)), v["C"].get(("PE", atm))
                    if ce is not None and pe is not None: sd = ce[i, 3] + pe[i, 3]
                j = i - 15; cls = oi_class(a[i, 3] - a[j, 3], a[i, 4] - a[j, 4]) if j >= 0 else "NA"
                out.append(f"| {hm(i)} | {spot[i]:.0f} | {sgn * (r.K - spot[i]) / st:.1f} | {a[i, 3]:.2f} | {a[i, 4]:.0f} | {a[i, 6]:.0f} | {a[i, 5]:.1f} | {cls} | {sd:.1f} |")
    txt = "\n".join(out)
    if path: open(path, "w").write(txt)
    return txt


def study_atlas():
    E = load(learn=True); print(f"LEARN expiry sym-days {len(E)} (monthly {sum(v['monthly'] for v in E.values())}, event {sum(v['event'] for v in E.values())}, sensex_pre {sum(v['sensex_pre'] for v in E.values())}); TEST not loaded", flush=True)
    R = candidates(E, pmax=max(PMAX)); os.makedirs(f"{OUT}/playbook", exist_ok=True)
    T = atlas(R, E); R.to_pickle(f"{OUT}/playbook/e43_candidates_learn.pkl"); T["by_day"].to_csv(f"{OUT}/playbook/e43_atlas_days.csv", index=False)
    with open(f"{OUT}/playbook/e43_atlas.csv", "w") as f:
        for k in ("by_pmax", "by_dist", "by_sym_monthly", "by_year", "by_side", "by_hour", "by_weekday", "by_event", "by_gap", "by_sensex_pre", "by_slot"):
            f.write(f"# {k}\n"); T[k].to_csv(f); f.write("\n")
    replay(T["spikes"], E, 20, f"{OUT}/playbook/e43_replay.md"); print("\nwrote e43_atlas.csv, e43_atlas_days.csv, e43_replay.md, e43_candidates_learn.pkl")
    oi_cadence(E)


def _day(c, o=None, vol=5000.0, oi=1000.0, iv=15.0):
    a = np.full((NB, 7), np.nan); a[:, 3] = c; a[:, 0] = c if o is None else o; a[:, 4] = oi; a[:, 5] = iv; a[:, 6] = vol; return a


def selftest():
    # one hand-built expiry day: spot flat at 22700 then +150 at 11:00; a cheap CE 5 steps out opens 3.95 at 09:46, closes 40 from 11:00 to 11:05, then 0.5
    spot = np.full(NB, 22700.0); spot[105:] = 22850.0; c = np.full(NB, 4.0); c[105:111] = 40.0; c[111:] = 0.5; o = c.copy(); o[31] = 3.95
    a = _day(c, o); a[108, 6] = 100.0                                                    # one thin bar inside the spike: not a fillable print
    E = {("NIFTY", "2024-01-04"): dict(spot=spot, atm=np.full(NB, 22700.0), C={("CE", 22950.0): a}, exp="2024-01-04", dte=0, d0=1, monthly=False, prev_close=22650.0, weekday="Thu", event=False, sensex_pre=False)}
    R = candidates(E, pmax=20, slots=[30, 60]); r = R[R.t == 30].iloc[0]
    assert r.p0 == 4.0 and r.ratio_close == (40 - HS) / 4 and r.tmax_close == 75 and hm(int(r.tm)) == "11:00" and r.steps_at_max == 3 and r.zero_close and not r.zero_60 and r.above3_min == 5, r.to_dict()
    assert abs(r.gap - (22700 / 22650 - 1) * 100) < 1e-9 and not r.new_in_window
    r6 = R[R.t == 60].iloc[0]; assert r6.p0 == 4.05 and r6.ratio_60 == (40 - HS) / 4.05 and r6.ratio_30 == (4 - HS) / 4.05, r6.to_dict()   # fill = next open + 1 tick
    assert 0 < r.ratio_bs < 10 and 0 < r.iv_share < 1, (r.ratio_bs, r.iv_share)        # a 150-pt move alone does not make a 5-step-OTM Rs 4 option x10 at 11:00
    # critic 1: a spike only on thin bars is not a spike; critic 16: bars after the fill bar do not change the fill or the entry features
    a2 = _day(c, o); a2[105:111, 6] = 100.0; E2 = {k: dict(v, C={("CE", 22950.0): a2}) for k, v in E.items()}
    assert candidates(E2, slots=[30]).iloc[0].ratio_close == (4 - HS) / 4   # the thin 40s do not count; the best fillable close is the flat 4.0
    a3 = _day(np.r_[c[:32], np.random.default_rng(1).uniform(0.5, 60, NB - 32)], o); E3 = {k: dict(v, C={("CE", 22950.0): a3}) for k, v in E.items()}
    r3 = candidates(E3, slots=[30]).iloc[0]; assert r3.p0 == r.p0 and r3.c_t == r.c_t and r3.dist == r.dist and r3.oi0 == r.oi0 and r3.iv0 == r.iv0
    # premium floor Rs 1, pmax, >= 1 step OTM, bar t must have traded, no spike bar after 15:15
    assert len(candidates({("NIFTY", "d"): dict(E[("NIFTY", "2024-01-04")], C={("CE", 22700.0): a})}, slots=[30])) == 0
    a4 = _day(np.full(NB, 0.6), None); assert len(candidates({k: dict(v, C={("CE", 22950.0): a4}) for k, v in E.items()}, slots=[30])) == 0
    a5 = _day(c, o); a5[30, 6] = 0.0; assert len(candidates({k: dict(v, C={("CE", 22950.0): a5}) for k, v in E.items()}, slots=[30])) == 0
    c6 = np.full(NB, 4.0); c6[361:] = 80.0; a6 = _day(c6, None); assert candidates({k: dict(v, C={("CE", 22950.0): a6}) for k, v in E.items()}, slots=[30]).iloc[0].ratio_close == (4 - HS) / 4.05   # 15:16 on is never counted
    c6[360] = 80.0; a6 = _day(c6, None); assert candidates({k: dict(v, C={("CE", 22950.0): a6}) for k, v in E.items()}, slots=[30]).iloc[0].ratio_close == (80 - HS) / 4.05             # the 15:15 bar is
    assert oi_class(1, 1) == "LONG_BUILD" and oi_class(-1, 1) == "SHORT_BUILD" and oi_class(1, -1) == "SHORT_COVER" and oi_class(-1, -1) == "LONG_UNWIND" and oi_class(0, 5) == "FLAT" and oi_class(np.nan, 1) == "NA"
    iv = implied_vol([4.0], [22700.0], [22950.0], [T_min(30)], np.array(["CE"]))[0]; assert abs(bs(22700.0, 22950.0, T_min(30), iv, "CE") - 4.0) < 0.05, iv
    assert float(rnd(3.9749)) == 3.95 and float(rnd(0.07)) == 0.05 and HO == "2025-10-27" and LAST == 360 and SLOTS[-1] == 345
    txt = replay(atlas(R, E)["spikes"], E, 1); assert "x10.0" in txt and "| 11:00 | 22850 |" in txt, txt[:400]
    print("hero_lab selftest OK (strict fill, volume-qualified spike, windows, 15:15 cap, zero flag, floor/pmax/OTM/traded guards, no-lookahead scramble, BS share, OI classes, implied vol, replay)")


if __name__ == "__main__":
    {"atlas": study_atlas, "oicad": lambda: oi_cadence(load(learn=True)), "selftest": selftest}[sys.argv[1]]()
