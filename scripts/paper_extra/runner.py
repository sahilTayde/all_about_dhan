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
# 2026-10-18 SENSEX support (box; paper only). Same PX rules, run per underlying; desk guard (opposite side across NIFTY+SENSEX,
# same contract, 10-lot cap, risk) is unchanged in desk_ml.research_rules._desk_pass. Q01/Q01_T15/pshadow stay NIFTY-only (sealed NIFTY specs).
UNDS = ("NIFTY", "SENSEX")
QTY = {"NIFTY": 650, "SENSEX": 200}   # 10 lots each (NIFTY 65, SENSEX 20)
LOT = {"NIFTY": 65, "SENSEX": 20}
OPT_SPEC = {"NIFTY": ("NSE", "NIFTY-", "NSE_FNO", 50), "SENSEX": ("BSE", "SENSEX-", "BSE_FNO", 100)}   # exch, symbol prefix, API segment, grid
BAND = {"NIFTY": (300, 200), "SENSEX": (1000, 700)}   # first / later fetch band in index points (SENSEX ~3.3x NIFTY)
XR = {"STOP": "STOP", "TARGET": "TARGET", "TIME": "TIME", "EXIT": "RULE_EXIT", "SIGNAL": "RULE_EXIT", "REVERSE": "RULE_EXIT",
      "EOD": "TIME", "open": "OPEN", "": None}
# 2026-10-19 PRICE EXITS (Sahil, Oct 18 23:54 CT via Opposition): every PX row gets a premium stop AND target AND trail; no timers.
# Replay: desk/verify/2026-10-19_price_exits_all/REPORT.md. Close-based trigger on 1m option closes (live: depth bid, see live_guard),
# fill = next minute OPEN; stop wins if both in one minute; trail = break-even at +STOP, then high-water x (1-STOP); 15:15 IST safety close.
PRICE_EXIT = {"stop": 0.30, "target": 0.60, "trail": True, "antichase_rise": 0.12, "safety_m": 915, "live_poll_s": 3.0}   # re-entry OFF (Sahil, Oct 19)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_pricer as LP   # noqa: E402
LIVE = {}            # (rule_id, underlying, signal_time) -> LP.LiveTrade
LIVE_FILE = REPO / "data" / "paper_extra" / DAY / "live_exits.json"
TAIL = LP.DepthTail(REPO / "data" / "tape" / "v2" / DAY / "depth_quotes.jsonl", start_at_end=True)   # never replay old tape quotes (2026-10-19 deploy bug)
LAST_ROWS = {"rows": None, "note": ""}
# REVIEW FIX (2026-10-19): restart-safe. START_FILE pins the first minute this runner (new version) ran today. Signals whose entry minute is
# before it are never back-filled from past bars (status PRE_START, never booked). Rows already in OUT from an earlier process are carried:
# CLOSED rows are frozen exactly as booked; OPEN rows get the new exits evaluated only from START_M onward (no retro exit).
START_FILE = REPO / "data" / "paper_extra" / DAY / "runner_start.json"
START = {"m": None, "frozen": {}, "carried": set()}


def _start_load(now_m: int) -> None:
    try:
        START["m"] = int(json.loads(START_FILE.read_text())["start_m"])
    except (OSError, ValueError, KeyError, TypeError):
        START["m"] = now_m + 1   # first start today: only signals entering after this minute are new
        START_FILE.parent.mkdir(parents=True, exist_ok=True); START_FILE.write_text(json.dumps({"start_m": START["m"]}))
    try:
        for r in json.loads(OUT.read_text()).get("rows") or []:
            if not str(r.get("rule_id", "")).startswith("PX_"):
                continue
            k = (r["rule_id"], r.get("underlying") or "NIFTY", r["signal_time"])
            if r.get("status") == "CLOSED" and r.get("price_src") is None and r.get("exit_src") != "v2_depth_bid":
                START["frozen"][k] = r          # closed by the old version: keep as booked
            elif r.get("status") in ("OPEN", "CLOSED"):
                START["carried"].add(k)
    except (OSError, ValueError, KeyError, TypeError):
        pass
# 2026-10-19 (Sahil 1:1 01:46 CT "max 2 open trades"): the paper-extra book holds at most CAP_MAX open trades at a time, NIFTY + SENSEX
# together. A new entry while CAP_MAX are open -> SKIPPED_CAP (never booked, kept in "not_booked" like SKIPPED_CHASE). Applies only to entries
# at/after cap_from_m (pinned in cap_start.json the first time this version runs today) so trades already booked are never re-judged.
# Decisions are sticky for the day: once admitted or skipped, a signal keeps that decision across cycles and restarts.
CAP_MAX = 2
# 2026-10-19 (Sahil 1:1 02:17 CT premium limit; 02:18 CT 10L account -> 9L): sum(entry_px x qty) over the book's open trades (NIFTY + SENSEX) plus the
# new trade must be <= PREMIUM_CAP_INR, else SKIPPED_PREMIUM (never booked, holds no slot, kept in "not_booked"). Checked after cap2.
# Applies to entries at/after prem_from_m (premium_cap_start.json); decisions sticky for the day like cap2.
PREMIUM_CAP_INR = 900000   # 90% of the 10L paper account (Sahil 1:1 02:18 CT "make account a 10 lakh account")
PREM_FILE = REPO / "data" / "paper_extra" / DAY / "premium_cap_start.json"
PREM = {"from_m": None, "skip": set()}
CAP_FILE = REPO / "data" / "paper_extra" / DAY / "cap_start.json"
CAP = {"from_m": None, "admit": set(), "skip": set()}


def _cap_load(now_m: int) -> None:
    try:
        CAP["from_m"] = int(json.loads(CAP_FILE.read_text())["cap_from_m"])
    except (OSError, ValueError, KeyError, TypeError):
        CAP["from_m"] = now_m + 1
        CAP_FILE.parent.mkdir(parents=True, exist_ok=True); CAP_FILE.write_text(json.dumps({"cap_from_m": CAP["from_m"], "cap_max": CAP_MAX}))
    try:
        j = json.loads(OUT.read_text())
        for r in j.get("rows") or []:
            CAP["admit"].add((r.get("rule_id"), r.get("underlying") or "NIFTY", r.get("signal_time")))
        for r in j.get("not_booked") or []:
            if r.get("status") == "SKIPPED_CAP":
                CAP["skip"].add((r.get("rule_id"), r.get("underlying") or "NIFTY", r.get("signal_time")))
    except (OSError, ValueError, KeyError, TypeError):
        pass


