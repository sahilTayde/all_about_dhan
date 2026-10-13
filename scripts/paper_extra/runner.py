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

IST = timezone(timedelta(hours=5, minutes=30))
DAY = os.environ.get("PX_DAY") or datetime.now(IST).strftime("%Y-%m-%d")
REPO = Path(__file__).resolve().parents[2]
RT = Path.home() / "paper_extra_rt"
VENV = Path.home() / "paper_extra_venv" / "bin" / "python"
BF = REPO / "data" / "backfill" / DAY
LIVE_RUN = REPO / "data" / "paper_extra" / DAY / "run"
OUT = REPO / "data" / "recon" / "paper_extra" / f"{DAY}.json"
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


def latest_bf_run():
    if not BF.is_dir():
        return None
    runs = [p for p in BF.iterdir() if p.is_dir() and (p / "IDX_NIFTY.json").is_file()]
    return max(runs, key=lambda p: (p / "IDX_NIFTY.json").stat().st_mtime) if runs else None


def scrip_master() -> Path:
    d = REPO / "data" / "cache" / "marketdata"
    p = d / f"scrip_master_{DAY}.csv"
    return p if p.is_file() else sorted(d.glob("scrip_master_*.csv"))[-1]


def nifty_expiry(rows) -> str:
    """Nearest NIFTY weekly option expiry on/after DAY (scrip master)."""
    exps = sorted({r["SEM_EXPIRY_DATE"][:10] for r in rows if r["SEM_EXM_EXCH_ID"] == "NSE" and r["SEM_INSTRUMENT_NAME"] == "OPTIDX"
                   and r["SEM_TRADING_SYMBOL"].startswith("NIFTY-") and r["SEM_EXPIRY_DATE"][:10] >= DAY})
    return exps[0]


SM_ROWS = None
EXP = None
CUTOFF_TS = 2 ** 40
EXTRA_STRIKES = set()
Q01_STATE = {"armed": None, "status": "not checked yet"}  # read by the desk: armed False -> no Q01 priority window  # strikes of open rows / Q01 contract, always refreshed


def fetch() -> str:
    """Refresh LIVE_RUN: copy latest backfill run, then re-fetch indices + NIFTY ATM±200 options (read-only)."""
    global SM_ROWS, EXP
    src = latest_bf_run()
    first = not LIVE_RUN.exists()
    if first:
        if src is not None:
            shutil.copytree(src, LIVE_RUN)
        else:
            LIVE_RUN.mkdir(parents=True)
    from dhan_client.client import DhanClient
    global CUTOFF_TS
    nowdt = datetime.now(IST)
    to = nowdt.strftime("%Y-%m-%d %H:%M:%S")
    CUTOFF_TS = int(nowdt.replace(second=0, microsecond=0).timestamp())
    if SM_ROWS is None:
        SM_ROWS = list(csv.DictReader(open(scrip_master())))
        EXP = nifty_expiry(SM_ROWS)
    sm = SM_ROWS
    band = 300 if first else 200
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
                    if isinstance(r, dict) and r.get("timestamp"):  # drop the minute still forming (complete bars only)
                        keep = [i for i, t in enumerate(r["timestamp"]) if int(t) < CUTOFF_TS]
                        r = {k: ([v[i] for i in keep] if isinstance(v, list) and len(v) == len(r["timestamp"]) else v) for k, v in r.items()}
                    (LIVE_RUN / f"{name}.json").write_text(json.dumps(r)); n += 1; time.sleep(0.35); return r
                except Exception:
                    time.sleep(1.5)
            return None
        r = get(13, "IDX_I", "INDEX", "IDX_NIFTY", "2026-08-20 09:15:00")
        get(51, "IDX_I", "INDEX", "IDX_SENSEX", "2026-08-20 09:15:00")
        if first or not (LIVE_RUN / "IDX_INDIAVIX.json").is_file():
            get(21, "IDX_I", "INDEX", "IDX_INDIAVIX", "2026-10-01 09:15:00")
        if not r or not r.get("close"):
            return f"from {src.name}, fetch FAILED (using backfill only)"
        atm = round(float(r["close"][-1]) / 50) * 50
        for row in sm:
            if (row["SEM_EXM_EXCH_ID"] == "NSE" and row["SEM_INSTRUMENT_NAME"] == "OPTIDX" and row["SEM_TRADING_SYMBOL"].startswith("NIFTY-")
                    and row["SEM_EXPIRY_DATE"].startswith(EXP)):
                k = float(row["SEM_STRIKE_PRICE"])
                if abs(k - atm) <= band or int(k) in EXTRA_STRIKES:
                    get(row["SEM_SMST_SECURITY_ID"], "NSE_FNO", "OPTIDX", f"NIFTY_{EXP}_{int(k)}_{row['SEM_OPTION_TYPE']}", f"{DAY} 09:15:00", True)
    return f"from {src.name if src else 'fresh'}, exp {EXP}, fetched {n} series to {to[11:16]} IST"


