"""Crash-safe append-only JSONL tape writer (V2-D2)."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from marketdata.utils import ist_date_str


class TapeWriter:
    """Append-only JSONL writer with crash safety."""

    def __init__(self, tape_root: Path, stream_name: str) -> None:
        self.tape_root = Path(tape_root)
        self.stream_name = stream_name
        self._file: Any = None
        self._current_date: str | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._should_stop = False
        
        # Repair existing files on init (crash recovery)
        self._repair_existing_files()

    def _ensure_open(self, ts: datetime) -> None:
        """Ensure file is open for today's date."""
        date_str = ist_date_str(ts)
        if self._current_date == date_str and self._file is not None:
            return

        if self._file is not None:
            self._flush()
            self._file.close()

        day_dir = self.tape_root / date_str
        day_dir.mkdir(parents=True, exist_ok=True)

        filepath = day_dir / f"{self.stream_name}.jsonl"
        
        # Repair BEFORE opening for append
        self._repair_truncated_line(filepath)
        
        self._file = open(filepath, "a", encoding="utf-8")
        self._current_date = date_str

    def _repair_existing_files(self) -> None:
        """Repair all existing JSONL files for this stream (crash recovery on init)."""
        if not self.tape_root.exists():
            return
        
        # Find all day directories
        for day_dir in self.tape_root.iterdir():
            if not day_dir.is_dir():
                continue
            filepath = day_dir / f"{self.stream_name}.jsonl"
            if filepath.exists():
                self._repair_truncated_line(filepath)
    
    def _repair_truncated_line(self, filepath: Path) -> None:
        """Remove truncated last line (crash recovery). Scan back past 8KB."""
        if not filepath.exists():
            return

        with open(filepath, "r+b") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return

            # Strip NUL tail first
            while size > 0:
                f.seek(size - 1)
                if f.read(1) != b"\x00":
                    break
                size -= 1
            if size == 0:
                f.truncate(0)
                return
            # Truncate after stripping NUL tail
            f.truncate(size)

            # Check if ends with newline
            f.seek(size - 1)
            if f.read(1) == b"\n":
                return

            # Scan back to find last newline (scan whole file if needed)
            chunk_size = 8192
            pos = size
            while pos > 0:
                read_size = min(chunk_size, pos)
                f.seek(pos - read_size)
                chunk = f.read(read_size)
                newline_pos = chunk.rfind(b"\n")
                if newline_pos != -1:
                    # Found it
                    truncate_at = pos - read_size + newline_pos + 1
                    f.seek(truncate_at)
                    f.truncate()
                    return
                pos -= read_size

            # No newline found anywhere - file is one giant truncated line
            f.seek(0)
            f.truncate()

    def write(self, record: dict[str, Any], ts: datetime) -> None:
        """Write one record."""
        self._ensure_open(ts)
        try:
            line = json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n"
        except ValueError as e:
            # NaN/Inf not allowed
            raise ValueError(f"Cannot serialize record with NaN/Inf: {e}")
        self._file.write(line)

    def _flush(self) -> None:
        """Flush pending writes to disk."""
        if self._file is not None:
            self._file.flush()
            os.fsync(self._file.fileno())

    async def start_flush_timer(self) -> None:
        """Start background flush every 1s."""
        while not self._should_stop:
            await asyncio.sleep(1.0)
            self._flush()

    def close(self) -> None:
        """Close the tape file."""
        self._should_stop = True
        if self._flush_task:
            self._flush_task.cancel()
        if self._file is not None:
            self._flush()
            self._file.close()
            self._file = None

    def __enter__(self) -> TapeWriter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
