"""JSON Lines writer with daily rotation."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


IST = timezone(timedelta(hours=5, minutes=30))


def ist_date_str() -> str:
    """Current IST date as YYYYMMDD."""
    return datetime.now(IST).strftime("%Y%m%d")


class JsonLinesWriter:
    """Append-only JSON Lines writer with daily file rotation."""

    def __init__(self, output_dir: Path, source: str, *, verbose: bool = False) -> None:
        self.output_dir = output_dir
        self.source = source
        self.verbose = verbose
        self._current_date: Optional[str] = None
        self._file_handle: Optional[Any] = None
        self._record_count = 0

    def _get_filepath(self, date_str: str) -> Path:
        """Get filepath for a given date: data/recon/{source}/YYYYMMDD.jsonl"""
        return self.output_dir / self.source / f"{date_str}.jsonl"

    def write(self, record: dict[str, Any]) -> None:
        """Write a single JSON record (one line)."""
        date_str = ist_date_str()

        # Rotate file if date changed
        if self._current_date != date_str:
            self.close()
            self._current_date = date_str
            filepath = self._get_filepath(date_str)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            # Append mode (safe to resume)
            self._file_handle = open(filepath, "a", encoding="utf-8")
            if self.verbose:
                print(f"[{self.source}] Opened {filepath}")

        # Write one JSON line
        line = json.dumps(record, default=str) + "\n"
        self._file_handle.write(line)
        self._file_handle.flush()
        self._record_count += 1

    def close(self) -> None:
        """Close current file handle."""
        if self._file_handle:
            self._file_handle.close()
            if self.verbose:
                print(f"[{self.source}] Closed file ({self._record_count} records)")
            self._file_handle = None
            self._record_count = 0

    def __enter__(self) -> JsonLinesWriter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
