"""paper_extra: PAPER-ONLY runner for lab strategies that have no desk code (2026-10-13, Sahil's call, no real-price recheck).

Each minute: (1) read-only Dhan 1m fetch (repo dhan_client.historical.intraday, same as /tmp/bf_refresh.py) of NIFTY/SENSEX index
+ NIFTY options near ATM, on top of the latest data/backfill run; (2) lab build_day.py + score_pass.py (box code, unchanged signal
logic) in ~/paper_extra_rt with ~/paper_extra_venv; (3) write data/recon/paper_extra/<day>.json. The desk loop
(desk_ml.research_rules.paper_extra_rows) books these rows through the same opposite-side / same-contract / 10-lot / risk gate.
Desk trades only from the PX_* on-from minute in config/desk_rules_on_from.yaml. No orders: orders=REFUSED.
Usage: runner.py once|loop|replay-check"""
import csv, json, os, shutil, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

DAY = "2026-10-13"
REPO = Path(__file__).resolve().parents[2]
RT = Path.home() / "paper_extra_rt"
VENV = Path.home() / "paper_extra_venv" / "bin" / "python"
BF = REPO / "data" / "backfill" / DAY
LIVE_RUN = REPO / "data" / "paper_extra" / DAY / "run"
OUT = REPO / "data" / "recon" / "paper_extra" / f"{DAY}.json"
IST = timezone(timedelta(hours=5, minutes=30))
STRATS = {  # score_pass strategy name -> desk rule id (T2 = the scored variant)
    "B2": "PX_B2", "R07": "PX_R07", "EP-010": "PX_EP010", "EP-018": "PX_EP018",
    "I1_ORB:ORB_A:T2": "PX_ORB_A", "I4_VWAP:VWAP_CONT:T2": "PX_VWAP_CONT", "I9_ENGULF:ENG_5:T2": "PX_ENG_5",
    "I10_INSIDEBAR:IB_5:T2": "PX_IB_5", "I10_INSIDEBAR:IB_15:T2": "PX_IB_15", "I11_MINED:MINE_PE:T2": "PX_MINE_PE",
}
EXIT_RULE = {
    "PX_B2": "Lab B2: NIFTY index stop / rule exit (stress.py path)", "PX_R07": "Lab R07 (combos): index path exit",
    "PX_EP010": "TV EP-010 port: own exit signal or stop", "PX_EP018": "TV EP-018 port: own exit signal or stop",
}
BASIS = "NONE_IN_PREMIUM: rule exits on NIFTY index levels, time, or its own exit signal; no option-premium stop/target"
XR = {"STOP": "STOP", "TARGET": "TARGET", "TIME": "TIME", "EXIT": "RULE_EXIT", "SIGNAL": "RULE_EXIT", "REVERSE": "RULE_EXIT",
      "EOD": "TIME", "open": "OPEN", "": None}
# 2026-10-13 fix (box fix_ep): score_pass entries = next-minute open after the signal (EP-018 was same-minute open = look-ahead);
# STOP/TARGET/SIGNAL/REVERSE exits = next-minute OPEN, never the touch-minute close. test_exit_fill.py checks every cycle.


def latest_bf_run() -> Path:
    runs = [p for p in BF.iterdir() if p.is_dir() and (p / "IDX_NIFTY.json").is_file()]
    return max(runs, key=lambda p: (p / "IDX_NIFTY.json").stat().st_mtime)


def fetch() -> str:
    """Refresh LIVE_RUN: copy latest backfill run, then re-fetch indices + NIFTY ATM±200 options (read-only)."""
    src = latest_bf_run()
    if LIVE_RUN.exists():
        shutil.rmtree(LIVE_RUN)
    shutil.copytree(src, LIVE_RUN)
    from dhan_client.client import DhanClient
    to = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    sm = list(csv.DictReader(open(REPO / "data" / "cache" / "marketdata" / f"scrip_master_{DAY}.csv")))
    n = 0
    with DhanClient(dry_run=False) as c:
        def get(sid, seg, inst, name, frm, oi=False):
            nonlocal n
            body = {"securityId": str(sid), "exchangeSegment": seg, "instrument": inst, "interval": 1, "fromDate": frm, "toDate": to}
            if oi:
                body["oi"] = True
            for _ in range(2):
                try:
                    r = c.historical.intraday(body)
                    (LIVE_RUN / f"{name}.json").write_text(json.dumps(r)); n += 1; time.sleep(0.35); return r
                except Exception:
                    time.sleep(1.5)
            return None
        r = get(13, "IDX_I", "INDEX", "IDX_NIFTY", "2026-08-20 09:15:00")
        get(51, "IDX_I", "INDEX", "IDX_SENSEX", "2026-08-20 09:15:00")
        if not r or not r.get("close"):
            return f"from {src.name}, fetch FAILED (using backfill only)"
        atm = round(float(r["close"][-1]) / 50) * 50
        for row in sm:
            if (row["SEM_EXM_EXCH_ID"] == "NSE" and row["SEM_INSTRUMENT_NAME"] == "OPTIDX" and row["SEM_TRADING_SYMBOL"].startswith("NIFTY-")
                    and row["SEM_EXPIRY_DATE"].startswith(DAY)):
                k = float(row["SEM_STRIKE_PRICE"])
                if abs(k - atm) <= 200:
                    get(row["SEM_SMST_SECURITY_ID"], "NSE_FNO", "OPTIDX", f"NIFTY_{DAY}_{int(k)}_{row['SEM_OPTION_TYPE']}", f"{DAY} 09:15:00", True)
    return f"from {src.name}, fetched {n} series to {to[11:16]} IST"


