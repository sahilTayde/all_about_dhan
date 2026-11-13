"""Round-2 loader: Dhan rolling expired-option 1m bars (pull_expired.py output) -> one long parquet.
Rows: sym, side (CE/PE), off (-10..10), ts, day, m (minute of day IST), o h l c vol oi iv (0 -> NaN), spot, strike, exp.
Expiry: nearest weekly per day, inferred from data = first day >= today whose 15:29 ATM straddle extrinsic is ~0.
Run: ~/paper_extra_venv/bin/python scripts/lab5y/opt1y_load.py OUTDIR [--full]
--full (2026-11-13, E39): no date cap and expiry days inferred from the DATA (the day's 15:29 ATM straddle extrinsic ~ 0) instead of the
weekday rule, because the weekly expiry weekday changed over 2021-2026 (NIFTY Thu -> Tue, SENSEX Fri -> Tue -> Thu)."""
import sys, os, re, glob, json, numpy as np, pandas as pd
ROOT = os.environ.get("DHAN_ROOT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
FULL = "--full" in sys.argv

def load():
    rows = []
    for f in sorted(glob.glob(f"{ROOT}/data/cache/expired_opts/*/*.json")):
        sym = f.split("/")[-2]; mt = re.match(r"ATM([+-]\d+)?_(CALL|PUT)_", os.path.basename(f))
        off = int(mt.group(1) or 0); side = "CE" if mt.group(2) == "CALL" else "PE"
        d = (json.load(open(f)).get("data") or {}).get(side.lower()) or {}
        if not d.get("timestamp"): continue
        df = pd.DataFrame({k: d[k] for k in ("timestamp", "open", "high", "low", "close", "volume", "oi", "iv", "spot", "strike")})
        df["sym"], df["side"], df["off"] = sym, side, off; rows.append(df)
    X = pd.concat(rows).drop_duplicates(["sym", "side", "off", "timestamp"])
    t = pd.to_datetime(X.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
    X["day"] = t.dt.strftime("%Y-%m-%d"); X["m"] = (t.dt.hour * 60 + t.dt.minute).astype(np.int16)
    X = X.rename(columns={"timestamp": "ts", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "vol"})
    X.loc[X.iv <= 0, "iv"] = np.nan
    if not FULL: X = X[X.day < "2026-10-26"]  # 10-27 is a partial day (ends 12:32) and its expiry week is incomplete
    else:
        n = X.groupby(["sym", "day"]).m.nunique(); keep = set(n[n >= 300].index)  # drop partial sessions (< 300 minutes)
        X = X[pd.MultiIndex.from_arrays([X.sym, X.day]).isin(keep)]
    return X.sort_values(["sym", "side", "off", "ts"]).reset_index(drop=True)

def expiries(X):
    """per sym: expiry days = days whose ATM straddle extrinsic at last bar <= 0.15% of spot... reported for audit."""
    a = X[(X.off == 0)].sort_values("ts").groupby(["sym", "day", "side"]).tail(1)
    p = a.pivot_table(index=["sym", "day"], columns="side", values=["c", "spot", "strike"], aggfunc="first")
    S, K = p[("spot", "CE")], p[("strike", "CE")]
    ext = p[("c", "CE")] + p[("c", "PE")] - (S - K).abs()
    r = pd.DataFrame({"ext": ext, "ext_pct": ext / S * 100}).reset_index()
    r["wd"] = pd.to_datetime(r.day).dt.day_name().str[:3]
    return r

if __name__ == "__main__":
    X = load(); r = expiries(X)
    for sym, g in r.groupby("sym"):
        # calendar rule: NIFTY Tue / SENSEX Thu; if that day is a holiday, the last trading day before it in that week
        g = g.sort_values("day"); d = pd.to_datetime(g.day); tw = 1 if sym == "NIFTY" else 3
        wk = d.dt.to_period("W-SUN"); g = g.assign(wk=wk.values, wdn=d.dt.weekday.values)
        ex = g.set_index("day").ext_pct
        if FULL:  # data-driven: at most one expiry per ISO week = the day with the smallest ATM straddle extrinsic at 15:29, accepted
            # only if it is clearly below the sym's typical level (expiry ~0.0-0.25% vs 0.3-1.5% on other days); weeks without one
            # (e.g. SENSEX before weekly expiries existed) get no expiry and roll to the next week's
            gg = g.dropna(subset=["ext_pct"]); cut = 0.6 * gg.ext_pct.median()
            e = gg.loc[gg.groupby("wk").ext_pct.idxmin()]; e = e[e.ext_pct < cut].day.tolist()
        else: e = g[g.wdn <= tw].groupby("wk").day.max().tolist()
        print(sym, "days", len(g), "expiries", len(e), "ext% on expiry: max", round(ex[e].max(), 3),
              "| min ext% other days", round(ex.drop(e).min(), 3), "| shifted:", [x for x in e if pd.Timestamp(x).weekday() != tw])
        cal = lambda dd: str((pd.Timestamp(dd) + pd.offsets.Week(weekday=tw)).date())  # after the last data expiry
        nxt = [next((x for x in e if x >= dd), None) or cal(dd) for dd in g.day]
        X.loc[X.sym == sym, "exp"] = X.loc[X.sym == sym, "day"].map(dict(zip(g.day, nxt)))
    r.to_csv(f"{OUT}/expiry_audit.csv", index=False)
    X.to_parquet(f"{OUT}/opt1y.parquet"); print(X.shape, X.day.min(), X.day.max(), "iv NaN %", round(X.iv.isna().mean() * 100, 2))
