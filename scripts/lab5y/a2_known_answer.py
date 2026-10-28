"""Audit A2 (2026-10-28): known-answer tests for every backtest engine path, on synthetic days whose P&L is computed
by hand here (costs re-derived from config/charges.yaml, not from the engine's cost()).
Paths: opt1y_lab.trade (long win, stop, gapped stop, target, stop+target bar, strike leaves window, expiry-day spread,
time hold, index stop, straddle legs = FIN1 path), sell_lab.struct cons/opt (short straddle win, credit stop, credit
target, short strike leaves the window -> bound, long directional spot target/stop, long straddle), fin1_shadow S2 and
FIN1 on a tape built from the same synthetic day (must equal the bar engine).
Run (from scripts/lab5y):  ~/paper_extra_venv/bin/python a2_known_answer.py"""
import os, pickle, re, sys, tempfile, numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
TMP = tempfile.mkdtemp(); NB, M0 = 375, 555
HS0, HS1 = 1.0, 2.0  # synthetic half-spread: 1.0 on non-expiry days, 2.0 on expiry days (checks the dte0 bucket)
pd.DataFrame([dict(sym=s, pb=pb, tb=tb, dte0=d, count=1, median=h, p75=h) for s in ("NIFTY", "SENSEX") for pb in range(6)
              for tb in range(5) for d, h in ((0, HS0), (1, HS1))]).to_csv(f"{TMP}/spreads.csv", index=False)
STRK = 24000.0; STEP = 50


def flat_day(d0=0, px=100.0, spot=STRK):
    """NIFTY day: spot flat, ATM 24000, strikes ATM+-3 both sides, every bar o=h=l=c=px."""
    C = {}
    for sd in ("CE", "PE"):
        for off in range(-3, 4):
            a = np.full((NB, 7), np.nan); a[:, :4] = px; a[:, 5] = 15.0; C[(sd, STRK + off * STEP)] = a
    return dict(spot=np.full(NB, spot), atm=np.full(NB, STRK), C=C, exp="2026-01-06", dte=0 if d0 else 1, d0=d0)


DAYS = [f"2026-01-{d:02d}" for d in range(5, 29)]
pickle.dump({("NIFTY", d): flat_day() for d in DAYS}, open(f"{TMP}/panel.pkl", "wb"))
sys.argv = [sys.argv[0], TMP]
import opt1y_lab as L  # noqa: E402
import sell_lab as S  # noqa: E402
import fin1_shadow as F  # noqa: E402

# ---------------------------------------------------------------- hand costs from config/charges.yaml
Y = {m[0]: float(m[1]) for m in re.findall(r"^(\w+):\s*([0-9.]+)", open(f"{ROOT}/config/charges.yaml").read(), re.M)}
BSE = float(re.search(r"BSE:\s*([0-9.]+)", open(f"{ROOT}/config/charges.yaml").read()).group(1))


def hand_cost(buy, sell, sym="NIFTY", lots=10, cm=1.5):
    q = {"NIFTY": 65, "SENSEX": 20}[sym] * lots; bt, st = buy * q, sell * q
    txn = (Y["exchange_txn_frac"] if sym == "NIFTY" else BSE) * (bt + st); sebi = Y["sebi_fee_frac"] * (bt + st)
    brk = 2 * Y["brokerage_per_order_inr"]  # one entry order + one exit order per leg
    return cm * (brk + txn + sebi + Y["gst_frac"] * (brk + txn + sebi) + Y["stamp_duty_buy_frac"] * bt + Y["stt_sell_premium_frac"] * st)


def eq(a, b, what, tol=0.5):  # 50 paise: the engine omits IPFT (Rs 0.01/crore)
    assert a is not None and abs(a - b) < tol, f"{what}: engine {a} != hand {b}"


Q = 650
for b_, s_ in ((101, 129), (55.5, 3.2), (480, 610)):
    eq(L.cost(b_, s_, "NIFTY"), hand_cost(b_, s_), f"cost {b_}/{s_}", 0.05)
    eq(L.cost(b_, s_, "SENSEX"), hand_cost(b_, s_, "SENSEX"), f"SENSEX cost {b_}/{s_}", 0.05)
    eq(F.cost(b_, s_, "NIFTY"), L.cost(b_, s_, "NIFTY"), "fin1_shadow cost == opt1y_lab cost", 1e-9)
