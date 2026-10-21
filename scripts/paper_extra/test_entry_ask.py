"""2026-10-21 entry-at-ask fix. Box only, synthetic depth file. Run: python3 test_entry_ask.py
Cases: fresh ask in entry minute -> v2_ask; ask only after the fresh window -> fallback; no tape -> 1m open + half spread (NIFTY 0.4977,
SENSEX 2.8275); stop/target levels follow the booked entry; source labelled; sticky (cache + file reload); not sticky while entry minute is
fresh; carried-over-restart row keeps its booked entry; PX_ENTRY_ASK=off -> old behaviour; zero/None asks ignored; other contract ignored."""
import json, os, sys, tempfile, importlib, pathlib, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE.clear(); R.LIVE_FILE = d / "live.json"; R.OUT = d / "out.json"; R.ENTRY_FILE = d / "entry_fill.json"
R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
B = {}
R._opt_bars = lambda u, K, side: B.setdefault((u, int(K), side), {m: (100.0, 101.0) for m in range(560, 930)})
DEP = d / "depth.jsonl"
def q(iid, ts, ask, bid=None, ets=None, rep=False):
    return json.dumps({"payload": {"instrument_id": iid, "bid": bid, "ask": ask, "exchange_ts": ets or ts, "repeat": rep}, "timestamp": ts}) + "\n"
FI = "NSE_FNO:NIFTY:2026-10-27:23300:PE"; GI = "NSE_FNO:NIFTY:2026-10-27:23350:PE"; HI = "NSE_FNO:NIFTY:2026-10-27:23400:PE"
NI = "NSE_FNO:NIFTY:2026-10-27:23100:PE"; SI = "BSE_FNO:SENSEX:2026-10-22:74900:PE"
DEP.write_text(q(NI, "2026-10-21T09:45:02.100+05:30", 101.35, 100.9) + q(NI, "2026-10-21T09:45:09.000+05:30", 102.0)
               + q(SI, "2026-10-21T10:05:20.000+05:30", 505.0) + q("NSE_FNO:NIFTY:2026-10-27:23000:CE", "2026-10-21T10:30:01+05:30", 99.0)
               + q(NI, "2026-10-21T11:00:03+05:30", 0) + q(NI, "2026-10-21T11:00:04+05:30", None)
               # 11 repeat frame first (old quote re-sent), then the first fresh one -> the fresh one is booked
               + q(FI, "2026-10-21T12:30:00.810+05:30", 88.35, ets="2026-10-21T12:29:59.750+05:30", rep=True)
               + q(FI, "2026-10-21T12:30:01.200+05:30", 86.0, ets="2026-10-21T12:30:01.100+05:30")
               # 12 frozen feed: only repeats of a quote from minute 12:39, all through the entry minute -> fallback
               + "".join(q(GI, "2026-10-21T12:40:%02d.500+05:30" % s_, 77.0, ets="2026-10-21T12:39:58.000+05:30", rep=True) for s_ in range(0, 14))
               # 13 not flagged repeat but exchange time from the previous minute (stale) -> ignored; 14 lag 5 s -> ignored
               + q(HI, "2026-10-21T12:50:01.000+05:30", 66.0, ets="2026-10-21T12:49:59.900+05:30")
               + q(HI, "2026-10-21T12:50:09.000+05:30", 67.0, ets="2026-10-21T12:50:04.000+05:30"))
def fresh():
    R.ENTRY.clear(); R.LIVE.clear(); R.START.update(m=None, frozen={}, carried=set()); R.ASKS = R.AskBook(DEP); R.ASKS.scan(); R.ENTRY_ASK_ON = True
    if R.ENTRY_FILE.exists(): R.ENTRY_FILE.unlink()
def row(rid, u, K, side, sig, ent, px):
    return dict(rule_id=rid, strategy=rid, underlying=u, qty=R.QTY[u], side=side, strike=float(K), signal_time=sig, entry_time=ent,
                entry_px=px, exit_px=None, exit_time=None, exit_reason=None, status="OPEN")