def write_vix_daily() -> dict:
    """Prior-day India VIX closes after the lab history (last 1m close of each day, Dhan IDX_I sid 21) -> work/vix_daily.json."""
    out = {}
    try:
        j = json.loads((LIVE_RUN / "IDX_INDIAVIX.json").read_text())
        for t, c in zip(j["timestamp"], j["close"]):
            d = datetime.fromtimestamp(int(t), IST).strftime("%Y-%m-%d")
            if "2026-10-09" < d < DAY:
                out[d] = float(c)
    except (OSError, ValueError, KeyError):
        pass
    if out:
        (RT / "live" / "work" / "vix_daily.json").write_text(json.dumps(out))
    return out


def score() -> list:
    live = RT / "live"
    cut = datetime.fromtimestamp(CUTOFF_TS, IST) if CUTOFF_TS < 2 ** 40 else None
    env = dict(os.environ, PX_DAY=DAY, PX_EXP=EXP or DAY, PX_CUTOFF_M=str(cut.hour * 60 + cut.minute) if cut else "")
    tape = REPO / "data" / "tape" / "v2" / DAY
    subprocess.run([str(VENV), "build_day.py", str(LIVE_RUN), str(tape), "work"], cwd=live, check=True, capture_output=True, timeout=120, env=env)
    p = subprocess.run([str(VENV), "score_pass.py"], cwd=live, check=True, capture_output=True, timeout=180, text=True, env=env)
    t = subprocess.run([str(VENV), str(REPO / "scripts" / "paper_extra" / "test_exit_fill.py"), str(live / "score_latest.csv")],
                       capture_output=True, text=True, timeout=60, env=dict(env, PX_RUN=str(LIVE_RUN)))
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
            "note": note, "strategies": sorted(set(STRATS.values())) + ["Q01_ITM100"], "q01": dict(Q01_STATE), "rows": rows}
    tmp = OUT.with_suffix(".tmp"); tmp.write_text(json.dumps(blob, indent=1)); os.replace(tmp, OUT)


# ---------------- Q01 ITM100 v1.1 (desk paper, from 2026-10-14) + Q01_T15 (shadow / background box only) ----------------
Q01_FROM = "2026-10-14"
VIX_HIST = REPO / "packages" / "desk-ml" / "tests" / "fixtures" / "q01" / "vix_daily_hist.json"
BG_DIR = REPO / "data" / "research" / "background_test"


