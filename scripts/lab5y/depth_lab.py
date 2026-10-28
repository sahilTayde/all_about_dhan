"""E9 (pre-registered): does order-book imbalance on ATM-near index options predict the option mid
over the next 60 s / 300 s by more than the cost of crossing the spread?
Paper research only: reads data/tape/v2/<day>/depth_quotes.jsonl (streamed line by line). No broker calls.
Usage: ~/paper_extra_venv/bin/python scripts/lab5y/depth_lab.py OUTDIR
Stage 1 caches a 1-second panel per day as OUTDIR/<day>_panel.parquet (skipped if present).
"""
import json, os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd

TAPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/tape/v2")
DAYS = ["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-21", "2026-10-22"]
T0, T1 = "09:20:00", "15:10:00"
DIST = {"NIFTY": 100, "SENSEX": 200}
LOT = {"NIFTY": 65, "SENSEX": 20}
RATE = {"NIFTY": 0.000355299, "SENSEX": 0.000325}
THR, HS, NDRAW, SEED = 0.6, (60, 300), 2000, 7
STALE = 5  # ponytail: as-of fill of a snapshot from the last quote <= 5 s old; beyond that = missing


def build_panel(arg):
    day, OUT = arg
    """Last quote per (instrument, second); index spot ltp per second."""
    path = f"{TAPE}/{day}/depth_quotes.jsonl"
    opt, spot = {}, {}
    with open(path) as f:
        for ln in f:
            isopt = ':CE"' in ln or ':PE"' in ln
            if not isopt and "_IDX:" not in ln: continue
            e = json.loads(ln); p = e["payload"]; iid = p["instrument_id"]; ts = e["timestamp"][:19]
            if not (T0 <= ts[11:] <= T1): continue
            if iid.count(":") == 4:
                lv = p.get("levels") or {}
                b5 = sum(q for _, q in lv.get("bid") or []) or None
                a5 = sum(q for _, q in lv.get("ask") or []) or None
                opt[(iid, ts)] = (p.get("bid"), p.get("ask"), p.get("bid_qty"), p.get("ask_qty"), b5, a5)
            elif "_IDX:" in iid:
                spot[(iid.split(":")[1], ts)] = p.get("ltp")
    df = pd.DataFrame([(k[0], k[1], *v) for k, v in opt.items()], columns="iid ts bid ask bq aq bq5 aq5".split())
    sp = pd.DataFrame([(k[0], k[1], v) for k, v in spot.items()], columns="sym ts spot".split())
    for d in (df, sp): d["ts"] = pd.to_datetime(d["ts"])
    out = f"{OUT}/{day}_panel.parquet"
    df.to_parquet(out); sp.to_parquet(f"{OUT}/{day}_spot.parquet")
    return day


def prep(day):
    df = pd.read_parquet(f"{OUT}/{day}_panel.parquet"); sp = pd.read_parquet(f"{OUT}/{day}_spot.parquet")
    parts = df["iid"].str.split(":", expand=True)
    df["sym"], df["strike"] = parts[1], parts[3].astype(float)
    for c in "bid ask bq aq bq5 aq5".split(): df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[(df.bid > 0) & (df.ask > df.bid)].copy()
    df["mid"] = (df.bid + df.ask) / 2; df["half"] = (df.ask - df.bid) / 2
    df["imb1"] = (df.bq - df.aq) / (df.bq + df.aq)
    df["imb5"] = (df.bq5 - df.aq5) / (df.bq5 + df.aq5)
    df["micro"] = (df.ask * df.bq + df.bid * df.aq) / (df.bq + df.aq) - df.mid
    df = df.sort_values(["iid", "ts"]).reset_index(drop=True)
    # targets: as-of snapshot at t+H (last valid quote in (t+H-STALE, t+H]); strictly future, never beyond t+H
    for H in HS:
        q = df[["iid", "ts"]].copy(); q["tq"] = q.ts + pd.Timedelta(seconds=H); q["row"] = np.arange(len(q))
        q = q.sort_values("tq")
        src = df[["iid", "ts", "mid", "bid"]].rename(columns={"ts": "tsrc", "mid": "m_f", "bid": "b_f"}).sort_values("tsrc")
        m = pd.merge_asof(q, src, left_on="tq", right_on="tsrc", by="iid", direction="backward",
                          tolerance=pd.Timedelta(seconds=STALE - 1)).sort_values("row")
        m.loc[m.tsrc <= m.ts, ["m_f", "b_f", "tsrc"]] = np.nan  # never use the entry snapshot itself
        df[f"dmid{H}"] = m.m_f.values - df.mid.values; df[f"bidx{H}"] = m.b_f.values; df[f"tsrc{H}"] = m.tsrc.values
        ok = df[f"tsrc{H}"].notna()
        lag = (df.loc[ok, f"tsrc{H}"] - df.loc[ok, "ts"]).dt.total_seconds()
        assert (lag > 0).all() and (lag <= H).all(), "target leaks past/beyond horizon"
        SANITY.append((day, H, float(lag.min()) if len(lag) else None, float(lag.max()) if len(lag) else None))
    # ATM-near filter on entry seconds (spot = last index ltp at or before t)
    sp = sp.sort_values("ts"); df = df.sort_values("ts")
    df = pd.merge_asof(df, sp, on="ts", by="sym", direction="backward")
    df = df[(df.strike - df.spot).abs() <= df.sym.map(DIST)]
    return df.sort_values(["iid", "ts"]).reset_index(drop=True)


def charges(buy, sell, sym):
    r = RATE[sym]; turn = buy + sell
    return 1.5 * (40 + r * turn + 0.18 * (40 + r * turn) + 0.00003 * buy + 0.0015 * sell)


