"""2026-10-19 total open premium limit (PREMIUM_CAP_INR = 9L, 10L paper account) + check order PRE_START -> anti-chase -> cap2 -> premium.
Box/Mac, no network. Run: python3 test_premium_cap.py  (DESKML_SRC=<desk-ml src> also checks desk booking)."""
import ast, json, os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.OUT = d / "out.json"
R.CAP_FILE = d / "cap_start.json"; R.PREM_FILE = d / "premium_cap_start.json"; R.START_FILE = d / "runner_start.json"
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, msg):
    if not c: fails.append(msg)
ok(R.PREMIUM_CAP_INR == 900000, "0 limit is 9L")
B = {}
def bars(p0, target_at=None, chase_at=None):
    ob = {m: (p0 * 1.01, p0 * 1.02) for m in range(600, 760)}
    if target_at: ob.update({m: (p0 * 1.7, p0 * 1.7) for m in range(target_at, 760)})
    if chase_at: ob[chase_at - 3] = (p0 * .8, p0 * .8)          # close 2 min before the signal minute 20% lower -> chase
    return ob
def add(u, K, side, p0, **kw): B[(u, K, side)] = bars(p0, **kw)
R._opt_bars = lambda u, K, side: B.get((u, int(K), side), {})
def row(rid, u, K, side, sig, ent, px):
    return dict(rule_id=rid, strategy=rid, underlying=u, qty=R.QTY[u], side=side, strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
def fresh(cap_from=600, prem_from=600):
    R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.CAP.update(from_m=cap_from, admit=set(), skip=set()); R.PREM.update(from_m=prem_from, skip=set())
def run(rows, now=745): return {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in rows], now)}
# 1: open 5.59L (NIFTY 860 x 650) + new 3.60L (SENSEX 1800 x 200) = 9.19L > 9L -> SKIPPED_PREMIUM (scaled 2.8L + 1.8L case)
add("NIFTY", 25000, "PE", 860.0); add("SENSEX", 80000, "CE", 1800.0)
fresh(); o = run([row("PX_A", "NIFTY", 25000, "PE", "12:00", "12:01", 860.0), row("PX_B", "SENSEX", 80000, "CE", "12:09", "12:10", 1800.0)])
ok(o["PX_A"]["status"] == "OPEN" and o["PX_B"]["status"] == "SKIPPED_PREMIUM", f"1 {o['PX_B']['status']}")
ok("559,000" in o["PX_B"]["note"] and "360,000" in o["PX_B"]["note"], f"1b note {o['PX_B'].get('note')}")
ok(all(k[0] != "PX_B" for k in R.LIVE), "1c skipped never live-priced")
# 2: 3.0L + 3.0L admitted (SENSEX 1500 x 200 twice)
add("SENSEX", 80100, "PE", 1500.0); add("SENSEX", 80200, "PE", 1500.0)
fresh(); o = run([row("PX_C", "SENSEX", 80100, "PE", "12:00", "12:01", 1500.0), row("PX_D", "SENSEX", 80200, "PE", "12:04", "12:05", 1500.0)])
ok(o["PX_C"]["status"] == "OPEN" and o["PX_D"]["status"] == "OPEN", f"2 {o['PX_D']['status']}")
# 3: exact boundary 3.9L (NIFTY 600 x 650) + 5.1L (SENSEX 2550 x 200) = 9.00L -> admitted; 1 paisa more -> skipped
add("NIFTY", 25100, "CE", 600.0); add("SENSEX", 80300, "PE", 2550.0); add("SENSEX", 80400, "PE", 2550.01)
fresh(); o = run([row("PX_E", "NIFTY", 25100, "CE", "12:00", "12:01", 600.0), row("PX_F", "SENSEX", 80300, "PE", "12:04", "12:05", 2550.0)])
ok(o["PX_F"]["status"] == "OPEN", f"3 exact 9L admitted {o['PX_F']['status']}")
fresh(); o = run([row("PX_E", "NIFTY", 25100, "CE", "12:00", "12:01", 600.0), row("PX_F2", "SENSEX", 80400, "PE", "12:04", "12:05", 2550.01)])
ok(o["PX_F2"]["status"] == "SKIPPED_PREMIUM", f"3b 9L + 2 INR skipped {o['PX_F2']['status']}")
# 4: closing frees premium (same-minute rule as cap2): A target trigger 12:30, fill 12:31; entry 12:32 admitted, entry 12:31 skipped
add("NIFTY", 25200, "PE", 860.0, target_at=750); add("SENSEX", 80500, "CE", 1800.0); add("SENSEX", 80600, "CE", 1800.0)
fresh(); o = run([row("PX_G", "NIFTY", 25200, "PE", "12:00", "12:01", 860.0), row("PX_H", "SENSEX", 80500, "CE", "12:30", "12:31", 1800.0),
                 row("PX_I", "SENSEX", 80600, "CE", "12:31", "12:32", 1800.0)], 760)
