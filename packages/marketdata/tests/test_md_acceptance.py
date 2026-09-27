"""V2-D2 spec acceptance tests (docs/architecture/V2_BUILD_PLAN.md, V2-D2 "Acceptance").

Every test runs the real ``MarketDataRecorder`` -> real ``MarketFeedCollector._run_socket`` ->
V2-D1 decoder -> tape writers against an in-process websocket server on 127.0.0.1 emitting
binary FULL/INDEX/OI packets, with a fake clock. No shim anywhere in the pipeline.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import math
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from dhan_client.config import Credentials, Settings
from dhan_client.errors import CredentialsError
from dhan_client.feed import MarketFeedCollector
from md_fake_dhan import (
    TEST_CLIENT_ID,
    TEST_TOKEN,
    FakeDhanServer,
    Session,
    StubSource,
    full_packet,
    ist,
    make_universe,
    oi_packet,
    option_sid,
    run_session,
    until,
)

from marketdata import logsafe
from marketdata.__main__ import setup_logging
from marketdata.config import RecorderConfig
from marketdata.oi_cadence import OiCadenceTracker
from marketdata.recorder import MarketDataRecorder

NSE_FNO = 2


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def by_instrument(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[row["payload"]["instrument_id"]].append(row)
    return out


def wobble(t: datetime) -> float:
    return 24512.35 + 4.0 * math.sin(t.timestamp() / 7.0)


MIXED_RATES = {
    35000: 5.0,  # future
    option_sid(24500, "CE"): 4.0,
    option_sid(24500, "PE"): 0.5,
    option_sid(24400, "CE"): 0.2,
    option_sid(24600, "PE"): 0.1,
}


@pytest.fixture(scope="module")
def mixed_session(tmp_path_factory: pytest.TempPathFactory) -> Session:
    tmp = tmp_path_factory.mktemp("mixed")
    return asyncio.run(
        run_session(
            tmp,
            ist(10, 0),
            ist(10, 3),
            spot=wobble,
            source=StubSource(),
            market_kw={"default_hz": 1.0, "rates": MIXED_RATES},
        )
    )


def test_acceptance_1_depth_row_per_instrument_at_least_once_per_second(mixed_session: Session) -> None:
    rows = by_instrument(mixed_session.rows("depth_quotes"))
    subscribed = {r["instrument_id"] for r in mixed_session.rows("subscriptions") if r["action"] == "subscribe"}
    assert len(subscribed) == 8
    assert set(rows) == subscribed
    for iid, items in rows.items():
        times = [ts(r["timestamp"]) for r in items]
        gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:], strict=False)]
        assert max(gaps) <= 1.0, (iid, max(gaps))
        seconds = {int(t.timestamp()) for t in times}
        first, last = int(times[0].timestamp()) + 1, int(ist(10, 3).timestamp())
        assert set(range(first, last)) <= seconds, iid
        fresh = [ts(r["timestamp"]) for r in items if not r["payload"]["repeat"]]
        assert all((b - a).total_seconds() >= 0.25 for a, b in zip(fresh, fresh[1:], strict=False)), iid
    # the 0.1 Hz instrument is carried by heartbeats that keep the old data time
    slow = rows["NSE_FNO:NIFTY:2026-09-29:24600:PE"]
    repeats = [r for r in slow if r["payload"]["repeat"]]
    assert len(repeats) > 100
    assert all(ts(r["payload"]["exchange_ts"]) < ts(r["timestamp"]) for r in repeats)


def test_acceptance_2_quote_snapshot_every_5s_within_half_a_second(mixed_session: Session) -> None:
    rows = by_instrument(mixed_session.rows("quote_snapshots"))
    assert set(rows) == {
        "NSE_FNO:NIFTY:2026-09-29:24500:CE",
        "NSE_FNO:NIFTY:2026-09-29:24400:CE",
        "NSE_FNO:NIFTY:2026-09-29:24300:CE",
        "NSE_FNO:NIFTY:2026-09-29:24500:PE",
        "NSE_FNO:NIFTY:2026-09-29:24600:PE",
        "NSE_FNO:NIFTY:2026-09-29:24700:PE",
    }
    for iid, items in rows.items():
        times = [ts(r["timestamp"]) for r in items]
        assert len(times) == 36, iid
        for a, b in zip(times, times[1:], strict=False):
            assert 4.5 <= (b - a).total_seconds() <= 5.5
        for t in times:
            off = t.timestamp() % 5
            assert min(off, 5 - off) <= 0.5
        p = items[-1]["payload"]
        assert p["bid"] is not None
        assert p["ask"] is not None
        assert p["ltt"] is not None
        assert p["depth_age_ms"] is not None


def test_acceptance_3_recentring_subscribes_new_strikes_and_keeps_old_for_10_minutes(tmp_path: Path) -> None:
    def trend(t: datetime) -> float:
        # 24512 -> 24812 between 10:00 and 10:05, then flat
        return 24512.35 + min(max((t - ist(10, 0)).total_seconds(), 0.0), 300.0)

    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 17), spot=trend, source=StubSource(), step=0.1))
    universe = make_universe()
    subs = s.rows("subscriptions")
    assert s.server.connections == 1, "re-centring must not need a reconnect"
    recentres = [r for r in subs if r["reason"] == "recentre"]
    atms = sorted({r["atm"] for r in recentres})
    assert atms[0] == 24550
    assert atms[-1] == 24800
    assert set(range(24550, 24801, 50)) <= set(atms)

    # the strike set follows ATM: final current set is ATM 24800 / CE ITM below / PE ITM above
    strikes = s.recorder.strikes
    assert strikes is not None
    final = set(strikes.current)
    assert final == {
        f"NSE_FNO:NIFTY:2026-09-29:{k}:{side}"
        for k, side in [(24800, "CE"), (24700, "CE"), (24600, "CE"), (24800, "PE"), (24900, "PE"), (25000, "PE")]
    }
    # dynamic subscribe on the open socket, and depth rows for the new strikes
    sent = set(s.server.sids(21))
    assert {option_sid(24800, "CE"), option_sid(25000, "PE")} <= sent
    depth = by_instrument(s.rows("depth_quotes"))
    assert "NSE_FNO:NIFTY:2026-09-29:24800:CE" in depth

    # left-the-set time per instrument, replayed from the logged ATM sequence
    left: dict[str, datetime] = {}
    current = strikes
    in_set = set(current.targets(24500))
    for r in sorted(recentres, key=lambda r: r["ts"]):
        now_set = set(current.targets(r["atm"]))
        for iid in in_set - now_set:
            left.setdefault(iid, ts(r["ts"]))
        for iid in now_set:
            left.pop(iid, None)
        in_set = now_set
    unsub = {r["instrument_id"]: ts(r["ts"]) for r in subs if r["action"] == "unsubscribe"}
    assert unsub, "old strikes must be dropped after retention"
    for iid, when in unsub.items():
        held = (when - left[iid]).total_seconds()
        assert 600.0 <= held <= 601.0, (iid, held)
        # still streaming (depth rows) during retention
        kept = [r for r in depth[iid] if left[iid] + timedelta(seconds=60) < ts(r["timestamp"]) < when]
        assert kept, iid
    for iid, t_left in left.items():
        if t_left + timedelta(seconds=601) < ist(10, 17):
            assert iid in unsub
        else:
            assert iid not in unsub
    sid_of = {i.instrument_id: int(i.security_id) for i in universe.all_instruments()}
    assert set(s.server.sids(22)) == {sid_of[iid] for iid in unsub}


def test_acceptance_4_stale_true_when_depth_older_than_5s(tmp_path: Path) -> None:
    atm_ce = option_sid(24500, "CE")
    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 2),
            source=StubSource(),
            market_kw={"default_hz": 2.0, "silent": {atm_ce: [(ist(10, 1), ist(10, 1, 20))]}},
        )
    )
    iid = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    snaps = [r["payload"] for r in s.rows("quote_snapshots") if r["payload"]["instrument_id"] == iid]
    assert any(p["stale"] for p in snaps)
    assert any(not p["stale"] for p in snaps)
    for p in snaps:
        assert p["stale"] == (p["depth_age_ms"] > 5000)
    stale_times = [
        ts(r["timestamp"])
        for r in s.rows("quote_snapshots")
        if r["payload"]["instrument_id"] == iid and r["payload"]["stale"]
    ]
    # last packet ~10:00:59.5, so 10:01:05 is already > 5 s old
    assert stale_times == [ist(10, 1, 5), ist(10, 1, 10), ist(10, 1, 15), ist(10, 1, 20)]
    status = [r["payload"] for r in s.rows("feed_status") if r["payload"].get("instrument_id") == iid]
    assert [p["status"] for p in status] == ["STALE", "FRESH"]
    assert ist(10, 1, 5) <= ts(status[0]["since"]) <= ist(10, 1, 6)
    # heartbeats continue through the silence, flagged repeat, with the old data time
    silent = [
        r
        for r in s.rows("depth_quotes")
        if r["payload"]["instrument_id"] == iid and ist(10, 1, 1) <= ts(r["timestamp"]) < ist(10, 1, 20)
    ]
    assert len(silent) >= 18
    assert all(r["payload"]["repeat"] and ts(r["payload"]["exchange_ts"]) < ist(10, 1) for r in silent)


def test_acceptance_5_oi_cadence_matches_hand_count(tmp_path: Path) -> None:
    # Unit hand count: baseline at 0 s, changes at 10, 25, 55 s in window [0, 60)
    tracker = OiCadenceTracker(60)
    base = 1_800_000_000.0  # a minute boundary
    for t, oi in [(0, 100), (5, 100), (10, 110), (25, 125), (40, 125), (55, 130)]:
        tracker.observe("X", oi, base + t, "feed_oi")
    [row] = tracker.close_window(base + 60)
    assert (row["oi_updates"], row["median_gap_s"], row["p90_gap_s"]) == (3, 22.5, 28.5)

    # Same hand count end to end: OI packets at 10:01:10, :25, :55 for the ATM CE
    sid = option_sid(24500, "CE")
    schedule = [(ist(10, 1, 10), 1_100_000), (ist(10, 1, 25), 1_250_000), (ist(10, 1, 55), 1_300_000)]

    def oi_at(s_id: int, t: datetime) -> int:
        if s_id != sid:
            return 900_000
        value = 1_000_000
        for when, v in schedule:
            if t >= when:
                value = v
        return value

    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        for when, v in schedule:
            if abs((t - when).total_seconds()) < 1e-6:
                await server.send(oi_packet(sid, NSE_FNO, v))

    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 3, 0.5),
            source=StubSource(),
            hook=hook,
            market_kw={"default_hz": 1.0, "rates": {sid: 0.2}, "oi": oi_at},
        )
    )
    rows = {(r["payload"]["instrument_id"], r["event_ts"]): r["payload"] for r in s.rows("oi_cadence")}
    iid = "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    # first window [10:00, 10:01) is partial (first seen after 10:00:00) and is skipped
    assert (iid, "2026-09-28T10:01:00.000+05:30") not in rows
    w = rows[(iid, "2026-09-28T10:02:00.000+05:30")]
    assert (w["oi_updates"], w["median_gap_s"], w["p90_gap_s"]) == (3, 22.5, 28.5)
    assert w["last_oi_change"] == "2026-09-28T10:01:55.000+05:30"
    assert w["sources"] == ["feed_oi", "full"]
    nxt = rows[(iid, "2026-09-28T10:03:00.000+05:30")]
    assert (nxt["oi_updates"], nxt["median_gap_s"], nxt["last_oi_change"]) == (0, None, "2026-09-28T10:01:55.000+05:30")


def test_acceptance_6_bad_frame_logged_to_ingest_errors_and_recording_continues(tmp_path: Path) -> None:
    ce, pe = option_sid(24500, "CE"), option_sid(24500, "PE")
    good_ce = full_packet(ce, NSE_FNO, 80.0, 79.95, 80.05)
    good_pe = full_packet(pe, NSE_FNO, 70.0, 69.95, 70.05)
    bad_mid = bytes([8]) + (20).to_bytes(2, "little") + bytes([NSE_FNO]) + ce.to_bytes(4, "little") + b"\x00" * 12
    nan_pkt = full_packet(option_sid(24400, "CE"), NSE_FNO, float("nan"), 150.0, 150.1)
    unknown = (
        bytes([99]) + (12).to_bytes(2, "little") + bytes([NSE_FNO]) + ce.to_bytes(4, "little") + b"\x01\x02\x03\x04"
    )
    burst: list[bytes | str] = [
        good_ce + bad_mid + good_pe,
        b"\x01\x02",
        good_ce[:100],
        '{"error":"text"}',
        nan_pkt,
        unknown,
    ]

    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 0, 10):
            for frame in burst:
                await server.send(frame)

    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 0, 30), source=StubSource(), hook=hook))
    assert type(s.recorder.collector) is MarketFeedCollector
    assert s.recorder.collector.connect_count == 1
    errors = s.rows("ingest_errors")
    reasons = [e["reason"] for e in errors]
    assert sum(r.startswith("decode error: full payload too short") for r in reasons) == 2
    assert "2 trailing bytes" in reasons
    assert "text frame (feed responses are binary)" in reasons
    assert "unknown response code 99" in reasons
    assert "non-finite value in full packet; written as null" in reasons
    for e in errors:
        assert e["ts"] == "2026-09-28T10:00:10.000+05:30"
        if e["reason"] != "text frame (feed responses are binary)":
            assert len(e["sha256"]) == 64
            assert base64.b64decode(e["raw_b64"])
    # both good packets of the mixed frame were recorded, with their exact raw bytes
    depth = s.rows("depth_quotes")
    at10 = {r["payload"]["raw_b64"] for r in depth if r["payload"]["exchange_ts"] == "2026-09-28T10:00:10.000+05:30"}
    assert base64.b64encode(good_pe).decode() in at10
    # the NaN packet became a row with a null ltp, not a lost row
    nan_rows = [
        r["payload"]
        for r in depth
        if r["payload"]["instrument_id"] == "NSE_FNO:NIFTY:2026-09-29:24400:CE"
        and r["payload"]["exchange_ts"] == "2026-09-28T10:00:10.000+05:30"
    ]
    assert nan_rows
    assert nan_rows[0]["ltp"] is None
    # recording continued: every instrument has rows carrying data received after the burst
    after = {r["payload"]["instrument_id"] for r in depth if ts(r["payload"]["exchange_ts"]) > ist(10, 0, 20)}
    assert len(after) == 8


def test_acceptance_7_refuses_to_start_without_credentials(tmp_path: Path) -> None:
    env = {**os.environ, "DHAN_CLIENT_ID": "", "DHAN_ACCESS_TOKEN": ""}
    proc = subprocess.run(
        [sys.executable, "-m", "marketdata", "--record-only", "--tape-root", str(tmp_path / "tape")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2
    assert "DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN" in proc.stderr
    assert not list((tmp_path / "tape").rglob("*.jsonl"))

    async def library_level() -> None:
        async with FakeDhanServer() as server:
            empty = Settings(
                credentials=Credentials(client_id="", access_token=""), dry_run=False, feed_ws_base=server.url
            )
            rec = MarketDataRecorder(RecorderConfig(tape_root=tmp_path / "lib"), empty, universe=make_universe())
            with pytest.raises(CredentialsError):
                await rec.run()
            assert server.attempts == []

    asyncio.run(library_level())


def test_acceptance_8_no_credential_in_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    log_file = tmp_path / "recorder.log"
    try:
        listener = setup_logging(log_file)
        # worst case: somebody turns everything, including the websockets client, to DEBUG
        root.setLevel(logging.DEBUG)
        for name in ("websockets", "websockets.client", "dhan_client", "marketdata"):
            logging.getLogger(name).setLevel(logging.DEBUG)
        root.addHandler(caplog.handler)
        caplog.set_level(logging.DEBUG)

        async def with_reconnect(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
            if t == ist(10, 0, 5):
                await server.drop_clients()
                await until(lambda: bool(server.subscribed) and server.connections >= 2, timeout=10)

        s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 0, 15), source=StubSource(), hook=with_reconnect))
    finally:
        listener.stop()
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
        logging.getLogger("websockets").setLevel(logging.WARNING)
    assert s.server.connections >= 2
    # the server really received the credentials, so the check below is meaningful
    assert s.server.query[0]["token"] == [TEST_TOKEN]
    assert s.server.query[0]["clientId"] == [TEST_CLIENT_ID]
    assert any("GET /?" in r.getMessage() for r in caplog.records), "websockets DEBUG handshake line expected"
    captured = "\n".join(r.getMessage() for r in caplog.records)
    texts = [captured, log_file.read_text(encoding="utf-8")]
    texts += [p.read_text(encoding="utf-8") for p in (tmp_path / "tape").rglob("*") if p.is_file()]
    assert "token=REDACTED" in captured
    for text in texts:
        assert TEST_TOKEN not in text
        assert TEST_CLIENT_ID not in text
    assert logsafe.redact(f"GET /?version=2&token={TEST_TOKEN}&clientId=x") == (
        "GET /?version=2&token=REDACTED&clientId=REDACTED"
    )
