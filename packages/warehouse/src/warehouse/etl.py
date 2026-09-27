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

Bad input never stops the run. A bad field (non-finite, out-of-range timestamp, wrong type) is stored as
NULL, a bad record (invalid JSON, not an object, no id) is skipped, and a bad file (top level not an
object, not SQLite) is skipped; each gets one row in `rejects` (file, line number, field, reason,
sample). Rejects belong to their file like any other row, so an unchanged file is not re-read and a
re-run adds nothing. Only transient failures (unreadable or locked right now) are `errors` and retried.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
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
-- Quarantine: one row per bad line (field '*'), bad field, or bad file (line_no 0). Loading carries on.
-- line_no is 1-based for text files and the row id / event seq for SQLite sources.
CREATE TABLE IF NOT EXISTS rejects (
    src_file TEXT NOT NULL, line_no INTEGER NOT NULL, field TEXT NOT NULL, reason TEXT NOT NULL, sample TEXT,
    PRIMARY KEY (src_file, line_no, field)
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
               "recon_reports", "rejects")


# ------------------------------------------------------------------ helpers


EPOCH_MIN, EPOCH_MAX = 946684800, 4102444800  # 2000-01-01 .. 2100-01-01 UTC
NUM_ABS_MAX = 1e12  # no paper price, P&L or quantity comes near this


class Bad(ValueError):
    """One unusable value; the caller stores NULL and a reject row."""


def _num(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    if isinstance(x, bool) or not isinstance(x, (int, float, str)):
        raise Bad(f"expected a number, got {type(x).__name__}")
    try:
        v = float(x)
    except OverflowError:
        raise Bad("out of range") from None
    except ValueError:
        raise Bad("not a number") from None
    if not math.isfinite(v):
        raise Bad("not finite")
    if abs(v) > NUM_ABS_MAX:
        raise Bad("out of range")
    return v


def _int(x: Any) -> Optional[int]:
    v = _num(x)
    return None if v is None else int(v)


def _epoch(x: Any) -> Optional[int]:
    """Epoch seconds (number or digits) or an ISO timestamp (naive = IST) -> epoch seconds."""
    if x is None or x == "":
        return None
    if isinstance(x, str) and not re.fullmatch(r"\s*-?\d+(\.\d+)?([eE][-+]?\d+)?\s*", x):
        try:
            dt = datetime.fromisoformat(x.strip().replace("Z", "+00:00"))
        except ValueError:
            raise Bad("unparseable timestamp") from None
        v = (dt if dt.tzinfo else dt.replace(tzinfo=IST)).timestamp()
    else:
        v = _num(x)
    if not EPOCH_MIN <= v <= EPOCH_MAX:
        raise Bad("timestamp out of range")
    return int(v)


def _day(x: Any) -> Optional[str]:
    """Epoch, ISO timestamp or YYYY-MM-DD -> IST date."""
    if isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.strip()):
        try:
            return date.fromisoformat(x.strip()).isoformat()
        except ValueError:
            raise Bad("invalid date") from None
    v = _epoch(x)
    return None if v is None else datetime.fromtimestamp(v, IST).date().isoformat()


def _text(x: Any, limit: int = 200) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, float) and not math.isfinite(x):
        raise Bad("not finite")
    if isinstance(x, (str, int, float)) and not isinstance(x, bool):
        return str(x)[:limit]
    raise Bad(f"expected text, got {type(x).__name__}")


def _sample(x: Any) -> str:
    try:
        return json.dumps(x, default=str)[:300]
    except (TypeError, ValueError, OverflowError):
        return repr(x)[:300]


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


# ------------------------------------------------------------------ loaders

REJECT_CAP = 500  # per unit; beyond this only a count row is kept


