"""Buyer enters at ask, exits at bid. Measured V2 spread when the tape has no book."""

from __future__ import annotations

from exitlab.clock import ReplayClock
from exitlab.tapes import spread_pts_for
from exitlab.types import Bar, Quote

# Fallback if V2 measure has not been loaded. Overridden by measured table.
DEFAULT_SPREAD_PTS = {"ATM": 0.20, "ITM100": 0.35, "ITM200": 0.55, "ITM": 0.35}
DEFAULT_MIN_SPREAD = 0.05
# Extra fractional slip on top of the measured book/half-spread. Off unless a stress sets it.
DEFAULT_SLIP_FRAC = 0.0


class SlippageModel:
    """Named, stated fill model. Never silent."""

    def __init__(
        self,
        name: str = "ask_in_bid_out",
        slip_frac: float = DEFAULT_SLIP_FRAC,
        min_spread: float = DEFAULT_MIN_SPREAD,
        spread_mult: float = 1.0,
        slip_mult: float = 1.0,
        spread_table: dict[str, float] | None = None,
        moneyness: str = "ATM",
    ) -> None:
        self.name = name
        self.slip_frac = float(slip_frac) * float(slip_mult)
        self.min_spread = float(min_spread)
        self.spread_mult = float(spread_mult)
        self.spread_table = dict(spread_table or DEFAULT_SPREAD_PTS)
        self.moneyness = moneyness

    def entry_px(self, quote: Quote | None, bar: Bar | None, clock: ReplayClock) -> float:
        px = self._book_px(quote, clock, want="ask")
        if px is not None:
            return px
        mid = self._mid(quote, bar, clock)
        return _tick(mid + self._half_spread(quote, mid))

    def exit_px(self, quote: Quote | None, bar: Bar | None, clock: ReplayClock) -> float:
        px = self._book_px(quote, clock, want="bid")
        if px is not None:
            return max(self.min_spread, px)
        mid = self._mid(quote, bar, clock)
        return _tick(max(self.min_spread, mid - self._half_spread(quote, mid)))

    def _half_spread(self, quote: Quote | None, mid: float) -> float:
        if quote is not None and quote.spread is not None and quote.spread > 0:
            half = (float(quote.spread) * self.spread_mult) / 2.0
        else:
            half = (spread_pts_for(self.moneyness, self.spread_table) * self.spread_mult) / 2.0
        extra = abs(mid) * self.slip_frac
        return half + extra

    def _book_px(self, quote: Quote | None, clock: ReplayClock, *, want: str) -> float | None:
        if quote is None:
            return None
        clock.visible(quote.available_ts, label="quote")
        raw = quote.ask if want == "ask" else quote.bid
        if raw is None or raw <= 0:
            return None
        if quote.spread is not None and self.spread_mult != 1.0:
            mid = ((quote.bid or raw) + (quote.ask or raw)) / 2.0
            half = (quote.spread * self.spread_mult) / 2.0
            raw = mid + half if want == "ask" else mid - half
        return _tick(float(raw))

    def _mid(self, quote: Quote | None, bar: Bar | None, clock: ReplayClock) -> float:
        if quote is not None:
            clock.visible(quote.available_ts, label="quote")
            if quote.ltp is not None and quote.ltp > 0:
                return float(quote.ltp)
            if quote.bid and quote.ask:
                return (float(quote.bid) + float(quote.ask)) / 2.0
            if quote.bid and quote.bid > 0:
                return float(quote.bid)
            if quote.ask and quote.ask > 0:
                return float(quote.ask)
        if bar is not None:
            clock.visible(bar.available_ts, label="bar")
            return float(bar.close)
        raise ValueError("no quote or bar for fill")


def _tick(px: float) -> float:
    return round(round(px / 0.05) * 0.05, 2)


def mark_long(quote: Quote | None, bar: Bar | None, clock: ReplayClock) -> float | None:
    """Mark-to-market for a long: bid, else LTP, else bar close. Never future."""
    if quote is not None:
        clock.visible(quote.available_ts, label="mark")
        if quote.bid is not None and quote.bid > 0:
            return float(quote.bid)
        if quote.ltp is not None and quote.ltp > 0:
            return float(quote.ltp)
    if bar is not None:
        clock.visible(bar.available_ts, label="bar")
        return float(bar.close)
    return None
