"""Read-only feed for the Desk / Founder pages: one compact snapshot, day history, decision trace.

Sources, all read-only (this module never writes a file and never calls a broker):
- paper board ``data/recon/ml_paper_dashboard.json`` (static mock copy as fallback);
- dual tape ``data/recon/paper_watch/DUAL-TAPE/<day>.jsonl`` for the index spot at entry;
- model log ``data/recon/ml_paper_model_logs.jsonl`` (+ ``archive/*.pre_slate``): OPEN / CLOSE /
  TRAIL_STOP / TARGET_LOCK_SHIFT per trade, so history survives the daily board reset;
- ledger ``data/ledger/ledger.sqlite`` (opened ``mode=ro``) when the event path has written one;
- health monitor ``data/health/status.json`` + ``alerts.jsonl`` and paper-ops status files.

Missing sources give ``None`` / ``NO_DATA``: the UI shows "-" or a grey step, never an invented number.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time as _time
from bisect import bisect_right
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[4]
IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)
MAX_SPOT_GAP_S = 180
TRADE_KEYS = ("closed_trades", "open_trades", "tickets", "closed_trades_sample")
MODEL_LOG = "ml_paper_model_logs.jsonl"
TRADE_EVENTS = {"OPEN", "CLOSE", "TRAIL_STOP", "TARGET_LOCK_SHIFT", "CANCEL_ELIGIBLE"}
TID_TS = re.compile(r"-(\d{9,11})-(CE|PE)$")
SEVERITY_RANK = {"EMERGENCY": 0, "CRITICAL": 1, "WARNING": 2, "INFO": 3}
BOARD_KEYS = (
    "ok", "live_session", "session_ist_date", "as_of_ist", "title", "source", "starting_desk_inr",
    "capital_plan", "overall_pnl_inr", "overall_gross_pnl_inr", "overall_charges_inr", "win_rate_net_pct",
    "last_index_regime", "book_rank", "closed_trades", "open_trades", "heartbeat", "orders", "promote",
)


# ---------- small cached readers ----------

_JSON: dict[str, tuple[tuple[int, int], Any]] = {}
_TAIL: dict[str, int] = {}


def _stamp(path: Path) -> Optional[tuple[int, int]]:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def read_json(path: Path) -> Any:
    """Parse once per (mtime, size). Callers must not mutate the result except via load_board."""
    stamp = _stamp(path)
    if stamp is None:
        return None
    hit = _JSON.get(str(path))
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    _JSON[str(path)] = (stamp, blob)
    return blob


def new_rows(path: Path, needles: tuple[bytes, ...] = (), budget_s: Optional[float] = None) -> tuple[list[dict[str, Any]], bool, bool]:
    """Rows appended to a JSONL file since the last call, streamed from the saved byte offset.

    Only lines containing one of ``needles`` are JSON-parsed (the model log is mostly SKIP/HOLD
    rows nobody here reads). ``budget_s`` caps the time spent, so a cold 200 MB log is indexed
    over several snapshots instead of blocking one. Returns ``(rows, reset, complete)``: ``reset``
    is True on the first read or when the file shrank or vanished, so callers drop their cache.
    """
    key = str(path)
    stamp = _stamp(path)
    if stamp is None:
        return [], _TAIL.pop(key, None) is not None, True
    size = stamp[1]
    reset = key not in _TAIL or size < _TAIL[key]
    offset = 0 if reset else _TAIL[key]
    rows: list[dict[str, Any]] = []
    deadline = None if budget_s is None else _time.monotonic() + budget_s
    if size > offset:
        with path.open("rb") as fh:
            fh.seek(offset)
            for n, line in enumerate(fh, 1):
                if not line.endswith(b"\n"):
                    break  # half-written last line: picked up next call
                offset += len(line)
                if not needles or any(x in line for x in needles):
                    try:
                        row = json.loads(line)
                    except ValueError:
                        row = None
                    if isinstance(row, dict):
                        rows.append(row)
                if deadline is not None and n % 2048 == 0 and _time.monotonic() > deadline:
                    break
    _TAIL[key] = offset
    return rows, reset, offset >= size


def ts_of(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        val = float(raw)
        return int(val / 1000 if val > 1e12 else val)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return int((dt if dt.tzinfo else dt.replace(tzinfo=IST)).timestamp())


def ist_iso(ts: Optional[int]) -> Optional[str]:
    return datetime.fromtimestamp(ts, IST).isoformat(timespec="seconds") if ts else None


def in_market_hours(now: datetime) -> bool:
    now = now.astimezone(IST)
    return now.weekday() < 5 and MARKET_OPEN <= now.time() <= MARKET_CLOSE


# ---------- spot at entry (dual tape) ----------

_SPOTS: dict[str, dict[str, tuple[list[int], list[float]]]] = {}
_TAPE_DONE: dict[str, bool] = {}


def _tape_series(path: Path, budget_s: Optional[float] = None) -> dict[str, tuple[list[int], list[float]]]:
    rows, reset, done = new_rows(path, budget_s=budget_s)
    _TAPE_DONE[str(path)] = done
    if reset:
        _SPOTS[str(path)] = {}
    series = _SPOTS.setdefault(str(path), {})
    for row in rows:
        row_ts = ts_of(row.get("as_of_ist"))
        for snap in row.get("underlyings") or []:
            if not isinstance(snap, dict):
                continue
            try:
                idx = float(snap["index_ltp"])
            except (KeyError, TypeError, ValueError):
                continue
            ts = ts_of(snap.get("as_of_ist")) or row_ts
            if ts is None:
                continue
            tss, idxs = series.setdefault(str(snap.get("underlying") or "").upper(), ([], []))
            i = bisect_right(tss, ts)
            tss.insert(i, ts)
            idxs.insert(i, idx)
    return series


def spot_at(tape_dir: Path, underlying: Any, opened: Any, budget_s: Optional[float] = None) -> Optional[float]:
    ts = ts_of(opened)
    if ts is None or not underlying:
        return None
    day = datetime.fromtimestamp(ts, IST).date().isoformat()
    path = tape_dir / f"{day}.jsonl"
    tss, idxs = _tape_series(path, budget_s).get(str(underlying).upper(), ([], []))
    if not _TAPE_DONE.get(str(path)) and (not tss or tss[-1] < ts):
        return None  # tape not indexed up to the entry yet: answer on a later call, never a stale print
    i = bisect_right(tss, ts) - 1
    if i < 0 or ts - tss[i] > MAX_SPOT_GAP_S:
        return None
    return idxs[i]


def attach_entry_spots(blob: dict[str, Any], tape_dir: Path, budget_s: Optional[float] = None) -> dict[str, Any]:
    """Fill missing ``spot_at_entry`` in place. Open tickets carry ``idx_at_open``; closed ones use the tape."""
    deadline = None if budget_s is None else _time.monotonic() + budget_s
    for key in TRADE_KEYS:
        for t in blob.get(key) or []:
            if not isinstance(t, dict) or t.get("spot_at_entry") is not None:
                continue
            if t.get("idx_at_open") is not None:
                t["spot_at_entry"], t["spot_at_entry_src"] = t["idx_at_open"], "OPEN_TICKET"
                continue
            if not tape_dir.is_dir():
                continue
            left = None if deadline is None else max(0.0, deadline - _time.monotonic())
            spot = spot_at(tape_dir, t.get("underlying"), t.get("opened_ts") or t.get("opened_ist"), left)
            if spot is not None:
                t["spot_at_entry"], t["spot_at_entry_src"] = spot, "DUAL-TAPE"
    return blob


# ---------- sources ----------


def load_board(root: Path = REPO, budget_s: Optional[float] = None) -> Optional[dict[str, Any]]:
    recon = root / "data" / "recon" / "ml_paper_dashboard.json"
    mock = root / "apps" / "web" / "public" / "mock" / "ml_paper_dashboard.json"
    blob = read_json(recon if recon.is_file() else mock)
    if not isinstance(blob, dict):
        return None
    blob.setdefault("orders", "REFUSED")
    blob.setdefault("promote", False)
    blob.setdefault("win_rate", None)
    attach_entry_spots(blob, root / "data" / "recon" / "paper_watch" / "DUAL-TAPE", budget_s)
    return blob


_EVENTS: dict[str, dict[str, list[dict[str, Any]]]] = {}
_EVENT_NEEDLES = tuple(f'"event": "{e}"'.encode() for e in sorted(TRADE_EVENTS))
SESSION_WRITE_END = time(15, 40)


_EVENTS_LOCK = threading.Lock()
_EVENTS_VIEW: dict[str, tuple[dict[str, list[dict[str, Any]]], bool]] = {}


def _index_events(root: Path, budget_s: Optional[float]) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    recon = root / "data" / "recon"
    files = [recon / MODEL_LOG, *sorted((recon / "archive").glob(f"{MODEL_LOG}.*"))]
    merged: dict[str, list[dict[str, Any]]] = {}
    complete = True
    deadline = None if budget_s is None else _time.monotonic() + budget_s
    for path in files:
        left = None if deadline is None else max(0.0, deadline - _time.monotonic())
        rows, reset, done = new_rows(path, _EVENT_NEEDLES, left)
        complete = complete and done
        if reset:
            _EVENTS[str(path)] = {}
        acc = _EVENTS.setdefault(str(path), {})
        for r in rows:
            tid = r.get("trade_id")
            if tid and r.get("event") in TRADE_EVENTS:
                acc.setdefault(str(tid), []).append(r)
        for tid, evs in acc.items():
            merged.setdefault(tid, []).extend(evs)
    return merged, complete


def trade_events(root: Path = REPO, budget_s: Optional[float] = None, *, wait: bool = True
                 ) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    """trade_id -> model-log events (live file + archived pre-slate copies), and whether indexing is complete.

    ``wait=False`` never blocks: while the start-up warmer holds the index, the caller gets the
    last published view with ``complete=False`` (the UI then shows "Indexing history…").
    """
    if not _EVENTS_LOCK.acquire(blocking=wait):
        return _EVENTS_VIEW.get(str(root), ({}, False))[0], False
    try:
        view = _index_events(root, budget_s)
        _EVENTS_VIEW[str(root)] = view
        return view
    finally:
        _EVENTS_LOCK.release()


def warm_history(root: Path = REPO) -> bool:
    """Index the whole model log in one go (run once in a background thread at API start)."""
    return trade_events(root, None, wait=True)[1]


def start_history_warmer(root: Path = REPO) -> threading.Thread:
    thread = threading.Thread(target=warm_history, args=(root,), name="ui-feed-history-warmer", daemon=True)
    thread.start()
    return thread


def live_write(row: dict[str, Any], opened_ts: Optional[int], max_after_s: int) -> bool:
    """Was this model-log row written by the live paper loop for this trade?

    The log also holds replay runs, and its rows carry no replay tag. A live row is written on the
    trade's own IST day, before the session ends, and within ``max_after_s`` of the entry.
    ponytail: a replay of today's tape run during market hours inside the hold window still passes;
    ceiling = rare same-session replays; upgrade = the engine writes a mode on every row.
    """
    ts = ts_of(row.get("ts_ist"))
    if ts is None or opened_ts is None:
        return False
    wrote, opened = datetime.fromtimestamp(ts, IST), datetime.fromtimestamp(opened_ts, IST)
    return wrote.date() == opened.date() and wrote.time() <= SESSION_WRITE_END and opened_ts - 120 <= ts <= opened_ts + max_after_s


def _ledger(root: Path) -> Optional[sqlite3.Connection]:
    path = root / "data" / "ledger" / "ledger.sqlite"
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=0.5)
    conn.row_factory = sqlite3.Row
    return conn


def _ledger_query(root: Path, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    try:
        conn = _ledger(root)
    except sqlite3.Error:
        return []
    if conn is None:
        return []
    try:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def founder_book(root: Path = REPO) -> dict[str, Any]:
    blob = read_json(root / "data" / "recon" / "founder_trade_underlyings.json")
    names = [str(n).upper() for n in (blob or {}).get("trade_underlyings") or []]
    known = ("NIFTY", "BANKNIFTY", "SENSEX")
    return {
        "source": "file" if blob else "default",
        "index_status": {n: ("START" if n in names else "STOP") for n in known},
        "as_of_ist": (blob or {}).get("as_of_ist"),
    }


def risk_halt(root: Path, days: set[str]) -> Optional[dict[str, Any]]:
    """Desk MTM halt (``data/desk/live_loop/mtm_halt.json``) for one of ``days``. A file the desk
    cannot parse makes it block every entry, so an unreadable file is reported as active."""
    path = root / "data" / "desk" / "live_loop" / "mtm_halt.json"
    if not path.is_file():
        return None
    blob = read_json(path)
    if not isinstance(blob, dict):
        return {"active": True, "session": None, "reason": "halt file unreadable — the desk blocks every new entry (fail closed)"}
    if blob.get("session") not in days:
        return None
    halt_ts = ts_of(blob.get("halt_ts"))
    return {
        "active": True,
        "session": blob.get("session"),
        "halt_ist": ist_iso(halt_ts),
        "reason": blob.get("reason") or "MTM halt",
        "kinds": blob.get("kinds") or [],
        "forced_closes": len(blob.get("forced_closes") or []),
    }


# ---------- history ----------


def _opened_ts(t: dict[str, Any]) -> Optional[int]:
    ts = ts_of(t.get("opened_ts")) or ts_of(t.get("opened_ist"))
    if ts:
        return ts
    m = TID_TS.search(str(t.get("trade_id") or ""))
    return int(m.group(1)) if m else None


def _row_from_log(tid: str, evs: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Rebuild a closed trade from live-written OPEN / CLOSE rows only (replay rows are skipped)."""
    ts = _opened_ts({"trade_id": tid})
    close = next((e for e in evs if e.get("event") == "CLOSE" and live_write(e, ts, 3 * 3600)), None)
    if close is None:
        return None
    opened = next((e for e in evs if e.get("event") == "OPEN" and live_write(e, ts, 15 * 60)), {})
    entry = opened.get("limit") if opened.get("limit") is not None else close.get("limit")
    pts = close.get("pnl_points")
    exit_px = round(float(entry) + float(pts), 4) if entry is not None and pts is not None else None
    return {
        "trade_id": tid,
        "book_id": close.get("book_id") or close.get("model"),
        "underlying": close.get("underlying"),
        "side": close.get("side"),
        "atm_strike": close.get("strike"),
        "strike_source": opened.get("strike_source"),
        "entry": entry,
        "exit": exit_px,
        "stop": close.get("stop"),
        "target": close.get("target"),
        "lots": opened.get("lots"),
        "lot_size": opened.get("lot_size"),
        "notional_inr": opened.get("notional_inr"),
        "realized_pnl": pts,
        "gross_pnl_inr": close.get("gross_pnl_inr"),
        "charges_inr": close.get("charges_inr"),
        "realized_pnl_inr": close.get("pnl_inr"),
        "exit_reason": close.get("exit_reason"),
        "status": close.get("status"),
        "filled": close.get("filled"),
        "target_step": close.get("target_step"),
        "index_regime": opened.get("index_regime"),
        "justification": close.get("justification") or opened.get("justification"),
        "opened_ts": ts,
        "opened_ist": ist_iso(ts),
        "source": "model_log (live)",
    }


