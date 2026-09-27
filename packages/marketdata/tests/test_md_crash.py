"""kill -9 mid-write, restart, SIGTERM: no corrupt line, nothing earlier lost, clean exit."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from md_fake_dhan import FakeDhanServer, Market, ist, make_universe

HERE = Path(__file__).parent


class ServerThread:
    """Fake feed in its own thread, streaming 20 Hz per subscribed instrument in real time."""

    def __init__(self) -> None:
        self.url = ""
        self.connections = 0
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=lambda: asyncio.run(self._main()), daemon=True)

    def __enter__(self) -> ServerThread:
        self._thread.start()
        assert self._ready.wait(10)
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(10)

    async def _main(self) -> None:
        async with FakeDhanServer() as server:
            self.url = server.url
            self._ready.set()
            start = time.monotonic()
            market = Market(make_universe(), lambda t: 24512.35 + (t.timestamp() % 7), default_hz=20.0)
            while not self._stop.is_set():
                now = ist(10, 0, time.monotonic() - start)
                for frame in market.frames(now, server.subscribed if server.client_count else {}):
                    await server.send(frame)
                self.connections = server.connections
                await asyncio.sleep(0.02)


def spawn(url: str, tape: Path, start: datetime) -> subprocess.Popen[bytes]:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(HERE), os.environ.get("PYTHONPATH", "")])}
    return subprocess.Popen(
        [sys.executable, str(HERE / "md_proc_runner.py"), url, str(tape), start.isoformat()],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def wait_rows(path: Path, n: int, timeout: float = 30.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if path.is_file() and path.read_bytes().count(b"\n") >= n:
            return
        time.sleep(0.05)
    raise TimeoutError(f"{path} never reached {n} rows")


def check_files(day: Path) -> dict[str, bytes]:
    out = {}
    for path in sorted(day.glob("*.jsonl")):
        data = path.read_bytes()
        assert b"\0" not in data, path
        if data:
            assert data.endswith(b"\n"), path
        for line in data.splitlines():
            json.loads(line)
        out[path.name] = data
    return out


def test_kill9_mid_write_then_restart(tmp_path: Path) -> None:
    tape = tmp_path / "tape"
    day = tape / "2026-09-28"
    with ServerThread() as server:
        proc = spawn(server.url, tape, ist(10, 0))
        wait_rows(day / "depth_quotes.jsonl", 400)
        proc.send_signal(signal.SIGKILL)
        assert proc.wait(10) == -signal.SIGKILL
        before = check_files(day)
        assert before["raw_frames.jsonl"].count(b"\n") > 50

        # simulate the worst case a kill (or power cut) can leave: a half-written row + NUL tail
        with open(day / "depth_quotes.jsonl", "ab") as f:
            f.write(b'{"event_type":"DEPTH_QUOTE","payload":{"instr' + b"\0" * 70_000)

        proc = spawn(server.url, tape, ist(10, 0, 30))
        wait_rows(day / "depth_quotes.jsonl", before["depth_quotes.jsonl"].count(b"\n") + 200)
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(20) == 0, proc.stderr.read().decode() if proc.stderr else ""

    after = check_files(day)
    for name, data in before.items():
        assert after[name].startswith(data), f"{name}: rows before the kill changed"
        assert len(after[name]) > len(data) or name in {"ingest_errors.jsonl", "oi_cadence.jsonl"}
    repairs = [json.loads(line) for line in after["ingest_errors.jsonl"].splitlines()]
    repair = [r for r in repairs if r["reason"] == "unterminated tail removed on open"]
    assert len(repair) == 1
    assert repair[0]["nul_bytes"] == 70_000
    assert repair[0]["offset"] == len(before["depth_quotes.jsonl"])
    status = [json.loads(line)["payload"]["status"] for line in after["feed_status.jsonl"].splitlines()]
    assert status[-1] == "DOWN"
    assert status.count("UP") == 2
    assert (day / "coverage_summary.json").is_file()
