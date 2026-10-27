"""2026-10-19 cap: paper-extra book holds at most 2 open trades (NIFTY+SENSEX). Box/Mac, no network. Run: python3 test_cap2.py
Case: 2 open SENSEX trades carried from before the cap (11:13, 11:52) + a third signal at 12:20 -> SKIPPED_CAP (not booked, no live
registration, kept in not_booked); open trades' stops/targets identical to the no-cap run; a signal after a slot frees is admitted;
decisions are sticky across cycles and restarts; desk booking (research_rules) and risk_minutes book_* ignore SKIPPED_CAP."""
import ast, json, os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
R._shadow_only = lambda: set()   # cap2 fixture predates the 2026-10-21 shadow-only list (test_shadow_only.py covers that)
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.OUT = d / "out.json"; R.ENTRY_FILE = d / "entry_fill.json"; R.ENTRY.clear(); R.CAP_FILE = d / "cap_start.json"
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, msg):
    if not c: fails.append(msg)
hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
def bars(p0, target_at=None):
    ob = {m: (p0 * 1.01, p0 * 1.02) for m in range(600, 760)}
    if target_at: ob.update({m: (p0 * 1.7, p0 * 1.7) for m in range(target_at, 760)})
    return ob
B = {("SENSEX", 74800, "PE"): bars(635.1), ("SENSEX", 74500, "PE"): bars(634.65, target_at=750),
     ("NIFTY", 25000, "PE"): bars(80.0), ("SENSEX", 74600, "CE"): bars(500.0)}