def _prem_load(now_m: int) -> None:
    try:
        PREM["from_m"] = int(json.loads(PREM_FILE.read_text())["prem_from_m"])
    except (OSError, ValueError, KeyError, TypeError):
        PREM["from_m"] = now_m + 1
        PREM_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREM_FILE.write_text(json.dumps({"prem_from_m": PREM["from_m"], "premium_cap_inr": PREMIUM_CAP_INR}))
    try:
        for r in json.loads(OUT.read_text()).get("not_booked") or []:
            if r.get("status") == "SKIPPED_PREMIUM":
                PREM["skip"].add((r.get("rule_id"), r.get("underlying") or "NIFTY", r.get("signal_time")))
    except (OSError, ValueError, KeyError, TypeError):
        pass


def _m(s) -> int:
    return int(s[:2]) * 60 + int(s[3:5]) if s and len(str(s)) >= 5 else None


def _pre_status(row: dict):
    """Restart guard + anti-chase verdict without side effects (same tests as apply_price_exits): FROZEN / CARRIED / PRE_START / CHASE / None."""
    u = row.get("underlying") or "NIFTY"; k = (row["rule_id"], u, row.get("signal_time")); em = _m(row.get("entry_time"))
    if START["m"] is not None:
        if k in START["frozen"]:
            return "FROZEN"
        if em is not None and em < START["m"]:
            return "CARRIED" if k in START["carried"] else "PRE_START"
    if em is None:
        return None
    ob = _opt_bars(u, row["strike"], row["side"]); sm = em - 1
    if sm in ob and sm - 2 in ob and ob[sm - 2][1] > 0 and ob[sm][1] / ob[sm - 2][1] - 1 > PRICE_EXIT["antichase_rise"]:
        return "CHASE"
    return None


def _open_at(done: list, em: int) -> list:
    """book trades open at minute em: entered at/before em and not exited before em (same-minute exit still counts as open)"""
    return [d for d in done if d.get("status") in ("OPEN", "CLOSED") and _m(d.get("entry_time")) is not None
            and _m(d["entry_time"]) <= em and (d["status"] == "OPEN" or (_m(d.get("exit_time")) or 10 ** 6) >= em)]


def cap_and_price(rows: list, now_m: int) -> list:
    """apply_price_exits in entry order. Checks, in order: restart guard (PRE_START), anti-chase (SKIPPED_CHASE), cap2 (SKIPPED_CAP),
    premium limit (SKIPPED_PREMIUM). Skipped rows hold no slot and no premium. A slot/premium frees only when the exit minute is before the entry."""
    out = [None] * len(rows)
    order = sorted(range(len(rows)), key=lambda i: (_m(rows[i].get("entry_time")) or 10 ** 6, rows[i].get("signal_time") or ""))
    done = []
    for i in order:
        r = rows[i]; k = (r["rule_id"], r.get("underlying") or "NIFTY", r.get("signal_time")); em = _m(r.get("entry_time"))
        new = r.get("status") in ("OPEN", "CLOSED") and em is not None and k not in CAP["admit"] and _pre_status(r) is None
        if new and CAP["from_m"] is not None and em >= CAP["from_m"]:
            if k in CAP["skip"] or len(_open_at(done, em)) >= CAP_MAX:
                CAP["skip"].add(k)
                r.update(status="SKIPPED_CAP", exit_reason_std="SKIPPED_CAP", exit_time=None, exit_px=None, exit_reason=None,
                         why=r.get("why") or WHY.get(r["rule_id"], r.get("strategy")),
                         note=f"cap: {CAP_MAX} trades already open in the paper-extra book at {r['entry_time']} IST; not booked")
                out[i] = r; done.append(r); continue
        if new and PREM["from_m"] is not None and em >= PREM["from_m"]:
            held = sum(float(d.get("entry_px") or 0) * int(d.get("qty") or 0) for d in _open_at(done, em))
            add = float(r.get("entry_px") or 0) * int(r.get("qty") or 0)
            if k in PREM["skip"] or held + add > PREMIUM_CAP_INR + 1e-6:
                PREM["skip"].add(k)
                r.update(status="SKIPPED_PREMIUM", exit_reason_std="SKIPPED_PREMIUM", exit_time=None, exit_px=None, exit_reason=None,
                         why=r.get("why") or WHY.get(r["rule_id"], r.get("strategy")),
                         note=f"premium limit: open {held:,.0f} + new {add:,.0f} > {PREMIUM_CAP_INR:,} INR at {r['entry_time']} IST; not booked")
                out[i] = r; done.append(r); continue
        x = apply_price_exits(r, now_m)
        if x.get("status") in ("OPEN", "CLOSED") and em is not None and (
                (CAP["from_m"] is not None and em >= CAP["from_m"]) or (PREM["from_m"] is not None and em >= PREM["from_m"])):
            CAP["admit"].add(k)
        out[i] = x; done.append(x)
    return out


WHY = {"PX_B2": "B2: prior day wide range closed near an extreme -> fade at 09:16", "PX_R07": "R07: 30-min efficiency >=0.4 and 3-min move >=0.05%",
       "PX_EP010": "EP-010: TV port entry signal (5m)", "PX_EP018": "EP-018: 2-pt box break on close (60m)", "PX_ORB_A": "ORB_A: opening-range break",
       "PX_VWAP_CONT": "VWAP_CONT: VWAP continuation", "PX_ENG_5": "ENG_5: 5m engulfing", "PX_IB_5": "IB_5: 5m inside-bar break",
       "PX_IB_15": "IB_15: 15m inside-bar break", "PX_MINE_PE": "MINE_PE: mined PE context rule"}


def _opt_bars(u: str, K: int, side: str) -> dict:
    return _bars(f"{u}_{EXPS.get(u) if u != 'NIFTY' else EXP}_{int(K)}_{side}") if EXPS.get(u) or u == "NIFTY" else {}


