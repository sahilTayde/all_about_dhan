"""5y index-1m strategy lab. Entry = next bar open after signal bar close (no look-ahead).
Stop/target on 1m high/low; both in one bar -> stop (conservative). Cost model for buying ITM option, in % of index:
round trip 0.0133% (spread+charges / delta~0.75) + theta 0.0045%/hour held.
Run (needs pandas; repo .venv lacks it): ~/paper_extra_venv/bin/python scripts/lab5y/lab.py [cache_dir]
Source: data/recon/ohlc/INDEX_IDX_I_{13,25,51}_1_*.json (Dhan 1m, 2021-09..2026-09)."""
import sys, os, glob, json, numpy as np, pandas as pd
S = sys.argv[1] if len(sys.argv) > 1 and __name__ == "__main__" else os.environ.get("LAB5Y_CACHE", "data/cache")
if not os.path.exists(f"{S}/idx1m.pkl"):
    out = []
    for sid, n in {"13": "NIFTY", "25": "BANKNIFTY", "51": "SENSEX"}.items():
        for f in sorted(glob.glob(f"data/recon/ohlc/INDEX_IDX_I_{sid}_1_*.json")):
            j = json.load(open(f)); df = pd.DataFrame({k: j[k] for k in ("open", "high", "low", "close", "timestamp")}); df["sym"] = n; out.append(df)
    X = pd.concat(out).drop_duplicates(["sym", "timestamp"]); t = pd.to_datetime(X.timestamp, unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
    X["day"] = t.dt.strftime("%Y-%m-%d"); X["m"] = t.dt.hour * 60 + t.dt.minute
    X[(X.m >= 555) & (X.m <= 929)].sort_values(["sym", "timestamp"]).to_pickle(f"{S}/idx1m.pkl")
D = pd.read_pickle(f"{S}/idx1m.pkl")
D = D[D.sym.isin(["NIFTY", "SENSEX", "BANKNIFTY"])]
DAYS = {}
for (s, d), g in D.groupby(["sym", "day"]):
    if len(g) < 300: continue
    DAYS[(s, d)] = (g.m.values, g.open.values, g.high.values, g.low.values, g.close.values)
KEYS = sorted(DAYS)
RT, TH = 0.000133, 0.000045

def trade(k, i, dirn, stop_pct=None, tgt_pct=None, exit_m=920):
    """enter at open of bar i; returns net return fraction of index (directional) or None."""
    m, o, h, l, c = DAYS[k]
    if i >= len(m) or m[i] >= exit_m: return None
    e = o[i]; sp = e * (1 - dirn * stop_pct) if stop_pct else None; tp = e * (1 + dirn * tgt_pct) if tgt_pct else None
    x = None; j = i
    for j in range(i, len(m)):
        if m[j] >= exit_m: x = o[j]; break
        if sp is not None and ((dirn > 0 and l[j] <= sp) or (dirn < 0 and h[j] >= sp)): x = sp; break
        if tp is not None and ((dirn > 0 and h[j] >= tp) or (dirn < 0 and l[j] <= tp)): x = tp; break
    if x is None: x = c[-1]
    hrs = (m[j] - m[i]) / 60
    return dirn * (x - e) / e - RT - TH * hrs, hrs

def idx_at(m, minute):
    w = np.searchsorted(m, minute); return w

# ---------------- signal generators: yield (key, entry_bar_index, dir) ----------------
def sig_mom(open_end=615, entry=870, thr=0.0):
    for k in KEYS:
        m, o, h, l, c = DAYS[k]
        a = idx_at(m, open_end)
        if a >= len(m) or m[0] > 560: continue
        r = c[a - 1] / o[0] - 1
        if abs(r) < thr: continue
        yield k, idx_at(m, entry), 1 if r > 0 else -1

def sig_orb(or_min=30, last=780):
    for k in KEYS:
        m, o, h, l, c = DAYS[k]
        a = idx_at(m, 555 + or_min)
        if a < 5 or m[0] > 560: continue
        hi, lo = h[:a].max(), l[:a].min()
        for j in range(a, len(m)):
            if m[j] >= last: break
            if c[j] > hi: yield k, j + 1, 1; break
            if c[j] < lo: yield k, j + 1, -1; break

def sig_gap(thr=0.004, fade=True):
    prev = {}
    for k in KEYS:
        s, d = k; m, o, h, l, c = DAYS[k]
        if s in prev:
            g = o[0] / prev[s] - 1
            if abs(g) >= thr: yield k, 1, (-1 if g > 0 else 1) * (1 if fade else -1)
        prev[s] = c[-1]

def sig_vwap_trend(at=660):
    for k in KEYS:
        m, o, h, l, c = DAYS[k]
        a = idx_at(m, at)
        if a < 20 or m[0] > 560: continue
        tp = (h[:a] + l[:a] + c[:a]) / 3; vw = tp.mean()  # index has no volume: equal-weight typical price
        hi, lo = h[:15].max(), l[:15].min()
        if c[a - 1] > vw and c[a - 1] > hi: yield k, a, 1
        elif c[a - 1] < vw and c[a - 1] < lo: yield k, a, -1

def sig_random(src, rng):
    """placebo: same days & entry bars as src, random direction."""
    for k, i, d in src: yield k, i, rng.choice([-1, 1])

def run(sigs, **kw):
    rows = []
    for k, i, d in sigs:
        r = trade(k, i, d, **kw)
        if r: rows.append((k[0], k[1], d, r[0], r[1]))
    return pd.DataFrame(rows, columns=["sym", "day", "dir", "ret", "hrs"])

def summ(df, label):
    out = []
    for per, q in (("IS 21-24", df.day < "2025-01-01"), ("OOS 25-26", df.day >= "2025-01-01")):
        x = df[q].ret
        if len(x) < 5: continue
        t = x.mean() / (x.std() / np.sqrt(len(x)))
        out.append(f"{per}: n={len(x)} win={(x>0).mean():.0%} avg={x.mean()*1e4:+.1f}bp t={t:+.1f}")
    return f"{label:42s} | " + " | ".join(out)

if __name__ == "__main__":
    rng = np.random.default_rng(7)
    tests = {}
    for oe in (615, 645, 735):
        for en in (840, 870, 885):
            for thr in (0, 0.003, 0.006):
                tests[f"MOM first->{oe} enter {en} thr{thr}"] = (lambda oe=oe, en=en, thr=thr: sig_mom(oe, en, thr), {})
    for om in (15, 30, 60):
        for sp in (0.002, 0.004):
            for tg in (None, 0.008):
                tests[f"ORB{om} stop{sp} tgt{tg}"] = (lambda om=om: sig_orb(om), dict(stop_pct=sp, tgt_pct=tg))
    for thr in (0.004, 0.008):
        for fade in (True, False):
            for ex in (615, 920):
                tests[f"GAP{thr} fade={fade} exit{ex}"] = (lambda thr=thr, fade=fade: sig_gap(thr, fade), dict(exit_m=ex, stop_pct=0.004))
    for at in (630, 660, 720):
        tests[f"VWAPTREND at{at}"] = (lambda at=at: sig_vwap_trend(at), dict(stop_pct=0.004))
    for name, (g, kw) in tests.items():
        for sym in ("NIFTY", "SENSEX", "BANKNIFTY"):
            df = run((s for s in g() if s[0][0] == sym), **kw)
            print(summ(df, f"{sym} {name}"), flush=True)
