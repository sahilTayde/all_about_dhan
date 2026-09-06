"""Documented annexure enums (https://dhanhq.co/docs/v2/annexure/)."""

from __future__ import annotations

from enum import IntEnum, Enum


class ExchangeSegment(str, Enum):
    IDX_I = "IDX_I"
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    NSE_CURRENCY = "NSE_CURRENCY"
    BSE_EQ = "BSE_EQ"
    MCX_COMM = "MCX_COMM"
    BSE_CURRENCY = "BSE_CURRENCY"
    BSE_FNO = "BSE_FNO"


# Byte values as sent in the binary feed header (annexure "enum" column).
EXCHANGE_SEGMENT_BYTE = {
    ExchangeSegment.IDX_I: 0,
    ExchangeSegment.NSE_EQ: 1,
    ExchangeSegment.NSE_FNO: 2,
    ExchangeSegment.NSE_CURRENCY: 3,
    ExchangeSegment.BSE_EQ: 4,
    ExchangeSegment.MCX_COMM: 5,
    # annexure has no enum 6
    ExchangeSegment.BSE_CURRENCY: 7,
    ExchangeSegment.BSE_FNO: 8,
}

BYTE_TO_EXCHANGE_SEGMENT = {v: k for k, v in EXCHANGE_SEGMENT_BYTE.items()}


class InstrumentType(str, Enum):
    INDEX = "INDEX"
    FUTIDX = "FUTIDX"
    OPTIDX = "OPTIDX"
    EQUITY = "EQUITY"
    FUTSTK = "FUTSTK"
    OPTSTK = "OPTSTK"
    FUTCOM = "FUTCOM"
    OPTFUT = "OPTFUT"
    FUTCUR = "FUTCUR"
    OPTCUR = "OPTCUR"


class ExpiryCode(IntEnum):
    CURRENT = 0
    NEXT = 1
    FAR = 2


class FeedRequestCode(IntEnum):
    CONNECT = 11  # VERIFY: v2 "Establishing Connection" uses the wss URL, not this JSON
    DISCONNECT = 12
    SUBSCRIBE_TICKER = 15
    UNSUBSCRIBE_TICKER = 16
    SUBSCRIBE_QUOTE = 17
    UNSUBSCRIBE_QUOTE = 18
    SUBSCRIBE_FULL = 21
    UNSUBSCRIBE_FULL = 22
    SUBSCRIBE_FULL_DEPTH = 23
    UNSUBSCRIBE_FULL_DEPTH = 24


class FeedResponseCode(IntEnum):
    INDEX = 1  # payload layout UNKNOWN — not on live-market-feed page
    TICKER = 2
    QUOTE = 4
    OI = 5
    PREV_CLOSE = 6
    MARKET_STATUS = 7  # payload layout UNKNOWN — not on live-market-feed page
    FULL = 8
    DISCONNECT = 50
