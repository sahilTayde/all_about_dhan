"""Known-answer checks for the log-only shadow leads in fin1_shadow.py (B1 NR4 stretch, SC1, LOC20/TREND labels, S1 tag).
Hand-computed synthetic cases (costs from a2_known_answer.hand_cost = config/charges.yaml), a cross-check of lead_feats against
book_lab.daily (nr4, stretch, rr1) and scen_lab.dfeat (LOC20, TREND) on a random-walk index history, and an assert that the FIN1/S2
fields of day_rows do not move when the leads are switched on. Importing a2_known_answer runs its tests first.
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python shadow_leads_known_answer.py"""
import os, tempfile, numpy as np, pandas as pd

T0 = tempfile.mkdtemp(); R = np.random.RandomState(3); rows = []
for sym in ("NIFTY", "SENSEX"):  # 60 weekdays of random-walk 1m bars, before the a2 panel days (2026-01-05..)
    for day in pd.bdate_range("2025-10-01", periods=60).strftime("%Y-%m-%d"):
        c = 20000 + R.randn() * 400 + np.cumsum(R.randn(375) * 6); o = np.r_[c[0], c[:-1]]
        rows += [(sym, day, 555 + i, o[i], max(o[i], c[i]) + abs(R.randn()) * 3, min(o[i], c[i]) - abs(R.randn()) * 3, c[i]) for i in range(375)]