R._opt_bars = lambda u, K, side: B[(u, int(K), side)]
def row(rid, u, K, side, sig, ent, px):
    return dict(rule_id=rid, strategy=rid, underlying=u, qty=R.QTY[u], side=side, strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
A = row("PX_VWAP_CONT", "SENSEX", 74800, "PE", "11:12", "11:13", 635.1)
Bo = row("PX_ORB_A", "SENSEX", 74500, "PE", "11:51", "11:52", 634.65)
C = row("PX_EP010", "NIFTY", 25000, "PE", "12:19", "12:20", 80.0)          # third while 2 open -> SKIPPED_CAP
D = row("PX_IB_5", "SENSEX", 74600, "CE", "12:39", "12:40", 500.0)         # after ORB_A target (12:30 trigger, 12:31 fill) -> admitted
R.START.update(m=697, frozen={}, carried={(A["rule_id"], "SENSEX", "11:12"), (Bo["rule_id"], "SENSEX", "11:51")})
# baseline (no cap) for the two open trades
R.CAP.update(from_m=None, admit=set(), skip=set())
base = {r["rule_id"]: (r["status"], r["stop_px"], r["target_px"]) for r in R.cap_and_price([copy.deepcopy(A), copy.deepcopy(Bo)], 745)}
R.LIVE.clear()
R.CAP.update(from_m=731, admit={(A["rule_id"], "SENSEX", "11:12"), (Bo["rule_id"], "SENSEX", "11:51")}, skip=set())   # cap from 12:11
out = R.cap_and_price([copy.deepcopy(x) for x in (A, Bo, C)], 745)
st = {r["rule_id"]: r for r in out}
ok(st["PX_EP010"]["status"] == "SKIPPED_CAP", f"1 third signal skipped {st['PX_EP010']['status']}")
ok(all(k[0] != "PX_EP010" for k in R.LIVE), "2 skipped signal never registered for live pricing")
ok({k: (st[k]["status"], st[k]["stop_px"], st[k]["target_px"]) for k in base} == base, f"3 open trades unchanged {base}")
ok([r["rule_id"] for r in out] == ["PX_VWAP_CONT", "PX_ORB_A", "PX_EP010"], "4 output order preserved")
# later cycle: ORB_A hits target 12:30 (fill 12:31); D at 12:40 admitted; C stays SKIPPED_CAP (sticky)
out2 = R.cap_and_price([copy.deepcopy(x) for x in (A, Bo, C, D)], 760)
st2 = {r["rule_id"]: r for r in out2}
ok(st2["PX_ORB_A"]["status"] == "CLOSED" and st2["PX_ORB_A"]["exit_time"] == "12:31", f"5 ORB_A target {st2['PX_ORB_A'].get('exit_time')}")
ok(st2["PX_EP010"]["status"] == "SKIPPED_CAP", "6 skip sticky")
ok(st2["PX_IB_5"]["status"] == "OPEN", f"7 slot freed -> admitted {st2['PX_IB_5']['status']}")
# 3 open at once never happens: count opens at every minute
for m in range(680, 761):
    n = sum(1 for r in out2 if r["status"] in ("OPEN", "CLOSED") and R._m(r["entry_time"]) <= m and (r["status"] == "OPEN" or R._m(r["exit_time"]) >= m))
    ok(n <= 2, f"8 {n} open at {hm(m)}")
# write(): SKIPPED_CAP -> not_booked; restart reload keeps it skipped
R.write(out2, "test"); j = json.loads(R.OUT.read_text())
ok(all(r["status"] in ("OPEN", "CLOSED") for r in j["rows"]) and [r["rule_id"] for r in j["not_booked"]] == ["PX_EP010"], "9 not_booked holds SKIPPED_CAP")
R.CAP.update(from_m=None, admit=set(), skip=set()); R.CAP_FILE.write_text(json.dumps({"cap_from_m": 731})); R._cap_load(800)
ok(R.CAP["from_m"] == 731 and ("PX_EP010", "NIFTY", "12:19") in R.CAP["skip"] and ("PX_IB_5", "SENSEX", "12:39") in R.CAP["admit"], "10 restart reload")
# fresh day: no cap file -> pinned at now+1
R.CAP_FILE.unlink(); R._cap_load(700); ok(R.CAP["from_m"] == 701 and json.loads(R.CAP_FILE.read_text())["cap_from_m"] == 701, "11 first start pins cap_from")
# desk booking ignores SKIPPED_CAP
src = os.environ.get("DESKML_SRC")
if src:
    sys.path.insert(0, src); from desk_ml import research_rules as RR
    t = pathlib.Path(tempfile.mkdtemp()); p = t / "data/recon/paper_extra" / "2026-10-21.json"; p.parent.mkdir(parents=True)
    p.write_text(json.dumps(dict(j, rows=j["rows"] + j["not_booked"])))      # even if a SKIPPED_CAP row leaked into rows
    o, c = RR.paper_extra_rows(t, "2026-10-21")
    ok(all("EP010" not in json.dumps(x) for x in o + c), "12 desk never books SKIPPED_CAP")
# risk_minutes book_* ignore SKIPPED_CAP
tree = ast.parse(open(R.__file__).read()); fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "log_risk")
t2 = pathlib.Path(tempfile.mkdtemp()); (t2 / "data/recon/research_rules").mkdir(parents=True); (t2 / "data/recon/research_rules/2026-10-21.json").write_text(json.dumps({"open": [], "risk": {}}))
g = dict(json=json, datetime=R.datetime, IST=R.IST, REPO=t2, DAY="2026-10-21", OUT=R.OUT, LOT=R.LOT, _w=R._w); exec(compile(ast.Module(body=[fn], type_ignores=[]), "r", "exec"), g)
g["log_risk"](); rec = json.loads((R.OUT.parent / "risk_minutes_2026-10-21.jsonl").read_text().splitlines()[-1])
ok(rec["book_open_trades"] == 2 and all(x[0] != "PX_EP010" for x in rec["book_open"]), f"13 risk book {rec['book_open']}")
# ---------- extra cases (Sahil "test thoroughly!") ----------
def fresh(from_m=600):
    R.ENTRY.clear(); R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.CAP.update(from_m=from_m, admit=set(), skip=set())
def addbars(u, K, side, p0, target_at=None):
    B[(u, K, side)] = bars(p0, target_at)
def opens_at(rows, m):
    return sum(1 for r in rows if r["status"] in ("OPEN", "CLOSED") and R._m(r["entry_time"]) <= m and (r["status"] == "OPEN" or R._m(r["exit_time"]) >= m))
