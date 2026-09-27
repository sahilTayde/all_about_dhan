"""Subprocess entry for crash tests: the real recorder via ``run_recorder`` (signal handling
included) against a fake feed URL, with stubbed instruments and a clock pinned to 10:00 IST.

    python md_proc_runner.py <ws-url> <tape-root> <start-iso>
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from md_fake_dhan import OffsetClock, StubSource, settings_for

from marketdata.__main__ import run_recorder, setup_logging
from marketdata.config import RecorderConfig
from marketdata.recorder import MarketDataRecorder


def main() -> int:
    url, tape_root, start = sys.argv[1], Path(sys.argv[2]), datetime.fromisoformat(sys.argv[3])
    listener = setup_logging(None)
    recorder = MarketDataRecorder(
        RecorderConfig(tape_root=tape_root, cache_dir=tape_root.parent / "cache"),
        settings_for(url, tape_root.parent),
        source=StubSource(),
        clock=OffsetClock(start),
    )
    try:
        return asyncio.run(run_recorder(recorder))
    finally:
        listener.stop()


if __name__ == "__main__":
    sys.exit(main())
