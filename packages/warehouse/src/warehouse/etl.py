"""Nightly warehouse ETL: paper books, ledger/event SQLite, model logs and recon files -> analytics SQLite.

    python -m warehouse.etl run            # incremental: only new or changed files
    python -m warehouse.etl run --full     # rebuild every fact table from the source files
    python -m warehouse.etl status
    python -m warehouse.etl query pnl --period week

Reads only. Never writes the source files, never calls a broker, never places orders.

ponytail: stdlib SQLite, not DuckDB (DuckDB is not installed and adds a dependency). The output is a
plain SQLite file, so DuckDB can still read it later with `ATTACH 'analytics.sqlite' (TYPE sqlite)`.
Every fact row carries `src_file`, so a changed source is replaced by deleting its rows and reloading
it in one transaction. Rollups (daily/weekly/monthly P&L, attribution) are views, never stored copies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence

from warehouse.paths import assert_writable_db, repo_root

IST = timezone(timedelta(hours=5, minutes=30))
ETL_VERSION = "etl-v1"


def default_analytics_db(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "warehouse" / "analytics.sqlite"


# Lower priority wins when the same trade_id appears in more than one source.
PRIO_PAPER_BOOKED, PRIO_DASHBOARD, PRIO_LEDGER = 1, 2, 3
# Same idea for stage counts: the event log is the most direct record of each stage.
PRIO_EVENTS, PRIO_LEDGER_RISK, PRIO_BOARD_SKIPS = 1, 2, 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS etl_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS etl_files (
    path TEXT PRIMARY KEY, kind TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0, rows INTEGER NOT NULL DEFAULT 0, loaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS etl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
    full_rebuild INTEGER NOT NULL, files_seen INTEGER NOT NULL, files_loaded INTEGER NOT NULL,
    files_tailed INTEGER NOT NULL, files_skipped INTEGER NOT NULL, rows INTEGER NOT NULL, errors_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades_raw (
    src_file TEXT NOT NULL, source TEXT NOT NULL, priority INTEGER NOT NULL, trade_id TEXT NOT NULL,
    day TEXT, book_id TEXT, underlying TEXT, side TEXT, strike REAL, opened_ts INTEGER, closed_ts INTEGER,
    entry REAL, exit REAL, limit_price REAL, qty INTEGER, lots INTEGER, exit_reason TEXT, regime TEXT,
    gross_pnl REAL, charges REAL, net_pnl REAL, brokerage REAL, stt REAL, exchange REAL, sebi REAL,
    stamp REAL, gst REAL, entry_slippage REAL, exit_slippage REAL, filled INTEGER NOT NULL,
    PRIMARY KEY (src_file, trade_id)
);
CREATE INDEX IF NOT EXISTS trades_raw_trade ON trades_raw (trade_id, priority);
CREATE TABLE IF NOT EXISTS trade_models (
    src_file TEXT NOT NULL, trade_id TEXT NOT NULL, model TEXT NOT NULL,
    PRIMARY KEY (src_file, trade_id, model)
);
CREATE TABLE IF NOT EXISTS fills (
    src_file TEXT NOT NULL, fill_id INTEGER NOT NULL, trade_id TEXT, client_order_id TEXT, ts TEXT, day TEXT,
    symbol TEXT, side TEXT, qty INTEGER, price REAL, decision_price REAL, slippage REAL,
    PRIMARY KEY (src_file, fill_id)
);
CREATE TABLE IF NOT EXISTS charges (
    src_file TEXT NOT NULL, charge_id INTEGER NOT NULL, trade_id TEXT, client_order_id TEXT, ts TEXT, day TEXT,
    turnover REAL, brokerage REAL, stt REAL, exchange REAL, sebi REAL, stamp REAL, gst REAL, total REAL,
    PRIMARY KEY (src_file, charge_id)
);
CREATE TABLE IF NOT EXISTS analyst_votes (
    src_file TEXT NOT NULL, day TEXT NOT NULL, underlying TEXT NOT NULL, analyst_id TEXT NOT NULL,
    signal TEXT NOT NULL, n INTEGER NOT NULL, confidence_sum REAL NOT NULL,
    PRIMARY KEY (src_file, day, underlying, analyst_id, signal)
);
CREATE TABLE IF NOT EXISTS stage_events (
    src_file TEXT NOT NULL, priority INTEGER NOT NULL, day TEXT NOT NULL, stage TEXT NOT NULL,
    outcome TEXT NOT NULL, reason TEXT NOT NULL, n INTEGER NOT NULL,
    PRIMARY KEY (src_file, day, stage, outcome, reason)
);
CREATE TABLE IF NOT EXISTS model_log (
    src_file TEXT NOT NULL, line_no INTEGER NOT NULL, day TEXT, ts_ist TEXT, event TEXT, book_id TEXT,
    trade_id TEXT, status TEXT, reason TEXT,
    PRIMARY KEY (src_file, line_no)
);
CREATE TABLE IF NOT EXISTS recon_reports (
    src_file TEXT NOT NULL, run_id INTEGER NOT NULL, kind TEXT NOT NULL, day TEXT, ts TEXT, ok INTEGER,
    n_mismatches INTEGER, summary_json TEXT NOT NULL,
    PRIMARY KEY (src_file, run_id)
);

DROP VIEW IF EXISTS trades;
CREATE VIEW trades AS
WITH ranked AS (
    SELECT t.*, ROW_NUMBER() OVER (PARTITION BY trade_id ORDER BY priority, src_file DESC) AS rn FROM trades_raw t
), led AS (
    SELECT trade_id, MAX(entry_slippage) AS es, MAX(exit_slippage) AS xs FROM trades_raw
    WHERE source = 'ledger' GROUP BY trade_id
)
SELECT r.trade_id, r.source, r.day, r.book_id, r.underlying, r.side, r.strike, r.opened_ts, r.closed_ts,
       r.entry, r.exit, r.limit_price, r.qty, r.lots, r.exit_reason, r.regime, r.gross_pnl, r.charges,
       r.net_pnl, r.brokerage, r.stt, r.exchange, r.sebi, r.stamp, r.gst,
       COALESCE(led.es, r.entry_slippage) AS entry_slippage, COALESCE(led.xs, r.exit_slippage) AS exit_slippage,
       r.filled
FROM ranked r LEFT JOIN led ON led.trade_id = r.trade_id WHERE r.rn = 1;

DROP VIEW IF EXISTS exit_reasons;
CREATE VIEW exit_reasons AS
SELECT day, book_id, COALESCE(exit_reason, 'UNKNOWN') AS exit_reason, COUNT(*) AS n_trades,
       SUM(net_pnl > 0) AS n_wins, ROUND(SUM(net_pnl), 2) AS net_pnl
FROM trades WHERE filled = 1 GROUP BY day, book_id, COALESCE(exit_reason, 'UNKNOWN');

DROP VIEW IF EXISTS model_attribution;
CREATE VIEW model_attribution AS
WITH tm AS (SELECT DISTINCT trade_id, model FROM trade_models)
SELECT t.day, tm.model, COUNT(*) AS n_trades, SUM(t.net_pnl > 0) AS n_wins,
       ROUND(100.0 * SUM(t.net_pnl > 0) / COUNT(*), 2) AS win_rate_pct, ROUND(SUM(t.net_pnl), 2) AS net_pnl
FROM tm JOIN trades t ON t.trade_id = tm.trade_id WHERE t.filled = 1 GROUP BY t.day, tm.model;

DROP VIEW IF EXISTS stage_attribution;
CREATE VIEW stage_attribution AS
SELECT s.day, s.stage, s.outcome, s.reason, SUM(s.n) AS n, NULL AS net_pnl FROM stage_events s
WHERE s.src_file = (SELECT s2.src_file FROM stage_events s2 WHERE s2.day = s.day AND s2.stage = s.stage
                    ORDER BY s2.priority, s2.src_file DESC LIMIT 1)
GROUP BY s.day, s.stage, s.outcome, s.reason
UNION ALL
SELECT day, 'exit', CASE WHEN net_pnl > 0 THEN 'WIN' ELSE 'LOSS' END, COALESCE(exit_reason, 'UNKNOWN'),
       COUNT(*), ROUND(SUM(net_pnl), 2)
FROM trades WHERE filled = 1 GROUP BY 1, 2, 3, 4;

DROP VIEW IF EXISTS analyst_vote_summary;
CREATE VIEW analyst_vote_summary AS
SELECT v.day, v.analyst_id, v.signal, SUM(v.n) AS n, ROUND(SUM(v.confidence_sum) / SUM(v.n), 4) AS avg_confidence
FROM analyst_votes v
WHERE v.src_file = (SELECT v2.src_file FROM analyst_votes v2 WHERE v2.day = v.day ORDER BY v2.src_file DESC LIMIT 1)
GROUP BY v.day, v.analyst_id, v.signal;
"""