@dataclass
class Batch:
    """Rows for one source unit (`src_file`). Loaders fill it; the ETL writes it in one transaction."""

    src_file: str
    rows: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    n_rejects: int = 0

    def add(self, table: str, row: dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append({"src_file": self.src_file, **row})

    def reject(self, line_no: int, fld: str, reason: str, sample: Any = None) -> None:
        self.n_rejects += 1
        if self.n_rejects <= REJECT_CAP:
            self.add("rejects", {"line_no": line_no, "field": fld, "reason": reason[:300],
                                 "sample": None if sample is None else _sample(sample)})

    def finish(self) -> "Batch":
        if self.n_rejects > REJECT_CAP:
            self.add("rejects", {"line_no": -1, "field": "*", "reason": f"{self.n_rejects - REJECT_CAP} more rejects not stored",
                                 "sample": None})
        return self

    def count(self) -> int:
        return sum(len(v) for k, v in self.rows.items() if k != "rejects")


class Rec:
    """Field reader for one source record: a bad field becomes None plus one reject row."""

    def __init__(self, batch: Batch, line_no: int, rec: dict[str, Any], prefix: str = "") -> None:
        self.batch, self.line_no, self.rec, self.prefix = batch, line_no, rec, prefix

    def __call__(self, key: str, conv: Callable[[Any], Any] = _text) -> Any:
        raw = self.rec.get(key)
        try:
            return conv(raw)
        except Bad as exc:
            self.batch.reject(self.line_no, self.prefix + key, str(exc), raw)
            return None


def paper_trade_row(g: Rec, *, source: str, priority: int, day: Optional[str] = None) -> dict[str, Any]:
    """One closed paper-engine trade (paper_booked line or board closed_trades row)."""
    entry, limit = g("entry", _num), g("limit_price", _num)
    opened, closed = g("opened_ts", _epoch), g("closed_ts", _epoch)
    return {
        "source": source, "priority": priority, "trade_id": g("trade_id"),
        "day": _day(closed or opened) or day,
        "book_id": g("book_id"), "underlying": g("underlying"), "side": g("side"),
        "strike": g("atm_strike", _num), "opened_ts": opened, "closed_ts": closed,
        "entry": entry, "exit": g("exit", _num), "limit_price": limit, "qty": g("qty", _int),
        "lots": g("lots", _int), "exit_reason": g("exit_reason"), "regime": g("index_regime"),
        "gross_pnl": g("gross_pnl_inr", _num), "charges": g("charges_inr", _num),
        "net_pnl": g("realized_pnl_inr", _num), "brokerage": g("brokerage_inr", _num),
        "stt": g("stt_inr", _num), "exchange": g("exchange_inr", _num), "sebi": g("sebi_inr", _num),
        "stamp": g("stamp_inr", _num), "gst": g("gst_inr", _num),
        # Premium points per unit paid above the working limit (buys only; + is worse).
        "entry_slippage": None if entry is None or limit is None else round(entry - limit, 4),
        "exit_slippage": None, "filled": 1 if g.rec.get("filled") is True else 0,
    }


_UNDERLYING = re.compile(r"^(BANKNIFTY|FINNIFTY|MIDCPNIFTY|NIFTY|SENSEX|BANKEX)")


def ledger_trade_row(g: Rec) -> dict[str, Any]:
    sym = (g("symbol") or "").upper()
    m = _UNDERLYING.match(sym)
    side = "CE" if sym.endswith("CE") else "PE" if sym.endswith("PE") else None
    opened, closed = g("entry_time", _epoch), g("exit_time", _epoch)
    return {
        "source": "ledger", "priority": PRIO_LEDGER, "trade_id": g("trade_id"),
        "day": g("day", _day) or _day(closed or opened),
        "book_id": None, "underlying": m.group(1) if m else sym or None, "side": side, "strike": None,
        "opened_ts": opened, "closed_ts": closed,
        "entry": g("entry_price", _num), "exit": g("exit_price", _num), "limit_price": None,
        "qty": g("entry_qty", _int), "lots": None, "exit_reason": g("exit_reason"), "regime": None,
        "gross_pnl": g("gross_pnl", _num), "charges": g("charges", _num), "net_pnl": g("net_pnl", _num),
        "brokerage": None, "stt": None, "exchange": None, "sebi": None, "stamp": None, "gst": None,
        "entry_slippage": g("entry_slippage", _num), "exit_slippage": g("exit_slippage", _num),
        "filled": 1 if g.rec.get("status") == "CLOSED" else 0,
    }


def _record(batch: Batch, line_no: int, rec: Any, build: Callable[[Rec], list[tuple[str, dict[str, Any]]]],
            prefix: str = "") -> None:
    """Build every row of one record, then add them; any surprise skips just this record."""
    if not isinstance(rec, dict):
        batch.reject(line_no, "*", f"record is {type(rec).__name__}, not an object", rec)
        return
    try:
        rows = build(Rec(batch, line_no, rec, prefix))
    except Bad as exc:
        batch.reject(line_no, "*", f"record skipped: {exc}", rec)
        return
    except Exception as exc:  # noqa: BLE001 - one odd record must never stop the night's load
        batch.reject(line_no, "*", f"record skipped: {type(exc).__name__}: {exc}", rec)
        return
    for table, row in rows:
        batch.add(table, row)


def _jsonl(batch: Batch, lines: Iterable[str], first_line: int) -> Iterator[tuple[int, Any]]:
    """(1-based line number, parsed JSON) for every non-blank line; bad JSON is rejected here."""
    for n, line in enumerate(lines, start=first_line + 1):
        line = line.strip()
        if not line:
            continue
        try:
            yield n, json.loads(line)
        except (ValueError, RecursionError) as exc:
            batch.reject(n, "*", f"invalid JSON: {exc}"[:200], line[:300])


def _need_id(g: Rec, key: str = "trade_id") -> str:
    tid = g(key)
    if not tid:
        raise Bad(f"missing {key}")
    return tid


def load_paper_booked(batch: Batch, lines: Sequence[str], first_line: int, path: Path) -> None:
    def build(g: Rec) -> list[tuple[str, dict[str, Any]]]:
        _need_id(g)
        return [("trades_raw", paper_trade_row(g, source="paper_booked", priority=PRIO_PAPER_BOOKED, day=path.stem))]

    for n, rec in _jsonl(batch, lines, first_line):
        _record(batch, n, rec, build)


def load_model_log(batch: Batch, lines: Sequence[str], first_line: int, path: Path) -> None:
    def build(g: Rec) -> list[tuple[str, dict[str, Any]]]:
        return [("model_log", {
            "line_no": g.line_no, "day": g("ts", _day) or g("ts_ist", _day), "ts_ist": g("ts_ist"),
            "event": g("event"), "book_id": g("book_id") or g("model"), "trade_id": g("trade_id"),
            "status": g("status"), "reason": g("reason"),
        })]

    for n, rec in _jsonl(batch, lines, first_line):
        _record(batch, n, rec, build)


def _whole_json(path: Path, batch: Batch) -> Optional[dict[str, Any]]:
    """Top-level JSON object, or None after a file-level reject (bad JSON, list, number, ...)."""
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, RecursionError) as exc:  # includes UnicodeDecodeError
        batch.reject(0, "*", f"invalid JSON file: {exc}"[:200])
        return None
    if not isinstance(blob, dict):
        batch.reject(0, "*", f"top-level JSON is {type(blob).__name__}, expected an object", blob)
        return None
    return blob


