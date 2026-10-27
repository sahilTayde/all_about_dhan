"""Dhan 20-level market depth (separate websocket; included in the Dhan data plan). Parser only.

Binary layout per Dhan "Full Market Depth" (20 level) docs, little-endian:
  header 12 bytes: int16 message length, uint8 feed response code (41 = bid side, 51 = ask side),
                   uint8 exchange segment, int32 security id, uint32 message sequence (ignored)
  then 20 packets of 16 bytes: float64 price, uint32 quantity, uint32 number of orders.
Bid and ask arrive as separate messages; one frame may hold several messages back to back.
Not wired to the live recorder yet (RecorderConfig.depth20 = False): verify against one recorded live
frame first. Box tests use synthetic fixtures only; no broker call from the box.
"""

from __future__ import annotations

import struct
from typing import Any

HEADER = struct.Struct("<hBBiI")
LEVEL = struct.Struct("<dII")
LEVELS = 20
BID_CODE, ASK_CODE = 41, 51
MESSAGE_LEN = HEADER.size + LEVELS * LEVEL.size  # 332


def parse_frame(buf: bytes) -> list[dict[str, Any]]:
    """Decode every 20-depth message in a frame. Zero price/qty levels are dropped (empty book side)."""
    out: list[dict[str, Any]] = []
    pos = 0
    while pos + HEADER.size <= len(buf):
        length, code, segment, security_id, _seq = HEADER.unpack_from(buf, pos)
        size = length if length >= MESSAGE_LEN else MESSAGE_LEN
        if code not in (BID_CODE, ASK_CODE) or pos + MESSAGE_LEN > len(buf):
            break
        levels = []
        for i in range(LEVELS):
            px, qty, orders = LEVEL.unpack_from(buf, pos + HEADER.size + i * LEVEL.size)
            if px > 0 and qty > 0:
                levels.append([round(px, 2), int(qty), int(orders)])
        out.append({"side": "bid" if code == BID_CODE else "ask", "segment": segment,
                    "security_id": str(security_id), "levels": levels})
        pos += size
    return out


def merge_sides(messages: list[dict[str, Any]]) -> dict[str, dict[str, list]]:
    """security_id -> {"bid": [[px, qty, orders] x<=20], "ask": [...]} (last message per side wins)."""
    book: dict[str, dict[str, list]] = {}
    for m in messages:
        book.setdefault(m["security_id"], {"bid": [], "ask": []})[m["side"]] = m["levels"]
    return book


def pack_message(code: int, segment: int, security_id: int, levels: list[tuple[float, int, int]]) -> bytes:
    """Test/fixture helper: build one message in the documented layout."""
    body = b"".join(LEVEL.pack(*(levels[i] if i < len(levels) else (0.0, 0, 0))) for i in range(LEVELS))
    return HEADER.pack(MESSAGE_LEN, code, segment, security_id, 0) + body
