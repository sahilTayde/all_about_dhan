"""V2-12 live market-data service: ticks, closed bars, chain, FEED_STATUS.

Against the in-process fake websocket (fixture frames). No Dhan network.
Tests write only under tmp_path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import struct
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
    dhan_ltt,
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
from marketdata.dhan_ws import MEMORY_PUBLISHER_MAXLEN, LiveMarketData, MemoryPublisher, RedisPublisher, replay_tape
from marketdata.frames import decode_frame_checked
from marketdata.lookahead import lookahead_failures
from marketdata.normalize import SecurityMap, resolve_exchange_ts, stamp_exchange_ts, tick_from_packet, tick_payload
from marketdata.types import BarClosed, SimClock

NSE_IDX = "NSE_IDX:NIFTY"
FUT = "NSE_FNO:NIFTY:2026-09-29"
NSE_FNO_SEG = 2
FUT_SID = 35000


def _full(t: datetime, ltp: float, *, ltt: datetime | None = None, ltt_epoch: int | None = None) -> bytes:
    epoch = dhan_ltt(ltt if ltt is not None else t) if ltt_epoch is None else ltt_epoch
    return full_packet(FUT_SID, NSE_FNO_SEG, ltp, ltp - 0.05, ltp + 0.05, ltt_epoch=epoch)


def _index_on_fut(ltp: float) -> bytes:
    """INDEX response on the future: LTP only, no ``last_trade_time_epoch``."""
    payload = struct.pack("<fI", ltp, 0)
    return struct.pack("<BHBI", 1, 8 + len(payload), NSE_FNO_SEG, FUT_SID) + payload


def _closed_emissions(pub: MemoryPublisher) -> list[tuple[BarClosed, datetime]]:
    """(BarClosed, emission time) for lookahead_failures."""
    out: list[tuple[BarClosed, datetime]] = []
    for env in pub.of("BAR_CLOSED"):
        payload = env["payload"]
        bar = BarClosed(
            instrument_id=payload["instrument_id"],
            tf=payload["tf"],
            start=payload["start"],
            end=payload["end"],
            o=payload["o"],
            h=payload["h"],
            l=payload["l"],
            c=payload["c"],
            v=payload["v"],
            n_ticks=payload["n_ticks"],
            gap=payload.get("gap", False),
            late_ticks=payload.get("late_ticks", 0),
            available_ts=env["available_ts"],
        )
        out.append((bar, datetime.fromisoformat(env["timestamp"])))
    return out


def _empty_env() -> dict[str, str]:
    env = {**os.environ, "DHAN_CLIENT_ID": "", "DHAN_ACCESS_TOKEN": ""}
    return env


async def _run_live(
    tmp: Path,
    start: datetime,
    end: datetime,
    *,
    hook: Any = None,
    stale_after_s: float = 3600.0,
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
            await server.send(_full(t, 24500.0))
        elif t == ist(10, 0, 40):
            await server.send(_full(t, 24510.0))
        elif t == ist(10, 1, 0):
            await server.send(_full(t, 24520.0))

    _live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 1, 2), hook=hook))
    ticks = [p for p in pub.payloads("TICK") if p["instrument_id"] == FUT]
    assert [(round(p["ltp"], 2) if p["ltp"] is not None else None) for p in ticks] == [24500.0, 24510.0, 24520.0]
    for tick in ticks:
        assert tick["exchange_ts"].endswith("+05:30")
        assert tick["ts_source"] == "ltt"
    bars = [p for p in pub.payloads("BAR_CLOSED") if p["instrument_id"] == FUT and p["tf"] == "1m"]
    assert len(bars) == 1
    bar = bars[0]
    assert bar["start"] == "2026-09-28T10:00:00+05:30"
    assert bar["end"] == "2026-09-28T10:01:00+05:30"
    assert (bar["o"], bar["h"], bar["l"], bar["c"]) == (24500.0, 24510.0, 24500.0, 24510.0)
    assert bar["feed_quality"] == "OK"
    env = next(e for e in pub.of("BAR_CLOSED") if e["payload"] is bar)
    assert datetime.fromisoformat(env["available_ts"]) >= datetime.fromisoformat(bar["end"])
    assert datetime.fromisoformat(env["available_ts"]) <= datetime.fromisoformat("2026-09-28T10:01:00.100+05:30")
    assert lookahead_failures(_closed_emissions(pub)) == []


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
    assert any(r.get("RequestCode") == 21 and r.get("InstrumentCount") == 7 for _, r in server.requests)
    assert any(r.get("RequestCode") == 15 and r.get("InstrumentCount") == 1 for _, r in server.requests)
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
    assert lookahead_failures(_closed_emissions(pub)) == []

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


def test_stamp_exchange_ts_uses_packet_ltt() -> None:
    recv = ist(10, 1, 5)
    fields = {"last_trade_time_epoch": dhan_ltt(ist(10, 0, 45))}
    stamped = stamp_exchange_ts(fields, recv)
    assert stamped.startswith("2026-09-28T10:00:45")
    assert stamped.endswith("+05:30")
    assert resolve_exchange_ts(fields, recv)[1] == "ltt"
    assert stamp_exchange_ts({}, recv).startswith("2026-09-28T10:01:05")
    assert resolve_exchange_ts({}, recv) == (stamp_exchange_ts({}, recv), "recv")
    assert resolve_exchange_ts({"last_trade_time_epoch": 0}, recv)[1] == "recv"
    assert resolve_exchange_ts({"last_trade_time_epoch": None}, recv)[1] == "recv"


def test_delayed_previous_minute_packet_is_late_not_in_ohlc(tmp_path: Path) -> None:
    """Delayed LTT from the previous minute after the next minute's first tick is dropped."""

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 1, 0):
            await server.send(full_packet(FUT_SID, NSE_FNO_SEG, 100.0, 99.95, 100.05, ltt_epoch=dhan_ltt(t)))
        elif t == ist(10, 1, 5):
            late_ltt = dhan_ltt(ist(10, 0, 45))
            await server.send(full_packet(FUT_SID, NSE_FNO_SEG, 999.0, 998.0, 999.1, ltt_epoch=late_ltt))
        elif t == ist(10, 2, 0):
            await server.send(full_packet(FUT_SID, NSE_FNO_SEG, 101.0, 100.95, 101.05, ltt_epoch=dhan_ltt(t)))

    live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0, 50), ist(10, 2, 2), hook=hook))
    bars = [p for p in pub.payloads("BAR_CLOSED") if p["instrument_id"] == FUT]
    assert bars
    bar = next(p for p in bars if p["start"].startswith("2026-09-28T10:01:00"))
    assert (bar["o"], bar["h"], bar["l"], bar["c"]) == (100.0, 100.0, 100.0, 100.0)
    assert 999.0 not in (bar["o"], bar["h"], bar["l"], bar["c"])
    assert bar["late_ticks"] == 1
    assert live.bars.late_tick_count == 1
    assert lookahead_failures(_closed_emissions(pub)) == []


