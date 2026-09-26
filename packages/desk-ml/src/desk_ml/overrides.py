"""Human paper overrides as an append-only, timestamped, session-scoped log.

``human_overrides.jsonl`` rows: ``{ts, session, action, trade_id, underlying, side, target, stop}``.
A replay applies each row once, at the first tick at or after ``ts`` in the same IST session
where a matching open ticket exists. ``CLEAR`` is a new row that drops earlier rows not yet
applied; nothing is ever deleted. The engine never writes this file, so re-replaying the day
(live loop, lab, parity) gives the same result every time.

Without a log, an active ``human_trade_override.json`` with an ``as_of_ist`` counts as a single
row at that time. An undated legacy file cannot be placed in time: replays ignore it and the
live loop stamps it when it first sees it (``ingest_legacy``).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from desk_ml.reliability import append_line, read_jsonl

IST = timezone(timedelta(hours=5, minutes=30))
LOG_NAME = "human_overrides.jsonl"
VIEW_NAME = "human_trade_override.json"
ROW_KEYS = ("action", "trade_id", "underlying", "side", "target", "stop")


def log_path(root: Path) -> Path:
    return Path(root) / "data" / "recon" / LOG_NAME


def view_path(root: Path) -> Path:
    return Path(root) / "data" / "recon" / VIEW_NAME


def session_of(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), IST).date().isoformat()


def make_row(payload: dict[str, Any], *, ts: float, source: str) -> dict[str, Any]:
    return {"ts": float(ts), "session": session_of(ts), **{k: payload.get(k) for k in ROW_KEYS}, "source": source}


def append_override(root: Path, payload: dict[str, Any], *, ts: float, source: str = "api") -> dict[str, Any]:
    row = make_row(payload, ts=ts, source=source)
    append_line(log_path(root), json.dumps(row, default=str))
    return row


def _legacy_rows(root: Path) -> list[dict[str, Any]]:
    try:
        blob = json.loads(view_path(root).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        raise ValueError("human override view is unreadable") from None
    if not isinstance(blob, dict) or not blob.get("active", True) or not blob.get("ok", True):
        return []
    try:
        ts = datetime.fromisoformat(str(blob["as_of_ist"])).timestamp()
    except (KeyError, TypeError, ValueError):
        return []
    return [make_row(blob, ts=ts, source="legacy_view")]


def read_overrides(root: Optional[Path]) -> list[dict[str, Any]]:
    """Every override row, oldest first. Raises ValueError when the log or view is corrupt."""
    if root is None:
        return []
    rows = read_jsonl(log_path(root))
    if rows is None:
        return _legacy_rows(Path(root))
    out = []
    for n, row in enumerate(rows):
        try:
            out.append({**row, "ts": float(row["ts"]), "action": str(row.get("action") or "").upper(),
                        "session": str(row.get("session") or session_of(float(row["ts"])))})
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"human override log row {n + 1} has no timestamp") from None
    return sorted(out, key=lambda r: r["ts"])


def ingest_legacy(root: Path, *, ts: float) -> Optional[dict[str, Any]]:
    """Live loop only: an active undated view with no log row becomes a row stamped ``ts``."""
    if log_path(root).exists():
        return None
    try:
        blob = json.loads(view_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(blob, dict) or not blob.get("active", True) or not blob.get("ok", True):
        return None
    stamp = ts
    try:
        stamp = datetime.fromisoformat(str(blob["as_of_ist"])).timestamp()
    except (KeyError, TypeError, ValueError):
        pass
    return append_override(root, blob, ts=stamp, source="legacy_view")


class OverrideBook:
    """One replay's view of the log: which rows apply to which ticket, each applied once."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = [r for r in rows if r.get("action") != "CLEAR"]
        self.clears = [r for r in rows if r.get("action") == "CLEAR"]
        self.used: set[int] = set()
        self.applied: list[dict[str, Any]] = []

    def _cleared(self, row: dict[str, Any], ts: float) -> bool:
        return any(c["session"] == row["session"] and row["ts"] < c["ts"] <= ts for c in self.clears)

    def pending_for(self, pos: Any, underlying: str, ts: int) -> Optional[tuple[int, dict[str, Any]]]:
        session = session_of(ts)
        for n, row in enumerate(self.rows):
            if row["ts"] > ts:
                break
            if n in self.used or row["session"] != session or self._cleared(row, ts):
                continue
            if row.get("trade_id") and row.get("trade_id") != pos.trade_id:
                continue
            if row.get("underlying") and str(row.get("underlying")).upper() != underlying.upper():
                continue
            if row.get("side") and str(row.get("side")).upper() != pos.side:
                continue
            return n, row
        return None

    def consume(self, n: int, row: dict[str, Any], *, ts: int, trade_id: str) -> None:
        self.used.add(n)
        self.applied.append({"row_ts": row["ts"], "applied_ts": int(ts), "trade_id": trade_id, "action": row.get("action")})
