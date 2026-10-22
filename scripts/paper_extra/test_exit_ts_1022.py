"""2026-10-22 fill check (a): paper_extra rows keep the exit time to the SECOND in exit_ts (exit_time stays HH:MM for the desk parser),
and desk_ml.research_rules.paper_extra_rows carries exit_ts through. Run: python3 test_exit_ts_1022.py
Real case: Oct 22 PX_EP010 SENSEX 73500 PE, entry 490.15, live stop at bid 342.3 at 09:48:35.470 IST (V2 depth tape, streamed with rg)."""
import os, sys, json, subprocess, tempfile, importlib
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "packages", "desk-ml", "src"))
os.environ["PX_DAY"] = "2026-10-22"
import live_pricer as LP
R = importlib.import_module("runner")
fails = []
def ok(c, m):
    if not c: fails.append(m)
d = Path(tempfile.mkdtemp()); __import__("atexit").register(__import__("shutil").rmtree, d, True)
R.LIVE.clear(); R.LIVE_FILE = d / "live_exits.json"; R.ENTRY_FILE = d / "entry_fill.json"; R.ENTRY.clear(); R.EXPS = {"NIFTY": "2026-10-27", "SENSEX": "2026-10-22"}; R.EXP = "2026-10-27"
TAPE = "/workspace/dhan/desk/ops/tape_live/2026-10-22/depth_quotes.jsonl"
IID = "BSE_FNO:SENSEX:2026-10-22:73500:PE"
row = lambda: {"rule_id": "PX_EP010", "strategy": "EP010", "underlying": "SENSEX", "qty": 200, "side": "PE", "strike": 73500.0, "signal_time": "09:19",
               "entry_time": "09:20", "entry_px": 490.15, "entry_px_1m_open": 490.15, "status": "OPEN", "exit_time": None, "exit_px": None, "exit_reason": None, "mark_px": None}
R._opt_bars = lambda u, K, s: {560: (490.0, 489.0)}
k = ("PX_EP010", "SENSEX", "09:19")
R.apply_price_exits(row(), 560, "2026-10-22T09:20:30+05:30")
ok(k in R.LIVE and R.LIVE[k].iid == IID, "0 live trade registered")
if os.path.exists(TAPE):
    p = subprocess.run(["rg", "-F", f'"instrument_id":"{IID}"', TAPE], capture_output=True, text=True)
    for l in p.stdout.splitlines():
        j = json.loads(l); q = j["payload"]; ts = q.get("exchange_ts") or j["timestamp"]
        if not q.get("repeat") and "09:21:00" <= ts[11:19] <= "10:00:00" and R.LIVE[k].on_quote(q.get("bid"), ts):
            break
else:
    R.LIVE[k].on_quote(342.3, "2026-10-22T09:48:35.470+05:30"); print("tape absent: synthetic quote with the real values")
x = R.apply_price_exits(row(), 589, "2026-10-22T09:49:00+05:30")
print("live row:", {kk: x.get(kk) for kk in ("status", "exit_px", "exit_time", "exit_ts", "exit_reason")})
ok(x["status"] == "CLOSED" and x["exit_px"] == 342.3 and x["exit_time"] == "09:48" and x["exit_ts"] == "2026-10-22T09:48:35.470+05:30", f"1 live exit_ts {x}")
# 1m fallback close: exit_ts is that fill minute's open, :00 seconds
R.LIVE.clear(); R._opt_bars = lambda u, K, s: {600: (100, 101), 601: (101, 90), 602: (90, 69), 603: (68, 66)}
y = R.apply_price_exits(dict(row(), underlying="NIFTY", strike=23000.0, entry_time="10:00", entry_px=100.0, entry_px_1m_open=100.0), 615, "2026-10-22T10:15:30+05:30")
ok(y["status"] == "CLOSED" and y["exit_ts"] == "2026-10-22T10:03:00+05:30", f"2 fallback exit_ts {y.get('exit_ts')}")
# desk reader carries exit_ts
from desk_ml import research_rules as rr
root = d / "root"; f = root / rr.PAPER_EXTRA_REL / "2026-10-22.json"; f.parent.mkdir(parents=True)
x.update(strategy="EP010"); f.write_text(json.dumps({"day": "2026-10-22", "orders": "REFUSED", "rows": [x]}))
o, c = rr.paper_extra_rows(root, "2026-10-22")
ok(len(c) == 1 and c[0].get("exit_ts") == "2026-10-22T09:48:35.470+05:30", f"3 desk row exit_ts {[r.get('exit_ts') for r in c]}")
print("\n".join(fails) or "test_exit_ts_1022: ALL PASS"); sys.exit(1 if fails else 0)
