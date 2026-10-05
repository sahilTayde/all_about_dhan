"""Recorder behaviour beyond the spec list: schemas, session window, reconnect, startup failures."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from dhan_client.errors import DhanApiError
from md_fake_dhan import (
    FakeDhanServer,
    Market,
    OffsetClock,
    StubSource,
    disconnect_packet,
    full_packet,
    ist,
    make_universe,
    option_sid,
    read_rows,
    run_session,
    schema_errors,
    settings_for,
    until,
)

from marketdata import __main__ as cli
from marketdata.clock import session_day
from marketdata.config import RecorderConfig
from marketdata.instruments import DEFAULT_RECORDER_UNDERLYINGS, StartupError
from marketdata.recorder import MarketDataRecorder


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_every_row_validates_against_schema_with_format_checker(tmp_path: Path) -> None:
    ce = option_sid(24500, "CE")

    def trend(t: datetime) -> float:
        return 24512.35 + 0.5 * max((t - ist(10, 0)).total_seconds(), 0.0) + 3 * math.sin(t.timestamp())

    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 1):
            await server.send(b"\x01\x02")
            await server.send(full_packet(ce, 2, float("nan"), 80.0, 80.1))

    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 6),
            spot=trend,
            source=StubSource(),
            hook=hook,
            step=0.1,
            market_kw={"silent": {ce: [(ist(10, 2), ist(10, 2, 30))]}},
        )
    )
    counts, errors = schema_errors(s.day_dir)
    assert errors == []
    assert counts["depth_quotes"] > 2000
    assert counts["quote_snapshots"] > 400
    assert counts["oi_cadence"] > 20
    assert {r["payload"]["rule"] for r in s.rows("quote_snapshots")} == {"ATM", "ITM100", "ITM200"}
    assert all(r["payload"]["instrument_id"].count(":") == 4 for r in s.rows("quote_snapshots"))
    ids = {r["payload"]["instrument_id"] for r in s.rows("depth_quotes")}
    assert {"NSE_IDX:NIFTY", "NSE_FNO:NIFTY:2026-09-29"} <= ids


def test_clean_stop_at_1530_ist(tmp_path: Path) -> None:
    s = asyncio.run(run_session(tmp_path, ist(15, 29, 50), ist(15, 45), source=StubSource()))
    assert s.exit_code == 0
    assert s.recorder.stop_reason == "market close 15:30 IST"
    last = max(ts(r["timestamp"]) for r in s.rows("depth_quotes"))
    assert ist(15, 29, 59) <= last < ist(15, 30)
    assert all(ts(r["timestamp"]) <= ist(15, 30) for r in s.rows("feed_status"))
    summary = json.loads((s.day_dir / "coverage_summary.json").read_text())
    assert summary["day"] == "2026-09-28"
    assert len(summary["instruments"]) == 8


def test_started_before_open_waits_and_connects_at_0913(tmp_path: Path) -> None:
    seen: dict[str, int] = {}

    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(9, 12, 59):
            await asyncio.sleep(0.2)
            seen["09:12:59"] = server.connections
        if t == ist(9, 13, 2):
            await until(lambda: bool(server.subscribed), timeout=10)
            seen["09:13:02"] = server.connections

    s = asyncio.run(
        run_session(tmp_path, ist(8, 5), ist(9, 16), source=StubSource(), hook=hook, step=1.0, wait_connect=False)
    )
    assert seen == {"09:12:59": 0, "09:13:02": 1}
    first = min(ts(r["ts"]) for r in s.rows("subscriptions"))
    assert ist(9, 13) <= first < ist(9, 13, 1)
    assert s.recorder.stop_reason == "test end"
    assert any(ts(r["timestamp"]) > ist(9, 15, 30) for r in s.rows("depth_quotes"))


def test_session_day() -> None:
    assert session_day(ist(6, 0)) == ist(0, 0).date()  # Monday morning: today
    assert session_day(ist(15, 29, 59)).isoformat() == "2026-09-28"
    assert session_day(ist(15, 30)).isoformat() == "2026-09-29"  # after the close: next day
    saturday = ist(10, 0, day=ist(0, 0).date() - timedelta(days=2))
    assert session_day(saturday).isoformat() == "2026-09-28"
    sunday_night_us = datetime.fromisoformat("2026-09-27T21:00:00-05:00")
    assert session_day(sunday_night_us).isoformat() == "2026-09-28"


def test_reconnects_after_drop_and_resubscribes(tmp_path: Path) -> None:
    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 0, 20):
            await server.drop_clients()
            await until(lambda: server.connections >= 2 and len(server.subscribed) == 8, timeout=10)

    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 0, 40), source=StubSource(), hook=hook))
    assert s.recorder.collector is not None
    assert s.recorder.collector.connect_count == 2
    statuses = [r["payload"]["status"] for r in s.rows("feed_status")]
    assert statuses[:3] == ["UP", "DOWN", "UP"]
    second = [r for _, r in s.server.requests if r.get("RequestCode") == 21][-1]
    assert second["InstrumentCount"] == 7  # future + 6 options; index is ticker (15)
    assert any(
        r.get("RequestCode") == 15 and 13 in {int(i["SecurityId"]) for i in r["InstrumentList"]}
        for _, r in s.server.requests
    )
    after = {
        r["payload"]["instrument_id"]
        for r in s.rows("depth_quotes")
        if ts(r["payload"]["exchange_ts"]) > ist(10, 0, 25)
    }
    assert len(after) == 8


def test_reconnect_uses_backoff(tmp_path: Path) -> None:
    async def scenario() -> list[float]:
        async with FakeDhanServer() as server:
            server.reject_status, server.reject_count = 503, 2
            rec = MarketDataRecorder(
                RecorderConfig(tape_root=tmp_path / "tape"),
                settings_for(server.url, tmp_path),
                universe=make_universe(),
                clock=OffsetClock(ist(10, 0)),
            )
            task = asyncio.create_task(rec.run())
            await until(lambda: bool(server.subscribed), timeout=15)
            rec.request_stop("test end")
            assert await asyncio.wait_for(task, 10) == 0
            return server.attempts

    attempts = asyncio.run(scenario())
    assert len(attempts) == 3
    assert 0.9 <= attempts[1] - attempts[0] < 1.8
    assert 1.9 <= attempts[2] - attempts[1] < 3.0


def test_websocket_auth_rejection_stops_with_exit_2(tmp_path: Path) -> None:
    async def scenario() -> tuple[int, MarketDataRecorder]:
        async with FakeDhanServer() as server:
            server.reject_status = 401
            rec = MarketDataRecorder(
                RecorderConfig(tape_root=tmp_path / "tape", max_auth_failures=2),
                settings_for(server.url, tmp_path),
                universe=make_universe(),
                clock=OffsetClock(ist(10, 0)),
            )
            return await asyncio.wait_for(rec.run(), 20), rec

    code, rec = asyncio.run(scenario())
    assert code == 2
    assert rec.stop_reason is not None
    assert "HTTP 401" in rec.stop_reason
    rows = read_rows(tmp_path / "tape" / "2026-09-28" / "feed_status.jsonl")
    assert "AUTH_FAILED" in [r["payload"]["status"] for r in rows]


def test_disconnect_code_for_bad_token_stops_with_exit_2(tmp_path: Path) -> None:
    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 0, 5):
            await server.send(disconnect_packet(808))

    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 1), source=StubSource(), hook=hook))
    assert s.exit_code == 2
    assert s.recorder.stop_reason is not None
    assert "code 808" in s.recorder.stop_reason
    assert "DISCONNECT" in [r["payload"]["status"] for r in s.rows("feed_status")]


def _network_down() -> list[Exception]:
    return [DhanApiError("network error on public GET") for _ in range(100)]


def test_startup_retries_then_uses_cached_instruments(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    first = asyncio.run(
        run_session(tmp_path / "a", ist(9, 30), ist(9, 30, 5), source=StubSource(), config_kw={"cache_dir": cache})
    )
    assert first.exit_code == 0
    assert (cache / "universe_NIFTY_2026-09-28.json").is_file()

    source = StubSource(fail={"scrip_master_csv": _network_down()})
    s = asyncio.run(
        run_session(
            tmp_path / "b",
            ist(9, 19),
            ist(9, 30),
            source=source,
            config_kw={"cache_dir": cache, "startup_attempts": 1},
            wait_connect=False,
            step=1.0,
        )
    )
    # retried every 30 s until max(09:20, start + 2 min) = 09:21, then fell back to the cache
    assert 4 <= source.calls.count("scrip_master_csv") <= 6
    assert s.exit_code == 0
    assert len(s.rows("depth_quotes")) > 0


def test_startup_without_cache_fails_loudly(tmp_path: Path) -> None:
    source = StubSource(fail={"scrip_master_csv": _network_down()})
    with pytest.raises(StartupError, match="could not reach Dhan for the scrip master CSV"):
        asyncio.run(
            run_session(
                tmp_path,
                ist(9, 19),
                ist(9, 30),
                source=source,
                config_kw={"startup_attempts": 1},
                wait_connect=False,
                step=1.0,
            )
        )


def test_bad_credentials_at_startup_fail_immediately(tmp_path: Path) -> None:
    source = StubSource(fail={"expiry_list": [DhanApiError("Invalid token", status_code=401, error_code="DH-901")]})
    with pytest.raises(StartupError, match="DHAN_ACCESS_TOKEN") as info:
        asyncio.run(run_session(tmp_path, ist(9, 0), ist(9, 30), source=source, wait_connect=False))
    assert not info.value.retryable
    assert source.calls.count("expiry_list") == 1


def test_cli_default_and_repeatable_underlyings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_record(underlyings: tuple[str, ...], root: Path, tape_root: Path, day: object) -> int:
        seen["underlyings"] = underlyings
        seen["tape_root"] = tape_root
        return 0

    monkeypatch.setattr(cli, "_record", fake_record)
    monkeypatch.setattr(cli, "setup_logging", lambda _p: type("L", (), {"stop": lambda self: None})())
    assert cli.main(["--record-only", "--tape-root", str(tmp_path / "tape")]) == 0
    assert seen["underlyings"] == DEFAULT_RECORDER_UNDERLYINGS == ("NIFTY", "SENSEX")
    assert cli.main(["--record-only", "--underlying", "NIFTY", "--tape-root", str(tmp_path / "tape")]) == 0
    assert seen["underlyings"] == ("NIFTY",)
    assert cli.main(["--record-only", "--underlying", "NIFTY,SENSEX", "--tape-root", str(tmp_path / "tape")]) == 0
    assert seen["underlyings"] == ("NIFTY", "SENSEX")
    assert (
        cli.main(
            [
                "--record-only",
                "--underlying",
                "NIFTY",
                "--underlying",
                "SENSEX",
                "--tape-root",
                str(tmp_path / "tape"),
            ]
        )
        == 0
    )
    assert seen["underlyings"] == ("NIFTY", "SENSEX")


def test_recorder_subscribes_nifty_and_sensex_weekly_wings(tmp_path: Path) -> None:
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 8),
            source=StubSource(),
            config_kw={"underlyings": ("NIFTY", "SENSEX")},
        )
    )
    assert s.exit_code == 0
    rows = [r for r in s.rows("subscriptions") if r["action"] == "subscribe"]
    ids = {r["instrument_id"] for r in rows}
    assert "NSE_IDX:NIFTY" in ids
    assert "NSE_FNO:NIFTY:2026-09-29" in ids
    assert "BSE_IDX:SENSEX" in ids
    assert any(i.startswith("BSE_FNO:SENSEX:") and i.count(":") == 2 for i in ids)
    nifty_opts = {i for i in ids if i.startswith("NSE_FNO:NIFTY:") and i.count(":") == 4}
    sensex_opts = {i for i in ids if i.startswith("BSE_FNO:SENSEX:") and i.count(":") == 4}
    assert len(nifty_opts) == 6
    assert len(sensex_opts) == 6
    assert any(i.endswith(":CE") for i in nifty_opts) and any(i.endswith(":PE") for i in nifty_opts)
    assert any(i.endswith(":CE") for i in sensex_opts) and any(i.endswith(":PE") for i in sensex_opts)
    assert all(i.startswith("BSE_FNO:SENSEX:2026-10-01:") for i in sensex_opts)
    assert len(ids) <= 20
    segs = {r["exchange_segment"] for r in rows}
    assert {"IDX_I", "NSE_FNO", "BSE_FNO"} <= segs


def test_cli_exit_code_2_on_startup_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import logging

    settings = settings_for("ws://127.0.0.1:9", tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda **_kw: settings)
    stub = StubSource(fail={"option_chain": [DhanApiError("bad", status_code=400, error_code="DH-905")]})
    stub.close = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setattr(cli, "DhanInstrumentSource", lambda *_a, **_kw: stub)
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        assert cli.main(["--record-only", "--tape-root", str(tmp_path / "tape")]) == 2
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
    logs = "".join(p.read_text() for p in (tmp_path / "tape").rglob("recorder.log"))
    assert "startup failed: Dhan returned an error for the option chain" in logs
    assert "Traceback" not in logs


def test_real_time_run_keeps_recording(tmp_path: Path) -> None:
    """Real clock speed: after 4 s the recorder is still running and rows are on disk."""

    async def scenario() -> tuple[int, int, bool]:
        async with FakeDhanServer() as server:
            universe = make_universe()
            clock = OffsetClock(ist(10, 0))
            rec = MarketDataRecorder(
                RecorderConfig(tape_root=tmp_path / "tape"),
                settings_for(server.url, tmp_path),
                universe=universe,
                clock=clock,
            )
            task = asyncio.create_task(rec.run())
            market = Market(universe, lambda t: 24512.35 + math.sin(t.timestamp()), default_hz=4.0)
            loop = asyncio.get_running_loop()
            end = loop.time() + 4.0
            while loop.time() < end:
                for frame in market.frames(clock.now(), server.subscribed):
                    await server.send(frame)
                await asyncio.sleep(0.05)
            alive = not task.done()
            on_disk = len(read_rows(tmp_path / "tape" / "2026-09-28" / "depth_quotes.jsonl"))
            rec.request_stop("test end")
            return await asyncio.wait_for(task, 10), on_disk, alive

    code, on_disk, alive = asyncio.run(scenario())
    assert alive
    assert on_disk >= 8 * 2
    assert code == 0


def test_stop_during_startup_retry_returns_promptly(tmp_path: Path) -> None:
    import time

    async def scenario() -> tuple[int, float]:
        source = StubSource(fail={"scrip_master_csv": _network_down()})
        rec = MarketDataRecorder(
            RecorderConfig(tape_root=tmp_path / "tape"),
            settings_for("ws://127.0.0.1:9", tmp_path),
            source=source,
            clock=OffsetClock(ist(8, 0)),
        )
        task = asyncio.create_task(rec.run())
        await asyncio.sleep(0.5)  # inside the 2 s / 4 s retry sleeps
        t0 = time.monotonic()
        rec.request_stop("signal SIGTERM")
        code = await asyncio.wait_for(task, 5)
        return code, time.monotonic() - t0

    code, took = asyncio.run(scenario())
    assert code == 0
    assert took < 1.0


def test_run_reraises_when_the_feed_task_dies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from dhan_client.feed import MarketFeedCollector

    async def boom(_self: MarketFeedCollector, *_a: object, **_kw: object) -> None:
        raise RuntimeError("feed exploded")

    monkeypatch.setattr(MarketFeedCollector, "run", boom)
    with pytest.raises(RuntimeError, match="feed exploded"):
        asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 1), source=StubSource(), wait_connect=False))
    assert (tmp_path / "tape" / "2026-09-28" / "coverage_summary.json").is_file()  # writers still closed


def test_run_reraises_when_the_clock_task_dies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    real_tick = MarketDataRecorder._tick

    async def tick(self: MarketDataRecorder, *args: Any) -> None:
        calls["n"] += 1
        if calls["n"] == 20:
            raise AttributeError("'DepthTracker' object has no attribute '_last_emit'")
        await real_tick(self, *args)

    monkeypatch.setattr(MarketDataRecorder, "_tick", tick)
    with pytest.raises(AttributeError, match="_last_emit"):
        asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 1), source=StubSource()))


def test_a_failing_packet_handler_is_contained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = MarketDataRecorder._on_packet
    seen = {"n": 0}

    async def flaky(self: MarketDataRecorder, packet: Any, now: datetime) -> None:
        seen["n"] += 1
        if seen["n"] % 10 == 0:
            raise KeyError("boom")
        await real(self, packet, now)

    monkeypatch.setattr(MarketDataRecorder, "_on_packet", flaky)
    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 0, 30), source=StubSource()))
    assert s.exit_code == 0
    assert s.recorder.collector is not None
    assert s.recorder.collector.connect_count == 1  # no reconnect storm
    errors = [e for e in s.rows("ingest_errors") if e["reason"].startswith("packet handling failed: KeyError")]
    assert len(errors) == seen["n"] // 10
    assert len(s.rows("depth_quotes")) > 200
