"""Test vendored types."""

from __future__ import annotations

from marketdata.types import DepthQuote, IngestError, OiCadence, QuoteSnapshot


def test_depth_quote_creation() -> None:
    """DepthQuote can be created with all fields."""
    dq = DepthQuote(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
        bid=100.0,
        bid_qty=100,
        ask=100.05,
        ask_qty=110,
        ltp=100.02,
        oi=50000,
        levels={"bid": [[100.0, 100]], "ask": [[100.05, 110]]},
        exchange_ts="2026-09-27T10:00:00+05:30",
        repeat=False,
        stale=False,
        raw_b64=None,
    )
    assert dq.instrument_id == "NSE_FNO:NIFTY:2026-09-29:24500:CE"
    assert dq.bid == 100.0


def test_quote_snapshot_creation() -> None:
    """QuoteSnapshot can be created."""
    qs = QuoteSnapshot(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
        rule="ATM",
        side="CE",
        bid=100.0,
        ask=100.05,
        mid=100.025,
        spread=0.05,
        ltp=100.02,
        ltt="2026-09-27T10:00:00+05:30",
        oi=50000,
        depth_age_ms=100,
        stale=False,
    )
    assert qs.rule == "ATM"
    assert qs.side == "CE"


def test_oi_cadence_creation() -> None:
    """OiCadence can be created."""
    oi = OiCadence(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
        window_s=60,
        oi_updates=3,
        median_gap_s=15.0,
        p90_gap_s=25.0,
        last_oi_change="2026-09-27T10:00:00+05:30",
        sources=["FULL"],
    )
    assert oi.oi_updates == 3


def test_ingest_error_creation() -> None:
    """IngestError can be created."""
    err = IngestError(
        ts="2026-09-27T10:00:00+05:30",
        source="decode",
        reason="bad packet",
        offset=100,
        sha256="abc123",
        raw_b64="dGVzdA==",
    )
    assert err.source == "decode"
