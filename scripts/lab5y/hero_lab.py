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
HSX = {"NIFTY": [(20, 0.05), (50, 0.10), (100, 0.20), (200, 0.38), (1e9, 0.80)], "SENSEX": [(20, 0.05), (50, 0.12), (100, 0.23), (200, 0.45), (1e9, 1.35)]}   # spreads_fine.csv p75 by premium (exits can leave the cheap bucket)
def hsx(sym, p): return next(h for u, h in HSX[sym] if p <= u)


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


def load(learn=True, path=None, P=None):
    """expiry sym-days only; learn=True keeps day < HO (TEST never enters memory in phase 1). Adds monthly, prev_close, weekday, event, sensex_pre."""
    own = P is None; P = P if P is not None else pickle.load(open(path or f"{OUT}/panel_off10h.pkl", "rb"))
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
    if own: del P
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
    # phase 3 leg(): Rs 4 fill, target 3x -> 12.05 + tick + HS on a thick bar fills AT 12.00; on a thin bar at that bar close - HS; SL 50% intrabar; 15:15 open when nothing hits
    b3 = _day(c, o); b3[:, 1] = b3[:, 3]; b3[:, 2] = b3[:, 3]; b3[105, 1] = 40.0
    tr = leg(b3, spot, "NIFTY", "2024-01-04", "2024-01-04", 31, 3.0); assert tr["why"] == "tgt" and tr["x"] == 12.0 and tr["en"] == 4.0 and tr["held"] == 74, tr
    assert abs(tr["pnl"] - ((12 - 4) * qty("NIFTY", "2024-01-04") - cost(4, 12, "NIFTY", "2024-01-04", "2024-01-04"))) < 1e-6 and qty("NIFTY", "2024-01-04") == 650 and qty("NIFTY", "2024-01-04", 1) == 50
    b3[105, 6] = 100.0; tr = leg(b3, spot, "NIFTY", "2024-01-04", "2024-01-04", 31, 3.0); assert tr["why"] == "tgt_thin" and tr["thin"] and abs(tr["x"] - (40 - hsx("NIFTY", 40))) < 1e-9, tr   # exits above Rs 20 pay the 20-50 bucket half-spread
    b4 = _day(np.full(NB, 4.0), None); b4[:, 1] = 4.0; b4[:, 2] = 4.0; b4[50, 2] = 1.0; tr = leg(b4, spot, "NIFTY", "2024-01-04", "2024-01-04", 31, 3.0); assert tr["why"] == "sl" and abs(tr["x"] - (4.05 * 0.5 - HS)) <= TICK and tr["held"] == 19, tr   # en 4.05 (open + tick), SL at 50% intrabar, fill - HS, tick-rounded
    b5 = _day(np.full(NB, 4.0), None); b5[:, 1] = 4.0; b5[:, 2] = 4.0; tr = leg(b5, spot, "NIFTY", "2024-01-04", "2024-01-04", 31, 3.0); assert tr["why"] == "time" and tr["held"] == LAST - 31 and tr["x"] == 4.0 - HS, tr
    tr = leg(b5, spot, "NIFTY", "2024-01-04", "2024-01-04", 31, 3.0, tstop=30); assert tr["why"] == "tstop" and tr["held"] == 30, tr
    assert abs(cost(4, 12, "NIFTY", "2024-01-04", "2024-01-04") - CM * (40 + 0.0005 * (4 + 12) * 650 + 1e-6 * 16 * 650 + 0.18 * (40 + 0.0005 * 16 * 650 + 1e-6 * 16 * 650) + 0.00003 * 4 * 650 + 0.000625 * 12 * 650)) < 1e-9
    assert len(GRID_A) == 16 and len(GRID_B) == 48 and len(GRID) == 64
    txt = replay(atlas(R, E)["spikes"], E, 1); assert "x10.0" in txt and "| 11:00 | 22850 |" in txt, txt[:400]
    print("hero_lab selftest OK (strict fill, volume-qualified spike, windows, 15:15 cap, zero flag, floor/pmax/OTM/traded guards, no-lookahead scramble, BS share, OI classes, implied vol, replay)")



# ---------------------------------------------------------------- phase 2: precursors (LEARN only; critic 4, 5, 11, 14)
OI_LAG = int(os.environ.get("OI_LAG", "2"))     # oicad 2026-11-16: OI unchanged on 71% of traded bars, |dOI| tracks the PRIOR bar's volume (0.327 vs 0.305) -> 1 bar stale + 1
NPL = int(os.environ.get("NPL", "200")); NBOOT = int(os.environ.get("NBOOT", "40")); NPERM = int(os.environ.get("NPERM", "100")); STRIDE = int(os.environ.get("STRIDE", "3"))  # phase 2 cost knobs (slots every 15 min by default)     # bars of OI staleness measured by `oicad` + 1 (critic 5); set before phase 2 from the measurement
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