def test_published_bars_pass_lookahead_on_replay(tmp_path: Path) -> None:
    tape = tmp_path / "ticks.jsonl"
    rows = [
        {"instrument_id": NSE_IDX, "ltp": 24500.0, "ltq": 1, "volume": 1, "oi": None, "exchange_ts": ts}
        for ts in (
            "2026-09-28T10:00:10.000+05:30",
            "2026-09-28T10:00:40.000+05:30",
            "2026-09-28T10:01:00.000+05:30",
            "2026-09-28T10:01:30.000+05:30",
            "2026-09-28T10:02:00.000+05:30",
        )
    ]
    tape.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    pub = MemoryPublisher()
    replay_tape(tape, pub, clock=SimClock(datetime.fromisoformat("2026-09-28T10:00:00+05:30")))
    assert pub.payloads("BAR_CLOSED")
    assert lookahead_failures(_closed_emissions(pub)) == []


def test_reg02c_one_up_per_down_up_no_heartbeat_dup(tmp_path: Path) -> None:
    """REG-02c: on_feed_status UP once per reconnect; heartbeats do not duplicate UP."""

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 2):
            await server.send(index_packet(13, 24512.35))
        if t == ist(10, 0, 25):
            await server.drop_clients()
            await until(lambda: server.connections >= 2 and len(server.subscribed) == 8, timeout=10)

    _live, server, _pub, statuses = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 0, 45), hook=hook))
    seq = [s["status"] for s in statuses if s["status"] in ("UP", "DOWN")]
    assert seq == ["UP", "DOWN", "UP", "DOWN"]
    assert seq.count("UP") == 2
    assert not any(a == b == "UP" for a, b in zip(seq, seq[1:], strict=False))
    assert server.connections >= 2


