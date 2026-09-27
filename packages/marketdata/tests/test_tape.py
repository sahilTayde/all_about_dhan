"""Tests for TapeWriter (crash safety, repair)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from marketdata.tape import TapeWriter


def test_tape_write_and_read(tmp_path: Path) -> None:
    """Write and read back records."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test_stream")
    
    now = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    records = [{"id": 1}, {"id": 2}]
    
    for rec in records:
        writer.write(rec, now)
    writer.close()
    
    tape_file = tape_root / "2026-09-27" / "test_stream.jsonl"
    assert tape_file.exists()
    
    with open(tape_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    assert json.loads(lines[0]) == records[0]
    assert json.loads(lines[1]) == records[1]


def test_tape_repair_truncated_line(tmp_path: Path) -> None:
    """Truncated last line is repaired."""
    tape_root = tmp_path / "tape/v2"
    day_dir = tape_root / "2026-09-27"
    day_dir.mkdir(parents=True)
    
    tape_file = day_dir / "test.jsonl"
    with open(tape_file, "w") as f:
        f.write('{"id":1}\n')
        f.write('{"id":2}\n')
        f.write('{"id":3,"trunca')  # No newline
    
    writer = TapeWriter(tape_root, "test")
    now = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    writer.write({"id": 4}, now)
    writer.close()
    
    with open(tape_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": 1}
    assert json.loads(lines[1]) == {"id": 2}
    assert json.loads(lines[2]) == {"id": 4}


def test_tape_repair_scans_past_8kb(tmp_path: Path) -> None:
    """Repair scans back past 8KB to find last newline."""
    tape_root = tmp_path / "tape/v2"
    day_dir = tape_root / "2026-09-27"
    day_dir.mkdir(parents=True)
    
    tape_file = day_dir / "test.jsonl"
    with open(tape_file, "wb") as f:
        # Write 500 valid rows
        for i in range(500):
            f.write(f'{{"id":{i}}}\n'.encode("utf-8"))
        # Add 64KB NUL tail (simulates power loss with buffered writes)
        f.write(b"\x00" * 65536)
    
    # Repair should keep all 500 rows
    writer = TapeWriter(tape_root, "test")
    writer.close()
    
    with open(tape_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 500
    assert json.loads(lines[0]) == {"id": 0}
    assert json.loads(lines[499]) == {"id": 499}


def test_tape_reject_nan(tmp_path: Path) -> None:
    """Tape writer rejects NaN with allow_nan=False."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test")
    
    now = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    
    with pytest.raises(ValueError, match="NaN"):
        writer.write({"value": float("nan")}, now)
    
    writer.close()
