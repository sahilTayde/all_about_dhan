"""2026-10-22 shadow-only CHASE8 (premium > +8% on the signal candle) and BE10 (break-even once +10%). Synthetic, no network.
Run: python3 test_shadow_chase8_be10.py. Checks: pure rules + boundaries; be_at=None identical to runner.price_exit_path;
runner overlay_rows adds chase8 / paths.be10 without changing any booked field or runner state; overlay_log writes would-have legs."""
import json, os, sys, tempfile, importlib, pathlib, copy, random
from datetime import datetime, timedelta, timezone
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import shadow_overlays as SO
IST = timezone(timedelta(hours=5, minutes=30)); fails = []
def ok(c, m):
    if not c: fails.append(m)
# 1 CHASE8
ok(SO.chase8({600: (100.0, 119.0)}, 600)["would_skip"] is True, "1a +19% signal candle (IB_5 SENSEX CE case) -> skip")
ok(SO.chase8({600: (100.0, 108.0)}, 600)["would_skip"] is False, "1b exactly +8% -> keep (> 8% only)")
ok(SO.chase8({600: (100.0, 108.01)}, 600)["would_skip"] is True, "1c just over 8%")
ok(SO.chase8({600: (100.0, 90.0)}, 600)["would_skip"] is False, "1d falling candle")
ok(SO.chase8({}, 600)["would_skip"] is None and SO.chase8({600: (0.0, 5.0)}, 600)["would_skip"] is None, "1e no bar / bad open -> unknown")
# 2 BE10
ob = {600: (100.0, 104.0), 601: (104.0, 111.0), 602: (111.0, 105.0), 603: (105.0, 99.5), 604: (99.0, 95.0), 605: (95.0, 60.0), 606: (60.0, 60.0)}
b = SO.path_1m(ob, 600, 100.0, 700, 0.60, be_at=0.10)
ok(b["status"] == "CLOSED" and b["why"] == "BE" and b["exit_m"] == 604 and b["exit_px"] == 99.0, f"2a BE exit {b}")
base = SO.path_1m(ob, 600, 100.0, 700, 0.60)
ok(base["status"] == "CLOSED" and base["why"] == "STOP" and base["exit_px"] == 60.0, f"2b base keeps the 30% stop {base}")
ob2 = {600: (100.0, 109.9), 601: (109.9, 99.0), 602: (99.0, 98.0)}
ok(SO.path_1m(ob2, 600, 100.0, 700, 0.60, be_at=0.10)["status"] == "OPEN", "2c peak +9.9% never arms BE")
ob3 = {600: (100.0, 135.0), 601: (135.0, 90.0), 602: (90.0, 90.0)}
ok(SO.path_1m(ob3, 600, 100.0, 700, 0.60, be_at=0.10)["why"] == "TRAIL", "2d above +30% the normal trail still wins")
# 3 be_at=None == runner
tmp = pathlib.Path(tempfile.mkdtemp()); __import__("atexit").register(__import__("shutil").rmtree, tmp, True); os.environ["PX_DAY"] = "2026-10-01"
for m in ("runner", "live_pricer", "regime_tags"): sys.modules.pop(m, None)
R = importlib.import_module("runner")
rng = random.Random(11); diff = 0
for n in range(200):
    p = 100.0; o2 = {}
    for m in range(600, 931):
        o = p; p = max(1.0, p * (1 + rng.gauss(0, 0.03))); o2[m] = (round(o, 2), round(p, 2))
    now = rng.choice([700, 916, 931]); a = R.price_exit_path(o2, 601, o2[601][0], now); c = SO.path_1m(o2, 601, o2[601][0], now, 0.60)
    if a["status"] != c["status"] or (a["status"] == "CLOSED" and (a["exit_m"], a["exit_px"], a["why"]) != (c["exit_m"], c["exit_px"], c["why"])): diff += 1
ok(diff == 0, f"3 default path differs from runner on {diff}/200")
# 4 runner integration: shadow only
day = "2026-10-01"; R.DAY = day
run = tmp / "run"; run.mkdir(); R.LIVE_RUN = run; R.OUT = tmp / "out.json"; R.SO_FILE = tmp / "so.jsonl"; R.SO_STATUS_FILE = tmp / "status.json"
R.EXP = "2026-10-06"; R.EXPS = {"NIFTY": "2026-10-06", "SENSEX": "2026-10-01"}; R.RT = pathlib.Path("/nonexistent")
def ts(m): return int(datetime(2026, 10, 1, m // 60, m % 60, tzinfo=IST).timestamp())
def dj(bars): ks = sorted(bars); return dict(timestamp=[ts(m) for m in ks], open=[bars[m][0] for m in ks], high=[max(bars[m]) for m in ks], low=[min(bars[m]) for m in ks], close=[bars[m][1] for m in ks], volume=[0] * len(ks))
(run / "IDX_NIFTY.json").write_text(json.dumps(dj({m: (25000.0, 25000.0) for m in range(555, 931)})))
bars = {600: (100.0, 119.0)}; p = 119.0
for m in range(601, 931): o = p; p = p * 1.025 if m < 606 else p * 0.98; bars[m] = (round(o, 2), round(p, 2))
(run / "NIFTY_2026-10-06_24950_CE.json").write_text(json.dumps(dj(bars)))
rows = [dict(rule_id="PX_IB_5", strategy="IB_5", underlying="NIFTY", qty=650, side="CE", strike=24950.0, signal_time="10:00", entry_time="10:01",
             entry_px=bars[601][0], status="CLOSED", exit_time="10:40", exit_px=bars[601][0] * 0.7, exit_reason="STOP", mark_px=None, mark_time=None,
             stop_px=1.0, target_px=2.0)]
before = copy.deepcopy(rows); stb = json.dumps([R.CAP, R.PREM, R.START, sorted(map(str, R.LIVE))], default=str)
print(R.overlay_rows(rows, 931))
ok([{k: v for k, v in r.items() if k not in ("exit_status", "shadow_overlays")} for r in rows] == before, "4a booked fields changed")
ok(json.dumps([R.CAP, R.PREM, R.START, sorted(map(str, R.LIVE))], default=str) == stb, "4b runner state changed")
so = rows[0]["shadow_overlays"]
ok(so["chase8"]["would_skip"] is True and so["chase8"]["signal_candle_pct"] == 19.0, f"4c chase8 {so.get('chase8')}")
ok(so["paths"]["be10"]["status"] == "CLOSED" and so["paths"]["be10"]["why"] == "BE", f"4d be10 {so['paths'].get('be10')}")
ok(so["shadow_only"] is True and rows[0]["status"] == "CLOSED", "4e shadow only")
print(R.overlay_log(rows, 931))
rec = json.loads(R.SO_FILE.read_text().splitlines()[0])
ok(rec["be10"] and rec["be10"]["why"] == "BE" and rec["chase8"]["would_skip"] is True, f"4f log {rec.get('be10')} {rec.get('chase8')}")
ok(rec["if_chase8_applied"]["gross_inr"] == 0.0 and rec["actual"]["gross_inr"] < 0, f"4g would-have: skip saves the loss {rec['if_chase8_applied']} {rec['actual']}")
print("test_shadow_chase8_be10:", "ALL PASS" if not fails else f"FAIL {fails}"); sys.exit(1 if fails else 0)