# ---------------------------------------------------------------- phase 3: cells (families and grids frozen in E43_hero_zero_freeze.md section 13)
# costs = opt1y_lab COSTS=dated tables (copied: importing opt1y_lab loads a second 2.3 GB panel). Sources: teams/01_research/docs/REPO_HARVEST.md section 5.
CM = float(os.environ.get("CM", "1.0"))   # critic 2 (commit 2): gate at CM=1.0 (the dated tables as they are); CM=1.5 = opt1y_lab's stress multiplier, reported beside it
STT_SELL = [("2016-06-01", 0.0005), ("2023-04-01", 0.000625), ("2024-10-01", 0.001), ("2026-04-01", 0.0015)]
TXN_D = {"NIFTY": [("2021-01-01", 0.00053), ("2023-04-01", 0.0005), ("2024-10-01", 0.0003503), ("2026-03-01", 0.000355299)], "SENSEX": [("2023-01-01", 0.000325)]}
LOT_D = {"NIFTY": [("2021-07-01", 50), ("2024-04-26", 25), ("2024-12-20", 75), ("2025-12-31", 65)], "SENSEX": [("2023-01-01", 10), ("2025-01-04", 20)]}
_at = lambda tab, d: [v for f, v in tab if f <= d][-1]


def qty(sym, exp, lots=LOTS):
    """units for `lots` of today's lot, as whole lots of the size in force at the contract's expiry (opt1y_lab.qty, dated)."""
    lt = _at(LOT_D[sym], exp); return max(1, round(LOT[sym] * lots / lt)) * lt


def cost(b, sl, sym, day, exp, lots=LOTS):
    """round-trip charges x CM for one leg bought at b and sold at sl (per unit) at `lots` (opt1y_lab.cost, dated)."""
    q = qty(sym, exp, lots); bt, st = b * q, sl * q; tx = _at(TXN_D[sym], day) * (bt + st); se = 1e-6 * (bt + st)
    return CM * (40 + tx + se + 0.18 * (40 + tx + se) + 0.00003 * bt + _at(STT_SELL, day) * st)


def leg(a, spot, sym, day, exp, e, tgt_x, stop_x=0.5, tstop=None, trail=True, cap=None, volx=VOLX, stress=0.0, chase=0.0):
    """long one cheap OTM leg filled at bar e OPEN + HS (+ stress ticks, + chase x bar-e range for family B); exits on 1-min bars:
    SL stop_x of entry intrabar (fill min(sl, open) - HS); target tgt_x x entry fills AT the target only if the bar high clears target + tick + HS
    AND the bar traded >= volx x qty, else at that bar's close - HS (thin); trailing from 2x: SL = max(SL, 0.6 x running high); adverse spot cap
    (steps) at the next open; time stop at bar e + tstop open; else the 15:15 (bar 360) open; a NaN bar = forced at the last close.
    Returns P&L at 10 lots and at 1 lot, net of dated costs."""
    o, h, l, c, vol = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 6]
    if not (np.isfinite(o[e]) and vol[e] > 0): return None
    en = float(rnd(o[e] + HS + stress + chase * max(h[e] - l[e], 0))); tp = tgt_x * en; sl = sl0 = en * (1 - stop_x); hi = en
    q10, q1 = qty(sym, exp, LOTS), qty(sym, exp, 1); s0 = spot[e]; xe = min(LAST, e + tstop) if tstop else LAST; x = why = None; thin = forced = False
    for j in range(e + 1, xe):
        if not np.isfinite(o[j]): x, why, forced = c[j - 1] - hsx(sym, c[j - 1]) - stress, "window", True; break
        if l[j] <= sl: x, why = min(sl, o[j]) - hsx(sym, min(sl, o[j])) - stress, "sl"; break
        if h[j] >= tp + TICK + hsx(sym, tp):
            if vol[j] >= volx * q10: x, why = tp, "tgt"
            else: x, why, thin = c[j] - hsx(sym, c[j]) - stress, "tgt_thin", True
            break
        hi = max(hi, h[j])
        if trail and hi >= 2 * en: sl = max(sl, 0.6 * hi)
        if cap and np.isfinite(spot[j]) and np.isfinite(s0) and -(spot[j] - s0) * (1 if a is not None else 1) >= 0 and False: pass
        if cap and np.isfinite(spot[j]) and np.isfinite(s0) and cap[0] * (spot[j] - s0) <= -cap[1] * STEP[sym] and j + 1 < xe and np.isfinite(o[j + 1]):
            x, why = o[j + 1] - hsx(sym, o[j + 1]) - stress, "cap"; j += 1; break
    if x is None:
        j = xe; x, why = (o[j] - hsx(sym, o[j]) - stress if np.isfinite(o[j]) else c[j - 1] - hsx(sym, c[j - 1]) - stress), ("tstop" if tstop and xe < LAST else "time")
    x = max(float(rnd(x)), TICK)
    return dict(en=en, x=x, why=why, held=j - e, thin=thin, forced=forced,
                pnl=(x - en) * q10 - cost(en, x, sym, day, exp, LOTS), pnl1=(x - en) * q1 - cost(en, x, sym, day, exp, 1))


