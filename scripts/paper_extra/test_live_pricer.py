"""Tests for live_pricer + the runner's price-exit path (2026-10-19). Box/Mac, no network. Run: python3 test_live_pricer.py
1 marks at the BID (never mid/ltp), 2 stop, 3 break-even trail, 4 high-water trail, 5 target, 6 stop wins over target, 7 bid None ignored,
8 15:15 safety, 9 stale -> fallback flag, 10 DepthTail incremental read, 11 runner fallback closes on 1m bars when live is stale,
12 runner keeps OPEN and marks at live bid when live is fresh, 13 live exit wins, 14 anti-chase skip, 15 Oct 19 EP010 real tape."""
import json, os, sys, tempfile, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_pricer as LP
T0 = "2026-10-21T10:00:%02d+05:30"
def lt(): return LP.LiveTrade(("PX_X", "NIFTY", "09:59"), "NSE_FNO:NIFTY:2026-10-27:23000:PE", 100.0, .30, .60)
fails = []
def ok(c, msg):
    if not c: fails.append(msg)
t = lt(); t.on_quote(105.0, T0 % 1); ok(t.last_bid == 105.0 and t.closed is None, "1 mark at bid")
t = lt(); ok(t.on_quote(70.5, T0 % 1) is None, "2a above stop"); c = t.on_quote(69.9, T0 % 4); ok(c and c["why"] == "STOP" and c["exit_px"] == 69.9, "2 stop at bid")
t = lt(); t.on_quote(131.0, T0 % 1); ok(abs(t.stop - 100.0) < 1e-9, "3a BE armed at +30%"); c = t.on_quote(99.9, T0 % 4); ok(c and c["why"] == "TRAIL", "3 BE trail")
t = lt(); t.on_quote(150.0, T0 % 1); ok(abs(t.stop - 105.0) < 1e-9, "4a hw*0.7"); ok(t.on_quote(106.0, T0 % 4) is None, "4b above trail"); c = t.on_quote(104.9, T0 % 7); ok(c and c["why"] == "TRAIL" and c["exit_px"] == 104.9, "4 hw trail")
t = lt(); c = t.on_quote(160.0, T0 % 1); ok(c and c["why"] == "TARGET", "5 target")
t = LP.LiveTrade(("k",), "i", 100.0, .30, -.40); c = t.on_quote(60.0, T0 % 1); ok(c and c["why"] == "STOP", "6 stop wins when both")
t = lt(); ok(t.on_quote(None, T0 % 1) is None and t.on_quote(0, T0 % 2) is None and t.last_bid is None, "7 no bid ignored")
t = lt(); c = t.on_quote(101.0, "2026-10-21T15:15:00+05:30"); ok(c and c["why"] == "SAFETY_1515", "8 safety close")
t = lt(); t.on_quote(101.0, T0 % 1); ok(not t.stale(T0 % 9) and t.stale("2026-10-21T10:00:15+05:30"), "9 stale after 10 s"); ok(lt().stale(T0 % 1), "9b never quoted = stale")
d = tempfile.mkdtemp(); f = os.path.join(d, "depth_quotes.jsonl")
q = lambda iid, bid, ask, ltp, s: json.dumps({"payload": {"instrument_id": iid, "bid": bid, "ask": ask, "ltp": ltp}, "timestamp": T0 % s}) + "\n"
open(f, "w").write(q("A", 10, 12, 11, 1) + q("B", 5, 6, 5.5, 1) + '{"payload": {"instrument_id": "A", "bi')
tl = LP.DepthTail(f); r1 = tl.read({"A"}); ok(r1 == [("A", 10, T0 % 1)], f"10a tail {r1}")
open(f, "a").write('d": 9}, "timestamp": "%s"}\n' % (T0 % 2)); r2 = tl.read({"A"}); ok(r2 == [("A", 9, T0 % 2)], f"10b partial line completed {r2}")
# runner integration (module imported with a temp REPO-less day; globals patched)
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner")
R.LIVE.clear(); R.LIVE_FILE = __import__("pathlib").Path(d) / "live_exits.json"; R.EXP = "2026-10-27"; R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}
bars = {598: (95, 96), 599: (96, 100), 600: (100, 101), 601: (101, 90), 602: (90, 69), 603: (68, 66)}
R._opt_bars = lambda u, K, s: bars
row = lambda: {"rule_id": "PX_X", "strategy": "X", "underlying": "NIFTY", "qty": 650, "side": "PE", "strike": 23000.0, "signal_time": "09:59",
               "entry_time": "10:00", "entry_px": 100.0, "status": "CLOSED", "exit_time": "10:20", "exit_px": 80.0, "exit_reason": "EXIT", "mark_px": None}