assert L.LOT == F.LOT == {"NIFTY": 65, "SENSEX": 20} and L.LOTS == F.LOTS == 10  # see registry A2 on the pre-2026 NIFTY lot


def day(n, **kw):
    k = ("NIFTY", DAYS[n]); L.P[k] = flat_day(**kw); return k


def set_bar(k, side, K, j, o, h, l, c):
    L.P[k]["C"][(side, K)][j, :4] = (o, h, l, c)


# ---------------------------------------------------------------- opt1y_lab.trade
k = day(0); L.P[k]["C"][("CE", STRK)][100:, :4] = 130.0
r = L.trade(k, 30, "CE", hold=None)  # decide 09:45 close, buy 09:46 open + hs, sell 15:15 open - hs
eq(r[0], (129 - 101) * Q - hand_cost(101, 129), "T1 winning long"); assert r[1] == L.FLAT - M0 - 31 and not r[2] and L.FLAT == 915  # 15:15
k = day(1); set_bar(k, "CE", STRK, 60, 95, 95, 78, 80)
eq(L.trade(k, 30, "CE", hold=None, stop=0.2)[0], (80.8 - 1 - 101) * Q - hand_cost(101, 79.8), "T2 stop at the stop price")
k = day(2); set_bar(k, "CE", STRK, 60, 70, 72, 65, 66)
eq(L.trade(k, 30, "CE", hold=None, stop=0.2)[0], (70 - 1 - 101) * Q - hand_cost(101, 69), "T2b gapped stop at the open")
k = day(3); set_bar(k, "CE", STRK, 60, 110, 135, 108, 120)
eq(L.trade(k, 30, "CE", hold=None, tgt=0.3)[0], (131.3 - 1 - 101) * Q - hand_cost(101, 130.3), "T3 target")
k = day(4); set_bar(k, "CE", STRK, 60, 100, 140, 70, 100)
eq(L.trade(k, 30, "CE", hold=None, stop=0.2, tgt=0.3)[0], (80.8 - 1 - 101) * Q - hand_cost(101, 79.8), "T3b stop+target bar = stop")
k = day(5); L.P[k]["C"][("CE", STRK)][200:] = np.nan  # strike leaves the ATM+-3 window at bar 200
r = L.trade(k, 30, "CE", hold=None)
eq(r[0], (100 - 1 - 101) * Q - hand_cost(101, 99), "T4 strike leaves window: last close"); assert r[2] and r[1] == 200 - 31
k = day(6, d0=1); L.P[k]["C"][("CE", STRK)][100:, :4] = 130.0
eq(L.trade(k, 30, "CE", hold=None)[0], (128 - 102) * Q - hand_cost(102, 128), "T5 expiry day uses the expiry half-spread")
k = day(7); L.P[k]["C"][("PE", STRK)][46:, :4] = 90.0
r = L.trade(k, 30, "PE", hold=15); eq(r[0], (89 - 101) * Q - hand_cost(101, 89), "T6 15-min hold exits at bar 46 open")
assert r[1] == 15
k = day(8); L.P[k]["spot"][70:] = STRK - 30; L.P[k]["C"][("CE", STRK)][71:, :4] = 85.0
r = L.trade(k, 30, "CE", hold=None, idx_stop=25)
eq(r[0], (84 - 101) * Q - hand_cost(101, 84), "T7 index stop -> next open"); assert r[1] == 71 - 31
k = day(9); L.P[k]["C"][("CE", STRK)][100:, :4] = 160.0; L.P[k]["C"][("PE", STRK)][100:, :4] = 60.0
r = L.trade(k, 30, "CE", hold=None, legs=(("CE", 0), ("PE", 0)))  # FIN1 path
eq(r[0], (159 - 101) * Q - hand_cost(101, 159) + (59 - 101) * Q - hand_cost(101, 59), "T8 FIN1 straddle legs")