def _pick(v, sym, side, t, pmax):
    """critic 13: the qualifying strike nearest to spot: >= 1 step OTM, bar t traded, fill (next open + HS) in [1, pmax]. Returns (K, a) or None."""
    spot = v["spot"]; st = STEP[sym]; sgn = 1 if side == "CE" else -1; best = None
    for (sd, K), a in v["C"].items():
        if sd != side: continue
        d = sgn * (K - spot[t]) / st
        if d < 1 or not (a[t, 6] > 0) or not np.isfinite(a[t + 1, 0]): continue
        f = float(rnd(a[t + 1, 0] + HS))
        if f < 1.0 or f > pmax: continue
        if best is None or d < best[0]: best = (d, K, a)
    return None if best is None else (best[1], best[2])


def _level_cross(v, L, t, sgn):
    """family C gate: within the last 15 min the spot crossed, in the strike's direction, one of prior-day H/L/C, OR high/low, week open, month open."""
    spot = v["spot"]; orh, orl = np.nanmax(spot[:31]), np.nanmin(spot[:31]); lv = [L["pdh"], L["pdl"], L["pdc"], orh, orl, L["wk_open"], L["mo_open"]]
    a, b = spot[t], spot[max(t - 15, 0)]
    return any(np.isfinite(x) and sgn * (a - x) > 0 and sgn * (b - x) <= 0 for x in lv)


GRID_A = [dict(fam="A", cr=cr, pmax=pm, k=k, add=ad) for cr in (0.5, 0.7) for pm in (5, 10) for k in (3, 5) for ad in (0, 1)]                      # 16
GRID_B = [dict(fam=f, cls=cl, vm=vm, k=k, ts=ts) for f in ("B", "C") for cl in ("SHORT_COVER", "LONG_BUILD", "EITHER") for vm in (2, 3) for k in (2, 3) for ts in (30, 60)]  # 48
GRID = GRID_A + GRID_B


def trades(E, P, days, F, R, grid=GRID, stress=0.0, chase_b=0.0):
    """all trades of every configuration on the expiry sym-days in E. F/R = features and candidate rows (phase 2 schema, every 5-min slot).
    One position per side per sym-day per configuration: the first slot whose gate holds (placebos: `placebo_trades`)."""
    out = []; FR = R.join(F); byday = {k: g for k, g in FR.groupby(["sym", "day"])}
    for (sym, day), v in E.items():
        L = _levels(P, sym, day, days[sym]); G = byday.get((sym, day))
        if G is None: continue
        for cfg in grid:
            done = set()
            for t in SLOTS:
                if t + 2 >= LAST: break
                for side in ("CE", "PE"):
                    if side in done: continue
                    sgn = 1 if side == "CE" else -1; rows = G[(G.t == t) & (G.side == side)]
                    if cfg["fam"] == "A":
                        if side == "PE" and "CE" not in done: continue                      # A enters both legs at the same slot (CE first)
                        r = rows[rows.p0 <= cfg["pmax"]].sort_values("dist").head(1)
                        if r.empty: continue
                        r = r.iloc[0]; other = G[(G.t == t) & (G.side == "PE") & (G.p0 <= cfg["pmax"])].sort_values("dist").head(1)
                        gate = (r.compress <= cfg["cr"]) and (r.cls in ("SHORT_BUILD", "LONG_BUILD") or (not other.empty and other.iloc[0].cls in ("SHORT_BUILD", "LONG_BUILD")))
                        if not gate or other.empty: continue
                        legs = [("CE", r), ("PE", other.iloc[0])]
                    else:
                        r = rows[rows.p0 <= 10].sort_values("dist").head(1)
                        if r.empty: continue
                        r = r.iloc[0]
                        okc = r.cls == cfg["cls"] if cfg["cls"] != "EITHER" else r.cls in ("SHORT_COVER", "LONG_BUILD")
                        gate = okc and (r.vsurge >= cfg["vm"]) and (r.r15 > 0)
                        if cfg["fam"] == "C": gate = gate and _level_cross(v, L, t, sgn)
                        if not gate: continue
                        legs = [(side, r)]
                    for sd, rr in legs:
                        vv, tt, dd = v, t, day
                        pk = _pick(vv, sym, sd, tt, cfg.get("pmax", 10))
                        if pk is None: continue
                        K, a = pk; exp = vv["exp"]; sg = 1 if sd == "CE" else -1
                        tr = leg(a, vv["spot"], sym, dd, exp, tt + 1, cfg["k"], 0.5, cfg.get("ts"), trail=cfg["fam"] != "A", cap=None, stress=stress, chase=chase_b if cfg["fam"] != "A" else 0.0)
                        if tr is None: continue
                        tr.update(sym=sym, day=day, side=sd, K=K, t=tt, cfg=str(cfg), fam=cfg["fam"], n_legs=1)
                        if cfg["fam"] == "A" and cfg["add"]:                                   # wait for the low: one add-on when the leg closes 10% below its running low
                            c = a[:, 3]; lo = tr["en"]; e2 = None
                            for j in range(tt + 2, min(LAST, tt + 1 + tr["held"])):
                                if np.isfinite(c[j]) and c[j] <= lo - 0.10 * tr["en"] and j + 1 < LAST: e2 = j + 1; break
                                if np.isfinite(c[j]): lo = min(lo, c[j])
                            if e2 is not None:
                                t2 = leg(a, vv["spot"], sym, dd, exp, e2, cfg["k"], 0.5, None, trail=False, stress=stress)
                                if t2: tr["pnl"] += t2["pnl"]; tr["pnl1"] += t2["pnl1"]; tr["n_legs"] = 2; tr["thin"] = tr["thin"] or t2["thin"]; tr["forced"] = tr["forced"] or t2["forced"]
                        out.append(tr)
                    done.update(sd for sd, _ in legs)
    return pd.DataFrame(out)


