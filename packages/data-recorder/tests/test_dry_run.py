"""Tests for dry-run mode (end-to-end with mocked Dhan client)."""

import asyncio
import json
import tempfile
from pathlib import Path

from data_recorder.config import RecorderConfig
from data_recorder.runner import DataRecorderRunner


def test_dry_run_end_to_end():
    """Test dry-run generates all expected files with correct schemas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create config
        config = RecorderConfig(output_dir=output_dir, dry_run=True, verbose=True)

        # Run recorder in dry-run mode
        runner = DataRecorderRunner(config)
        runner.start()

        # Check that files were created
        expected_sources = [
            "index_ticks",
            "futures_ticks",
            "option_chain",
            "heavyweight_ticks",
            "news",
            "global_markets",
        ]

        total_records = 0
        for source in expected_sources:
            source_dir = output_dir / source
            assert source_dir.exists(), f"Expected directory {source_dir}"

            files = list(source_dir.glob("*.jsonl"))
            assert len(files) >= 1, f"Expected at least 1 file in {source}"

            # Read and validate records
            for file in files:
                content = file.read_text()
                lines = content.strip().split("\n")

                for line in lines:
                    record = json.loads(line)
                    assert isinstance(record, dict), f"Expected dict, got {type(record)}"
                    total_records += 1

                print(f"{source}: {len(lines)} records in {file.name}")

        print(f"Total records: {total_records}")
        assert total_records > 0, "Expected at least some records"


def test_index_schema():
    """Test index ticks have correct schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        config = RecorderConfig(output_dir=output_dir, dry_run=True, verbose=False)
        runner = DataRecorderRunner(config)
        runner.start()

        # Read index ticks
        index_file = list((output_dir / "index_ticks").glob("*.jsonl"))[0]
        content = index_file.read_text()
        record = json.loads(content.strip().split("\n")[0])

        # Validate schema
        assert "symbol" in record
        assert "timestamp" in record
        assert "open" in record
        assert "high" in record
        assert "low" in record
        assert "close" in record
        # volume may be None for indices


def test_futures_schema_with_volume():
    """Test futures ticks have volume field (CRITICAL check)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        config = RecorderConfig(output_dir=output_dir, dry_run=True, verbose=False)
        runner = DataRecorderRunner(config)
        runner.start()

        # Read futures ticks
        futures_file = list((output_dir / "futures_ticks").glob("*.jsonl"))[0]
        content = futures_file.read_text()
        record = json.loads(content.strip().split("\n")[0])

        # CRITICAL: Volume must be present and non-zero
        assert "volume" in record, "Volume field missing!"
        assert record["volume"] is not None, "Volume is None!"
        assert record["volume"] > 0, "Volume is zero!"
        print(f"✅ CRITICAL check passed: futures volume = {record['volume']}")


def test_option_chain_schema_with_oi_iv_greeks():
    """Test option chain has OI, IV, greeks (CRITICAL check)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        config = RecorderConfig(output_dir=output_dir, dry_run=True, verbose=False)
        runner = DataRecorderRunner(config)
        runner.start()

        # Read option chain
        chain_file = list((output_dir / "option_chain").glob("*.jsonl"))[0]
        content = chain_file.read_text()
        record = json.loads(content.strip().split("\n")[0])

        # CRITICAL: OI, IV, greeks must be present
        assert "open_interest" in record, "OI field missing!"
        assert record["open_interest"] is not None, "OI is None!"
        assert record["open_interest"] > 0, "OI is zero!"

        assert "iv" in record, "IV field missing!"
        assert record["iv"] is not None, "IV is None!"

        assert "delta" in record, "Delta field missing!"
        assert record["delta"] is not None, "Delta is None!"

        assert "gamma" in record, "Gamma field missing!"
        assert "theta" in record, "Theta field missing!"
        assert "vega" in record, "Vega field missing!"

        print(f"✅ CRITICAL checks passed: OI={record['open_interest']}, IV={record['iv']}")


if __name__ == "__main__":
    print("Running dry-run tests...")
    test_dry_run_end_to_end()
    print("\nValidating schemas...")
    test_index_schema()
    test_futures_schema_with_volume()
    test_option_chain_schema_with_oi_iv_greeks()
    print("\n✅ All dry-run tests passed!")
