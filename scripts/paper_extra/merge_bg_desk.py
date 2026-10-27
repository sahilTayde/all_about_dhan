"""Display-only: today's desk-strategy rows (10 PX + R01) -> background test file, section `desk_strategies_today`.
Never desk P&L: count_in_total False on every row; the box's own `trades`/`summary` are left untouched.
PX prices = score_pass (real 1m option bars, completed minutes, entry = next-minute open, STOP/TARGET/SIGNAL exits = next-minute open).
R01 prices = the desk's own paper fill (v2 tape) because SENSEX options are not in the 1m fetch. Status from the desk journal.
Usage: merge_bg_desk.py [once|loop]   (loop: every 5 min until 15:31 IST)"""
import csv, json, os, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
IST = timezone(timedelta(hours=5, minutes=30))
REPO = Path(__file__).resolve().parents[2]
DAY = os.environ.get("PX_DAY") or datetime.now(IST).strftime("%Y-%m-%d")
SCORE = Path.home() / "paper_extra_rt" / "live" / "score_latest.csv"
JOURNAL = REPO / "data" / "recon" / "research_rules" / f"{DAY}.json"
BG = REPO / "data" / "research" / "background_test" / f"{DAY}.json"
sys.path.insert(0, str(Path(__file__).parent)); from runner import STRATS  # noqa: E402
ON_FROM = {"PX": "12:06", "R01": "11:46"}
GUARD = {"RISK_DAY_STOP": "BLOCKED_RISK_DAY_STOP", "BLOCKED_OPPOSITE_SIDE": "BLOCKED_OPPOSITE"}
STD = {"EXIT": "RULE_EXIT", "SIGNAL": "RULE_EXIT", "REVERSE": "RULE_EXIT", "EOD": "TIME", "open": "OPEN"}
f2 = lambda v: None if v in (None, "") else round(float(v), 2)


def journal_status(j):
    st = {}
    for key, lab in (("closed", "DESK"), ("open", "DESK")):
        for r in j.get(key) or []:
            st[(r["rule_id"], r["underlying"], r["side"], r.get("entry_min"))] = (lab, r)
    for key in ("risk_blocked", "guard_blocked"):
        for r in j.get(key) or []:
            st.setdefault((r["rule_id"], r["underlying"], r["side"], r.get("entry_min")), (GUARD.get(r.get("guard"), "BLOCKED_" + str(r.get("guard"))), r))
    return st


