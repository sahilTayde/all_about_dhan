"""Durable storage for founder commands: an append-only JSONL log, fsync'd on every append.

* ``data/recon/founder_controls.jsonl``: every command the API accepted or rejected. One JSON
  object per line. A command is acknowledged only after its line is on disk (``fsync``).
* A final line without ``\\n`` is a write that never finished (never acknowledged). Readers skip
  it; the next append moves it to ``founder_controls.torn`` so it cannot become a corrupt line in
  the middle of the log.
* When the log cannot be written (disk full, permissions), exit commands (cut loss, kill) go to a
  spool in RAM-backed storage (``/dev/shm`` when present). The engine reads log + spool, and the
  next successful append drains the spool into the log. Exits are never refused for lack of disk.
* ``founder_controls_status.jsonl``: the engine's acks (applied / rejected), written by the live
  loop. Best effort: engine behaviour never depends on it.
* ``founder_account.json``: current account view (funds added, minimum capital) for the UI.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

from desk_ml.founder_commands.book import EXIT_KINDS, validate_row

try:  # POSIX (Mac, Linux VPS). Without it a single API process still serialises through its lock.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

RECON = Path("data") / "recon"
LOG_NAME = "founder_controls.jsonl"
TORN_NAME = "founder_controls.torn"
STATUS_NAME = "founder_controls_status.jsonl"
ACCOUNT_NAME = "founder_account.json"
SPOOL_ENV = "AAD_FOUNDER_SPOOL_DIR"


def log_path(root: Path) -> Path:
    return Path(root) / RECON / LOG_NAME


def status_path(root: Path) -> Path:
    return Path(root) / RECON / STATUS_NAME


def account_path(root: Path) -> Path:
    return Path(root) / RECON / ACCOUNT_NAME


def spool_path(root: Path) -> Path:
    base = os.environ.get(SPOOL_ENV) or ("/dev/shm" if Path("/dev/shm").is_dir() else tempfile.gettempdir())
    key = hashlib.sha1(str(Path(root).resolve()).encode()).hexdigest()[:12]
    return Path(base) / "aad_founder_controls" / f"{key}.jsonl"


@dataclass
class ReadResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    # Entries are blocked from here on. Lines are appended in time order, so a bad line was written
    # after the last good line before it: trades booked before that stay as they were.
    blocked_from: Optional[float] = None

    def problem(self, text: str, since: float) -> None:
        self.problems.append(text)
        self.blocked_from = since if self.blocked_from is None else min(self.blocked_from, since)


def _parse(blob: bytes, label: str, out: ReadResult, seen: set[str]) -> None:
    lines = blob.split(b"\n")
    last_good = 0.0
    for n, raw in enumerate(lines[:-1], start=1):  # lines[-1] is b"" or an unfinished write
        if not raw.strip():
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            out.problem(f"{label} line {n}: not JSON", last_good)
            continue
        err = validate_row(row)
        if err:
            out.problem(f"{label} line {n}: {err}", last_good)
            continue
        last_good = max(last_good, float(row["ts"]))
        if row["id"] in seen:  # idempotent: the first write of an id wins
            continue
        seen.add(row["id"])
        out.rows.append(row)


def _read_bytes(path: Path) -> Optional[bytes]:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def read_commands(root: Path, *, path: Optional[Path] = None, spool: bool = True) -> ReadResult:
    """Every valid command (log, then spool), plus a problem per unreadable or invalid line."""
    out, seen = ReadResult(), set()
    sources = [(Path(path) if path is not None else log_path(root), "log")]
    if spool and path is None:
        sources.append((spool_path(root), "spool"))
    for src, label in sources:
        try:
            blob = _read_bytes(src)
        except OSError as exc:  # a directory at the path, permission denied, I/O error
            out.problem(f"{label} unreadable: {type(exc).__name__}", 0.0)
            continue
        if blob is not None:
            _parse(blob, label, out, seen)
    return out


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield fd
    finally:
        os.close(fd)  # closing releases the lock


def _fsync_dir(path: Path) -> None:
    with contextlib.suppress(OSError):
        dfd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


def _existing(fd: int) -> tuple[bytes, dict[str, dict[str, Any]]]:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        b = os.read(fd, 1 << 20)
        if not b:
            break
        chunks.append(b)
    blob = b"".join(chunks)
    out, ids = ReadResult(), set()
    _parse(blob, "log", out, ids)
    return blob, {r["id"]: r for r in out.rows}


def _drop_torn_tail(path: Path, fd: int, blob: bytes) -> None:
    """Move an unfinished (never acknowledged) final line out of the log before appending."""
    if not blob or blob.endswith(b"\n"):
        return
    cut = blob.rfind(b"\n") + 1
    with open(path.with_name(TORN_NAME), "ab") as fh:
        fh.write(blob[cut:] + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.ftruncate(fd, cut)


def _write_line(fd: int, row: dict[str, Any]) -> None:
    data = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]
    os.fsync(fd)


def append_command(root: Path, row: dict[str, Any]) -> tuple[dict[str, Any], bool, str]:
    """Durably append one validated row. Returns ``(row, duplicate, where)``.

    ``duplicate``: a row with this id already exists; the stored row is returned unchanged.
    ``where``: ``"log"`` or ``"spool"``. Raises ``OSError`` when the command could not be stored
    anywhere (callers must report it as NOT recorded), ``ValueError`` for an invalid row.
    """
    err = validate_row(row)
    if err:
        raise ValueError(err)
    path = log_path(root)
    try:
        created = not path.exists()
        with _locked(path) as fd:
            blob, existing = _existing(fd)
            if row["id"] in existing:
                return existing[row["id"]], True, "log"
            _drop_torn_tail(path, fd, blob)
            for spooled in _read_spool(root):
                if spooled["id"] not in existing and spooled["id"] != row["id"]:
                    _write_line(fd, spooled)
                    existing[spooled["id"]] = spooled
            _write_line(fd, row)
        if created:
            _fsync_dir(path.parent)
        with contextlib.suppress(OSError):
            spool_path(root).unlink()
        return row, False, "log"
    except OSError:
        if row.get("kind") not in EXIT_KINDS or row.get("status") == "rejected":
            raise
    spooled_rows = {r["id"]: r for r in _read_spool(root)}
    if row["id"] in spooled_rows:
        return spooled_rows[row["id"]], True, "spool"
    with _locked(spool_path(root)) as fd:
        _write_line(fd, row)
    return row, False, "spool"


def _read_spool(root: Path) -> list[dict[str, Any]]:
    out, seen = ReadResult(), set()
    try:
        blob = _read_bytes(spool_path(root))
    except OSError:
        return []
    if blob:
        _parse(blob, "spool", out, seen)
    return out.rows


# ------------------------------------------------------------------ engine acks


def read_statuses(root: Path) -> dict[str, dict[str, Any]]:
    """Latest engine ack per command id. Unreadable lines are ignored (advisory file)."""
    out: dict[str, dict[str, Any]] = {}
    try:
        blob = _read_bytes(status_path(root)) or b""
    except OSError:
        return out
    for raw in blob.split(b"\n")[:-1]:
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def append_statuses(root: Path, results: list[dict[str, Any]]) -> int:
    """Append acks that changed since the last write. Never raises: the engine must keep going."""
    try:
        have = read_statuses(root)
        new = [
            r for r in results
            if r.get("status") in {"applied", "rejected"}
            and (have.get(r["id"], {}).get("status"), have.get(r["id"], {}).get("status_reason"))
            != (r.get("status"), r.get("status_reason"))
        ]
        if not new:
            return 0
        with _locked(status_path(root)) as fd:
            for r in new:
                _write_line(fd, r)
        return len(new)
    except OSError:
        return 0


def write_account_view(root: Path, account: dict[str, Any]) -> bool:
    """Atomic replace (tmp in the same dir, fsync, rename). Never raises."""
    path = account_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{ACCOUNT_NAME}.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(account, fh, indent=2, sort_keys=True)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        _fsync_dir(path.parent)
        return True
    except OSError:
        return False
