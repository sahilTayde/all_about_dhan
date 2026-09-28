"""Index packet decode (synthetic / recorded layout) and mixed-mode subscribe."""

from __future__ import annotations

import struct

import pytest
from dhan_client.annexure import FeedRequestCode, FeedResponseCode
from dhan_client.decode import decode_frame
from dhan_client.feed import (
    feed_mode_for,
    subscribe_messages,
    subscribe_messages_for_modes,
)
from dhan_client.types import FeedInstrument, FeedMode


def _header(code: int, length: int, seg: int, sid: int) -> bytes:
    return struct.pack("<BHBI", code, length, seg, sid)


def _index_frame(ltp: float, ltt: int | None = None, sid: int = 13) -> bytes:
    payload = struct.pack("<f", ltp)
    if ltt is not None:
        payload += struct.pack("<i", ltt)
    return _header(FeedResponseCode.INDEX, 8 + len(payload), 0, sid) + payload


def test_index_packet_ltp_only_still_decodes() -> None:
    packets = decode_frame(_index_frame(18500.50))
    assert len(packets) == 1
    assert packets[0].kind == "index"
    assert packets[0].fields["ltp"] == pytest.approx(18500.50, abs=0.01)
    assert "last_trade_time_epoch" not in packets[0].fields


def test_index_packet_synthetic_ltp_and_ltt() -> None:
    packets = decode_frame(_index_frame(24512.35, ltt=1_700_000_000, sid=13))
    assert len(packets) == 1
    decoded = packets[0]
    assert decoded.kind == "index"
    assert decoded.header.security_id == 13
    assert decoded.header.exchange_segment == "IDX_I"
    assert decoded.fields["ltp"] == pytest.approx(24512.35, abs=0.01)
    assert decoded.fields["last_trade_time_epoch"] == 1_700_000_000


def test_index_ticker_request_messages_split_from_full() -> None:
    index = FeedInstrument("IDX_I", "13")
    fut = FeedInstrument("NSE_FNO", "35000")
    opt = FeedInstrument("NSE_FNO", "40000")
    modes = {
        ("IDX_I", "13"): FeedMode.TICKER,
        ("NSE_FNO", "35000"): FeedMode.FULL,
        ("NSE_FNO", "40000"): FeedMode.FULL,
    }
    messages = subscribe_messages_for_modes(
        [index, fut, opt], modes, default=FeedMode.FULL
    )
    codes = {int(m["RequestCode"]): m for m in messages}
    assert codes[int(FeedRequestCode.SUBSCRIBE_TICKER)]["InstrumentCount"] == 1
    assert (
        codes[int(FeedRequestCode.SUBSCRIBE_TICKER)]["InstrumentList"][0]["SecurityId"]
        == "13"
    )
    assert codes[int(FeedRequestCode.SUBSCRIBE_FULL)]["InstrumentCount"] == 2
    assert {
        row["SecurityId"]
        for row in codes[int(FeedRequestCode.SUBSCRIBE_FULL)]["InstrumentList"]
    } == {
        "35000",
        "40000",
    }


def test_feed_mode_for_idx_i_is_ticker_not_full() -> None:
    assert (
        feed_mode_for(FeedInstrument("IDX_I", "13"), default=FeedMode.FULL)
        == FeedMode.TICKER
    )
    assert (
        feed_mode_for(FeedInstrument("NSE_FNO", "35000"), default=FeedMode.FULL)
        == FeedMode.FULL
    )
    assert (
        feed_mode_for(
            FeedInstrument("IDX_I", "13"),
            default=FeedMode.FULL,
            index_mode=FeedMode.QUOTE,
        )
        == FeedMode.QUOTE
    )


def test_single_mode_subscribe_messages_unchanged() -> None:
    insts = [FeedInstrument("NSE_EQ", "1333")]
    [msg] = subscribe_messages(insts, FeedMode.TICKER)
    assert msg["RequestCode"] == int(FeedRequestCode.SUBSCRIBE_TICKER)
    assert msg["InstrumentCount"] == 1