def build():
    j = json.loads(JOURNAL.read_text()) if JOURNAL.is_file() else {}
    st = journal_status(j); rows = []; seen = set()
    for r in csv.DictReader(open(SCORE)):
        rid = STRATS.get(r["strategy"])
        if not rid or r["signalled"] != "Y" or r["status"] not in ("OPEN", "CLOSED"): continue
        key = (rid, r["side"], r["signal_time"])
        if key in seen: continue
        seen.add(key)
        hit = st.get((rid, "NIFTY", r["side"], r["entry_time"]))
        status = hit[0] if hit else ("TEST_ONLY_PRE_" + ON_FROM["PX"].replace(":", "") if r["entry_time"] < ON_FROM["PX"] else "NOT_BOOKED")
        closed = r["status"] == "CLOSED"
        rows.append(dict(strategy=rid[3:], rule_id=rid, underlying="NIFTY", side=r["side"], strike=f2(r["strike"]), signal_ist=r["signal_time"],
                         entry_ist=r["entry_time"], exit_ist=r["exit_time"] if closed else None, entry_px=f2(r["entry_px"]),
                         exit_px=f2(r["exit_px"]) if closed else None, mark_px=f2(r.get("mark_px")), status="CLOSED" if closed else "OPEN",
                         desk_status=status, exit_reason_std=STD.get(r["exit_reason"], r["exit_reason"]) if closed else "OPEN",
                         net_inr_1x=f2(r["pnl_1x"]) if closed else None, net_inr_1_5x=f2(r["pnl_1_5x"]) if closed else None,
                         qty=650, stop_px=None, target_px=None, stop_target_basis="Rule exits on NIFTY index levels / time / own signal; no premium stop or target",
                         price_source="real 1m option bars (Dhan), next-minute-open fills", verified="PAPER_EXTRA", count_in_total=False))
    for r in (j.get("closed") or []) + (j.get("open") or []) + (j.get("risk_blocked") or []) + (j.get("guard_blocked") or []):
        if not str(r["rule_id"]).startswith("R01"): continue
        key = (r["rule_id"], r["underlying"], r["side"], r.get("sig_min"))
        if key in seen: continue
        seen.add(key)
        lab = st.get((r["rule_id"], r["underlying"], r["side"], r.get("entry_min")), ("?",))[0]
        if r.get("sig_min") and r["sig_min"] < ON_FROM["R01"]: lab = "TEST_ONLY_PRE_1146"
        closed = r.get("status") == "CLOSED"; ch = float(r.get("charges_inr") or 0)
        rows.append(dict(strategy="R01", rule_id=r["rule_id"], underlying=r["underlying"], side=r["side"], strike=f2(r.get("held_strike")),
                         signal_ist=r.get("sig_min"), entry_ist=r.get("entry_min"), exit_ist=r.get("exit_min") if closed else None,
                         entry_px=f2(r.get("entry")), exit_px=f2(r.get("exit")) if closed else None, mark_px=f2(r.get("last_ltp")),
                         status="CLOSED" if closed else "OPEN", desk_status=lab, exit_reason_std=r.get("exit_reason") if closed else "OPEN",
                         net_inr_1x=round(float(r["gross_pnl_inr"]) - ch / 1.5, 2) if closed else None,
                         net_inr_1_5x=f2(r.get("realized_pnl_inr")) if closed else None, qty=r.get("qty"), stop_px=None, target_px=None,
                         stop_target_basis="R01 has no stop or target; time exit at signal + 21 min", planned_exit_ist=r.get("spec_exit_min"),
                         price_source="desk paper fill (v2 tape quotes)", verified="PAPER_EXTRA", count_in_total=False))
    rows.sort(key=lambda x: (x["entry_ist"] or "", x["strategy"]))
    sub = {}
    for x in rows:
        s = sub.setdefault(x["strategy"], dict(strategy=x["strategy"], trades=0, closed=0, open=0, net_inr_1x=0.0, net_inr_1_5x=0.0, by_status={}))
        s["trades"] += 1; s["closed" if x["status"] == "CLOSED" else "open"] += 1
        s["by_status"][x["desk_status"]] = s["by_status"].get(x["desk_status"], 0) + 1
        if x["net_inr_1_5x"] is not None: s["net_inr_1x"] = round(s["net_inr_1x"] + x["net_inr_1x"], 2); s["net_inr_1_5x"] = round(s["net_inr_1_5x"] + x["net_inr_1_5x"], 2)
    return rows, sorted(sub.values(), key=lambda s: -s["net_inr_1_5x"])


def once():
    rows, sub = build()
    body = json.loads(BG.read_text()) if BG.is_file() else {"source": "background-test", "label": "Background test (not traded)", "paper_only": True,
                                                               "in_desk_pnl": False, "day": DAY, "summary": {}, "trades": []}
    body["desk_strategies_today"] = {"as_of_ist": datetime.now(IST).isoformat(timespec="seconds"), "count_in_total": False, "in_desk_pnl": False,
                                     "note": "Today's desk-strategy signals (10 PX + R01) with what the desk did. Paper only; not in desk P&L.",
                                     "rows": rows, "per_strategy": sub}
    tmp = BG.with_suffix(".tmp2"); tmp.write_text(json.dumps(body, indent=1)); os.replace(tmp, BG)
    return f"{datetime.now(IST):%H:%M:%S} IST rows {len(rows)} strategies {len(sub)}"


if __name__ == "__main__":
    if (sys.argv[1:] or ["once"])[0] == "loop":
        while datetime.now(IST).strftime("%H:%M") < "15:31":
            try: print(once(), flush=True)
            except Exception as e: print("ERROR", type(e).__name__, e, flush=True)
            time.sleep(300)
        print(once(), flush=True)
    else:
        print(once())
