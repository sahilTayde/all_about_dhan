"""2026-10-22 wrong-side guard (Sahil 1:1 2026-10-21 22:57 CT). Box/Mac test, no network, synthetic bars. Run: python3 test_wrong_side.py
Cases: Oct 21 shape (NIFTY falling all day) -> 10:40 CE blocked, PE allowed; before 10:00 never blocked; rising day blocks PE;
neutral (below open but above vwap) allowed; other index read separately; sticky + restart reload; entries before ws_from_m not judged;
blocked row holds no cap2 slot; PX_WRONG_SIDE=off restores old behaviour; write() -> not_booked; no lookahead (later bars ignored)."""
import json, os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
R._shadow_only = lambda: set()
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.OUT = d / "out.json"
R.CAP_FILE = d / "cap.json"; R.PREM_FILE = d / "prem.json"; R.DUP_FILE = d / "dup.json"; R.START_FILE = d / "start.json"; R.ENTRY_FILE = d / "entry.json"; R.ENTRY.clear()
R.WS_FILE = d / "wrong_side_start.json"; R.WS_LOG = d / "wrong_side.jsonl"
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, msg):
    print(("PASS " if c else "FAIL ") + msg)
    if not c: fails.append(msg)
def falling(o=23000.0, step=-1.0):
    return {m: (o + step * (m - 555), o + step * (m - 555) + 2, o + step * (m - 555) - 2, o + step * (m - 555 + 1)) for m in range(555, 931)}
IDX = {"NIFTY": falling(), "SENSEX": falling(74000.0, 3.0)}   # NIFTY falling, SENSEX rising
R._idx_ohlc = lambda u: IDX[u]
B = {}
R._opt_bars = lambda u, K, side: B[(u, int(K), side)]
def row(rid, u, K, side, sig, ent, px):
    B.setdefault((u, int(K), side), {m: (px * 1.01, px * 1.02) for m in range(555, 930)})
    return dict(rule_id=rid, strategy=rid, underlying=u, qty=R.QTY[u], side=side, strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
def fresh(ws_from=556, cap_from=None, on=True):
    R.WS_ON = on; R.DUP_ON = True; R.LIVE.clear(); R.ENTRY.clear(); R.START.update(m=None, frozen={}, carried=set())
    R.CAP.update(from_m=cap_from, admit=set(), skip=set()); R.PREM.update(from_m=None, skip=set()); R.DUP.update(from_m=None, skip=set())
    R.WS.update(from_m=ws_from, skip=set())
def run(rows, now_m):
    return {r["rule_id"]: r for r in R.cap_and_price([copy.deepcopy(x) for x in rows], now_m)}
CE = row("PX_EP010", "NIFTY", 22950, "CE", "10:39", "10:40", 186.65)
PE = row("PX_IB_5", "NIFTY", 22850, "PE", "10:39", "10:40", 158.35)
fresh(); o = run([CE, PE], 700)
ok(o["PX_EP010"]["status"] == "BLOCKED_WRONG_SIDE", f"1a Oct21 shape: CE into falling NIFTY blocked {o['PX_EP010']['status']}")
ok(o["PX_IB_5"]["status"] == "OPEN", "1b PE with the trend allowed")
ok("FALLING" in o["PX_EP010"]["note"] and o["PX_EP010"]["wrong_side"]["at"] == "10:39" and o["PX_EP010"].get("exit_px") is None, "1c note + read at signal minute")
ok(not any(k[0] == "PX_EP010" for k in R.LIVE), "1d blocked row never live-priced")
fresh(); o = run([row("PX_B2", "NIFTY", 23000, "CE", "09:44", "09:45", 100.0)], 700)
ok(o["PX_B2"]["status"] == "OPEN", "2 before 10:00 never blocked")
fresh(); o = run([row("PX_R07", "SENSEX", 74500, "PE", "10:39", "10:40", 300.0), row("PX_ORB_A", "SENSEX", 74500, "CE", "10:39", "10:40", 300.0)], 700)
ok(o["PX_R07"]["status"] == "BLOCKED_WRONG_SIDE" and o["PX_ORB_A"]["status"] == "OPEN", "3 SENSEX rising: PE blocked, CE allowed (own index)")
save = IDX["NIFTY"]; IDX["NIFTY"] = dict(save)
for m in range(600, 640): IDX["NIFTY"][m] = (22999, 23000, 22998, 22999.0)   # just below open, above the running vwap? make vwap lower
IDX["NIFTY"].update({m: (22900, 22901, 22899, 22900) for m in range(556, 600)})
fresh(); o = run([CE], 700)
st, info = R.ws_trend(IDX["NIFTY"], 639)
ok(st == "NEUTRAL" and o["PX_EP010"]["status"] == "OPEN", f"4 below open but above vwap = NEUTRAL, allowed ({st} {info})")
IDX["NIFTY"] = save
look = dict(save); look.update({m: (24000, 24001, 23999, 24000) for m in range(640, 931)})   # big rally AFTER the signal
ok(R.ws_trend(look, 639)[0] == "FALLING", "5 no lookahead: later bars ignored")
fresh(); o = run([CE], 700); o2 = run([CE], 760)
ok(o2["PX_EP010"]["status"] == "BLOCKED_WRONG_SIDE", "6a sticky across cycles")
R.write(list(o2.values()), "t"); j = json.loads(R.OUT.read_text())
ok([r["rule_id"] for r in j["not_booked"]] == ["PX_EP010"] and j["rows"] == [], "6b write: BLOCKED_WRONG_SIDE -> not_booked")
R.WS.update(from_m=None, skip=set()); R.WS_FILE.write_text(json.dumps({"ws_from_m": 556})); R._ws_load(800)
ok(R.WS["from_m"] == 556 and ("PX_EP010", "NIFTY", "10:39") in R.WS["skip"], "6c restart reload keeps skip + from_m")
R.WS_FILE.unlink(); R._ws_load(700)
ok(R.WS["from_m"] == 701 and json.loads(R.WS_FILE.read_text())["ws_from_m"] == 701, "6d first start pins ws_from_m = now+1")
fresh(ws_from=690); ok(run([CE], 700)["PX_EP010"]["status"] == "OPEN", "7 entries before ws_from_m not judged (already booked stays)")
fresh(cap_from=556); R.CAP_MAX = 1
o = run([CE, row("PX_VWAP_CONT", "NIFTY", 23100, "PE", "10:40", "10:41", 120.0)], 700); R.CAP_MAX = 2
ok(o["PX_VWAP_CONT"]["status"] == "OPEN", "8 blocked row holds no cap slot")
fresh(on=False); ok(run([CE], 700)["PX_EP010"]["status"] == "OPEN", "9 PX_WRONG_SIDE=off restores old behaviour")
fresh(); txt = R.ws_status(700)
ok("NIFTY=FALLING" in txt and "SENSEX=RISING" in txt and R.WS_LOG.read_text().count("\n") == 1, f"10 status log: {txt}")
print("ALL PASS" if not fails else f"{len(fails)} FAIL"); sys.exit(1 if fails else 0)
