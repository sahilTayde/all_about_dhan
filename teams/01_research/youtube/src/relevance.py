"""Relevance tagging from title/description. Never deletes catalog rows."""

from __future__ import annotations

import re
from typing import Iterable

from .discovery import VideoRecord

# HIGH PRIORITY — PLAN.md §7 / ANALYSIS.md
_HIGH = [
    r"\boptions?\b",
    r"\bnifty\b",
    r"\bbanknifty\b",
    r"\bbank\s*nifty\b",
    r"\bsensex\b",
    r"\bindex\s+(?:option|derivative|future)",
    r"\boption\s+buying\b",
    r"\boption\s+selling\b",
    r"\boption\s+chain\b",
    r"\bstrike(?:\s+price|\s+selection)?\b",
    r"\bexpir(?:y|ies|ation)\b",
    r"\bgreeks?\b",
    r"\bdelta\b",
    r"\bgamma\b",
    r"\btheta\b",
    r"\bvega\b",
    r"\bimplied\s+volatilit",
    r"\bIV\b",
    r"\bopen\s+interest\b",
    r"\bOI\b",
    r"\bprice\s+action\b",
    r"\bcandlesticks?\b",
    r"\bintraday\b",
    r"\bscalp(?:ing)?\b",
    r"\bbreakout\b",
    r"\bbreakdown\b",
    r"\bmomentum\b",
    r"\bopening\s+(?:range|bell|strategy|market)?",
    r"\bmarket\s+open",
    r"\btrend\s+identification\b",
    r"\btrend[\s-]?following\b",
    r"\buptrend\b",
    r"\bdowntrend\b",
    r"\breversal\b",
    r"\bsupport(?:\s*/\s*|\s+and\s+)?resistance\b",
    r"\bvwap\b",
    r"\brsi\b",
    r"\bsuper\s*trend\b",
    r"\bmoving\s+averages?\b",
    r"\bEMA\b",
    r"\bSMA\b",
    r"\bmacd\b",
    r"\badx\b",
    r"\btrading\s+volume\b",
    r"\brelative\s+volume\b",
    r"\bvolume\s+profile\b",
    r"\bvolatilit",
    r"\brisk\s+management\b",
    r"\bstop\s*loss\b",
    r"\bprofit\s+target\b",
    r"\btarget\s+price\b",
    r"\bposition\s+siz",
    r"\bcustom\s+indicators?\b",
    r"\bdhan\s+indicators?\b",
    r"\bleading\s+indicators?\b",
    r"\blagging\s+indicators?\b",
    r"\bstrategy\s+builder\b",
    r"\bmarket\s+structure\b",
    r"\bf&o\b",
    r"\bfutures?\s+and\s+options\b",
    r"\bderivatives?\b",
    r"\bcall\s+options?\b",
    r"\bput\s+options?\b",
]

_MEDIUM = [
    r"\btechnical\s+analysis\b",
    r"\bchart(?:ing|s)?\b",
    r"\bindicators?\b",
    r"\boscillator\b",
    r"\bbollinger\b",
    r"\batr\b",
    r"\bstochastic\b",
    r"\bfibonacci\b",
    r"\bpivot\b",
    r"\bswing\b",
    r"\bpositional\b",
    r"\btrading\s+strateg",
    r"\bentry\b",
    r"\bexit\b",
]

_LOW = [
    r"\blong[\s-]?term\s+invest",
    r"\bvaluations?\b",
    r"\bmutual\s+funds?\b",
    r"\bsips?\b",
    r"\bportfolio\s+invest",
    r"\bstock\s+(?:pick|recommend|tip)",
    r"\bfundamental\s+analysis\b",
    r"\bipo\b",
    r"\binsurance\b",
    r"\bhow\s+to\s+open\s+(?:a\s+)?(?:dhan\s+)?(?:demat|account)",
    r"\bapp\s+tutorial\b",
    r"\breferral\b",
]

_EXCLUSIVE_STOCK = [
    r"\bstock[\s-]?specific\b",
    r"\bequity\s+research\b",
    r"\bfundamental\s+analysis\b",
    r"\blong[\s-]?term\s+invest",
    r"\bwhich\s+stock\b",
    r"\bbuy\s+this\s+stock\b",
    r"\bmultibagger\b",
    r"\bmutual\s+funds?\b",
    r"\bsips?\b",
]

_STOCK_MENTION = [
    r"\bstock[\s-]?picks?\b",
    r"\bwhich\s+stock\b",
    r"\bthis\s+stock\b",
    r"\bindividual\s+stocks?\b",
    r"\bequity\s+delivery\b",
    r"\bcash\s+market\s+stocks?\b",
    r"\bstock[\s-]?specific\b",
]

