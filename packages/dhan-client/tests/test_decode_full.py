"""Tests for FULL packet decoder (V2-D1) with authoritative layout.

Golden test frames built from DhanHQ API v2 documented layout and official SDK.
Sources:
1. https://dhanhq.co/docs/v2/live-market-feed/ (Full Packet table)
2. https://github.com/dhan-oss/DhanHQ-py/blob/63b9030d700f0fd331c124fd948ba0b79a6e7fd8/src/dhanhq/marketfeed.py#L446-L490

Authoritative layout: 162 bytes total
- Header: 8 bytes (code u8, msg_len u16, segment u8, security_id u32)
- Body: 54 bytes (LTP, LTQ, LTT, ATP, volume, total_sell/buy, OI, OI_high/low, OHLC)
- Depth: 100 bytes (5 levels × 20 bytes, INTERLEAVED bid/ask)
"""

import struct

import pytest
from dhan_client.annexure import FeedResponseCode
from dhan_client.decode import decode_frame


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
    oi_day_high: int = 260000,
    oi_day_low: int = 240000,
    day_open: float = 98.00,
    day_close: float = 101.00,
    day_high: float = 102.50,
    day_low: float = 97.50,
    depth_levels: list[tuple[int, int, int, int, float, float]] | None = None,
) -> bytes:
    """Build a golden FULL packet from authoritative layout.

    Args:
        security_id: Security ID (uint32)
        exchange_segment: Exchange segment byte (uint8)
        ltp: Last traded price (float32)
        ltq: Last trade quantity (uint16)
        ltt: Last trade time epoch (uint32)
        atp: Average trade price (float32)
        volume: Volume (uint32)
        total_sell_qty: Total sell quantity (uint32)
        total_buy_qty: Total buy quantity (uint32)
        oi: Open interest (uint32)
        oi_day_high: OI day high (uint32)
        oi_day_low: OI day low (uint32)
        day_open: Day open (float32)
        day_close: Day close (float32)
        day_high: Day high (float32)
        day_low: Day low (float32)
        depth_levels: List of 5 tuples (bid_qty, ask_qty, bid_orders, ask_orders, bid_price, ask_price)

    Returns:
        Complete binary packet (162 bytes: 8 header + 154 payload)
    """
    # Default interleaved depth levels
    if depth_levels is None:
        depth_levels = [
            (100, 110, 5, 6, 100.00, 100.05),  # Level 1
            (200, 180, 8, 7, 99.95, 100.10),   # Level 2
            (150, 140, 6, 5, 99.90, 100.15),   # Level 3
            (120, 130, 4, 4, 99.85, 100.20),   # Level 4
            (100, 110, 3, 3, 99.80, 100.25),   # Level 5
        ]

    # Build payload (154 bytes: 54 body + 100 depth)
    # Body: '<fHIfIIIIIIffff' (54 bytes)
    payload = struct.pack("<f", ltp)  # Bytes 0-3
    payload += struct.pack("<H", ltq)  # Bytes 4-5
    payload += struct.pack("<I", ltt)  # Bytes 6-9
    payload += struct.pack("<f", atp)  # Bytes 10-13
    payload += struct.pack("<I", volume)  # Bytes 14-17
    payload += struct.pack("<I", total_sell_qty)  # Bytes 18-21
    payload += struct.pack("<I", total_buy_qty)  # Bytes 22-25
    payload += struct.pack("<I", oi)  # Bytes 26-29
    payload += struct.pack("<I", oi_day_high)  # Bytes 30-33
    payload += struct.pack("<I", oi_day_low)  # Bytes 34-37
    payload += struct.pack("<f", day_open)  # Bytes 38-41
    payload += struct.pack("<f", day_close)  # Bytes 42-45
    payload += struct.pack("<f", day_high)  # Bytes 46-49
    payload += struct.pack("<f", day_low)  # Bytes 50-53

    # Depth: 5 levels × '<IIHHff' (20 bytes each, interleaved)
    for bid_qty, ask_qty, bid_orders, ask_orders, bid_price, ask_price in depth_levels:
        level_data = struct.pack(
            "<IIHHff",
            bid_qty,
            ask_qty,
            bid_orders,
            ask_orders,
            bid_price,
            ask_price,
        )
        payload += level_data

    # Build header (8 bytes)
    message_length = len(payload) + 8  # Total packet length
    header = struct.pack(
        "<BHBi",  # code(B), length(H), segment(B), security_id(i)
        FeedResponseCode.FULL,  # code = 8
        message_length,
        exchange_segment,
        security_id,
    )

    return header + payload


