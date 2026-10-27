"""2026-10-22 two-week review bug 2 + fill check: stops fire on the BID and book the BID that triggered them (not the stop level, not LTP).
Run: python3 test_stop_at_bid_1022.py. Real V2 depth tape (desk/ops/tape_live/2026-10-22/depth_quotes.jsonl, read-only, streamed with rg
so memory stays small); real-tape parts skip if the tape is absent.
 A Oct 22 PX_EP010 SENSEX 73500 PE, entry 490.15 (stop 343.105): booked STOP 342.3 at 09:48. The depth tape has bid 342.3 at 09:48:35.470,
   the first bid <= stop. (The review's 324.2 came from a 5-second snapshot replay with a different entry, 481.2 -> stop 336.84.)
 B Oct 22 PX_EP018 NIFTY 22650 PE, entry 145.9 (stop 102.13): booked STOP 101.7 at 10:36. Depth tape bid 101.7 at 10:36:01.572 (LTP 101.6
   on that same quote); the 5-second snapshots missed that tick, which is why the fill check saw a 101.80 low.
 C synthetic: LTP through the stop with the bid above it must NOT fire; bid through the stop fires at that bid."""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_pricer as LP
fails = []
def ok(c, m):
    if not c: fails.append(m)
TAPE = "/workspace/dhan/desk/ops/tape_live/2026-10-22/depth_quotes.jsonl"
def quotes(iid, t0, t1):
    p = subprocess.run(["rg", "-F", f'"instrument_id":"{iid}"', TAPE], capture_output=True, text=True)
    out = []
    for l in p.stdout.splitlines():
        j = json.loads(l); q = j["payload"]; ts = q.get("exchange_ts") or j["timestamp"]
        if not q.get("repeat") and t0 <= ts[11:19] <= t1:
            out.append((ts, q.get("bid"), q.get("ltp")))
    return sorted(out)
def run(iid, key, entry, t0, t1, nb):
    t = LP.LiveTrade(key, iid, entry, .30, .60, not_before=nb)
    for ts, bid, ltp in quotes(iid, t0, t1):
        if t.on_quote(bid, ts):
            return t, ltp
    return t, None
if os.path.exists(TAPE):
    t, ltp = run("BSE_FNO:SENSEX:2026-10-22:73500:PE", ("PX_EP010", "SENSEX", "09:19"), 490.15, "09:20:00", "10:00:00", "2026-10-22T09:20:00")
    print("A", t.closed)
    ok(t.closed and t.closed["why"] == "STOP" and t.closed["exit_px"] == 342.3 and t.closed["exit_ts"][11:23] == "09:48:35.470", f"A EP010 {t.closed}")
    ok(t.closed and t.closed["exit_px"] <= 490.15 * .70, "A2 booked at a bid at/below the stop, not the stop level")
    t, ltp = run("NSE_FNO:NIFTY:2026-10-27:22650:PE", ("PX_EP018", "NIFTY", "10:14"), 145.9, "10:15:00", "10:40:00", "2026-10-22T10:15:00")
    print("B", t.closed, "ltp on that quote", ltp)
    ok(t.closed and t.closed["why"] == "STOP" and t.closed["exit_px"] == 101.7 and t.closed["exit_ts"][11:23] == "10:36:01.572", f"B EP018 {t.closed}")
    ok(ltp is not None and ltp != t.closed["exit_px"], "B2 booked price is the bid, not the LTP")
else:
    print("real-tape parts SKIPPED (no tape)")
import tempfile; f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
q = lambda bid, ltp, s: json.dumps({"payload": {"instrument_id": "X", "bid": bid, "ask": bid + .3, "ltp": ltp}, "timestamp": f"2026-10-22T10:00:{s:02d}+05:30"}) + "\n"
f.write(q(72.0, 69.0, 1) + q(71.0, 68.5, 2) + q(69.8, 70.2, 3)); f.close()
t = LP.LiveTrade(("C",), "X", 100.0, .30, .60); hits = [t.on_quote(b, ts) for _, b, ts in LP.DepthTail(f.name).read({"X"})]
ok(hits[0] is None and hits[1] is None, "C1 LTP under stop, bid above -> no fire")
ok(hits[2] and hits[2]["exit_px"] == 69.8 and hits[2]["why"] == "STOP", f"C2 fires on bid at the bid {hits[2]}")
os.unlink(f.name)
print("\n".join(fails) or "test_stop_at_bid_1022: ALL PASS"); sys.exit(1 if fails else 0)
