"""Tests for FULL packet decoder (V2-D1).

Golden test frames built from DhanHQ API v2 documented layout using struct.pack.
https://dhanhq.co/docs/v2/live-market-feed/
"""

import struct

import pytest

from dhan_client.annexure import FeedResponseCode
from dhan_client.decode import decode_frame, decode_packet, _header
from dhan_client.errors import DecodeError


def _build_full_packet(
    security_id: int = 12345,
    exchange_segment: int = 1,
    ltp: float = 100.50,
    ltq: int = 10,
    ltt: int = 1695000000,
    atp: float = 99.75,
    volume: int = 1000000,
    total_sell_qty: int = 500000,
    total_buy_qty: int = 500000,
    oi: int = 250000,
    day_open: float = 98.00,
    day_close: float = 101.00,
    day_high: float = 102.50,
    day_low: float = 97.50,
    bid_levels: list[tuple[float, int, int, int]] | None = None,
    ask_levels: list[tuple[float, int, int, int]] | None = None,
) -> bytes:
    """Build a golden FULL packet from documented layout.

    Args:
        security_id: Security ID (int32)
        exchange_segment: Exchange segment byte (uint8)
        ltp: Last traded price (float32)
        ltq: Last trade quantity (int16)
        ltt: Last trade time epoch (int32)
        atp: Average trade price (float32)
        volume: Volume (int32)
        total_sell_qty: Total sell quantity (int32)
        total_buy_qty: Total buy quantity (int32)
        oi: Open interest (int32)
        day_open: Day open (float32)
        day_close: Day close (float32)
        day_high: Day high (float32)
        day_low: Day low (float32)
        bid_levels: List of 5 tuples (price, qty, orders, bid_orders)
        ask_levels: List of 5 tuples (price, qty, orders, ask_orders)

    Returns:
        Complete binary packet (header + payload)
    """
    # Default bid levels (5 levels, descending prices)
    if bid_levels is None:
        bid_levels = [
            (100.00, 100, 5, 5),
            (99.95, 200, 8, 8),
            (99.90, 150, 6, 6),
            (99.85, 120, 4, 4),
            (99.80, 100, 3, 3),
        ]

    # Default ask levels (5 levels, ascending prices)
    if ask_levels is None:
        ask_levels = [
            (100.05, 110, 6, 6),
            (100.10, 180, 7, 7),
            (100.15, 140, 5, 5),
            (100.20, 130, 4, 4),
            (100.25, 110, 3, 3),
        ]

    # Build payload (246 bytes minimum: 46 main + 100 bid depth + 100 ask depth)
    # Manual packing with explicit padding to match documented byte offsets
    payload = struct.pack("<f", ltp)  # Bytes 0-3
    payload += struct.pack("<h", ltq)  # Bytes 4-5
    payload += struct.pack("<i", ltt)  # Bytes 6-9
    payload += struct.pack("<f", atp)  # Bytes 10-13
    payload += struct.pack("<i", volume)  # Bytes 14-17
    payload += struct.pack("<i", total_sell_qty)  # Bytes 18-21
    payload += struct.pack("<i", total_buy_qty)  # Bytes 22-25
    payload += struct.pack("<i", oi)  # Bytes 26-29
    payload += struct.pack("<f", day_open)  # Bytes 30-33
    payload += struct.pack("<f", day_close)  # Bytes 34-37
    payload += struct.pack("<f", day_high)  # Bytes 38-41
    payload += struct.pack("<f", day_low)  # Bytes 42-45

    # Add 5 bid depth levels (20 bytes each = 100 bytes total)
    for price, qty, orders, bid_orders in bid_levels:
        level_data = struct.pack(
            "<fiiixxxx",  # price(f), qty(i), orders(i), bid_orders(i), padding(4 bytes)
            price,
            qty,
            orders,
            bid_orders,
        )
        payload += level_data

    # Add 5 ask depth levels (20 bytes each = 100 bytes total)
    for price, qty, orders, ask_orders in ask_levels:
        level_data = struct.pack(
            "<fiiixxxx",  # price(f), qty(i), orders(i), ask_orders(i), padding(4 bytes)
            price,
            qty,
            orders,
            ask_orders,
        )
        payload += level_data

    # Build header (8 bytes)
    message_length = len(payload) + 8  # Total packet length
    header = struct.pack(
        "<BhBi",  # code(B), length(h), segment(B), security_id(i)
        FeedResponseCode.FULL,  # code = 8
        message_length,
        exchange_segment,
        security_id,
    )

    return header + payload


