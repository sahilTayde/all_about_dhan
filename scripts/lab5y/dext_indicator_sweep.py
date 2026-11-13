"""Parameter sweep: does any length / combination of the DEXT chart indicators change the next-15m hit rate?
1y ATM cache, 5m bars, NIFTY + SENSEX. Also CE/PE premium co-movement by 1m/5m/15m/30m bar size. Paper research only."""
import sys, json, glob
import numpy as np, pandas as pd
from datetime import timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30)); root = sys.argv[1]

def load(sym, side, pat):
    rows = []
    for f in sorted(glob.glob(f"{root}/{sym}/{pat}_*.json")):
        d = (json.load(open(f)).get("data") or {}).get(side) or {}
        if d: rows.append(pd.DataFrame({k: d[k] for k in ("timestamp", "spot", "strike", "close", "volume", "oi", "iv")}))
    df = pd.concat(rows).drop_duplicates("timestamp").sort_values("timestamp")
    dt = pd.to_datetime(df.timestamp, unit="s", utc=True).dt.tz_convert(IST)
    df["day"] = dt.dt.strftime("%Y-%m-%d"); df["min"] = dt.dt.hour * 60 + dt.dt.minute
    return df[(df["min"] >= 555) & (df["min"] < 930)].set_index("timestamp")

