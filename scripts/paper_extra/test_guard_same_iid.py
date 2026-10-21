"""2026-10-21 v3: guard_tick feeds every open live trade on a contract, not only the last one registered (Oct 21 EP010 SENSEX 821.1 case)."""
import os, sys, pathlib, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["PX_DAY"] = "2026-10-21"
R = importlib.import_module("runner"); LP = R.LP
d = pathlib.Path(R.STATE); R.OUT = d / "out.json"; R.LIVE_FILE = d / "live.json"; R.SO = None
IID = "BSE_FNO:SENSEX:2026-10-22:74900:PE"
R.LIVE.clear()
ep = LP.LiveTrade(("PX_EP010", "SENSEX", "09:44"), IID, 481.4, .30, .60, not_before="2026-10-21T09:47:00")
mp = LP.LiveTrade(("PX_MINE_PE", "SENSEX", "09:45"), IID, 507.45, .30, .60, not_before="2026-10-21T09:48:00")
R.LIVE[ep.key] = ep; R.LIVE[mp.key] = mp; R.LAST_ROWS.update(rows=[], note="t")
class Tape:
    def __init__(self, q): self.q = q
    def read(self, want): out, self.q = [(i, b, t) for i, b, t in self.q if i in want], []; return out
R.TAIL = Tape([(IID, 760.0, "2026-10-21T10:05:30.000+05:30"), (IID, 771.5, "2026-10-21T10:05:39.265+05:30"),
               (IID, 816.7, "2026-10-21T10:08:00.951+05:30"), (IID, 821.1, "2026-10-21T10:08:03.184+05:30")])
n = R.guard_tick()
fails = []
if not (ep.closed and ep.closed["exit_px"] == 771.5 and ep.closed["why"] == "TARGET"): fails.append(f"EP010 closes at first bid >= 770.24: {ep.closed}")
if not (mp.closed and mp.closed["exit_px"] == 816.7): fails.append(f"MINE_PE closes at 816.7: {mp.closed}")
if n != 2: fails.append(f"2 closes {n}")
print("FAILS:", fails) if fails else print("ALL PASS test_guard_same_iid (3 checks)")
sys.exit(1 if fails else 0)
