"""Bounded background tape queue: slow-disk, drop counting, clean-stop flush."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

import pytest
from marketdata.config import RecorderConfig
from marketdata.recorder import MarketDataRecorder
from marketdata.strikes import StrikeSet
from marketdata.tape import TapeWriter, reset_tape_flusher, tape_drop_count
from md_fake_dhan import ist, make_universe, read_rows, settings_for


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_tape_queue_slow_disk_simulation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_tape_flusher(maxsize=2, put_timeout_s=0.05)
    real_fsync = os.fsync

    def slow_fsync(fd: int) -> None:
        time.sleep(0.35)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", slow_fsync)
    writer = TapeWriter(tmp_path, "q", background=True)
    t0 = time.perf_counter()
    for i in range(16):
        writer.write({"i": i}, ist(10, 0))
        writer.flush()
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.5  # never block the caller for 16 * 0.35 s
    assert tape_drop_count() >= 1
    writer.close()


def test_tape_queue_drop_counting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    reset_tape_flusher(maxsize=1, put_timeout_s=0.01)
    real_fsync = os.fsync
    hold = threading.Event()
    started = threading.Event()

    def blocked_fsync(fd: int) -> None:
        started.set()
        hold.wait(timeout=2.0)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", blocked_fsync)
    writer = TapeWriter(tmp_path, "q", background=True)
    writer.write({"i": 0}, ist(10, 0))
    writer.flush()
    assert started.wait(timeout=2.0)
    for i in range(1, 8):
        writer.write({"i": i}, ist(10, 0))
        writer.flush()
    dropped = tape_drop_count()
    assert dropped >= 1
    hold.set()
    writer.close()

    rec = MarketDataRecorder(
        RecorderConfig(tape_root=tmp_path / "tape"),
        settings_for("ws://127.0.0.1:1", tmp_path),
        universe=make_universe(),
    )
    rec.strikes = StrikeSet(make_universe())
    rec.tape["feed_status"].open(ist(10, 0))
    rec._status(ist(10, 0), "UP")
    rec.tape["feed_status"].close()
    rows = read_rows(tmp_path / "tape" / "2026-09-28" / "feed_status.jsonl")
    assert rows[-1]["payload"]["tape_drops"] >= dropped
    with caplog.at_level(logging.INFO):
        rec._log_status(ist(10, 0))
    assert "tape_drops=" in caplog.text


def test_tape_queue_clean_stop_flush(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reset_tape_flusher(maxsize=32, put_timeout_s=0.05)
    real_fsync = os.fsync
    started = threading.Event()

    def slow_fsync(fd: int) -> None:
        started.set()
        time.sleep(0.2)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", slow_fsync)
    writer = TapeWriter(tmp_path, "q", background=True)
    expected = list(range(6))
    for i in expected:
        writer.write({"i": i}, ist(10, 0))
        writer.flush()
    assert started.wait(timeout=2.0)
    writer.close()
    assert tape_drop_count() == 0
    assert [r["i"] for r in _rows(tmp_path / "2026-09-28" / "q.jsonl")] == expected


def test_tape_format_byte_compatible_for_v2_03_readers(tmp_path: Path) -> None:
    """Existing envelope keys and compact JSONL; tape_drops is FEED_STATUS-only."""
    reset_tape_flusher()
    writer = TapeWriter(tmp_path, "depth_quotes", background=False)
    env = {
        "event_type": "DEPTH_QUOTE",
        "payload": {"instrument_id": "NSE_IDX:NIFTY", "ltp": 24512.35},
        "source": "marketdata",
        "event_id": "abc",
        "timestamp": "2026-09-28T10:00:00+05:30",
        "v": 2,
        "stream": "md:depth",
        "event_ts": "2026-09-28T10:00:00+05:30",
        "available_ts": "2026-09-28T10:00:00+05:30",
        "account_id": None,
        "correlation_id": None,
        "causation_id": None,
    }
    writer.write(env, ist(10, 0))
    writer.close()
    raw = (tmp_path / "2026-09-28" / "depth_quotes.jsonl").read_bytes()
    assert raw.endswith(b"\n")
    assert b"tape_drops" not in raw
    line = raw.decode()
    assert line == json.dumps(env, separators=(",", ":")) + "\n"
