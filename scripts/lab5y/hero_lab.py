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



# ---------------------------------------------------------------- phase 2: precursors (LEARN only; critic 4, 5, 11, 14)
OI_LAG = int(os.environ.get("OI_LAG", "2"))     # oicad 2026-11-16: OI unchanged on 71% of traded bars, |dOI| tracks the PRIOR bar's volume (0.327 vs 0.305) -> 1 bar stale + 1
NBOOT = int(os.environ.get("NBOOT", "40")); NPERM = int(os.environ.get("NPERM", "100")); STRIDE = int(os.environ.get("STRIDE", "3"))  # phase 2 cost knobs (slots every 15 min by default)     # bars of OI staleness measured by `oicad` + 1 (critic 5); set before phase 2 from the measurement
FEATS = ["r15", "r60", "range30", "compress", "or_pos", "vs_pdh", "vs_pdl", "vs_pdc", "vs_wk", "vs_mo", "fh_er",
         "d_iv15", "iv_rel", "doi15", "doi15_m", "cls", "cls_m", "vsurge", "pcr_d", "wall_steps", "oi_rank", "gam_conc", "sd_decay"]
NUMF = [f for f in FEATS if f not in ("cls", "cls_m")]


def _levels(P, sym, day, days):
    """prior-day high/low/close, week open, month open from the FULL panel (all days), spot only."""
    i = days.index(day); pc = P[(sym, days[i - 1])]["spot"] if i > 0 else None
    wk = next((d for d in days[:i + 1][::-1] if pd.Timestamp(d).weekday() == 0 or d == days[0]), day)
    wk = [d for d in days[:i + 1] if pd.Timestamp(d).isocalendar()[1] == pd.Timestamp(day).isocalendar()[1] and d[:4] == day[:4]][0]
    mo = [d for d in days[:i + 1] if d[:7] == day[:7]][0]
    return dict(pdh=np.nanmax(pc) if pc is not None else np.nan, pdl=np.nanmin(pc) if pc is not None else np.nan,
                pdc=pc[LAST + 14] if pc is not None else np.nan, wk_open=P[(sym, wk)]["spot"][0], mo_open=P[(sym, mo)]["spot"][0])


def load_full(path=None):
    P = pickle.load(open(path or f"{OUT}/panel_off10h.pkl", "rb")); days = collections.defaultdict(list)
    for (s, d) in P: days[s].append(d)
    for s in days: days[s].sort()
    return P, days


