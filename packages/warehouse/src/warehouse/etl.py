"""V2-18 ETL: ledger/events/tapes/recorder/bench/forward → Parquet partitions + views.

Read-only sources (O_RDONLY; never rename/rewrite tapes). Never writes data/ or the
legacy sqlite. Idempotent + incremental. Paper only. IST session dates.

python -m warehouse.etl --src DIR --out DIR --session YYYY-MM-DD

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TextIO

IST = timezone(timedelta(hours=5, minutes=30))
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
    ingest_errors: int = 0
    dest_hash: str = ""


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


def _catalog(dest: Path) -> sqlite3.Connection:
    dest.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(dest / "catalog.sqlite")
    c.execute(
        "CREATE TABLE IF NOT EXISTS file_cache (path TEXT PRIMARY KEY, sha256 TEXT, kind TEXT, rows_json TEXT, skipped INTEGER)"
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


def _write_part(dest: Path, table: str, session: str, rows: list[dict[str, Any]]) -> None:
    part = dest / "parquet" / table / f"date={session}" / "part-000.jsonl"
    part.parent.mkdir(parents=True, exist_ok=True)
    tmp = part.with_name("part-000.jsonl.tmp")
    tmp.write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), default=str) + "\n" for r in rows),
        encoding="utf-8",
    )
    tmp.replace(part)


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    body = row.get("payload")
    return body if isinstance(body, dict) else row


def _cache_get(c: sqlite3.Connection, path: Path, digest: str) -> Any | None:
    row = c.execute("SELECT sha256, rows_json, skipped FROM file_cache WHERE path=?", (str(path),)).fetchone()
    return row if row and row[0] == digest else None


def _cache_put(c: sqlite3.Connection, path: Path, digest: str, kind: str, payload: Any, skipped: int) -> None:
    c.execute(
        "INSERT OR REPLACE INTO file_cache VALUES (?,?,?,?,?)",
        (str(path), digest, kind, json.dumps(payload, default=str), skipped),
    )


def _load_jsonl(path: Path, kind: str, c: sqlite3.Connection, report: EtlReport) -> list[dict[str, Any]]:
    report.files_seen += 1
    digest = file_sha256(path)
    hit = _cache_get(c, path, digest)
    if hit:
        report.files_reused += 1
        report.skipped_lines += int(hit[2])
        return list(json.loads(hit[1]))
    rows: list[dict[str, Any]] = []
    skipped = 0
    for n, obj, err in iter_jsonl(path):
        if err:
            skipped += 1
            report.skipped_files += int(n == 0)
            _err(c, kind, path, n, err)
            continue
        assert obj is not None
        rows.append(obj)
    report.files_read += 1
    report.skipped_lines += skipped
    _cache_put(c, path, digest, kind, rows, skipped)
    return rows


def _load_ledger(path: Path, c: sqlite3.Connection, report: EtlReport) -> dict[str, list[dict[str, Any]]]:
    report.files_seen += 1
    digest = file_sha256(path)
    hit = _cache_get(c, path, digest)
    if hit:
        report.files_reused += 1
        return {k: list(v) for k, v in json.loads(hit[1]).items()}
    db = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    tables = {}
    for name in ("orders", "trades"):
        try:
            tables[name] = [dict(r) for r in db.execute(f"SELECT * FROM {name}")]
        except sqlite3.Error as exc:
            tables[name] = []
            _err(c, "ledger", path, 0, f"{name}: {exc}")
    db.close()
    report.files_read += 1
    _cache_put(c, path, digest, "ledger", tables, 0)
    return tables


def _entry_loc(events: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _oi_daily(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _spreads(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _dest_hash(dest: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in dest.rglob("*") if x.is_file() and x.suffix != ".sqlite" and "duckdb" not in x.name):
        h.update(p.relative_to(dest).as_posix().encode())
        h.update(p.read_bytes())
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


def run_etl(*, src: Path, dest: Path, session: str) -> EtlReport:
    dest = assert_not_checkout_data(dest)
    report = EtlReport(session=session)
    c = _catalog(dest)
    tables: dict[str, list[dict[str, Any]]] = {n: [] for n in TABLES}
    ledger = src / "ledger.sqlite"
    if ledger.is_file():
        loaded = _load_ledger(ledger, c, report)
        tables["ledger_orders"] = loaded.get("orders", [])
        tables["ledger_trades"] = loaded.get("trades", [])
        report.source_rows["ledger_orders"] = len(tables["ledger_orders"])
        report.source_rows["ledger_trades"] = len(tables["ledger_trades"])
    for rel, kind, table in JSONL_MAP:
        path = src / rel
        gz = Path(str(path) + ".gz")
        if not path.is_file() and gz.is_file():
            path = gz
        if path.is_file():
            tables[table] = _load_jsonl(path, kind, c, report)
            report.source_rows[table] = len(tables[table])
    tables["entry_location_daily"] = _entry_loc(tables["events"], tables["ledger_trades"])
    tables["oi_cadence"] = _oi_daily(tables["oi_cadence_raw"])
    tables["spread_by_moneyness"] = _spreads(tables["quote_snapshots"])
    for name, rows in tables.items():
        _write_part(dest, name, session, rows)
        report.loaded_rows[name] = len(rows)
    c.commit()
    report.ingest_errors = int(c.execute("SELECT COUNT(*) FROM ingest_errors").fetchone()[0])
    c.close()
    _duckdb_views(dest)
    report.dest_hash = _dest_hash(dest)
    return report


def connect(dest: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for table in TABLES:
        conn.execute(f"CREATE TABLE {table} (doc TEXT)")
        for part in sorted((dest / "parquet" / table).glob("date=*/part-000.jsonl")):
            for line in part.read_text(encoding="utf-8").splitlines():
                if line:
                    conn.execute(f"INSERT INTO {table} VALUES (?)", (line,))
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
    p.add_argument("--session", required=True)
    args = p.parse_args(argv)
    print(json.dumps(run_etl(src=args.src, dest=args.out, session=args.session).__dict__, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