def _row_from_ledger(r: dict[str, Any]) -> dict[str, Any]:
    ts = ts_of(r.get("entry_time"))
    return {
        "trade_id": r.get("trade_id"),
        "underlying": r.get("symbol"),
        "side": r.get("direction"),
        "entry": r.get("entry_price"),
        "exit": r.get("exit_price"),
        "gross_pnl_inr": r.get("gross_pnl"),
        "charges_inr": r.get("charges"),
        "realized_pnl_inr": r.get("net_pnl"),
        "exit_reason": r.get("exit_reason") or r.get("cancel_reason"),
        "entry_slippage": r.get("entry_slippage"),
        "exit_slippage": r.get("exit_slippage"),
        "opened_ts": ts,
        "opened_ist": ist_iso(ts),
        "closed_ist": r.get("exit_time"),
        "day": r.get("day"),
        "filled": True,
        "source": "ledger",
    }


def _day(t: dict[str, Any]) -> Optional[str]:
    if t.get("day"):
        return str(t["day"])
    ts = _opened_ts(t)
    return datetime.fromtimestamp(ts, IST).date().isoformat() if ts else None


def history_rows(root: Path = REPO, board: Optional[dict[str, Any]] = None,
                 events: Optional[dict[str, list[dict[str, Any]]]] = None) -> list[dict[str, Any]]:
    """Every closed paper trade we have a record of, one row per book, newest first.

    Source of truth per IST day, first match wins: the paper board for its own session day, then the
    event-path ledger, then live-written model-log rows. A lower source never adds trades to a day a
    higher one already covers, so a replay in the model log cannot inflate a day the board owns.
    """
    board = board if board is not None else load_board(root) or {}
    rows: dict[str, dict[str, Any]] = {}
    for t in board.get("closed_trades") or []:
        if t.get("trade_id"):
            rows[str(t["trade_id"])] = {**t, "source": "board"}
    owned = {_day(t) for t in rows.values()} - {None}
    ledger_rows = _ledger_query(root, "SELECT * FROM trades WHERE status = 'CLOSED'")
    for r in ledger_rows:
        tid = str(r.get("trade_id") or "")
        if tid in rows:
            rows[tid].setdefault("entry_slippage", r.get("entry_slippage"))
            rows[tid].setdefault("exit_slippage", r.get("exit_slippage"))
        elif tid and r.get("day") not in owned:
            rows[tid] = _row_from_ledger(r)
    owned |= {r.get("day") for r in ledger_rows if r.get("day")}
    for tid, evs in (events if events is not None else trade_events(root)[0]).items():
        if tid in rows:
            continue
        row = _row_from_log(tid, evs)
        if row and _day(row) not in owned:
            rows[tid] = row
    out = []
    for r in rows.values():
        r["day"] = _day(r)
        out.append(r)
    out.sort(key=lambda r: _opened_ts(r) or 0, reverse=True)
    return out