def load_dashboard(path: Path) -> list[Batch]:
    """The board is rewritten all day and holds one session, so each session day is its own unit."""
    file_unit = Batch(str(path))
    board = _whole_json(path, file_unit)
    if board is None:
        return [file_unit.finish()]
    day = Rec(file_unit, 0, board)("session_ist_date", _day) or Rec(file_unit, 0, board)("as_of_ist", _day)
    if not day:
        file_unit.reject(0, "session_ist_date", "board has no usable session date")
        return [file_unit.finish()]
    batch = Batch(f"{path}#{day}")
    trades = board.get("closed_trades")
    if trades is not None and not isinstance(trades, list):
        batch.reject(0, "closed_trades", f"expected a list, got {type(trades).__name__}", trades)
        trades = []

    def build(g: Rec) -> list[tuple[str, dict[str, Any]]]:
        _need_id(g)
        row = paper_trade_row(g, source="dashboard", priority=PRIO_DASHBOARD, day=day)
        models = g.rec.get("model_names") or []
        if not isinstance(models, list):
            g.batch.reject(g.line_no, g.prefix + "model_names", "expected a list", models)
            models = []
        out = [("trades_raw", row)]
        for m in [*models, g.rec.get("book_id")]:
            try:
                name = _text(m)
            except Bad as exc:
                g.batch.reject(g.line_no, g.prefix + "model_names", str(exc), m)
                continue
            if name:
                out.append(("trade_models", {"trade_id": row["trade_id"], "model": name}))
        return out

    for i, r in enumerate(trades or [], start=1):
        _record(batch, i, r, build, prefix="closed_trades.")
    skips = board.get("skip_reason_counts") or {}
    if not isinstance(skips, dict):
        batch.reject(0, "skip_reason_counts", f"expected an object, got {type(skips).__name__}", skips)
        skips = {}
    for reason, n in skips.items():
        try:
            count = _int(n)
        except Bad as exc:
            batch.reject(0, f"skip_reason_counts.{reason}"[:200], str(exc), n)
            continue
        if count is not None:
            batch.add("stage_events", {"priority": PRIO_BOARD_SKIPS, "day": day, "stage": "boss",
                                       "outcome": "NO_ENTRY", "reason": str(reason)[:200], "n": count})
    return [file_unit.finish(), batch.finish()]


