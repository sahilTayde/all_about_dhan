"""Cutover: sqlite → postgres, row-by-row, counts + checksum. Fail-closed. Paper only."""

from __future__ import annotations

import hashlib
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ledger.postgres import connect_postgres, migrate_postgres, redact_dsn

# Views and sqlite bookkeeping are not copied. schema_version is verified, not overwritten.
SKIP_COPY = frozenset({"schema_version", "daily_pnl", "sqlite_sequence", "sqlite_stat1"})
IDENTITY = {
    "order_events": "id",
    "fills": "id",
    "charges": "id",
    "risk_decisions": "id",
    "recon_runs": "id",
    "outbox": "seq",
}


class ExportError(RuntimeError):
    """Count or checksum mismatch, or dest already has rows."""


def canonical_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, Decimal)):
        return format(Decimal(str(value)).normalize(), "f")
    text = str(value)
    try:
        return format(Decimal(text).normalize(), "f")
    except (InvalidOperation, ValueError):
        return text


def row_line(cols: list[str], row: Any) -> str:
    cells = []
    for col in cols:
        cells.append(canonical_cell(row[col] if not isinstance(row, tuple) else row[cols.index(col)]))
    return "|".join(cells)


def checksum_lines(lines: list[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(r[0]) for r in rows if r[0] not in SKIP_COPY]


def _sqlite_cols(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")]


def _sqlite_lines(conn: sqlite3.Connection, table: str, cols: list[str]) -> list[str]:
    conn.row_factory = sqlite3.Row
    order = ", ".join(cols)
    rows = conn.execute(f"SELECT {order} FROM {table} ORDER BY {order}").fetchall()
    return [row_line(cols, r) for r in rows]


def export_sqlite_to_postgres(sqlite_path: Path | str, dsn: str) -> dict[str, Any]:
    """Copy after dest migrate. Refuse if dest table already has rows. Per-table count + sha256."""
    src = sqlite3.connect(str(sqlite_path))
    src.row_factory = sqlite3.Row
    try:
        migrate_postgres(dsn)
        dest = connect_postgres(dsn)
        try:
            tables = _sqlite_tables(src)
            report: dict[str, Any] = {"ok": True, "dsn": redact_dsn(dsn), "tables": {}}
            for table in tables:
                cols = _sqlite_cols(src, table)
                lines = _sqlite_lines(src, table, cols)
                dest_n = dest.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
                if int(dest_n) != 0:
                    raise ExportError(f"{table} already has {dest_n} rows; refuse overwrite")
                if lines:
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_sql = ", ".join(cols)
                    for line in lines:
                        values = [None if cell == "NULL" else cell for cell in line.split("|")]
                        dest.execute(
                            f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})",
                            values,
                        )
                    ident = IDENTITY.get(table)
                    if ident is not None:
                        dest.execute(
                            f"SELECT setval(pg_get_serial_sequence(%s, %s), "
                            f"COALESCE((SELECT MAX({ident}) FROM {table}), 1))",
                            (table, ident),
                        )
                dest_lines = []
                for r in dest.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY {', '.join(cols)}"):
                    dest_lines.append(row_line(cols, r))
                src_sum = checksum_lines(lines)
                dest_sum = checksum_lines(dest_lines)
                if len(lines) != len(dest_lines) or src_sum != dest_sum:
                    raise ExportError(f"{table} count/checksum mismatch src={len(lines)} dest={len(dest_lines)}")
                report["tables"][table] = {"count": len(lines), "checksum": src_sum}
            return report
        finally:
            dest.close()
    finally:
        src.close()