fresh(); r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 600)
ok(r["entry_px"] == 101.35 and r["entry_src"] == "v2_ask" and r["entry_px_1m_open"] == 100.0, f"1 fresh ask booked {r['entry_px']} {r['entry_src']}")
ok(r["stop_px"] == round(101.35 * 0.7, 2) and r["target_px"] == round(101.35 * 1.6, 2), "1b stop/target from the booked entry")
ok(abs(R.LIVE[("PX_EP010", "NIFTY", "09:44")].entry - 101.35) < 1e-9, "1c live pricer gets the booked entry")
fresh(); r = R.apply_price_exits(row("PX_EP010", "SENSEX", 74900, "PE", "10:04", "10:05", 500.0), 620)
ok(r["entry_px"] == round(500 + 2.8275, 2) and r["entry_src"] == "1m_open+half_spread", f"2 ask after 15 s ignored -> fallback {r['entry_px']}")
fresh(); r = R.apply_price_exits(row("PX_R07", "NIFTY", 23050, "CE", "12:00", "12:01", 80.0), 730)
ok(r["entry_px"] == round(80 + 0.4977, 2) and r["entry_src"] == "1m_open+half_spread", f"3 no tape -> NIFTY open + 0.4977 {r['entry_px']}")
fresh(); r = R.apply_price_exits(row("PX_IB_5", "NIFTY", 23000, "PE", "10:29", "10:30", 90.0), 640)
ok(r["entry_src"] == "1m_open+half_spread", "4 other contract's ask never used")
fresh(); r = R.apply_price_exits(row("PX_B2", "NIFTY", 23100, "PE", "10:59", "11:00", 95.0), 670)
ok(r["entry_src"] == "1m_open+half_spread", "5 zero / None ask ignored")
fresh(); x = row("PX_ENG_5", "NIFTY", 23200, "CE", "13:00", "13:01", 70.0); R.apply_price_exits(copy.deepcopy(x), 781)
ok(R.ENTRY.get("PX_ENG_5|NIFTY|13:00", {}).get("entry_px") == round(70 + 0.4977, 2), "6a fallback saved at once (v3), open + half spread")
R.apply_price_exits(copy.deepcopy(x), 783); ok("PX_ENG_5|NIFTY|13:00" in R.ENTRY, "6b sticky once entry minute is 2+ min old")
fresh(); R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 600)
R.ENTRY.clear(); R._entry_load(); R.ASKS = R.AskBook(d / "missing.jsonl")
r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 640)
ok(r["entry_px"] == 101.35 and r["entry_src"] == "v2_ask", "7 restart: entry_fill.json reload keeps the decision")
fresh(); R.START.update(m=700, frozen={}, carried={("PX_EP010", "NIFTY", "09:44")})
r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 710)
ok(r["entry_px"] == 100.0 and "entry_src" not in r, "8 row carried over a restart keeps its booked entry")
fresh(); R.ENTRY_ASK_ON = False; r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 600)
ok(r["entry_px"] == 100.0, "9 PX_ENTRY_ASK=off -> 1m open (old behaviour)")
fresh(); r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23100, "PE", "09:44", "09:45", 100.0), 600)
r2 = R.apply_price_exits(copy.deepcopy(r), 601); ok(r2["entry_px"] == 101.35, "10 a row already priced is not re-priced again (no double half-spread)")
fresh(); r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23300, "PE", "12:29", "12:30", 85.0), 760)
ok(r["entry_px"] == 86.0 and r["ask_ts"].startswith("2026-10-21T12:30:01.1"), f"11 repeat frame skipped, first fresh ask booked {r['entry_px']}")
fresh(); r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23350, "PE", "12:39", "12:40", 76.0), 770)
ok(r["entry_src"] == "1m_open+half_spread" and r["entry_px"] == round(76 + 0.4977, 2), f"12 frozen feed (repeats only) -> fallback {r['entry_px']}")
fresh(); r = R.apply_price_exits(row("PX_EP010", "NIFTY", 23400, "PE", "12:49", "12:50", 65.0), 780)
ok(r["entry_src"] == "1m_open+half_spread", f"13/14 stale exchange time or 5 s lag -> fallback {r['entry_px']}")
ok(R.AskBook.qualify({"payload": {"instrument_id": "X", "ask": 5}, "timestamp": "2026-10-21T10:00:01+05:30"}) is None, "15 no exchange_ts -> not used")
ok(R.TEST_MODE and R.REAL_DATA not in pathlib.Path(R.STATE).resolve().parents, "16 test mode: state folder is a temp dir")
try:
    R._w(R.REPO / "data" / "paper_extra" / "2026-10-21" / "entry_fill.json"); ok(False, "17 guard refuses real data path")