def price_exit_path(ob: dict, em: int, p0: float, now_m: int, from_m: int = None) -> dict:
    """Premium stop/target/trail from entry minute em (filled at its open). ob = {minute: (open, close)}. Pure; no look-ahead."""
    S, T = PRICE_EXIT["stop"], PRICE_EXIT["target"]; stop = p0 * (1 - S); tgt = p0 * (1 + T); hw = p0
    for m in range(em, min(now_m, PRICE_EXIT["safety_m"]) + 1):
        if m not in ob:
            continue
        c = ob[m][1]; hw = max(hw, c)
        if from_m is not None and m < from_m:   # carried row: build trail state from history, but never exit before the restart
            if PRICE_EXIT["trail"] and hw >= p0 * (1 + S):
                stop = max(stop, p0, hw * (1 - S))
            continue
        if PRICE_EXIT["trail"] and hw >= p0 * (1 + S):
            stop = max(stop, p0, hw * (1 - S))
        why = "STOP" if c <= stop and stop < p0 else "TRAIL" if c <= stop else "TARGET" if c >= tgt else None
        if why:
            fill = next(((m2, ob[m2][0]) for m2 in (m + 1, m + 2, m + 3) if m2 in ob), None)
            if fill is None and now_m >= m + 3:   # no bar in the next 3 minutes: book at the trigger close (same as the replay harness)
                fill = (m, c)
            if fill is None or fill[0] > now_m:
                return dict(status="OPEN", stop_px=round(stop, 2), target_px=round(tgt, 2), pending_exit=why)
            return dict(status="CLOSED", exit_m=fill[0], exit_px=fill[1], why=why, stop_px=round(stop, 2), target_px=round(tgt, 2))
    sf = PRICE_EXIT["safety_m"]
    if now_m > sf:
        nx = next(((m2, ob[m2][0]) for m2 in (sf + 1, sf + 2, sf + 3) if m2 in ob), None)
        if nx is None and now_m >= sf + 3:   # no bar after 15:15: last complete close at/before 15:15
            prev = [m2 for m2 in ob if em <= m2 <= sf]
            nx = (max(prev), ob[max(prev)][1]) if prev else None
        if nx is not None:
            return dict(status="CLOSED", exit_m=nx[0], exit_px=nx[1], why="SAFETY_1515", stop_px=round(stop, 2), target_px=round(tgt, 2))
    return dict(status="OPEN", stop_px=round(stop, 2), target_px=round(tgt, 2))


def _live_load():
    try:
        for d in json.loads(LIVE_FILE.read_text()):
            if "not_before" not in d or not d.get("not_before"):   # written by the pre-fix build (11:30 IST Oct 19): may hold backdated exits; ignore
                continue
            t = LP.LiveTrade.from_json(d); LIVE[t.key] = t
    except (OSError, ValueError, KeyError):
        pass


def _live_save():
    LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = LIVE_FILE.with_suffix(".tmp"); tmp.write_text(json.dumps([t.to_json() for t in LIVE.values()])); os.replace(tmp, LIVE_FILE)


def _hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def apply_price_exits(row: dict, now_m: int, now_iso: str = None) -> dict:
    """Replace the lab exit (index/time/own signal) with premium stop/target/trail.
    Order: (1) anti-chase skip (premium close up > 12% over the 2 minutes before entry -> SKIPPED_CHASE, never booked);
    (2) a live (V2 depth bid) exit already taken wins; (3) live feed fresh -> stay OPEN, marked at the live bid;
    (4) live stale/absent -> 1-minute-close rule (fill next minute open) = fallback. Adds 'why'."""
    hm2m = lambda s: int(s[:2]) * 60 + int(s[3:5])
    now_iso = now_iso or datetime.now(IST).isoformat(timespec="seconds")
    row["why"] = row.get("why") or WHY.get(row["rule_id"], row.get("strategy"))
    row["planned_exit_ist"] = None; row["safety_close_ist"] = "15:15"; row["trail"] = "BE at +30%, then high-water x 0.70"
    row["exit_rule"] = "Premium stop 30% / target 60% / trail (BE at +30%, then HW x 0.70); 15:15 safety close; no timer"
    row["stop_target_basis"] = "PREMIUM: live V2 depth BID every 3 s (fallback: 1-min option close, fill next minute open); stop wins ties"
    u = row["underlying"]; ob = _opt_bars(u, row["strike"], row["side"])
    em = hm2m(row["entry_time"]); sm = em - 1; p0 = float(row["entry_px"])
    key0 = (row["rule_id"], u, row["signal_time"]); from_m = None
    if START["m"] is not None:
        if key0 in START["frozen"]:
            return dict(START["frozen"][key0])
        if em < START["m"]:
            if key0 not in START["carried"]:
                row.update(status="PRE_START", exit_reason_std="PRE_START", note="entry before runner start; not back-filled, not booked"); return row
            from_m = START["m"]
    if from_m is None and sm in ob and sm - 2 in ob and ob[sm - 2][1] > 0 and ob[sm][1] / ob[sm - 2][1] - 1 > PRICE_EXIT["antichase_rise"]:
        row.update(status="SKIPPED_CHASE", exit_reason_std="SKIPPED_CHASE", exit_time=None, exit_px=None, exit_reason=None,
                   note=f"anti-chase: premium +{ob[sm][1] / ob[sm - 2][1] - 1:.0%} in the 2 min before entry; not booked")
        return row
    S, T = PRICE_EXIT["stop"], PRICE_EXIT["target"]
    row["stop_px"] = round(p0 * (1 - S), 2); row["target_px"] = round(p0 * (1 + T), 2)
    key = (row["rule_id"], u, row["signal_time"]); lt = LIVE.get(key)
    if lt is not None and lt.closed:
        c = lt.closed
        row.update(status="CLOSED", exit_time=c["exit_ts"][11:16], exit_px=c["exit_px"], exit_reason=c["why"], exit_reason_std=c["why"],
                   exit_src="v2_depth_bid", stop_px=round(lt.stop, 2), price_src="v2_depth")
        return row
    if em not in ob:
        row["stop_target_basis"] = "PRICE_EXIT_UNPRICED: no option bar at entry; levels from entry price"
    r = price_exit_path(ob, em, p0, now_m, from_m) if em in ob else dict(status="OPEN", stop_px=row["stop_px"], target_px=row["target_px"])
    live_ok = lt is not None and not lt.stale(now_iso)
    if r["status"] == "CLOSED" and not live_ok:
        row.update(status="CLOSED", exit_time=_hm(r["exit_m"]), exit_px=r["exit_px"], exit_reason=r["why"], exit_reason_std=r["why"],
                   stop_px=r["stop_px"], price_src="1m_fallback")
        if lt is not None:
            lt.closed = dict(exit_px=r["exit_px"], exit_ts=f"{DAY}T{_hm(r['exit_m'])}:00+05:30", why=r["why"])
        return row
    if lt is None:   # register for live pricing; seed the high-water from completed 1m closes so trail state matches
        hw = max([ob[m][1] for m in ob if em <= m <= now_m] + [p0])
        exp = EXP if u == "NIFTY" else EXPS.get(u)
        nb = max(now_m + 1, em)   # live quotes count only from the first minute after this cycle's data (never before entry/restart)
        lt = LIVE[key] = LP.LiveTrade(key, LP.iid_of(u, exp, row["strike"], row["side"]), p0, S, T, hw, not_before=f"{DAY}T{_hm(nb)}:00")
    row.update(status="OPEN", exit_time=None, exit_px=None, exit_reason=None, exit_reason_std="OPEN", stop_px=round(lt.stop, 2))
    if live_ok:
        row.update(mark_px=lt.last_bid, mark_time=lt.last_ts[11:16], mark_ts=lt.last_ts, price_src="v2_depth")   # desk parses HH:MM only
    else:   # lab exit may already be CLOSED in the score row: mark from our own last complete 1m close (never leave mark_px empty)
        ms = [m for m in ob if em <= m <= now_m]
        if ms:
            row.update(mark_px=ob[max(ms)][1], mark_time=_hm(max(ms)))
        elif row.get("mark_px") is None:
            row.update(mark_px=p0, mark_time=row["entry_time"])
        row["price_src"] = "1m_fallback"
    return row