def test_full_packet_golden_decode() -> None:
    """Golden test: FULL packet decodes to expected fields with correct layout."""
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
        oi_day_high=510000,
        oi_day_low=490000,
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
    assert len(decoded.raw_payload) == 154  # 154-byte payload

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
    assert fields["oi_day_high"] == 510000
    assert fields["oi_day_low"] == 490000
    assert fields["day_open"] == pytest.approx(148.00, abs=0.01)
    assert fields["day_close"] == pytest.approx(151.00, abs=0.01)
    assert fields["day_high"] == pytest.approx(152.50, abs=0.01)
    assert fields["day_low"] == pytest.approx(147.00, abs=0.01)


def test_full_packet_interleaved_depth() -> None:
    """All 5 interleaved depth levels decode correctly."""
    depth_levels = [
        (100, 110, 5, 6, 200.00, 200.05),  # Level 1
        (200, 180, 8, 7, 199.95, 200.10),  # Level 2
        (150, 140, 6, 5, 199.90, 200.15),  # Level 3
        (120, 130, 4, 4, 199.85, 200.20),  # Level 4
        (100, 110, 3, 3, 199.80, 200.25),  # Level 5
    ]

    packet = _build_full_packet(ltp=200.00, depth_levels=depth_levels)

    packets = decode_frame(packet)
    decoded = packets[0]
    fields = decoded.fields

    # Check we have exactly 5 bid and 5 ask levels
    assert "bid_depth" in fields
    assert "ask_depth" in fields
    assert len(fields["bid_depth"]) == 5
    assert len(fields["ask_depth"]) == 5

    # Verify each level
    for i, (bid_qty, ask_qty, bid_orders, ask_orders, bid_price, ask_price) in enumerate(
        depth_levels
    ):
        bid = fields["bid_depth"][i]
        assert bid["price"] == pytest.approx(bid_price, abs=0.01)
        assert bid["quantity"] == bid_qty
        assert bid["orders"] == bid_orders

        ask = fields["ask_depth"][i]
        assert ask["price"] == pytest.approx(ask_price, abs=0.01)
        assert ask["quantity"] == ask_qty
        assert ask["orders"] == ask_orders


def test_full_packet_exact_size():
    """FULL packet must be exactly 162 bytes (8 header + 154 payload)."""
    packet = _build_full_packet()
    
    # Check total packet size
    assert len(packet) == 162, f"Expected 162 bytes, got {len(packet)}"
    
    # Check header size
    header_bytes = packet[:8]
    assert len(header_bytes) == 8
    
    # Check payload size
    payload_bytes = packet[8:]
    assert len(payload_bytes) == 154


def test_full_packet_oi_high_low() -> None:
    """OI day high and low fields decode correctly."""
    packet = _build_full_packet(
        oi=750000,
        oi_day_high=780000,
        oi_day_low=720000,
    )

    packets = decode_frame(packet)
    fields = packets[0].fields

    assert fields["oi"] == 750000
    assert fields["oi_day_high"] == 780000
    assert fields["oi_day_low"] == 720000


def test_full_packet_truncated_raises_decode_error():
    """Truncated FULL packet raises DecodeError."""
    full_packet = _build_full_packet()

    # Truncate to only 100 bytes (needs 162)
    truncated = full_packet[:100]

    # decode_frame logs and skips bad packets, returns empty list
    packets = decode_frame(truncated)
    assert len(packets) == 0  # Bad packet skipped


def test_full_packet_garbage_data_raises_decode_error():
    """Garbage FULL packet raises DecodeError and is skipped."""
    # Build header for FULL packet but with garbage payload
    header = struct.pack(
        "<BHBi",
        FeedResponseCode.FULL,  # code = 8
        170,  # Claim valid length
        1,  # segment
        12345,  # security_id
    )
    # Add garbage data (not enough bytes)
    garbage_payload = b"garbage" * 10  # Only 70 bytes, need 154

    packet = header + garbage_payload

    # decode_frame catches the error and skips the packet
    packets = decode_frame(packet)
    assert len(packets) == 0  # Bad packet skipped


def test_full_packet_decoder_verified_flag():
    """FULL packet includes decoder_verified flag (False until verified)."""
    packet = _build_full_packet()
    packets = decode_frame(packet)
    decoded = packets[0]

    # Check that decoder_verified flag exists and is False
    assert hasattr(decoded, "decoder_verified")
    assert decoded.decoder_verified is False
    # Should have note about verification
    assert any("not yet verified" in note for note in decoded.notes)


def test_full_packet_raw_payload_preserved():
    """FULL packet preserves raw_payload for verification."""
    packet = _build_full_packet(security_id=99999)
    packets = decode_frame(packet)
    decoded = packets[0]

    # raw_payload should be preserved (154 bytes)
    assert len(decoded.raw_payload) == 154
    # We can rebuild the packet from raw_payload if needed
    assert decoded.raw_payload == packet[8:]  # Skip 8-byte header