except RuntimeError:
    ok(True, "17 guard refuses real data path")
R.ENTRY_FILE = R.REPO / "data" / "paper_extra" / "2026-10-21" / "zz_guard_probe.json"
try:
    R._entry_fill(row("PX_Z", "NIFTY", 23000, "PE", "09:00", "09:01", 50.0), "NIFTY", 541, 600); probe = R.ENTRY_FILE.exists()
except RuntimeError:
    probe = R.ENTRY_FILE.exists()
ok(not probe, "18 _entry_fill cannot write into the real data path in a test")
R.ENTRY_FILE = d / "entry_fill.json"
# 19 (v3, review V2 #B) restart inside the 2-minute window on a no-ask entry: reload gives open + half spread, never the raw open
fresh(); x = row("PX_R07", "NIFTY", 23500, "CE", "13:20", "13:21", 60.0); R.apply_price_exits(copy.deepcopy(x), 801)   # now = em: not final
saved = json.loads(R.ENTRY_FILE.read_text()); ok(saved.get("PX_R07|NIFTY|13:20", {}).get("entry_src") == "1m_open+half_spread", "19a fallback on disk before em+2")
R.ENTRY.clear(); R.LIVE.clear(); R._entry_load(); R.START.update(m=802, frozen={}, carried={("PX_R07", "NIFTY", "13:20")})
r = R.apply_price_exits(copy.deepcopy(x), 803)
ok(r["entry_px"] == round(60 + 0.4977, 2) and r["entry_src"] == "1m_open+half_spread", f"19b carried row after restart books open + half spread {r['entry_px']}")
# 20 a late ask inside the window replaces the cached fallback; after em+2 the decision is final
JI = "NSE_FNO:NIFTY:2026-10-27:23550:CE"; fresh(); y = row("PX_R07", "NIFTY", 23550, "CE", "13:30", "13:31", 50.0)
r = R.apply_price_exits(copy.deepcopy(y), 811); ok(r["entry_src"] == "1m_open+half_spread", "20a no ask yet -> fallback")
with open(DEP, "a") as f: f.write(q(JI, "2026-10-21T13:31:02.000+05:30", 50.9))
R.ASKS.scan(); r = R.apply_price_exits(copy.deepcopy(y), 812); ok(r["entry_px"] == 50.9 and r["entry_src"] == "v2_ask", "20b late ask inside window replaces fallback")
lt = R.LIVE[("PX_R07", "NIFTY", "13:30")]
ok(abs(lt.entry - r["entry_px"]) < 1e-9 and abs(lt.target - 50.9 * 1.6) < 1e-9 and abs(lt.stop - max(50.9 * 0.7, 50.9, lt.hw * 0.7)) < 1e-9,
   f"20d live pricer rebuilt on the ask: entry {lt.entry} target {lt.target:.2f} stop {lt.stop:.2f}")
ok(r["stop_px"] == round(lt.stop, 2) and r["target_px"] == round(50.9 * 1.6, 2), f"20e row stop/target match the live pricer {r['stop_px']} {r['target_px']}")
lt = R.LP.LiveTrade.from_json(dict(lt.to_json(), closed=None, hw=50.9))   # fixture bars hit the target on 1m; check the live levels alone
c = lt.on_quote(81.0, "2026-10-21T13:33:05+05:30"); ok(c is None, "20f bid 81.0 (>= old target 80.8, < new 81.44) does not close")
c = lt.on_quote(81.5, "2026-10-21T13:33:08+05:30"); ok(c and c["why"] == "TARGET" and c["exit_px"] == 81.5, f"20g closes at the new target {c} nb={lt.not_before}")
with open(DEP, "a") as f: f.write(q("NSE_FNO:NIFTY:2026-10-27:23600:CE", "2026-10-21T13:41:03.000+05:30", 40.9))
fresh(); z = row("PX_R07", "NIFTY", 23600, "CE", "13:40", "13:41", 40.0); R.ASKS = R.AskBook(d / "missing.jsonl")
R.apply_price_exits(copy.deepcopy(z), 823); R.ASKS = R.AskBook(DEP); R.ASKS.scan()
r = R.apply_price_exits(copy.deepcopy(z), 824); ok(r["entry_src"] == "1m_open+half_spread", "20c after em+2 the fallback is final (no later change)")
print("FAILS:", fails) if fails else print("ALL PASS test_entry_ask")
sys.exit(1 if fails else 0)