def guard_tick() -> int:
    """Every ~3 s between cycles: feed new V2 depth quotes to open live trades; rewrite OUT if any closed or marks moved."""
    open_lt = {t.iid: t for t in LIVE.values() if t.closed is None}
    if not open_lt or LAST_ROWS["rows"] is None:
        TAIL.read(set()); return 0
    nclosed = 0
    for iid, bid, ts in TAIL.read(set(open_lt)):
        t = open_lt.get(iid)
        if t is not None and t.closed is None and t.on_quote(bid, ts):
            nclosed += 1
    now_m = (datetime.now(IST) - timedelta(minutes=1)); nm = now_m.hour * 60 + now_m.minute
    rows = [apply_price_exits(dict(r), nm) if r.get("rule_id", "").startswith("PX_") and r["status"] in ("OPEN", "CLOSED") else r
            for r in LAST_ROWS["rows"]]
    try:   # display only: refresh exit_status with the new marks (never read back by any decision)
        if SO is not None:
            overlay_status(rows, nm)
    except Exception:
        pass
    _live_save(); write(rows, LAST_ROWS["note"] + f"; live_guard {datetime.now(IST):%H:%M:%S}")
    return nclosed


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


def opt_expiry(rows, u: str = "NIFTY") -> str:
    """Nearest weekly option expiry of underlying u on/after DAY (scrip master)."""
    ex, pre = OPT_SPEC[u][:2]
    exps = sorted({r["SEM_EXPIRY_DATE"][:10] for r in rows if r["SEM_EXM_EXCH_ID"] == ex and r["SEM_INSTRUMENT_NAME"] == "OPTIDX"
                   and r["SEM_TRADING_SYMBOL"].startswith(pre) and r["SEM_EXPIRY_DATE"][:10] >= DAY})
    return exps[0]


def nifty_expiry(rows) -> str:
    return opt_expiry(rows, "NIFTY")


SM_ROWS = None
EXP = None   # NIFTY expiry (Q01 / pshadow use it)
EXPS = {}    # {underlying: expiry}
CUTOFF_TS = 2 ** 40
EXTRA_STRIKES = set()   # NIFTY strikes to keep fetching (open rows, Q01, pshadow)
EXTRA_STRIKES_U = {"NIFTY": EXTRA_STRIKES, "SENSEX": set()}
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
        EXPS["NIFTY"] = EXP
        try:   # a SENSEX scrip-master problem must never stop the NIFTY fetch
            EXPS["SENSEX"] = opt_expiry(SM_ROWS, "SENSEX")
        except (IndexError, KeyError):
            EXPS["SENSEX"] = None
    sm = SM_ROWS
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
        rs = get(51, "IDX_I", "INDEX", "IDX_SENSEX", "2026-08-20 09:15:00")
        if first or not (LIVE_RUN / "IDX_INDIAVIX.json").is_file():
            get(21, "IDX_I", "INDEX", "IDX_INDIAVIX", "2026-10-01 09:15:00")
        if not r or not r.get("close"):
            return f"from {src.name}, fetch FAILED (using backfill only)"
        sx_note = ""
        for u, ri in (("NIFTY", r), ("SENSEX", rs)):
            if not ri or not ri.get("close"):
                sx_note = " SENSEX index fetch FAILED"; continue
            ex, pre, seg, grid = OPT_SPEC[u]; band = BAND[u][0 if first else 1]; xu = EXPS.get(u)
            if not xu:
                sx_note += f" {u} expiry not in scrip master"; continue
            atm = round(float(ri["close"][-1]) / grid) * grid
            for row in sm:
                if (row["SEM_EXM_EXCH_ID"] == ex and row["SEM_INSTRUMENT_NAME"] == "OPTIDX" and row["SEM_TRADING_SYMBOL"].startswith(pre)
                        and row["SEM_EXPIRY_DATE"].startswith(xu)):
                    k = float(row["SEM_STRIKE_PRICE"])
                    if abs(k - atm) <= band or int(k) in EXTRA_STRIKES_U[u]:
                        get(row["SEM_SMST_SECURITY_ID"], seg, "OPTIDX", f"{u}_{xu}_{int(k)}_{row['SEM_OPTION_TYPE']}", f"{DAY} 09:15:00", True)
    return f"from {src.name if src else 'fresh'}, exp {EXP} sensex exp {EXPS.get('SENSEX')}, fetched {n} series to {to[11:16]} IST{sx_note}"


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
    env = dict(os.environ, PX_DAY=DAY, PX_EXP=EXP or DAY, PX_EXP_SENSEX=EXPS.get("SENSEX") or "",
               PX_CUTOFF_M=str(cut.hour * 60 + cut.minute) if cut else "")
    tape = REPO / "data" / "tape" / "v2" / DAY
    subprocess.run([str(VENV), "build_day.py", str(LIVE_RUN), str(tape), "work"], cwd=live, check=True, capture_output=True, timeout=120, env=env)
    out, lines = {}, []
    for u in UNDS:
        eu = dict(env, PX_UNDERLYING=u, PX_EXP=(EXP if u == "NIFTY" else EXPS.get(u)) or DAY)
        f = live / ("score_latest.csv" if u == "NIFTY" else f"score_latest_{u}.csv")
        if u != "NIFTY" and not EXPS.get(u):
            out[u] = None; lines.append(f"{u} skipped (no expiry)"); continue
        if u != "NIFTY" and f.exists():
            f.unlink()   # never re-book a stale SENSEX file if this cycle fails
        try:
            p = subprocess.run([str(VENV), "score_pass.py"], cwd=live, check=True, capture_output=True, timeout=180, text=True, env=eu)
            t = subprocess.run([str(VENV), str(REPO / "scripts" / "paper_extra" / "test_exit_fill.py"), str(f)],
                               capture_output=True, text=True, timeout=60, env=dict(eu, PX_RUN=str(LIVE_RUN)))
            if t.returncode != 0:  # fail closed: keep last good file, book nothing new
                raise RuntimeError("FILL_RULE_FAIL " + t.stdout.strip()[:300])
        except Exception:
            if u == "NIFTY":
                raise   # NIFTY behaviour unchanged: a NIFTY failure fails the cycle
            out[u] = None; lines.append(f"{u} score FAILED (no SENSEX rows this cycle)"); continue
        out[u] = list(csv.DictReader(open(f))); lines.append(p.stdout.strip().splitlines()[-1])
    return out, "; ".join(lines)


