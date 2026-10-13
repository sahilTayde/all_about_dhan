"""Premium-stop BACKGROUND SHADOWS, live job (PAPER/RESEARCH ONLY; no broker calls; never desk rows).
Usage: pshadow_live.py SNAPDIR   (SNAPDIR holds a snapshot of ~/paper_extra_rt/live/work: base_1m_aug.parquet, opt1m_<DAY>.parquet, vix_daily.json,
all already cut at the last COMPLETE minute by build_day). Writes SNAPDIR/pshadow_latest.json.
Signals = Research's own code (same calls proven on history: EP-009 443/443, B2 62/62, VWAP_CONT 2478/2478 signals);
exits = desk_ml.premium_shadow.exit_one (port of ps_a.py one(), 1156/1156 trades matched)."""
import sys, os, types, json, traceback, numpy as np, pandas as pd
sys.dont_write_bytecode = True
SNAP = os.path.abspath(sys.argv[1]); DAY = os.environ["PX_DAY"]; EXP = os.environ.get("PX_EXP", DAY)
LAB = os.path.expanduser("~/paper_extra_rt/dhan/research/lab"); sys.path[:0] = [LAB + "/lib", LAB]
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")); sys.path.insert(0, REPO + "/packages/desk-ml/src")
from desk_ml import premium_shadow as PS
_rp = pd.read_parquet
VIXX = json.load(open(SNAP + "/vix_daily.json")) if os.path.exists(SNAP + "/vix_daily.json") else {}
def rp(p, *a, **k):
    p = str(p)
    if p.endswith("lab_round7b/base_1m.parquet"): p = SNAP + "/base_1m_aug.parquet"
    df = _rp(p, *a, **k)
    if p.endswith("global_daily.parquet"):
        df["date"] = df.date.astype(str).str[:10]; add = [d for d in VIXX if d not in set(df.date)]
        if add: df = pd.concat([df, pd.DataFrame({"date": add, "INDIAVIX": [VIXX[d] for d in add]})], ignore_index=True).sort_values("date").reset_index(drop=True)
    return df
pd.read_parquet = rp
def load_mod(name, path, subs=()):
    src = open(path).read()
    for a, b in subs:
        assert a in src, (path, a); src = src.replace(a, b)
    m = types.ModuleType(name); m.__file__ = path; sys.modules[name] = m; cwd = os.getcwd(); os.chdir(os.path.dirname(path))
    try: exec(compile(src, path, "exec"), m.__dict__)
    finally: os.chdir(cwd)
    return m
BA = _rp(SNAP + "/base_1m_aug.parquet"); TD = BA[BA.day == DAY].sort_values("m").set_index("m"); LASTM = int(TD.index.max())
OPT = _rp(SNAP + f"/opt1m_{DAY}.parquet"); OPT = OPT[(OPT.symbol == "NIFTY") & (OPT.expiry == EXP)]
OB = {(int(k), o): {int(m): (float(a), float(c)) for m, a, c in zip(g.m, g.open, g.close)} for (k, o), g in OPT.groupby(["strike", "option_type"])}
SIG = []; ERR = {}; SKIP = []
def hm(m): return None if m is None else f"{int(m)//60:02d}:{int(m)%60:02d}"
def ep009():
    sys.path[:0] = [LAB + "/2026-10-11_tv_ep23"]
    EP = load_mod("engine", LAB + "/2026-10-11_tv_ep23/engine.py", [('M = M[M.groupby("day").m.transform("size") >= 300]', f'M = M[(M.groupby("day").m.transform("size") >= 300) | (M.day == "{DAY}")]')])
    EPP = load_mod("ports", LAB + "/2026-10-11_tv_ep23/ports.py"); TR = pd.read_csv(LAB + "/2026-10-11_tv_ep23/test_results.csv")
    B = EP.bars(int(TR[TR.ep == "EP-009"].tf.iloc[0])); T = EP.run(EPP.PORTS["EP-009"](B), B)
    for r in T.itertuples():   # signals.py add(): 571<=MM[f]<=886 and p0 finite > 1; hold = MM[x]-MM[f]
        f, x = int(r.f), int(r.x)
        if EP.DAY[f] != DAY or not (571 <= EP.MM[f] <= 886): continue
        p0 = EP.p0_at(r.sg, f, r.S0)
        if not np.isfinite(p0) or p0 <= 1: continue
        e = f + 1 if f + 1 < len(EP.DAY) and EP.DAY[f + 1] == DAY else None
        if e is None and LASTM < 915: SIG.append(dict(name="EP009_P", sig_m=int(EP.MM[f]), sg=int(r.sg), pending="waiting for entry minute")); continue
        e = f if e is None else e
        known = int(EP.MM[x]) < LASTM or LASTM >= 915
        SIG.append(dict(name="EP009_P", sig_m=int(EP.MM[f]), sg=int(r.sg), e_m=int(EP.MM[e]), sref=float(EP.O[e]), hold=int(EP.MM[x]) - int(EP.MM[f]), capx=None, known=known))
