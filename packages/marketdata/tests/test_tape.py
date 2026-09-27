"""Tests for TapeWriter (V2-D2 acceptance test 7)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from marketdata.tape import TapeWriter


def test_tape_write_and_read(tmp_path: Path) -> None:
    """Write records and read them back."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test_stream")
    
    now = datetime(2026, 9, 27, 10, 0, 0)
    records = [
        {"id": 1, "value": "foo"},
        {"id": 2, "value": "bar"},
    ]
    
    for rec in records:
        writer.write(rec, now)
    writer.close()
    
    # Read back
    tape_file = tape_root / "2026-09-27" / "test_stream.jsonl"
    assert tape_file.exists()
    
    with open(tape_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    assert json.loads(lines[0]) == records[0]
    assert json.loads(lines[1]) == records[1]


def test_tape_repair_truncated_line(tmp_path: Path) -> None:
    """Truncated last line is repaired on restart (acceptance test 7)."""
    tape_root = tmp_path / "tape/v2"
    day_dir = tape_root / "2026-09-27"
    day_dir.mkdir(parents=True)
    
    tape_file = day_dir / "test_stream.jsonl"
    
    # Write good lines and one truncated line
    with open(tape_file, "w") as f:
        f.write('{"id": 1}\n')
        f.write('{"id": 2}\n')
        f.write('{"id": 3, "trunca')  # No newline, incomplete JSON
    
    # Open writer (should repair)
    writer = TapeWriter(tape_root, "test_stream")
    now = datetime(2026, 9, 27, 10, 0, 0)
    writer.write({"id": 4}, now)
    writer.close()
    
    # Read back
    with open(tape_file) as f:
        lines = f.readlines()
    
    # Should have only good lines: 1, 2, and the new 4
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"id": 1}
    assert json.loads(lines[1]) == {"id": 2}
    assert json.loads(lines[2]) == {"id": 4}


def test_tape_date_rotation(tmp_path: Path) -> None:
    """Tape rotates to new file on date change."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test_stream")
    
    day1 = datetime(2026, 9, 27, 10, 0, 0)
    day2 = datetime(2026, 9, 28, 10, 0, 0)
    
    writer.write({"day": 1}, day1)
    writer.write({"day": 2}, day2)
    writer.close()
    
    # Check two files created
    file1 = tape_root / "2026-09-27" / "test_stream.jsonl"
    file2 = tape_root / "2026-09-28" / "test_stream.jsonl"
    
    assert file1.exists()
    assert file2.exists()
    
    with open(file1) as f:
        assert json.loads(f.read()) == {"day": 1}
    
    with open(file2) as f:
        assert json.loads(f.read()) == {"day": 2}


def test_tape_never_writes_outside_root(tmp_path: Path) -> None:
    """Tape never writes outside the configured root."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test_stream")
    
    now = datetime(2026, 9, 27, 10, 0, 0)
    writer.write({"test": 1}, now)
    writer.close()
    
    # Verify file is under tape_root
    tape_file = tape_root / "2026-09-27" / "test_stream.jsonl"
    assert tape_file.exists()
    assert tape_root in tape_file.parents


def test_tape_flush_on_close(tmp_path: Path) -> None:
    """Tape flushes on close (crash safety)."""
    tape_root = tmp_path / "tape/v2"
    writer = TapeWriter(tape_root, "test_stream")
    
    now = datetime(2026, 9, 27, 10, 0, 0)
    writer.write({"test": 1}, now)
    # Don't call close explicitly, but verify flush happens
    writer._flush()
    
    tape_file = tape_root / "2026-09-27" / "test_stream.jsonl"
    assert tape_file.exists()
    
    with open(tape_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"test": 1}
    
    writer.close()