PERIODS = {
    "day": "day",
    "week": "date(day, 'weekday 0', '-6 days')",  # Monday of the ISO week
    "month": "substr(day, 1, 7)",
}
_PNL_VIEW = """
DROP VIEW IF EXISTS pnl_{name};
CREATE VIEW pnl_{name} AS
SELECT {expr} AS period, book_id, COUNT(*) AS n_trades, SUM(net_pnl > 0) AS n_wins,
       ROUND(100.0 * SUM(net_pnl > 0) / COUNT(*), 2) AS win_rate_pct, ROUND(SUM(gross_pnl), 2) AS gross_pnl,
       ROUND(SUM(charges), 2) AS charges, ROUND(SUM(net_pnl), 2) AS net_pnl,
       ROUND(AVG(entry_slippage), 4) AS avg_entry_slippage, ROUND(AVG(exit_slippage), 4) AS avg_exit_slippage
FROM trades WHERE filled = 1 AND day IS NOT NULL GROUP BY {expr}, book_id;
"""
VIEWS = "".join(_PNL_VIEW.format(name={"day": "daily", "week": "weekly", "month": "monthly"}[k], expr=v)
                for k, v in PERIODS.items())
FACT_TABLES = ("trades_raw", "trade_models", "fills", "charges", "analyst_votes", "stage_events", "model_log",
               "recon_reports")


