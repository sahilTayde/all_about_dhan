"""Shared types. Request bodies match official docs; extra fields are not invented."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, MutableMapping, Sequence, TypedDict, Union

JsonDict = MutableMapping[str, Any]
JsonMapping = Mapping[str, Any]
SecurityId = Union[int, str]


class FeedMode(str, Enum):
    """Subscribe RequestCode from annexure (https://dhanhq.co/docs/v2/annexure/)."""

    TICKER = "ticker"  # 15
    QUOTE = "quote"  # 17
    FULL = "full"  # 21


@dataclass(frozen=True)
class FeedInstrument:
    """One row of InstrumentList on the live-market-feed subscribe message."""

    exchange_segment: str
    security_id: str


class HistoricalDailyBody(TypedDict, total=False):
    securityId: str
    exchangeSegment: str
    instrument: str
    expiryCode: int
    oi: bool
    fromDate: str
    toDate: str


class HistoricalIntradayBody(TypedDict, total=False):
    securityId: str
    exchangeSegment: str
    instrument: str
    interval: Union[int, str]
    oi: bool
    fromDate: str
    toDate: str


class OptionChainBody(TypedDict, total=False):
    UnderlyingScrip: int
    UnderlyingSeg: str
    Expiry: str


class OptionExpiryListBody(TypedDict, total=False):
    UnderlyingScrip: int
    UnderlyingSeg: str


class RollingOptionBody(TypedDict, total=False):
    exchangeSegment: str
    interval: Union[int, str]
    securityId: Union[int, str]
    instrument: str
    expiryFlag: str
    expiryCode: int
    strike: str
    drvOptionType: str
    requiredData: list[str]
    fromDate: str
    toDate: str


QuoteBody = Mapping[str, Sequence[SecurityId]]