def b2():
    sys.path[:0] = [LAB + "/2026-10-11_stress", LAB + "/2026-10-11_range_boxes", LAB + "/2026-10-11_bigmove_re"]
    S = load_mod("stress", LAB + "/2026-10-11_stress/stress.py", [("len(g)>=300]", f"(len(g)>=300 or d==\"{DAY}\")]")])
    from path1m import run_path_sf
    assert S.days[-1] == DAY, S.days[-1]; k = len(S.days) - 1; g = S.GD[DAY]; x = TD.reindex(g.m.values)
    o, h, l = (x[c].values.astype(float) for c in ("open", "high", "low")); c = g.close.values.astype(float); m = g.m.values.astype(int); tw = g.twap.values.astype(float)
    for e, sg, kw, itm in S.B2(k, g, S.RULES["B2"][1]):   # hist_b2q01.py sim(), exit minute only
        if e is None or (e >= len(g) - 2 and LASTM < 915): continue
        p0 = (g.ce_c if sg > 0 else g.pe_c).values[e]
        if not np.isfinite(p0) or p0 <= 1: SKIP.append(dict(name="B2_P", sig_m=int(m[e]), sg=int(sg), why="no ATM premium at entry (research skips too)")); continue
        dl = .54
        if itm == "ITM100": p0 += 54
        elif itm: p0 += 27; dl = .60
        kw = dict(kw); sf = kw.pop("stop_frac", None)
        if sf: kw["stop_pts"] = sf * p0 / dl
        z, lvl, st = run_path_sf(o, h, l, c, m, tw, e, sg, **kw)
        known = bool(st) or int(m[z]) < LASTM or LASTM >= 915
        SIG.append(dict(name="B2_P", sig_m=int(m[e]), sg=int(sg), e_m=int(m[e]), sref=float(o[e]), hold=None, capx=int(m[z]), known=known))
def vwap_pe():
    C = load_mod("common", LAB + "/2026-10-12_realprice/v2_candle/common.py", [("if not np.isfinite(A) or A <= 0 or len(g) < 300: continue", f"if not np.isfinite(A) or A <= 0 or (len(g) < 300 and d != \"{DAY}\"): continue")])
    G = C.load(); CX = C.context(G); assert DAY in CX, "no context for today"; g = G[DAY]; X = CX[DAY]; m = g.m.values; last, cnt = -999, 0
    for t, sg, stop in C.signals("VWAP_CONT", g, X):   # run.py: CAP/GAP counted on both sides, trade() must exist
        if cnt >= C.CAP or m[t] - last < C.GAP: continue
        e = t + 1
        if e >= len(m): SIG.append(dict(name="VWAPCONT_PE_P", sig_m=int(m[t]), sg=int(sg), pending="waiting for entry minute")) if sg < 0 else None; continue
        S0 = g.open.values[e]; R = sg * (S0 - stop)
        if R < C.RMIN * X["A"]: R = C.RMIN * X["A"]
        if R > C.RMAX * X["A"]: continue
        p0 = (g.ce_o if sg > 0 else g.pe_o).values[e]
        if not np.isfinite(p0) or p0 <= 1: continue
        last, cnt = m[t], cnt + 1
        if sg < 0: SIG.append(dict(name="VWAPCONT_PE_P", sig_m=int(m[t]), sg=-1, e_m=int(m[e]), sref=float(S0), hold=30, capx=None, known=True))
for nm, fn in (("EP009_P", ep009), ("B2_P", b2), ("VWAPCONT_PE_P", vwap_pe)):
    try: fn()
    except Exception as ex: ERR[nm] = f"{type(ex).__name__}: {ex}"; traceback.print_exc()
rows, need = [], set()
for s in SIG:
    st_, off, S, k, dl, pe = PS.CONFIGS[s["name"]]; side = "CE" if s["sg"] > 0 else "PE"
    r = dict(name=s["name"], research_strat=st_, side=side, signal_ist=hm(s["sig_m"]), off=off, S=S, k=k)
    if "pending" in s: r.update(status="PENDING_ENTRY", note=s["pending"]); rows.append(r); continue
    K = PS.strike(s["sref"], s["sg"], off); r.update(strike=K, sref=s["sref"]); need.add(K)
    b = OB.get((K, side))
    if b is None: r.update(status="PENDING_DATA", note=f"{K}{side} not fetched yet (pinned for next cycle)"); rows.append(r); continue
    x = PS.exit_one(b, s["e_m"], S, k, hold=s["hold"], capx=s["capx"], cap_known=s["known"], last=LASTM)
    r.update(x); rows.append(r)
json.dump(dict(day=DAY, exp=EXP, last_m=LASTM, data_through=hm(LASTM), rows=rows, need_strikes=sorted(need), errors=ERR,
               skipped=[dict(k, signal_ist=hm(k['sig_m'])) for k in SKIP]),
          open(SNAP + "/pshadow_latest.tmp", "w"), indent=1)
os.replace(SNAP + "/pshadow_latest.tmp", SNAP + "/pshadow_latest.json")
print("pshadow", DAY, "through", hm(LASTM), "rows", len(rows), "skipped", len(SKIP), "errors", ERR)
