"""2026-10-21 (Opposition two-week audit #7): same-contract guard in the paper-extra book. Box only, no network, synthetic bars.
Run: python3 test_dup_contract.py
Cases: Oct 16 ENG_5 + IB_5 both NIFTY 23100 CE at 11:25 -> second is SKIPPED_DUP_CONTRACT; other strike / other side / other index allowed;
held-trade exit frees the contract (same-minute exit still holds); sticky + restart reload; entries before dup_from_m not judged;
blocked row holds no cap2 slot; PX_DUP_GUARD=off restores old behaviour; write() -> not_booked; shadow-only rows never block or get blocked."""
import json, os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
_SHADOW = R._shadow_only(); R._shadow_only = lambda: set()
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.OUT = d / "out.json"
R.CAP_FILE = d / "cap.json"; R.PREM_FILE = d / "prem.json"; R.DUP_FILE = d / "dup_guard_start.json"; R.START_FILE = d / "runner_start.json"; R.ENTRY_FILE = d / "entry_fill.json"; R.ENTRY.clear()
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, msg):
    print(("PASS " if c else "FAIL ") + msg)
    if not c: fails.append(msg)
def bars(p0, exit_at=None, lvl=1.7):
    ob = {m: (p0 * 1.01, p0 * 1.02) for m in range(600, 930)}
    if exit_at: ob.update({m: (p0 * lvl, p0 * lvl) for m in range(exit_at, 930)})
    return ob
B = {}
R._opt_bars = lambda u, K, side: B[(u, int(K), side)]
def row(rid, u, K, side, sig, ent, px):
    B.setdefault((u, int(K), side), bars(px))
    return dict(rule_id=rid, strategy=rid, underlying=u, qty=R.QTY[u], side=side, strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
def fresh(dup_from=600, cap_from=None, on=True):
    R.DUP_ON = on; R.LIVE.clear(); R.ENTRY.clear(); R.START.update(m=None, frozen={}, carried=set())
    R.CAP.update(from_m=cap_from, admit=set(), skip=set()); R.PREM.update(from_m=None, skip=set()); R.DUP.update(from_m=dup_from, skip=set())
def run(rows, now_m):
    return {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in rows], now_m)}
ENG = row("PX_ENG_5", "NIFTY", 23100, "CE", "11:24", "11:25", 104.00)
IB = row("PX_IB_5", "NIFTY", 23100, "CE", "11:24", "11:25", 104.00)
fresh(); o = run([ENG, IB], 700)
st = sorted(x["status"] for x in o.values())
ok(st == ["OPEN", "SKIPPED_DUP_CONTRACT"], f"1 Oct16 case: one booked, one skipped {st}")
sk = [x for x in o.values() if x["status"] == "SKIPPED_DUP_CONTRACT"][0]
ok("NIFTY 23100 CE" in sk["note"] and sk.get("exit_px") is None, "1b note names the held contract, no exit")
ok(sum(1 for k in R.LIVE if k[0] == sk["rule_id"]) == 0, "1c skipped row never registered for live pricing")
fresh(); ok(run([ENG, row("PX_IB_15", "NIFTY", 23150, "CE", "11:24", "11:25", 90.0)], 700)["PX_IB_15"]["status"] == "OPEN", "2a other strike allowed")
fresh(); ok(run([ENG, row("PX_MINE_PE", "NIFTY", 23100, "PE", "11:24", "11:25", 90.0)], 700)["PX_MINE_PE"]["status"] == "OPEN", "2b other side allowed")
fresh(); ok(run([ENG, row("PX_R07", "SENSEX", 23100, "CE", "11:24", "11:25", 90.0)], 700)["PX_R07"]["status"] == "OPEN", "2c other index allowed")
B[("NIFTY", 23200, "CE")] = bars(100.0, exit_at=700, lvl=0.6)   # stop trigger 11:40 close -> fill 11:41 (a drop, so anti-chase stays quiet)
X = row("PX_VWAP_CONT", "NIFTY", 23200, "CE", "11:00", "11:01", 100.0)
same = row("PX_EP010", "NIFTY", 23200, "CE", "11:40", "11:41", 100.0); after = row("PX_EP018", "NIFTY", 23200, "CE", "11:41", "11:42", 100.0)
fresh(); o = run([X, same, after], 760)
ok(o["PX_VWAP_CONT"]["status"] == "CLOSED" and o["PX_VWAP_CONT"]["exit_time"] == "11:41", f"3a held exits 11:41 {o['PX_VWAP_CONT'].get('exit_time')}")
ok(o["PX_EP010"]["status"] == "SKIPPED_DUP_CONTRACT" and o["PX_EP018"]["status"] in ("OPEN", "CLOSED"),
   f"3b same-minute blocked {o['PX_EP010']['status']}, after exit admitted {o['PX_EP018']['status']}")