def test_live_data_never_constructs_or_calls_order_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end fake WS: service publishes bars and never constructs ExecutionClient.

    Importing the execution module is allowed. Constructing it or calling place_order is not.
    ``DhanClient`` has no order-placing methods; ``ExecutionClient.place_order`` is the mutator.
    """
    import inspect

    from marketdata import chain, dhan_ws, normalize

    for mod in (dhan_ws, chain, normalize):
        src = inspect.getsource(mod)
        assert "ExecutionClient" not in src
        assert "place_order" not in src
        assert "DhanClient" not in src

    tripped: list[str] = []

    def boom_init(_self: object, *_a: object, **_k: object) -> None:
        tripped.append("ExecutionClient.__init__")
        raise RuntimeError("ExecutionClient must not be constructed on the live-data path")

    def boom_place(_self: object, *_a: object, **_k: object) -> None:
        tripped.append("ExecutionClient.place_order")
        raise RuntimeError("place_order must not be called on the live-data path")

    import dhan_client.client as client_mod
    import dhan_client.execution as execution

    monkeypatch.setattr(execution.ExecutionClient, "__init__", boom_init)
    monkeypatch.setattr(execution.ExecutionClient, "place_order", boom_place)
    assert not hasattr(client_mod.DhanClient, "place_order")

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 10):
            await server.send(_full(t, 24500.0))
        elif t == ist(10, 0, 40):
            await server.send(_full(t, 24510.0))
        elif t == ist(10, 1, 0):
            await server.send(_full(t, 24520.0))

    _live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0), ist(10, 1, 2), hook=hook))
    bars = [p for p in pub.payloads("BAR_CLOSED") if p["instrument_id"] == FUT]
    assert bars
    assert (bars[0]["o"], bars[0]["c"]) == (24500.0, 24510.0)
    assert tripped == []


def test_zero_and_missing_ltt_do_not_change_open_bar_ohlc(tmp_path: Path) -> None:
    """Zero LTT and missing LTT stay off the open bar; unstamped_ticks increments."""

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 1, 0):
            await server.send(_full(t, 100.0))
        elif t == ist(10, 1, 5):
            await server.send(_full(t, 999.0, ltt_epoch=0))
            await server.send(_index_on_fut(888.0))
        elif t == ist(10, 2, 0):
            await server.send(_full(t, 101.0))

    live, _server, pub, _st = asyncio.run(_run_live(tmp_path, ist(10, 0, 50), ist(10, 2, 2), hook=hook))
    ticks = [p for p in pub.payloads("TICK") if p["instrument_id"] == FUT]
    sources = [p["ts_source"] for p in ticks]
    assert "recv" in sources
    assert sources.count("recv") == 2
    bars = [p for p in pub.payloads("BAR_CLOSED") if p["instrument_id"] == FUT]
    bar = next(p for p in bars if p["start"].startswith("2026-09-28T10:01:00"))
    assert (bar["o"], bar["h"], bar["l"], bar["c"]) == (100.0, 100.0, 100.0, 100.0)
    assert 999.0 not in (bar["o"], bar["h"], bar["l"], bar["c"])
    assert 888.0 not in (bar["o"], bar["h"], bar["l"], bar["c"])
    assert bar["unstamped_ticks"] == 2
    assert live.unstamped_tick_count == 2
    assert lookahead_failures(_closed_emissions(pub)) == []


def test_stale_then_down_gap_publishes_no_clean_bar(tmp_path: Path) -> None:
    """UP → STALE → DOWN → UP: no clean BAR_CLOSED for the gap interval."""

    async def hook(t: datetime, server: FakeDhanServer, _live: LiveMarketData) -> None:
        if t == ist(10, 0, 1):
            await server.send(_full(t, 100.0))
        if t == ist(10, 0, 12):
            await server.drop_clients()
            await until(lambda: server.connections >= 2 and len(server.subscribed) == 8, timeout=10)
        if t >= ist(10, 0, 20) and t.microsecond == 0 and t.second % 2 == 0:
            await server.send(index_packet(13, 24512.35))
        if t == ist(10, 1, 0):
            await server.send(_full(t, 101.0))
        if t == ist(10, 2, 0):
            await server.send(_full(t, 102.0))

    live, _server, pub, statuses = asyncio.run(
        _run_live(tmp_path, ist(10, 0), ist(10, 2, 2), hook=hook, stale_after_s=5.0)
    )
    seq = [s["status"] for s in statuses]
    assert "UP" in seq
    assert "STALE" in seq
    assert "DOWN" in seq
    gap = [p for p in pub.payloads("BAR_CLOSED") if p["start"].startswith("2026-09-28T10:00:00")]
    assert gap == []
    later = [p for p in pub.payloads("BAR_CLOSED") if p["start"].startswith("2026-09-28T10:01:00")]
    assert later
    assert later[0]["feed_quality"] == "OK"
    assert (later[0]["o"], later[0]["c"]) == (101.0, 101.0)
    assert live.suppressed_bars >= 1
    assert lookahead_failures(_closed_emissions(pub)) == []


def test_memory_publisher_caps_after_50k_envelopes() -> None:
    pub = MemoryPublisher()
    assert pub.maxlen == MEMORY_PUBLISHER_MAXLEN
    for i in range(50_000):
        pub.publish({"event_type": "TICK", "n": i, "stream": "md:ticks"})
    assert len(pub.events) == MEMORY_PUBLISHER_MAXLEN
    assert pub.events[0]["n"] == 50_000 - MEMORY_PUBLISHER_MAXLEN
    assert pub.events[-1]["n"] == 49_999


def test_dhan_ws_import_leaves_normal_dhan_client_imports_working() -> None:
    """After marketdata.dhan_ws, the real package still exports DhanClient / execution."""
    import importlib

    importlib.import_module("marketdata.dhan_ws")
    import dhan_client.execution
    from dhan_client import DhanClient

    assert DhanClient is not None
    assert dhan_client.execution.ExecutionClient is not None
    assert hasattr(dhan_client.execution.ExecutionClient, "place_order")