def load_eod_recon(path: Path) -> list[Batch]:
    batch = Batch(str(path))
    blob = _whole_json(path, batch)
    if blob is None:
        return [batch.finish()]
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    g = Rec(batch, 0, blob)
    scalars = {str(k)[:80]: v for k, v in blob.items()
               if (isinstance(v, (str, int, bool)) or v is None or (isinstance(v, float) and math.isfinite(v)))}
    ok = blob.get("ok")
    batch.add("recon_reports", {
        "run_id": 0, "kind": "eod_recon", "day": m.group(1) if m else g("as_of_ist", _day),
        "ts": g("as_of_ist"), "ok": None if ok is None else int(bool(ok)),
        "n_mismatches": None, "summary_json": json.dumps(dict(list(scalars.items())[:40])),
    })
    return [batch.finish()]


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
            for t in _rows(conn, "SELECT rowid AS _row, * FROM trades WHERE status IN ('CLOSED', 'CANCELLED')"):
                _record(batch, _int(t["_row"]) or 0, t,
                        lambda g: [("trades_raw", {**ledger_trade_row(g), "trade_id": _need_id(g)})], "trades.")
        if "fills" in names:
            for r in _rows(conn, "SELECT * FROM fills"):
                _record(batch, _int(r.get("id")) or 0, r, lambda g: [("fills", {
                    "fill_id": _int(g.rec["id"]), "trade_id": g("trade_id"), "client_order_id": g("client_order_id"),
                    "ts": g("ts"), "day": g("ts", _day), "symbol": g("symbol"), "side": g("side"),
                    "qty": g("qty", _int), "price": g("price", _num), "decision_price": g("decision_price", _num),
                    "slippage": g("slippage", _num),
                })], "fills.")
        if "charges" in names:
            for r in _rows(conn, "SELECT * FROM charges"):
                _record(batch, _int(r.get("id")) or 0, r, lambda g: [("charges", {
                    "charge_id": _int(g.rec["id"]), "trade_id": g("trade_id"), "client_order_id": g("client_order_id"),
                    "ts": g("ts"), "day": g("day", _day),
                    **{k: g(k, _num) for k in ("turnover", "brokerage", "stt", "exchange", "sebi", "stamp", "gst", "total")},
                })], "charges.")
        if "risk_decisions" in names:
            agg: dict[tuple[str, str, str], int] = {}

            def risk(g: Rec) -> list[tuple[str, dict[str, Any]]]:
                key = (g("day", _day) or "UNKNOWN", "APPROVED" if g.rec.get("approved") else "VETOED",
                       g("reason_code") or "")
                agg[key] = agg.get(key, 0) + 1
                return []

            for r in _rows(conn, "SELECT rowid AS _row, day, approved, reason_code FROM risk_decisions"):
                _record(batch, _int(r["_row"]) or 0, r, risk, "risk_decisions.")
            for (day, outcome, reason), n in agg.items():
                batch.add("stage_events", {"priority": PRIO_LEDGER_RISK, "day": day, "stage": "risk",
                                           "outcome": outcome, "reason": reason, "n": n})
        if "recon_runs" in names:
            def recon(g: Rec) -> list[tuple[str, dict[str, Any]]]:
                try:
                    mism = json.loads(g.rec.get("mismatches_json") or "[]")
                except (TypeError, ValueError):
                    g.batch.reject(g.line_no, g.prefix + "mismatches_json", "invalid JSON", g.rec.get("mismatches_json"))
                    mism = None
                return [("recon_reports", {
                    "run_id": _int(g.rec["id"]), "kind": "ledger_recon", "day": g("ts", _day), "ts": g("ts"),
                    "ok": int(bool(g.rec.get("ok"))), "n_mismatches": len(mism) if isinstance(mism, list) else None,
                    "summary_json": "{}",
                })]

            for r in _rows(conn, "SELECT * FROM recon_runs"):
                _record(batch, _int(r.get("id")) or 0, r, recon, "recon_runs.")
        if "events" in names:
            _load_events(conn, batch)
        return [batch.finish()] if batch.count() or batch.n_rejects else []
    finally:
        conn.close()


