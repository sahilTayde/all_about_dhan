"""Crash-safe append-only JSONL tape writer (V2-D2).

Writes to data/tape/v2/YYYY-MM-DD/ by default. Configurable root for tests.
Flushes every second. Repairs truncated last line on restart.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class TapeWriter:
    """Append-only JSONL writer with crash safety."""

    def __init__(self, tape_root: Path | str, stream_name: str) -> None:
        """
        Args:
            tape_root: Root directory for tapes (e.g. data/tape/v2 or tmp_path/tape/v2 for tests)
            stream_name: Stream name (e.g. depth_quotes, quote_snapshots, oi_cadence, raw_frames, ingest_errors)
        """
        self.tape_root = Path(tape_root)
        self.stream_name = stream_name
        self._file: Any = None  # TextIO, opened lazily
        self._current_date: str | None = None
        self._pending_lines: list[str] = []
        self._last_flush_ts: float = 0.0

    def _ensure_open(self, ts: datetime) -> None:
        """Ensure file is open for today's date. Rotate if date changed."""
        date_str = ts.strftime("%Y-%m-%d")
        if self._current_date == date_str and self._file is not None:
            return
        
        # Date changed or first open: close old file and open new one
        if self._file is not None:
            self._flush()
            self._file.close()
        
        # Create directory
        day_dir = self.tape_root / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        
        # Open file in append mode
        filepath = day_dir / f"{self.stream_name}.jsonl"
        self._file = open(filepath, "a", encoding="utf-8")
        self._current_date = date_str
        
        # Repair truncated last line if file existed
        self._repair_truncated_line(filepath)

    def _repair_truncated_line(self, filepath: Path) -> None:
        """Remove truncated last line from file if present (crash recovery)."""
        if not filepath.exists() or filepath.stat().st_size == 0:
            return
        
        with open(filepath, "r+b") as f:
            # Find last newline
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return
            
            # Read last few KB to find last complete line
            read_size = min(8192, size)
            f.seek(size - read_size)
            tail = f.read()
            
            # If file ends with \n, no truncation
            if tail.endswith(b"\n"):
                return
            
            # Find last \n before the truncated line
            last_newline = tail.rfind(b"\n")
            if last_newline == -1:
                # Entire file is one truncated line: clear it
                f.seek(0)
                f.truncate()
                return
            
            # Truncate at the last good line
            truncate_at = size - read_size + last_newline + 1
            f.seek(truncate_at)
            f.truncate()

    def write(self, record: dict[str, Any], ts: datetime) -> None:
        """Write one record. Flushes every second."""
        import time
        
        self._ensure_open(ts)
        line = json.dumps(record, separators=(",", ":")) + "\n"
        self._file.write(line)
        
        # Flush every second
        now = time.time()
        if now - self._last_flush_ts >= 1.0:
            self._flush()
            self._last_flush_ts = now

    def _flush(self) -> None:
        """Flush pending writes to disk."""
        if self._file is not None:
            self._file.flush()
            os.fsync(self._file.fileno())

    def close(self) -> None:
        """Close the tape file."""
        if self._file is not None:
            self._flush()
            self._file.close()
            self._file = None

    def __enter__(self) -> TapeWriter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