def trades(df, H):
    """frozen rule: imb5 > +0.6 -> buy at ask, exit at bid after H s; one open per instrument, cooldown H."""
    rows = []
    for iid, g in df[df.imb5 > THR].groupby("iid", sort=False):
        nxt = None
        for i, t in zip(g.index, g.ts):
            if nxt is not None and t < nxt: continue
            rows.append(i); nxt = t + pd.Timedelta(seconds=H)
    return df.loc[rows]


def pnl(tr, H):
    pts = tr[f"bidx{H}"] - tr.ask
    lot = tr.sym.map(LOT)
    ch = np.array([charges(a * l, b * l, s) for a, b, l, s in zip(tr.ask, tr[f"bidx{H}"].fillna(0), lot, tr.sym)])
    return pts, pts * lot - ch


def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    return np.nan if len(x) < 2 or x.std(ddof=1) == 0 else x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


if __name__ == "__main__":
    OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True); SANITY = []
    have = [d for d in DAYS if os.path.exists(f"{TAPE}/{d}/depth_quotes.jsonl")]
    print("missing files:", [d for d in DAYS if d not in have])
    todo = [d for d in have if not os.path.exists(f"{OUT}/{d}_spot.parquet")]
    if todo:
        with Pool(min(len(todo), 4)) as pool:
            for d in pool.imap_unordered(build_panel, [(d, OUT) for d in todo]): print("cached", d, flush=True)
    days, P = [], {}
    for d in have:
        raw = pd.read_parquet(f"{OUT}/{d}_panel.parquet", columns=["ts"])
        secs = raw.ts.nunique()
        if secs < 3 * 3600: print(f"skip {d}: only {secs} s of option rows"); continue
        P[d] = prep(d); days.append(d)
        print(f"{d}: raw option 1s rows {len(raw)}, option seconds {secs}, ATM-near rows {len(P[d])}, "
              f"instruments {P[d].iid.nunique()}", flush=True)
    print("sanity (day, H, min lag s, max lag s of target source vs entry):", SANITY)

    # 4. information: per-day Spearman IC
    feats, tg = ["imb1", "imb5", "micro"], ["dmid60", "dmid300"]
    ic = []
    for d in days:
        for scope in ("ALL", "NIFTY", "SENSEX"):
            x = P[d] if scope == "ALL" else P[d][P[d].sym == scope]
            for f in feats:
                for t in tg:
                    z = x[[f, t]].dropna()
                    ic.append((d, scope, f, t, z[f].rank().corr(z[t].rank()) if len(z) > 100 else np.nan, len(z)))
    ic = pd.DataFrame(ic, columns="day scope feat target ic n".split()); ic.to_csv(f"{OUT}/ic_by_day.csv", index=False)
    s = ic.groupby(["scope", "feat", "target"]).ic.agg(mean_ic="mean", t=tstat, days="count").reset_index()
    s.to_csv(f"{OUT}/ic_summary.csv", index=False); print("\nIC summary\n", s.round(4).to_string(index=False))

    # 5-6. rule vs random
    rng = np.random.default_rng(SEED); res = []; miss = []
    for H in HS:
        for sym in ("NIFTY", "SENSEX"):
            sig_pts, sig_net, rnd_pts_draws, rnd_net_draws, day_sig, day_rnd = [], [], [], [], [], []
            for d in days:
                x = P[d][P[d].sym == sym]
                tr = trades(x, H)
                miss.append((d, sym, H, len(tr), int(tr[f"bidx{H}"].isna().sum())))
                tr = tr[tr[f"bidx{H}"].notna()]
                if len(tr) == 0: continue
                p, n = pnl(tr, H); sig_pts.append(p.values); sig_net.append(n.values); day_sig.append(n.mean())
                pool_ = x[x[f"bidx{H}"].notna()]
                pp, nn = pnl(pool_, H); pp, nn = pp.values, nn.values
                idx = rng.integers(0, len(pool_), size=(NDRAW, len(tr)))
                rnd_pts_draws.append(pp[idx]); rnd_net_draws.append(nn[idx]); day_rnd.append(nn[idx].mean())
            if not sig_pts: continue
            sp_, sn = np.concatenate(sig_pts), np.concatenate(sig_net)
            rp, rn = np.concatenate(rnd_pts_draws, axis=1), np.concatenate(rnd_net_draws, axis=1)
            rmean_n = rn.mean(axis=1); rmean_p = rp.mean(axis=1)
            res.append(dict(H=H, sym=sym, n=len(sp_), days=len(day_sig), mean_pts=sp_.mean(), mean_net_rs=sn.mean(),
                            t_trades=tstat(sn), t_days=tstat(day_sig), rnd_mean_pts=rmean_p.mean(),
                            rnd_mean_net_rs=rmean_n.mean(), diff_pts=sp_.mean() - rmean_p.mean(),
                            diff_net_rs=sn.mean() - rmean_n.mean(),
                            p_vs_random=(1 + (rmean_p >= sp_.mean()).sum()) / (NDRAW + 1),
                            win_share_net=(sn > 0).mean()))
    res = pd.DataFrame(res); res.to_csv(f"{OUT}/rule_vs_random.csv", index=False)
    print("\nRule (imb5>+0.6 buy at ask, exit bid after H) vs random (same count/day, seed 7, 2000 draws)\n",
          res.round(3).to_string(index=False))
    miss = pd.DataFrame(miss, columns="day sym H signals exit_missing".split()); miss.to_csv(f"{OUT}/exit_missing.csv", index=False)
    g = miss.groupby(["sym", "H"])[["signals", "exit_missing"]].sum(); g["share"] = g.exit_missing / g.signals
    print("\nexit snapshot missing\n", g.round(4).to_string())