# ---------------------------------------------------------------- sell_lab.struct
SS = S.SSTRAD
k = day(10); [L.P[k]["C"][(sd, STRK)].__setitem__((slice(100, None), slice(0, 4)), 60.0) for sd in ("CE", "PE")]
for mode in ("cons", "opt"):  # entry: decide 09:46 close (31), sell 09:47 open - hs; exit 15:15 open + hs
    r = S.struct(k, 31, SS, mode=mode)
    eq(r["pnl"], 2 * ((99 - 61) * Q - hand_cost(61, 99)), f"S1 short straddle decays, {mode}"); assert r["why"] == "time"
k = day(11); L.P[k]["C"][("CE", STRK)][80:, :4] = 200.0  # value 300 >= credit 198 * 1.5 at the bar-80 close -> exit 81 open
r = S.struct(k, 31, SS, stop=0.5)
eq(r["pnl"], (99 - 201) * Q - hand_cost(201, 99) + (99 - 101) * Q - hand_cost(101, 99), "S2 credit stop next open")
assert r["why"] == "stop" and r["held"] == 81 - 32
k = day(12); [L.P[k]["C"][(sd, STRK)].__setitem__((slice(90, None), slice(0, 4)), 65.0) for sd in ("CE", "PE")]
r = S.struct(k, 31, SS, tgt=0.3)  # 130 <= 0.7 * 198 at bar 90 -> exit 91
eq(r["pnl"], 2 * ((99 - 66) * Q - hand_cost(66, 99)), "S3 credit target"); assert r["why"] == "tgt" and r["held"] == 91 - 32
# S4: spot rallies 5 steps; the short 24000 CE leaves the tape; taped CE strikes become 24100..24400 (24100 CE = 160)
k = day(13); p = L.P[k]; p["spot"][150:] = STRK + 250; p["atm"][150:] = STRK + 250
for sd in ("CE", "PE"):
    for off in range(-3, 4):
        p["C"].setdefault((sd, STRK + 250 + off * STEP), np.full((NB, 7), np.nan))
for (sd, K), a in p["C"].items():
    if abs(K - (STRK + 250)) > 3 * STEP: a[150:] = np.nan  # off the new window
    else: a[150:, :4] = max(0.0, (STRK + 250 - K) if sd == "CE" else (K - STRK - 250)) + 10.0  # intrinsic + 10 extrinsic
ce_c, ce_o = S.struct(k, 31, [("CE", 0, -1)], mode="cons"), S.struct(k, 31, [("CE", 0, -1)], mode="opt")
eq(ce_c["pnl"], (99 - (250 + 10 + 1)) * Q - hand_cost(261, 99), "S4 cons: off-tape short = intrinsic + nearest extrinsic")
eq(ce_o["pnl"], (99 - (250 + 1)) * Q - hand_cost(251, 99), "S4 opt: off-tape short = intrinsic"); assert ce_c["forced"]
# S4b: a data hole at the short strike with taped neighbours both 1 step away: cons takes the LARGER extrinsic (A2 fix)
k = day(19); L.P[k]["C"][("CE", STRK)][100:] = np.nan
L.P[k]["C"][("CE", STRK - STEP)][:, :4] = 50 + 5.0; L.P[k]["C"][("CE", STRK + STEP)][:, :4] = 12.0  # extrinsic 5 vs 12
r = S.struct(k, 31, [("CE", 0, -1)], mode="cons")
eq(r["pnl"], (99 - 13) * Q - hand_cost(13, 99), "S4b tie -> larger extrinsic"); assert r["forced"]
# S5: long ATM CE, directional spot exits (E5): +1 step at bar 80 -> target, exit 81 open
k = day(14); L.P[k]["spot"][80:] = STRK + 50; L.P[k]["C"][("CE", STRK)][81:, :4] = 125.0
r = S.struct(k, 31, [("CE", 0, 1)], dirn=1, s_tgt=1, s_stp=0.5)
eq(r["pnl"], (124 - 101) * Q - hand_cost(101, 124), "S5 long spot target"); assert r["why"] == "s_tgt" and r["held"] == 81 - 32
k = day(15); L.P[k]["spot"][80:] = STRK - 25; L.P[k]["C"][("CE", STRK)][81:, :4] = 88.0
r = S.struct(k, 31, [("CE", 0, 1)], dirn=1, s_tgt=1, s_stp=0.5)
eq(r["pnl"], (87 - 101) * Q - hand_cost(101, 87), "S5b long spot stop"); assert r["why"] == "s_stp"
k = day(16); L.P[k]["C"][("CE", STRK)][100:, :4] = 170.0; L.P[k]["C"][("PE", STRK)][100:, :4] = 40.0
r = S.struct(k, 31, S.LSTRAD)
eq(r["pnl"], (169 - 101) * Q - hand_cost(101, 169) + (39 - 101) * Q - hand_cost(101, 39), "S6 long straddle")