def placebo_trades(T, cfg, E, rg, kind):
    """critic 8: the same count of trades as T with identical exits, each replaced by (a) "minute": the same sym-day at a random slot,
    (b) "day": a random other expiry sym-day of the same sym at the same minute, (c) "mirror": the other side at the same minute;
    the strike is the pick rule's (nearest qualifying, same pmax), so premium bucket and distance are matched by construction."""
    out = []; dl = {sym: [d for (s_, d) in E if s_ == sym] for sym in LOT}
    for r in T.itertuples():
        sd, tt, dd = r.side, int(r.t), r.day
        if kind == "minute": tt = int(rg.choice([x for x in SLOTS if x + 2 < LAST]))
        elif kind == "day": dd = str(rg.choice([d for d in dl[r.sym] if d != r.day]))
        elif kind == "mirror": sd = "PE" if sd == "CE" else "CE"
        v = E[(r.sym, dd)]; pk = _pick(v, r.sym, sd, tt, cfg.get("pmax", 10))
        if pk is None: continue
        K, a = pk; tr = leg(a, v["spot"], r.sym, dd, v["exp"], tt + 1, cfg["k"], 0.5, cfg.get("ts"), trail=cfg["fam"] != "A")
        if tr: out.append(tr["pnl"])
    return np.array(out)


def dayboot_p(T, B=2000, seed=11):
    """day-block bootstrap (both syms one block): P(mean <= 0)."""
    if T.empty: return np.nan
    d = T.groupby("day").pnl.sum(); n = T.groupby("day").pnl.size(); rg = np.random.default_rng(seed); dv, nv = d.values, n.values
    m = [(dv[i].sum() / nv[i].sum()) for i in (rg.integers(len(dv), size=len(dv)) for _ in range(B))]
    return float(np.mean(np.array(m) <= 0))


