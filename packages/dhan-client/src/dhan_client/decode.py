"""Binary decoder for Dhan Live Market Feed.

https://dhanhq.co/docs/v2/live-market-feed/

FULL Packet Binary Layout (Response Code 8)
--------------------------------------------
Authoritative sources:
1. DhanHQ API v2 Live Market Feed - Full Packet table
   https://dhanhq.co/docs/v2/live-market-feed/
2. Official DhanHQ Python SDK - process_full function
   https://github.com/dhan-oss/DhanHQ-py/blob/63b9030d700f0fd331c124fd948ba0b79a6e7fd8/src/dhanhq/marketfeed.py#L446-L490

Total packet: 162 bytes (8-byte header + 154-byte payload)

Header (8 bytes, all packets):
- Byte 0: Response code (uint8) = 8 for FULL
- Bytes 1-2: Message length (uint16, little-endian)
- Byte 3: Exchange segment (uint8)
- Bytes 4-7: Security ID (uint32, little-endian)

Payload (154 bytes, little-endian):
Body fields (54 bytes, offset 8-61):
- Bytes 8-11:   LTP (float32)
- Bytes 12-13:  Last Trade Quantity - LTQ (uint16)
- Bytes 14-17:  Last Trade Time - LTT (uint32, epoch)
- Bytes 18-21:  Average Trade Price - ATP (float32)
- Bytes 22-25:  Volume (uint32)
- Bytes 26-29:  Total Sell Quantity (uint32)
- Bytes 30-33:  Total Buy Quantity (uint32)
- Bytes 34-37:  Open Interest - OI (uint32)
- Bytes 38-41:  OI Day High (uint32)
- Bytes 42-45:  OI Day Low (uint32)
- Bytes 46-49:  Open (float32)
- Bytes 50-53:  Close (float32)
- Bytes 54-57:  High (float32)
- Bytes 58-61:  Low (float32)

5-Level Depth (100 bytes, offset 62-161, INTERLEAVED):
Each level = 20 bytes with bid and ask fields interleaved:
- Bytes 0-3:   Bid Quantity (uint32)
- Bytes 4-7:   Ask Quantity (uint32)
- Bytes 8-9:   Bid Orders (uint16)
- Bytes 10-11: Ask Orders (uint16)
- Bytes 12-15: Bid Price (float32)
- Bytes 16-19: Ask Price (float32)

Note: This is the 5-level depth feed (code 8). The 20-level depth feed
(codes 41/51) uses a different structure (12-byte header, 16-byte levels).

Documented facts used here
--------------------------
- Responses are binary, little-endian
- Header is 8 bytes: code (1), message length uint16 (2), segment (1), security id uint32 (4)
- Ticker (code 2): float32 LTP, uint32 LTT epoch
- Prev close (code 6): float32 prev close, uint32 prev OI
- Quote (code 4), OI (code 5), Full (code 8), disconnect (code 50): offsets per docs
- Index (code 1): annexure-named; payload matches ticker (float32 LTP, int32 LTT) when >= 8 bytes
- Market status (code 7): named in annexure only — payload UNKNOWN

decoder_verified: Stays False until one real captured frame is verified against this layout
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from dhan_client.annexure import BYTE_TO_EXCHANGE_SEGMENT, FeedResponseCode
from dhan_client.errors import DecodeError
from dhan_client.logging_util import get_logger

log = get_logger(__name__)

HEADER_SIZE = 8
# decoder_verified: Set to True only after verifying against a real captured frame
DECODER_VERIFIED = False


@dataclass
class FeedHeader:
    response_code: int
    message_length: int
    exchange_segment_byte: int
    security_id: int

    @property
    def exchange_segment(self) -> str | None:
        seg = BYTE_TO_EXCHANGE_SEGMENT.get(self.exchange_segment_byte)
        return seg.value if seg is not None else None


@dataclass
class DecodedPacket:
    header: FeedHeader
    kind: str
    fields: dict[str, Any] = field(default_factory=dict)
    raw_payload: bytes = b""
    notes: tuple[str, ...] = ()
    decoder_verified: bool = False  # Flag for FULL packet verification


def _header(buf: bytes, offset: int) -> FeedHeader:
    if len(buf) - offset < HEADER_SIZE:
        raise DecodeError("short frame: need 8-byte header")
    code, length, segment, security_id = struct.unpack_from("<BhBi", buf, offset)
    return FeedHeader(
        response_code=code,
        message_length=length,
        exchange_segment_byte=segment,
        security_id=security_id,
    )


def _u16(buf: bytes, off: int) -> int:
    """Read unsigned 16-bit integer (little-endian)."""
    result: int = struct.unpack_from("<H", buf, off)[0]
    return result


def _u32(buf: bytes, off: int) -> int:
    """Read unsigned 32-bit integer (little-endian)."""
    result: int = struct.unpack_from("<I", buf, off)[0]
    return result


def _i16(buf: bytes, off: int) -> int:
    """Read signed 16-bit integer (little-endian)."""
    result: int = struct.unpack_from("<h", buf, off)[0]
    return result


def _i32(buf: bytes, off: int) -> int:
    """Read signed 32-bit integer (little-endian)."""
    result: int = struct.unpack_from("<i", buf, off)[0]
    return result


def _f32(buf: bytes, off: int) -> float:
    """Read 32-bit float (little-endian)."""
    result: float = struct.unpack_from("<f", buf, off)[0]
    return result


def _decode_full_packet(payload: bytes) -> dict[str, Any]:
    """Decode FULL packet (response code 8) with all fields and 5-level interleaved depth.

    Minimum payload size: 154 bytes (54 body + 100 depth)
    Total packet: 162 bytes (8 header + 154 payload)

    Layout per DhanHQ v2 docs and official SDK:
    - Body: '<fHIfIIIIIIffff' (54 bytes)
    - Depth: 5 levels × '<IIHHff' (20 bytes each, interleaved bid/ask)
    """
    min_size = 154  # 54 body + 100 depth
    if len(payload) < min_size:
        raise DecodeError(
            f"full payload too short: need {min_size} bytes, got {len(payload)}"
        )

    fields: dict[str, Any] = {}

    # Body fields (54 bytes, offsets 0-53 of payload)
    fields["ltp"] = _f32(payload, 0)  # Bytes 0-3
    fields["last_quantity"] = _u16(payload, 4)  # Bytes 4-5
    fields["last_trade_time_epoch"] = _u32(payload, 6)  # Bytes 6-9
    fields["atp"] = _f32(payload, 10)  # Bytes 10-13
    fields["volume"] = _u32(payload, 14)  # Bytes 14-17
    fields["total_sell_quantity"] = _u32(payload, 18)  # Bytes 18-21
    fields["total_buy_quantity"] = _u32(payload, 22)  # Bytes 22-25
    fields["oi"] = _u32(payload, 26)  # Bytes 26-29
    fields["oi_day_high"] = _u32(payload, 30)  # Bytes 30-33
    fields["oi_day_low"] = _u32(payload, 34)  # Bytes 34-37
    fields["day_open"] = _f32(payload, 38)  # Bytes 38-41
    fields["day_close"] = _f32(payload, 42)  # Bytes 42-45
    fields["day_high"] = _f32(payload, 46)  # Bytes 46-49
    fields["day_low"] = _f32(payload, 50)  # Bytes 50-53

    # 5-level interleaved depth (100 bytes, offset 54-153 of payload)
    # Each level: bid_qty(u32), ask_qty(u32), bid_orders(u16), ask_orders(u16), bid_price(f32), ask_price(f32)
    bid_depth = []
    ask_depth = []
    for i in range(5):
        offset = 54 + (i * 20)
        bid_qty = _u32(payload, offset)
        ask_qty = _u32(payload, offset + 4)
        bid_orders = _u16(payload, offset + 8)
        ask_orders = _u16(payload, offset + 10)
        bid_price = _f32(payload, offset + 12)
        ask_price = _f32(payload, offset + 16)

        bid_depth.append(
            {
                "price": bid_price,
                "quantity": bid_qty,
                "orders": bid_orders,
            }
        )
        ask_depth.append(
            {
                "price": ask_price,
                "quantity": ask_qty,
                "orders": ask_orders,
            }
        )

    fields["bid_depth"] = bid_depth
    fields["ask_depth"] = ask_depth

    return fields


def decode_packet(header: FeedHeader, payload: bytes) -> DecodedPacket:
    code = header.response_code
    notes: list[str] = []

    if code == FeedResponseCode.TICKER:
        if len(payload) < 8:
            raise DecodeError("ticker payload shorter than 8 bytes")
        return DecodedPacket(
            header=header,
            kind="ticker",
            fields={
                "ltp": _f32(payload, 0),
                "last_trade_time_epoch": _i32(payload, 4),
            },
            raw_payload=payload,
        )

    if code == FeedResponseCode.PREV_CLOSE:
        if len(payload) < 8:
            raise DecodeError("prev-close payload shorter than 8 bytes")
        return DecodedPacket(
            header=header,
            kind="prev_close",
            fields={
                "prev_close": _f32(payload, 0),
                "prev_oi": _i32(payload, 4),
            },
            raw_payload=payload,
        )

    if code == FeedResponseCode.OI:
        if len(payload) < 4:
            raise DecodeError("oi payload shorter than 4 bytes")
        return DecodedPacket(
            header=header,
            kind="oi",
            fields={"oi": _i32(payload, 0)},
            raw_payload=payload,
        )

    if code == FeedResponseCode.DISCONNECT:
        reason = _i16(payload, 0) if len(payload) >= 2 else None
        return DecodedPacket(
            header=header,
            kind="disconnect",
            fields={"disconnection_code": reason},
            raw_payload=payload,
            notes=("See annexure / live-market-feed disconnect codes.",),
        )

    if code == FeedResponseCode.QUOTE:
        notes.append(
            "Quote offsets are on the live-market-feed page; decoder is a placeholder."
        )
        fields: dict[str, Any] = {}
        if len(payload) >= 42:
            fields["ltp"] = _f32(payload, 0)
            fields["last_quantity"] = _i16(payload, 4)
            fields["last_trade_time_epoch"] = _i32(payload, 6)
            fields["atp"] = _f32(payload, 10)
            fields["volume"] = _i32(payload, 14)
            fields["total_sell_quantity"] = _i32(payload, 18)
            fields["total_buy_quantity"] = _i32(payload, 22)
            fields["day_open"] = _f32(payload, 26)
            fields["day_close"] = _f32(payload, 30)
            fields["day_high"] = _f32(payload, 34)
            fields["day_low"] = _f32(payload, 38)
        return DecodedPacket(
            header=header,
            kind="quote",
            fields=fields,
            raw_payload=payload,
            notes=tuple(notes),
        )

    if code == FeedResponseCode.FULL:
        try:
            fields = _decode_full_packet(payload)
            if not DECODER_VERIFIED:
                notes.append(
                    "FULL decoder not yet verified against a captured frame from founder's box. "
                    "Set DECODER_VERIFIED=True after verification."
                )
            return DecodedPacket(
                header=header,
                kind="full",
                fields=fields,
                raw_payload=payload,
                notes=tuple(notes),
                decoder_verified=DECODER_VERIFIED,
            )
        except (struct.error, IndexError) as e:
            raise DecodeError(f"failed to decode full packet: {e}") from e

    if code == FeedResponseCode.INDEX:
        if len(payload) < 4:
            raise DecodeError("index payload shorter than 4 bytes")
        # Same body as ticker (official SDK process_ticker: LTP f32 + LTT i32). IDX_I
        # subscribed with request 15/17 arrives as response 1, not FULL (8).
        fields = {"ltp": _f32(payload, 0)}
        if len(payload) >= 8:
            fields["last_trade_time_epoch"] = _i32(payload, 4)
        notes.append(
            "Index packet (response 1) is annexure-named; LTP+LTT match the ticker body. "
            "IDX_I has no FULL/depth ticks."
        )
        return DecodedPacket(
            header=header,
            kind="index",
            fields=fields,
            raw_payload=payload,
            notes=tuple(notes),
        )

    # Map known codes to string kinds
    kind_map: dict[int, str] = {
        FeedResponseCode.MARKET_STATUS: "market_status",
    }
    kind: str = kind_map.get(code, f"unknown_{code}")
    notes.append("Payload layout UNKNOWN / VERIFY FROM DOCS (annexure name only).")
    return DecodedPacket(
        header=header,
        kind=kind,
        fields={},
        raw_payload=payload,
        notes=tuple(notes),
    )


def decode_frame(buf: bytes) -> list[DecodedPacket]:
    """Decode one WebSocket binary frame into zero or more packets.

    Bad packets are logged and skipped; the function never raises on individual packet errors.
    """
    if not buf:
        return []
    packets: list[DecodedPacket] = []
    offset = 0
    while offset + HEADER_SIZE <= len(buf):
        try:
            header = _header(buf, offset)
            length = header.message_length
            if length >= HEADER_SIZE:
                packet_end = offset + length
            else:
                # VERIFY: treat documented "message length" as payload size if < 8
                packet_end = offset + HEADER_SIZE + max(length, 0)
                log.debug(
                    "feed message_length=%s < 8; using header+payload heuristic",
                    length,
                )
            if packet_end > len(buf) or packet_end <= offset + HEADER_SIZE:
                payload = buf[offset + HEADER_SIZE :]
                try:
                    packets.append(decode_packet(header, payload))
                except DecodeError as e:
                    log.error(f"Failed to decode packet at offset {offset}: {e}")
                break
            payload = buf[offset + HEADER_SIZE : packet_end]
            try:
                packets.append(decode_packet(header, payload))
            except DecodeError as e:
                log.error(f"Failed to decode packet at offset {offset}: {e}")
            offset = packet_end
        except DecodeError as e:
            log.error(f"Failed to parse header at offset {offset}: {e}")
            break
    return packets


def packet_as_dict(packet: DecodedPacket) -> dict[str, Any]:
    header = packet.header
    return {
        "kind": packet.kind,
        "response_code": header.response_code,
        "exchange_segment": header.exchange_segment,
        "exchange_segment_byte": header.exchange_segment_byte,
        "security_id": header.security_id,
        "fields": packet.fields,
        "notes": list(packet.notes),
        "payload_len": len(packet.raw_payload),
        "decoder_verified": packet.decoder_verified,
    }
