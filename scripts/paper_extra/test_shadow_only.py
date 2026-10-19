"""2026-10-21 SHADOW ONLY rules in the runner: priced/scored, but never take a cap2 slot or premium. Run: python3 test_shadow_only.py"""
import os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.OUT = d / "out.json"
R.CAP_FILE = d / "cap_start.json"; R.PREM_FILE = d / "premium_cap_start.json"; R.START_FILE = d / "runner_start.json"
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, m):
    if not c: fails.append(m)
B = {}
R._opt_bars = lambda u, K, side: B.get((u, int(K), side), {})
def row(rid, K, sig, ent, px=100.0):
    B[("NIFTY", K, "CE")] = {m: (px * 1.01, px * 1.02) for m in range(600, 760)}
    return dict(rule_id=rid, strategy=rid, underlying="NIFTY", qty=650, side="CE", strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
def fresh():
    R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.CAP.update(from_m=600, admit=set(), skip=set()); R.PREM.update(from_m=600, skip=set())
ok(R._shadow_only() == {"PX_ENG_5", "PX_EP018", "PX_IB_15", "PX_MINE_PE", "PX_ORB_A", "PX_R07"}, f"ids {R._shadow_only()}")
# cap2 = 2 open: two shadow rows first, then two real rows -> both real rows admitted (shadow holds no slot)
fresh()
rows = [row("PX_ENG_5", 25000, "10:00", "10:01"), row("PX_R07", 25050, "10:01", "10:02"),
        row("PX_EP010", 25100, "10:02", "10:03"), row("PX_VWAP_CONT", 25150, "10:03", "10:04"), row("PX_IB_5", 25200, "10:04", "10:05")]
o = {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in rows], 745)}
ok(o["PX_ENG_5"]["status"] == "OPEN" and o["PX_ENG_5"].get("shadow_only") is True, f"shadow priced {o['PX_ENG_5']}")
ok(o["PX_EP010"]["status"] == "OPEN" and o["PX_VWAP_CONT"]["status"] == "OPEN", "real rows admitted past shadow rows")
ok(o["PX_IB_5"]["status"] == "SKIPPED_CAP", f"cap2 still applies to real rows {o['PX_IB_5']['status']}")
ok(not o["PX_EP010"].get("shadow_only"), "keep rules not flagged")
print("FAIL" if fails else "ALL PASS", "4 checks" + ("" if not fails else f": {fails}"))
sys.exit(1 if fails else 0)
