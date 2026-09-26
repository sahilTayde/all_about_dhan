"""Tests for DailyJSONLWriter (file rotation, append, resume)."""

import json
import tempfile
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch

from data_recorder.writer import DailyJSONLWriter


def test_writer_creates_file():
    """Test writer creates file on first write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        writer = DailyJSONLWriter(base_path, "test_source")
        
        record = {"symbol": "TEST", "value": 123}
        writer.write(record)
        writer.close()
        
        # Check file exists
        today = date.today()
        expected_file = base_path / "test_source" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert expected_file.exists()
        
        # Check content
        with open(expected_file, 'r') as f:
            lines = f.readlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed == record


def test_writer_appends_multiple_records():
    """Test writer appends multiple records (line by line)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        writer = DailyJSONLWriter(base_path, "test_source")
        
        records = [
            {"symbol": "A", "value": 1},
            {"symbol": "B", "value": 2},
            {"symbol": "C", "value": 3}
        ]
        for record in records:
            writer.write(record)
        writer.close()
        
        # Check content
        today = date.today()
        filepath = base_path / "test_source" / f"{today.strftime('%Y%m%d')}.jsonl"
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed == records[i]


def test_writer_rotates_on_date_change():
    """Test writer creates new file when date changes (simulated)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        writer = DailyJSONLWriter(base_path, "test_source")
        
        # Write on "today"
        today = date.today()
        with patch('data_recorder.writer.date') as mock_date:
            mock_date.today.return_value = today
            writer.write({"day": "today"})
        
        # Write on "tomorrow" (simulate next day)
        tomorrow = today + timedelta(days=1)
        with patch('data_recorder.writer.date') as mock_date:
            mock_date.today.return_value = tomorrow
            writer.write({"day": "tomorrow"})
        
        writer.close()
        
        # Check two files exist
        today_file = base_path / "test_source" / f"{today.strftime('%Y%m%d')}.jsonl"
        tomorrow_file = base_path / "test_source" / f"{tomorrow.strftime('%Y%m%d')}.jsonl"
        assert today_file.exists()
        assert tomorrow_file.exists()
        
        # Check content
        with open(today_file, 'r') as f:
            lines_today = f.readlines()
        with open(tomorrow_file, 'r') as f:
            lines_tomorrow = f.readlines()
        
        assert len(lines_today) == 1
        assert json.loads(lines_today[0]) == {"day": "today"}
        
        assert len(lines_tomorrow) == 1
        assert json.loads(lines_tomorrow[0]) == {"day": "tomorrow"}


def test_writer_resumes_append_same_day():
    """Test writer appends to existing file (resume after restart)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        
        # First writer session
        writer1 = DailyJSONLWriter(base_path, "test_source")
        writer1.write({"session": 1, "record": 1})
        writer1.write({"session": 1, "record": 2})
        writer1.close()
        
        # Second writer session (same day, simulates restart)
        writer2 = DailyJSONLWriter(base_path, "test_source")
        writer2.write({"session": 2, "record": 3})
        writer2.close()
        
        # Check content (should have 3 records total, appended)
        today = date.today()
        filepath = base_path / "test_source" / f"{today.strftime('%Y%m%d')}.jsonl"
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 3
        assert json.loads(lines[0]) == {"session": 1, "record": 1}
        assert json.loads(lines[1]) == {"session": 1, "record": 2}
        assert json.loads(lines[2]) == {"session": 2, "record": 3}


def test_writer_context_manager():
    """Test writer works as context manager (auto-close)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        
        with DailyJSONLWriter(base_path, "test_source") as writer:
            writer.write({"test": "context manager"})
        
        # File should be closed and exist
        today = date.today()
        filepath = base_path / "test_source" / f"{today.strftime('%Y%m%d')}.jsonl"
        assert filepath.exists()
        
        with open(filepath, 'r') as f:
            content = f.read()
        assert "context manager" in content
