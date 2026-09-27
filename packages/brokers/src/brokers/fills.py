"""V2 paper fill models: realistic only. DepthFill then FcMeasFill. No look-ahead."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Protocol

import yaml  # type: ignore[import-untyped]
from risk_engine import IST, RiskDecision

from brokers.orders import Order, OrderRefused
from brokers.paper import PaperBroker

TICK = 0.05
IMPACT_AT_25 = 0.05
DEFAULT_TABLE: dict[str, dict[str, float]] = {
    "ATM": {"before_12": 0.20, "from_12": 0.25, "after_15": 0.30},
    "ITM100": {"before_12": 0.30, "from_12": 0.35, "after_15": 0.40},
    "ITM200": {"before_12": 0.35, "from_12": 0.40, "after_15": 0.45},
}
_INDIA_YAML = (
    Path(__file__).resolve().parents[4] / "config" / "v2" / "markets" / "india.yaml"
)


def tick_against(price: float, side: str, tick: float = TICK) -> float:
    """Round against the order: BUY up, SELL down."""
    n = round(price / tick, 6)
    n = math.ceil(n) if side == "BUY" else math.floor(n)
    return max(tick, round(n * tick, 2))


def resting_limit(limit: float, side: str, tick: float = TICK) -> float | None:
    n = round(limit / tick, 6)
    ticks = math.floor(n) if side == "BUY" else math.ceil(n)
    if ticks < 1:
        return None
    return round(ticks * tick, 2)


def traded_through(
    print_px: float, limit: float, side: str, tick: float = TICK
) -> bool:
    rest = resting_limit(limit, side, tick)
    if rest is None:
        return False
    if side == "BUY":
        return print_px <= rest - tick + 1e-9
    return print_px >= rest + tick - 1e-9


def limit_fill_price(
    print_px: float, limit: float, side: str, tick: float = TICK
) -> float | None:
    """REG-14: fill only on a trade-through, always at the limit. Touch is not a fill."""
    rest = resting_limit(limit, side, tick)
    if rest is None or not traded_through(print_px, limit, side, tick):
        return None
    return rest


def stop_fill_price(
    print_px: float, trigger: float, side: str, slip: float, tick: float = TICK
) -> float | None:
    """REG-14: stop fills at print ± slip, never better than the trigger."""
    hit = print_px >= trigger - 1e-9 if side == "BUY" else print_px <= trigger + 1e-9
    if not hit:
        return None
    raw = print_px + slip if side == "BUY" else print_px - slip
    px = tick_against(raw, side, tick)
    if side == "BUY":
        return max(px, trigger)
    return min(px, trigger)


def fcmeas_half_spread(
    bucket: str, now: datetime, table: dict[str, dict[str, float]] | None = None
) -> float:
    rows = table or DEFAULT_TABLE
    band = "before_12"
    tod = now.astimezone(IST).time()
    if tod >= time(15, 0):
        band = "after_15"
    elif tod >= time(12, 0):
        band = "from_12"
    return float(rows[bucket][band])


def flat_sensitivity(ltp: float, side: str, pts: float = 0.20) -> float:
    """Flat 0.20 pt/side — reports only, never the booked fill (K15)."""
    return ltp + pts if side == "BUY" else ltp - pts


def load_fcmeas_table(path: Path | None = None) -> dict[str, dict[str, float]]:
    src = path or _INDIA_YAML
    if not src.is_file():
        return {k: dict(v) for k, v in DEFAULT_TABLE.items()}
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    raw = data.get("fcmeas_pts_per_side") or DEFAULT_TABLE
    return {
        str(k): {str(bk): float(bv) for bk, bv in row.items()} for k, row in raw.items()
    }


@dataclass(frozen=True)
class Quote:
    """One depth/LTP observation visible to the fill model."""

    available_ts: datetime
    bid: float | None
    ask: float | None
    ltp: float | None
    instrument_id: str = ""


@dataclass
class FillOrder:
    """Fill-model view of an order (clock-aware; no broker secrets)."""

    client_order_id: str
    side: str
    order_type: str
    available_ts: datetime
    decision_ts: datetime
    lots: int
    lot_size: int
    instrument_id: str
    price: float | None = None
    trigger_price: float | None = None
    moneyness: str = "ATM"
    tick_size: float = TICK
    latency_ms: int = 0


class FillModel(Protocol):
    name: str

    def price(
        self, order: FillOrder, quote: Quote | None, ltp: float | None, now: datetime
    ) -> tuple[float, str] | None: ...


def _visible(order: FillOrder, quote: Quote, now: datetime) -> bool:
    """No look-ahead: quote must be at/after latency and at/before engine now."""
    earliest = order.available_ts
    if order.latency_ms:
        earliest = order.available_ts + timedelta(milliseconds=order.latency_ms)
    return earliest <= quote.available_ts <= now


def _impact(lots: int) -> float:
    return IMPACT_AT_25 * (lots / 25.0)


class DepthFill:
    """Buy at the ask (sell at the bid) of the first eligible depth quote."""

    name = "depth"

    def price(
        self, order: FillOrder, quote: Quote | None, ltp: float | None, now: datetime
    ) -> tuple[float, str] | None:
        if quote is None or not _visible(order, quote, now):
            return None
        if quote.bid is None and quote.ask is None:
            return None
        side = order.side
        kind = order.order_type
        touch = quote.ask if side == "BUY" else quote.bid
        print_px = quote.ltp if quote.ltp is not None else touch
        if touch is None and print_px is None:
            return None
        if kind == "MARKET":
            raw = (touch if touch is not None else print_px) or 0.0
            raw = (
                raw + _impact(order.lots)
                if side == "BUY"
                else raw - _impact(order.lots)
            )
            return tick_against(raw, side, order.tick_size), self.name
        if kind in ("SL", "SL-M"):
            if order.trigger_price is None or print_px is None:
                return None
            slip = fcmeas_half_spread(order.moneyness, now)
            px = stop_fill_price(
                print_px, order.trigger_price, side, slip, order.tick_size
            )
            return (px, self.name) if px is not None else None
        if order.price is None:
            return None
        through = touch if touch is not None else print_px
        if through is None:
            return None
        px = limit_fill_price(through, order.price, side, order.tick_size)
        return (px, self.name) if px is not None else None


class FcMeasFill:
    """LTP ± Round 8 FC-MEAS half-spread by moneyness and time of day (K15)."""

    name = "fcmeas"

    def __init__(self, table: dict[str, dict[str, float]] | None = None) -> None:
        self.table = table or load_fcmeas_table()

    def price(
        self, order: FillOrder, quote: Quote | None, ltp: float | None, now: datetime
    ) -> tuple[float, str] | None:
        px_ltp = ltp
        if px_ltp is None and quote is not None and _visible(order, quote, now):
            px_ltp = quote.ltp
        if px_ltp is None:
            return None
        if quote is not None and not _visible(order, quote, now):
            return None
        slip = fcmeas_half_spread(order.moneyness, now, self.table)
        side = order.side
        kind = order.order_type
        if kind == "MARKET":
            raw = px_ltp + slip if side == "BUY" else px_ltp - slip
            return tick_against(raw, side, order.tick_size), self.name
        if kind in ("SL", "SL-M"):
            if order.trigger_price is None:
                return None
            px = stop_fill_price(
                px_ltp, order.trigger_price, side, slip, order.tick_size
            )
            return (px, self.name) if px is not None else None
        if order.price is None:
            return None
        px = limit_fill_price(px_ltp, order.price, side, order.tick_size)
        return (px, self.name) if px is not None else None


def choose_fill(
    order: FillOrder, quotes: list[Quote], ltp: float | None, now: datetime
) -> tuple[float, str] | None:
    """DepthFill on the first eligible quote; else FcMeasFill. Never reads after `now`."""
    visible = [q for q in quotes if _visible(order, q, now)]
    depth = DepthFill()
    for q in visible:
        got = depth.price(order, q, q.ltp, now)
        if got is not None:
            return got
    return FcMeasFill().price(order, visible[0] if visible else None, ltp, now)


class ClockedPaperBroker(PaperBroker):
    """PaperBroker wrap: engine clock, realistic fills only, DepthFill then FcMeasFill."""

    name = "paper"
    mode = "paper"
    is_paper = True

    def __init__(
        self,
        *,
        clock: Any,
        slippage_ticks: int = 1,
        tick_size: float = TICK,
        starting_cash: float = 0.0,
        latency_ms: int = 0,
    ) -> None:
        super().__init__(
            slippage_ticks=slippage_ticks,
            tick_size=tick_size,
            starting_cash=starting_cash,
            cost_model="realistic",
        )
        self.clock = clock
        self.latency_ms = latency_ms
        self.quotes: list[Quote] = []
        self.fill_models: dict[str, str] = {}
        self.sensitivity_flat: dict[str, float] = {}
        self._order_meta: dict[str, FillOrder] = {}

    def approval_problems(
        self, decision: Any, action: str, client_order_id: str
    ) -> list[str]:
        if not isinstance(decision, RiskDecision):
            return ["no risk decision"]
        problems: list[str] = []
        if not decision.approved:
            problems.append(f"risk vetoed ({decision.reason_code})")
        if decision.action != action:
            problems.append(f"decision is for {decision.action}, not {action}")
        if decision.client_order_id != client_order_id:
            problems.append("decision is for a different order")
        age = (self.clock.now() - decision.ts).total_seconds()
        if not -5 <= age <= self.max_decision_age_s:
            problems.append(
                f"decision is {age:.0f}s old (max {self.max_decision_age_s:.0f}s)"
            )
        return problems

    def require_approval(
        self, decision: Any, action: str, client_order_id: str
    ) -> None:
        problems = self.approval_problems(decision, action, client_order_id)
        if problems:
            raise OrderRefused("; ".join(problems))

    def _accept(self, intent: Any, **kw: Any) -> Order:
        if intent.client_order_id in self.orders:
            return self.orders[intent.client_order_id]
        order = super()._accept(intent, **kw)
        now = self.clock.now()
        self._order_meta[intent.client_order_id] = FillOrder(
            client_order_id=intent.client_order_id,
            side=intent.side,
            order_type=intent.order_type,
            available_ts=now,
            decision_ts=now,
            lots=intent.lots,
            lot_size=intent.lot_size,
            instrument_id=intent.instrument_id,
            price=intent.price,
            trigger_price=intent.trigger_price,
            latency_ms=self.latency_ms,
            tick_size=self.tick_size,
        )
        return order

    def remember(self, client_order_id: str, **fields: Any) -> None:
        meta = self._order_meta.get(client_order_id)
        if meta is None:
            return
        self._order_meta[client_order_id] = FillOrder(**{**meta.__dict__, **fields})

    def on_depth(self, quote: Quote) -> None:
        now = self.clock.now()
        if quote.available_ts > now:
            return
        self.quotes.append(quote)
        inst = quote.instrument_id
        ltp = quote.ltp
        for order in list(self.orders.values()):
            if not order.is_open:
                continue
            meta = self._order_meta.get(order.client_order_id)
            if meta is None:
                continue
            if inst and meta.instrument_id and inst != meta.instrument_id:
                continue
            got = choose_fill(meta, self.quotes, ltp, now)
            if got is None:
                continue
            px, model = got
            self.fill_models[order.client_order_id] = model
            if ltp is not None:
                self.sensitivity_flat[order.client_order_id] = flat_sensitivity(
                    ltp, order.intent.side
                )
            self._fill(order, px, quote.available_ts)

    def on_tick(self, symbol: str, ltp: float, ts: Any = None) -> None:
        now = self.clock.now()
        if ts is not None and isinstance(ts, datetime) and ts > now:
            return
        self.ltp[symbol] = ltp
        q_ts = ts if isinstance(ts, datetime) else now
        quote = Quote(available_ts=q_ts, bid=None, ask=None, ltp=ltp)
        if q_ts <= now:
            self.quotes.append(quote)
        for order in [
            o for o in self.orders.values() if o.is_open and o.intent.symbol == symbol
        ]:
            if not order.is_open:
                continue
            self._trail(order, ltp)
            meta = self._order_meta.get(order.client_order_id)
            if meta is None:
                px = self._fill_price(order, ltp)
                model = "fcmeas"
            else:
                got = choose_fill(meta, self.quotes, ltp, now)
                if got is None:
                    continue
                px, model = got
            if px is None:
                continue
            self.fill_models[order.client_order_id] = model
            self.sensitivity_flat[order.client_order_id] = flat_sensitivity(
                ltp, order.intent.side
            )
            self._fill(order, px, ts)