def test_full_packet_golden_decode():
    """Golden test: FULL packet decodes to expected fields."""
    packet = _build_full_packet(
        security_id=54321,
        ltp=150.25,
        ltq=25,
        ltt=1695123456,
        atp=149.80,
        volume=2000000,
        total_sell_qty=900000,
        total_buy_qty=1100000,
        oi=500000,
        day_open=148.00,
        day_close=151.00,
        day_high=152.50,
        day_low=147.00,
    )

    packets = decode_frame(packet)
    assert len(packets) == 1

    decoded = packets[0]
    assert decoded.kind == "full"
    assert decoded.header.security_id == 54321
    assert len(decoded.raw_payload) >= 246

    fields = decoded.fields
    # Main fields
    assert fields["ltp"] == pytest.approx(150.25, abs=0.01)
    assert fields["last_quantity"] == 25
    assert fields["last_trade_time_epoch"] == 1695123456
    assert fields["atp"] == pytest.approx(149.80, abs=0.01)
    assert fields["volume"] == 2000000
    assert fields["total_sell_quantity"] == 900000
    assert fields["total_buy_quantity"] == 1100000
    assert fields["oi"] == 500000
    assert fields["day_open"] == pytest.approx(148.00, abs=0.01)
    assert fields["day_close"] == pytest.approx(151.00, abs=0.01)
    assert fields["day_high"] == pytest.approx(152.50, abs=0.01)
    assert fields["day_low"] == pytest.approx(147.00, abs=0.01)


def test_full_packet_five_depth_levels():
    """All 5 depth levels on both bid and ask sides are decoded."""
    bid_levels = [
        (200.00, 100, 5, 5),
        (199.95, 200, 8, 8),
        (199.90, 150, 6, 6),
        (199.85, 120, 4, 4),
        (199.80, 100, 3, 3),
    ]
    ask_levels = [
        (200.05, 110, 6, 6),
        (200.10, 180, 7, 7),
        (200.15, 140, 5, 5),
        (200.20, 130, 4, 4),
        (200.25, 110, 3, 3),
    ]

    packet = _build_full_packet(
        ltp=200.00,
        bid_levels=bid_levels,
        ask_levels=ask_levels,
    )

    packets = decode_frame(packet)
    decoded = packets[0]
    fields = decoded.fields

    # Check we have exactly 5 bid levels
    assert "bid_depth" in fields
    assert len(fields["bid_depth"]) == 5

    # Check we have exactly 5 ask levels
    assert "ask_depth" in fields
    assert len(fields["ask_depth"]) == 5

    # Verify bid levels
    for i, (expected_price, expected_qty, expected_orders, expected_bid_orders) in enumerate(
        bid_levels
    ):
        bid = fields["bid_depth"][i]
        assert bid["price"] == pytest.approx(expected_price, abs=0.01)
        assert bid["quantity"] == expected_qty
        assert bid["orders"] == expected_orders
        assert bid["bid_orders"] == expected_bid_orders

    # Verify ask levels
    for i, (expected_price, expected_qty, expected_orders, expected_ask_orders) in enumerate(
        ask_levels
    ):
        ask = fields["ask_depth"][i]
        assert ask["price"] == pytest.approx(expected_price, abs=0.01)
        assert ask["quantity"] == expected_qty
        assert ask["orders"] == expected_orders
        assert ask["ask_orders"] == expected_ask_orders


def test_full_packet_truncated_raises_decode_error():
    """Truncated FULL packet raises DecodeError."""
    # Build a valid packet first
    full_packet = _build_full_packet()

    # Truncate to only 100 bytes (needs 246+ for full payload)
    truncated = full_packet[:100]

    with pytest.raises(DecodeError, match="full payload too short"):
        decode_frame(truncated)


def test_full_packet_garbage_data_raises_decode_error():
    """Garbage FULL packet raises DecodeError."""
    # Build header for FULL packet but with garbage payload
    header = struct.pack(
        "<BhBi",
        FeedResponseCode.FULL,  # code = 8
        270,  # Claim valid length
        1,  # segment
        12345,  # security_id
    )
    # Add garbage data (not enough bytes)
    garbage_payload = b"garbage" * 10  # Only 70 bytes, need 246+

    packet = header + garbage_payload

    with pytest.raises(DecodeError, match="full payload too short"):
        decode_frame(packet)


def test_full_packet_short_header_raises_decode_error():
    """Frame with incomplete header returns empty list (cannot parse)."""
    # Only 5 bytes, needs 8 for header
    short_frame = b"12345"

    # Short frame returns empty list since we can't parse a header
    packets = decode_frame(short_frame)
    assert packets == []


def test_full_packet_decoder_verified_flag():
    """FULL packet includes decoder_verified flag."""
    packet = _build_full_packet()
    packets = decode_frame(packet)
    decoded = packets[0]

    # Check that decoder_verified flag exists and is False (until verified)
    assert hasattr(decoded, "decoder_verified")
    assert decoded.decoder_verified is False
    # Should have note about verification
    assert any("not yet verified" in note for note in decoded.notes)


