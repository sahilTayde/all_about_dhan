"""Review test: mid-session restart must not back-fill pre-start entries, must freeze old CLOSED rows, and must not retro-exit carried OPEN rows."""
import csv, os, sys, json, pathlib, tempfile, importlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
day = "2026-10-14"
if not pathlib.Path(f"/workspace/sensex_px/rp/new/{day}").is_dir(): print("test_restart_guard: SKIP (box replay data not on this machine)"); sys.exit(0)
os.environ["PX_DAY"] = day; R = importlib.import_module("runner"); D = pathlib.Path(f"/workspace/sensex_px/rp/new/{day}")
R.LIVE_RUN = D / "run"; R.EXP = "2026-10-19"; R.EXPS = {"NIFTY": "2026-10-19", "SENSEX": "2026-10-15"}; R.DAY = day
tmp = pathlib.Path(tempfile.mkdtemp()); R.LIVE_FILE = tmp / "l.json"; R.OUT = tmp / "out.json"; R.START_FILE = tmp / "s.json"
rows = R.rows_from(list(csv.DictReader(open(D / "v_NIFTY_base/score_latest.csv"))), "NIFTY")
hm = lambda s: int(s[:2]) * 60 + int(s[3:5]); start = 12 * 60
pre = [r for r in rows if hm(r["entry_time"]) < start]; post = [r for r in rows if hm(r["entry_time"]) >= start]
assert len(pre) >= 3 and post, (len(pre), len(post))
old_closed = dict(pre[0], status="CLOSED", exit_time="10:30", exit_px=123.45, exit_reason="EXIT")
old_open = dict(pre[1], status="OPEN")
R.OUT.write_text(json.dumps({"day": day, "rows": [old_closed, old_open]}))
R.START_FILE.write_text(json.dumps({"start_m": start})); R._start_load(start - 1)
out = [R.apply_price_exits(dict(r), 931, f"{day}T15:31:00+05:30") for r in rows]
by = {(r["rule_id"], r["signal_time"]): r for r in out}
a = by[(pre[0]["rule_id"], pre[0]["signal_time"])]; assert a["exit_px"] == 123.45 and a["status"] == "CLOSED", a
b = by[(pre[1]["rule_id"], pre[1]["signal_time"])]; assert b["status"] != "PRE_START"
if b["status"] == "CLOSED": assert hm(b["exit_time"]) >= start, b["exit_time"]
for r in pre[2:]: assert by[(r["rule_id"], r["signal_time"])]["status"] == "PRE_START"
for r in post: assert by[(r["rule_id"], r["signal_time"])]["status"] in ("OPEN", "CLOSED", "SKIPPED_CHASE")
# first-ever start mid-session with no START_FILE pins now+1
R.START_FILE.unlink(); R.START.update(m=None, frozen={}, carried=set()); R.OUT.unlink(); R._start_load(600); assert R.START["m"] == 601
print(f"test_restart_guard: ALL PASS (pre {len(pre)}, post {len(post)})")