def _load_events(conn: sqlite3.Connection, batch: Batch) -> None:
    votes: dict[tuple[str, str, str, str], list[float]] = {}
    stages: dict[tuple[str, str, str, str], int] = {}

    def stage(day: str, name: str, outcome: str, reason: Any) -> None:
        key = (day, name, outcome, reason or "")
        stages[key] = stages.get(key, 0) + 1

    def build(g: Rec) -> list[tuple[str, dict[str, Any]]]:
        ev_type = g.rec["_type"]
        day = g("ts", _day) or g("_ts", _day) or "UNKNOWN"
        out: list[tuple[str, dict[str, Any]]] = []
        if ev_type == "ANALYST_VOTE":
            key = (day, g("underlying") or "", g("analyst_id") or "", g("signal") or "")
            acc = votes.setdefault(key, [0, 0.0])
            acc[0] += 1
            acc[1] += g("confidence", _num) or 0.0
        elif ev_type == "ENTRY_APPROVED":
            tid = _need_id(g)
            stage(day, "boss", "ENTRY_APPROVED", g("book_id"))
            models = g.rec.get("analysts") or []
            for m in [*(models if isinstance(models, list) else []), g.rec.get("book_id")]:
                name = _text(m) if isinstance(m, (str, int)) else None
                if name:
                    out.append(("trade_models", {"trade_id": tid, "model": name}))
        elif ev_type == "NO_ENTRY":
            stage(day, "boss", "NO_ENTRY", g("reason"))
        elif ev_type == "ENTRY_VETOED":
            stage(day, "risk", "VETOED", g("reason_code") or g("reason"))
        elif ev_type == "ORDER_FILLED":
            stage(day, "desk", "ORDER_FILLED", g("purpose") or g("side"))
        elif ev_type == "ORDER_REJECTED":
            stage(day, "desk", "ORDER_REJECTED", g("reason"))
        elif ev_type == "POSITION_CLOSED":
            stage(day, "desk", "POSITION_CLOSED", g("exit_reason") or g("reason"))
        return out

    for seq, ev_type, ev_ts, raw in conn.execute("SELECT seq, event_type, ts, payload_json FROM events ORDER BY seq"):
        try:
            p = json.loads(raw)
        except (TypeError, ValueError, RecursionError) as exc:
            batch.reject(int(seq), "events.payload_json", f"invalid JSON: {exc}"[:200], raw)
            continue
        if isinstance(p, dict):
            p = {**p, "_type": ev_type, "_ts": ev_ts}
        _record(batch, int(seq), p, build, "events.")
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
    if "rejects" not in {r[1] for r in conn.execute("PRAGMA table_info(etl_runs)")}:
        conn.execute("ALTER TABLE etl_runs ADD COLUMN rejects INTEGER NOT NULL DEFAULT 0")
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
                return "skipped", 0, 0
            start, first_line = consumed, data[:consumed].count(b"\n")
    batch = Batch(str(path))
    lines = data[start:end].decode("utf-8", errors="replace").splitlines()
    src.jsonl(batch, lines, first_line, path)
    batch.finish()
    with conn:
        if start == 0:
            _delete_unit(conn, str(path))
        _insert(conn, batch)
        total = batch.count() + (prev[3] if start else 0)
        _record_file(conn, str(path), src.kind, len(data), hashlib.sha256(data[:end]).hexdigest(), end, total)
    return ("tailed" if start else "loaded"), batch.count(), batch.n_rejects