x = R.apply_price_exits(row(), 610, "2026-10-21T10:10:30+05:30")
ok(x["status"] == "CLOSED" and x["exit_reason"] == "STOP" and x["exit_time"] == "10:03" and x["exit_px"] == 68 and x["price_src"] == "1m_fallback", f"11 fallback {x}")
R.LIVE.clear(); x = R.apply_price_exits(row(), 600, "2026-10-21T10:01:05+05:30"); ok(x["status"] == "OPEN" and x["mark_px"] == 101, f"12a open, 1m mark {x}")
k = ("PX_X", "NIFTY", "09:59"); R.LIVE[k].on_quote(92.0, "2026-10-21T10:02:58+05:30")
bars[601] = (101, 69)   # 1m close under stop, but live is fresh -> live decides, row stays OPEN marked at the bid
x = R.apply_price_exits(row(), 601, "2026-10-21T10:03:01+05:30"); ok(x["status"] == "OPEN" and x["mark_px"] == 92.0 and x["price_src"] == "v2_depth", f"12 live fresh {x}")
R.LIVE[k].on_quote(69.5, "2026-10-21T10:03:04+05:30"); x = R.apply_price_exits(row(), 602, "2026-10-21T10:03:05+05:30")
ok(x["status"] == "CLOSED" and x["exit_px"] == 69.5 and x["exit_reason"] == "STOP" and x["exit_src"] == "v2_depth_bid", f"13 live exit wins {x}")
bars2 = {597: (60, 61), 598: (61, 75), 599: (75, 88), 600: (85, 64)}; R._opt_bars = lambda u, K, s: bars2; R.LIVE.clear()
x = R.apply_price_exits(dict(row(), entry_px=85.1), 620, "2026-10-21T10:20:00+05:30"); ok(x["status"] == "SKIPPED_CHASE", f"14 anti-chase {x['status']}")
# 15: Oct 19 EP010 NIFTY 23050 PE on the real (partial) live depth tape: bid-marked live trade from the 10:00 entry
tape = "/workspace/dhan/desk/ops/tape_live/2026-10-19/depth_quotes.jsonl"
if os.path.exists(tape):
    t = LP.LiveTrade(("PX_EP010", "NIFTY", "09:59"), "NSE_FNO:NIFTY:2026-10-19:23050:PE", 85.10, .30, .60)
    for iid, bid, ts in LP.DepthTail(tape).read({t.iid}):
        if ts[11:19] >= "10:00:00" and t.on_quote(bid, ts):
            break
    ok(t.closed and t.closed["why"] == "STOP" and t.closed["exit_px"] <= 85.10 * .70, f"15 Oct19 {t.closed}")
    print("15 Oct19 EP010 live:", t.closed)

# 16: guard_tick end-to-end: open row registered, new depth lines appended, guard closes it at the bid and rewrites OUT
R._opt_bars = lambda u, K, s: {600: (100, 101), 601: (101, 102)}; R.LIVE.clear()
R.OUT = __import__("pathlib").Path(d) / "out.json"; tf = os.path.join(d, "dq2.jsonl"); open(tf, "w").close(); R.TAIL = LP.DepthTail(tf)
r0 = R.apply_price_exits(row(), 601, "2026-10-21T10:02:01+05:30"); R.LAST_ROWS.update(rows=[r0], note="t")
iid = R.LIVE[k].iid
open(tf, "a").write(q(iid, 103.0, 104, 103.5, 30).replace(T0 % 30, "2026-10-21T10:02:30+05:30") + q(iid, 69.0, 70, 69.5, 33).replace(T0 % 33, "2026-10-21T10:02:33+05:30"))
n = R.guard_tick(); js = json.loads(R.OUT.read_text()); x = js["rows"][0]
ok(n == 1 and x["status"] == "CLOSED" and x["exit_px"] == 69.0 and x["exit_reason"] == "STOP" and js["orders"] == "REFUSED", f"16 guard_tick {n} {x.get('status')} {x.get('exit_px')}")