o2 = {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in (after, same, X)], 770)}
ok(o2["PX_EP010"]["status"] == "SKIPPED_DUP_CONTRACT", "4a sticky across cycles")
R.write(list(o2.values()), "t"); j = json.loads(R.OUT.read_text())
ok([r["rule_id"] for r in j["not_booked"]] == ["PX_EP010"], "4b write: SKIPPED_DUP_CONTRACT -> not_booked")
R.DUP.update(from_m=None, skip=set()); R.DUP_FILE.write_text(json.dumps({"dup_from_m": 600})); R._dup_load(800)
ok(R.DUP["from_m"] == 600 and ("PX_EP010", "NIFTY", "11:40") in R.DUP["skip"], "4c restart reload keeps skip + from_m")
R.DUP_FILE.unlink(); R._dup_load(700)
ok(R.DUP["from_m"] == 701 and json.loads(R.DUP_FILE.read_text())["dup_from_m"] == 701, "4d first start pins dup_from_m = now+1")
fresh(dup_from=690); st = sorted(x["status"] for x in run([ENG, IB], 700).values())
ok(st == ["OPEN", "OPEN"], f"5 entries before dup_from_m not judged {st}")
P2 = row("PX_R07", "SENSEX", 74000, "PE", "11:24", "11:25", 500.0)
fresh(cap_from=600); o = run([ENG, IB, P2], 700)
ok(o["PX_R07"]["status"] == "OPEN", f"6 blocked row holds no cap2 slot {o['PX_R07']['status']}")
fresh(on=False); st = sorted(x["status"] for x in run([ENG, IB], 700).values())
ok(st == ["OPEN", "OPEN"], f"7 PX_DUP_GUARD=off -> old behaviour {st}")
R._shadow_only = lambda: {"PX_ENG_5"}
fresh(); o = run([ENG, IB], 700)
ok(o["PX_IB_5"]["status"] == "OPEN" and o["PX_ENG_5"].get("shadow_only") is True, f"8 shadow-only ENG_5 does not block IB_5 {o['PX_IB_5']['status']}")
R._shadow_only = lambda: _SHADOW
# 9 (v3, review V2 #A) full once() cycle: dup skip -> OUT day file "not_booked" -> restart -> _dup_load reloads it -> still skipped
R._shadow_only = lambda: set(); fresh(dup_from=600)
for nm, v in dict(fetch=lambda: "f", score=lambda: ({}, "s"), rows_all=lambda sr: [copy.deepcopy(ENG), copy.deepcopy(IB)],
                  q01_cycle=lambda m: ([], None, "q"), write_bg_t15=lambda bg: None, pshadow_cycle=lambda: "p", tag_rows=lambda rows: "t",
                  overlay_rows=lambda rows, m: "o", shadow_log=lambda rows: "sl", overlay_log=lambda rows, m: "ol", log_risk=lambda: "r").items():
    setattr(R, nm, v)
R.ENTRY_ASK_ON = False; R.once(); j = json.loads(R.OUT.read_text())
nb = [(r["rule_id"], r["status"]) for r in j.get("not_booked") or []]
ok(("PX_IB_5", "SKIPPED_DUP_CONTRACT") in nb or ("PX_ENG_5", "SKIPPED_DUP_CONTRACT") in nb, f"9a once(): dup skip written to OUT not_booked {nb}")
ok(all(r["status"] in ("OPEN", "CLOSED") for r in j["rows"]) and len(j["rows"]) == 1, "9b only the booked one is in rows")
skipped = [r for r in j["not_booked"] if r["status"] == "SKIPPED_DUP_CONTRACT"][0]["rule_id"]
R.DUP.update(from_m=None, skip=set()); R.DUP_FILE.write_text(json.dumps({"dup_from_m": 600})); R._dup_load(900)
ok((skipped, "NIFTY", "11:24") in R.DUP["skip"], "9c restart: _dup_load reloads the skip from the day file")
R.once(); j2 = json.loads(R.OUT.read_text())
ok([r["rule_id"] for r in j2["not_booked"] if r["status"] == "SKIPPED_DUP_CONTRACT"] == [skipped], "9d after restart the same row stays skipped")
print("real shadow list:", sorted(_SHADOW))
print("FAILS:", fails) if fails else print("ALL PASS test_dup_contract")
sys.exit(1 if fails else 0)