def _fill_key(t: dict[str, Any]) -> tuple:
    return (_opened_ts(t), t.get("underlying"), t.get("side"), t.get("atm_strike"), t.get("entry"), t.get("exit_reason"))


def _scored(t: dict[str, Any]) -> bool:
    return t.get("filled") is not False and t.get("realized_pnl_inr") is not None


def day_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per IST day: unique fills (book clones counted once) plus per-book and per-exit-reason splits."""
    days: dict[str, dict[str, Any]] = {}
    seen: set[tuple] = set()
    for t in rows:
        if not t.get("day") or not _scored(t):
            continue
        d = days.setdefault(t["day"], {"day": t["day"], "n": 0, "wins": 0, "gross": 0.0, "charges": 0.0,
                                        "net": 0.0, "by_book": {}, "by_reason": {}})
        net = float(t.get("realized_pnl_inr") or 0)
        book = d["by_book"].setdefault(str(t.get("book_id") or "UNKNOWN"), {"n": 0, "wins": 0, "net": 0.0})
        book["n"] += 1
        book["wins"] += net > 0
        book["net"] = round(book["net"] + net, 2)
        key = _fill_key(t)
        if key in seen:
            continue
        seen.add(key)
        d["n"] += 1
        d["wins"] += net > 0
        d["gross"] = round(d["gross"] + float(t.get("gross_pnl_inr") or 0), 2)
        d["charges"] = round(d["charges"] + float(t.get("charges_inr") or 0), 2)
        d["net"] = round(d["net"] + net, 2)
        reason = d["by_reason"].setdefault(str(t.get("exit_reason") or t.get("status") or "UNKNOWN"),
                                           {"n": 0, "gross": 0.0, "charges": 0.0, "net": 0.0})
        reason["n"] += 1
        reason["gross"] = round(reason["gross"] + float(t.get("gross_pnl_inr") or 0), 2)
        reason["charges"] = round(reason["charges"] + float(t.get("charges_inr") or 0), 2)
        reason["net"] = round(reason["net"] + net, 2)
    return sorted(days.values(), key=lambda d: d["day"], reverse=True)


def account(board: dict[str, Any], days: list[dict[str, Any]]) -> dict[str, Any]:
    plan = board.get("capital_plan") or {}
    start = plan.get("desk_capital_inr") or board.get("starting_desk_inr")
    gross = round(sum(d["gross"] for d in days), 2)
    charges = round(sum(d["charges"] for d in days), 2)
    net = round(sum(d["net"] for d in days), 2)
    return {
        "starting_capital_inr": start,
        "gross_inr": gross,
        "charges_inr": charges,
        "net_inr": net,
        "equity_inr": round(float(start) + net, 2) if start is not None else None,
        "n_days": len(days),
        "first_day": days[-1]["day"] if days else None,
        "last_day": days[0]["day"] if days else None,
        "funds_editable": False,
        "funds_note": "Add funds / minimum capital need an engine-side setting. Coming in the controls PR.",
    }


# ---------- health + alerts ----------


def _age(now: datetime, iso: Any) -> Optional[int]:
    ts = ts_of(iso)
    return int(now.timestamp() - ts) if ts else None


def _fmt_age(sec: Optional[int]) -> str:
    if sec is None:
        return "never"
    if sec < 120:
        return f"{sec}s ago"
    if sec < 7200:
        return f"{sec // 60} min ago"
    if sec < 172800:
        return f"{sec // 3600} h ago"
    return f"{sec // 86400} d ago"


def tape_last(board: dict[str, Any]) -> Optional[str]:
    lasts = sorted(str((s or {}).get("span_ist", {}).get("last")) for s in (board.get("steps") or {}).values()
                   if (s or {}).get("span_ist", {}).get("last"))
    return lasts[-1] if lasts else board.get("as_of_ist")


def _news_times(blob: Any, out: list[int], depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(blob, dict):
        if blob.get("headline") and blob.get("time_ist"):
            ts = ts_of(blob["time_ist"])
            if ts:
                out.append(ts)
        for v in blob.values():
            _news_times(v, out, depth + 1)
    elif isinstance(blob, list):
        for v in blob:
            _news_times(v, out, depth + 1)


def latest_news_ts(root: Path, max_files: int = 8, max_bytes: int = 5_000_000) -> Optional[int]:
    """Newest ``time_ist`` of any news item (``headline`` + ``time_ist``) in the latest desk-intel JSON files."""
    folder = root / "data" / "desk_intel"
    if not folder.is_dir():
        return None
    files = sorted((p for p in folder.rglob("*.json") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    times: list[int] = []
    for path in files[:max_files]:
        if path.stat().st_size <= max_bytes:
            _news_times(read_json(path), times)
    return max(times, default=None)


def _row(rid: str, name: str, tone: str, detail: str, age: Optional[int] = None) -> dict[str, Any]:
    return {"id": rid, "name": name, "tone": tone, "detail": detail, "age_s": age}


def health_rows(root: Path, board: dict[str, Any], fstatus: dict[str, Any], hstatus: dict[str, Any], now: datetime,
                halt: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    market = in_market_hours(now)
    checks = hstatus.get("checks") or {}
    agents = {a.get("id"): a for a in fstatus.get("agents") or []}
    rows = [_row("api", "API", "green", "answering this request", 0)]

    loop = agents.get("paper-loop") or {}
    if loop.get("alive"):
        rows.append(_row("paper", "Paper loop", "green", "running"))
    else:
        rows.append(_row("paper", "Paper loop", "red" if market else "grey",
                         f"not running{'' if market else ' (market closed)'}"))

    recon = checks.get("reconciliation") or {}
    if recon and not recon.get("ok", True):
        rows.append(_row("broker", "Broker (paper)", "red", recon.get("message") or "reconciliation mismatch"))
    else:
        rows.append(_row("broker", "Broker (paper)", "green", "paper broker · orders refused · no live connection"))

    last = tape_last(board)
    age = _age(now, last)
    recorder = checks.get("recorder") or {}
    if recorder and not recorder.get("ok", True):
        rows.append(_row("data", "Market data", "red", recorder.get("message") or "recorder stale", age))
    elif not market:
        rows.append(_row("data", "Market data", "grey", f"market closed · last tape tick {_fmt_age(age)}", age))
    elif age is None or age > 300:
        rows.append(_row("data", "Market data", "red", f"stale · last tape tick {_fmt_age(age)}", age))
    elif age > 60:
        rows.append(_row("data", "Market data", "amber", f"slow · last tape tick {_fmt_age(age)}", age))
    else:
        rows.append(_row("data", "Market data", "green", f"fresh · last tape tick {_fmt_age(age)}", age))

    veto = hstatus.get("latest_entry_veto") or {}
    if halt:
        rows.append(_row("risk", "Risk / halt", "red", f"HALT · {halt['reason']}"))
    elif veto:
        rows.append(_row("risk", "Risk / halt", "amber", f"last entry vetoed: {veto.get('reason_code')}"))
    else:
        rows.append(_row("risk", "Risk / halt", "green", "no halt, no vetoed entry today"))

    db = root / "data" / "ledger" / "ledger.sqlite"
    if not db.is_file():
        rows.append(_row("db", "Database", "grey", "no ledger.sqlite yet (event path off)"))
    else:
        try:
            conn = _ledger(root)
            n = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0] if conn else 0
            if conn:
                conn.close()
            rows.append(_row("db", "Database", "green", f"ledger readable · {n} trades"))
        except sqlite3.Error as exc:
            rows.append(_row("db", "Database", "red", f"ledger unreadable: {type(exc).__name__}"))

    llm = agents.get("llm-agents") or {}
    rows.append(_row("llm", "LLM", "green" if llm.get("alive") else "grey", str(llm.get("detail") or "off / rules-only")))

    newest = latest_news_ts(root)
    if newest is None:
        rows.append(_row("news", "News", "grey", "no news items on disk"))
    else:
        n_age = int(now.timestamp() - newest)
        rows.append(_row("news", "News", "green" if n_age < 86400 else "amber", f"newest news item {_fmt_age(n_age)}", n_age))

    backend = os.environ.get("EVENT_BUS_BACKEND", "memory")
    rows.append(_row("queue", "Queue", "grey", f"{backend} event bus in the paper process (no external queue to probe)"))

    beat = (board.get("heartbeat") or {}).get("as_of_ist") or board.get("as_of_ist")
    b_age = _age(now, beat)
    tone = "grey" if not market else ("green" if (b_age or 10**9) <= 60 else "amber" if (b_age or 10**9) <= 300 else "red")
    rows.append(_row("heartbeat", "Last heartbeat", tone, f"board written {_fmt_age(b_age)}", b_age))

    h_age = _age(now, hstatus.get("as_of"))
    if not hstatus:
        rows.append(_row("monitor", "Health monitor", "grey", "not running (python -m health)"))
    else:
        rows.append(_row("monitor", "Health monitor", "green" if (h_age or 0) < 300 else "amber", f"last run {_fmt_age(h_age)}", h_age))
    return rows


def alert_list(board: dict[str, Any], rows: list[dict[str, Any]], hstatus: dict[str, Any],
               halerts: list[dict[str, Any]], fstatus: dict[str, Any], now: datetime,
               halt: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    day = now.astimezone(IST).date().isoformat()
    out: list[dict[str, Any]] = []
    if halt:
        out.append({"id": f"halt:{halt.get('session')}:{halt.get('halt_ist')}", "severity": "CRITICAL",
                    "title": "Risk halt — new entries blocked", "detail": halt.get("reason"),
                    "ts": halt.get("halt_ist") or now.isoformat(timespec="seconds"), "source": "desk"})
    veto = hstatus.get("latest_entry_veto") or {}
    if veto:
        risk = veto.get("ticket_risk_inr")
        out.append({"id": f"veto:{veto.get('ts')}", "severity": "WARNING", "title": f"Entry vetoed: {veto.get('reason_code')}",
                    "detail": f"{veto.get('reason_text') or ''}{f' (ticket risk ₹{risk:,.0f})' if risk is not None else ''}".strip(),
                    "ts": veto.get("ts"), "source": "risk"})
    by_id = {r["id"]: r for r in rows}
    # One id per episode (when the condition started), so a second outage the same day alerts again.
    recon = (hstatus.get("checks") or {}).get("reconciliation") or {}
    episodes = {
        "data": ("Stale market data", tape_last(board)),
        "paper": ("Paper loop down in market hours", (board.get("heartbeat") or {}).get("as_of_ist") or board.get("as_of_ist")),
        "broker": ("Broker reconciliation mismatch", str(recon.get("message") or "")[:80]),
    }
    for rid, (title, since) in episodes.items():
        r = by_id.get(rid)
        if r and r["tone"] == "red":
            out.append({"id": f"{rid}:{since or day}", "severity": "CRITICAL", "title": title, "detail": r["detail"],
                        "since": since, "ts": now.isoformat(timespec="seconds"), "source": "health"})
    vetoes = (hstatus.get("checks") or {}).get("risk_vetoes") or {}
    if vetoes and not vetoes.get("ok", True):
        out.append({"id": f"risk:{vetoes.get('last_seen') or day}", "severity": "CRITICAL", "title": "Risk limit hit",
                    "detail": vetoes.get("message"), "ts": vetoes.get("last_seen") or now.isoformat(timespec="seconds"),
                    "source": "risk"})
    started = ts_of(fstatus.get("started_at_ist"))
    for t in board.get("open_trades") or []:
        opened = _opened_ts(t)
        if started and opened and started > opened:
            out.append({"id": f"restart:{t.get('trade_id')}:{started}", "severity": "CRITICAL",
                        "title": "Restart during an open trade",
                        "detail": f"{t.get('underlying')} {t.get('side')} {t.get('atm_strike')} opened before the paper loop restarted",
                        "ts": ist_iso(started), "source": "paper"})
    sev = {"CRITICAL": "CRITICAL", "WARN": "WARNING", "WARNING": "WARNING", "OK": "INFO"}
    for a in halerts[:20]:
        level = "INFO" if a.get("event") == "RECOVERED" else sev.get(str(a.get("severity")), "WARNING")
        out.append({"id": f"h:{a.get('ts')}:{a.get('check')}:{a.get('event')}", "severity": level,
                    "title": f"{a.get('check')} {str(a.get('event') or '').lower()}", "detail": a.get("message"),
                    "ts": a.get("ts"), "source": "health monitor"})
    out.sort(key=lambda a: (SEVERITY_RANK.get(a["severity"], 9), str(a.get("ts") or "")), reverse=False)
    return out


# ---------- snapshot ----------


def _health_files(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    hdir = root / "data" / "health"
    status = read_json(hdir / "status.json") or {}
    alerts: list[dict[str, Any]] = []
    try:
        with open(hdir / "alerts.jsonl", encoding="utf-8") as fh:
            lines = fh.readlines()[-50:]
    except OSError:
        lines = []
    for line in reversed(lines):
        try:
            alerts.append(json.loads(line))
        except ValueError:
            continue
    return status, alerts


def trim_board(board: dict[str, Any]) -> dict[str, Any]:
    out = {k: board[k] for k in BOARD_KEYS if k in board}
    out["steps"] = {u: {"span_ist": (s or {}).get("span_ist")} for u, s in (board.get("steps") or {}).items()}
    seen = board.get("seen_not_taken") or {}
    out["seen_not_taken"] = {"skipped_latest": (seen.get("skipped_latest") or [])[:40],
                             "cancelled": (seen.get("cancelled") or [])[:40]}
    sig = board.get("model_signals") or {}
    out["model_signals"] = {"latest": (sig.get("latest") or [])[:60], "counts": sig.get("counts")}
    today = board.get("today") or {}
    out["today"] = {k: today.get(k) for k in ("net_pnl_inr", "starting_desk_inr", "charges_inr", "win_rate_net_pct", "unique_books")}
    return out


SNAPSHOT_BUDGET_S = 0.25


def build_snapshot(root: Path = REPO, *, now: Optional[datetime] = None, fstatus: Optional[dict[str, Any]] = None,
                   budget_s: Optional[float] = None) -> dict[str, Any]:
    """``budget_s`` caps log/tape indexing per call; the API passes SNAPSHOT_BUDGET_S, tests pass None (read all)."""
    now = (now or datetime.now(IST)).astimezone(IST)
    board = load_board(root, budget_s) or {}
    if fstatus is None:
        from api.founder_status import build_founder_status

        try:
            fstatus = build_founder_status()
        except Exception:  # noqa: BLE001 — ops status is advisory; the snapshot must still load
            fstatus = {}
    hstatus, halerts = _health_files(root)
    events, history_complete = trade_events(root, budget_s, wait=budget_s is None)
    rows = history_rows(root, board, events)
    days = day_summaries(rows)
    halt = risk_halt(root, {now.date().isoformat(), str(board.get("session_ist_date") or "")})
    health = health_rows(root, board, fstatus, hstatus, now, halt)
    exam_path = root / "data" / "recon" / "sod_exam_report.json"
    exam = read_json(exam_path if exam_path.is_file() else root / "apps" / "web" / "public" / "mock" / "sod_exam_report.json")
    return {
        "ok": bool(board),
        "as_of": now.isoformat(timespec="seconds"),
        "board": trim_board(board),
        "exam": exam,
        "tape_last_ist": tape_last(board),
        "founder": {k: fstatus.get(k) for k in ("ok", "mode", "issues", "next_action", "agents", "services", "started_at_ist")},
        "founder_book": founder_book(root),
        "health": health,
        "alerts": alert_list(board, health, hstatus, halerts, fstatus, now, halt),
        "risk_halt": halt,
        "days": days,
        "history_complete": history_complete,
        "account": account(board, days),
        "orders": "REFUSED",
        "promote": False,
    }


def day_history(root: Path = REPO, day: Optional[str] = None, budget_s: Optional[float] = None) -> dict[str, Any]:
    board = load_board(root, budget_s) or {}
    events, complete = trade_events(root, budget_s, wait=budget_s is None)
    rows = history_rows(root, board, events)
    days = sorted({r["day"] for r in rows if r.get("day")}, reverse=True)
    pick = day or (days[0] if days else None)
    trades = [r for r in rows if r.get("day") == pick]
    attach_entry_spots({"closed_trades": trades}, root / "data" / "recon" / "paper_watch" / "DUAL-TAPE", budget_s)
    return {"day": pick, "days": days, "trades": trades, "complete": complete}


# ---------- decision trace ----------


def _step(sid: str, title: str, decided: Optional[str], why: Optional[str], fields: dict[str, Any], source: str,
          status: str = "OK") -> dict[str, Any]:
    fields = {k: v for k, v in fields.items() if v not in (None, "", [], {})}
    if not decided and not fields:
        return {"id": sid, "title": title, "status": "NO_DATA", "decided": None, "why": why, "fields": {}, "source": None}
    if not decided:
        key, val = next(iter(fields.items()))
        decided = f"{key} {', '.join(map(str, val)) if isinstance(val, list) else val}"
    return {"id": sid, "title": title, "status": status, "decided": decided, "why": why, "fields": fields, "source": source}


def _why_now(text: Any) -> Optional[str]:
    m = re.search(r"why_now=([^;|]+)", str(text or ""))
    return m.group(1).strip() if m else None


def _r(v: Any, dp: int) -> Any:
    return round(v, dp) if isinstance(v, float) else v


def trade_trace(root: Path = REPO, trade_id: str = "", budget_s: Optional[float] = None) -> dict[str, Any]:
    board = load_board(root, budget_s) or {}
    events, _ = trade_events(root, budget_s, wait=budget_s is None)
    trades = [*(board.get("open_trades") or []), *(board.get("closed_trades") or [])]
    t = next((x for x in trades if x.get("trade_id") == trade_id), None)
    if t is None:
        t = next((x for x in history_rows(root, board, events) if x.get("trade_id") == trade_id), None)
    if t is None:
        return {"ok": False, "trade_id": trade_id, "reason": "trade not found in board, model log or ledger", "steps": []}
    opened = _opened_ts(t)
    evs = [e for e in events.get(trade_id, []) if live_write(e, opened, 3 * 3600)]
    und = t.get("underlying")
    sig = board.get("model_signals") or {}
    votes = [s for s in [*(sig.get("recent") or []), *(sig.get("latest") or [])]
             if s.get("underlying") == und and opened and opened - 180 <= int(s.get("ts") or 0) <= opened]
    at_open = [s for s in votes if s.get("desk_opened")] or votes
    lg_orders = _ledger_query(root, "SELECT * FROM orders WHERE trade_id = ?", (trade_id,))
    ids = tuple(o["client_order_id"] for o in lg_orders)
    marks = ",".join("?" * len(ids)) or "''"
    lg_risk = _ledger_query(root, f"SELECT * FROM risk_decisions WHERE client_order_id IN ({marks})", ids) if ids else []
    lg_fills = _ledger_query(root, "SELECT * FROM fills WHERE trade_id = ?", (trade_id,))
    lg_events = _ledger_query(root, "SELECT event_type, ts, source, payload_json FROM events WHERE payload_json LIKE ? ORDER BY seq",
                              (f"%{trade_id}%",))
    boss_ev = next((e for e in lg_events if e.get("event_type") in ("ENTRY_APPROVED", "NO_ENTRY")), None)

    vote_list = [f"{s.get('source')}: {s.get('side') or 'SILENT'} ({s.get('vs_picker') or s.get('reason')})" for s in at_open]
    steps = [
        _step("data", "Data",
              f"{und} spot {t.get('spot_at_entry')}" if t.get("spot_at_entry") is not None else None,
              t.get("regime_reason"),
              {"regime": t.get("index_regime"), "market kind": t.get("market_kind_open"), "ER": _r(t.get("regime_er"), 3),
               "range/ATR": _r(t.get("regime_range_over_atr"), 2), "IV": _r(t.get("iv"), 2), "delta": _r(t.get("delta"), 3),
               "spot source": t.get("spot_at_entry_src")},
              "trade record"),
        _step("analysts", "Analysts",
              f"{len([s for s in at_open if s.get('side')])} spoke, {len([s for s in at_open if not s.get('side')])} silent" if at_open else (
                  f"agreed: {', '.join(t.get('model_names') or [])}" if t.get("model_names") else None),
              None,
              {"votes at open": vote_list, "agreeing models": t.get("model_names")},
              "board model_signals" if at_open else "trade record"),
        _step("boss", "Boss",
              (f"{boss_ev['event_type']}" if boss_ev else
               f"BUY {t.get('side')} via {t.get('book_id')}" if t.get("book_id") else None),
              _why_now(t.get("justification")),
              {"picker": next((s.get("picker_action") for s in at_open if s.get("picker_action")), None),
               "observer": next((s.get("observer_action") for s in at_open if s.get("observer_action")), None),
               "event payload": json.loads(boss_ev["payload_json"]) if boss_ev else None},
              "event log" if boss_ev else "trade record"),
        _step("risk", "Risk",
              (f"{'APPROVED' if lg_risk[-1].get('approved') else 'VETOED'} · {lg_risk[-1].get('reason_code')}" if lg_risk else None),
              lg_risk[-1].get("reason") if lg_risk else "No risk-engine record for this paper trade (event path not writing a ledger).",
              {"checks": [f"{r.get('action')} {r.get('reason_code')}" for r in lg_risk]},
              "ledger risk_decisions"),
        _step("desk", "Desk",
              f"{t.get('atm_strike')} {t.get('side')} limit {t.get('limit_price') or t.get('entry')}" if t.get("atm_strike") else None,
              f"strike from {t.get('strike_source')}" if t.get("strike_source") else None,
              {"stop": t.get("stop"), "target": t.get("target"), "lots": t.get("lots"), "lot size": t.get("lot_size"),
               "lot check": t.get("lot_status"),
               "events": [f"{e.get('event')} {e.get('status') or ''}".strip() for e in evs if e.get("event") != "CLOSE"]},
              "trade record + model log"),
        _step("broker", "Broker",
              (f"{len(lg_orders)} ledger order(s)" if lg_orders else
               "Paper only — no broker order" if t.get("execution") or t.get("shadow") is not None else None),
              "Paper mode: execution refused by design" if not lg_orders and t.get("execution") else None,
              {"execution": t.get("execution"),
               "orders": [f"{o.get('order_type')} {o.get('side')} {o.get('qty')} @ {o.get('price')} ({o.get('purpose')})" for o in lg_orders]},
              "ledger orders" if lg_orders else "trade record", status="PAPER" if not lg_orders else "OK"),
        _step("fill", "Fill",
              (f"filled @ {t.get('entry')}" if t.get("filled") else "not filled") if t.get("filled") is not None else None,
              t.get("exit_reason"),
              {"opened": t.get("opened_ist"), "closed": t.get("closed_ist"), "exit": t.get("exit"),
               "points": t.get("realized_pnl"), "net ₹": t.get("realized_pnl_inr"),
               "fills": [f"{f.get('side')} {f.get('qty')} @ {f.get('price')} slip {f.get('slippage')}" for f in lg_fills],
               "path": [f"{e.get('event')} stop {e.get('stop')} target {e.get('target')}" for e in evs
                        if e.get("event") in ("TRAIL_STOP", "TARGET_LOCK_SHIFT")]},
              "trade record + model log"),
    ]
    closed = t.get("exit") is not None or bool(t.get("closed_ist"))
    return {"ok": True, "trade_id": trade_id, "underlying": und, "side": t.get("side"), "closed": closed, "steps": steps}