def features(R, P, days, lag=OI_LAG):
    """per candidate row, features from bars <= t only (OI from bars <= t - lag). Vectorised per sym-day group."""
    F = {}; g = lambda a, i: a[i] if 0 <= i < NB else np.nan
    for (sym, day), G in R.groupby(["sym", "day"]):
        v = P[(sym, day)]; spot = v["spot"]; st = STEP[sym]; L = _levels(P, sym, day, days[sym]); C = v["C"]
        orh, orl = np.nanmax(spot[:31]), np.nanmin(spot[:31])
        atm = v["atm"]
        for idx, r in G.iterrows():
            t = int(r.t); a = C[(r.side, r.K)]; sgn = 1 if r.side == "CE" else -1; tl = t - lag
            f = {}
            f["r15"] = sgn * (spot[t] - g(spot, t - 15)) / st; f["r60"] = sgn * (spot[t] - g(spot, t - 60)) / st
            w = spot[max(0, t - 30):t + 1]; f["range30"] = (np.nanmax(w) - np.nanmin(w)) / st; f["compress"] = f["range30"] / max((orh - orl) / st, 0.5)
            f["or_pos"] = sgn * ((spot[t] - orl) / (orh - orl) - 0.5) if orh > orl else 0.0
            f["vs_pdh"] = sgn * (spot[t] - L["pdh"]) / st; f["vs_pdl"] = sgn * (spot[t] - L["pdl"]) / st; f["vs_pdc"] = sgn * (spot[t] - L["pdc"]) / st
            f["vs_wk"] = sgn * (spot[t] - L["wk_open"]) / st; f["vs_mo"] = sgn * (spot[t] - L["mo_open"]) / st
            w60 = spot[max(0, t - 60):t + 1]; dd = np.abs(np.diff(w60)); f["fh_er"] = abs(w60[-1] - w60[0]) / dd.sum() if dd.sum() > 0 else 0.0
            f["d_iv15"] = a[t, 5] - g(a[:, 5], t - 15); f["iv_rel"] = a[t, 5] / (C[("CE", atm[t])][t, 5] if (atm[t] == atm[t] and ("CE", atm[t]) in C) else np.nan)
            f["doi15"] = (g(a[:, 4], tl) - g(a[:, 4], tl - 15)) / LOT[sym]; dp = a[t, 3] - g(a[:, 3], t - 15); f["cls"] = oi_class(dp, f["doi15"])
            Km = r.K - 2 * sgn * r.dist * st if False else (spot[t] - sgn * r.dist * st); Km = round(Km / st) * st; m = C.get(("PE" if r.side == "CE" else "CE", Km))
            f["doi15_m"] = (g(m[:, 4], tl) - g(m[:, 4], tl - 15)) / LOT[sym] if m is not None else np.nan
            f["cls_m"] = oi_class(m[t, 3] - g(m[:, 3], t - 15), f["doi15_m"]) if m is not None else "NA"
            v5 = np.nansum(a[max(0, t - 4):t + 1, 6]); vb = np.nansum(a[max(0, t - 34):max(0, t - 4), 6]) / 6; f["vsurge"] = v5 / vb if vb > 0 else np.nan
            dce = dpe = 0.0; wall = np.nan; best = -1; oir = []
            for (sd, K2), b in C.items():
                if abs(K2 - spot[t]) > 5 * st or not np.isfinite(b[tl, 4]): continue
                d = b[tl, 4] - g(b[:, 4], tl - 15)
                if sd == "CE": dce += d if d == d else 0
                else: dpe += d if d == d else 0
                if sd == r.side and b[tl, 4] > best: best = b[tl, 4]; wall = sgn * (K2 - spot[t]) / st
                if sd == r.side: oir.append(b[tl, 4])
            f["pcr_d"] = sgn * (dpe - dce) / LOT[sym]; f["wall_steps"] = wall
            f["oi_rank"] = float(np.mean(np.array(oir) <= g(a[:, 4], tl))) if oir else np.nan
            gn = gt = 0.0
            for (sd, K2), b in C.items():
                if not (np.isfinite(b[t, 5]) and 1 < b[t, 5] < 200 and np.isfinite(b[tl, 4])): continue
                T = T_min(t); vv = b[t, 5] / 100; d1 = (math.log(spot[t] / K2) + 0.5 * vv * vv * T) / (vv * math.sqrt(T)); gm = math.exp(-0.5 * d1 * d1) / (spot[t] * vv * math.sqrt(2 * math.pi * T))
                x = gm * b[tl, 4]; gt += x; gn += x if abs(K2 - spot[t]) <= 2 * st else 0
            f["gam_conc"] = gn / gt if gt > 0 else np.nan
            ce, pe = C.get(("CE", atm[t])), C.get(("PE", atm[t])); a30 = atm[t - 30] if t >= 30 else np.nan
            if ce is not None and pe is not None and a30 == a30 and ("CE", a30) in C and ("PE", a30) in C:
                s_now = ce[t, 3] + pe[t, 3]; s_then = C[("CE", a30)][t - 30, 3] + C[("PE", a30)][t - 30, 3]
                f["sd_decay"] = (s_now / s_then) / math.sqrt(T_min(t) / T_min(t - 30)) if s_then > 0 else np.nan
            else: f["sd_decay"] = np.nan
            F[idx] = f
    return pd.DataFrame.from_dict(F, orient="index").reindex(R.index)


def touch_prob(S, K, T, v, cp):
    """reflection-principle probability that the spot touches the strike before expiry at the entry IV (driftless)."""
    S, K, T, v = (np.asarray(x, float) for x in (S, K, T, v)); d = np.abs(np.log(K / S)) / (v * np.sqrt(T)); return 2 * (1 - _N(d))


def _logit(X, y, l2=1e-3, it=50):
    """IRLS logistic regression with a tiny ridge; X without intercept (added here); returns the weight vector."""
    X = np.c_[np.ones(len(X)), X]; w = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]); gr = X.T @ (y - p) - l2 * w
        step = np.linalg.solve(H, gr); w = w + step
        if np.abs(step).max() < 1e-8: break
    return w


def auc(score, y):
    r = pd.Series(score).rank().values; n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan


def _z(X, mu=None, sd=None):
    mu = X.mean(0) if mu is None else mu; sd = X.std(0) + 1e-9 if sd is None else sd; return (X - mu) / sd, mu, sd


