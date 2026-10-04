"""Index ticks: ticker/quote subscribe, synthetic packets, staleness on the right type."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from md_fake_dhan import (
    FakeDhanServer,
    StubSource,
    dhan_ltt,
    index_packet,
    ist,
    quote_packet,
    run_session,
    ticker_packet,
)

from marketdata.frames import decode_frame_checked
from marketdata.recorder import MarketDataRecorder


def test_index_subscribed_in_ticker_not_full(tmp_path: Path) -> None:
    s = asyncio.run(run_session(tmp_path, ist(10, 0), ist(10, 0, 8), source=StubSource()))
    ticker_sids = set(s.server.sids(15))
    quote_sids = set(s.server.sids(17))
    full_sids = set(s.server.sids(21))
    assert 13 in ticker_sids
    assert 13 not in full_sids
    assert 13 not in quote_sids
    assert full_sids


def test_index_synthetic_packet_updates_spot_and_clears_stale(tmp_path: Path) -> None:
    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 0, 12):
            await server.send(index_packet(13, 24540.0, dhan_ltt(t)))

    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 16),
            source=StubSource(),
            market_kw={"silent": {13: [(ist(10, 0), ist(10, 1))]}},
            config_kw={"stale_after_s": 5.0, "spot_fallback_after_s": 60.0},
            hook=hook,
        )
    )
    iid = "NSE_IDX:NIFTY"
    status = [r["payload"] for r in s.rows("feed_status") if r["payload"].get("instrument_id") == iid]
    kinds = [p["status"] for p in status]
    assert "STALE" in kinds
    assert "FRESH" in kinds
    assert kinds.index("STALE") < kinds.index("FRESH")
    assert s.recorder.spot == 24540.0


def test_index_ticker_and_quote_packets_are_freshness(tmp_path: Path) -> None:
    sent: list[str] = []

    async def hook(t: datetime, server: FakeDhanServer, _rec: MarketDataRecorder) -> None:
        if t == ist(10, 0, 12) and "ticker" not in sent:
            sent.append("ticker")
            await server.send(ticker_packet(13, 0, 24550.0, dhan_ltt(t)))
        if t == ist(10, 0, 20) and "quote" not in sent:
            sent.append("quote")
            await server.send(quote_packet(13, 0, 24555.0, dhan_ltt(t)))

    s = asyncio.run(
        run_session(
            tmp_path,
            ist(10, 0),
            ist(10, 0, 24),
            source=StubSource(),
            market_kw={"silent": {13: [(ist(10, 0), ist(10, 1))]}},
            config_kw={"stale_after_s": 5.0, "spot_fallback_after_s": 60.0},
            hook=hook,
        )
    )
    iid = "NSE_IDX:NIFTY"
    status = [r["payload"]["status"] for r in s.rows("feed_status") if r["payload"].get("instrument_id") == iid]
    assert status.count("STALE") >= 1
    assert status.count("FRESH") >= 1
    assert s.recorder.spot == 24555.0
    packets, errors = decode_frame_checked(ticker_packet(13, 0, 24550.0, 1_700_000_000))
    assert errors == []
    assert packets[0].decoded.kind == "ticker"
    assert packets[0].decoded.fields["ltp"] == 24550.0
    packets, errors = decode_frame_checked(quote_packet(13, 0, 24555.0, 1_700_000_000))
    assert errors == []
    assert packets[0].decoded.kind == "quote"
    assert packets[0].decoded.header.security_id == 13