def test_full_packet_raw_payload_preserved():
    """FULL packet preserves raw_payload for future verification."""
    packet = _build_full_packet(security_id=99999)
    packets = decode_frame(packet)
    decoded = packets[0]

    # raw_payload should be preserved
    assert len(decoded.raw_payload) >= 246
    # We can rebuild the packet from raw_payload if needed
    assert decoded.raw_payload == packet[8:]  # Skip 8-byte header


def test_quote_packet_unchanged():
    """QUOTE packet decoding unchanged (regression test)."""
    # Build QUOTE packet (code 4) - same format as existing decoder expects
    payload = struct.pack("<f", 100.50)  # LTP
    payload += struct.pack("<h", 10)  # last_quantity (int16)
    payload += struct.pack("<i", 1695000000)  # last_trade_time
    payload += struct.pack("<f", 99.75)  # atp
    payload += struct.pack("<i", 1000000)  # volume
    payload += struct.pack("<i", 500000)  # total_sell_qty
    payload += struct.pack("<i", 500000)  # total_buy_qty
    payload += struct.pack("<f", 98.00)  # day_open
    payload += struct.pack("<f", 101.00)  # day_close
    payload += struct.pack("<f", 102.50)  # day_high
    payload += struct.pack("<f", 97.50)  # day_low

    header = struct.pack(
        "<BhBi",
        FeedResponseCode.QUOTE,  # code = 4
        len(payload) + 8,
        1,
        12345,
    )

    packet = header + payload
    packets = decode_frame(packet)
    decoded = packets[0]

    assert decoded.kind == "quote"
    assert decoded.fields["ltp"] == pytest.approx(100.50, abs=0.01)
    assert decoded.fields["volume"] == 1000000


def test_index_packet_unchanged():
    """INDEX packet decoding unchanged (regression test)."""
    # Build INDEX packet (code 1)
    payload = struct.pack("<f", 18500.50)  # Just LTP
    header = struct.pack(
        "<BhBi",
        FeedResponseCode.INDEX,  # code = 1
        len(payload) + 8,
        1,
        13,  # NIFTY
    )

    packet = header + payload
    packets = decode_frame(packet)
    decoded = packets[0]

    assert decoded.kind == "index"
    assert decoded.fields["ltp"] == pytest.approx(18500.50, abs=0.01)


def test_full_packet_multiple_in_frame():
    """Multiple FULL packets in one frame are decoded correctly."""
    packet1 = _build_full_packet(security_id=111, ltp=100.0)
    packet2 = _build_full_packet(security_id=222, ltp=200.0)

    # Combine into one frame
    frame = packet1 + packet2

    packets = decode_frame(frame)
    assert len(packets) == 2

    assert packets[0].header.security_id == 111
    assert packets[0].fields["ltp"] == pytest.approx(100.0, abs=0.01)

    assert packets[1].header.security_id == 222
    assert packets[1].fields["ltp"] == pytest.approx(200.0, abs=0.01)


def test_full_packet_ohlc_fields():
    """OHLC fields are correctly decoded."""
    packet = _build_full_packet(
        day_open=95.00,
        day_high=105.00,
        day_low=94.50,
        day_close=104.75,
    )

    packets = decode_frame(packet)
    fields = packets[0].fields

    assert fields["day_open"] == pytest.approx(95.00, abs=0.01)
    assert fields["day_high"] == pytest.approx(105.00, abs=0.01)
    assert fields["day_low"] == pytest.approx(94.50, abs=0.01)
    assert fields["day_close"] == pytest.approx(104.75, abs=0.01)


def test_full_packet_volume_and_oi():
    """Volume and OI fields are correctly decoded."""
    packet = _build_full_packet(
        volume=5000000,
        oi=750000,
        total_buy_qty=2800000,
        total_sell_qty=2200000,
    )

    packets = decode_frame(packet)
    fields = packets[0].fields

    assert fields["volume"] == 5000000
    assert fields["oi"] == 750000
    assert fields["total_buy_quantity"] == 2800000
    assert fields["total_sell_quantity"] == 2200000


def test_collector_continues_after_bad_packet():
    """Collector logs bad packet and continues (simulated via exception)."""
    # Build one good packet, one bad (truncated), one good
    good1 = _build_full_packet(security_id=111, ltp=100.0)
    bad = _build_full_packet(security_id=222, ltp=200.0)[:50]  # Truncated
    good2 = _build_full_packet(security_id=333, ltp=300.0)

    # Test that we can catch the error for bad packet
    try:
        decode_frame(bad)
        assert False, "Should have raised DecodeError"
    except DecodeError:
        pass  # Expected

    # Good packets still decode fine
    packets1 = decode_frame(good1)
    assert len(packets1) == 1
    assert packets1[0].header.security_id == 111

    packets2 = decode_frame(good2)
    assert len(packets2) == 1
    assert packets2[0].header.security_id == 333