def precursors(R, F, labels=(("D10_5x_60", lambda R: (R.p0 <= 10) & (R.ratio_60 >= 5), lambda R: R.p0 <= 10), ("D20_3x_60", lambda R: R.ratio_60 >= 3, lambda R: R.p0 <= 20)),
               nperm=None, seed=43):
    """critic 4: per feature, AUC added over the pricing baseline (log price, steps OTM, minutes to 15:15, touch probability) in leave-one-year-out
    rotations (2021-22 | 2023 | 2024 | 2025), day-block bootstrap CI of the mean dAUC, day-permutation null, BH-FDR across features x labels."""
    rg = np.random.default_rng(seed); out = []; nperm = NPERM if nperm is None else nperm
    S0 = R.spot0.values; tp = touch_prob(S0, R.K.values, T_min(R.t.values), np.where(np.isfinite(R.iv0), R.iv0, np.nanmedian(R.iv0)), R.side.values)
    base = np.c_[np.log(R.p0.values), R.dist.values, (LAST - R.t.values) / 60.0, tp]
    yrs = R.yr.replace({"2021": "2022"}).values; rot = sorted(set(yrs)); days = R.day.values
    cat = {"cls": pd.get_dummies(F.cls).reindex(columns=["LONG_BUILD", "SHORT_BUILD", "SHORT_COVER", "LONG_UNWIND"], fill_value=0).values.astype(float),
           "cls_m": pd.get_dummies(F.cls_m).reindex(columns=["LONG_BUILD", "SHORT_BUILD", "SHORT_COVER", "LONG_UNWIND"], fill_value=0).values.astype(float)}
    def dauc(Xb, Xf, y, mask, perm=None):
        """mean over rotations of AUC(base+feat) - AUC(base) on the held-out year; perm = permuted-by-day label vector."""
        yy = y if perm is None else perm; ds = []
        for h in rot:
            tr = mask & (yrs != h); te = mask & (yrs == h)
            if yy[tr].sum() < 20 or yy[te].sum() < 5 or (1 - yy[te]).sum() < 5: continue
            zb, mu, sd = _z(Xb[tr]); wb = _logit(zb, yy[tr]); zf, mu2, sd2 = _z(Xf[tr]); wf = _logit(zf, yy[tr])
            sb = np.c_[np.ones(te.sum()), _z(Xb[te], mu, sd)[0]] @ wb; sf = np.c_[np.ones(te.sum()), _z(Xf[te], mu2, sd2)[0]] @ wf
            ds.append((auc(sf, yy[te]) - auc(sb, yy[te]), auc(sb, yy[te]), auc(sf, yy[te])))
        return ds
    for lname, lab, cond in labels:
        y = lab(R).values.astype(float); m0 = cond(R).values & np.isfinite(R.ratio_60.values)
        strata = pd.factorize(pd.Series(list(zip(pd.cut(R.p0, [0.99, 2, 5, 10, 20.01]).astype(str), pd.cut(R.dist, [0.99, 2, 4, 7, 10.5]).astype(str), (R.t + M0) // 60))))[0]
        def permute(col, ok):
            """null: the feature shuffled within (premium, distance, hour) strata; the baseline columns stay, so dAUC under the null is pure noise."""
            c = col.copy()
            for st_ in np.unique(strata[ok]):
                idx = np.where(ok & (strata == st_))[0]; c[idx] = c[rg.permutation(idx)]
            return c
        for f in FEATS:
            col = cat[f] if f in cat else F[f].values[:, None]
            ok = m0 & np.isfinite(col).all(1) & np.isfinite(base).all(1)
            if ok.sum() < 200 or y[ok].sum() < 20: out.append(dict(label=lname, feat=f, n=int(ok.sum()), note="too few")); continue
            Xf = np.c_[base, col]; ds = dauc(base, Xf, y, ok)
            if not ds: out.append(dict(label=lname, feat=f, n=int(ok.sum()), note="no rotation")); continue
            d = np.array([x[0] for x in ds]); every = bool((d > 0).all())
            # day-block bootstrap of the mean dAUC: resample days within each held-out year
            B = []
            for _ in range(NBOOT):
                keep = np.isin(days, rg.choice(np.unique(days[ok]), size=len(np.unique(days[ok])), replace=True)); bb = dauc(base, Xf, y, ok & keep)
                if bb: B.append(np.mean([x[0] for x in bb]))
            lo, hi = (np.percentile(B, [2.5, 97.5]) if B else (np.nan, np.nan))
            null = [np.mean([x[0] for x in dauc(base, np.c_[base, permute(col, ok)], y, ok)] or [np.nan]) for _ in range(nperm)]
            pperm = float(np.mean(np.array(null) >= d.mean())) if null else np.nan
            lift = np.nan
            if f not in cat:
                q = F[f].values[ok]; hi_q = q >= np.nanpercentile(q, 80); lift = y[ok][hi_q].mean() / max(y[ok].mean(), 1e-9)
            out.append(dict(label=lname, feat=f, n=int(ok.sum()), pos=int(y[ok].sum()), base_auc=np.mean([x[1] for x in ds]), feat_auc=np.mean([x[2] for x in ds]), dauc=d.mean(), dauc_min=d.min(),
                            every_rot=every, ci_lo=lo, ci_hi=hi, p_perm=pperm, lift_top20=lift))
    O = pd.DataFrame(out)
    if "p_perm" in O:
        ok = O.p_perm.notna(); pv = O.loc[ok, "p_perm"].values; n = len(pv); order = np.argsort(pv); bh = np.empty(n); bh[order] = np.minimum.accumulate((pv[order] * n / np.arange(1, n + 1))[::-1])[::-1]
        O.loc[ok, "q_bh"] = np.clip(bh, 0, 1); O["precursor"] = ok & O.every_rot.fillna(False) & (O.q_bh < 0.1) & (O.ci_lo > 0)
    return O


def study_precursors():
    R = pd.read_pickle(f"{OUT}/playbook/e43_candidates_learn.pkl"); assert (R.day < HO).all(), "TEST rows in the LEARN candidates"
    R = R[~R.sensex_pre & (R.ratio_60.notna()) & (((R.t - 5) // 5) % STRIDE == 0)].copy(); print(f"phase 2 on {len(R)} LEARN candidate strike-slots ({R.day.nunique()} days), OI_LAG={OI_LAG}", flush=True)
    P, days = load_full(); R["spot0"] = [P[(s, d)]["spot"][t] for s, d, t in zip(R.sym, R.day, R.t)]
    F = features(R, P, days); del P
    # IV quality (critic 11): own BS IV vs Dhan IV by premium bucket
    q = R.assign(iv_gap=(R.iv0 * 100 - R.iv_dhan).abs(), p_b=pd.cut(R.p0, [0.99, 2, 5, 10, 20.01]), ttc=pd.cut(LAST - R.t, [0, 60, 120, 240, 400]))
    print("IV quality: |own BS IV - Dhan IV| (IV points) by premium bucket x minutes to 15:15\n" + q.groupby(["p_b", "ttc"], observed=True).iv_gap.agg(["count", "median", lambda x: np.mean(x > 5)]).round(2).to_string(), flush=True)
    bad = (q.iv_gap > 5) & (q.iv_gap / q.iv_dhan.abs().clip(lower=1) > 0.2); F.loc[bad.values, ["d_iv15", "iv_rel"]] = np.nan; print(f"IV features dropped on {bad.mean():.3f} of rows (disagreement > 5 pts and > 20%)")
    F.to_pickle(f"{OUT}/playbook/e43_features_learn.pkl")
    for c in ("cls", "cls_m"):
        print(f"\n-- lift by {c} (P(ratio_60 >= 3) and >= 5 by OI class, p0 <= 10):\n" + R[R.p0 <= 10].assign(k=F[c]).groupby("k").agg(n=("p0", "size"), P3=("ratio_60", lambda x: (x >= 3).mean()), P5=("ratio_60", lambda x: (x >= 5).mean()), mean_ratio=("ratio_60", "mean")).round(3).to_string())
    O = precursors(R, F); pd.set_option("display.width", 250); print("\n== precursor scoring (leave-one-year-out dAUC over the pricing baseline; day-block CI; day-permutation p; BH q) ==")
    print(O.round(4).to_string()); O.to_csv(f"{OUT}/playbook/e43_precursors.csv", index=False)
    print("\nPRECURSORS (every rotation > 0, CI low > 0, q_bh < 0.1):", O[O.get("precursor", False) == True][["label", "feat", "dauc", "q_bh"]].to_string() if "precursor" in O else "none")


if __name__ == "__main__":
    {"atlas": study_atlas, "precursors": study_precursors, "oicad": lambda: oi_cadence(load(learn=True)), "selftest": selftest}[sys.argv[1]]()