ok(o["PX_G"]["status"] == "CLOSED" and o["PX_G"]["exit_time"] == "12:31", f"4a G exit {o['PX_G'].get('exit_time')}")
ok(o["PX_H"]["status"] == "SKIPPED_PREMIUM" and o["PX_I"]["status"] == "OPEN", f"4 H={o['PX_H']['status']} I={o['PX_I']['status']}")
# 5: interaction with cap2 and check order
add("SENSEX", 80700, "PE", 500.0); add("SENSEX", 80800, "PE", 500.0); add("NIFTY", 25300, "PE", 1100.0); add("NIFTY", 25400, "CE", 100.0)
add("NIFTY", 25500, "CE", 100.0, chase_at=744)
fresh(); o = run([row("PX_J", "SENSEX", 80700, "PE", "12:00", "12:01", 500.0), row("PX_K", "SENSEX", 80800, "PE", "12:02", "12:03", 500.0),
                 row("PX_L", "NIFTY", 25300, "PE", "12:05", "12:06", 1100.0), row("PX_M", "NIFTY", 25500, "CE", "12:23", "12:24", 100.0)])
ok(o["PX_L"]["status"] == "SKIPPED_CAP", f"5a cap2 checked before premium {o['PX_L']['status']}")   # 2 open AND 2L + 7.15L > 9L: both fail -> cap2 label wins (checked first)
ok(o["PX_M"]["status"] == "SKIPPED_CHASE", f"5b anti-chase checked before cap2 {o['PX_M']['status']}")
# premium-skipped holds no slot: big open 5.59L, new 3.6L skipped, then a small one admitted as the 2nd slot
fresh(); o = run([row("PX_A", "NIFTY", 25000, "PE", "12:00", "12:01", 860.0), row("PX_B", "SENSEX", 80000, "CE", "12:09", "12:10", 1800.0),
                 row("PX_N", "NIFTY", 25400, "CE", "12:12", "12:13", 100.0)])
ok(o["PX_B"]["status"] == "SKIPPED_PREMIUM" and o["PX_N"]["status"] == "OPEN", f"5d premium skip holds no slot {o['PX_N']['status']}")
# 6: mixed NIFTY + SENSEX premium sum: NIFTY 3.25L (500) + SENSEX 5.0L (2500) open = 8.25L; NIFTY 120 x 650 = 0.78L -> 9.03L skipped (cap2 off here)
add("NIFTY", 25600, "PE", 500.0); add("SENSEX", 80900, "PE", 2500.0); add("NIFTY", 25700, "PE", 120.0)
fresh(cap_from=None); o = run([row("PX_O", "NIFTY", 25600, "PE", "12:00", "12:01", 500.0), row("PX_P", "SENSEX", 80900, "PE", "12:02", "12:03", 2500.0),
                              row("PX_Q", "NIFTY", 25700, "PE", "12:05", "12:06", 120.0)])
