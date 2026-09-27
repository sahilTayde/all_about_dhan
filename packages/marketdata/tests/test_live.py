"""V2-12 live market-data service: ticks, closed bars, chain, FEED_STATUS.

Against the in-process fake websocket (fixture frames). No Dhan network.
Tests write only under tmp_path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from dhan_client.config import Credentials, Settings
from dhan_client.errors import CredentialsError
from md_fake_dhan import (
    TEST_CLIENT_ID,
    TEST_TOKEN,
    FakeClock,
    FakeDhanServer,
    full_packet,
    index_packet,
    ist,
    make_universe,
    option_chain,
    option_sid,
    settings_for,
    until,
)

from marketdata import logsafe
from marketdata.__main__ import setup_logging
from marketdata.chain import ChainPoller, snapshot_from_chain
from marketdata.config import RecorderConfig
from marketdata.dhan_ws import LiveMarketData, MemoryPublisher, RedisPublisher, replay_tape
from marketdata.frames import decode_frame_checked
from marketdata.normalize import SecurityMap, tick_from_packet, tick_payload
from marketdata.types import SimClock

NSE_IDX = "NSE_IDX:NIFTY"


def _empty_env() -> dict[str, str]:
    env = {**os.environ, "DHAN_CLIENT_ID": "", "DHAN_ACCESS_TOKEN": ""}
    return env


async def _run_live(
    tmp: Path,
    start: datetime,
    end: datetime,
    *,
    hook: Any = None,
    stale_after_s: float = 5.0,
    chain_fetch: Any = None,
    step: float = 0.1,
) -> tuple[LiveMarketData, FakeDhanServer, MemoryPublisher, list[dict[str, Any]]]:
    statuses: list[dict[str, Any]] = []
    pub = MemoryPublisher()
    async with FakeDhanServer() as server:
        clock = FakeClock(start)
        live = LiveMarketData(
            settings_for(server.url, tmp),
            make_universe(),
            publisher=pub,
            clock=clock,
            config=RecorderConfig(tape_root=tmp / "tape", stale_after_s=stale_after_s),
            on_feed_status=statuses.append,
            chain_fetch=chain_fetch,
        )
        task = asyncio.create_task(live.run())
        clock.done = task.done
        await until(lambda: bool(server.subscribed) or task.done(), timeout=15)
        await until(lambda: clock.sleeping() or task.done(), timeout=15)
        t = start
        while not task.done() and t < end:
            t += timedelta(seconds=step)
            await clock.advance_to(t)
            if hook is not None:
                await hook(t, server, live)
            await until(lambda: live.frames >= server.sent or task.done(), timeout=10)
        if not task.done():
            live.request_stop("test end")
            await clock.advance_to(t + timedelta(seconds=1))
        await asyncio.wait_for(task, timeout=20)
        return live, server, pub, statuses


def test_normalize_fixture_full_and_index() -> None:
    universe = make_universe()
    mapping = SecurityMap(universe.all_instruments())
    idx = mapping.resolve("IDX_I", 13)
    assert idx is not None
    assert idx.instrument_id == NSE_IDX
    packets, errors = decode_frame_checked(index_packet(13, 24512.35))
    assert errors == []
    tick = tick_from_packet(packets[0], idx.instrument_id, "2026-09-28T10:00:10.000+05:30")
    assert tick is not None
    assert tick.ltp == pytest.approx(24512.35)
    assert tick_payload(tick)["exchange_ts"].endswith("+05:30")
    opt = mapping.resolve("NSE_FNO", option_sid(24500, "CE"))
    assert opt is not None
    fulls, ferrs = decode_frame_checked(full_packet(int(opt.security_id), 2, 151.2, 151.1, 151.35))
    assert ferrs == []
    ftick = tick_from_packet(fulls[0], opt.instrument_id, "2026-09-28T10:00:10.000+05:30")
    assert ftick is not None
    assert ftick.ltp == pytest.approx(151.2)


def test_chain_poller_rate_limit_and_snapshot() -> None:
    calls = {"n": 0}

    def fetch(_scrip: int, _seg: str, _expiry: str) -> dict[str, Any]:
        calls["n"] += 1
        return option_chain(24512.35)

    poller = ChainPoller(fetch, interval_s=3.0)
    first = poller.poll(13, "IDX_I", "2026-09-29", "NIFTY", 1_000.0)
    assert first is not None
    assert first["underlying"] == "NIFTY"
    assert first["expiry"] == "2026-09-29"
    assert first["spot"] == pytest.approx(24512.35)
    assert first["strikes"][0]["strike"] == 22000
    assert poller.poll(13, "IDX_I", "2026-09-29", "NIFTY", 1_002.0) is None
    assert poller.poll(13, "IDX_I", "2026-09-29", "NIFTY", 1_003.0) is not None
    assert calls["n"] == 2
    snap = snapshot_from_chain(option_chain(100.0), "NIFTY", "2026-09-29")
    assert snap["spot"] == 100.0


def test_ticks_and_closed_bars_match_fixture(tmp_path: Path) -> None:
    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 10):
            await server.send(index_packet(13, 24500.0))
        elif t == ist(10, 0, 40):
            await server.send(index_packet(13, 24510.0))
        elif t == ist(10, 1, 0):
            await server.send(index_packet(13, 24520.0))

    _live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 1, 2), hook=hook))
    ticks = [p for p in pub.payloads("TICK") if p["instrument_id"] == NSE_IDX]
    assert [(round(p["ltp"], 2) if p["ltp"] is not None else None) for p in ticks] == [24500.0, 24510.0, 24520.0]
    for tick in ticks:
        assert tick["exchange_ts"].endswith("+05:30")
    bars = [p for p in pub.payloads("BAR_CLOSED") if p["instrument_id"] == NSE_IDX and p["tf"] == "1m"]
    assert len(bars) == 1
    bar = bars[0]
    assert bar["start"] == "2026-09-28T10:00:00+05:30"
    assert bar["end"] == "2026-09-28T10:01:00+05:30"
    assert (bar["o"], bar["h"], bar["l"], bar["c"]) == (24500.0, 24510.0, 24500.0, 24510.0)
    env = next(e for e in pub.of("BAR_CLOSED") if e["payload"] is bar)
    assert datetime.fromisoformat(env["available_ts"]) >= datetime.fromisoformat(bar["end"])
    assert datetime.fromisoformat(env["available_ts"]) <= datetime.fromisoformat("2026-09-28T10:01:00.100+05:30")


def test_disconnect_down_up_resubscribe_and_reg02c(tmp_path: Path) -> None:
    """Disconnect -> DOWN then UP with resubscribe. REG-02c: UP is the stop re-check."""

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 5):
            await server.send(index_packet(13, 24512.35))
        if t == ist(10, 0, 20):
            await server.drop_clients()
            await until(lambda: server.connections >= 2 and len(server.subscribed) == 8, timeout=10)

    _live, server, _pub, statuses = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 0, 40), hook=hook))
    seq = [s["status"] for s in statuses if s["status"] in ("UP", "DOWN")]
    assert seq[:3] == ["UP", "DOWN", "UP"]
    assert server.connections >= 2
    assert any(r.get("RequestCode") == 21 and r.get("InstrumentCount") == 8 for _, r in server.requests)
    # REG-02c: reconnect publishes DOWN then UP on on_feed_status (engine stop re-check).
    rechecks = [i for i in range(1, len(seq)) if seq[i - 1] == "DOWN" and seq[i] == "UP"]
    assert rechecks
    ups = [s for s in statuses if s["status"] == "UP"]
    assert len(ups) >= 2
    assert "gap_s" in ups[1]


def test_silence_beyond_stale_after_gives_stale(tmp_path: Path) -> None:
    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 1):
            await server.send(index_packet(13, 24512.35))

    _live, _server, _pub, statuses = asyncio.run(
        _run_live(tmp_path, ist(10, 0), ist(10, 0, 8), hook=hook, stale_after_s=5.0)
    )
    stale = [s for s in statuses if s["status"] == "STALE"]
    assert stale
    assert stale[0]["instrument_id"] == NSE_IDX


def test_refuse_live_data_without_credentials() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "marketdata.dhan_ws", "--mode", "live-data"],
        env=_empty_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "DHAN_CLIENT_ID" in proc.stderr or "DHAN_CLIENT_ID" in proc.stdout

    async def library() -> None:
        async with FakeDhanServer() as server:
            empty = Settings(
                credentials=Credentials(client_id="", access_token=""),
                dry_run=False,
                feed_ws_base=server.url,
            )
            live = LiveMarketData(empty, make_universe(), publisher=MemoryPublisher())
            with pytest.raises(CredentialsError):
                await live.run()
            assert server.attempts == []

    asyncio.run(library())


def test_no_credential_in_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    log_file = tmp_path / "live.log"
    try:
        listener = setup_logging(log_file)
        root.setLevel(logging.DEBUG)
        for name in ("websockets", "websockets.client", "dhan_client", "marketdata"):
            logging.getLogger(name).setLevel(logging.DEBUG)
        root.addHandler(caplog.handler)
        caplog.set_level(logging.DEBUG)

        async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
            if t == ist(10, 0, 3):
                await server.send(index_packet(13, 24512.35))
            if t == ist(10, 0, 5):
                await server.drop_clients()
                await until(lambda: server.connections >= 2, timeout=10)

        _live, server, _pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 0, 12), hook=hook))
    finally:
        listener.stop()
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
        logging.getLogger("websockets").setLevel(logging.WARNING)
    assert server.query[0]["token"] == [TEST_TOKEN]
    captured = "\n".join(r.getMessage() for r in caplog.records)
    texts = [captured, log_file.read_text(encoding="utf-8")]
    for text in texts:
        assert TEST_TOKEN not in text
        assert TEST_CLIENT_ID not in text
    assert logsafe.redact(f"token={TEST_TOKEN}&clientId={TEST_CLIENT_ID}") == "token=REDACTED&clientId=REDACTED"


def test_replay_tape_emits_ticks_and_bars(tmp_path: Path) -> None:
    tape = tmp_path / "ticks.jsonl"
    rows = [
        {
            "instrument_id": NSE_IDX,
            "ltp": ltp,
            "ltq": 1,
            "volume": 1,
            "oi": None,
            "exchange_ts": ts,
        }
        for ltp, ts in (
            (24500.0, "2026-09-28T10:00:10.000+05:30"),
            (24510.0, "2026-09-28T10:00:40.000+05:30"),
            (24520.0, "2026-09-28T10:01:00.000+05:30"),
        )
    ]
    tape.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    pub = MemoryPublisher()
    clock = SimClock(datetime.fromisoformat("2026-09-28T10:00:00+05:30"))
    n = replay_tape(tape, pub, clock=clock)
    assert n >= 3
    assert [p["ltp"] for p in pub.payloads("TICK")] == [24500.0, 24510.0, 24520.0]
    bars = pub.payloads("BAR_CLOSED")
    assert bars
    assert bars[0]["end"] == "2026-09-28T10:01:00+05:30"
    assert datetime.fromisoformat(pub.of("BAR_CLOSED")[0]["available_ts"]) >= datetime.fromisoformat(bars[0]["end"])

    class _Redis:
        def __init__(self) -> None:
            self.added: list[tuple[str, dict[str, str]]] = []

        def xadd(self, stream: str, fields: dict[str, str], **_kw: object) -> None:
            self.added.append((stream, fields))

    fake = _Redis()
    replay_tape(tape, RedisPublisher(fake))
    assert any(stream == "md:ticks" for stream, _ in fake.added)
    assert any(stream == "md:bars:1m" for stream, _ in fake.added)


def test_recorder_help_unchanged() -> None:
    proc = subprocess.run([sys.executable, "-m", "marketdata", "--help"], capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0
    assert "--record-only" in proc.stdout
    assert "--coverage" in proc.stdout
    assert "--mode" not in proc.stdout
    assert "live-data" not in proc.stdout
    live = subprocess.run(
        [sys.executable, "-m", "marketdata.dhan_ws", "--help"], capture_output=True, text=True, timeout=15
    )
    assert live.returncode == 0
    assert "--mode" in live.stdout


def test_chain_emitted_on_live_loop(tmp_path: Path) -> None:
    def fetch(_s: int, _g: str, _e: str) -> dict[str, Any]:
        return option_chain(24512.35)

    _live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 0, 4), chain_fetch=fetch, step=0.5))
    snaps = pub.payloads("CHAIN_SNAPSHOT")
    assert snaps
    assert snaps[0]["underlying"] == "NIFTY"
    assert snaps[0]["strikes"]
