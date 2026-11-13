"""Indicator / confirmation study on the 1y ATM NIFTY per-minute cache (CE+PE OHLC, OI, volume, IV, spot).
Paper research only. Prints a plain report. Usage: python dext_study.py <cache_dir> [SYM]"""
import sys, json, glob
import numpy as np, pandas as pd
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
root, sym = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "NIFTY")

def load(side, pat):
    rows = []
    for f in sorted(glob.glob(f"{root}/{sym}/{pat}_*.json")):
        d = (json.load(open(f)).get("data") or {}).get(side) or {}
        if not d: continue
        df = pd.DataFrame({k: d[k] for k in ("timestamp", "spot", "strike", "open", "high", "low", "close", "volume", "oi", "iv")})
        rows.append(df)
    df = pd.concat(rows).drop_duplicates("timestamp").sort_values("timestamp")
    dt = pd.to_datetime(df.timestamp, unit="s", utc=True).dt.tz_convert(IST)
    df["day"] = dt.dt.strftime("%Y-%m-%d"); df["min"] = dt.dt.hour * 60 + dt.dt.minute
    return df[(df["min"] >= 555) & (df["min"] < 930)].set_index("timestamp")

ce, pe = load("ce", "ATM_CALL"), load("pe", "ATM_PUT")
m = ce.join(pe, lsuffix="_ce", rsuffix="_pe", how="inner")
m["day"] = m.day_ce; m["min"] = m.min_ce; m["spot"] = m.spot_ce
print(f"{sym}: {len(m)} aligned minutes, {m.day.nunique()} days, {m.day.min()}..{m.day.max()}")

# tick rule signed volume per minute (option)
for s in ("ce", "pe"):
    sgn = np.sign(m[f"close_{s}"].diff()).replace(0, np.nan).ffill().fillna(0)
    m[f"sv_{s}"] = sgn * m[f"volume_{s}"]

m["b"] = (m["min"] - 555) // 5
g = m.groupby(["day", "b"])
b = pd.DataFrame({
    "t": g["min"].first(), "o": g.spot.first(), "h": g.spot.max(), "l": g.spot.min(), "c": g.spot.last(),
    "cec": g.close_ce.last(), "pec": g.close_pe.last(), "ceoi": g.oi_ce.last(), "peoi": g.oi_pe.last(),
    "cev": g.volume_ce.sum(), "pev": g.volume_pe.sum(), "cesv": g.sv_ce.sum(), "pesv": g.sv_pe.sum(),
    "ceiv": g.iv_ce.last(), "peiv": g.iv_pe.last(), "k0": g.strike_ce.first(), "k1": g.strike_ce.last(), "pk0": g.strike_pe.first(), "pk1": g.strike_pe.last(), "n": g.spot.size()}).reset_index()
b = b[b.n >= 3].copy()
b["roll"] = (b.k0 != b.k1) | (b.k0 != b.k0.shift()) | (b.pk0 != b.pk1) | (b.pk0 != b.pk0.shift()) | (b.day != b.day.shift())
b["r"] = b.c - b.c.shift()                      # spot pts, this bar
b["rce"] = b.cec - b.cec.shift(); b["rpe"] = b.pec - b.pec.shift()
b["dceoi"] = b.ceoi - b.ceoi.shift(); b["dpeoi"] = b.peoi - b.peoi.shift()
for k in (1, 3, 6): b[f"f{k}"] = b.c.shift(-k) - b.c   # forward spot pts
same = b.day == b.day.shift(); b.loc[~same, ["r", "rce", "rpe", "dceoi", "dpeoi"]] = np.nan
for k in (1, 3, 6): b.loc[b.day != b.day.shift(-k), f"f{k}"] = np.nan
ok = ~b.roll
expiry = b.groupby("day").k0.transform(lambda s: s.name) if False else None

def hit(x, d):  # fraction of forward moves in direction d
    v = x[np.isfinite(x) & (d != 0)]; dd = d[np.isfinite(x) & (d != 0)]
    return (np.sign(v) == dd).mean() if len(v) else np.nan

