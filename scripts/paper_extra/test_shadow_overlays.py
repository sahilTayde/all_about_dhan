"""Exit-status labels + shadow overlays (display / logging only). Box/Mac, no network, synthetic data. Run: python3 test_shadow_overlays.py
1 labels: HEALTHY / FADING (giveback, slope+premium) / REVERSING (giveback, VWAP cross) incl. boundaries; 2 path_1m == runner.price_exit_path
at 60% on 300 random paths; 3 TS target reasons; 4 DR order rule; 5 runner overlay_rows/overlay_status/overlay_log never change any other
field or runner state; one log line per closed trade, idempotent across restart; 6 broken/missing index json -> no crash; 7 runner survives
a shadow_overlays import failure; 8 guard-style refresh drops exit_status when a row closes."""
import json, os, sys, tempfile, importlib, pathlib, copy, random
from datetime import datetime, timedelta, timezone
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import shadow_overlays as SO
IST = timezone(timedelta(hours=5, minutes=30)); fails = []
def ok(c, m):
    if not c: fails.append(m)
# ---- 1 labels. index: flat 25000 except where set; idx minute k -> (o,h,l,c)
def flat(n=200, v=25000.0): return {k: (v, v + 1, v - 1, v) for k in range(n)}
idx = flat()
L = lambda **a: SO.status(**dict(dict(p0=100.0, px=100.0, peak=100.0, prem_3ago=None, sg=1, idx=idx, k_now=100, k_sig=50), **a))["label"]
ok(L() == "HEALTHY", "1a flat")
ok(L(px=112, peak=120) == "REVERSING", "1b gave back exactly 40% of a +20% peak -> REVERSING (<=)")
ok(L(px=112.1, peak=120) == "FADING", "1c gave back 39.5% -> FADING (>=20%)")
ok(L(px=116, peak=120) == "FADING", "1d gave back 20% -> FADING")
ok(L(px=116.1, peak=120) == "HEALTHY", "1e gave back <20%")
ok(L(px=106, peak=110) == "FADING", "1f +10% peak, 40% giveback but peak <15% -> FADING only")
ok(L(px=108.1, peak=110) == "HEALTHY", "1g +10% peak, <20% giveback")
ok(L(px=104, peak=109.9) == "HEALTHY", "1h peak below +10%: no giveback rule")
i2 = {k: (25000.0 + k, 25001.0 + k, 24999.0 + k, 25000.0 + k) for k in range(98)}; [i2.__setitem__(k, (25090.0, 25091.0, 25089.0, 25090.0)) for k in range(98, 101)]   # rising, then 3-min dip; still far above VWAP
ok(L(idx=i2, px=99, prem_3ago=100) == "FADING", "1i index 3-min against + premium falling")
ok(L(idx=i2, px=101, prem_3ago=100) == "HEALTHY", "1j index against but premium up")
ok(L(idx=i2, px=99, prem_3ago=None) == "HEALTHY", "1k no premium 3 min ago")
i3 = {k: (25000.0, 25010.0, 24990.0, 25000.0 + (k if k <= 60 else 60 - 3 * (k - 60))) for k in range(150)}   # up to k=60 then down hard: below VWAP by k=100
ok(L(idx=i3, sg=1, k_sig=50) == "REVERSING", "1l CE: index crossed below VWAP since entry")
ok(L(idx=i3, sg=-1, k_sig=50) == "HEALTHY" or L(idx=i3, sg=-1, k_sig=50) == "FADING", "1m PE same path: no cross against")
st = SO.status(100, 112, 120, 110, 1, idx, 100, 50, held_min=40)
ok(st["gain_now_pct"] == 12.0 and st["peak_gain_pct"] == 20.0 and st["minutes_held"] == 40 and st["vwap_side"] == "WITH" and st["display_only"] is True, f"1n fields {st}")
ok(SO.status(100, 90, 95, None, 1, {}, 100, 50)["label"] == "HEALTHY", "1o empty index -> no crash")
# ---- 2 path_1m == runner.price_exit_path at 60%
tmp = pathlib.Path(tempfile.mkdtemp()); os.environ["PX_DAY"] = "2026-10-01"
for m in ("runner", "live_pricer", "regime_tags"): sys.modules.pop(m, None)
R = importlib.import_module("runner")
rng = random.Random(7); diff = 0
for n in range(300):
    p = 100.0; ob = {}
    for m in range(600, 931):
        if rng.random() < 0.05: continue
        o = p; p = max(1.0, p * (1 + rng.gauss(0, 0.03))); ob[m] = (round(o, 2), round(p, 2))
    em = 601 if 601 in ob else min(m for m in ob if m > 600); now = rng.choice([700, 800, 915, 916, 931])
    a = R.price_exit_path(ob, em, ob[em][0], now); b = SO.path_1m(ob, em, ob[em][0], now, 0.60)
    if a["status"] != b["status"] or (a["status"] == "CLOSED" and (a["exit_m"], a["exit_px"], a["why"]) != (b["exit_m"], b["exit_px"], b["why"])): diff += 1