def score() -> list:
    live = RT / "live"
    tape = REPO / "data" / "tape" / "v2" / DAY
    subprocess.run([str(VENV), "build_day.py", str(LIVE_RUN), str(tape), "work"], cwd=live, check=True, capture_output=True, timeout=120)
    p = subprocess.run([str(VENV), "score_pass.py"], cwd=live, check=True, capture_output=True, timeout=180, text=True)
    t = subprocess.run([str(VENV), str(REPO / "scripts" / "paper_extra" / "test_exit_fill.py"), str(live / "score_latest.csv")],
                       capture_output=True, text=True, timeout=60, env=dict(os.environ, PX_RUN=str(LIVE_RUN)))
    if t.returncode != 0:  # fail closed: keep last good file, book nothing new
        raise RuntimeError("FILL_RULE_FAIL " + t.stdout.strip()[:300])
    return list(csv.DictReader(open(live / "score_latest.csv"))), p.stdout.strip().splitlines()[-1]


def rows_from(score_rows: list) -> list:
    out = []
    for r in score_rows:
        rid = STRATS.get(r["strategy"])
        if not rid or r.get("signalled") != "Y" or r.get("status") not in ("OPEN", "CLOSED"):
            continue
        st = r["status"]
        out.append({
            "rule_id": rid, "strategy": r["strategy"], "underlying": "NIFTY", "side": r["side"], "strike": float(r["strike"]),
            "signal_time": r["signal_time"], "entry_time": r["entry_time"], "exit_time": r["exit_time"] if st == "CLOSED" else None,
            "exit_reason": r["exit_reason"] if st == "CLOSED" else None, "entry_px": float(r["entry_px"]),
            "exit_px": float(r["exit_px"]) if st == "CLOSED" else None, "status": st,
            "mark_time": r.get("mark_time") or None, "mark_px": float(r["mark_px"]) if r.get("mark_px") else None,
            "entry_src": r.get("entry_src"), "exit_src": r.get("exit_src") or None,
            "stop_px": None, "target_px": None, "stop_target_basis": BASIS,
            "planned_exit_ist": None, "exit_reason_std": XR.get(r["exit_reason"], r["exit_reason"]) if st == "CLOSED" else "OPEN",
            "exit_rule": EXIT_RULE.get(rid, f"Lab {r['strategy']}: index stop / target / time per lab rule (T2 variant)"),
        })
    return [x for x in out if x["status"] == "CLOSED" or x["mark_px"] is not None]


def write(rows: list, note: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    blob = {"day": DAY, "orders": "REFUSED", "paper_only": True, "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
            "note": note, "strategies": sorted(set(STRATS.values())), "rows": rows}
    tmp = OUT.with_suffix(".tmp"); tmp.write_text(json.dumps(blob, indent=1)); os.replace(tmp, OUT)


def log_risk() -> str:
    """Per-minute desk exposure from the desk's own journal (all desk rules, not just PX): open lots + premium at risk."""
    try:
        j = json.loads((REPO / "data" / "recon" / "research_rules" / f"{DAY}.json").read_text())
    except (OSError, ValueError):
        return "risk n/a"
    op = j.get("open") or []
    lots = {u: sum(int(r.get("lots") or 0) for r in op if r.get("underlying") == u) for u in ("NIFTY", "SENSEX")}
    prem = round(sum(float(r.get("entry") or 0) * int(r.get("qty") or 0) for r in op), 2)
    rk = j.get("risk") or {}
    rec = {"ist": datetime.now(IST).isoformat(timespec="seconds"), "open_trades": len(op), "open_lots": lots,
           "premium_at_risk_inr": prem, "day_net_inr": rk.get("day_net_inr"), "halted_reason": rk.get("halted_reason"),
           "open": [(r.get("rule_id"), r.get("side"), r.get("entry_min")) for r in op]}
    with open(OUT.parent / f"risk_minutes_{DAY}.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    return f"open {len(op)} lots {lots} prem_at_risk {prem} net {rk.get('day_net_inr')} halt {rk.get('halted_reason')}"


def once() -> str:
    f = fetch()
    sr, line = score()
    rows = rows_from(sr)
    write(rows, f"{f}; {line}")
    return f"{datetime.now(IST):%H:%M:%S} IST {f}; {line}; px rows {len(rows)}; {log_risk()}"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "loop":
        while datetime.now(IST).strftime("%H:%M") < "15:31":
            t = time.time()
            try:
                print(once(), flush=True)
            except Exception as e:  # keep last good file; desk keeps running
                print(f"{datetime.now(IST):%H:%M:%S} IST CYCLE_ERROR {type(e).__name__}: {e}", flush=True)
            time.sleep(max(5, 60 - (time.time() - t)))
    else:
        print(once())
