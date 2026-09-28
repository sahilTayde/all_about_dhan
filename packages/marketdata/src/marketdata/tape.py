"""Crash-safe append-only JSONL tapes: ``<root>/YYYY-MM-DD/<stream>.jsonl`` (IST date).

- Lines are buffered in memory and appended with ``os.write`` on an ``O_APPEND`` descriptor
  when ``flush`` is called (the recorder calls it every second) or the buffer passes 256 KB,
  then ``fsync``ed. A kill loses at most the unflushed buffer, never earlier lines.
- With ``background=True`` the write and fsync run on one shared writer thread, so a slow
  disk never stalls the event loop (fsync can take hundreds of ms on a busy disk).
- The writer queue is bounded. A full queue applies a short put-timeout (backpressure) and
  then drops the flush; ``tape_drop_count()`` is the running total. ``close()`` waits out
  the queue so a clean stop does not drop the last buffer.
- On first open of a day file, a partial last line (or a NUL tail left by a power cut) is
  cut back to the last newline, however far back it is. What was cut is reported so it
  lands in ``ingest_errors``; the file is emptied only if it holds no newline at all.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from marketdata.clock import IST

log = logging.getLogger(__name__)

_FLUSH_BYTES = 256 * 1024
_SCAN_CHUNK = 64 * 1024
DEFAULT_QUEUE_MAX = 256
DEFAULT_PUT_TIMEOUT_S = 0.05


def _nulls(value: Any) -> Any:
    """NaN and +/-inf become null so a row is never lost for not being strict JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _nulls(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_nulls(v) for v in value]
    return value


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


class _Flusher:
    """One daemon thread that appends and fsyncs for every background TapeWriter, in order.

    Bounded queue: a slow disk applies ``put_timeout_s`` of backpressure, then drops.
    ``close()`` submits with ``wait=True`` and ``drain()`` so a clean stop flushes all.
    """

    def __init__(
        self,
        maxsize: int = DEFAULT_QUEUE_MAX,
        put_timeout_s: float = DEFAULT_PUT_TIMEOUT_S,
    ) -> None:
        if maxsize < 1:
            raise ValueError("tape queue maxsize must be >= 1")
        self.maxsize = maxsize
        self.put_timeout_s = put_timeout_s
        self._jobs: queue.Queue[tuple[int, bytes, bool]] = queue.Queue(maxsize=maxsize)
        self.dropped = 0
        self._drop_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name="tape-flusher", daemon=True)
        self._thread.start()

    def submit(self, fd: int, data: bytes, fsync: bool, *, wait: bool = False) -> bool:
        item = (fd, data, fsync)
        try:
            if wait:
                self._jobs.put(item)
            else:
                self._jobs.put(item, timeout=self.put_timeout_s)
            return True
        except queue.Full:
            with self._drop_lock:
                self.dropped += 1
                n = self.dropped
            log.warning("tape queue full (max=%d); drop #%d (%d bytes)", self.maxsize, n, len(data))
            return False

    def drain(self) -> None:
        self._jobs.join()

    def _run(self) -> None:
        while True:
            batch = [self._jobs.get()]
            while True:  # coalesce a backlog: write everything, then one fsync per file
                try:
                    batch.append(self._jobs.get_nowait())
                except queue.Empty:
                    break
            sync: list[int] = []
            for fd, data, fsync in batch:
                try:
                    if data:
                        _write_all(fd, data)
                except OSError:
                    log.exception("tape write failed (fd %d, %d bytes)", fd, len(data))
                if fsync and fd not in sync:
                    sync.append(fd)
            for fd in sync:
                try:
                    os.fsync(fd)
                except OSError:
                    log.exception("tape fsync failed (fd %d)", fd)
            for _ in batch:
                self._jobs.task_done()


_flusher: _Flusher | None = None
_flusher_lock = threading.Lock()


def tape_drop_count() -> int:
    """Flushes dropped after backpressure. 0 until a background writer is created."""
    flusher = _flusher
    return 0 if flusher is None else flusher.dropped