IDXP = f"{T0}/idx1m.pkl"; pd.DataFrame(rows, columns=["sym", "day", "m", "open", "high", "low", "close"]).to_pickle(IDXP)
os.environ["IDX5Y"] = IDXP  # opt1y_lab (imported by a2) reads it at import
import a2_known_answer as A  # noqa: E402
import book_lab as B  # noqa: E402
import ast  # scen_lab needs >= 148 panel days at import: take just BK / tri / dfeat from its source
_t = ast.parse(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scen_lab.py")).read())
SC = type("SC", (), {}); _ns = dict(np=np, pd=pd)
exec(compile(ast.Module([n for n in _t.body if (isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "BK") or (isinstance(n, ast.FunctionDef) and n.name in ("tri", "dfeat"))], []), "scen_lab", "exec"), _ns); SC.dfeat = _ns["dfeat"]
F, hand_cost, eq = A.F, A.hand_cost, A.eq
fl = lambda **kw: dict(dict(oc=100, hc=105, lc=95, c=100, H=106, L=94), **kw)
bars = lambda days: [tuple(d[k] for k in ("oc", "hc", "lc", "c", "H", "L")) for d in days]

# ---- 1. hand cases. 20 days: open 100, range 95..105 (10), stretch 5, H/L 106/94, close 100; yesterday (the 21st) varies.
def feats(**last): return F.lead_feats(bars([fl()] * 20 + [fl(**last)]))
y = dict(hc=103, lc=97, H=104, L=96, c=105)  # range 6, stretch min(3,3)=3, close at 105 in [94,106]
f = feats(**y)
assert f["nr4"] and abs(f["stretch"] - (9 * 5 + 3) / 10) < 1e-12 and abs(f["rr1"] - 0.6) < 1e-12, f   # 6/mean(20 x 10)
assert f["loc20"] == "HIGH" and f["trend"] == "UP", f   # (105-94)/(106-94)=0.917 >= 0.8; 105 > (19*100+105)/20
f = feats(**dict(y, c=96)); assert f["loc20"] == "LOW" and f["trend"] == "DN", f   # 0.167 <= 0.2; 96 < 99.8
assert feats(**dict(y, c=100))["loc20"] == "MID"   # 0.5
assert feats(**dict(y, c=97.1))["loc20"] == "MID" and feats(**dict(y, c=96.3))["loc20"] == "LOW"   # 0.258 (MID) and 0.19 (LOW)
# exact cut edges: LOC20 0.8 -> HIGH and 0.2 -> LOW (<=/>= as scen_lab), flat 20-day range -> no label (0/0 in scen_lab)
e = lambda c, H=110, L=100: F.lead_feats(bars([fl(H=H, L=L)] * 20 + [fl(H=H, L=L, c=c)]))["loc20"]
assert e(108) == "HIGH" and e(102) == "LOW" and e(107.9) == "MID" and e(102.1) == "MID" and e(100, 100, 100) is None
assert feats(hc=103.5, lc=96.5)["rr1"] == 0.7   # exactly 7 / 10
# NR4: yesterday must be <= the smallest of the last 4 ranges (ties count), here day -2 has range 8
assert feats(hc=105, lc=95)["nr4"]  # tie at 10 with days -2..-4
dd = [fl()] * 18 + [fl(hc=104, lc=96), fl()]; dd = bars(dd + [fl()]); assert not F.lead_feats(dd)["nr4"]  # range 10 > 8
# SC1 cut at 0.7 x the mean of the 20 before (10): range 6.9 yes, 7.1 no
assert feats(hc=103.45, lc=96.55)["rr1"] < 0.7 and feats(hc=103.55, lc=96.45)["rr1"] > 0.7
# stretch is the 10-day mean of min(h-o, o-l): one old day with stretch 1 only counts inside the last 10
a = [fl(hc=101)] + [fl()] * 20; assert F.lead_feats(bars(a))["stretch"] == 5.0   # day -21 is outside the 10 (and the 21-bar window)
a = [fl()] * 11 + [fl(hc=101)] + [fl()] * 9; assert abs(F.lead_feats(bars(a))["stretch"] - (9 * 5 + 1) / 10) < 1e-12  # day -10 is inside
assert F.lead_feats(bars([fl()] * 20)) is None and F.lead_feats(bars([fl()] * 20 + [fl(c=float("nan"))])) is None   # < 21 days / NaN: no label

# ---- 2. B1 trade: NIFTY, step 50, ATM 22700 (hand: buy ask at the first quote >= signal minute+1, sell bid at the first quote >= exit minute)
def day_sp(**ch): return {_t: 22700.0 for _t in [A.F._hm(i) for i in range(375)]} | ch
def qs(ce, pe=((), )):
    return {("NIFTY", 22700.0, "CE"): [(t, b, a, "2026-01-06") for t, b, a in ce], ("NIFTY", 22700.0, "PE"): [(t, b, a, "2026-01-06") for t, b, a in (pe if pe != ((),) else ce)]}
Q = 650
ce = [("09:25:05", 90, 95), ("09:26:05", 99, 101), ("10:00:03", 70, 72), ("10:01:03", 80, 82),  # quotes at the trigger/breach minute AND the next one
       ("11:01:00", 130, 132), ("15:15:02", 90, 92)]
# stretch 40: the 09:25 close 22740 >= open + 40 -> buy CE at 09:26 (ask 101); spot at 09:26 is 22742 (s0); stop = 2*40/50 = 1.6 steps = 80 pts
sp = day_sp(**{"09:25": 22740.0, "09:26": 22742.0}); sp |= {A.F._hm(i): 22742.0 for i in range(12, 375)}
r = F.b1_trade("NIFTY", sp | {"10:00": 22742.0 - 80.001}, qs(ce), 40.0)   # 80.001 below s0 at 10:00 -> exit at the first quote >= 10:01
assert r[0] == "TRADE" and r[2] == "CE" and r[3] == "spot_stop" and r[4] == "09:26:05", r
eq(r[1], (80 - 101) * Q - hand_cost(101, 80), "B1 stop")
r = F.b1_trade("NIFTY", sp | {"10:00": 22742.0 - 79.0}, qs(ce), 40.0); assert r[3] == "time", r   # 79 pts < 1.6 steps: held to 15:15
eq(r[1], (90 - 101) * Q - hand_cost(101, 90), "B1 time exit")
r = F.b1_trade("NIFTY", sp | {"10:00": 22742.0 + 125.0}, qs(ce), 40.0); assert r[3] == "spot_tgt", r   # +2.5 steps, exit first quote >= 10:01
eq(r[1], (80 - 101) * Q - hand_cost(101, 80), "B1 target (2.5 steps)")
r = F.b1_trade("NIFTY", sp | {"10:00": 22742.0 + 124.0}, qs(ce), 40.0); assert r[3] == "time", r
# the stop is capped at 2.5 steps (stretch 100 -> 2*100/50 = 4 -> 2.5) and floored at 0.5 (stretch 10 -> 0.4 -> 0.5)
spb = day_sp(**{"09:25": 22800.0, "09:26": 22800.0}) | {A.F._hm(i): 22800.0 for i in range(12, 375)}
assert F.b1_trade("NIFTY", spb | {"10:00": 22800 - 124.0}, qs(ce), 100.0)[3] == "time" and F.b1_trade("NIFTY", spb | {"10:00": 22800 - 126.0}, qs(ce), 100.0)[3] == "spot_stop"
spc = day_sp(**{"09:25": 22710.0, "09:26": 22710.0}) | {A.F._hm(i): 22710.0 for i in range(12, 375)}
assert F.b1_trade("NIFTY", spc | {"10:00": 22710 - 24.0}, qs(ce), 10.0)[3] == "time" and F.b1_trade("NIFTY", spc | {"10:00": 22710 - 26.0}, qs(ce), 10.0)[3] == "spot_stop"
# PE side: first close at or below open - stretch; the trigger is the first one in time (a CE trigger later is ignored)
spp = day_sp(**{"09:20": 22659.0, "09:21": 22700.0, "09:30": 22745.0}); r = F.b1_trade("NIFTY", spp, qs(ce, [("09:21:01", 50, 52), ("15:15:00", 60, 62)]), 40.0)
assert r[2] == "PE" and r[4] == "09:21:01", r; eq(r[1], (60 - 52) * Q - hand_cost(52, 60), "B1 PE")
# window: no trigger before 09:20 (bar 5) or after 14:00 (bar 285)
assert F.b1_trade("NIFTY", day_sp(**{"09:19": 22745.0}), qs(ce), 40.0) == ("NO_CROSS",) and F.b1_trade("NIFTY", day_sp(**{"14:01": 22745.0}), qs(ce), 40.0) == ("NO_CROSS",)
assert F.b1_trade("NIFTY", day_sp(**{"14:00": 22745.0}), qs(ce), 40.0)[0] in ("TRADE", "NO_QUOTES")   # 14:00 is the last decision bar
assert F.b1_trade("NIFTY", {k: v for k, v in sp.items() if k > "09:17"}, qs(ce), 40.0) == ("NO_SPOT",)   # open not on tape: not a trade

# ---- 3. leads() through day_rows: SC1 on/off, B1 only on NR4 days, S1 tag by LOC20, and FIN1/S2 fields unchanged
k = A.day(21); sp0, q0 = A.tape(k); day = A.DAYS[21]  # a flat day, spot 24000 all day
h_on, h_off = bars([fl()] * 20 + [fl(**y)]), bars([fl()] * 19 + [fl(hc=104, lc=96), fl()])   # rr1 0.6 (SC1, NR4, HIGH) / 1.01 (day -2 narrower: no NR4, MID)
base = F.day_rows(day, sp0, q0)[0]; on = F.day_rows(day, sp0, q0, hist={"NIFTY": h_on})[0]; off = F.day_rows(day, sp0, q0, hist={"NIFTY": h_off})[0]
LEAD = ("lead_hist", "s1_", "b1_", "sc1_", "loc20", "trend", "rr1", "bar")
core = lambda r: {a: b for a, b in r.items() if not a.startswith(LEAD)}
dj = lambda r: __import__("json").dumps(core(r), sort_keys=True)  # NaN-safe compare
assert dj(base) == dj(on) == dj(off), "FIN1/S2 fields must not depend on the leads"
assert base["lead_hist"] == "NO_HIST" and on["lead_hist"] == "OK" and base["status"] == "OK"
assert on["s1_pnl_inr"] == on["s2_short_pnl_inr"] and on["sc1_signal"] and on["sc1_pnl_inr"] == on["s1_pnl_inr"] and on["s1_loc20_high_pnl_inr"] == on["s1_pnl_inr"]
assert on["loc20"] == "HIGH" and on["b1_nr4"] and on["b1_status"] == "NO_CROSS" and on["b1_pnl_inr"] == 0.0   # flat day: no breakout
assert not off["sc1_signal"] and off["sc1_pnl_inr"] == 0.0 and off["s1_pnl_inr"] == on["s1_pnl_inr"] and not off["b1_nr4"] and off["b1_status"] == "NR4_NO"
mid = F.day_rows(day, sp0, q0, hist={"NIFTY": bars([fl()] * 20 + [fl(**dict(y, c=100))])})[0]; assert mid["loc20"] == "MID" and mid["s1_loc20_high_pnl_inr"] == 0.0
cut = lambda hc, lc: F.day_rows(day, sp0, q0, hist={"NIFTY": bars([fl()] * 20 + [fl(hc=hc, lc=lc)])})[0]["sc1_signal"]
assert cut(103.45, 96.55) and not cut(103.55, 96.45)   # SC1 flag itself flips at rr1 0.7 (6.9 vs 7.1 on a mean of 10)
assert not cut(103.5, 96.5)   # rr1 exactly 0.7 is NOT a contracting day (strict <)
for bad in (object(), ValueError("x")):   # a failing history/leads must not lose the FIN1/S2 row
    er = F.day_rows(day, sp0, q0, hist={"NIFTY": bad})[0]; assert er["lead_hist"].startswith("ERROR:") and dj(er) == dj(base), er["lead_hist"]
rep = F.leads_report([on, off, mid, base]); assert "B1 NR4 stretch: n=0" in rep and "SC1 S1 after contracting day: n=2" in rep and "S1 in 20d-range HIGH: n=1" in rep and "(no inputs 1/4)" in rep, rep

# ---- 3b. prior_days / _bar on a tiny synthetic data dir (ohlc json for NIFTY, 25 weekdays ending Thu 2026-10-01; 10-02 is an NSE holiday)
import json, pathlib, datetime as dtm
T1 = pathlib.Path(tempfile.mkdtemp()); (T1 / "recon/ohlc").mkdir(parents=True); bd = list(pd.bdate_range(end="2026-10-01", periods=25).strftime("%Y-%m-%d"))
ts, hi, lo, cl = [], [], [], []
for n, d in enumerate(bd):
    for i in range(375):
        ts.append(int(dtm.datetime.fromisoformat(d + "T09:15:00").replace(tzinfo=F.IST).timestamp()) + 60 * i); c = 20000 + 5 * n + 0.01 * i; cl.append(c); hi.append(c + 2); lo.append(c - 2)
json.dump(dict(timestamp=ts, high=hi, low=lo, close=cl), open(T1 / "recon/ohlc/INDEX_IDX_I_13_1_x.json", "w"))
F.DATA, F._HB = T1, {}
base = F._hist_base("NIFTY"); assert sorted(base) == bd and base[bd[0]][:4] == (20000.0, 20000 + 3.74, 20000.0, 20000 + 3.74), base[bd[0]]
sp5 = {A.F._hm(i): 100 + 0.01 * i for i in range(375)}; b5 = F._bar(sp5); assert b5 == [100.0, 103.74, 100.0, 103.74, 103.74, 100.0]
assert F._bar({k: v for k, v in sp5.items() if k >= "09:30"}) is None and F._bar({k: v for k, v in sp5.items() if k < "14:00"}) is None   # late open / < 300 min
lg = lambda *x: [dict(sym="NIFTY", day=d, bar=b) for d, b in x]
r = F.prior_days("NIFTY", "2026-10-06", lg(("2026-10-05", b5)))   # 10-02 holiday (config/v2/calendar), 10-05 on tape: no NaN row between
assert len(r) == 26 and r[-1] == tuple(b5) and r[-2] == base["2026-10-01"] and F.lead_feats(r) is not None
r = F.prior_days("NIFTY", "2026-10-07", lg(("2026-10-05", b5)))   # 10-06 is a weekday with no row: NaN, no silent span
assert r[-1][0] != r[-1][0] and r[-2] == tuple(b5) and F.lead_feats(r) is None
assert F.lead_feats(F.prior_days("NIFTY", "2026-10-06", lg(("2026-10-05", None)))) is None   # logged but no bar: NaN row
r = F.prior_days("NIFTY", "2026-10-06", lg(("2026-10-05", b5), ("2026-10-06", b5))); assert len(r) == 26 and r[-1] == tuple(b5)   # same day is not history
r = F.prior_days("NIFTY", bd[20], []); assert r[-1] == base[bd[19]] and len(r) == 20   # backfill: base days >= before are dropped, `before` itself too
assert F.prior_days("NIFTY", "2026-10-02", []) == [base[d] for d in bd]   # nothing between the base and a holiday

# ---- 4. lead_feats == book_lab.daily (nr4, stretch, rr1) and scen_lab.dfeat (LOC20, TREND) on 60 random-walk days x 2 syms
D = B.daily(); n = 0; seen = set()
for sym in ("NIFTY", "SENSEX"):
    X = pd.read_pickle(IDXP); X = X[X.sym == sym]; g = X.groupby("day"); d = pd.DataFrame(dict(O=g.open.first(), H=g.high.max(), L=g.low.min(), C=g.close.last(), orr=0.0))
    f2 = SC.dfeat(d); h = [(x.close.iloc[0], x.close.max(), x.close.min(), x.close.iloc[-1], x.high.max(), x.low.min()) for _, x in g]
    for t, day in enumerate(d.index):
        if t < 21: continue
        m = F.lead_feats(h[:t]); b = D.loc[(sym, day)]; n += 1; seen |= {m["loc20"], m["trend"]}
        assert m["nr4"] == bool(b.nr4) and abs(m["stretch"] - b.stretch) < 1e-9 and abs(m["rr1"] - b.rr1) < 1e-9, (sym, day, m, b[["nr4", "stretch", "rr1"]].to_dict())
        assert m["loc20"] == f2.LOC20[day] and m["trend"] == f2.TREND[day], (sym, day, m, f2.loc[day, ["LOC20", "TREND"]].to_dict())
assert {"LOW", "MID", "HIGH", "UP", "DN"} <= seen, seen
print(f"shadow leads known-answer OK (hand cases, B1 trade x13, day_rows leads, {n} sym-days == book_lab.daily / scen_lab.dfeat)")