# Repeated channel CTAs that would otherwise tag every video HIGH / STOCK_ONLY.
_BOILERPLATE_MARKERS = (
    "download dhan app",
    "download options trader",
    "https://invite.dhan.co",
    "follow us on:",
    "made for trade community:",
    "create your custom scanner",
    "start investing & trading in stock market",
)

_TOPIC_MAP = [
    ("OPTIONS", [r"\boptions?\b", r"\bcall\s+options?\b", r"\bput\s+options?\b", r"\bf&o\b"]),
    ("OPTION_CHAIN", [r"\boption\s+chain\b", r"\boi\b", r"\bopen\s+interest\b"]),
    ("NIFTY", [r"\bnifty\b"]),
    ("BANKNIFTY", [r"\bbanknifty\b", r"\bbank\s*nifty\b"]),
    ("SENSEX", [r"\bsensex\b"]),
    ("PRICE_ACTION", [r"\bprice\s+action\b", r"\bmarket\s+structure\b", r"\bsupport\b", r"\bresistance\b"]),
    ("CANDLESTICKS", [r"\bcandlesticks?\b"]),
    ("RSI", [r"\brsi\b"]),
    ("SUPERTREND", [r"\bsuper\s*trend\b"]),
    ("MOVING_AVERAGES", [r"\bmoving\s+average", r"\bEMA\b", r"\bSMA\b"]),
    ("MACD", [r"\bmacd\b"]),
    ("VWAP", [r"\bvwap\b"]),
    ("VOLUME", [r"\bvolume\b"]),
    ("VOLATILITY", [r"\bvolatilit", r"\biv\b", r"\batr\b"]),
    ("GREEKS", [r"\bgreeks?\b", r"\bdelta\b", r"\btheta\b", r"\bgamma\b", r"\bvega\b"]),
    ("OPENING", [r"\bopening\b", r"\bmarket\s+open"]),
    ("SCALPING", [r"\bscalp"]),
    ("INTRADAY", [r"\bintraday\b"]),
    ("RISK_MANAGEMENT", [r"\brisk\b", r"\bstop\s*loss\b", r"\bposition\s+siz"]),
    ("STRATEGY_DESIGN", [r"\bstrategy\b", r"\bstrategy\s+builder\b"]),
]


def _compile(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


HIGH_RE = _compile(_HIGH)
MEDIUM_RE = _compile(_MEDIUM)
LOW_RE = _compile(_LOW)
EXCLUSIVE_STOCK_RE = _compile(_EXCLUSIVE_STOCK)
STOCK_MENTION_RE = _compile(_STOCK_MENTION)
TOPIC_RE = [(name, _compile(pats)) for name, pats in _TOPIC_MAP]


def unique_description(description: str) -> str:
    """Drop repeated Dhan app / social CTAs so they do not classify every video."""
    if not description:
        return ""
    lower = description.lower()
    cut = len(description)
    for marker in _BOILERPLATE_MARKERS:
        idx = lower.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return description[:cut].strip()


def _blob(video: VideoRecord) -> str:
    return f"{video.title}\n{unique_description(video.description)}"


def _any(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def _topic_tags(text: str) -> list[str]:
    tags: list[str] = []
    for name, patterns in TOPIC_RE:
        if _any(patterns, text):
            tags.append(name)
    return tags


def classify_video(video: VideoRecord) -> VideoRecord:
    text = _blob(video)
    high = _any(HIGH_RE, text)
    medium = _any(MEDIUM_RE, text)
    low = _any(LOW_RE, text)
    exclusive = _any(EXCLUSIVE_STOCK_RE, text)
    stock_mention = _any(STOCK_MENTION_RE, text)

    if exclusive and not high:
        video.relevance_band = "LOW"
        video.stock_tag = "EXCLUDED_STOCK_ONLY"
    elif high:
        video.relevance_band = "HIGH"
        video.stock_tag = "STOCK_ONLY" if stock_mention else None
    elif medium:
        video.relevance_band = "MEDIUM"
        video.stock_tag = "STOCK_ONLY" if stock_mention else None
    elif low:
        video.relevance_band = "LOW"
        video.stock_tag = "EXCLUDED_STOCK_ONLY" if exclusive or stock_mention else None
    else:
        video.relevance_band = "LOW"
        video.stock_tag = "STOCK_ONLY" if stock_mention else None

    video.topic_tags = _topic_tags(text)
    video.topic_source = "METADATA"
    return video


def apply_relevance(videos: list[VideoRecord]) -> list[VideoRecord]:
    for video in videos:
        classify_video(video)
    return videos