# 17: regression for the 2026-10-19 mid-session deploy bug: quotes from before entry/restart (old tape lines) must never close a trade
t = LP.LiveTrade(("k2",), "i", 72.65, .30, .60, not_before="2026-10-19T11:31:00")
ok(t.on_quote(118.45, "2026-10-19T09:59:11.419+05:30") is None and t.closed is None and t.last_bid is None, "17a old quote ignored")
ok(t.on_quote(80.0, "2026-10-19T11:31:05+05:30") is None and t.last_bid == 80.0, "17b new quote used")
R.LIVE.clear(); R._opt_bars = lambda u, K, s: {600: (100, 101), 601: (101, 102)}
R.apply_price_exits(row(), 601, "2026-10-21T10:02:01+05:30"); ok(R.LIVE[k].not_before == "2026-10-21T10:02:00", f"17c runner sets not_before {R.LIVE[k].not_before}")
open(tf, "a").write(q(iid, 200.0, 201, 200, 1).replace(T0 % 1, "2026-10-21T09:30:00+05:30")); t3 = LP.DepthTail(tf, start_at_end=True); ok(t3.read() == [], "17d start_at_end skips old lines")

# 18: a live_exits.json written by the pre-fix build (no not_before) is ignored on load; a fixed-build entry is kept
R.LIVE.clear(); R.LIVE_FILE.write_text(json.dumps([{"key": ["PX_VWAP_CONT", "NIFTY", "11:10"], "iid": "x", "entry": 72.65, "S": .3, "T": .6, "hw": 110.15, "last_bid": 118.45,
    "last_ts": "2026-10-19T09:59:11+05:30", "closed": {"exit_px": 118.45, "exit_ts": "2026-10-19T09:59:11+05:30", "why": "TARGET"}},
    {"not_before": "2026-10-19T11:40:00", "key": ["PX_A", "NIFTY", "11:20"], "iid": "y", "entry": 50, "S": .3, "T": .6, "hw": 50, "last_bid": None, "last_ts": None, "closed": None}]))
R._live_load(); ok(list(R.LIVE) == [("PX_A", "NIFTY", "11:20")], f"18 stale live file ignored {list(R.LIVE)}")

# 19: exact Oct 19 11:39 IST case: two R07 SKIPPED_CHASE rows + live-priced SENSEX VWAP_CONT OPEN. OUT "rows" must hold only OPEN/CLOSED,
# with mark_time HH:MM so desk_ml._trade_row parses it (old desk code books every non-CLOSED row in "rows")
sk = lambda u, K: dict(row(), rule_id="PX_R07", underlying=u, strike=K, signal_time="11:38", entry_time="11:39", status="SKIPPED_CHASE", mark_px=70.85)
vw = dict(row(), rule_id="PX_VWAP_CONT", underlying="SENSEX", strike=74800.0, signal_time="11:12", entry_time="11:13", entry_px=635.1, status="OPEN",
          mark_px=786.9, mark_time="11:48", mark_ts="2026-10-19T11:48:35+05:30", stop_px=635.1, target_px=1016.16)
R.write([sk("NIFTY", 23000.0), sk("SENSEX", 74500.0), vw], "t"); js = json.loads(R.OUT.read_text())
ok([r["rule_id"] for r in js["rows"]] == ["PX_VWAP_CONT"] and len(js["not_booked"]) == 2, f"19a rows {[r['rule_id'] for r in js['rows']]}")
ok(all(len(str(r.get("mark_time") or "")) <= 5 for r in js["rows"]), "19b mark_time HH:MM")
R.LIVE.clear(); R._opt_bars = lambda u, K, s: {600: (100, 101), 601: (101, 102)}
R.apply_price_exits(row(), 601, "2026-10-21T10:02:01+05:30"); R.LIVE[k].on_quote(103.0, "2026-10-21T10:02:30.500+05:30")
x = R.apply_price_exits(row(), 602, "2026-10-21T10:02:31+05:30"); ok(x["mark_time"] == "10:02" and x["mark_px"] == 103.0, f"19c live mark_time {x.get('mark_time')}")
print("\n".join(fails) or "test_live_pricer: ALL PASS"); sys.exit(1 if fails else 0)