# ------------------------------------------------------------------ helpers


def _f(x: Any) -> Optional[float]:
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def _i(x: Any) -> Optional[int]:
    v = _f(x)
    return None if v is None else int(v)


def _ist_day(ts: Any) -> Optional[str]:
    """Epoch seconds or ISO string -> IST date."""
    if ts is None or ts == "":
        return None
    v = _f(ts)
    if v is not None and v > 1e9:
        return datetime.fromtimestamp(v, IST).date().isoformat()
    s = str(ts)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else None
    return (dt.astimezone(IST) if dt.tzinfo else dt).date().isoformat()


def _epoch(ts: Any) -> Optional[int]:
    v = _f(ts)
    if v is not None:
        return int(v)
    try:
        dt = datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    return int((dt if dt.tzinfo else dt.replace(tzinfo=IST)).timestamp())


def _sha(*paths: Path, limit: Optional[int] = None) -> str:
    h = hashlib.sha256()
    for p in paths:
        if not p.is_file():
            continue
        with p.open("rb") as fh:
            left = limit
            while left is None or left > 0:
                chunk = fh.read(1 << 20 if left is None else min(1 << 20, left))
                if not chunk:
                    break
                h.update(chunk)
                if left is not None:
                    left -= len(chunk)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def paper_trade_row(r: dict[str, Any], *, source: str, priority: int, day: Optional[str] = None) -> dict[str, Any]:
    """One closed paper-engine trade (paper_booked line or board closed_trades row)."""
    entry, limit = _f(r.get("entry")), _f(r.get("limit_price"))
    return {
        "source": source, "priority": priority, "trade_id": str(r.get("trade_id")),
        "day": _ist_day(r.get("closed_ts")) or _ist_day(r.get("opened_ts")) or day,
        "book_id": r.get("book_id"), "underlying": r.get("underlying"), "side": r.get("side"),
        "strike": _f(r.get("atm_strike")), "opened_ts": _i(r.get("opened_ts")), "closed_ts": _i(r.get("closed_ts")),
        "entry": entry, "exit": _f(r.get("exit")), "limit_price": limit, "qty": _i(r.get("qty")),
        "lots": _i(r.get("lots")), "exit_reason": r.get("exit_reason"), "regime": r.get("index_regime"),
        "gross_pnl": _f(r.get("gross_pnl_inr")), "charges": _f(r.get("charges_inr")),
        "net_pnl": _f(r.get("realized_pnl_inr")), "brokerage": _f(r.get("brokerage_inr")),
        "stt": _f(r.get("stt_inr")), "exchange": _f(r.get("exchange_inr")), "sebi": _f(r.get("sebi_inr")),
        "stamp": _f(r.get("stamp_inr")), "gst": _f(r.get("gst_inr")),
        # Premium points per unit paid above the working limit (buys only; + is worse).
        "entry_slippage": None if entry is None or limit is None else round(entry - limit, 4),
        "exit_slippage": None, "filled": 1 if r.get("filled") else 0,
    }


