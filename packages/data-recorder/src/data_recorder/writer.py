"""File writer for daily JSON Lines output with rotation."""

import json
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any


class DailyJSONLWriter:
    """
    Writes records to JSON Lines (.jsonl) files with daily rotation.
    
    Pattern: data/recon/{source}/YYYYMMDD.jsonl
    Each line is a JSON object (one record per line).
    Append-only for safety (can resume after crash without overwriting).
    """
    
    def __init__(self, base_path: Path, source: str):
        """
        Args:
            base_path: Base directory (e.g., data/recon)
            source: Source name (e.g., "index_ticks", "futures_ticks")
        """
        self.base_path = base_path
        self.source = source
        self.current_date: date | None = None
        self.file_handle = None
        self.records_written = 0
    
    def _get_filepath(self, date_obj: date) -> Path:
        """Get filepath for a given date."""
        source_dir = self.base_path / self.source
        source_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{date_obj.strftime('%Y%m%d')}.jsonl"
        return source_dir / filename
    
    def write(self, record: Dict[str, Any]) -> None:
        """
        Write a record (one JSON object per line).
        
        Args:
            record: Dictionary to write as JSON
        """
        today = date.today()
        
        # Rotate file if date changed
        if self.current_date != today:
            self._close()
            self.current_date = today
            filepath = self._get_filepath(today)
            # Append mode (safe for resume after crash)
            self.file_handle = open(filepath, 'a', encoding='utf-8')
        
        # Write JSON line
        json_line = json.dumps(record, ensure_ascii=False)
        self.file_handle.write(json_line + '\n')
        self.file_handle.flush()  # Ensure written (safety vs performance trade-off)
        self.records_written += 1
    
    def _close(self) -> None:
        """Close current file handle."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
    
    def close(self) -> None:
        """Close writer (call on shutdown)."""
        self._close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
