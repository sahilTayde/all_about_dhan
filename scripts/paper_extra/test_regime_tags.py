"""Regime tags / narrow-open shadow (logging only). Box/Mac, no network, synthetic data. Run: python3 test_regime_tags.py
1 labels on a hand-built day, 2 missing VIX -> null + reason, no crash, 3 missing/malformed index json, 4 broken VIX rows, 5 runner tag_rows
never changes any other field, 6 shadow log: one line per closed trade, half qty, skip 0, idempotent across restarts, 7 regime_counts in
risk_minutes, 8 runner survives regime_tags import failure, 9 rows with no signal_time."""
import json, os, sys, tempfile, importlib, pathlib, copy
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regime_tags as RG
IST = timezone(timedelta(hours=5, minutes=30)); fails = []
def ok(c, m):
    if not c: fails.append(m)
def mkday(day, o, step, n=376, wig=0.0, rng=None):
    out = {}; p = o
    for k in range(n):
        c = p + step + (wig if k % 2 else -wig); hi = max(p, c) + (rng or 1); lo = min(p, c) - (rng or 1); out[k] = (p, hi, lo, c); p = c
    return out
days = [f"2026-09-{d:02d}" for d in range(1, 31)] + ["2026-10-01"]
BY = {d: mkday(d, 25000, 0.5, rng=10) for d in days[:-1]}            # prior days: trend days, OR15 range ~ 7.5+20
BY["2026-10-01"] = mkday("2026-10-01", 25400, 0.0, wig=0.5, rng=1)   # gap up 0.84% (prior close 25188), tiny range -> OR_NARROW, chop
VIX = [[f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", 10 + i * 0.01] for i in range(300)] + [["2026-09-30", 50.0]]
ctx = RG.day_context(BY, "2026-10-01", VIX, True, "2026-09-30")
g = RG.tag(ctx, 600, "CE")
ok(g["gap_bucket"] == "GAP_UP" and g["or15"] == "OR_NARROW" and g["trend_chop"] == "CHOP" and g["vix_bucket"] == "VOL_HI" and g["time_bucket"] == "T2_1000_1130"
   and g["prior_day_type"] == "PD_TREND" and g["expiry_day"] is True and g["side_vs_move"] == "WITH" and not g["missing"], f"1 labels {g}")
ok(RG.tag(ctx, 562, "PE")["or15"] == "OR_NOTYET" and RG.narrow_shadow(RG.tag(ctx, 562, "PE"))["would_skip"] is False, "1b before 09:29")
sh = RG.narrow_shadow(g); ok(sh == {"would_skip": True, "would_halve": True, "rule": "opening range 15m < 20d median", "or15": "OR_NARROW", "basis": "or15 known"}, f"1c {sh}")
# 2 missing VIX
for v in ([], None, [["2026-09-30", 15.0]]):
    c2 = RG.day_context(BY, "2026-10-01", v, True); g2 = RG.tag_safe(c2, 600, "CE")
    ok(g2.get("vix_bucket") is None and "vix" in g2["missing"] and g2.get("cell") is None and g2.get("gap_bucket") == "GAP_UP" and "error" not in g2, f"2 missing VIX {v and len(v)} {g2.get('missing')}")
# 3 missing / malformed index json
ok(RG.days_from_dhan({}) == {} and RG.days_from_dhan({"timestamp": [1, "x"], "open": [1]}) == {}, "3a malformed json")
c3 = RG.day_context({}, "2026-10-01", VIX, None); g3 = RG.tag_safe(c3, 600, "CE")
ok("error" not in g3 and g3["trend_chop"] is None and g3["side_vs_move"] is None and g3["gap_bucket"] is None and g3["expiry_day"] is None
   and {"prev", "or15_med", "expiry_day"} <= set(g3["missing"]), f"3b no index {g3}")
# 4 broken VIX rows
c4 = RG.day_context(BY, "2026-10-01", [["2026-09-30", "abc"], [None]], True); ok("vix" in c4["missing"], f"4 broken VIX {c4['missing']}")
ok("error" in RG.tag_safe(None, 600, "CE"), "4b tag_safe never raises")
# 5-8 runner integration
os.environ["PX_DAY"] = "2026-10-01"
R = importlib.import_module("runner")
d = pathlib.Path(tempfile.mkdtemp()); R.LIVE_RUN = d / "run"; R.LIVE_RUN.mkdir(); R.OUT = d / "out.json"; R.SHADOW_FILE = d / "shadow.jsonl"; R.VIX_HIST = d / "no_vix.json"
R.EXP = "2026-10-01"; R.EXPS = {"NIFTY": "2026-10-01", "SENSEX": "2026-10-02"}
def dhan(by):
    ts, o, h, l, c = [], [], [], [], []
    for day in sorted(by):
        for k in sorted(by[day]):
            t = datetime.fromisoformat(f"{day}T{(555 + k) // 60:02d}:{(555 + k) % 60:02d}:00+05:30"); ts.append(int(t.timestamp()))
            a = by[day][k]; o.append(a[0]); h.append(a[1]); l.append(a[2]); c.append(a[3])
    return dict(open=o, high=h, low=l, close=c, volume=[0] * len(ts), timestamp=ts)
(R.LIVE_RUN / "IDX_NIFTY.json").write_text(json.dumps(dhan(BY)))         # SENSEX index file missing on purpose; no VIX at all
base = dict(strategy="X", qty=650, side="CE", strike=25000.0, entry_src="t", exit_src=None, stop_px=1.0, target_px=2.0, exit_reason=None)
rows = [dict(base, rule_id="PX_A", underlying="NIFTY", signal_time="10:00", entry_time="10:01", entry_px=100.0, status="CLOSED", exit_px=130.0, exit_time="10:30", exit_reason="TARGET"),
        dict(base, rule_id="PX_B", underlying="SENSEX", qty=200, signal_time="10:05", entry_time="10:06", entry_px=300.0, status="OPEN", exit_px=None, exit_time=None),
        dict(base, rule_id="PX_C", underlying="NIFTY", signal_time="10:10", entry_time="10:11", entry_px=90.0, status="SKIPPED_CAP"),
        dict(base, rule_id="PX_D", underlying="NIFTY", signal_time=None, entry_time=None, entry_px=90.0, status="PRE_START")]
before = copy.deepcopy(rows); st = (json.dumps(sorted(map(str, R.LIVE))), str(R.CAP), str(R.PREM), str(R.START))
txt = R.tag_rows(rows)
ok([{k: v for k, v in r.items() if k not in ("regime", "shadow_narrow_open")} for r in rows] == before, "5 only logging keys added")
ok(st == (json.dumps(sorted(map(str, R.LIVE))), str(R.CAP), str(R.PREM), str(R.START)), "5b runner state untouched")
a, b, c_, dd = (r["regime"] for r in rows)
ok(a.get("or15") == "OR_NARROW" and a.get("vix_bucket") is None and "vix" in a["missing"] and a.get("expiry_day") is True, f"5c NIFTY row, no VIX {a}")
ok(b.get("trend_chop") is None and "index" in b["missing"] and b.get("expiry_day") is False, f"5d SENSEX row, no index {b.get('missing')}")
ok(c_.get("gap_bucket") == "GAP_UP" and "error" in dd, f"5e skipped row tagged; no-signal row error {dd}")
ok("errors" in txt, f"5f summary {txt}")
R.write(rows, "t"); t1 = R.shadow_log(rows); t2 = R.shadow_log(rows)
L = [json.loads(x) for x in R.SHADOW_FILE.read_text().splitlines()]
ok(len(L) == 1 and L[0]["key"] == ["PX_A", "NIFTY", "10:00"] and L[0]["actual"]["gross_inr"] == 19500.0 and L[0]["under_half"]["qty"] == 325
   and L[0]["under_half"]["gross_inr"] == 9750.0 and L[0]["under_skip"]["gross_inr"] == 0.0 and L[0]["if_rule_applied"]["qty"] == 0, f"6 shadow {L}")
R.SHADOW_DONE.clear(); R.shadow_log(rows); ok(len(R.SHADOW_FILE.read_text().splitlines()) == 1, "6b idempotent across restart")
(d / "rr").mkdir(); R.REPO = d / "rr"; (R.REPO / "data/recon/research_rules").mkdir(parents=True)
(R.REPO / "data/recon/research_rules/2026-10-01.json").write_text(json.dumps({"open": [], "risk": {}}))
R.log_risk(); rec = json.loads((R.OUT.parent / "risk_minutes_2026-10-01.jsonl").read_text().splitlines()[-1])
rc = rec.get("regime_counts") or {}
ok(rc.get("booked", {}).get("or15") == {"OR_NARROW": 1, "None": 1} and rc.get("not_booked", {}).get("narrow_would_skip") == 1, f"7 regime_counts {rc}")
R.RG, R._RG_ERR = None, "ImportError: x"; ok(R.tag_rows(rows).startswith("regime OFF"), "8 no module -> OFF, no crash")
print("test_regime_tags:", "ALL PASS" if not fails else f"FAIL {fails}"); sys.exit(1 if fails else 0)