def test_quote_packet_unchanged():
    """QUOTE packet decoding unchanged (regression test)."""
    # Build QUOTE packet (code 4) - existing format
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


def test_full_packet_multiple_in_frame() -> None:
    """Multiple FULL packets in one frame decode correctly."""
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


def test_full_packet_ohlc_fields() -> None:
    """OHLC fields decode correctly."""
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


def test_full_packet_volume_and_oi() -> None:
    """Volume and OI fields decode correctly."""
    packet = _build_full_packet(
        volume=5000000,
        oi=750000,
        oi_day_high=780000,
        oi_day_low=720000,
        total_buy_qty=2800000,
        total_sell_qty=2200000,
    )

    packets = decode_frame(packet)
    fields = packets[0].fields

    assert fields["volume"] == 5000000
    assert fields["oi"] == 750000
    assert fields["oi_day_high"] == 780000
    assert fields["oi_day_low"] == 720000
    assert fields["total_buy_quantity"] == 2800000
    assert fields["total_sell_quantity"] == 2200000


def test_bad_packet_logged_and_skipped():
    """Bad packet is logged and skipped without crashing."""
    # Build one good packet, then a bad (malformed) packet
    good1 = _build_full_packet(security_id=111, ltp=100.0)
    
    # Create a malformed FULL packet with wrong payload length
    bad_header = struct.pack(
        "<BHBi",
        FeedResponseCode.FULL,  # code = 8
        50,  # Wrong length (too short)
        1,
        222,
    )
    bad_payload = b"x" * 42  # Only 42 bytes, need 154
    bad = bad_header + bad_payload
    
    # Good packet after bad one
    good2 = _build_full_packet(security_id=333, ltp=300.0)

    # Each packet separately should work for good ones
    packets1 = decode_frame(good1)
    assert len(packets1) == 1
    assert packets1[0].header.security_id == 111

    # Bad packet alone should be skipped
    packets_bad = decode_frame(bad)
    assert len(packets_bad) == 0  # Bad packet is logged and skipped

    packets2 = decode_frame(good2)
    assert len(packets2) == 1
    assert packets2[0].header.security_id == 333


def test_layout_offsets_exact() -> None:
    """Test that layout offsets match documented structure exactly."""
    packet = _build_full_packet(
        ltp=123.45,
        ltq=99,
        ltt=1234567890,
        atp=123.00,
        volume=9999999,
        total_sell_qty=5000000,
        total_buy_qty=4999999,
        oi=888888,
        oi_day_high=900000,
        oi_day_low=850000,
        day_open=120.00,
        day_close=125.00,
        day_high=126.50,
        day_low=119.50,
    )

    payload = packet[8:]  # Skip header
    
    # Verify each field at exact offset
    assert struct.unpack_from("<f", payload, 0)[0] == pytest.approx(123.45, abs=0.01)  # LTP @0
    assert struct.unpack_from("<H", payload, 4)[0] == 99  # LTQ @4
    assert struct.unpack_from("<I", payload, 6)[0] == 1234567890  # LTT @6
    assert struct.unpack_from("<f", payload, 10)[0] == pytest.approx(123.00, abs=0.01)  # ATP @10
    assert struct.unpack_from("<I", payload, 14)[0] == 9999999  # volume @14
    assert struct.unpack_from("<I", payload, 18)[0] == 5000000  # total_sell @18
    assert struct.unpack_from("<I", payload, 22)[0] == 4999999  # total_buy @22
    assert struct.unpack_from("<I", payload, 26)[0] == 888888  # OI @26
    assert struct.unpack_from("<I", payload, 30)[0] == 900000  # OI_high @30
    assert struct.unpack_from("<I", payload, 34)[0] == 850000  # OI_low @34
    assert struct.unpack_from("<f", payload, 38)[0] == pytest.approx(120.00, abs=0.01)  # open @38
    assert struct.unpack_from("<f", payload, 42)[0] == pytest.approx(125.00, abs=0.01)  # close @42
    assert struct.unpack_from("<f", payload, 46)[0] == pytest.approx(126.50, abs=0.01)  # high @46
    assert struct.unpack_from("<f", payload, 50)[0] == pytest.approx(119.50, abs=0.01)  # low @50
    
    # Verify depth starts at offset 54
    first_level = struct.unpack_from("<IIHHff", payload, 54)
    assert len(first_level) == 6  # bid_qty, ask_qty, bid_orders, ask_orders, bid_price, ask_price


