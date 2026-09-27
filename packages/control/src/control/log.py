"""Append-only founder command log. Per-line parse; a bad line never erases earlier rows."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from control.kinds import ts_of, validate_row

LOG_NAME = "founder_controls.jsonl"


@dataclass
class ReadResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    blocked_from: float | None = None
    first_bad: dict[str, Any] | None = None


def log_path(root: Path) -> Path:
    """Same directory as the v2 ledger (`data/ledger/`)."""
    return Path(root) / "data" / "ledger" / LOG_NAME


def append_command(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    """fsync one JSON object. Idempotent: a known command_id is not written again."""
    err = validate_row(row)
    if err:
        raise ValueError(err)
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    cid = str(row.get("command_id") or row["id"])
    existing = read_commands(root)
    for prev in existing.rows:
        if str(prev.get("command_id") or prev.get("id")) == cid:
            if prev.get("status") == row.get("status") and prev.get("applied_ts") == row.get("applied_ts"):
                return prev
            break
    _drop_torn_tail(path)
    line = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("ab") as fh:
        fh.write(line.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())
    return row


def _drop_torn_tail(path: Path) -> None:
    """Move an unfinished final line out of the log so the next append stays a full line."""
    if not path.exists():
        return
    blob = path.read_bytes()
    if not blob or blob.endswith(b"\n"):
        return
    cut = blob.rfind(b"\n") + 1
    torn = path.with_name(path.name + ".torn")
    with torn.open("ab") as fh:
        fh.write(blob[cut:] + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    path.write_bytes(blob[:cut])


def read_commands(root: Path, *, path: Path | None = None) -> ReadResult:
    """Load valid rows. Truncated / non-JSON / wrong-schema lines become problems."""
    src = Path(path) if path is not None else log_path(root)
    out = ReadResult()
    try:
        blob = src.read_bytes()
    except FileNotFoundError:
        return out
    lines = blob.split(b"\n")
    last_good = 0.0
    seen: set[str] = set()
    for n, raw in enumerate(lines[:-1] if lines[-1] == b"" else lines, start=1):
        if not raw.strip():
            continue
        offset = blob.find(raw)
        try:
            row = json.loads(raw.decode("utf-8"))
            err = validate_row(row)
        except Exception:
            _problem(out, f"log line {n}: not JSON", last_good, n, offset, raw)
            continue
        if err:
            _problem(out, f"log line {n}: {err}", last_good, n, offset, raw)
            continue
        last_good = max(last_good, float(ts_of(row.get("ts") or row["available_ts"])))
        cid = str(row.get("command_id") or row["id"])
        if cid in seen:
            out.rows = [r for r in out.rows if str(r.get("command_id") or r.get("id")) != cid]
        seen.add(cid)
        out.rows.append(row)
    return out


def _problem(out: ReadResult, text: str, last_good: float, line_no: int, offset: int, raw: bytes) -> None:
    out.problems.append(text)
    out.blocked_from = last_good if out.blocked_from is None else min(out.blocked_from, last_good)
    if out.first_bad is None:
        out.first_bad = {
            "line_no": line_no,
            "byte_offset": offset,
            "error": text,
            "line_sha256": hashlib.sha256(raw).hexdigest(),
        }
