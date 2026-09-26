"""Append-only SQLite audit log of every published event.

ponytail: one table next to the ledger (share `Ledger.conn`, or its own file) instead of the
DuckDB `warehouse.events` in docs/04_MIGRATION_PLAN.md; the nightly ETL can copy it across.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional, Union

from events.schema import Event

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    ts TEXT NOT NULL,
    source TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_type ON events (event_type);
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
    BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
    BEGIN SELECT RAISE(ABORT, 'event log is append-only'); END;
"""


class EventAuditLog:
    """`EventAuditLog(":memory:")`, `EventAuditLog(path)` or `EventAuditLog(ledger.conn)`."""

    def __init__(self, target: Union[str, Path, sqlite3.Connection] = ":memory:") -> None:
        if isinstance(target, sqlite3.Connection):
            self.conn = target
        else:
            if str(target) != ":memory:":
                Path(target).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(target), check_same_thread=False)
            if str(target) != ":memory:":
                # Own file only: commit without fsync per event; WAL keeps it crash-consistent.
                self.conn.execute("PRAGMA journal_mode=WAL")
                self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)

    def append(self, event: Event, raw_payload: Optional[str] = None) -> None:
        payload = raw_payload if raw_payload is not None else json.dumps(event.payload, allow_nan=False)
        with self.conn:
            self.conn.execute(
                "INSERT INTO events (event_id, event_type, ts, source, payload_json) VALUES (?, ?, ?, ?, ?)",
                (event.event_id, event.event_type, event.timestamp, event.source, payload),
            )

    def count(self, event_type: Optional[str] = None) -> int:
        if event_type:
            return self.conn.execute("SELECT COUNT(*) FROM events WHERE event_type = ?", (event_type,)).fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY event_type")
        return {k: n for k, n in rows.fetchall()}

    def rows(self, event_type: Optional[str] = None, limit: int = 1000) -> list[dict[str, Any]]:
        sql = "SELECT seq, event_id, event_type, ts, source, payload_json FROM events"
        args: tuple = ()
        if event_type:
            sql += " WHERE event_type = ?"
            args = (event_type,)
        sql += " ORDER BY seq LIMIT ?"
        cur = self.conn.execute(sql, (*args, limit))
        return [
            {"seq": r[0], "event_id": r[1], "event_type": r[2], "ts": r[3], "source": r[4], "payload": json.loads(r[5])}
            for r in cur.fetchall()
        ]