def test_sdk_cross_check() -> None:
    """SDK cross-check: hand-built 162-byte frame with distinct values in every field,
    decoded field-by-field against expected values computed with struct directly from
    the documented layout (independent of decode.py's own format strings)."""
    # Hand-build with distinct values for every field
    security_id = 987654
    exchange_segment = 3
    ltp = 111.11
    ltq = 11
    ltt = 1111111111
    atp = 222.22
    volume = 2222222
    total_sell = 333333
    total_buy = 444444
    oi = 555555
    oi_high = 666666
    oi_low = 777777
    day_open = 88.88
    day_close = 99.99
    day_high = 100.10
    day_low = 77.77
    
    # 5 levels with distinct values
    depth = [
        (1000, 1001, 10, 11, 110.00, 110.05),  # L1
        (2000, 2001, 20, 21, 109.95, 110.10),  # L2
        (3000, 3001, 30, 31, 109.90, 110.15),  # L3
        (4000, 4001, 40, 41, 109.85, 110.20),  # L4
        (5000, 5001, 50, 51, 109.80, 110.25),  # L5
    ]
    
    # Build payload manually using struct (the documented layout)
    payload = struct.pack("<f", ltp)
    payload += struct.pack("<H", ltq)
    payload += struct.pack("<I", ltt)
    payload += struct.pack("<f", atp)
    payload += struct.pack("<I", volume)
    payload += struct.pack("<I", total_sell)
    payload += struct.pack("<I", total_buy)
    payload += struct.pack("<I", oi)
    payload += struct.pack("<I", oi_high)
    payload += struct.pack("<I", oi_low)
    payload += struct.pack("<f", day_open)
    payload += struct.pack("<f", day_close)
    payload += struct.pack("<f", day_high)
    payload += struct.pack("<f", day_low)
    
    for bq, aq, bo, ao, bp, ap in depth:
        payload += struct.pack("<IIHHff", bq, aq, bo, ao, bp, ap)
    
    # Build header
    msg_len = len(payload) + 8
    header = struct.pack("<BHBi", 8, msg_len, exchange_segment, security_id)
    packet = header + payload
    
    # Decode using decode_frame
    packets = decode_frame(packet)
    assert len(packets) == 1
    decoded = packets[0]
    
    # Verify header fields
    assert decoded.header.response_code == 8
    assert decoded.header.security_id == security_id
    assert decoded.header.exchange_segment_byte == exchange_segment
    
    # Verify body fields against expected values
    f = decoded.fields
    assert f["ltp"] == pytest.approx(ltp, abs=0.01)
    assert f["last_quantity"] == ltq
    assert f["last_trade_time_epoch"] == ltt
    assert f["atp"] == pytest.approx(atp, abs=0.01)
    assert f["volume"] == volume
    assert f["total_sell_quantity"] == total_sell
    assert f["total_buy_quantity"] == total_buy
    assert f["oi"] == oi
    assert f["oi_day_high"] == oi_high
    assert f["oi_day_low"] == oi_low
    assert f["day_open"] == pytest.approx(day_open, abs=0.01)
    assert f["day_close"] == pytest.approx(day_close, abs=0.01)
    assert f["day_high"] == pytest.approx(day_high, abs=0.01)
    assert f["day_low"] == pytest.approx(day_low, abs=0.01)
    
    # Verify depth levels
    assert len(f["bid_depth"]) == 5
    assert len(f["ask_depth"]) == 5
    for i, (bq, aq, bo, ao, bp, ap) in enumerate(depth):
        assert f["bid_depth"][i]["quantity"] == bq
        assert f["bid_depth"][i]["orders"] == bo
        assert f["bid_depth"][i]["price"] == pytest.approx(bp, abs=0.01)
        assert f["ask_depth"][i]["quantity"] == aq
        assert f["ask_depth"][i]["orders"] == ao
        assert f["ask_depth"][i]["price"] == pytest.approx(ap, abs=0.01)


def test_decode_frame_bad_packet_between_good() -> None:
    """decode_frame with a bad packet between two good packets in the same frame:
    the bad packet is skipped and logged, and both good packets are decoded."""
    good1 = _build_full_packet(security_id=111, ltp=100.0)
    good2 = _build_full_packet(security_id=222, ltp=200.0)
    
    # Bad packet: valid header but truncated payload (only 50 bytes instead of 154)
    bad_header = struct.pack("<BHBi", 8, 58, 1, 999)  # 8 byte header + 50 payload = 58 total
    bad_payload = b"X" * 50  # Not enough for a valid FULL packet
    bad = bad_header + bad_payload
    
    # Frame: good1 + bad + good2
    frame = good1 + bad + good2
    
    packets = decode_frame(frame)
    # Should decode good1 and good2, skip bad
    assert len(packets) == 2
    assert packets[0].header.security_id == 111
    assert packets[0].fields["ltp"] == pytest.approx(100.0, abs=0.01)
    assert packets[1].header.security_id == 222
    assert packets[1].fields["ltp"] == pytest.approx(200.0, abs=0.01)