_UNDERLYING = re.compile(r"^(BANKNIFTY|FINNIFTY|MIDCPNIFTY|NIFTY|SENSEX|BANKEX)")


def ledger_trade_row(t: dict[str, Any]) -> dict[str, Any]:
    sym = str(t.get("symbol") or "")
    m = _UNDERLYING.match(sym.upper())
    side = "CE" if sym.upper().endswith("CE") else "PE" if sym.upper().endswith("PE") else None
    return {
        "source": "ledger", "priority": PRIO_LEDGER, "trade_id": str(t["trade_id"]),
        "day": t.get("day") or _ist_day(t.get("exit_time")) or _ist_day(t.get("entry_time")),
        "book_id": None, "underlying": m.group(1) if m else sym or None, "side": side, "strike": None,
        "opened_ts": _epoch(t.get("entry_time")), "closed_ts": _epoch(t.get("exit_time")),
        "entry": _f(t.get("entry_price")), "exit": _f(t.get("exit_price")), "limit_price": None,
        "qty": _i(t.get("entry_qty")), "lots": None, "exit_reason": t.get("exit_reason"), "regime": None,
        "gross_pnl": _f(t.get("gross_pnl")), "charges": _f(t.get("charges")), "net_pnl": _f(t.get("net_pnl")),
        "brokerage": None, "stt": None, "exchange": None, "sebi": None, "stamp": None, "gst": None,
        "entry_slippage": _f(t.get("entry_slippage")), "exit_slippage": _f(t.get("exit_slippage")),
        "filled": 1 if t.get("status") == "CLOSED" else 0,
    }


# ------------------------------------------------------------------ loaders


