"""QUOTE_SNAPSHOT: one compact bid/ask row per traded strike on every 5 s clock boundary."""

from __future__ import annotations

from typing import Any

from marketdata.depth import Book


def snapshot(
    iid: str, rule: str, side: str, book: Book | None, now_s: float, stale_after_s: float = 5.0
) -> dict[str, Any]:
    """``stale`` is true when no packet arrived for the instrument in the last ``stale_after_s``."""
    quote = book.quote if book else {}
    bid: float | None = quote.get("bid")
    ask: float | None = quote.get("ask")
    mid = spread = None
    if bid is not None and ask is not None:
        mid, spread = round((bid + ask) / 2, 4), round(ask - bid, 2)
    age_ms = int(round((now_s - book.data_s) * 1000)) if book else None
    return {
        "instrument_id": iid,
        "rule": rule,
        "side": side,
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "ltp": quote.get("ltp"),
        "ltt": book.ltt if book else None,
        "oi": quote.get("oi"),
        "depth_age_ms": age_ms,
        "stale": age_ms is None or age_ms > stale_after_s * 1000,
    }