def _bars(name: str) -> dict:
    try:
        j = json.loads((LIVE_RUN / f"{name}.json").read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for i, t in enumerate(j.get("timestamp") or []):
        dt = datetime.fromtimestamp(int(t), IST)
        if dt.strftime("%Y-%m-%d") == DAY:
            out[dt.hour * 60 + dt.minute] = (float(j["open"][i]), float(j["close"][i]))
    return out


def prev_trading_day(day: str) -> str:
    """Previous NSE session (weekends + NSE holiday list in the lab lib)."""
    hol = set()
    for f in (RT / "dhan" / "research" / "lab" / "lib").glob("nse_holidays_20*.csv"):
        for line in f.read_text().splitlines():
            if line[:2] == "20":
                hol.add(line[:10])
    d = datetime.fromisoformat(day).date() - timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in hol:
        d -= timedelta(days=1)
    return d.isoformat()


def q01_cycle(now_m: int) -> tuple:
    """Returns (desk_rows, t15_bg_row or None, status text). now_m = last COMPLETE IST minute."""
    sys.path.insert(0, str(REPO / "packages" / "desk-ml" / "src"))
    from desk_ml import q01
    if DAY < Q01_FROM:
        return [], None, "Q01 off before " + Q01_FROM
    vix = json.loads(VIX_HIST.read_text()) + [[d, c] for d, c in write_vix_daily().items()]
    vf = q01.vix_filter(vix, DAY)
    Q01_STATE.update(armed=None, status="VIX check failed")
    if vf.get("status") != "OK" or vf.get("v1_date") != prev_trading_day(DAY):
        return [], None, f"Q01 DATA_MISSING: VIX close for {prev_trading_day(DAY)} not available (last {vf.get('v1_date')})"
    Q01_STATE.update(armed=bool(vf["armed"]), status=f"VIX pct {vf['pct']} chg {vf['chg']} (close {vf['v1_date']})")
    if not vf["armed"]:
        return [], None, f"Q01 NO_SIGNAL (VIX pct {vf['pct']}, chg {vf['chg']})"
    op, osrc = q01.official_open(REPO / "data" / "tape" / "v2" / DAY)
    if op is None:
        return [], None, f"Q01 DATA_MISSING {osrc}"
    idx = {m: c for m, (o, c) in _bars("IDX_NIFTY").items()}
    if now_m < q01.SIG_M or q01.SIG_M not in idx:
        return [], None, f"Q01 armed (pct {vf['pct']}, chg {vf['chg']}), open {op} {osrc}; waiting for 10:00 close"
    s10 = idx[q01.SIG_M]
    ss = q01.side_strike(op, s10)
    if ss is None:
        return [], None, "Q01 NO_TRADE mv=0"
    sg, side, K = ss
    EXTRA_STRIKES.add(K)
    opt = _bars(f"NIFTY_{EXP}_{K}_{side}")
    rows, bg = [], None
    for variant in ("PLAIN", "T15"):
        r = q01.simulate(sg=sg, s10=s10, idx=idx, opt=opt, variant=variant, now_m=now_m)
        if r["status"] not in ("OPEN", "CLOSED"):
            continue
        closed = r["status"] == "CLOSED"
        row = {"rule_id": "Q01_ITM100" if variant == "PLAIN" else "Q01_T15", "strategy": "Q01_ITM100_v1.1" if variant == "PLAIN" else "Q01_T15",
               "underlying": "NIFTY", "side": side, "strike": float(K), "signal_time": "10:00", "entry_time": r["entry_min"],
               "exit_time": r.get("exit_min") if closed else None, "exit_reason": r.get("exit_reason") if closed else None,
               "entry_px": r["entry_px"], "exit_px": r.get("exit_px"), "status": r["status"],
               "mark_time": r.get("mark_min"), "mark_px": r.get("mark_px"), "entry_src": "dhan_api_1m", "exit_src": "dhan_api_1m",
               "stop_px": None, "target_px": r["target_px"], "index_stop": r["index_stop"], "stop_dist_idx": r["stop_dist_idx"],
               "stop_target_basis": f"Stop is an index level: NIFTY 1-min close {'<=' if sg > 0 else '>='} {r['index_stop']} (S10 {s10} -/+ 0.3xE/0.54)."
               + (f" Target = entry + 1.5R = {r['target_px']} on 1-min option close." if variant == "T15" else " No target (v1.1)."),
               "planned_exit_ist": r["planned_exit"], "exit_reason_std": (r.get("exit_reason") if closed else "OPEN"),
               "exit_rule": "Q01 v1.1: index stop on 1-min closes, else 10:21 time exit" if variant == "PLAIN" else "Q01_T15 shadow: index stop, target E+1.5R, 10:21 cap",
               "official_open": op, "open_src": osrc, "vix_pct": vf["pct"], "vix_chg": vf["chg"], "S10": s10}
        if variant == "PLAIN":
            rows.append(row)
        else:
            bg = row
    return rows, bg, f"Q01 {side} {K} " + ", ".join(f"{r['rule_id']}:{r['status']}" for r in rows + ([bg] if bg else []))


def write_bg_t15(bg) -> None:
    """Q01_T15 is shadow only: background test box, never desk rows. Merges into the day's background file."""
    if bg is None:
        return
    p = BG_DIR / f"{DAY}.json"
    try:
        body = json.loads(p.read_text())
    except (OSError, ValueError):
        body = {"source": "background-test", "label": "Background test (not traded)", "paper_only": True, "in_desk_pnl": False,
                "day": DAY, "summary": {}, "trades": []}
    body["trades"] = [t for t in body.get("trades") or [] if t.get("strategy") != "Q01_T15"]
    t = {"source": "paper_extra_shadow", "paper_only": True, "traded": False, "day": DAY, "strategy": "Q01_T15", "side": bg["side"],
         "strike": int(bg["strike"]), "signal_ist": "10:00", "entry_ist": bg["entry_time"], "exit_ist": bg["exit_time"],
         "exit_reason": bg["exit_reason"], "exit_reason_std": bg["exit_reason_std"], "entry_px": bg["entry_px"], "exit_px": bg["exit_px"],
         "qty": 650, "net_inr_1_5x": None, "status": bg["status"], "stop_px": None, "target_px": bg["target_px"],
         "index_stop": bg["index_stop"], "stop_target_basis": bg["stop_target_basis"], "planned_exit_ist": bg["planned_exit_ist"],
         "verified": "SHADOW", "count_in_total": False}
    if bg["status"] == "CLOSED":
        sys.path.insert(0, str(REPO / "packages" / "desk-ml" / "src"))
        from desk_ml import research_rules as rr
        c = rr._cost_row(entry=bg["entry_px"], exit_px=bg["exit_px"], qty=650, filled=True, underlying="NIFTY")
        t["net_inr_1_5x"] = round((bg["exit_px"] - bg["entry_px"]) * 650 - float(c["charges_inr"]), 2)
    body["trades"].append(t)
    body["as_of_ist"] = datetime.now(IST).isoformat(timespec="seconds")
    BG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(body, indent=1)); os.replace(tmp, p)