def _load_whole(conn: sqlite3.Connection, src: Source, path: Path, prev: Optional[tuple]) -> tuple[str, int]:
    sidecar = path.with_name(path.name + "-wal")
    sha = _sha(path, sidecar)
    size = path.stat().st_size + (sidecar.stat().st_size if sidecar.is_file() else 0)
    if prev is not None and prev[1] == sha:
        return "skipped", 0, 0
    try:
        batches = src.whole(path)
    except sqlite3.OperationalError:
        raise  # locked / unreadable right now: an error, retried next run
    except sqlite3.DatabaseError as exc:  # not a database, corrupt: the same bytes fail every night
        batches = [Batch(str(path))]
        batches[0].reject(0, "*", f"unreadable SQLite file: {exc}"[:200])
    n = sum(b.count() for b in batches)
    with conn:
        # Exact-match delete: the board's earlier `<path>#<day>` units stay as history.
        _delete_unit(conn, str(path))
        for b in batches:
            _delete_unit(conn, b.src_file)
            _insert(conn, b)
        _record_file(conn, str(path), src.kind, size, sha, size, n)
    return "loaded", n, sum(b.n_rejects for b in batches)


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
        rows, rejects, errors, files = 0, 0, [], discover(root, sources)
        for src, path in files:
            if path.resolve() == db:
                continue
            try:
                loader = _load_jsonl if src.jsonl else _load_whole
                status, n, r = loader(conn, src, path, prev_rows.get(str(path)))
            except (OSError, sqlite3.Error) as exc:
                # Transient (unreadable now, locked): nothing recorded, so the next run retries the file.
                errors.append({"path": str(path.relative_to(root)), "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            except Exception as exc:  # noqa: BLE001 - a loader bug must not stop the other files
                errors.append({"path": str(path.relative_to(root)), "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            stats[status] += 1
            rows += n
            rejects += r
        with conn:
            conn.execute(
                "INSERT INTO etl_runs (started_at, finished_at, full_rebuild, files_seen, files_loaded, files_tailed, "
                "files_skipped, rows, errors_json, rejects) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (started, _now(), int(full), len(files), stats["loaded"], stats["tailed"], stats["skipped"], rows,
                 json.dumps(errors), rejects),
            )
        return {"ok": not errors, "db": str(db), "files_seen": len(files), **{f"files_{k}": v for k, v in stats.items()},
                "rows": rows, "rejects": rejects, "errors": errors, "orders": "never"}
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
    p_q.add_argument("what", choices=("pnl", "exit-reasons", "models", "stages", "votes", "slippage", "charges",
                                      "rejects"))
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
        "rejects": lambda: queries.rejects(db, limit=args.limit),
    }[args.what]
    print(json.dumps(fn(), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