def reset_tape_flusher(
    *,
    maxsize: int = DEFAULT_QUEUE_MAX,
    put_timeout_s: float = DEFAULT_PUT_TIMEOUT_S,
) -> None:
    """Replace the shared flusher. Tests only; production never calls this."""
    global _flusher
    with _flusher_lock:
        old = _flusher
        if old is not None:
            old.drain()
        _flusher = _Flusher(maxsize=maxsize, put_timeout_s=put_timeout_s)


def _get_flusher(
    *,
    maxsize: int | None = None,
    put_timeout_s: float | None = None,
) -> _Flusher:
    global _flusher
    with _flusher_lock:
        if _flusher is None:
            _flusher = _Flusher(
                maxsize=maxsize if maxsize is not None else DEFAULT_QUEUE_MAX,
                put_timeout_s=put_timeout_s if put_timeout_s is not None else DEFAULT_PUT_TIMEOUT_S,
            )
        return _flusher


def repair_tail(path: Path) -> dict[str, Any] | None:
    """Cut an unterminated tail back to the last newline; return what was removed."""
    if not path.is_file() or path.stat().st_size == 0:
        return None
    with open(path, "r+b") as f:
        size = f.seek(0, os.SEEK_END)
        f.seek(size - 1)
        if f.read(1) == b"\n":
            return None
        keep, pos = 0, size
        while pos > 0:
            start = max(0, pos - _SCAN_CHUNK)
            f.seek(start)
            cut = f.read(pos - start).rfind(b"\n")
            if cut != -1:
                keep = start + cut + 1
                break
            pos = start
        f.seek(keep)
        removed = f.read()
        f.truncate(keep)
        f.flush()
        os.fsync(f.fileno())
    return {
        "reason": "unterminated tail removed on open",
        "path": str(path),
        "offset": keep,
        "removed_bytes": len(removed),
        "nul_bytes": removed.count(b"\0"),
        "sha256": hashlib.sha256(removed).hexdigest(),
        "raw_b64": base64.b64encode(removed[:4096]).decode("ascii"),
    }


class TapeWriter:
    def __init__(
        self,
        root: Path | str,
        stream: str,
        *,
        background: bool = False,
        queue_max: int | None = None,
        put_timeout_s: float | None = None,
    ) -> None:
        self.root = Path(root)
        self.stream = stream
        self.background = background
        self.path: Path | None = None
        self.rows = 0
        self._fd: int | None = None
        self._day: str | None = None
        self._buf: list[bytes] = []
        self._size = 0
        self._dirty = False
        self._queue_max = queue_max
        self._put_timeout_s = put_timeout_s

    def open(self, ts: datetime) -> dict[str, Any] | None:
        """Open (and repair) the file for ``ts``'s IST day. Returns a repair record, if any."""
        day = ts.astimezone(IST).strftime("%Y-%m-%d")
        if day == self._day and self._fd is not None:
            return None
        self.close()
        path = self.root / day / f"{self.stream}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        repaired = repair_tail(path)
        self._fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        self._day, self.path = day, path
        return repaired

    def write(self, record: dict[str, Any], ts: datetime) -> dict[str, Any] | None:
        """Buffer one row; NaN/inf are written as null."""
        try:
            text = json.dumps(record, separators=(",", ":"), allow_nan=False)
        except ValueError:
            text = json.dumps(_nulls(record), separators=(",", ":"), allow_nan=False)
        line = (text + "\n").encode()
        repaired = self.open(ts)
        self._buf.append(line)
        self._size += len(line)
        self.rows += 1
        if self._size >= _FLUSH_BYTES:
            self.flush(fsync=False)
        return repaired

    def flush(self, fsync: bool = True, *, wait: bool = False) -> None:
        if self._fd is None:
            return
        data = b"".join(self._buf)
        self._buf, self._size = [], 0
        self._dirty = self._dirty or bool(data)
        sync = fsync and self._dirty
        if sync:
            self._dirty = False
        if not data and not sync:
            return
        if self.background:
            _get_flusher(maxsize=self._queue_max, put_timeout_s=self._put_timeout_s).submit(
                self._fd, data, sync, wait=wait
            )
            return
        if data:
            _write_all(self._fd, data)
        if sync:
            os.fsync(self._fd)

    def close(self) -> None:
        if self._fd is not None:
            self.flush(wait=True)
            if self.background:
                _get_flusher().drain()
            os.close(self._fd)
        self._fd, self._day = None, None
