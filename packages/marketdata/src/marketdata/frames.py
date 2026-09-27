"""Wrap the V2-D1 decoder so every bad packet is reported, not only logged.

``dhan_client.decode.decode_frame`` logs and skips bad packets. The recorder must write
each one to ``ingest_errors`` (REG-06), so this walks a frame with the same framing rule
and calls the same ``decode_packet`` per packet. Decoding itself is not changed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from dhan_client.decode import HEADER_SIZE, DecodedPacket, _header, decode_packet
from dhan_client.errors import DecodeError


@dataclass(frozen=True)
class Packet:
    decoded: DecodedPacket
    raw: bytes  # header + payload, exactly as received
    finite: bool = True  # False if a float field is NaN/inf (written as null)


@dataclass(frozen=True)
class FrameError:
    reason: str
    offset: int
    raw: bytes


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return True


def _decode_one(buf: bytes, offset: int, end: int) -> Packet | FrameError:
    raw = buf[offset:end]
    try:
        packet = decode_packet(_header(buf, offset), buf[offset + HEADER_SIZE : end])
    except DecodeError as exc:
        return FrameError(f"decode error: {exc}", offset, raw)
    if packet.kind.startswith("unknown_"):
        return FrameError(f"unknown response code {packet.header.response_code}", offset, raw)
    return Packet(packet, raw, finite=_finite(packet.fields))


def decode_frame_checked(buf: bytes) -> tuple[list[Packet], list[FrameError]]:
    """Same framing as ``decode_frame``; returns good packets and every failure."""
    packets: list[Packet] = []
    errors: list[FrameError] = []
    if not buf:
        return packets, [FrameError("empty binary frame", 0, b"")]
    offset = 0
    while offset + HEADER_SIZE <= len(buf):
        length = _header(buf, offset).message_length
        end = offset + length if length >= HEADER_SIZE else offset + HEADER_SIZE + length
        last = end > len(buf) or end <= offset + HEADER_SIZE
        item = _decode_one(buf, offset, len(buf) if last else end)
        if isinstance(item, Packet):
            packets.append(item)
        else:
            errors.append(item)
        if last:
            return packets, errors
        offset = end
    if offset < len(buf):
        errors.append(FrameError(f"{len(buf) - offset} trailing bytes", offset, buf[offset:]))
    return packets, errors
