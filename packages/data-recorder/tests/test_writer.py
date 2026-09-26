"""Tests for JSON Lines writer."""

import json
import tempfile
from pathlib import Path

from data_recorder.writer import JsonLinesWriter


def test_writer_creates_file():
    """Test that writer creates .jsonl file on first write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        writer = JsonLinesWriter(output_dir, "test_source", verbose=False)

        record = {"symbol": "NIFTY", "price": 19800.0}
        writer.write(record)
        writer.close()

        # Check file exists
        files = list((output_dir / "test_source").glob("*.jsonl"))
        assert len(files) == 1, "Expected 1 .jsonl file"

        # Check content
        content = files[0].read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1, "Expected 1 line"

        parsed = json.loads(lines[0])
        assert parsed["symbol"] == "NIFTY"
        assert parsed["price"] == 19800.0


def test_writer_appends_multiple_records():
    """Test that writer appends line-by-line (not array)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        writer = JsonLinesWriter(output_dir, "test_source", verbose=False)

        records = [
            {"symbol": "NIFTY", "price": 19800.0},
            {"symbol": "BANKNIFTY", "price": 45000.0},
            {"symbol": "SENSEX", "price": 66000.0},
        ]

        for record in records:
            writer.write(record)

        writer.close()

        # Check content
        files = list((output_dir / "test_source").glob("*.jsonl"))
        content = files[0].read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3, "Expected 3 lines"

        # Parse each line
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["symbol"] == records[i]["symbol"]


def test_writer_context_manager():
    """Test that writer auto-closes with context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        with JsonLinesWriter(output_dir, "test_source", verbose=False) as writer:
            writer.write({"test": "data"})

        # File should be closed and written
        files = list((output_dir / "test_source").glob("*.jsonl"))
        assert len(files) == 1
        assert files[0].read_text().strip()


if __name__ == "__main__":
    test_writer_creates_file()
    test_writer_appends_multiple_records()
    test_writer_context_manager()
    print("All writer tests passed!")
