"""2026-10-21 desk book entry-at-ask: research_rules.paper_extra_rows entry pricing. Box test, no broker."""
import atexit, json, os, pathlib, shutil, sys, tempfile
os.environ["DESK_ENTRY_ASK_FROM"] = "2026-10-21"
sys.path.insert(0, os.environ.get("DESKML_SRC", str(pathlib.Path(__file__).resolve().parents[2] / "packages/desk-ml/src")))
from desk_ml import research_rules as RR
ok = 0
def chk(c, m):
    global ok
    assert c, m; ok += 1
def base(**k):
    r = {"rule_id": "EP010", "underlying": "NIFTY", "signal_time": "10:00", "entry_time": "10:01", "exit_time": "10:30",
         "status": "CLOSED", "strategy": "s", "side": "PE", "strike": 25000, "entry_px": 100.0, "exit_px": 120.0}
    r.update(k); return r
def rows(day, xs):
    d = pathlib.Path(tempfile.mkdtemp()); atexit.register(shutil.rmtree, d, True); p = d / RR.PAPER_EXTRA_REL; p.mkdir(parents=True)
    (p / f"{day}.json").write_text(json.dumps({"day": day, "orders": "REFUSED", "rows": xs}))
    return RR.paper_extra_rows(d, day)[1]
r = rows("2026-10-21", [base()])[0]                      # old-format row on/after cut-over: open + half spread
chk(r["entry"] == 100.5, "half spread added")
chk(r["entry_src"] == "1m_open+half_spread", r["entry_src"]); chk(r["entry_px_1m_open"] == 100.0, "open kept")
r = rows("2026-10-21", [base(underlying="SENSEX")])[0]
chk(r["entry_src"] == "1m_open+half_spread", "sensex label")
r = rows("2026-10-21", [base(entry_px=101.2, entry_px_1m_open=100.0, entry_src="v2_ask")])[0]   # fixed runner row: untouched
chk(r["entry_src"] == "v2_ask" and r["entry_px_1m_open"] == 100.0, "ask row kept")
r = rows("2026-10-20", [base()])[0]                      # history before cut-over: unchanged
chk(r["entry_src"] == "dhan_api_1m" and "entry_px_1m_open" not in r, "history unchanged")
a = rows("2026-10-21", [base()])[0]; b = rows("2026-10-20", [base()])[0]
pa, pb = RR.desk_entry_px(base(), "NIFTY", "2026-10-21")[0], RR.desk_entry_px(base(), "NIFTY", "2026-10-20")[0]
chk(abs(pa - 100.50) < 1e-9 and pb == 100.0, (pa, pb))
for k in ("realized_pnl_inr",):
    if k in a and a[k] is not None:
        chk(a[k] < b[k], f"{k} lower with ask entry"); break
print(f"ALL PASS test_desk_entry_ask ({ok} checks)")