def cell_stats(T, nm):
    if T.empty: return dict(cell=nm, n=0)
    d = T.groupby("day").pnl.sum().sort_values()
    return dict(cell=nm, n=len(T), days=T.day.nunique(), win=(T.pnl > 0).mean(), mean=T.pnl.mean(), total=T.pnl.sum(), p=dayboot_p(T), mean1=T.pnl1.mean(), p1=dayboot_p(T.assign(pnl=T.pnl1)),
                top5_share=T.pnl.nlargest(max(1, len(T) // 20)).sum() / T.pnl.sum() if T.pnl.sum() > 0 else np.nan, thin=T.thin.mean(), forced=T.forced.mean(),
                maxdd=float((d.cumsum() - d.cumsum().cummax()).min()) if len(d) else np.nan, drop3=T.pnl.sum() - d.tail(3).sum(),
                h1=T[T.day < HALF].pnl.mean() if (T.day < HALF).any() else np.nan, h2=T[T.day >= HALF].pnl.mean() if (T.day >= HALF).any() else np.nan)


def loyo(TR, grid, metric="pnl"):
    """critic 3: leave-one-year-out: for each held-out year, the configuration with the best mean on the other years prices that year."""
    yrs = TR.day.str[:4].replace({"2021": "2022"}); parts = []; picks = {}
    for h in sorted(yrs.unique()):
        tr = TR[yrs != h]; m = tr.groupby("cfg")[metric].mean()
        if m.empty: continue
        best = m.idxmax(); picks[h] = best; parts.append(TR[(yrs == h) & (TR.cfg == best)])
    return (pd.concat(parts) if parts else TR.iloc[0:0]), picks


def study_cells():
    """LEARN: every configuration priced; per family LOYO series, PBO, placebos, stress, 1 lot; the <= 12 final cells written to e43_cells_learn.csv.
    TEST is NOT touched here (study_test does that once, after commit 2)."""
    from honest_stats import pbo_cscv
    P, days = load_full(); E = load(learn=True, P=P); E = {k: v for k, v in E.items() if not v["sensex_pre"]}
    R = pd.read_pickle(f"{OUT}/playbook/e43_candidates_learn.pkl"); R = R[~R.sensex_pre]          # critic (commit 2): no ratio_60 filter here, it reads the future
    try: F = pd.read_pickle(f"{OUT}/playbook/e43_features_all.pkl"); assert len(F) == len(R) and (F.index == R.index).all()
    except Exception:
        R["spot0"] = [P[(s, d)]["spot"][t] for s, d, t in zip(R.sym, R.day, R.t)]; F = features(R, P, days); F.to_pickle(f"{OUT}/playbook/e43_features_all.pkl")
    print(f"phase 3 LEARN: {len(E)} expiry sym-days, {len(GRID)} configurations ({len(GRID_A)} A, {len(GRID_B)} B+C)", flush=True)
    try: TR = pd.read_pickle(f"{OUT}/playbook/e43_trades_learn.pkl"); assert os.environ.get("REPRICE") is None; print(f"trades {len(TR)} (cached e43_trades_learn.pkl; REPRICE=1 to re-run)", flush=True)
    except Exception:
        TR = trades(E, P, days, F, R); TR.to_pickle(f"{OUT}/playbook/e43_trades_learn.pkl"); print(f"trades {len(TR)}", flush=True)
    rows = []; final = []
    for fam in ("A", "B", "C"):
        G = [c for c in GRID if c["fam"] == fam]; T = TR[TR.fam == fam]
        if T.empty: print(f"family {fam}: no trades"); continue
        M = T.pivot_table(index="day", columns="cfg", values="pnl", aggfunc="sum").fillna(0.0)
        pbo = pbo_cscv(M.values, S=8)["pbo"] if M.shape[1] >= 2 and M.shape[0] >= 16 else np.nan
        Lo, picks = loyo(T, G); st = cell_stats(Lo, f"{fam} LOYO"); st.update(pbo=pbo, configs=len(G), picks=str(picks)); rows.append(st)
        print(f"\n== family {fam}: {len(G)} configs, {len(T)} trades; LOYO n {st['n']} mean {st['mean']:,.0f} p {st['p']:.4f} | 1 lot mean {st['mean1']:,.0f} p {st['p1']:.4f} | PBO {pbo:.2f} | picks {picks}", flush=True)
        per = T.groupby("cfg").agg(n=("pnl", "size"), days=("day", "nunique"), mean=("pnl", "mean"), win=("pnl", lambda x: (x > 0).mean()), mean1=("pnl1", "mean")).sort_values("mean", ascending=False)
        print(per.round(1).head(8).to_string())
        for cfg in per.index[:3]: final.append(dict(fam=fam, cfg=cfg, learn_mean=per.loc[cfg, "mean"], learn_n=int(per.loc[cfg, "n"])))
    pd.DataFrame(rows).to_csv(f"{OUT}/playbook/e43_families_learn.csv", index=False)
    # final cells (<= 12): top 3 per family on full LEARN among configs; each gets the LEARN gates, the three placebos, stress and 1 lot
    rg = np.random.default_rng(7); cells = []
    for f in final:
        cfg = eval(f["cfg"]); T = TR[TR.cfg == f["cfg"]]; st = cell_stats(T, f["cfg"])
        PL = {}
        for nm in ("minute", "day", "mirror"):
            ms = [placebo_trades(T, cfg, E, rg, nm).mean() for _ in range(NPL)]
            PL[f"pl_{nm}"] = float(np.mean(np.array(ms) >= st["mean"])) if ms else np.nan
        S2 = trades(E, P, days, F, R, [cfg], stress=2 * TICK, chase_b=0.25); st.update(PL, stress_mean=S2.pnl.mean() if len(S2) else np.nan, stress_mean1=S2.pnl1.mean() if len(S2) else np.nan)
        fr = next(r for r in rows if r["cell"].startswith(f["fam"])); st.update(loyo_mean=fr["mean"], loyo_p=fr["p"], pbo=fr["pbo"], cm=CM)
        cells.append(st); print(f"cell {f['cfg']}: n {st['n']} mean {st['mean']:,.0f} p {st['p']:.4f} win {st['win']:.2f} 1lot {st['mean1']:,.0f} p1 {st['p1']:.4f} placebo(day) {st['pl_day']:.3f} stress {st['stress_mean']:,.0f} top5 {st['top5_share']:.2f} thin {st['thin']:.2f} forced {st['forced']:.3f} drop3 {st['drop3']:,.0f}", flush=True)
    C = pd.DataFrame(cells); C.to_csv(f"{OUT}/playbook/e43_cells_learn.csv", index=False); print(f"\nwrote e43_cells_learn.csv ({len(C)} cells); alpha = 0.05 / {len(C)} = {0.05 / max(len(C), 1):.5f}")



# ---------------------------------------------------------------- cross-instrument study (founder 2026-11-16: "relation between instruments that causes
# the spikes; 11:00-12:30 and 13:00-15:10; catch 4 of 10"). LEARN only, exploratory (NOT one of the 12 frozen cells): any rule it suggests must be
# frozen in a later commit before it sees TEST.
WIN_X = [(105, 195), (225, 355)]          # 11:00-12:30 and 13:00-15:10 as minute indices from 09:15
XF = ["oth_r15", "oth_r30", "oth_spk15", "own_spk15", "sd_exp15", "sd_exp30", "pcr_d", "wall_steps", "chain_vsurge", "range30", "compress", "r15", "r30", "oi_cover", "oi_build"]


def cross_table(E, P, R):
    """one row per (sym, day, slot t in the two windows, side): label = some cheap strike on this side reaches 5x (fillable) within 60 min of t
    (from the candidate rows, max over strikes); features at t from THIS index, the OTHER index's spot and its own cheap-OTM state, the ATM
    straddle, the chain (OI, volume). All features use bars <= t (OI lagged OI_LAG)."""
    lab = R[R.t.apply(lambda t: any(a <= t <= b for a, b in WIN_X))].groupby(["sym", "day", "t", "side"]).agg(spk5=("ratio_60", lambda x: (x >= 5).any()), spk3=("ratio_60", lambda x: (x >= 3).any()), best=("ratio_60", "max"), n=("p0", "size")).reset_index()
    sp3 = {(r.sym, r.day, r.side): set() for r in lab.itertuples()}
    for r in R[R.ratio_60 >= 3].itertuples():                       # the minute a >= 3x move COMPLETED (its max); "spiked in the prior 15 min" = that minute in [t-15, t) (critic: no look-ahead)
        if r.tmax_60 == r.tmax_60: sp3.setdefault((r.sym, r.day, r.side), set()).add(int(r.t) + int(r.tmax_60))
    rows = []
    for r in lab.itertuples():
        v = E[(r.sym, r.day)]; oth = "SENSEX" if r.sym == "NIFTY" else "NIFTY"; vo = P.get((oth, r.day)); t = int(r.t); st = STEP[r.sym]; sgn = 1 if r.side == "CE" else -1; spot = v["spot"]
        f = dict(sym=r.sym, day=r.day, t=t, side=r.side, spk5=bool(r.spk5), spk3=bool(r.spk3), best=r.best, yr=r.day[:4], win="A" if t < 200 else "B")
        f["r15"] = sgn * (spot[t] - spot[t - 15]) / st; f["r30"] = sgn * (spot[t] - spot[t - 30]) / st
        w = spot[t - 30:t + 1]; f["range30"] = (np.nanmax(w) - np.nanmin(w)) / st; orr = (np.nanmax(spot[:31]) - np.nanmin(spot[:31])) / st; f["compress"] = f["range30"] / max(orr, 0.5)
        if vo is not None:
            so = vo["spot"]; sto = STEP[oth]; f["oth_r15"] = sgn * (so[t] - so[t - 15]) / sto; f["oth_r30"] = sgn * (so[t] - so[t - 30]) / sto
        else: f["oth_r15"] = f["oth_r30"] = np.nan
        f["oth_spk15"] = float(any(x in sp3.get((oth, r.day, r.side), ()) for x in range(t - 15, t))) if vo is not None and vo["d0"] == 1 else np.nan   # other index expiring today and spiking already
        f["own_spk15"] = float(any(x in sp3.get((r.sym, r.day, "PE" if r.side == "CE" else "CE"), ()) for x in range(t - 15, t)))                    # the OTHER side of this index spiked just before (reversal?)
        atm = v["atm"]; C = v["C"]
        def strad(i):
            a = atm[i]
            if a != a or ("CE", a) not in C or ("PE", a) not in C: return np.nan
            return C[("CE", a)][i, 3] + C[("PE", a)][i, 3]
        s0, s15, s30 = strad(t), strad(t - 15), strad(t - 30)
        f["sd_exp15"] = (s0 / s15) / math.sqrt(T_min(t) / T_min(t - 15)) if s15 and s15 == s15 and s0 == s0 else np.nan
        f["sd_exp30"] = (s0 / s30) / math.sqrt(T_min(t) / T_min(t - 30)) if s30 and s30 == s30 and s0 == s0 else np.nan
        tl = t - OI_LAG; dce = dpe = 0.0; wall = np.nan; best = -1; v5 = v30 = 0.0; cover = build = 0
        for (sd, K), b in C.items():
            if abs(K - spot[t]) > 5 * st: continue
            v5 += np.nansum(b[t - 4:t + 1, 6]); v30 += np.nansum(b[t - 34:t - 4, 6]) / 6
            if not np.isfinite(b[tl, 4]) or not np.isfinite(b[tl - 15, 4]): continue
            d = b[tl, 4] - b[tl - 15, 4]; dp = b[t, 3] - b[t - 15, 3]
            if sd == "CE": dce += d
            else: dpe += d
            if sd == r.side and (K - spot[t]) * sgn > 0:
                if dp > 0 and d < 0: cover += 1
                if dp < 0 and d > 0: build += 1
                if b[tl, 4] > best: best = b[tl, 4]; wall = sgn * (K - spot[t]) / st
        f["pcr_d"] = sgn * (dpe - dce) / LOT[r.sym]; f["wall_steps"] = wall; f["chain_vsurge"] = v5 / v30 if v30 > 0 else np.nan; f["oi_cover"] = cover; f["oi_build"] = build
        rows.append(f)
    return pd.DataFrame(rows)


def study_cross():
    """prints: base rates per window; per feature the LOYO AUC (no baseline: the label is per slot, not per option), the catch-vs-false-alarm curve
    (recall of spike-slots vs the alarm rate on non-spike slots at the top-q threshold), the NIFTY<->SENSEX spike co-occurrence and lead, and the
    LEARN P&L of buying the nearest cheap strike (<= Rs 10, target 5x / stop 50% / 60 min) at the alarms of the best feature (exploratory)."""
    P, days = load_full(); E = load(learn=True, P=P); E = {k: v for k, v in E.items() if not v["sensex_pre"]}
    R = pd.read_pickle(f"{OUT}/playbook/e43_candidates_learn.pkl"); R = R[~R.sensex_pre & R.ratio_60.notna()]
    X = cross_table(E, P, R); X.to_pickle(f"{OUT}/playbook/e43_cross_learn.pkl"); pd.set_option("display.width", 250)
    print(f"\n== cross-instrument study (LEARN): {len(X)} (sym, day, slot, side) rows in 11:00-12:30 and 13:00-15:10")
    print("base rate P(some cheap strike on this side reaches 5x within 60 min):\n" + X.groupby(["win", "sym"]).spk5.agg(["size", "mean"]).round(3).to_string())
    print("per sym-day-side: P(at least one such slot in the day)", X.groupby(["sym", "day", "side"]).spk5.any().mean().round(3))
    yrs = X.yr.replace({"2021": "2022"}); rows = []
    for f in XF:
        x = X[f].values; y = X.spk5.values.astype(float); ok = np.isfinite(x)
        if ok.sum() < 500 or y[ok].sum() < 20: continue
        aucs = []
        for h in sorted(yrs.unique()):
            te = ok & (yrs == h).values
            if y[te].sum() < 5: continue
            aucs.append(auc(x[te], y[te]))
        a = np.array(aucs); flip = a.mean() < 0.5
        rk = pd.Series(x).rank(pct=True, method="average").values            # rank threshold: discrete / binary features cannot alarm on everything (critic)
        alarm = (rk <= 0.2) if flip else (rk >= 0.8)
        rec = y[ok & alarm].sum() / y[ok].sum(); fa = (alarm & ok & (y == 0)).sum() / (ok & (y == 0)).sum(); prec = y[ok & alarm].mean()
        rows.append(dict(feat=f, n=int(ok.sum()), auc_mean=a.mean(), auc_min=a.min(), auc_max=a.max(), direction="low" if flip else "high", catch_at_top20=rec, false_alarm=fa, precision=prec, base=y[ok].mean()))
    O = pd.DataFrame(rows).sort_values("auc_mean", ascending=False); print("\n-- per feature: LOYO AUC for 'spike within 60 min' (0.5 = nothing); catch = share of spike-slots in the top-20% alarm; false_alarm = share of non-spike slots alarmed\n" + O.round(3).to_string())
    O.to_csv(f"{OUT}/playbook/e43_cross_learn.csv", index=False)
    # NIFTY <-> SENSEX: co-occurrence and lead of >= 5x spikes on days when both expire (rare) and on all days via the OTHER index's 30-min move
    S = R[R.ratio_60 >= 5].drop_duplicates(["sym", "day", "side", "K"])
    both = S.groupby("day").sym.nunique(); print(f"\n-- days with a >= 5x spike on NIFTY: {S[S.sym == 'NIFTY'].day.nunique()}, on SENSEX: {S[S.sym == 'SENSEX'].day.nunique()}, same day both (both expiring that day): {(both == 2).sum()}")
    lead = []
    for d, g in S.groupby("day"):
        if g.sym.nunique() < 2: continue
        n = g[g.sym == "NIFTY"].tm.min(); s_ = g[g.sym == "SENSEX"].tm.min(); lead.append(n - s_)
    if lead: print("   NIFTY max minus SENSEX max on those days (minutes; negative = NIFTY first):", np.round(np.percentile(lead, [10, 50, 90]), 0), "n", len(lead))
    # exploratory P&L at the alarms of the best feature (LEARN only; not a frozen cell)
    for f in ("range30", O.iloc[0].feat) if len(O) else ():
        flip = O.set_index("feat").loc[f, "direction"] == "low"; rk = X[f].rank(pct=True); A = X[(rk <= 0.2) if flip else (rk >= 0.8)]
        out = []
        for r in A.itertuples():
            v = E[(r.sym, r.day)]; pk = _pick(v, r.sym, r.side, int(r.t), 10)
            if pk is None: continue
            tr = leg(pk[1], v["spot"], r.sym, r.day, v["exp"], int(r.t) + 1, 5.0, 0.5, 60)
            if tr: out.append(dict(tr, day=r.day, sym=r.sym))
        T = pd.DataFrame(out)
        if len(T): print(f"\n-- exploratory: buy the nearest cheap strike (<= 10) at every '{f}' alarm (top 20%), target 5x, stop 50%, 60 min: n {len(T)} days {T.day.nunique()} win {(T.pnl > 0).mean():.2f} mean {T.pnl.mean():,.0f} (1 lot {T.pnl1.mean():,.0f}) p {dayboot_p(T):.3f} top5 share {T.pnl.nlargest(max(1, len(T) // 20)).sum() / T.pnl.sum() if T.pnl.sum() > 0 else float('nan'):.2f}")



# ---------------------------------------------------------------- TEST, read once (commit 2 freezes OUT/playbook/e43_cells_frozen.json first)
def trades_D(E, X, thr, k, ts):
    """family D (frozen in commit 2 if LEARN-positive): first slot per sym-day-side whose nearest cheap strike (<= 10) has iv_rel <= thr; target k x, stop 50%, time stop ts."""
    out = []
    for (sym, day, side), g in X[(X.p0 <= 10) & (X.iv_rel <= thr)].sort_values("t").groupby(["sym", "day", "side"]):
        r = g.iloc[0]; v = E[(sym, day)]; a = v["C"][(side, r.K)]
        tr = leg(a, v["spot"], sym, day, v["exp"], int(r.t) + 1, float(k), 0.5, ts)
        if tr: out.append(dict(tr, sym=sym, day=day, side=side, K=r.K, t=int(r.t), cfg=f"D iv_rel<={thr} k{k} ts{ts}", fam="D"))
    return pd.DataFrame(out)


def verdict(L, T, alpha, min_learn=(100, 60), min_test=40):
    """the frozen pass rule (sections 7, 12): LEARN mean > 0 p < alpha, both halves > 0, drop3 > 0, 1 lot > 0; TEST n >= 40, net > 0 p < 0.05, placebo(day) < 0.05, forced <= 5%, stress > 0, 1 lot > 0."""
    if L["n"] < min_learn[0] or L["days"] < min_learn[1] or T["n"] < min_test or T.get("days", 0) < 20: return "UNTESTABLE"
    ok = (L["mean"] > 0 and L["p"] < alpha and L.get("loyo_mean", -1) > 0 and L.get("pbo", 1) < 0.5 and L["h1"] > 0 and L["h2"] > 0 and L["drop3"] > 0 and L["mean1"] > 0
          and T["mean"] > 0 and T["p"] < 0.05 and T["pl_day"] < 0.05 and T["forced"] <= 0.05 and T["stress_mean"] > 0 and T["mean1"] > 0)
    return "PASS" if ok else "FAIL"


def study_test():
    import json
    cells = json.load(open(f"{OUT}/playbook/e43_cells_frozen.json")); L = pd.read_csv(f"{OUT}/playbook/e43_cells_learn.csv").set_index("cell")
    P, days = load_full(); E = load(learn=False, P=P); assert all(k[1] >= HO for k in E); print(f"TEST expiry sym-days {len(E)} (read once, {HO}..)", flush=True)
    R = candidates(E, pmax=max(PMAX)); R["spot0"] = [P[(s, d)]["spot"][t] for s, d, t in zip(R.sym, R.day, R.t)]; F = features(R, P, days)
    rg = np.random.default_rng(99); rows = []; alpha = 0.05 / len(cells)
    for c in cells:
        cfg = c["cfg"]
        if c["fam"] == "D": T = trades_D(E, R.join(F), c["thr"], c["k"], c["ts"]); S2 = T.assign(pnl=T.pnl - 2 * TICK * T.sym.map(lambda s_: qty(s_, "2026-01-01")), pnl1=T.pnl1 - 2 * TICK * T.sym.map(lambda s_: qty(s_, "2026-01-01", 1))) if len(T) else T
        else:
            T = trades(E, P, days, F, R, [cfg]); S2 = trades(E, P, days, F, R, [cfg], stress=2 * TICK, chase_b=0.25)
        st = cell_stats(T, c["name"]) if len(T) else dict(cell=c["name"], n=0, days=0, mean=np.nan, p=np.nan, mean1=np.nan, forced=np.nan, win=np.nan, top5_share=np.nan)
        if len(T):
            pc = dict(cfg) if c["fam"] != "D" else dict(fam="D", k=c["k"], ts=c["ts"], pmax=10)
            ms = [placebo_trades(T, pc, E, rg, "day").mean() for _ in range(NPL)]; st["pl_day"] = float(np.mean(np.array(ms) >= st["mean"]))
            st["stress_mean"] = S2.pnl.mean() if len(S2) else np.nan
        st["verdict"] = verdict(L.loc[c["name"]].to_dict(), st, alpha) if c["name"] in L.index and len(T) else "UNTESTABLE"
        rows.append(st); print(f"{c['name']}: TEST n {st['n']} days {st.get('days')} win {st.get('win', float('nan')):.2f} mean {st['mean']:,.0f} p {st.get('p', float('nan')):.4f} 1lot {st.get('mean1', float('nan')):,.0f} placebo(day) {st.get('pl_day', float('nan')):.3f} stress {st.get('stress_mean', float('nan')):,.0f} forced {st.get('forced', float('nan')):.3f} -> {st['verdict']}", flush=True)
    C = pd.DataFrame(rows); C.to_csv(f"{OUT}/playbook/e43_cells_test.csv", index=False); print(f"\nalpha {alpha:.5f}; verdicts: {C.verdict.value_counts().to_dict()}")


if __name__ == "__main__":
    {"atlas": study_atlas, "precursors": study_precursors, "cells": study_cells, "cross": study_cross, "test": study_test, "oicad": lambda: oi_cadence(load(learn=True)), "selftest": selftest}[sys.argv[1]]()