# 14: three signals in the same minute, book empty -> first two (signal order) admitted, third SKIPPED_CAP; re-run is stable
for K in (25100, 25200, 25300): addbars("NIFTY", K, "CE", 90.0)
fresh()
S3 = [row(f"PX_R{i}", "NIFTY", K, "CE", "12:29", "12:30", 90.0) for i, K in enumerate((25100, 25200, 25300))]
o = R.cap_and_price([copy.deepcopy(x) for x in S3], 745)
ok([r["status"] for r in o] == ["OPEN", "OPEN", "SKIPPED_CAP"], f"14 same minute {[r['status'] for r in o]}")
o = R.cap_and_price([copy.deepcopy(x) for x in reversed(S3)], 746)
ok({r["rule_id"]: r["status"] for r in o} == {"PX_R0": "OPEN", "PX_R1": "OPEN", "PX_R2": "SKIPPED_CAP"}, "14b sticky even if input order changes")
ok(max(opens_at(o, m) for m in range(700, 760)) == 2, "14c never 3 open")
# 15: slot frees in the same cycle: open trade's target fills at 12:31 (trigger 12:30) -> entry at 12:32 admitted; entry at 12:31 (same minute
# as the exit fill) is conservatively SKIPPED_CAP
addbars("SENSEX", 74900, "PE", 600.0, target_at=750); addbars("NIFTY", 25400, "PE", 70.0); addbars("NIFTY", 25500, "PE", 70.0); addbars("NIFTY", 25600, "PE", 70.0)
fresh()
o1 = row("PX_A", "SENSEX", 74900, "PE", "12:00", "12:01", 600.0); o2 = row("PX_B", "NIFTY", 25400, "PE", "12:05", "12:06", 70.0)
same = row("PX_C", "NIFTY", 25500, "PE", "12:30", "12:31", 70.0); after = row("PX_D", "NIFTY", 25600, "PE", "12:31", "12:32", 70.0)
o = {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in (o1, o2, same, after)], 760)}
ok(o["PX_A"]["status"] == "CLOSED" and o["PX_A"]["exit_time"] == "12:31", f"15a exit {o['PX_A'].get('exit_time')}")
ok(o["PX_C"]["status"] == "SKIPPED_CAP" and o["PX_D"]["status"] == "OPEN", f"15 slot frees same cycle C={o['PX_C']['status']} D={o['PX_D']['status']}")
ok(max(opens_at(list(o.values()), m) for m in range(700, 760)) == 2, "15c never 3 open")
# 16: restart while 2 are open: carried rows keep levels, no exit before the restart minute even though a target was touched earlier,
# a signal entering before the restart minute is PRE_START (not counted), one after is capped, cap_from survives
addbars("SENSEX", 75000, "PE", 500.0, target_at=726)        # target touched 12:06, before restart at 12:10
addbars("NIFTY", 25700, "CE", 60.0); addbars("NIFTY", 25800, "CE", 60.0); addbars("SENSEX", 75100, "CE", 400.0)
fresh(from_m=700)
p1 = row("PX_E", "SENSEX", 75000, "PE", "11:50", "11:51", 500.0); p2 = row("PX_F", "NIFTY", 25700, "CE", "11:55", "11:56", 60.0)
first = R.cap_and_price([copy.deepcopy(p1), copy.deepcopy(p2)], 720)        # before the target (cycle at 12:00)
ok([r["status"] for r in first] == ["OPEN", "OPEN"], "16a both open before restart")
R.write(first, "pre-restart"); R.START_FILE = d / "runner_start.json"; R.START_FILE.write_text(json.dumps({"start_m": 730})); R.CAP_FILE.write_text(json.dumps({"cap_from_m": 700}))
R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.CAP.update(from_m=None, admit=set(), skip=set())
R._start_load(735); R._cap_load(735)
ok(R.START["m"] == 730 and R.CAP["from_m"] == 700 and len(R.START["carried"]) == 2, f"16b reload start {R.START['m']} cap {R.CAP['from_m']}")
pre = row("PX_G", "NIFTY", 25800, "CE", "12:07", "12:08", 60.0)            # entered before restart -> PRE_START
new = row("PX_H", "SENSEX", 75100, "CE", "12:09", "12:10", 400.0)          # at the restart minute while 2 open (E exits 12:11) -> SKIPPED_CAP
o = {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in (p1, p2, pre, new)], 736)}
ok(o["PX_E"]["status"] == "OPEN" or (o["PX_E"]["status"] == "CLOSED" and R._m(o["PX_E"]["exit_time"]) > 730),
   f"16c no backdated exit {o['PX_E']['status']} {o['PX_E'].get('exit_time')}")