# ---------------- Premium-stop BACKGROUND SHADOWS (from 2026-10-14): EP009_P, B2_P, VWAPCONT_PE_P ----------------
# Specs sealed in research/lab/2026-10-13_premium_stops/SHADOW_*.md. Same contract as Q01_T15: never desk rows, never in desk P&L,
# written only to the background test box with count_in_total False. Computed by pshadow_live.py in a background process on a
# snapshot of the completed-minute work files, so it can never slow or break the desk cycle (result lags at most one cycle).
PS_FROM = "2026-10-14"
PS_NAMES = {"EP009_P": "SHADOW_EP009_P", "B2_P": "SHADOW_B2_P", "VWAPCONT_PE_P": "SHADOW_VWAPCONT_PE_P"}
PS_SPEC = {"EP009_P": "SHADOW_EP009_P.md b09d74bf", "B2_P": "SHADOW_B2_P.md 1006e2ac", "VWAPCONT_PE_P": "SHADOW_VWAPCONT_PE_P.md daf44776"}
PS_DIR = RT / "live" / "work_ps"
PS_PROC = None
PS_T0 = 0.0
PS_STD = {"STOP": "STOP", "TARGET": "TARGET", "TIME": "TIME"}


def ps_bg_trades(js: dict) -> list:
    """pshadow_latest.json rows -> background-box trade dicts (never desk rows)."""
    out = []
    for r in js.get("rows") or []:
        name = r["name"]; st = r.get("status"); closed = st == "CLOSED"
        hm = lambda m: None if m is None else f"{int(m) // 60:02d}:{int(m) % 60:02d}"
        t = {"source": "paper_extra_shadow", "paper_only": True, "traded": False, "day": js.get("day", DAY), "strategy": PS_NAMES[name],
             "research_strat": r.get("research_strat"), "side": r.get("side"), "strike": r.get("strike"), "signal_ist": r.get("signal_ist"),
             "entry_ist": hm(r.get("em")), "exit_ist": hm(r.get("fill_m")) if closed else None, "exit_signal_ist": hm(r.get("xm")),
             "exit_reason": r.get("kind") if closed else None, "exit_reason_std": PS_STD.get(r.get("kind"), r.get("kind")) if closed else (st or "OPEN"),
             "entry_px": r.get("en"), "exit_px": r.get("ex") if closed else None, "mark_ist": hm(r.get("mark_m")), "mark_px": r.get("mark_px"),
             "qty": 650, "net_inr_1_5x": None, "status": st, "stop_px": r.get("stop_px"), "target_px": r.get("target_px"),
             "stop_target_basis": f"Premium levels on 1-min option CLOSES, stop checked first: stop = entry x (1-{r['S']}), target = entry + {r['k']} x {r['S']} x entry; "
                                  "fill = next minute OPEN - 0.05; else TIME at the cap.",
             "planned_exit_ist": hm(r.get("capm")), "note": r.get("note"), "data_through_ist": js.get("data_through"),
             "spec": PS_SPEC[name], "verified": "SHADOW", "count_in_total": False}
        if closed:
            sys.path.insert(0, str(REPO / "packages" / "desk-ml" / "src"))
            from desk_ml import research_rules as rr
            c = rr._cost_row(entry=t["entry_px"], exit_px=t["exit_px"], qty=650, filled=True, underlying="NIFTY")
            t["net_inr_1_5x"] = round((t["exit_px"] - t["entry_px"]) * 650 - float(c["charges_inr"]), 2)
        out.append(t)
    return out