ok(diff == 0, f"2 path_1m differs from runner on {diff}/300")
# ---- 3 TS
mor = {k: (25000.0 + 2 * k, 25000.0 + 2 * k + 1, 25000.0 + 2 * k - 1, 25000.0 + 2 * k + 2) for k in range(376)}   # strong trend morning
ok(SO.ts_target(mor, 650, 651, False)[0] == 0.5 and "trend morning" in SO.ts_target(mor, 650, 651, False)[1], "3a trend morning -> 50%")
ok(SO.ts_target(mor, 570, 571, False)[1] == ["entry before 10:00"], f"3b signal before 09:45: trend not known {SO.ts_target(mor, 570, 571, False)}")
chop = {k: (25000.0, 25005.0, 24995.0, 25000.0 + (3 if k % 2 else -3)) for k in range(376)}
ok(SO.ts_target(chop, 700, 701, False)[0] == 0.6, "3c chop midday -> 60%")
ok(SO.ts_target(chop, 700, 701, True)[1] == ["expiry day"], "3d expiry")
ok(SO.ts_target(chop, 810, 811, False)[1] == ["entry at/after 13:30"] and SO.ts_target(chop, 808, 809, False)[0] == 0.6, "3e 13:30 boundary")
ok(SO.ts_target({}, 700, 701, False)[0] == 0.6, "3f no index -> 60%")
# ---- 4 DR
T = [dict(key="a", entry_m=600, sig_m=599, exit_m=620, giveback=True, ok=False), dict(key="b", entry_m=615, sig_m=614, exit_m=640, giveback=False, ok=False),
     dict(key="c", entry_m=625, sig_m=624, exit_m=650, giveback=True, ok=False), dict(key="d", entry_m=630, sig_m=629, exit_m=None, giveback=False, ok=True),
     dict(key="e", entry_m=660, sig_m=659, exit_m=None, giveback=False, ok=False)]