ok(o["PX_E"]["target_px"] == first[0]["target_px"] and o["PX_F"]["stop_px"] == first[1]["stop_px"], "16d levels unchanged")
ok(o["PX_G"]["status"] == "PRE_START" and o["PX_H"]["status"] == "SKIPPED_CAP", f"16e G={o['PX_G']['status']} H={o['PX_H']['status']}")
# 17: mixed NIFTY + SENSEX: 1 NIFTY + 1 SENSEX open -> a third on either underlying is skipped
for K in (25900, 26000): addbars("NIFTY", K, "PE", 50.0)
for K in (75200, 75300): addbars("SENSEX", K, "PE", 300.0)
fresh()
mix = [row("PX_N1", "NIFTY", 25900, "PE", "12:00", "12:01", 50.0), row("PX_S1", "SENSEX", 75200, "PE", "12:02", "12:03", 300.0),
       row("PX_N2", "NIFTY", 26000, "PE", "12:10", "12:11", 50.0), row("PX_S2", "SENSEX", 75300, "PE", "12:12", "12:13", 300.0)]
o = {r["rule_id"]: r["status"] for r in R.cap_and_price([copy.deepcopy(x) for x in mix], 745)}
ok(o == {"PX_N1": "OPEN", "PX_S1": "OPEN", "PX_N2": "SKIPPED_CAP", "PX_S2": "SKIPPED_CAP"}, f"17 mixed {o}")
# 18: SKIPPED_CAP never counts toward P&L or open count: a skipped row does not hold a slot, and the desk books none of it
addbars("SENSEX", 75400, "PE", 300.0, target_at=736); addbars("NIFTY", 26100, "PE", 50.0)
fresh()
q = [row("PX_P1", "SENSEX", 75400, "PE", "12:00", "12:01", 300.0), row("PX_P2", "NIFTY", 25900, "PE", "12:02", "12:03", 50.0),
     row("PX_P3", "NIFTY", 26000, "PE", "12:05", "12:06", 50.0),      # skipped (2 open)
     row("PX_P4", "NIFTY", 26100, "PE", "12:20", "12:21", 50.0)]      # P1 target fill 12:17 -> slot free; P3 (skipped) must not hold it
o = R.cap_and_price([copy.deepcopy(x) for x in q], 745); st = {r["rule_id"]: r["status"] for r in o}
ok(st == {"PX_P1": "CLOSED", "PX_P2": "OPEN", "PX_P3": "SKIPPED_CAP", "PX_P4": "OPEN"}, f"18a skipped holds no slot {st}")
R.write(o, "t18"); j = json.loads(R.OUT.read_text())
ok(sorted(r["rule_id"] for r in j["rows"]) == ["PX_P1", "PX_P2", "PX_P4"] and [r["rule_id"] for r in j["not_booked"]] == ["PX_P3"], "18b rows/not_booked")
if src:
    t = pathlib.Path(tempfile.mkdtemp()); p = t / "data/recon/paper_extra" / "2026-10-21.json"; p.parent.mkdir(parents=True); p.write_text(json.dumps(j))
    oo, cc = RR.paper_extra_rows(t, "2026-10-21")
    ok(len(oo) == 2 and len(cc) == 1 and all("P3" not in json.dumps(x) for x in oo + cc), f"18c desk books open {len(oo)} closed {len(cc)}, never P3")
g["OUT"] = R.OUT; g["log_risk"](); rec = json.loads((R.OUT.parent / "risk_minutes_2026-10-21.jsonl").read_text().splitlines()[-1])
ok(rec["book_open_trades"] == 2 and all(x[0] != "PX_P3" for x in rec["book_open"]), f"18d risk book {rec['book_open']}")
print("test_cap2:", "ALL PASS" if not fails else f"FAIL {fails}"); sys.exit(1 if fails else 0)