print("\n[A] 5m co-movement (same strike, no roll)")
v = b[ok & b.r.notna()]
print(f"  corr(spot, CE) = {v.r.corr(v.rce):.2f}   corr(spot, PE) = {v.r.corr(v.rpe):.2f}   corr(CE, PE) = {v.rce.corr(v.rpe):.2f}")
up = v[v.r > 0]; dn = v[v.r < 0]
print(f"  spot up bars: CE +{up.rce.mean():.2f} / PE {up.rpe.mean():.2f} per bar (median spot +{up.r.median():.1f} pts), ratio |PE|/CE = {abs(up.rpe.mean())/up.rce.mean():.2f}")
print(f"  spot dn bars: CE {dn.rce.mean():.2f} / PE +{dn.rpe.mean():.2f} per bar (median spot {dn.r.median():.1f} pts)")
beta_ce = np.polyfit(v.r, v.rce, 1)[0]; beta_pe = np.polyfit(v.r, v.rpe, 1)[0]
print(f"  option pts per 1 spot pt: CE {beta_ce:.3f}, PE {beta_pe:.3f} (ATM delta read from tape)")
flat = v[v.r.abs() <= 3]
print(f"  flat bars (|spot|<=3 pts, n={len(flat)}): CE {flat.rce.mean():+.2f}, PE {flat.rpe.mean():+.2f} per 5m  <- theta/IV bleed both sides")
dis = v[(np.sign(v.rce) == np.sign(v.rpe)) & (v.rce != 0)]
print(f"  CE and PE move the SAME way in {len(dis)/len(v):.0%} of bars (IV shift dominates spot): next-15m |move| {dis.f3.abs().mean():.1f} vs {v.f3.abs().mean():.1f} all")

print("\n[B] OI build-up matrix (5m): rows = spot bar, cols = CE OI change -> mean next-15m spot pts, hit rate up, n")
for s, nm in (("dceoi", "CE OI"), ("dpeoi", "PE OI")):
    for rs, rl in ((1, "spot up"), (-1, "spot dn")):
        for os_, ol in ((1, "OI up"), (-1, "OI dn")):
            w = v[(np.sign(v.r) == rs) & (np.sign(v[s]) == os_) & v.f3.notna()]
            print(f"  {rl:8s} x {nm} {ol}: next15m {w.f3.mean():+6.1f} pts, up {hit(w.f3.values, np.ones(len(w))):.0%}, n={len(w)}")
print(f"  baseline next-15m: {v.f3.mean():+.1f} pts, up {hit(v.f3.values, np.ones(len(v))):.0%}, n={v.f3.notna().sum()}")

print("\n[C] tick-rule signed option volume (5m) as a direction vote")
for s, nm in (("cesv", "CE signed vol"), ("pesv", "PE signed vol")):
    d = np.sign(v[s]).values * (1 if s == "cesv" else -1)
    print(f"  {nm}: next-5m hit {hit(v.f1.values, d):.1%}, next-15m hit {hit(v.f3.values, d):.1%}, n={int((d != 0).sum())}")
d = np.where((np.sign(v.cesv) > 0) & (np.sign(v.pesv) < 0), 1, np.where((np.sign(v.cesv) < 0) & (np.sign(v.pesv) > 0), -1, 0))
print(f"  CE+ & PE- (or mirror) agree: next-15m hit {hit(v.f3.values, d):.1%}, mean {np.nanmean(v.f3.values*d) if (d!=0).any() else 0:+.1f} pts, n={int((d!=0).sum())}")

