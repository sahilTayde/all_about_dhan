"""Binary decoder for Dhan Live Market Feed.

https://dhanhq.co/docs/v2/live-market-feed/

FULL Packet Binary Layout (Response Code 8)
--------------------------------------------
Based on DhanHQ API v2 Live Market Feed documentation:
https://dhanhq.co/docs/v2/live-market-feed/ (accessed 2026-09-27)

Header: 8 bytes (same for all packets)
- Byte 0: Response code (uint8) = 8 for FULL
- Bytes 1-2: Message length (int16, little-endian)
- Byte 3: Exchange segment (uint8)
- Bytes 4-7: Security ID (int32, little-endian)

Payload (bytes 8+, field numbers from docs are 1-based from byte 9):
Main fields:
- Bytes 8-11 (field 1-4): LTP (float32)
- Bytes 12-13 (field 5-6): Last Trade Quantity - LTQ (int16)
- Bytes 14-17 (field 7-10): Last Trade Time - LTT (int32, epoch seconds)
- Bytes 18-21 (field 11-14): Average Trade Price - ATP (float32)
- Bytes 22-25 (field 15-18): Volume (int32)
- Bytes 26-29 (field 19-22): Total Sell Quantity (int32)
- Bytes 30-33 (field 23-26): Total Buy Quantity (int32)
- Bytes 34-37 (field 27-30): Open Interest - OI (int32)
- Bytes 38-41 (field 31-34): Open (float32)
- Bytes 42-45 (field 35-38): Close (float32)
- Bytes 46-49 (field 39-42): High (float32)
- Bytes 50-53 (field 43-46): Low (float32)

5-Level Depth (10 levels total: 5 bid + 5 ask):
Each level is 20 bytes (4-byte float32 price + 4-byte int32 qty repeated)

Bid side (bytes 54-153, 100 bytes = 5 levels × 20 bytes):
- Level 1: Bytes 54-57 bid_price, Bytes 58-61 bid_qty, Bytes 62-65 orders, Bytes 66-69 bid_orders (4×4=16), pad 4
- (Pattern repeats for levels 2-5)

Ask side (bytes 154-253, 100 bytes = 5 levels × 20 bytes):
- Level 1: Bytes 154-157 ask_price, Bytes 158-161 ask_qty, Bytes 162-165 orders, Bytes 166-169 ask_orders (4×4=16), pad 4
- (Pattern repeats for levels 2-5)

Note: The exact depth layout uses 20 bytes per level as documented. Each level contains:
- price (float32, 4 bytes)
- quantity (int32, 4 bytes)
- orders (int32, 4 bytes)
- bid_orders or ask_orders (int32, 4 bytes)
- padding (4 bytes)

Total minimum payload size for FULL packet: 246 bytes (46 base + 200 depth)

Ambiguities Flagged (VERIFY):
- The documentation shows depth structure but exact byte-level field order within each
  20-byte level may need verification against a captured frame.
- Whether "orders" and "bid_orders"/"ask_orders" are separate fields or the same field
  needs verification.

Documented facts used here
--------------------------
- Responses are binary, little-endian.
- Header is 8 bytes: code (1), message length int16 (2), segment (1), security id int32 (4).
- Docs number payload fields from byte 9 (1-based). We treat the header as bytes 0–7.
- Ticker (code 2): float32 LTP, int32 LTT epoch.
- Prev close (code 6): float32 prev close, int32 prev OI.
- Quote (code 4), OI (code 5), Full (code 8), disconnect (code 50): offsets on that page.
- Index (code 1) and market status (code 7): named in annexure only — payload UNKNOWN.

VERIFY
------
- Is ``message length`` the full packet or payload-after-header?
- Can one WebSocket frame contain several packets? Not stated; we try to slice
  by length when length >= 8, else treat the remainder as one payload.
- decoder_verified flag: stays False until one frame captured on founder's box is checked.
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
class DepthLevel:
    """One level of market depth (bid or ask)."""

    price: float
    quantity: int
    orders: int
    bid_orders: int  # For bid side; ask_orders for ask side


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


def _i16(buf: bytes, off: int) -> int:
    result: int = struct.unpack_from("<h", buf, off)[0]
    return result


def _i32(buf: bytes, off: int) -> int:
    result: int = struct.unpack_from("<i", buf, off)[0]
    return result


def _f32(buf: bytes, off: int) -> float:
    result: float = struct.unpack_from("<f", buf, off)[0]
    return result


def _decode_full_packet(payload: bytes) -> dict[str, Any]:
    """Decode FULL packet (response code 8) with all fields and 5-level depth.

    Minimum payload size: 246 bytes (46 base fields + 200 depth bytes)
    """
    min_size = 246  # 46 base + 100 bid depth + 100 ask depth
    if len(payload) < min_size:
        raise DecodeError(f"full payload too short: need {min_size} bytes, got {len(payload)}")

    fields: dict[str, Any] = {}

    # Main fields (bytes 0-53 of payload, which is bytes 8-61 absolute)
    fields["ltp"] = _f32(payload, 0)  # Bytes 8-11 absolute
    fields["last_quantity"] = _i16(payload, 4)  # Bytes 12-13 absolute
    fields["last_trade_time_epoch"] = _i32(payload, 6)  # Bytes 14-17 absolute
    fields["atp"] = _f32(payload, 10)  # Bytes 18-21 absolute
    fields["volume"] = _i32(payload, 14)  # Bytes 22-25 absolute
    fields["total_sell_quantity"] = _i32(payload, 18)  # Bytes 26-29 absolute
    fields["total_buy_quantity"] = _i32(payload, 22)  # Bytes 30-33 absolute
    fields["oi"] = _i32(payload, 26)  # Bytes 34-37 absolute (OI field)
    fields["day_open"] = _f32(payload, 30)  # Bytes 38-41 absolute
    fields["day_close"] = _f32(payload, 34)  # Bytes 42-45 absolute
    fields["day_high"] = _f32(payload, 38)  # Bytes 46-49 absolute
    fields["day_low"] = _f32(payload, 42)  # Bytes 50-53 absolute

    # 5-level bid depth (bytes 46-145 of payload, 20 bytes per level)
    bid_depth = []
    for i in range(5):
        offset = 46 + (i * 20)
        level = DepthLevel(
            price=_f32(payload, offset),
            quantity=_i32(payload, offset + 4),
            orders=_i32(payload, offset + 8),
            bid_orders=_i32(payload, offset + 12),
        )
        bid_depth.append(
            {
                "price": level.price,
                "quantity": level.quantity,
                "orders": level.orders,
                "bid_orders": level.bid_orders,
            }
        )

    # 5-level ask depth (bytes 146-245 of payload, 20 bytes per level)
    ask_depth = []
    for i in range(5):
        offset = 146 + (i * 20)
        level = DepthLevel(
            price=_f32(payload, offset),
            quantity=_i32(payload, offset + 4),
            orders=_i32(payload, offset + 8),
            bid_orders=_i32(payload, offset + 12),  # ask_orders in documentation
        )
        ask_depth.append(
            {
                "price": level.price,
                "quantity": level.quantity,
                "orders": level.orders,
                "ask_orders": level.bid_orders,  # Rename for clarity
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
            header=header, kind="quote", fields=fields, raw_payload=payload, notes=tuple(notes)
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
        fields = {}
        notes.append(
            "Index packet layout is annexure-named only on the feed page. "
            "First float32 as LTP is VERIFY, not a documented field table."
        )
        if len(payload) >= 4:
            fields["ltp"] = _f32(payload, 0)
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
    """Decode one WebSocket binary frame into zero or more packets."""
    if not buf:
        return []
    packets: list[DecodedPacket] = []
    offset = 0
    while offset + HEADER_SIZE <= len(buf):
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
            packets.append(decode_packet(header, payload))
            break
        payload = buf[offset + HEADER_SIZE : packet_end]
        packets.append(decode_packet(header, payload))
        offset = packet_end
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
