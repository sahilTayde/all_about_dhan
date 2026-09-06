"""Placeholder binary decoder for Live Market Feed.

https://dhanhq.co/docs/v2/live-market-feed/

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
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

from dhan_client.annexure import BYTE_TO_EXCHANGE_SEGMENT, FeedResponseCode
from dhan_client.errors import DecodeError
from dhan_client.logging_util import get_logger

log = get_logger(__name__)

HEADER_SIZE = 8


@dataclass
class FeedHeader:
    response_code: int
    message_length: int
    exchange_segment_byte: int
    security_id: int

    @property
    def exchange_segment(self) -> Optional[str]:
        seg = BYTE_TO_EXCHANGE_SEGMENT.get(self.exchange_segment_byte)
        return seg.value if seg is not None else None


@dataclass
class DecodedPacket:
    header: FeedHeader
    kind: str
    fields: dict[str, Any] = field(default_factory=dict)
    raw_payload: bytes = b""
    notes: tuple[str, ...] = ()


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
    return struct.unpack_from("<h", buf, off)[0]


def _i32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<i", buf, off)[0]


def _f32(buf: bytes, off: int) -> float:
    return struct.unpack_from("<f", buf, off)[0]


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
        notes.append(
            "Full packet + 5x20-byte depth: placeholder. Offsets on live-market-feed."
        )
        fields = {}
        if len(payload) >= 4:
            fields["ltp"] = _f32(payload, 0)
        return DecodedPacket(
            header=header, kind="full", fields=fields, raw_payload=payload, notes=tuple(notes)
        )

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

    kind = {
        FeedResponseCode.MARKET_STATUS: "market_status",
    }.get(code, f"unknown_{code}")
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
    }