# indicators on 5m spot, per day
def ema(x, n): return x.ewm(span=n, adjust=False).mean()
out = []
for day, s in b.groupby("day", sort=True):
    s = s.copy()
    tr = pd.concat([s.h - s.l, (s.h - s.c.shift()).abs(), (s.l - s.c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    up = s.h.diff(); dn = -s.l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdi = 100 * pd.Series(pdm, index=s.index).ewm(alpha=1 / 14, adjust=False).mean() / atr
    mdi = 100 * pd.Series(mdm, index=s.index).ewm(alpha=1 / 14, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    s["adx"] = dx.ewm(alpha=1 / 14, adjust=False).mean()
    rng = s.h.rolling(14).max() - s.l.rolling(14).min()
    s["chop"] = 100 * np.log10(tr.rolling(14).sum() / rng.replace(0, np.nan)) / np.log10(14)
    s["ema21"] = ema(s.c, 21); s["twap"] = s.c.expanding().mean()
    # supertrend 10,3
    hl2 = (s.h + s.l) / 2; a10 = tr.ewm(alpha=1 / 10, adjust=False).mean()
    ub, lb = hl2 + 3 * a10, hl2 - 3 * a10; st = np.zeros(len(s)); dirn = np.ones(len(s)); fu, fl = ub.values.copy(), lb.values.copy()
    c = s.c.values
    for i in range(1, len(s)):
        fu[i] = min(ub.values[i], fu[i - 1]) if c[i - 1] <= fu[i - 1] else ub.values[i]
        fl[i] = max(lb.values[i], fl[i - 1]) if c[i - 1] >= fl[i - 1] else lb.values[i]
        dirn[i] = 1 if c[i] > fu[i - 1] else -1 if c[i] < fl[i - 1] else dirn[i - 1]
    s["st"] = dirn
    # FVG on spot 5m
    s["fvg_bull"] = s.l > s.h.shift(2); s["fvg_bear"] = s.h < s.l.shift(2)
    s["or_h"] = s.h.iloc[:3].max(); s["or_l"] = s.l.iloc[:3].min()
    out.append(s)
b2 = pd.concat(out)
prev = b2.groupby("day").agg(pdh=("h", "max"), pdl=("l", "min")).shift(1)
b2 = b2.join(prev, on="day")
w = b2[(~b2.roll) & b2.f3.notna()]

print("\n[D] regime: ADX-14 / CHOP-14 on 5m spot -> next-30m range and follow-through")
for lo, hi in ((0, 15), (15, 20), (20, 25), (25, 35), (35, 100)):
    q = w[(w.adx >= lo) & (w.adx < hi) & w.f6.notna()]
    cont = (np.sign(q.f6) == np.sign(q.c - q.ema21)).mean()
    print(f"  ADX {lo:2d}-{hi:<3d}: next-30m |move| {q.f6.abs().mean():5.1f} pts, continues EMA21 side {cont:.0%}, n={len(q)}")
for lo, hi in ((0, 38.2), (38.2, 61.8), (61.8, 101)):
    q = w[(w.chop >= lo) & (w.chop < hi) & w.f6.notna()]
    cont = (np.sign(q.f6) == np.sign(q.c - q.ema21)).mean()
    print(f"  CHOP {lo:4.1f}-{hi:<5.1f}: next-30m |move| {q.f6.abs().mean():5.1f} pts, continues EMA21 side {cont:.0%}, n={len(q)}")

print("\n[E] trend filters as direction votes (next-15m spot hit rate, mean pts in vote direction)")
votes = {
    "close vs EMA21": np.sign(w.c - w.ema21), "close vs session TWAP (VWAP proxy)": np.sign(w.c - w.twap),
    "SuperTrend 10/3": w.st, "candle colour": np.sign(w.c - w.o), "prev-day 20-bar bias (c>20-SMA of closes)": np.sign(w.c - w.c.rolling(20).mean()),
}
for nm, d in votes.items():
    d = d.values; print(f"  {nm:44s}: hit {hit(w.f3.values, d):.1%}, mean {np.nanmean(w.f3.values*d):+.1f} pts, n={int((d!=0).sum())}")
d_all = np.sign(np.sign(w.c - w.ema21) + np.sign(w.c - w.twap) + w.st)
agree = (np.sign(w.c - w.ema21) == np.sign(w.c - w.twap)) & (np.sign(w.c - w.twap) == w.st)
d = np.where(agree, d_all, 0)
print(f"  EMA21 + TWAP + SuperTrend all agree                : hit {hit(w.f3.values, d):.1%}, mean {np.nanmean(w.f3.values*d):+.1f} pts, n={int((d!=0).sum())}")
d2 = np.where(agree & (w.adx > 20), d_all, 0)
print(f"  ... and ADX>20                                     : hit {hit(w.f3.values, d2):.1%}, mean {np.nanmean(w.f3.values*d2):+.1f} pts, n={int((d2!=0).sum())}")
d3 = np.where(agree & (w.adx > 20) & (np.sign(w.cesv) == d_all) , d_all, 0)
print(f"  ... and CE signed volume agrees                    : hit {hit(w.f3.values, d3):.1%}, mean {np.nanmean(w.f3.values*d3):+.1f} pts, n={int((d3!=0).sum())}")
d4 = np.where(agree & (w.adx > 20) & (np.sign(w.dceoi) == -d_all), d_all, 0)
print(f"  ... and CE OI falling on up / rising on down (short cover / writing): hit {hit(w.f3.values, d4):.1%}, mean {np.nanmean(w.f3.values*d4):+.1f} pts, n={int((d4!=0).sum())}")
d5 = np.where(agree & (w.adx < 20), d_all, 0)
print(f"  all agree but ADX<20 (chop)                        : hit {hit(w.f3.values, d5):.1%}, mean {np.nanmean(w.f3.values*d5):+.1f} pts, n={int((d5!=0).sum())}")

print("\n[F] fair value gaps on 5m spot (3-candle gap)")
for nm, col, sgn in (("bullish", "fvg_bull", 1), ("bearish", "fvg_bear", -1)):
    q = w[w[col]]
    gap_top = np.where(sgn == 1, q.l, q.l.shift(2)); gap_bot = np.where(sgn == 1, q.h.shift(2), q.h)
    filled = []
    for idx in q.index:
        i = b2.index.get_loc(idx); day = b2.day.iloc[i]; f = False
        for k in range(1, 13):
            if i + k >= len(b2) or b2.day.iloc[i + k] != day: break
            if (sgn == 1 and b2.l.iloc[i + k] <= b2.h.iloc[i - 2]) or (sgn == -1 and b2.h.iloc[i + k] >= b2.l.iloc[i - 2]): f = True; break
        filled.append(f)
    print(f"  {nm}: n={len(q)}, next-15m in gap direction {hit(q.f3.values, np.full(len(q), sgn)):.0%} (mean {np.nanmean(q.f3.values*sgn):+.1f} pts), gap refilled within 1h {np.mean(filled):.0%}")

print("\n[G] levels: first touch of PDH / PDL / opening-range H/L (bar crosses level) -> next-15m")
for nm, lvl, side in (("PDH", "pdh", 1), ("PDL", "pdl", -1), ("OR high", "or_h", 1), ("OR low", "or_l", -1)):
    cross = (side == 1) & (w.h >= w[lvl]) & (w.c.shift() < w[lvl]) | (side == -1) & (w.l <= w[lvl]) & (w.c.shift() > w[lvl])
    q = w[cross & (w.t > 570)]
    q = q.groupby("day").head(1)
    print(f"  {nm}: first touches n={len(q)}, next-15m beyond level (break) {hit(q.f3.values, np.full(len(q), side)):.0%}, mean {np.nanmean(q.f3.values*side):+.1f} pts")

print("\n[H] time of day: next-15m |move| and CE/PE bleed on flat bars")
for lo, hi in ((555, 585), (585, 630), (630, 720), (720, 810), (810, 870), (870, 915)):
    q = w[(w.t >= lo) & (w.t < hi)]; fl = q[q.r.abs() <= 3]
    print(f"  {lo//60:02d}:{lo%60:02d}-{hi//60:02d}:{hi%60:02d}: |next15m| {q.f3.abs().mean():5.1f} pts, flat-bar CE {fl.rce.mean():+.2f} PE {fl.rpe.mean():+.2f}, ADX avg {q.adx.mean():.0f}, n={len(q)}")