ok(o["PX_P"]["status"] == "OPEN" and o["PX_Q"]["status"] == "SKIPPED_PREMIUM", f"6 mixed {o['PX_Q']['status']}")
# 7: open trades untouched: same stop/target as with no limit
fresh(cap_from=None, prem_from=None); base = run([row("PX_A", "NIFTY", 25000, "PE", "12:00", "12:01", 860.0)])
fresh(); o = run([row("PX_A", "NIFTY", 25000, "PE", "12:00", "12:01", 860.0), row("PX_B", "SENSEX", 80000, "CE", "12:09", "12:10", 1800.0)])
ok((o["PX_A"]["stop_px"], o["PX_A"]["target_px"], o["PX_A"]["status"]) == (base["PX_A"]["stop_px"], base["PX_A"]["target_px"], base["PX_A"]["status"]), "7 open unchanged")
# 8: restart keeps decisions, no backdating; limit starts at prem_from (entries before it are not judged)
add("NIFTY", 25800, "PE", 860.0, target_at=726)        # touches target 12:06, before restart 12:10
add("SENSEX", 81000, "CE", 1800.0); add("SENSEX", 81100, "CE", 1800.0)
fresh(cap_from=None, prem_from=700)
pre = [row("PX_R", "NIFTY", 25800, "PE", "11:50", "11:51", 860.0), row("PX_S", "SENSEX", 81000, "CE", "11:55", "11:56", 1800.0)]
first = R.cap_and_price([copy.deepcopy(x) for x in pre], 720)
ok([r["status"] for r in first] == ["OPEN", "SKIPPED_PREMIUM"], f"8a {[r['status'] for r in first]}")
R.write(first, "pre"); R.START_FILE.write_text(json.dumps({"start_m": 730})); R.PREM_FILE.write_text(json.dumps({"prem_from_m": 700}))
R.CAP_FILE.write_text(json.dumps({"cap_from_m": 700}))
R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.CAP.update(from_m=None, admit=set(), skip=set()); R.PREM.update(from_m=None, skip=set())
R._start_load(735); R._cap_load(735); R._prem_load(735)
ok(R.PREM["from_m"] == 700 and ("PX_S", "SENSEX", "11:55") in R.PREM["skip"], f"8b reload {R.PREM}")
B[("NIFTY", 25800, "PE")] = bars(860.0, target_at=726)
o = run(pre + [row("PX_T", "SENSEX", 81100, "CE", "12:11", "12:12", 1800.0)], 736)
ok(o["PX_S"]["status"] in ("SKIPPED_PREMIUM", "PRE_START"), f"8c decision kept / never booked {o['PX_S']['status']}")
ok(o["PX_R"]["status"] == "OPEN" or (o["PX_R"]["status"] == "CLOSED" and R._m(o["PX_R"]["exit_time"]) > 730), f"8d no backdated exit {o['PX_R'].get('exit_time')}")
ok(o["PX_T"]["status"] == "SKIPPED_PREMIUM" if o["PX_R"]["status"] == "OPEN" or R._m(o["PX_R"]["exit_time"]) >= 732 else o["PX_T"]["status"] == "OPEN", f"8e T {o['PX_T']['status']} R exit {o['PX_R'].get('exit_time')}")
# first start: no file -> pinned now+1
R.PREM_FILE.unlink(); R.PREM.update(from_m=None, skip=set()); R._prem_load(700)
ok(R.PREM["from_m"] == 701 and json.loads(R.PREM_FILE.read_text())["premium_cap_inr"] == 900000, "8f first start pins prem_from")
# 9: write -> not_booked; desk never books; risk book ignores
fresh(); o = R.cap_and_price([copy.deepcopy(x) for x in (row("PX_A", "NIFTY", 25000, "PE", "12:00", "12:01", 860.0), row("PX_B", "SENSEX", 80000, "CE", "12:09", "12:10", 1800.0))], 745)
R.write(o, "t9"); j = json.loads(R.OUT.read_text())
ok([r["rule_id"] for r in j["rows"]] == ["PX_A"] and [r["status"] for r in j["not_booked"]] == ["SKIPPED_PREMIUM"], "9a rows/not_booked")
src = os.environ.get("DESKML_SRC")
if src:
    sys.path.insert(0, src); from desk_ml import research_rules as RR
    t = pathlib.Path(tempfile.mkdtemp()); p = t / "data/recon/paper_extra" / "2026-10-21.json"; p.parent.mkdir(parents=True)
    p.write_text(json.dumps(dict(j, rows=j["rows"] + j["not_booked"])))
    oo, cc = RR.paper_extra_rows(t, "2026-10-21"); ok(len(oo) == 1 and not cc and "PX_B" not in json.dumps(oo), "9b desk never books SKIPPED_PREMIUM")
tree = ast.parse(open(R.__file__).read()); fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "log_risk")
t2 = pathlib.Path(tempfile.mkdtemp()); (t2 / "data/recon/research_rules").mkdir(parents=True); (t2 / "data/recon/research_rules/2026-10-21.json").write_text(json.dumps({"open": [], "risk": {}}))
g = dict(json=json, datetime=R.datetime, IST=R.IST, REPO=t2, DAY="2026-10-21", OUT=R.OUT, LOT=R.LOT); exec(compile(ast.Module(body=[fn], type_ignores=[]), "r", "exec"), g)
g["log_risk"](); rec = json.loads((R.OUT.parent / "risk_minutes_2026-10-21.jsonl").read_text().splitlines()[-1])
ok(rec["book_open_trades"] == 1 and rec["book_premium_at_risk_inr"] == 559000.0, f"9c risk book {rec['book_open_trades']} {rec['book_premium_at_risk_inr']}")
print("test_premium_cap:", "ALL PASS" if not fails else f"FAIL {fails}"); sys.exit(1 if fails else 0)