def bars(m, n):
    m = m.copy(); m["b"] = (m["min"] - 555) // n
    g = m.groupby(["day", "b"])
    b = pd.DataFrame({"t": g["min"].first(), "o": g.spot.first(), "h": g.spot.max(), "l": g.spot.min(), "c": g.spot.last(),
                      "cec": g.close_ce.last(), "pec": g.close_pe.last(), "k": g.strike_ce.first(), "k1": g.strike_ce.last(),
                      "pk": g.strike_pe.first(), "pk1": g.strike_pe.last(), "n": g.spot.size()}).reset_index()
    b = b[b.n >= max(1, n // 2)].copy()
    b["roll"] = (b.k != b.k1) | (b.k != b.k.shift()) | (b.pk != b.pk1) | (b.pk != b.pk.shift()) | (b.day != b.day.shift())
    for col, src in (("r", "c"), ("rce", "cec"), ("rpe", "pec")): b[col] = b[src] - b[src].shift()
    b.loc[b.day != b.day.shift(), ["r", "rce", "rpe"]] = np.nan
    return b

def hit(f, d):
    ok = np.isfinite(f) & (d != 0); return (np.sign(f[ok]) == d[ok]).mean() if ok.any() else np.nan, int(ok.sum())

for sym in ("NIFTY", "SENSEX"):
    ce, pe = load(sym, "ce", "ATM_CALL"), load(sym, "pe", "ATM_PUT")
    m = ce.join(pe, lsuffix="_ce", rsuffix="_pe", how="inner"); m["day"] = m.day_ce; m["min"] = m.min_ce; m["spot"] = m.spot_ce
    print(f"\n===== {sym} =====")
    print("[1] CE / PE premium vs index by bar size (same strike, no roll): corr, option pts per index pt, |PE|/CE on up bars, CE&PE same-way share")
    for n in (1, 5, 15, 30):
        b = bars(m, n); v = b[~b.roll & b.r.notna() & (b.r != 0)]
        up = v[v.r > 0]; bce = np.polyfit(v.r, v.rce, 1)[0]; bpe = np.polyfit(v.r, v.rpe, 1)[0]
        same = ((np.sign(v.rce) == np.sign(v.rpe)) & (v.rce != 0)).mean()
        print(f"  {n:2d}m: corr spot-CE {v.r.corr(v.rce):.2f} spot-PE {v.r.corr(v.rpe):.2f} CE-PE {v.rce.corr(v.rpe):.2f} | CE {bce:.3f} PE {bpe:.3f} per pt | |PE|/CE up {abs(up.rpe.mean())/up.rce.mean():.2f} | same-way {same:.0%} | n={len(v)}")
    b = bars(m, 5)
    # per-day indicator sweep on 5m
    def ind(s):
        s = s.copy(); tr = pd.concat([s.h - s.l, (s.h - s.c.shift()).abs(), (s.l - s.c.shift()).abs()], axis=1).max(axis=1)
        for L in (7, 14, 21, 28):
            atr = tr.ewm(alpha=1 / L, adjust=False).mean(); up = s.h.diff(); dn = -s.l.diff()
            pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=s.index); mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=s.index)
            pdi = 100 * pdm.ewm(alpha=1 / L, adjust=False).mean() / atr; mdi = 100 * mdm.ewm(alpha=1 / L, adjust=False).mean() / atr
            s[f"adx{L}"] = (100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)).ewm(alpha=1 / L, adjust=False).mean()
            s[f"di{L}"] = np.sign(pdi - mdi)
        for L in (9, 21, 50): s[f"ema{L}"] = s.c.ewm(span=L, adjust=False).mean()
        s["vwap"] = ((s.h + s.l + s.c) / 3).expanding().mean()
        for (P, M) in ((10, 3), (10, 2), (7, 3), (14, 2)):
            hl2 = (s.h + s.l) / 2; a = tr.ewm(alpha=1 / P, adjust=False).mean(); ub, lb = (hl2 + M * a).values, (hl2 - M * a).values
            c = s.c.values; d = np.ones(len(s)); fu, fl = ub.copy(), lb.copy()
            for i in range(1, len(s)):
                fu[i] = min(ub[i], fu[i - 1]) if c[i - 1] <= fu[i - 1] else ub[i]; fl[i] = max(lb[i], fl[i - 1]) if c[i - 1] >= fl[i - 1] else lb[i]
                d[i] = 1 if c[i] > fu[i - 1] else -1 if c[i] < fl[i - 1] else d[i - 1]
            s[f"st{P}_{M}"] = d
        for L in (7, 14, 21): s[f"rsi{L}"] = 100 - 100 / (1 + s.c.diff().clip(lower=0).ewm(alpha=1 / L, adjust=False).mean() / (-s.c.diff().clip(upper=0)).ewm(alpha=1 / L, adjust=False).mean())
        for L in (3, 6): s[f"mom{L}"] = np.sign(s.c - s.c.shift(L))
        return s
    b = pd.concat(ind(s) for _, s in b.groupby("day", sort=True))
    for k in (3, 6): b[f"f{k}"] = b.c.shift(-k) - b.c; b.loc[b.day != b.day.shift(-k), f"f{k}"] = np.nan
    w = b[~b.roll & b.f3.notna()]; f3 = w.f3.values
    print("[2] single votes, next-15m hit (50% = coin), n")
    votes = {}
    for L in (9, 21, 50): votes[f"close>EMA{L}"] = np.sign(w.c - w[f"ema{L}"]).values
    votes["close>VWAP(hlc3)"] = np.sign(w.c - w.vwap).values
    for P, M in ((10, 3), (10, 2), (7, 3), (14, 2)): votes[f"SuperTrend {P}/{M}"] = w[f"st{P}_{M}"].values
    for L in (7, 14, 21, 28): votes[f"+DI>-DI ({L})"] = w[f"di{L}"].values
    for L in (7, 14, 21): votes[f"RSI{L}>50"] = np.sign(w[f"rsi{L}"] - 50).values
    for L in (3, 6): votes[f"momentum {L} bars"] = w[f"mom{L}"].values
    votes["RSI14<30 -> long / >70 -> short (mean reversion)"] = np.where(w.rsi14 < 30, 1, np.where(w.rsi14 > 70, -1, 0))
    votes["EMA9 vs EMA21 cross state"] = np.sign(w.ema9 - w.ema21).values
    for nm, d in votes.items():
        h, n = hit(f3, d); print(f"  {nm:48s} {h:.1%}  mean {np.nanmean(f3 * d):+.2f} pts  n={n}")
    print("[3] combinations gated by ADX (trend filter) — hit, mean, n")
    base = np.sign(np.sign(w.c - w.ema21) + np.sign(w.c - w.vwap) + w.st10_3).values
    agree = ((np.sign(w.c - w.ema21) == np.sign(w.c - w.vwap)) & (np.sign(w.c - w.vwap) == w.st10_3)).values
    for L in (7, 14, 21, 28):
        for th in (15, 20, 25, 30):
            d = np.where(agree & (w[f"adx{L}"].values > th), base, 0); h, n = hit(f3, d)
            print(f"  EMA21+VWAP+ST agree & ADX{L}>{th}: {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    d = np.where(agree & (w.rsi14.values > 50) == (base > 0), base, 0); h, n = hit(f3, d); print(f"  ... & RSI14 same side: {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    d = np.where(agree & (w.mom3.values == base), base, 0); h, n = hit(f3, d); print(f"  ... & 3-bar momentum same side: {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    d = np.where(agree & (w.t.values < 660), base, 0); h, n = hit(f3, d); print(f"  ... & before 11:00: {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    d = np.where(agree & (w.t.values >= 870), base, 0); h, n = hit(f3, d); print(f"  ... & after 14:30: {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    d = -base * agree; h, n = hit(f3, d); print(f"  FADE all three (contrarian): {h:.1%} mean {np.nanmean(f3*d):+.2f} n={n}")
    print("[4] 30-minute follow-through of the same votes (next-30m hit)")
    f6 = w.f6.values
    for nm in ("close>EMA21", "close>VWAP(hlc3)", "SuperTrend 10/3", "+DI>-DI (14)", "RSI14>50"):
        h, n = hit(f6, votes[nm]); print(f"  {nm:28s} {h:.1%} mean {np.nanmean(f6*votes[nm]):+.2f} n={n}")
    print("[5] best / worst single vote spread over 2 halves of the year (stability)")
    half = (w.day < sorted(w.day.unique())[len(w.day.unique()) // 2]).values
    for nm in ("close>EMA21", "close>VWAP(hlc3)", "SuperTrend 10/3", "RSI14>50", "momentum 3 bars"):
        d = votes[nm]; h1, n1 = hit(f3[half], d[half]); h2, n2 = hit(f3[~half], d[~half]); print(f"  {nm:28s} H1 {h1:.1%} (n={n1})  H2 {h2:.1%} (n={n2})")