def write_bg_pshadow(js: dict) -> None:
    p = BG_DIR / f"{DAY}.json"
    try:
        body = json.loads(p.read_text())
    except (OSError, ValueError):
        body = {"source": "background-test", "label": "Background test (not traded)", "paper_only": True, "in_desk_pnl": False,
                "day": DAY, "summary": {}, "trades": []}
    keep = set(PS_NAMES.values())
    body["trades"] = [t for t in body.get("trades") or [] if t.get("strategy") not in keep] + ps_bg_trades(js)
    body["pshadow"] = {"data_through_ist": js.get("data_through"), "errors": js.get("errors"), "skipped": js.get("skipped"), "count_in_total": False}
    body["as_of_ist"] = datetime.now(IST).isoformat(timespec="seconds")
    BG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(body, indent=1)); os.replace(tmp, p)


def pshadow_cycle() -> str:
    """Harvest the last background result (bg box + pin strikes), then launch the next one on a fresh snapshot."""
    global PS_PROC, PS_T0
    if DAY < PS_FROM:
        return "pshadow off before " + PS_FROM
    if PS_PROC is not None and PS_PROC.poll() is None:
        if time.time() - PS_T0 < 240:
            return "pshadow running"
        PS_PROC.kill(); PS_PROC.wait()
    txt = "pshadow started"
    res = PS_DIR / "pshadow_latest.json"
    if res.is_file():
        js = json.loads(res.read_text())
        if js.get("day") == DAY:
            for k in js.get("need_strikes") or []:
                EXTRA_STRIKES.add(int(k))
            write_bg_pshadow(js)
            txt = f"pshadow thru {js.get('data_through')}: " + (", ".join(f"{r['name']}:{r.get('status')}" for r in js["rows"]) or "no signal") \
                + (f" ERR {js['errors']}" if js.get("errors") else "")
    work = RT / "live" / "work"
    PS_DIR.mkdir(parents=True, exist_ok=True)
    for f in ("base_1m_aug.parquet", f"opt1m_{DAY}.parquet", "vix_daily.json"):
        if (work / f).is_file():
            shutil.copy2(work / f, PS_DIR / f)
    env = dict(os.environ, PX_DAY=DAY, PX_EXP=EXP or DAY)
    PS_PROC = subprocess.Popen([str(VENV), str(REPO / "scripts" / "paper_extra" / "pshadow_live.py"), str(PS_DIR)], cwd=RT / "live", env=env,
                               stdout=open(PS_DIR / "pshadow.log", "a"), stderr=subprocess.STDOUT)
    PS_T0 = time.time()
    return txt


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
    for r in rows:
        if r["status"] == "OPEN":
            EXTRA_STRIKES.add(int(r["strike"]))
    now = datetime.now(IST) - timedelta(minutes=1)
    try:
        qrows, bg, qtxt = q01_cycle(now.hour * 60 + now.minute)
        write_bg_t15(bg)
    except Exception as e:  # Q01 must not stop the PX strategies
        qrows, qtxt = [], f"Q01 ERROR {type(e).__name__}: {e}"
    rows += qrows
    try:  # background shadows only: never desk rows, never stop the desk path
        ptxt = pshadow_cycle()
    except Exception as e:
        ptxt = f"pshadow ERROR {type(e).__name__}: {e}"
    write(rows, f"{f}; {line}; {qtxt}; {ptxt}")
    line = f"{line}; {qtxt}; {ptxt}"
    return f"{datetime.now(IST):%H:%M:%S} IST {f}; {line}; px rows {len(rows)}; {log_risk()}"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "loop":
        start = datetime.now(IST).replace(hour=9, minute=16, second=5, microsecond=0)
        if datetime.now(IST) < start:  # first complete 1m bar is 09:15
            print(f"{datetime.now(IST):%H:%M:%S} IST waiting for 09:16:05 IST (day {DAY})", flush=True)
            time.sleep((start - datetime.now(IST)).total_seconds())
        while datetime.now(IST).strftime("%H:%M") < "15:31":
            t = time.time()
            try:
                print(once(), flush=True)
            except Exception as e:  # keep last good file; desk keeps running
                print(f"{datetime.now(IST):%H:%M:%S} IST CYCLE_ERROR {type(e).__name__}: {e}", flush=True)
            time.sleep(max(5, 60 - (time.time() - t)))
    else:
        print(once())
