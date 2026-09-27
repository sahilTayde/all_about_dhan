"""DEPTH_QUOTE: emitted on change (at most one per 250 ms per instrument) and repeated as a
heartbeat (``repeat: true``) so every instrument has a row at least once per second.

``exchange_ts`` is the receive time of the packet the data came from, so a heartbeat keeps
the old time and the data age stays visible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

Quote = dict[str, Any]


def _px(value: Any) -> float | None:
    """Price rounded to 2 dp (drops float32 noise); zero, NaN or inf means no price."""
    return round(float(value), 2) if value and math.isfinite(value) else None


def quote_from_full(fields: dict[str, Any]) -> Quote:
    """Top of book and 5 levels from a decoded FULL packet; zero price or qty means no quote."""
    levels: dict[str, list[list[float | int]]] = {}
    for side in ("bid", "ask"):
        levels[side] = [
            [px, int(lv["quantity"])]
            for lv in fields.get(f"{side}_depth", [])
            if (px := _px(lv.get("price"))) is not None and lv.get("quantity")
        ]
    bid = levels["bid"][0] if levels["bid"] else None
    ask = levels["ask"][0] if levels["ask"] else None
    return {
        "bid": bid[0] if bid else None,
        "bid_qty": int(bid[1]) if bid else None,
        "ask": ask[0] if ask else None,
        "ask_qty": int(ask[1]) if ask else None,
        "ltp": _px(fields.get("ltp")),
        "oi": int(fields["oi"]) if fields.get("oi") is not None else None,
        "levels": levels,
    }


def quote_from_ltp(ltp: float) -> Quote:
    return {
        "bid": None,
        "bid_qty": None,
        "ask": None,
        "ask_qty": None,
        "ltp": _px(ltp),
        "oi": None,
        "levels": {"bid": [], "ask": []},
    }


@dataclass
class Book:
    quote: Quote
    exchange_ts: str
    data_s: float
    raw_b64: str | None
    ltt: str | None
    emitted_s: float = float("-inf")
    pending: bool = False


class DepthTracker:
    def __init__(self, throttle_s: float = 0.25, heartbeat_s: float = 0.9) -> None:
        self.throttle_s = throttle_s
        self.heartbeat_s = heartbeat_s
        self.books: dict[str, Book] = {}

    def _emit(self, iid: str, book: Book, now_s: float, repeat: bool) -> dict[str, Any]:
        book.emitted_s = now_s
        book.pending = False
        return {
            "instrument_id": iid,
            **book.quote,
            "exchange_ts": book.exchange_ts,
            "repeat": repeat,
            "raw_b64": None if repeat else book.raw_b64,
        }

    def update(
        self,
        iid: str,
        quote: Quote,
        now_s: float,
        exchange_ts: str,
        raw_b64: str | None = None,
        ltt: str | None = None,
    ) -> dict[str, Any] | None:
        """Record a packet; return a DEPTH_QUOTE payload if it must be written now."""
        book = self.books.get(iid)
        if book is None:
            book = self.books[iid] = Book(quote, exchange_ts, now_s, raw_b64, ltt)
            return self._emit(iid, book, now_s, repeat=False)
        changed = quote != book.quote
        book.quote, book.exchange_ts, book.data_s = quote, exchange_ts, now_s
        book.raw_b64, book.ltt = raw_b64, ltt or book.ltt
        if not changed:
            return None
        if now_s - book.emitted_s >= self.throttle_s:
            return self._emit(iid, book, now_s, repeat=False)
        book.pending = True
        return None

    def tick(self, now_s: float, heartbeat: bool = True) -> list[dict[str, Any]]:
        """Throttled changes that are now due, then heartbeats for quiet instruments."""
        out: list[dict[str, Any]] = []
        for iid, book in self.books.items():
            if book.pending and now_s - book.emitted_s >= self.throttle_s:
                out.append(self._emit(iid, book, now_s, repeat=False))
            elif heartbeat and now_s - book.emitted_s >= self.heartbeat_s:
                out.append(self._emit(iid, book, now_s, repeat=True))
        return out

    def age_s(self, iid: str, now_s: float) -> float | None:
        book = self.books.get(iid)
        return None if book is None else now_s - book.data_s

    def drop(self, iid: str) -> None:
        self.books.pop(iid, None)