F = SO.dr_flags(T)
ok([F[k]["would_skip"] for k in "abcde"] == [False, False, True, False, True], f"4 DR {[(k, F[k]['would_skip']) for k in 'abcde']}")
# ---- 5 runner integration (synthetic Dhan json in a temp repo)
day = "2026-10-01"; os.environ["PX_DAY"] = day
for m in ("runner", "live_pricer", "regime_tags", "shadow_overlays"): sys.modules.pop(m, None)
R = importlib.import_module("runner"); R.DAY = day
run = tmp / "run"; run.mkdir(); R.LIVE_RUN = run; R.OUT = tmp / "out.json"; R.SO_FILE = tmp / "so.jsonl"; R.SO_STATUS_FILE = tmp / "status.json"
R.EXP = "2026-10-06"; R.EXPS = {"NIFTY": "2026-10-06", "SENSEX": "2026-10-01"}; R.RT = pathlib.Path("/nonexistent")
def ts(m): return int(datetime(2026, 10, 1, m // 60, m % 60, tzinfo=IST).timestamp())
def dj(bars): ks = sorted(bars); return dict(timestamp=[ts(m) for m in ks], open=[bars[m][0] for m in ks], high=[max(bars[m]) for m in ks], low=[min(bars[m]) for m in ks], close=[bars[m][1] for m in ks], volume=[0] * len(ks))
ix = {m: (25000.0 + (m - 555), 25000.0 + (m - 554)) for m in range(555, 931)}
(run / "IDX_NIFTY.json").write_text(json.dumps(dj(ix)))
up = {}; p = 100.0
for m in range(600, 931): o = p; p = p * 1.012 if m < 625 else p * 0.985; up[m] = (round(o, 2), round(p, 2))
(run / "NIFTY_2026-10-06_24950_CE.json").write_text(json.dumps(dj(up)))
(run / "NIFTY_2026-10-06_25100_PE.json").write_text(json.dumps(dj({m: (100.0, 100.0 + (m % 3)) for m in range(600, 931)})))
rows = [dict(rule_id="PX_ORB_A", strategy="I1_ORB:ORB_A:T2", underlying="NIFTY", qty=650, side="CE", strike=24950.0, signal_time="10:00", entry_time="10:01",
             entry_px=up[601][0], status="CLOSED", exit_time="10:40", exit_px=95.0, exit_reason="STOP", mark_px=None, mark_time=None, stop_px=1.0, target_px=2.0),
        dict(rule_id="PX_R07", strategy="R07", underlying="NIFTY", qty=650, side="PE", strike=25100.0, signal_time="10:50", entry_time="10:51",
             entry_px=100.0, status="OPEN", exit_time=None, exit_px=None, exit_reason=None, mark_px=101.0, mark_time="11:00", stop_px=70.0, target_px=160.0),
        dict(rule_id="Q01_ITM100", strategy="Q01", underlying="NIFTY", status="OPEN", side="CE", strike=1.0, signal_time="10:00", entry_time="10:01", entry_px=1.0)]
before = copy.deepcopy(rows); stb = json.dumps([R.CAP, R.PREM, R.START, sorted(map(str, R.LIVE))], default=str)
txt = R.overlay_rows(rows, 931); print(txt)
NEW = ("exit_status", "shadow_overlays")
ok([{k: v for k, v in r.items() if k not in NEW} for r in rows] == before, "5a other fields changed")
ok(json.dumps([R.CAP, R.PREM, R.START, sorted(map(str, R.LIVE))], default=str) == stb, "5b runner state changed")
ok("exit_status" in rows[1] and "exit_status" not in rows[0] and "exit_status" not in rows[2] and "shadow_overlays" not in rows[2], "5c keys only on PX rows / OPEN for status")
ok(rows[1]["exit_status"]["label"] in ("HEALTHY", "FADING", "REVERSING") and rows[1]["exit_status"]["stop_px"] == 70.0, f"5d status {rows[1].get('exit_status')}")
so = rows[0]["shadow_overlays"]; ok(so["giveback"] is True and so["paths"]["base60_1m"]["status"] == "CLOSED" and "error" not in so, f"5e giveback/paths {so}")
ok(so["dr"]["would_skip"] is False and rows[1]["shadow_overlays"]["dr"]["after_giveback_exit"] is True and rows[1]["shadow_overlays"]["dr"]["would_skip"] is True, f"5f DR flags {rows[1]['shadow_overlays']['dr']}")
ok(json.loads(R.SO_STATUS_FILE.read_text())[0]["key"] == ["PX_R07", "NIFTY", "10:50"], "5g sidecar status file")
print(R.overlay_log(rows, 931)); print(R.overlay_log(rows, 931))
L1 = R.SO_FILE.read_text().splitlines(); ok(len(L1) == 1, f"5h log lines {len(L1)} (1 closed PX trade, idempotent)")
rec = json.loads(L1[0]); ok(rec["actual"]["net_inr_1_5x"] is None and rec["actual"]["gross_inr"] == round((95.0 - up[601][0]) * 650, 2) and rec["t50"] and rec["ts"], f"5i rec {rec}")
R.SO_DONE.clear(); print(R.overlay_log(rows, 931)); ok(len(R.SO_FILE.read_text().splitlines()) == 1, "5j idempotent after restart (reload from file)")
r2 = copy.deepcopy(rows); r2[1]["status"] = "CLOSED"; r2[1]["exit_time"] = "11:05"; r2[1]["exit_px"] = 99.0; R.overlay_status(r2, 931)
ok("exit_status" not in r2[1], "8 status removed once closed")
# ---- 6 broken index json
(run / "IDX_NIFTY.json").write_text("{not json"); R.SO_IDX.clear(); rows3 = copy.deepcopy(before)
t3 = R.overlay_rows(rows3, 931); ok("ERROR" not in t3 and rows3[1]["exit_status"]["label"] is not None, f"6 broken index {t3} {rows3[1].get('exit_status')}")
(run / "IDX_NIFTY.json").unlink(); R.SO_IDX.clear(); rows4 = copy.deepcopy(before); t4 = R.overlay_rows(rows4, 931); ok(rows4[1]["exit_status"]["label"] is not None, f"6b missing index {t4}")
# ---- 7 import failure
for m in ("runner", "live_pricer", "regime_tags"): sys.modules.pop(m, None)
sys.modules["shadow_overlays"] = None   # makes "import shadow_overlays" raise ImportError
R2 = importlib.import_module("runner"); ok(R2.SO is None and R2.overlay_rows([], 931).startswith("overlays OFF"), "7 import failure")
r7 = copy.deepcopy(before); R2.overlay_status
sys.modules.pop("shadow_overlays", None)
print("test_shadow_overlays:", "ALL PASS" if not fails else f"FAIL {fails}"); sys.exit(1 if fails else 0)