@dataclass
class Batch:
    """Rows for one source unit (`src_file`). Loaders fill it; the ETL writes it in one transaction."""

    src_file: str
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def add(self, table: str, row: dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append({"src_file": self.src_file, **row})

    def count(self) -> int:
        return sum(len(v) for v in self.rows.values())


def _jsonl(lines: Iterable[str]) -> Iterator[tuple[int, dict[str, Any]]]:
    for n, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            yield n, rec


def load_paper_booked(batch: Batch, lines: Sequence[str], first_line: int, path: Path) -> None:
    for _n, rec in _jsonl(lines):
        if rec.get("trade_id") is None:
            continue
        batch.add("trades_raw", paper_trade_row(rec, source="paper_booked", priority=PRIO_PAPER_BOOKED, day=path.stem))


def load_model_log(batch: Batch, lines: Sequence[str], first_line: int, path: Path) -> None:
    for n, rec in _jsonl(lines):
        batch.add("model_log", {
            "line_no": first_line + n, "day": _ist_day(rec.get("ts")) or _ist_day(rec.get("ts_ist")),
            "ts_ist": rec.get("ts_ist"), "event": rec.get("event"), "book_id": rec.get("book_id") or rec.get("model"),
            "trade_id": rec.get("trade_id"), "status": rec.get("status"),
            "reason": None if rec.get("reason") is None else str(rec.get("reason"))[:200],
        })


def load_dashboard(path: Path) -> list[Batch]:
    """The board is rewritten all day and holds one session, so each session day is its own unit."""
    board = json.loads(path.read_text(encoding="utf-8"))
    day = board.get("session_ist_date") or _ist_day(board.get("as_of_ist"))
    if not day:
        return []
    batch = Batch(f"{path}#{day}")
    for r in board.get("closed_trades") or []:
        if isinstance(r, dict) and r.get("trade_id") is not None:
            row = paper_trade_row(r, source="dashboard", priority=PRIO_DASHBOARD, day=day)
            batch.add("trades_raw", row)
            for model in r.get("model_names") or []:
                batch.add("trade_models", {"trade_id": row["trade_id"], "model": str(model)})
            if r.get("book_id"):
                batch.add("trade_models", {"trade_id": row["trade_id"], "model": str(r["book_id"])})
    for reason, n in (board.get("skip_reason_counts") or {}).items():
        batch.add("stage_events", {"priority": PRIO_BOARD_SKIPS, "day": day, "stage": "boss", "outcome": "NO_ENTRY",
                                   "reason": str(reason), "n": int(n)})
    return [batch]


def load_eod_recon(path: Path) -> list[Batch]:
    blob = json.loads(path.read_text(encoding="utf-8"))
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    scalars = {k: v for k, v in blob.items() if isinstance(v, (str, int, float, bool)) or v is None}
    batch = Batch(str(path))
    ok = blob.get("ok")
    batch.add("recon_reports", {
        "run_id": 0, "kind": "eod_recon", "day": m.group(1) if m else _ist_day(blob.get("as_of_ist")),
        "ts": blob.get("as_of_ist"), "ok": None if ok is None else int(bool(ok)),
        "n_mismatches": None, "summary_json": json.dumps(dict(list(scalars.items())[:40]), default=str),
    })
    return [batch]


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def load_sqlite(path: Path) -> list[Batch]:
    """A ledger file (trades/fills/charges/risk_decisions/recon_runs) and/or an event audit (`events`)."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = _tables(conn)
        batch = Batch(str(path))
        if "trades" in names:
            for t in _rows(conn, "SELECT * FROM trades WHERE status IN ('CLOSED', 'CANCELLED')"):
                batch.add("trades_raw", ledger_trade_row(t))
        if "fills" in names:
            for r in _rows(conn, "SELECT * FROM fills"):
                batch.add("fills", {
                    "fill_id": r["id"], "trade_id": r.get("trade_id"), "client_order_id": r.get("client_order_id"),
                    "ts": r.get("ts"), "day": _ist_day(r.get("ts")), "symbol": r.get("symbol"), "side": r.get("side"),
                    "qty": r.get("qty"), "price": r.get("price"), "decision_price": r.get("decision_price"),
                    "slippage": r.get("slippage"),
                })
        if "charges" in names:
            for r in _rows(conn, "SELECT * FROM charges"):
                batch.add("charges", {"charge_id": r["id"], **{k: r.get(k) for k in (
                    "trade_id", "client_order_id", "ts", "day", "turnover", "brokerage", "stt", "exchange", "sebi",
                    "stamp", "gst", "total")}})
        if "risk_decisions" in names:
            agg: dict[tuple[str, str, str], int] = {}
            for r in _rows(conn, "SELECT day, approved, reason_code FROM risk_decisions"):
                key = (str(r["day"]), "APPROVED" if r["approved"] else "VETOED", str(r["reason_code"]))
                agg[key] = agg.get(key, 0) + 1
            for (day, outcome, reason), n in agg.items():
                batch.add("stage_events", {"priority": PRIO_LEDGER_RISK, "day": day, "stage": "risk",
                                           "outcome": outcome, "reason": reason, "n": n})
        if "recon_runs" in names:
            for r in _rows(conn, "SELECT * FROM recon_runs"):
                try:
                    mism = json.loads(r.get("mismatches_json") or "[]")
                except ValueError:
                    mism = []
                batch.add("recon_reports", {
                    "run_id": r["id"], "kind": "ledger_recon", "day": _ist_day(r.get("ts")), "ts": r.get("ts"),
                    "ok": int(bool(r.get("ok"))), "n_mismatches": len(mism) if isinstance(mism, list) else None,
                    "summary_json": "{}",
                })
        if "events" in names:
            _load_events(conn, batch)
        return [batch] if batch.count() else []
    finally:
        conn.close()


def _event_day(ev_ts: Any, payload: dict[str, Any]) -> str:
    return _ist_day(payload.get("ts")) or _ist_day(ev_ts) or "UNKNOWN"


def _load_events(conn: sqlite3.Connection, batch: Batch) -> None:
    votes: dict[tuple[str, str, str, str], list[float]] = {}
    stages: dict[tuple[str, str, str, str], int] = {}

    def stage(day: str, name: str, outcome: str, reason: Any) -> None:
        key = (day, name, outcome, str(reason or ""))
        stages[key] = stages.get(key, 0) + 1

    for ev_type, ev_ts, raw in conn.execute("SELECT event_type, ts, payload_json FROM events ORDER BY seq"):
        try:
            p = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(p, dict):
            continue
        day = _event_day(ev_ts, p)
        if ev_type == "ANALYST_VOTE":
            key = (day, str(p.get("underlying") or ""), str(p.get("analyst_id") or ""), str(p.get("signal") or ""))
            acc = votes.setdefault(key, [0, 0.0])
            acc[0] += 1
            acc[1] += _f(p.get("confidence")) or 0.0
        elif ev_type == "ENTRY_APPROVED":
            stage(day, "boss", "ENTRY_APPROVED", p.get("book_id"))
            for model in p.get("analysts") or []:
                batch.add("trade_models", {"trade_id": str(p.get("trade_id")), "model": str(model)})
            if p.get("book_id"):
                batch.add("trade_models", {"trade_id": str(p.get("trade_id")), "model": str(p["book_id"])})
        elif ev_type == "NO_ENTRY":
            stage(day, "boss", "NO_ENTRY", p.get("reason"))
        elif ev_type == "ENTRY_VETOED":
            stage(day, "risk", "VETOED", p.get("reason_code") or p.get("reason"))
        elif ev_type == "ORDER_FILLED":
            stage(day, "desk", "ORDER_FILLED", p.get("purpose") or p.get("side"))
        elif ev_type == "ORDER_REJECTED":
            stage(day, "desk", "ORDER_REJECTED", p.get("reason"))
        elif ev_type == "POSITION_CLOSED":
            stage(day, "desk", "POSITION_CLOSED", p.get("exit_reason") or p.get("reason"))
    for (day, und, analyst, signal), (n, conf) in votes.items():
        batch.add("analyst_votes", {"day": day, "underlying": und, "analyst_id": analyst, "signal": signal,
                                    "n": n, "confidence_sum": round(conf, 6)})
    for (day, name, outcome, reason), n in stages.items():
        batch.add("stage_events", {"priority": PRIO_EVENTS, "day": day, "stage": name, "outcome": outcome,
                                   "reason": reason, "n": n})


# ------------------------------------------------------------------ sources


JsonlLoader = Callable[[Batch, Sequence[str], int, Path], None]
WholeLoader = Callable[[Path], list[Batch]]


@dataclass(frozen=True)
class Source:
    kind: str
    globs: tuple[str, ...]
    jsonl: Optional[JsonlLoader] = None  # append-only JSONL: tail-loaded from the last consumed byte
    whole: Optional[WholeLoader] = None  # anything else: reloaded when its bytes change


SOURCES: tuple[Source, ...] = (
    Source("paper_booked", ("data/recon/paper_booked/*.jsonl",), jsonl=load_paper_booked),
    Source("dashboard", ("data/recon/ml_paper_dashboard.json",), whole=load_dashboard),
    Source("model_log", ("data/recon/ml_paper_model_logs.jsonl",
                         "data/recon/archive/ml_paper_model_logs.jsonl.*.pre_slate"), jsonl=load_model_log),
    Source("sqlite", ("data/ledger/*.sqlite", "data/events/*.sqlite"), whole=load_sqlite),
    Source("eod_recon", ("data/recon/EOD_RECON_*.json",), whole=load_eod_recon),
)


# ------------------------------------------------------------------ ETL


def connect(db: Path) -> sqlite3.Connection:
    assert_writable_db(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA + VIEWS)
    conn.execute("INSERT OR REPLACE INTO etl_meta (key, value) VALUES ('etl_version', ?)", (ETL_VERSION,))
    conn.commit()
    return conn


def _insert(conn: sqlite3.Connection, batch: Batch) -> None:
    for table, rows in batch.rows.items():
        cols = list(rows[0])
        sql = f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
        conn.executemany(sql, [tuple(r.get(c) for c in cols) for r in rows])


def _delete_unit(conn: sqlite3.Connection, src_file: str) -> None:
    for t in FACT_TABLES:
        conn.execute(f"DELETE FROM {t} WHERE src_file = ?", (src_file,))


def _record_file(conn: sqlite3.Connection, path: str, kind: str, size: int, sha: str, consumed: int, rows: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO etl_files (path, kind, size, sha256, consumed, rows, loaded_at) VALUES (?,?,?,?,?,?,?)",
        (path, kind, size, sha, consumed, rows, _now()),
    )


def _load_jsonl(conn: sqlite3.Connection, src: Source, path: Path, prev: Optional[tuple]) -> tuple[str, int]:
    data = path.read_bytes()
    end = data.rfind(b"\n") + 1  # a half-written last line waits for the next run
    start, first_line = 0, 0
    if prev is not None:
        _size, sha, consumed, rows = prev
        if consumed <= end and hashlib.sha256(data[:consumed]).hexdigest() == sha:
            if consumed == end:
                return "skipped", 0
            start, first_line = consumed, data[:consumed].count(b"\n")
    batch = Batch(str(path))
    lines = data[start:end].decode("utf-8", errors="replace").splitlines()
    src.jsonl(batch, lines, first_line, path)
    with conn:
        if start == 0:
            _delete_unit(conn, str(path))
        _insert(conn, batch)
        total = batch.count() + (prev[3] if start else 0)
        _record_file(conn, str(path), src.kind, len(data), hashlib.sha256(data[:end]).hexdigest(), end, total)
    return ("tailed" if start else "loaded"), batch.count()


def _load_whole(conn: sqlite3.Connection, src: Source, path: Path, prev: Optional[tuple]) -> tuple[str, int]:
    sidecar = path.with_name(path.name + "-wal")
    sha = _sha(path, sidecar)
    size = path.stat().st_size + (sidecar.stat().st_size if sidecar.is_file() else 0)
    if prev is not None and prev[1] == sha:
        return "skipped", 0
    batches = src.whole(path)
    n = sum(b.count() for b in batches)
    with conn:
        # The board only ever holds today's session, so earlier `<path>#<day>` units stay as history.
        if src.kind != "dashboard":
            _delete_unit(conn, str(path))
        for b in batches:
            _delete_unit(conn, b.src_file)
            _insert(conn, b)
        _record_file(conn, str(path), src.kind, size, sha, size, n)
    return "loaded", n


def discover(root: Path, sources: Sequence[Source] = SOURCES) -> list[tuple[Source, Path]]:
    out: list[tuple[Source, Path]] = []
    for src in sources:
        seen: set[Path] = set()
        for pattern in src.globs:
            for p in sorted(root.glob(pattern)):
                if p.is_file() and p not in seen and not p.name.endswith((".state.json", "-wal", "-shm")):
                    seen.add(p)
                    out.append((src, p))
    return out


def run_etl(
    *, root: Optional[Path] = None, db: Optional[Path] = None, full: bool = False,
    sources: Sequence[Source] = SOURCES,
) -> dict[str, Any]:
    """Load every new or changed source file. Safe to re-run: unchanged files are skipped."""
    root = Path(root or repo_root()).resolve()
    db = Path(db or default_analytics_db(root)).resolve()
    started = _now()
    conn = connect(db)
    try:
        if full:
            # Board days whose file has since moved on cannot be rebuilt; keep them (they are history).
            with conn:
                for t in FACT_TABLES:
                    conn.execute(f"DELETE FROM {t} WHERE instr(src_file, '#') = 0")
                conn.execute("DELETE FROM etl_files")
        prev_rows = {r[0]: r[1:] for r in conn.execute("SELECT path, size, sha256, consumed, rows FROM etl_files")}
        stats = {"loaded": 0, "tailed": 0, "skipped": 0}
        rows, errors, files = 0, [], discover(root, sources)
        for src, path in files:
            if path.resolve() == db:
                continue
            try:
                loader = _load_jsonl if src.jsonl else _load_whole
                status, n = loader(conn, src, path, prev_rows.get(str(path)))
            except (OSError, ValueError, sqlite3.Error, KeyError, TypeError) as exc:
                errors.append({"path": str(path.relative_to(root)), "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            stats[status] += 1
            rows += n
        with conn:
            conn.execute(
                "INSERT INTO etl_runs (started_at, finished_at, full_rebuild, files_seen, files_loaded, files_tailed, "
                "files_skipped, rows, errors_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (started, _now(), int(full), len(files), stats["loaded"], stats["tailed"], stats["skipped"], rows,
                 json.dumps(errors)),
            )
        return {"ok": not errors, "db": str(db), "files_seen": len(files), **{f"files_{k}": v for k, v in stats.items()},
                "rows": rows, "errors": errors, "orders": "never"}
    finally:
        conn.close()


# ------------------------------------------------------------------ CLI


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m warehouse.etl", description="Nightly paper warehouse ETL (read-only).")
    ap.add_argument("--root", type=Path, help="repo/data root holding data/recon (default: this checkout)")
    ap.add_argument("--db", type=Path, help="analytics SQLite (default data/warehouse/analytics.sqlite)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="incremental load (only new/changed files)")
    p_run.add_argument("--full", action="store_true", help="drop fact rows and reload every file")
    sub.add_parser("status", help="row counts and the last run")
    p_q = sub.add_parser("query", help="read-only query helpers")
    p_q.add_argument("what", choices=("pnl", "exit-reasons", "models", "stages", "votes", "slippage", "charges"))
    p_q.add_argument("--period", choices=tuple(PERIODS), default="day")
    p_q.add_argument("--since")
    p_q.add_argument("--until")
    p_q.add_argument("--book")
    p_q.add_argument("--limit", type=int, default=200)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    from warehouse import queries

    args = build_parser().parse_args(argv)
    root = Path(args.root or repo_root()).resolve()
    db = Path(args.db or default_analytics_db(root)).resolve()
    if args.cmd == "run":
        out = run_etl(root=root, db=db, full=args.full)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    if args.cmd == "status":
        print(json.dumps(queries.etl_status(db), indent=2))
        return 0
    rng = {"since": args.since, "until": args.until, "limit": args.limit}
    fn = {
        "pnl": lambda: queries.pnl(db, period=args.period, book_id=args.book, **rng),
        "exit-reasons": lambda: queries.exit_reasons(db, book_id=args.book, **rng),
        "models": lambda: queries.model_attribution(db, **rng),
        "stages": lambda: queries.stage_attribution(db, **rng),
        "votes": lambda: queries.analyst_votes(db, **rng),
        "slippage": lambda: queries.slippage(db, book_id=args.book, **rng),
        "charges": lambda: queries.charges(db, period=args.period, **rng),
    }[args.what]
    print(json.dumps(fn(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
