"""2026-10-22 two-week review bug 1: paper_extra exits are PRICE-ONLY (no SAFETY_1515 time close). Run: python3 test_price_only_1022.py
Real tape case: Oct 21 PX_R07 NIFTY 22800 PE, entry 159.45 (11:50 IST), was closed by SAFETY_1515 at 15:15:00 IST at 191.4.
Uses the review's 5-second V2 snapshot tape (desk/verify/2026-10-22_twoweek_review/tape_2026-10-21.pkl, read-only); skips if absent."""
import os, sys, pickle, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PX_DAY", "2026-10-21")
import live_pricer as LP
R = importlib.import_module("runner")
fails = []
def ok(c, m):
    if not c: fails.append(m)
PKL = "/workspace/dhan/desk/verify/2026-10-22_twoweek_review/tape_2026-10-21.pkl"
IID = "NSE_FNO:NIFTY:%s:22800:PE"
E0 = 159.45
if not os.path.exists(PKL):
    print("test_price_only_1022: SKIP (no tape)"); sys.exit(0)
T = pickle.load(open(PKL, "rb"))
k = sorted(x for x in T if x.startswith("NSE_FNO:NIFTY:") and x.endswith(":22800:PE"))[0]
v = T[k]; hm = lambda s: "%02d:%02d:%02d" % (s // 3600, s % 3600 // 60, int(s % 60))
# (1) live bid path: replay every real bid from 11:50 to 15:29 IST; nothing may close the trade on time, and any close is a price exit
t = LP.LiveTrade(("PX_R07", "NIFTY", "11:49"), k, E0, .30, .60)
for s, b, a, l in v:
    if 11 * 3600 + 50 * 60 <= s <= 15 * 3600 + 29 * 60 and t.on_quote(b, f"2026-10-21T{hm(s)}+05:30"):
        break
ok(t.closed is None or t.closed["why"] in ("STOP", "TRAIL", "TARGET"), f"1 live close is price-only {t.closed}")
ok(not (t.closed and t.closed["exit_ts"][11:16] == "15:15" and t.closed["why"] == "SAFETY_1515"), "1b no SAFETY_1515")
print("live bid path:", t.closed or f"still OPEN at 15:29, last bid {t.last_bid} {t.last_ts}")
# (2) 1-minute fallback path (open, close from the tape LTP) asked at 15:29: no SAFETY_1515, OPEN unless a price level was hit
ob = {}
for s, b, a, l in v:
    px = l or b
    if px:
        m = int(s // 60); o, c = ob.get(m, (px, px)); ob[m] = (o, px)
r = R.price_exit_path(ob, 11 * 60 + 50, E0, 15 * 60 + 29)
ok(r.get("why") != "SAFETY_1515" and (r["status"] == "OPEN" or r["why"] in ("STOP", "TRAIL", "TARGET")), f"2 1m path price-only {r}")
print("1m path:", r)
# (3) synthetic: flat trade past 15:15 stays OPEN in both paths (the desk FLATTEN_1516 square-off closes the ticket, not paper_extra)
flat = {m: (100.0, 100.0) for m in range(600, 930)}
ok(R.price_exit_path(flat, 600, 100.0, 929)["status"] == "OPEN", "3a 1m flat past 15:15 stays OPEN")
t = LP.LiveTrade(("k",), "i", 100.0, .30, .60); ok(t.on_quote(100.0, "2026-10-21T15:20:00+05:30") is None, "3b live flat past 15:15 stays OPEN")
ok("safety_m" not in R.PRICE_EXIT, "3c no safety_m in PRICE_EXIT")
print("\n".join(fails) or "test_price_only_1022: ALL PASS"); sys.exit(1 if fails else 0)
