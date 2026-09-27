"""Additive SQLite migrations for ledger v2. Never touches the legacy Monday path by default."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

IST = timezone(timedelta(hours=5, minutes=30))
CODE_SCHEMA_VERSION = 2
LEGACY_DB_NAME = "ledger.sqlite"
_DUP_COL = re.compile(r"duplicate column name", re.I)


class SchemaTooNew(RuntimeError):
    """DB schema_version is newer than this code knows (refuse to start)."""


class LegacyPathError(RuntimeError):
    """Refused to migrate the legacy Monday engine DB without an explicit flag."""


def migrations_dir() -> Path:
    """Repo path `packages/ledger/migrations` (editable install)."""
    here = Path(__file__).resolve()
    for cand in (here.parents[2] / "migrations", here.parent / "migrations"):
        if cand.is_dir():
            return cand
    raise FileNotFoundError("ledger migrations directory not found")


def is_legacy_path(path: Path | str) -> bool:
    p = Path(path)
    parts = [x.lower() for x in p.parts]
    return p.name == LEGACY_DB_NAME and "data" in parts and "ledger" in parts


def list_migration_files() -> list[Path]:
    files = sorted(migrations_dir().glob("*.sql"))
    return [f for f in files if re.match(r"^\d{3}_", f.name)]


def current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if row is None:
        return 0
    got = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(got[0] if got else 0)


def check_schema(conn: sqlite3.Connection, *, code_version: int = CODE_SCHEMA_VERSION) -> int:
    """Refuse a DB written by a newer release. Returns the on-disk version."""
    ver = current_version(conn)
    if ver > code_version:
        raise SchemaTooNew(f"schema_version {ver} > code {code_version}; refuse to start")
    return ver


def _apply_sql(conn: sqlite3.Connection, sql: str) -> None:
    # ponytail: split on ';' so one duplicate-column ALTER does not abort the rest
    for stmt in (s.strip() for s in sql.split(";")):
        if not stmt or stmt.startswith("--"):
            continue
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as exc:
            if _DUP_COL.search(str(exc)) and stmt.upper().lstrip().startswith("ALTER"):
                continue
            raise


def _record_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    stamp = datetime.now(IST).isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
        (version, stamp),
    )


def _version_of(path: Path) -> int:
    m = re.match(r"^(\d{3})_", path.name)
    return int(m.group(1)) if m else 0


def migrate(
    path: Path | str,
    *,
    allow_legacy: bool = False,
    files: Iterable[Path] | None = None,
) -> int:
    """Apply pending numbered SQL files. Returns the resulting schema_version."""
    db = Path(path)
    if is_legacy_path(db) and not allow_legacy:
        raise LegacyPathError(
            f"refusing to migrate legacy DB {db}; pass allow_legacy=True to invoke explicitly"
        )
    if str(db) != ":memory:":
        db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        check_schema(conn)
        applied = current_version(conn)
        pending = [f for f in (files if files is not None else list_migration_files()) if _version_of(f) > applied]
        for f in pending:
            _apply_sql(conn, f.read_text(encoding="utf-8"))
            _record_version(conn, _version_of(f))
            if _version_of(f) >= 2:
                conn.execute(
                    "CREATE TRIGGER IF NOT EXISTS outbox_no_update BEFORE UPDATE ON outbox "
                    "BEGIN SELECT CASE WHEN NEW.event_id != OLD.event_id OR NEW.stream != OLD.stream "
                    "OR NEW.envelope_json != OLD.envelope_json OR NEW.created_at != OLD.created_at "
                    "OR NEW.seq != OLD.seq THEN RAISE(ABORT, 'ledger is append-only') END; END"
                )
            conn.commit()
        ver = current_version(conn)
        if ver == 0:
            _record_version(conn, 0)
            conn.commit()
        return current_version(conn)
    finally:
        conn.close()
