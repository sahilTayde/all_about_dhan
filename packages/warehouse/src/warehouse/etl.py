"""V2-18 ETL: ledger/events/tapes/recorder/bench/forward → Parquet partitions + views.

Read-only sources (O_RDONLY; never rename/rewrite tapes). Never writes data/ or the
legacy sqlite. Idempotent + incremental. Paper only. IST session dates.

Each kept row is partitioned by the IST date of ITS OWN event_ts (quote ts for
quotes). The caller --session string is only a trading-day gate, never a partition
key. Rows after 15:30 IST stay on that date with in_session=false. Missing or
unparseable timestamps are counted and excluded.

python -m warehouse.etl --src DIR --out DIR [--session YYYY-MM-DD]

ponytail: duckdb is the planned sink. The hashed CI lock cannot gain a pin here;
when duckdb is importable we write aad.duckdb views, else sqlite over the same JSONL.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any, TextIO

from warehouse.calendar import IST, NonTradingDay, resolve_trading_day

SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
DEFAULT_MAX_SKIP_RATIO = 0.05
TABLES = (
    "ledger_orders",
    "ledger_trades",
    "events",
    "depth_quotes",
    "quote_snapshots",
    "oi_cadence_raw",
    "recorder",
    "bench_legacy_trades",
    "forward_trades",
    "entry_location_daily",
    "oi_cadence",
    "spread_by_moneyness",
)
JSONL_MAP = (
    ("events.jsonl", "events", "events"),
    ("tape/depth.jsonl", "tapes", "depth_quotes"),
    ("tape/quotes.jsonl", "tapes", "quote_snapshots"),
    ("tape/oi_cadence.jsonl", "tapes", "oi_cadence_raw"),
    ("recorder.jsonl", "recorder", "recorder"),
    ("bench.jsonl", "bench", "bench_legacy_trades"),
    ("forward.jsonl", "forward", "forward_trades"),
)
QUOTE_TABLES = frozenset({"quote_snapshots", "depth_quotes"})
_TS_ROW = ("event_ts", "available_ts", "timestamp", "created_at", "entry_time", "opened_ts", "ts")
_TS_PAYLOAD = ("exchange_ts", "ltt", "quote_ts", "event_ts", "ts")


@dataclass
class EtlReport:
    session: str
    files_seen: int = 0
    files_read: int = 0
    files_reused: int = 0
    source_rows: dict[str, int] = field(default_factory=dict)
    loaded_rows: dict[str, int] = field(default_factory=dict)
    skipped_lines: int = 0
    skipped_files: int = 0
    missing_ts: int = 0
    ingest_errors: int = 0
    fail_closed: bool = False
    dest_hash: str = ""


class WarehouseFailClosed(RuntimeError):
    def __init__(self, report: EtlReport, reason: str) -> None:
        self.report = report
        super().__init__(reason)


def assert_not_checkout_data(path: Path) -> Path:
    resolved = path.resolve()
    cur = resolved
    while cur != cur.parent:
        if cur.name == "data" and (cur.parent / ".git").is_dir():
            raise ValueError(f"refusing to write under checkout data/: {resolved}")
        cur = cur.parent
    return resolved


def open_text_readonly(path: Path) -> TextIO:
    fd = os.open(path, os.O_RDONLY)
    raw = os.fdopen(fd, "rb")
    if path.name.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(fileobj=raw, mode="rb"), encoding="utf-8", errors="replace")
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with os.fdopen(os.open(path, os.O_RDONLY), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any] | None, str | None]]:
    try:
        with open_text_readonly(path) as fh:
            for n, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    yield n, None, f"json: {exc}"
                    continue
                if not isinstance(obj, dict):
                    yield n, None, "wrong-schema: not an object"
                    continue
                yield n, obj, None
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        yield 0, None, f"file: {type(exc).__name__}"


def parse_ts(raw: Any) -> datetime | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = float(raw)
        if value <= 0:
            return None
        seconds = value / 1000.0 if value >= 1_000_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))  # noqa: FURB162  3.11 rejects Z
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None
    return None


def row_event_ts(row: dict[str, Any], *, table: str) -> datetime | None:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    assert isinstance(payload, dict)
    keys = list(_TS_PAYLOAD) + list(_TS_ROW) if table in QUOTE_TABLES else list(_TS_ROW) + list(_TS_PAYLOAD)
    if table in QUOTE_TABLES:
        for key in ("ltt", "exchange_ts", "quote_ts"):
            found = parse_ts(payload.get(key))
            if found is not None:
                return found
    for key in keys:
        found = parse_ts(row.get(key))
        if found is not None:
            return found
        found = parse_ts(payload.get(key))
        if found is not None:
            return found
    return None


def annotate_row(row: dict[str, Any], *, table: str) -> tuple[str, dict[str, Any]] | None:
    ts = row_event_ts(row, table=table)
    if ts is None:
        return None
    ist = ts.astimezone(IST)
    out = dict(row)
    out["in_session"] = SESSION_OPEN <= ist.time() <= SESSION_CLOSE
    return ist.date().isoformat(), out


def _catalog(dest: Path) -> sqlite3.Connection:
    dest.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(dest / "catalog.sqlite")
    cols = [r[1] for r in c.execute("PRAGMA table_info(file_cache)")]
    if cols and "parts_json" not in cols:
        c.execute("DROP TABLE file_cache")
    c.execute(
        "CREATE TABLE IF NOT EXISTS file_cache ("
        "path TEXT PRIMARY KEY, sha256 TEXT, kind TEXT, loaded INTEGER, skipped INTEGER, "
        "missing_ts INTEGER, parts_json TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS ingest_errors (source TEXT, path TEXT, line_no INTEGER, byte_offset INTEGER, "
        "error TEXT, line_sha256 TEXT, first_seen TEXT, PRIMARY KEY (source, path, line_no))"
    )
    return c


def _err(c: sqlite3.Connection, source: str, path: Path, n: int, error: str) -> None:
    c.execute(
        "INSERT OR IGNORE INTO ingest_errors VALUES (?,?,?,?,?,?,?)",
        (source, str(path), n, 0, error, hashlib.sha256(error.encode()).hexdigest(), datetime.now(IST).isoformat()),
    )


def _cache_get(c: sqlite3.Connection, path: Path, digest: str) -> tuple[int, int, int, str] | None:
    row = c.execute(
        "SELECT sha256, loaded, skipped, missing_ts, parts_json FROM file_cache WHERE path=?",
        (str(path),),
    ).fetchone()
    if not row or row[0] != digest:
        return None
    return int(row[1]), int(row[2]), int(row[3]), str(row[4])


def _cache_put(
    c: sqlite3.Connection,
    path: Path,
    digest: str,
    kind: str,
    loaded: int,
    skipped: int,
    missing_ts: int,
    parts: list[dict[str, Any]],
) -> None:
    c.execute(
        "INSERT OR REPLACE INTO file_cache VALUES (?,?,?,?,?,?,?)",
        (str(path), digest, kind, loaded, skipped, missing_ts, json.dumps(parts, separators=(",", ":"))),
    )


def _parts_ok(dest: Path, parts: list[dict[str, Any]]) -> bool:
    for part in parts:
        path = dest / "parquet" / str(part["table"]) / f"date={part['date']}" / "part-000.jsonl"
        if not path.is_file() or file_sha256(path) != part["sha256"]:
            return False
    return True


class PartitionWriter:
    """Append one JSON object at a time to per-date tmp files, then atomically replace."""

    def __init__(self, dest: Path) -> None:
        self.dest = dest
        self._handles: dict[tuple[str, str], TextIO] = {}
        self._counts: dict[tuple[str, str], int] = {}

    def write(self, table: str, day: str, row: dict[str, Any]) -> None:
        key = (table, day)
        fh = self._handles.get(key)
        if fh is None:
            part_dir = self.dest / "parquet" / table / f"date={day}"
            part_dir.mkdir(parents=True, exist_ok=True)
            tmp = part_dir / "part-000.jsonl.tmp"
            if tmp.exists():
                tmp.unlink()
            fh = tmp.open("w", encoding="utf-8")
            self._handles[key] = fh
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str) + "\n")
        self._counts[key] = self._counts.get(key, 0) + 1

    def finalize(self) -> list[dict[str, Any]]:
        parts: list[dict[str, Any]] = []
        for (table, day), fh in list(self._handles.items()):
            fh.close()
            tmp = self.dest / "parquet" / table / f"date={day}" / "part-000.jsonl.tmp"
            digest = file_sha256(tmp)
            tmp.replace(tmp.with_name("part-000.jsonl"))
            parts.append({"table": table, "date": day, "sha256": digest, "rows": self._counts[(table, day)]})
        self._handles.clear()
        return parts


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    body = row.get("payload")
    return body if isinstance(body, dict) else row


def _iter_part(path: Path) -> Iterator[dict[str, Any]]:
    with open_text_readonly(path) as fh:
        for raw in fh:
            line = raw.strip()
            if line:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj


def _max_skip_ratio(override: float | None) -> float:
    if override is not None:
        return override
    raw = os.environ.get("AAD_WAREHOUSE_MAX_SKIP_RATIO", str(DEFAULT_MAX_SKIP_RATIO))
    return float(raw)


def _fail_closed(total: int, loaded: int, skipped: int, ratio: float) -> str | None:
    if total > 0 and loaded == 0:
        return "0 loaded rows from a non-empty source"
    if total > 0 and skipped / total > ratio:
        return f"skipped/total {skipped}/{total} exceeds {ratio}"
    return None


def _apply_reuse(report: EtlReport, parts: list[dict[str, Any]], skipped: int, missing_ts: int) -> None:
    report.files_reused += 1
    report.skipped_lines += skipped
    report.missing_ts += missing_ts
    for part in parts:
        table = str(part["table"])
        n = int(part["rows"])
        report.source_rows[table] = report.source_rows.get(table, 0) + n
        report.loaded_rows[table] = report.loaded_rows.get(table, 0) + n


def _load_jsonl(
    path: Path,
    kind: str,
    table: str,
    dest: Path,
    c: sqlite3.Connection,
    report: EtlReport,
    ratio: float,
    failures: list[str],
) -> None:
    report.files_seen += 1
    digest = file_sha256(path)
    hit = _cache_get(c, path, digest)
    if hit:
        loaded, skipped, missing_ts, parts_raw = hit
        parts = json.loads(parts_raw)
        if isinstance(parts, list) and _parts_ok(dest, parts):
            _apply_reuse(report, parts, skipped, missing_ts)
            return
    writer = PartitionWriter(dest)
    skipped = 0
    missing_ts = 0
    loaded = 0
    total = 0
    for n, obj, err in iter_jsonl(path):
        if err:
            if n == 0:
                report.skipped_files += 1
                _err(c, kind, path, n, err)
                break
            skipped += 1
            total += 1
            _err(c, kind, path, n, err)
            continue
        assert obj is not None
        total += 1
        stamped = annotate_row(obj, table=table)
        if stamped is None:
            missing_ts += 1
            skipped += 1
            _err(c, kind, path, n, "missing-or-unparseable-ts")
            continue
        day, row = stamped
        writer.write(table, day, row)
        loaded += 1
    parts = writer.finalize()
    report.files_read += 1
    report.skipped_lines += skipped
    report.missing_ts += missing_ts
    report.source_rows[table] = report.source_rows.get(table, 0) + loaded + missing_ts
    report.loaded_rows[table] = report.loaded_rows.get(table, 0) + loaded
    _cache_put(c, path, digest, kind, loaded, skipped, missing_ts, parts)
    reason = _fail_closed(total, loaded, skipped, ratio)
    if reason:
        failures.append(f"{path.name}: {reason}")


def _load_ledger(
    path: Path,
    dest: Path,
    c: sqlite3.Connection,
    report: EtlReport,
    ratio: float,
    failures: list[str],
) -> None:
    report.files_seen += 1
    digest = file_sha256(path)
    hit = _cache_get(c, path, digest)
    if hit:
        loaded, skipped, missing_ts, parts_raw = hit
        parts = json.loads(parts_raw)
        if isinstance(parts, list) and _parts_ok(dest, parts):
            _apply_reuse(report, parts, skipped, missing_ts)
            return
    writer = PartitionWriter(dest)
    skipped = 0
    missing_ts = 0
    loaded = 0
    total = 0
    db = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        for name, table in (("orders", "ledger_orders"), ("trades", "ledger_trades")):
            try:
                cursor = db.execute(f"SELECT * FROM {name}")
            except sqlite3.Error as exc:
                _err(c, "ledger", path, 0, f"{name}: {exc}")
                continue
            for raw in cursor:
                total += 1
                stamped = annotate_row(dict(raw), table=table)
                report.source_rows[table] = report.source_rows.get(table, 0) + 1
                if stamped is None:
                    missing_ts += 1
                    skipped += 1
                    continue
                day, row = stamped
                writer.write(table, day, row)
                loaded += 1
                report.loaded_rows[table] = report.loaded_rows.get(table, 0) + 1
    finally:
        db.close()
    parts = writer.finalize()
    report.files_read += 1
    report.skipped_lines += skipped
    report.missing_ts += missing_ts
    _cache_put(c, path, digest, "ledger", loaded, skipped, missing_ts, parts)
    reason = _fail_closed(total, loaded, skipped, ratio)
    if reason:
        failures.append(f"{path.name}: {reason}")


def _entry_loc(events: Iterator[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    net: dict[str, float] = {}
    stops: dict[str, int] = {}
    for t in trades:
        sid = str(t.get("signal_id") or "")
        net[sid] = net.get(sid, 0.0) + float(t.get("net_pnl") or 0)
        if "STOP" in str(t.get("exit_reason") or "").upper():
            stops[sid] = stops.get(sid, 0) + 1
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in events:
        if row.get("event_type") not in {"ENTRY_PLAN", "ENTRY_PLAN_RESULT"}:
            continue
        p = _payload(row)
        key = (str(p.get("action") or "CHASE"), str(p.get("zone") or "none"), str(p.get("strategy_id") or "unknown"))
        b = buckets.setdefault(key, {"n": 0, "fills": 0, "missed": 0, "giveback": 0.0, "stop_outs": 0, "net": 0.0})
        if row.get("event_type") == "ENTRY_PLAN":
            b["n"] += 1
            sid = str(p.get("signal_id") or "")
            b["net"] += net.get(sid, 0.0)
            b["stop_outs"] += stops.get(sid, 0)
        else:
            st = str(p.get("status") or "")
            b["fills"] += int(st == "FILLED")
            b["missed"] += int(st.startswith("MISSED"))
            if p.get("giveback_5m_pts") is not None:
                b["giveback"] += float(p["giveback_5m_pts"])
    out = []
    for (action, zone, strat), b in sorted(buckets.items()):
        n = max(int(b["n"]), 1)
        out.append(
            {
                "action": action,
                "zone": zone,
                "strategy_id": strat,
                "n": int(b["n"]),
                "fills": int(b["fills"]),
                "fill_rate": round(int(b["fills"]) / n, 4),
                "missed": int(b["missed"]),
                "giveback": round(float(b["giveback"]), 4),
                "stop_outs": int(b["stop_outs"]),
                "net": round(float(b["net"]), 4),
            }
        )
    return out


def _oi_daily(rows: Iterator[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        p = _payload(row)
        by.setdefault(str(p.get("instrument_id") or "unknown"), []).append(p)
    out = []
    for inst, items in sorted(by.items()):
        gaps = [float(p["median_gap_s"]) for p in items if p.get("median_gap_s") is not None]
        p90s = [float(p["p90_gap_s"]) for p in items if p.get("p90_gap_s") is not None]
        out.append(
            {
                "instrument_id": inst,
                "oi_updates": sum(int(p.get("oi_updates") or 0) for p in items),
                "median_gap_s": round(sum(gaps) / len(gaps), 4) if gaps else None,
                "p90_gap_s": round(sum(p90s) / len(p90s), 4) if p90s else None,
                "n": len(items),
            }
        )
    return out


def _spreads(rows: Iterator[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, list[float]] = {}
    for row in rows:
        p = _payload(row)
        if p.get("spread") is None:
            continue
        by.setdefault(str(p.get("rule") or "ATM"), []).append(float(p["spread"]))
    out = []
    for rule, vals in sorted(by.items()):
        ordered = sorted(vals)
        out.append(
            {
                "rule": rule,
                "n": len(vals),
                "avg_spread": round(sum(vals) / len(vals), 4),
                "p90_spread": ordered[min(len(ordered) - 1, round(0.9 * (len(ordered) - 1)))],
            }
        )
    return out


def _in_session_rows(path: Path) -> Iterator[dict[str, Any]]:
    for row in _iter_part(path):
        if row.get("in_session") is True:
            yield row


def _part(dest: Path, table: str, day: str) -> Path:
    return dest / "parquet" / table / f"date={day}" / "part-000.jsonl"


def _dates_with_parts(dest: Path) -> list[str]:
    days: set[str] = set()
    root = dest / "parquet"
    if not root.is_dir():
        return []
    for table in ("events", "ledger_trades", "quote_snapshots", "oi_cadence_raw"):
        for part in (root / table).glob("date=*/part-000.jsonl"):
            days.add(part.parent.name.removeprefix("date="))
    return sorted(days)


def _write_derived(dest: Path, report: EtlReport) -> None:
    writer = PartitionWriter(dest)
    loc_n = oi_n = spr_n = 0
    for day in _dates_with_parts(dest):
        events_p, trades_p = _part(dest, "events", day), _part(dest, "ledger_trades", day)
        quotes_p, oi_p = _part(dest, "quote_snapshots", day), _part(dest, "oi_cadence_raw", day)
        trades = list(_in_session_rows(trades_p)) if trades_p.is_file() else []
        events = _in_session_rows(events_p) if events_p.is_file() else iter(())
        for row in _entry_loc(events, trades):
            writer.write("entry_location_daily", day, row)
            loc_n += 1
        if oi_p.is_file():
            for row in _oi_daily(_in_session_rows(oi_p)):
                writer.write("oi_cadence", day, row)
                oi_n += 1
        if quotes_p.is_file():
            for row in _spreads(_in_session_rows(quotes_p)):
                writer.write("spread_by_moneyness", day, row)
                spr_n += 1
    writer.finalize()
    report.loaded_rows["entry_location_daily"] = loc_n
    report.loaded_rows["oi_cadence"] = oi_n
    report.loaded_rows["spread_by_moneyness"] = spr_n


def _dest_hash(dest: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in dest.rglob("*") if x.is_file()):
        if p.suffix in {".sqlite", ".tmp"} or "duckdb" in p.name:
            continue
        h.update(p.relative_to(dest).as_posix().encode())
        with os.fdopen(os.open(p, os.O_RDONLY), "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()


def _duckdb_views(dest: Path) -> None:
    try:
        import duckdb  # type: ignore[import-not-found]
    except ImportError:
        return
    con = duckdb.connect(str(dest / "aad.duckdb"))
    for table in TABLES:
        glob = str(dest / "parquet" / table / "*" / "part-000.jsonl")
        con.execute(f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_json_auto('{glob}', union_by_name=true)")
    con.close()


def run_etl(
    *,
    src: Path,
    dest: Path,
    session: str | None = None,
    now: datetime | None = None,
    max_skip_ratio: float | None = None,
) -> EtlReport:
    dest = assert_not_checkout_data(dest)
    clock = now or datetime.now(IST)
    day = resolve_trading_day(session, clock)
    report = EtlReport(session=day.isoformat())
    ratio = _max_skip_ratio(max_skip_ratio)
    c = _catalog(dest)
    failures: list[str] = []
    ledger = src / "ledger.sqlite"
    if ledger.is_file():
        _load_ledger(ledger, dest, c, report, ratio, failures)
    for rel, kind, table in JSONL_MAP:
        path = src / rel
        gz = Path(str(path) + ".gz")
        if not path.is_file() and gz.is_file():
            path = gz
        if path.is_file():
            _load_jsonl(path, kind, table, dest, c, report, ratio, failures)
    _write_derived(dest, report)
    c.commit()
    report.ingest_errors = int(c.execute("SELECT COUNT(*) FROM ingest_errors").fetchone()[0])
    c.close()
    if failures:
        report.fail_closed = True
        raise WarehouseFailClosed(report, "; ".join(failures))
    _duckdb_views(dest)
    report.dest_hash = _dest_hash(dest)
    return report


def connect(dest: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for table in TABLES:
        conn.execute(f"CREATE TABLE {table} (doc TEXT)")
        for part in sorted((dest / "parquet" / table).glob("date=*/part-000.jsonl")):
            with open_text_readonly(part) as fh:
                for line in fh:
                    if line.strip():
                        conn.execute(f"INSERT INTO {table} VALUES (?)", (line.strip(),))
    return conn


def attribution_chain(dest: Path) -> list[dict[str, Any]]:
    conn = connect(dest)
    sigs, decs, orders, trades = [], [], [], []
    for (doc,) in conn.execute("SELECT doc FROM events"):
        row = json.loads(doc)
        p = _payload(row)
        if row.get("event_type") == "SIGNAL":
            sigs.append(p)
        elif row.get("event_type") == "DECISION":
            decs.append(p)
    for (doc,) in conn.execute("SELECT doc FROM ledger_orders"):
        orders.append(json.loads(doc))
    for (doc,) in conn.execute("SELECT doc FROM ledger_trades"):
        trades.append(json.loads(doc))
    conn.close()
    out = []
    for s in sigs:
        sid = s.get("signal_id")
        d = next((x for x in decs if sid in (x.get("signal_ids") or [])), None)
        o = next(
            (x for x in orders if d and (x.get("decision_id") == d.get("decision_id") or x.get("signal_id") == sid)),
            None,
        )
        t = next(
            (
                x
                for x in trades
                if o and (x.get("entry_client_order_id") == o.get("client_order_id") or x.get("signal_id") == sid)
            ),
            None,
        )
        if d and o and t:
            out.append(
                {
                    "signal_id": sid,
                    "decision_id": d.get("decision_id"),
                    "client_order_id": o.get("client_order_id"),
                    "trade_id": t.get("trade_id"),
                    "net_pnl": t.get("net_pnl"),
                }
            )
    return out


def list_ingest_errors(dest: Path) -> list[dict[str, Any]]:
    c = sqlite3.connect(dest / "catalog.sqlite")
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("SELECT * FROM ingest_errors ORDER BY path, line_no")]
    c.close()
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="V2-18 warehouse ETL (paper; read-only sources)")
    p.add_argument("--src", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--session", default=None, help="optional YYYY-MM-DD trading day (else derived from --now)")
    p.add_argument("--now", default=None, help="tz-aware ISO timestamp used when --session is omitted")
    p.add_argument("--max-skip-ratio", type=float, default=None)
    args = p.parse_args(argv)
    clock = datetime.fromisoformat(args.now) if args.now else datetime.now(IST)
    try:
        report = run_etl(
            src=args.src,
            dest=args.out,
            session=args.session,
            now=clock,
            max_skip_ratio=args.max_skip_ratio,
        )
    except NonTradingDay as exc:
        print(json.dumps({"error": "non-trading-day", "detail": str(exc)}, sort_keys=True))
        return 2
    except WarehouseFailClosed as exc:
        print(json.dumps({**exc.report.__dict__, "error": str(exc)}, sort_keys=True, default=str))
        return 1
    print(json.dumps(report.__dict__, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