def rows_from(score_rows: list, u: str = "NIFTY") -> list:
    out = []
    for r in score_rows:
        rid = STRATS.get(r["strategy"])
        if not rid or r.get("signalled") != "Y" or r.get("status") not in ("OPEN", "CLOSED"):
            continue
        st = r["status"]
        out.append({
            "rule_id": rid, "strategy": r["strategy"], "underlying": u, "qty": QTY[u], "side": r["side"], "strike": float(r["strike"]),
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


def rows_all(score_by_u: dict) -> list:
    rows = []
    for u in UNDS:
        rows += rows_from(score_by_u.get(u) or [], u)
    return rows


def write(rows: list, note: str) -> None:
    # 2026-10-19 live fix: the desk loop (dual-tape process) books every non-CLOSED row in "rows" as open with the research_rules code it
    # loaded at start, so SKIPPED_CHASE / SKIPPED_CAP / SKIPPED_PREMIUM / PRE_START rows go to "not_booked", never to "rows". Live marks keep HH:MM in mark_time.
    keep = [r for r in rows if r.get("status") in ("OPEN", "CLOSED")]
    not_booked = [r for r in rows if r.get("status") not in ("OPEN", "CLOSED")]
    rows = keep
    OUT.parent.mkdir(parents=True, exist_ok=True)
    blob = {"day": DAY, "orders": "REFUSED", "paper_only": True, "as_of_ist": datetime.now(IST).isoformat(timespec="seconds"),
            "note": note, "strategies": sorted(set(STRATS.values())) + ["Q01_ITM100"], "underlyings": list(UNDS), "qty": QTY, "q01": dict(Q01_STATE), "rows": rows, "not_booked": not_booked}
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
    u = "NIFTY"   # Q01 v1.1 is a sealed NIFTY spec (NIFTY VIX filter, NIFTY open/S10); not run on SENSEX
    EXTRA_STRIKES.add(K)
    opt = _bars(f"NIFTY_{EXP}_{K}_{side}")
    rows, bg = [], None
    for variant in ("PLAIN", "T15"):
        r = q01.simulate(sg=sg, s10=s10, idx=idx, opt=opt, variant=variant, now_m=now_m)
        if r["status"] not in ("OPEN", "CLOSED"):
            continue
        closed = r["status"] == "CLOSED"
        row = {"rule_id": "Q01_ITM100" if variant == "PLAIN" else "Q01_T15", "strategy": "Q01_ITM100_v1.1" if variant == "PLAIN" else "Q01_T15",
               "underlying": u, "qty": QTY[u], "side": side, "strike": float(K), "signal_time": "10:00", "entry_time": r["entry_min"],
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
         "underlying": bg.get("underlying", "NIFTY"), "qty": QTY[bg.get("underlying", "NIFTY")], "net_inr_1_5x": None, "status": bg["status"], "stop_px": None, "target_px": bg["target_px"],
         "index_stop": bg["index_stop"], "stop_target_basis": bg["stop_target_basis"], "planned_exit_ist": bg["planned_exit_ist"],
         "verified": "SHADOW", "count_in_total": False}
    if bg["status"] == "CLOSED":
        sys.path.insert(0, str(REPO / "packages" / "desk-ml" / "src"))
        from desk_ml import research_rules as rr
        u = t["underlying"]
        c = rr._cost_row(entry=bg["entry_px"], exit_px=bg["exit_px"], qty=QTY[u], filled=True, underlying=u)
        t["net_inr_1_5x"] = round((bg["exit_px"] - bg["entry_px"]) * QTY[u] - float(c["charges_inr"]), 2)
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
             "underlying": r.get("underlying", "NIFTY"), "qty": QTY[r.get("underlying", "NIFTY")], "net_inr_1_5x": None, "status": st, "stop_px": r.get("stop_px"), "target_px": r.get("target_px"),
             "stop_target_basis": f"Premium levels on 1-min option CLOSES, stop checked first: stop = entry x (1-{r['S']}), target = entry + {r['k']} x {r['S']} x entry; "
                                  "fill = next minute OPEN - 0.05; else TIME at the cap.",
             "planned_exit_ist": hm(r.get("capm")), "note": r.get("note"), "data_through_ist": js.get("data_through"),
             "spec": PS_SPEC[name], "verified": "SHADOW", "count_in_total": False}
        if closed:
            sys.path.insert(0, str(REPO / "packages" / "desk-ml" / "src"))
            from desk_ml import research_rules as rr
            u = t["underlying"]   # pshadow specs are NIFTY-only today; this keeps qty/charges tied to the row's index
            c = rr._cost_row(entry=t["entry_px"], exit_px=t["exit_px"], qty=QTY[u], filled=True, underlying=u)
            t["net_inr_1_5x"] = round((t["exit_px"] - t["entry_px"]) * QTY[u] - float(c["charges_inr"]), 2)
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


# ---------------- regime tags + narrow-open shadow (2026-10-19, Sahil 1:1 02:29 CT). LOGGING ONLY ----------------
# Runs after admission/exits are final for the cycle; adds only the keys "regime" and "shadow_narrow_open" to each row and appends
# shadow_narrow_open_<day>.jsonl. Never changes status, prices, LIVE, CAP, PREM or START. Every step is wrapped: a failure logs, never stops.
try:
    import regime_tags as RG
except Exception as _e:   # a broken tag module must never stop the runner
    RG = None; _RG_ERR = f"{type(_e).__name__}: {_e}"
REG_MEMO = {}            # row key -> regime dict (frozen once complete: no missing fields)
REG_CTX = {}             # underlying -> (file mtime tuple, context)
SHADOW_FILE = OUT.parent / f"shadow_narrow_open_{DAY}.jsonl"
SHADOW_DONE = set()


def _vix_series() -> list:
    """Same read-only VIX sources as Q01: lab fixture history + prior-day closes in today's IDX_INDIAVIX.json (no file is written)."""
    out = []
    try:
        out += [[d, float(c)] for d, c in json.loads(VIX_HIST.read_text())]
    except (OSError, ValueError, TypeError):
        pass
    try:
        j = json.loads((LIVE_RUN / "IDX_INDIAVIX.json").read_text()); last = {}
        for t, c in zip(j["timestamp"], j["close"]):
            d = datetime.fromtimestamp(int(t), IST).strftime("%Y-%m-%d")
            if d < DAY:
                last[d] = float(c)
        have = {d for d, _ in out}; out += [[d, c] for d, c in sorted(last.items()) if d not in have]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return out


def _regime_ctx(u: str) -> dict:
    f = LIVE_RUN / f"IDX_{u}.json"; fv = LIVE_RUN / "IDX_INDIAVIX.json"
    key = tuple(x.stat().st_mtime if x.exists() else None for x in (f, fv, VIX_HIST))
    if u in REG_CTX and REG_CTX[u][0] == key:
        return REG_CTX[u][1]
    try:
        bars = RG.days_from_dhan(json.loads(f.read_text()))
    except (OSError, ValueError):
        bars = {}
    exp = (EXP if u == "NIFTY" else EXPS.get(u))
    try:
        pexp = prev_trading_day(DAY)
    except Exception:
        pexp = None
    ctx = RG.day_context(bars, DAY, _vix_series(), (exp == DAY) if exp else None, pexp)
    if not bars:
        ctx["missing"]["index"] = f"IDX_{u}.json missing or unreadable"
    REG_CTX[u] = (key, ctx)
    return ctx


def tag_rows(rows: list) -> str:
    if RG is None:
        return f"regime OFF ({_RG_ERR})"
    n = bad = 0
    for r in rows:
        try:
            k = (r.get("rule_id"), r.get("underlying") or "NIFTY", r.get("signal_time"))
            reg = REG_MEMO.get(k)
            if reg is None:
                sm = _m(r.get("signal_time"))
                reg = RG.tag_safe(_regime_ctx(r.get("underlying") or "NIFTY"), sm, r.get("side")) if sm is not None else \
                    {"version": RG.VERSION, "error": "no signal_time"}
                if not reg.get("missing") and not reg.get("error"):
                    REG_MEMO[k] = reg
            r["regime"] = reg; r["shadow_narrow_open"] = RG.narrow_shadow(reg); n += 1
            bad += bool(reg.get("error"))
        except Exception as e:   # never stop the cycle
            r["regime"] = {"version": RG.VERSION, "error": f"{type(e).__name__}: {e}"}; bad += 1
    return f"regime tagged {n}" + (f" ({bad} errors)" if bad else "")


def _net(e, x, q, u):
    try:
        if str(RT / "dhan" / "research" / "lab" / "lib") not in sys.path:
            sys.path.insert(0, str(RT / "dhan" / "research" / "lab" / "lib"))
        import costs
        return round(costs.net_at(float(e), float(x), int(q), u, DAY)[3], 2)
    except Exception:
        return None


def shadow_log(rows: list) -> str:
    """One line per booked trade when it closes: actual vs skip vs half size under the narrow-open rule (shadow only)."""
    if not SHADOW_DONE and SHADOW_FILE.exists():
        try:
            for line in SHADOW_FILE.read_text().splitlines():
                SHADOW_DONE.add(tuple(json.loads(line)["key"]))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    n = 0
    for r in rows:
        try:
            if r.get("status") != "CLOSED" or r.get("exit_px") is None:
                continue
            k = (r["rule_id"], r.get("underlying") or "NIFTY", r["signal_time"])
            if k in SHADOW_DONE:
                continue
            q = int(r["qty"]); h = q // 2; e, x = float(r["entry_px"]), float(r["exit_px"]); u = r.get("underlying") or "NIFTY"
            sh = r.get("shadow_narrow_open") or {}
            if not sh:
                continue
            act = dict(qty=q, gross_inr=round((x - e) * q, 2), net_inr_1_5x=_net(e, x, q, u))
            half = dict(qty=h, gross_inr=round((x - e) * h, 2), net_inr_1_5x=_net(e, x, h, u))
            rec = dict(day=DAY, key=list(k), entry_time=r.get("entry_time"), exit_time=r.get("exit_time"), entry_px=e, exit_px=x,
                       exit_reason=r.get("exit_reason"), regime=r.get("regime"), shadow=sh, actual=act,
                       under_skip=dict(qty=0, gross_inr=0.0, net_inr_1_5x=0.0), under_half=half,
                       if_rule_applied=(dict(qty=0, gross_inr=0.0, net_inr_1_5x=0.0) if sh.get("would_skip") else act),
                       if_half_applied=(half if sh.get("would_halve") else act), logged_ist=datetime.now(IST).isoformat(timespec="seconds"))
            with open(SHADOW_FILE, "a") as f:
                f.write(json.dumps(rec) + "\n")
            SHADOW_DONE.add(k); n += 1
        except Exception:
            continue
    return f"shadow_narrow_open +{n}"


def _regime_counts(blob: dict) -> dict:
    out = {}
    for grp, rows in (("booked", blob.get("rows") or []), ("not_booked", blob.get("not_booked") or [])):
        c = {"cell": {}, "or15": {}, "gap_bucket": {}, "expiry_day": {}}
        for r in rows:
            g = r.get("regime") or {}
            for f in c:
                v = str(g.get(f)); c[f][v] = c[f].get(v, 0) + 1
        c["narrow_would_skip"] = sum(1 for r in rows if (r.get("shadow_narrow_open") or {}).get("would_skip"))
        out[grp] = c
    return out


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
    # Every PX trade the paper-extra book still holds OPEN, including ones carried over a restart and ones
    # the desk's cap replay put in risk_blocked/guard_blocked/dup_same_contract (paper-extra trades every signal).
    try:
        _blob = json.loads(OUT.read_text()); pb = [r for r in (_blob.get("rows") or []) if r.get("status") == "OPEN"]
    except (OSError, ValueError):
        _blob, pb = {}, []
    try:
        _rc = _regime_counts(_blob)
    except Exception as e:   # logging only
        _rc = {"error": f"{type(e).__name__}: {e}"}
    pb_lots = {u: sum(int(r.get("qty") or 0) // LOT[u] for r in pb if r.get("underlying") == u) for u in ("NIFTY", "SENSEX")}
    pb_prem = round(sum(float(r.get("entry_px") or 0) * int(r.get("qty") or 0) for r in pb), 2)
    admitted = {(r.get("rule_id"), r.get("underlying") or ("SENSEX" if "-SENSEX-" in str(r.get("trade_id")) else "NIFTY"), r.get("entry_min")) for r in op}
    outside = [(r.get("rule_id"), r.get("underlying"), r.get("entry_time")) for r in pb
               if (r.get("rule_id"), r.get("underlying"), r.get("entry_time")) not in admitted]
    rec = {"ist": datetime.now(IST).isoformat(timespec="seconds"), "open_trades": len(op), "open_lots": lots,
           "premium_at_risk_inr": prem, "day_net_inr": rk.get("day_net_inr"), "halted_reason": rk.get("halted_reason"),
           "open": [(r.get("rule_id"), r.get("side"), r.get("entry_min")) for r in op],
           "book_open_trades": len(pb), "book_open_lots": pb_lots, "book_premium_at_risk_inr": pb_prem,
           "book_open": [(r.get("rule_id"), r.get("underlying"), r.get("side"), r.get("strike"), r.get("entry_time"), r.get("stop_px"))
                         for r in pb],
           "book_open_not_desk_admitted": outside, "regime_counts": _rc}
    with open(OUT.parent / f"risk_minutes_{DAY}.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    return (f"open {len(op)} lots {lots} prem_at_risk {prem} net {rk.get('day_net_inr')} halt {rk.get('halted_reason')}; "
            f"book open {len(pb)} lots {pb_lots} prem_at_risk {pb_prem}")


# ---------------- exit-status labels + shadow overlays (2026-10-19, Sahil "your decision" 02:58 CT). DISPLAY / LOGGING ONLY ----------------
# Runs after admission/exits are final for the cycle (and in each live-guard tick, before write). Adds only the keys "exit_status" (OPEN PX rows)
# and "shadow_overlays" (all booked PX rows), writes data/paper_extra/<day>/live_exits_status.json and appends shadow_overlays_<day>.jsonl.
# Never changes status, prices, LIVE, CAP, PREM or START; never read back by any decision. Every step is wrapped: a failure logs, never stops.
try:
    import shadow_overlays as SO
except Exception as _e:   # a broken overlay module must never stop the runner
    SO = None; _SO_ERR = f"{type(_e).__name__}: {_e}"
SO_FILE = OUT.parent / f"shadow_overlays_{DAY}.jsonl"
SO_STATUS_FILE = REPO / "data" / "paper_extra" / DAY / "live_exits_status.json"
SO_DONE = set()
SO_IDX = {}              # underlying -> (file mtime, {minute_index: (o, h, l, c)} for DAY)


def _so_idx(u: str) -> dict:
    f = LIVE_RUN / f"IDX_{u}.json"
    try:
        key = f.stat().st_mtime
    except OSError:
        return {}
    if u in SO_IDX and SO_IDX[u][0] == key:
        return SO_IDX[u][1]
    out = {}
    try:
        j = json.loads(f.read_text())
        for i, t in enumerate(j.get("timestamp") or []):
            try:
                dt = datetime.fromtimestamp(int(t), IST); k = dt.hour * 60 + dt.minute - 555
                if dt.strftime("%Y-%m-%d") == DAY and 0 <= k < 376:
                    out[k] = (float(j["open"][i]), float(j["high"][i]), float(j["low"][i]), float(j["close"][i]))
            except (KeyError, IndexError, TypeError, ValueError):
                continue
    except (OSError, ValueError):
        out = {}
    SO_IDX[u] = (key, out)
    return out


def _so_key(r):
    return (r["rule_id"], r.get("underlying") or "NIFTY", r["signal_time"])


def _so_status(r: dict, now_m: int) -> dict:
    u = r.get("underlying") or "NIFTY"; sg = 1 if r["side"] == "CE" else -1; em = _m(r["entry_time"]); p0 = float(r["entry_px"])
    ob = _opt_bars(u, r["strike"], r["side"]); ms = sorted(m for m in ob if em <= m <= now_m)
    px = r.get("mark_px"); mt = _m(r.get("mark_time")) if r.get("mark_time") else None
    if px is None:
        px, mt = (ob[ms[-1]][1], ms[-1]) if ms else (p0, em)
    mt = mt if mt is not None else now_m
    lt = LIVE.get(_so_key(r))
    peak = max([ob[m][1] for m in ms if m <= mt] + [p0, float(px)] + ([float(lt.hw)] if lt is not None and lt.last_bid is not None else []))
    p3 = ob[mt - 3][1] if (mt - 3) >= em - 1 and (mt - 3) in ob else None
    st = SO.status(p0, float(px), peak, p3, sg, _so_idx(u), mt - 555, _m(r["signal_time"]) - 555, held_min=mt - em)
    armed = peak >= p0 * (1 + PRICE_EXIT["stop"])
    st.update(price_now=float(px), price_time=_hm(mt), price_src=r.get("price_src"), entry_px=p0, stop_px=r.get("stop_px"), target_px=r.get("target_px"),
              trail_armed=armed, trail_px=round(max(p0, peak * (1 - PRICE_EXIT["stop"])), 2) if armed else None,
              trail_rule=r.get("trail") or "BE at +30%, then high-water x 0.70", updated_ist=datetime.now(IST).isoformat(timespec="seconds"))
    return st


def overlay_status(rows: list, now_m: int) -> int:
    """exit_status on OPEN PX rows (display only) + sidecar file. Returns rows labelled."""
    n = 0; side = []
    for r in rows:
        if not str(r.get("rule_id", "")).startswith("PX_"):
            continue
        if r.get("status") != "OPEN":
            r.pop("exit_status", None); continue
        try:
            r["exit_status"] = _so_status(r, now_m); n += 1
        except Exception as e:
            r["exit_status"] = {"version": getattr(SO, "VERSION", None), "label": None, "error": f"{type(e).__name__}: {e}", "display_only": True}
        side.append(dict(key=list(_so_key(r)), exit_status=r["exit_status"]))
    try:
        SO_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True); tmp = SO_STATUS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(side)); os.replace(tmp, SO_STATUS_FILE)
    except OSError:
        pass
    return n


def overlay_rows(rows: list, now_m: int) -> str:
    if SO is None:
        return f"overlays OFF ({_SO_ERR})"
    bad = 0; dr_in = []; info = {}
    booked = [r for r in rows if str(r.get("rule_id", "")).startswith("PX_") and r.get("status") in ("OPEN", "CLOSED")]
    for r in booked:
        try:
            u = r.get("underlying") or "NIFTY"; sg = 1 if r["side"] == "CE" else -1; em = _m(r["entry_time"]); sm = _m(r["signal_time"])
            p0 = float(r["entry_px"]); ob = _opt_bars(u, r["strike"], r["side"]); idx = _so_idx(u); exp = EXP if u == "NIFTY" else EXPS.get(u)
            tgt, tw, m30, eff = SO.ts_target(idx, sm, em, (exp == DAY) if exp else False)
            paths = {k: SO.path_1m(ob, em, p0, now_m, t) for k, t in (("base60_1m", 0.60), ("t50", 0.50), ("ts", tgt))} if em in ob else {}
            gb = None; xm = _m(r.get("exit_time")) if r.get("status") == "CLOSED" else None
            if xm is not None and r.get("exit_px") is not None:
                pk = max([ob[m][1] for m in ob if em <= m < xm] + [p0]); net = _net(p0, float(r["exit_px"]), int(r["qty"]), u)
                gb = bool(pk >= p0 * 1.15 and (net if net is not None else (float(r["exit_px"]) - p0)) < 0)
            ok, s10, vs = SO.dr_ok(idx, sm, sg)
            dr_in.append(dict(key=_so_key(r), entry_m=em, sig_m=sm, exit_m=xm, giveback=bool(gb), ok=ok, ok_s10=s10, ok_side=vs))
            info[_so_key(r)] = dict(ts_target=tgt, ts_reasons=tw, morning_move_bps=m30, morning_eff=eff, giveback=gb,
                                    paths={k: {kk: (round(vv, 2) if kk == "hw" else vv) for kk, vv in v.items()} for k, v in paths.items()})
        except Exception as e:
            info[_so_key(r)] = {"error": f"{type(e).__name__}: {e}"}; bad += 1
    try:
        fl = SO.dr_flags(dr_in)
    except Exception as e:
        fl = {}; bad += 1
    for r in booked:
        k = _so_key(r); d = dict(info.get(k) or {}); d["dr"] = fl.get(k); d["version"] = SO.VERSION; d["shadow_only"] = True
        r["shadow_overlays"] = d
    try:
        nl = overlay_status(rows, now_m)
    except Exception as e:
        nl = 0; bad += 1
    return f"overlays {len(booked)} status {nl}" + (f" ({bad} errors)" if bad else "")


def _leg(p0, x, q, u):
    return dict(exit_px=x, gross_inr=round((float(x) - p0) * q, 2), net_inr_1_5x=_net(p0, float(x), q, u)) if x is not None else None


def overlay_log(rows: list, now_m: int) -> str:
    """One line per booked PX trade once it AND its three 1m shadow paths are closed (or after 15:18 IST)."""
    if SO is None:
        return "shadow_overlays OFF"
    if not SO_DONE and SO_FILE.exists():
        try:
            for line in SO_FILE.read_text().splitlines():
                SO_DONE.add(tuple(json.loads(line)["key"]))
        except (OSError, ValueError, KeyError, TypeError):
            pass
    n = 0
    for r in rows:
        try:
            if not str(r.get("rule_id", "")).startswith("PX_") or r.get("status") != "CLOSED" or r.get("exit_px") is None:
                continue
            k = _so_key(r)
            if k in SO_DONE:
                continue
            so = r.get("shadow_overlays") or {}; P = so.get("paths") or {}
            if so.get("error") or (any((P.get(x) or {}).get("status") != "CLOSED" for x in ("base60_1m", "t50", "ts")) and now_m < 918):
                continue
            u = r.get("underlying") or "NIFTY"; p0 = float(r["entry_px"]); q = int(r["qty"])
            act = _leg(p0, r["exit_px"], q, u); act.update(exit_time=r.get("exit_time"), why=r.get("exit_reason"))
            legs = {}
            for x in ("base60_1m", "t50", "ts"):
                v = P.get(x) or {}
                legs[x] = _leg(p0, v.get("exit_px"), q, u) if v.get("status") == "CLOSED" else None
                if legs[x]:
                    legs[x].update(exit_time=_hm(v["exit_m"]), why=v.get("why"))
            dr = so.get("dr") or {}
            rec = dict(day=DAY, key=list(k), entry_time=r.get("entry_time"), entry_px=p0, qty=q, actual=act, **legs, ts_target=so.get("ts_target"),
                       ts_reasons=so.get("ts_reasons"), giveback=so.get("giveback"), dr=dr,
                       if_dr_applied=(dict(exit_px=None, gross_inr=0.0, net_inr_1_5x=0.0) if dr.get("would_skip") else act),
                       version=so.get("version"), shadow_only=True, logged_ist=datetime.now(IST).isoformat(timespec="seconds"))
            with open(SO_FILE, "a") as f:
                f.write(json.dumps(rec) + "\n")
            SO_DONE.add(k); n += 1
        except Exception:
            continue
    return f"shadow_overlays +{n}"


def once() -> str:
    f = fetch()
    sr, line = score()
    now_m = (datetime.now(IST) - timedelta(minutes=1)).hour * 60 + (datetime.now(IST) - timedelta(minutes=1)).minute
    rows = cap_and_price(rows_all(sr), now_m)
    rows = [r for r in rows if r["status"] in ("OPEN", "CLOSED", "SKIPPED_CHASE", "SKIPPED_CAP", "SKIPPED_PREMIUM", "PRE_START")]   # PRE_START kept visible in OUT, never booked
    _live_save()
    for r in rows:
        if r["status"] == "OPEN":
            EXTRA_STRIKES_U[r["underlying"]].add(int(r["strike"]))
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
    try:   # logging only, after every admission/exit decision of this cycle
        rtxt = tag_rows(rows)
    except Exception as e:
        rtxt = f"regime ERROR {type(e).__name__}: {e}"
    try:   # display/logging only, after every admission/exit decision of this cycle
        rtxt += "; " + overlay_rows(rows, now_m)
    except Exception as e:
        rtxt += f"; overlays ERROR {type(e).__name__}: {e}"
    write(rows, f"{f}; {line}; {qtxt}; {ptxt}"); LAST_ROWS.update(rows=rows, note=f"{f}; {line}; {qtxt}; {ptxt}")
    try:
        rtxt += "; " + shadow_log(rows)
    except Exception as e:
        rtxt += f"; shadow ERROR {type(e).__name__}: {e}"
    try:
        rtxt += "; " + overlay_log(rows, now_m)
    except Exception as e:
        rtxt += f"; overlay log ERROR {type(e).__name__}: {e}"
    line = f"{line}; {qtxt}; {ptxt}; {rtxt}"
    return f"{datetime.now(IST):%H:%M:%S} IST {f}; {line}; px rows {len(rows)}; {log_risk()}"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "loop":
        start = datetime.now(IST).replace(hour=9, minute=16, second=5, microsecond=0)
        if datetime.now(IST) < start:  # first complete 1m bar is 09:15
            print(f"{datetime.now(IST):%H:%M:%S} IST waiting for 09:16:05 IST (day {DAY})", flush=True)
            time.sleep((start - datetime.now(IST)).total_seconds())
        _live_load(); _n = datetime.now(IST) - timedelta(minutes=1); _start_load(_n.hour * 60 + _n.minute); _cap_load(_n.hour * 60 + _n.minute); _prem_load(_n.hour * 60 + _n.minute)
        while datetime.now(IST).strftime("%H:%M") < "15:31":
            t = time.time()
            try:
                print(once(), flush=True)
            except Exception as e:  # keep last good file; desk keeps running
                print(f"{datetime.now(IST):%H:%M:%S} IST CYCLE_ERROR {type(e).__name__}: {e}", flush=True)
            while time.time() - t < max(5, 60 - PRICE_EXIT["live_poll_s"]):   # live depth guard every ~3 s until the next cycle
                try:
                    n = guard_tick()
                    if n:
                        print(f"{datetime.now(IST):%H:%M:%S} IST live_guard closed {n}", flush=True)
                except Exception as e:  # live guard must never stop the cycle; 1m fallback still applies
                    print(f"{datetime.now(IST):%H:%M:%S} IST LIVE_GUARD_ERROR {type(e).__name__}: {e}", flush=True)
                time.sleep(PRICE_EXIT["live_poll_s"])
    else:
        _live_load(); _n = datetime.now(IST) - timedelta(minutes=1); _start_load(_n.hour * 60 + _n.minute); print(once())