# ---------------------------------------------------------------- fin1_shadow on a tape built from a bar day
def tape(k, step_s=0):
    """bid/ask = bar open -+ hs at hh:mm:00 of every minute; spot minute = bar close (as Dhan's option 'spot')."""
    p = L.P[k]; hm = lambda j: f"{(M0 + j) // 60:02d}:{(M0 + j) % 60:02d}"
    sp = {hm(j): float(p["spot"][j]) for j in range(NB)}; q = {}
    for (sd, K), a in p["C"].items():
        q[("NIFTY", K, sd)] = [(hm(j) + ":00", a[j, 0] - HS0, a[j, 0] + HS0, "2026-01-06") for j in range(NB) if np.isfinite(a[j, 0])]
    return {"NIFTY": sp, "SENSEX": {}}, q


k = day(17); L.P[k]["spot"][100:] = STRK + 100
L.P[k]["C"][("CE", STRK)][101:, :4] = 150.0; L.P[k]["C"][("PE", STRK)][101:, :4] = 70.0
sp, q = tape(k); s2 = F.s2_trade("NIFTY", sp["NIFTY"], sorted(q[("NIFTY", STRK, "CE")]), sorted(q[("NIFTY", STRK, "PE")]))
lab = S.struct(k, 31, SS, sstop=2)
eq(s2[0], lab["pnl"], "S2 shadow == sell_lab S1/S2 bar engine", 0.05)
eq(lab["pnl"], (99 - 151) * Q - hand_cost(151, 99) + (99 - 71) * Q - hand_cost(71, 99), "S2 hand")
k = day(18); L.P[k]["C"][("CE", STRK)][100:, :4] = 130.0
sp, q = tape(k); row = F.day_rows(DAYS[18], sp, q)[0]
eq(row["straddle_pnl_inr"], L.trade(k, 30, "CE", hold=None, legs=(("CE", 0), ("PE", 0)))[0], "FIN1 shadow == opt1y_lab FIN1", 0.05)
# 15:15 flatten (critic A2: FLAT was 900 = 15:00): a jump at 15:05 must reach both engines and the shadow
k = day(20); L.P[k]["C"][("CE", STRK)][350:, :4] = 200.0
eq(L.trade(k, 30, "CE", hold=None)[0], (199 - 101) * Q - hand_cost(101, 199), "T9 15:05 jump kept to the 15:15 exit")
sp, q = tape(k); row = F.day_rows(DAYS[20], sp, q)[0]
eq(row["straddle_pnl_inr"], L.trade(k, 30, "CE", hold=None, legs=(("CE", 0), ("PE", 0)))[0], "FIN1 shadow == lab with a 15:05 jump", 0.05)
print("A2 known-answer tests OK (opt1y_lab.trade x10, sell_lab.struct x9, fin1_shadow x2, costs vs charges.yaml)")
# ---------------------------------------------------------------- maxdd counts losses from the start (peak starts at 0)
Dd = pd.DataFrame(dict(day=["2026-01-05", "2026-01-06", "2026-01-07"], pnl=[-1000.0, -500.0, 700.0], sym="NIFTY", forced=False, maxloss=np.nan))
assert S.summ(Dd)["maxdd"] == -1500, S.summ(Dd)
print("A2 maxdd check OK")
