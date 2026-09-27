"""Entry-location features from closed 1m bars only (V2-05b, REG-01).

Diagnostics only (research round 10: no entry-location rule). A snapshot at
time t uses only bars with available_ts <= t. An FVG whose third bar is still
open is never reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts.payloads import BarClosed, EntryLocation

from indicators.core import ATR, EMA
from indicators.view import FeatureValue

MAX_AGE_BARS = 60
FILL_RULE = "full"
POC_BIN = 1.0
STRETCH_ZONES = frozenset({"fvg", "candle_50"})
LOCATION_FIELDS = (
    "loc_signal_candle_atr",
    "loc_signal_body_atr",
    "loc_entry_distance_atr",
    "loc_atr",
    "loc_spot",
    "loc_candle_50",
    "loc_ema20",
    "loc_twap",
    "loc_vwap",
    "loc_poc",
    "loc_fvg",
)


@dataclass(frozen=True)
class FairValueGap:
    """Unfilled (or partly filled) 3-bar FVG."""

    kind: str  # "bullish" | "bearish"
    low: float
    high: float
    formed_index: int
    filled: str  # "none" | "partial"


@dataclass(frozen=True)
class _StampedBar:
    bar: BarClosed
    available_ts: datetime


def underlying_id(instrument_id: str) -> str:
    """Symbol from an instrument id (`NIFTY` or `NSE_IDX:NIFTY` → `NIFTY`)."""
    parts = instrument_id.split(":")
    return parts[1] if len(parts) >= 2 else instrument_id


def is_index_future(instrument_id: str) -> bool:
    """True for an index future (`NSE_FNO:NIFTY:YYYY-MM-DD`), not options."""
    parts = instrument_id.split(":")
    return len(parts) == 3 and "FNO" in parts[0]


def signed_distance_atr(spot: float, zone: float, atr: float, side: str) -> float:
    """(spot - zone) / ATR; PE flips so + means stretched away from pullback."""
    raw = (spot - zone) / atr
    return -raw if side == "PE" else raw


def candle_50(bar: BarClosed) -> float | None:
    """Signal-candle midpoint (high + low) / 2."""
    if bar.h is None or bar.l is None:
        return None
    return (bar.h + bar.l) / 2.0


def detect_fvgs(
    bars: list[BarClosed],
    *,
    max_age_bars: int = MAX_AGE_BARS,
    fill_rule: str = FILL_RULE,
) -> list[FairValueGap]:
    """3-bar FVGs still live under `fill_rule=full` and `max_age_bars`."""
    del fill_rule  # only `full` is supported; partial fill does not retire the gap
    found: list[tuple[str, float, float, int]] = []
    for i in range(2, len(bars)):
        first, third = bars[i - 2], bars[i]
        if first.h is None or first.l is None or third.h is None or third.l is None:
            continue
        if first.h < third.l:
            found.append(("bullish", first.h, third.l, i))
        elif first.l > third.h:
            found.append(("bearish", third.h, first.l, i))

    live: list[FairValueGap] = []
    n = len(bars)
    for kind, low, high, formed in found:
        if (n - 1 - formed) >= max_age_bars:
            continue
        filled = "none"
        retired = False
        for later in bars[formed + 1 :]:
            if later.h is None or later.l is None:
                continue
            if kind == "bullish":
                if later.l <= low:
                    retired = True
                    break
                if later.l < high:
                    filled = "partial"
            elif later.h >= high:
                retired = True
                break
            elif later.h > low:
                filled = "partial"
        if not retired:
            live.append(FairValueGap(kind, low, high, formed, filled))
    return live


def _typical(bar: BarClosed) -> float | None:
    if bar.h is not None and bar.l is not None and bar.c is not None:
        return (bar.h + bar.l + bar.c) / 3.0
    return bar.c


def _twap(bars: list[BarClosed]) -> float | None:
    prices = [_typical(b) for b in bars]
    known = [p for p in prices if p is not None]
    return sum(known) / len(known) if known else None


def _futures_vwap(bars: list[BarClosed]) -> float | None:
    num = 0.0
    den = 0.0
    for bar in bars:
        px = _typical(bar)
        if px is None or bar.v is None or bar.v <= 0:
            continue
        num += px * float(bar.v)
        den += float(bar.v)
    return num / den if den > 0.0 else None


def _volume_poc(bars: list[BarClosed], bin_size: float = POC_BIN) -> float | None:
    """Close-binned volume POC; absent when no futures volume."""
    buckets: dict[float, float] = {}
    for bar in bars:
        if bar.c is None or bar.v is None or bar.v <= 0:
            continue
        key = round(bar.c / bin_size) * bin_size
        buckets[key] = buckets.get(key, 0.0) + float(bar.v)
    if not buckets:
        return None
    return max(buckets.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def _nearest_edge(spot: float, low: float, high: float) -> float:
    if spot >= high:
        return high
    if spot <= low:
        return low
    return low if (spot - low) <= (high - spot) else high


def _zone(
    zone: str, price: float, spot: float, atr: float, source: str, side: str
) -> dict[str, float | str]:
    return {
        "zone": zone,
        "price": price,
        "distance_atr": signed_distance_atr(spot, price, atr, side),
        "source": source,
    }


def compute_entry_location(
    spot_bars: list[BarClosed],
    *,
    side: str,
    fut_bars: list[BarClosed] | None = None,
    max_age_bars: int = MAX_AGE_BARS,
    poc_bin: float = POC_BIN,
) -> EntryLocation | None:
    """Build EntryLocation from closed bars. `side` is CE or PE."""
    parts = _compute(
        spot_bars, side=side, fut_bars=fut_bars, max_age_bars=max_age_bars, poc_bin=poc_bin
    )
    return None if parts is None else parts[0]


def _compute(
    spot_bars: list[BarClosed],
    *,
    side: str,
    fut_bars: list[BarClosed] | None = None,
    max_age_bars: int = MAX_AGE_BARS,
    poc_bin: float = POC_BIN,
) -> tuple[EntryLocation, dict[str, float]] | None:
    """Build EntryLocation plus raw zone prices from closed bars."""
    series = spot_bars if spot_bars else list(fut_bars or [])
    if not series:
        return None
    signal = series[-1]
    if signal.o is None or signal.h is None or signal.l is None or signal.c is None:
        return None

    atr = ATR(period=14)
    ema = EMA(period=20)
    atr_val: float | None = None
    ema_val: float | None = None
    for bar in series:
        if bar.c is not None:
            ema_val = ema.update(bar.c)
        if bar.h is not None and bar.l is not None and bar.c is not None:
            atr_val = atr.update(bar.h, bar.l, bar.c)
    if atr_val is None or atr_val <= 0.0 or ema_val is None:
        return None

    spot = signal.c
    twap = _twap(series)
    fut = list(fut_bars or [])
    fut_vwap = _futures_vwap(fut)
    poc = _volume_poc(fut, poc_bin)
    if fut_vwap is not None and spot_bars and fut and fut[-1].c is not None:
        fut_vwap = fut_vwap - (fut[-1].c - spot)

    prices: dict[str, float] = {"ema20": ema_val}
    mid = candle_50(signal)
    zones: list[dict[str, float | str]] = []
    if mid is not None:
        prices["candle_50"] = mid
        zones.append(_zone("candle_50", mid, spot, atr_val, "1m", side))
    zones.append(_zone("ema20", ema_val, spot, atr_val, "1m", side))
    if twap is not None:
        prices["twap"] = twap
        zones.append(_zone("vwap", twap, spot, atr_val, "twap", side))
    if fut_vwap is not None:
        prices["vwap"] = fut_vwap
        zones.append(_zone("vwap", fut_vwap, spot, atr_val, "fut_vwap", side))
    elif twap is not None:
        prices["vwap"] = twap
    if poc is not None:
        prices["poc"] = poc
        zones.append(_zone("poc", poc, spot, atr_val, "fut_volume_profile", side))

    for gap in detect_fvgs(series, max_age_bars=max_age_bars):
        edge = _nearest_edge(spot, gap.low, gap.high)
        z = _zone("fvg", edge, spot, atr_val, "1m", side)
        zones.append(z)
        prev = prices.get("fvg")
        if prev is None or float(z["distance_atr"]) < signed_distance_atr(
            spot, prev, atr_val, side
        ):
            prices["fvg"] = edge

    pullback = [z for z in zones if float(z["distance_atr"]) >= 0.0]
    stretch = [z for z in pullback if z["zone"] in STRETCH_ZONES]
    nearest = min(stretch, key=lambda z: float(z["distance_atr"])) if stretch else None
    # Stretch zones (fvg, candle_50) only on the pullback side; EMA/TWAP/VWAP/POC always kept.
    always = [z for z in zones if z["zone"] not in STRETCH_ZONES]
    reported = [z for z in pullback if z["zone"] in STRETCH_ZONES] + always

    loc = EntryLocation(
        signal_candle_atr=(signal.h - signal.l) / atr_val,
        signal_body_atr=abs(signal.c - signal.o) / atr_val,
        entry_distance_atr=float(nearest["distance_atr"]) if nearest is not None else None,
        atr=atr_val,
        spot=spot,
        nearest=dict(nearest) if nearest is not None else None,
        zones=[dict(z) for z in reported],
    )
    return loc, prices


class LocationTracker:
    """Causal bar book: snapshot(now) sees only available_ts <= now."""

    def __init__(self, max_age_bars: int = MAX_AGE_BARS, poc_bin: float = POC_BIN) -> None:
        self._spot: list[_StampedBar] = []
        self._fut: list[_StampedBar] = []
        self._max_age_bars = max_age_bars
        self._poc_bin = poc_bin
        self.spot_instrument_id: str | None = None

    def on_bar(self, bar: BarClosed, available_ts: datetime) -> None:
        """Record a CLOSED bar. Open bars never arrive here."""
        if bar.tf != "1m":
            return
        stamped = _StampedBar(bar, available_ts)
        if is_index_future(bar.instrument_id):
            self._fut.append(stamped)
        else:
            self._spot.append(stamped)
            self.spot_instrument_id = bar.instrument_id

    def reset(self) -> None:
        """Clear session-scoped bars."""
        self._spot.clear()
        self._fut.clear()
        self.spot_instrument_id = None

    def last_available_ts(self) -> datetime | None:
        """available_ts of the latest recorded closed bar."""
        used = [s.available_ts for s in self._spot + self._fut]
        return max(used) if used else None

    def _asof(self, now: datetime) -> tuple[list[BarClosed], list[BarClosed], datetime | None]:
        spot = [s.bar for s in self._spot if s.available_ts <= now]
        fut = [s.bar for s in self._fut if s.available_ts <= now]
        used = [s.available_ts for s in self._spot + self._fut if s.available_ts <= now]
        return spot, fut, max(used) if used else None

    def snapshot(
        self, now: datetime, side: str, instrument_id: str = "NIFTY"
    ) -> EntryLocation | None:
        """EntryLocation at `now` from bars with available_ts <= now."""
        del instrument_id
        spot, fut, _avail = self._asof(now)
        return compute_entry_location(
            spot, side=side, fut_bars=fut, max_age_bars=self._max_age_bars, poc_bin=self._poc_bin
        )

    def feature_values(
        self, now: datetime, side: str = "CE"
    ) -> dict[tuple[str, str, str], FeatureValue]:
        """loc_* FeatureValues stamped with the last used bar's available_ts."""
        spot, fut, avail = self._asof(now)
        parts = _compute(
            spot, side=side, fut_bars=fut, max_age_bars=self._max_age_bars, poc_bin=self._poc_bin
        )
        inst = self.spot_instrument_id
        if parts is None or avail is None or inst is None:
            return {}
        loc, prices = parts
        as_of = datetime.fromisoformat(spot[-1].end) if spot else avail
        out: dict[tuple[str, str, str], FeatureValue] = {}

        def put(name: str, value: float | None) -> None:
            if value is None:
                return
            out[(name, inst, "1m")] = FeatureValue(value=value, as_of=as_of, available_ts=avail)

        put("loc_signal_candle_atr", loc.signal_candle_atr)
        put("loc_signal_body_atr", loc.signal_body_atr)
        put("loc_entry_distance_atr", loc.entry_distance_atr)
        put("loc_atr", loc.atr)
        put("loc_spot", loc.spot)
        put("loc_candle_50", prices.get("candle_50"))
        put("loc_ema20", prices.get("ema20"))
        put("loc_twap", prices.get("twap"))
        put("loc_vwap", prices.get("vwap"))
        put("loc_poc", prices.get("poc"))
        put("loc_fvg", prices.get("fvg"))
        return out
