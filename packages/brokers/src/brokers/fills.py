"""V2 paper fill models: realistic only. DepthFill then FcMeasFill. No look-ahead."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Protocol

import yaml  # type: ignore[import-untyped]
from risk_engine import IST, RiskDecision, TradeIntent

from brokers.orders import Order, OrderRefused, OrderState
from brokers.paper import PaperBroker, _lots_from_qty

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


class ModifyUnsupported(Exception):
    """In-place quantity modify is not available; caller may cancel-then-replace."""


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
        allowed = set(FillOrder.__dataclass_fields__)
        extra = {k: v for k, v in fields.items() if k in allowed}
        meta = self._order_meta.get(client_order_id)
        if meta is None:
            order = self.orders.get(client_order_id)
            if order is None and not extra:
                return
            now = self.clock.now()
            intent = getattr(order, "intent", None) if order is not None else None

            def _field(name: str, default: Any = None) -> Any:
                if extra.get(name) is not None:
                    return extra[name]
                if intent is not None:
                    return getattr(intent, name, default)
                return default

            meta = FillOrder(
                client_order_id=client_order_id,
                side=str(_field("side", "BUY")),
                order_type=str(_field("order_type", "LIMIT")),
                available_ts=extra.get("available_ts") or now,
                decision_ts=extra.get("decision_ts") or now,
                lots=int(_field("lots") or 1),
                lot_size=int(_field("lot_size") or 1),
                instrument_id=str(_field("instrument_id") or ""),
                price=_field("price"),
                trigger_price=_field("trigger_price"),
                moneyness=str(extra.get("moneyness") or "ITM100"),
                tick_size=float(extra.get("tick_size") or self.tick_size),
                latency_ms=int(extra.get("latency_ms") or self.latency_ms),
            )
        self._order_meta[client_order_id] = FillOrder(**{**meta.__dict__, **extra})

    def restore_working_order(
        self,
        row: dict[str, Any],
        *,
        plan: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> Order:
        """Rehydrate a persisted paper order with price + fill meta. Never place/submit."""
        oid = str(row["client_order_id"])
        held = self.orders.get(oid)
        stamp = now if now is not None else self.clock.now()
        extras = self._restore_meta_fields(row, plan or {}, stamp)
        if held is not None:
            if oid not in self._order_meta:
                self.remember(oid, **extras)
            return held
        price = row.get("price")
        if price is None:
            price = (plan or {}).get("limit_price")
        kind = str(row.get("order_type") or "LIMIT")
        trigger = row.get("trigger_price") if kind in ("SL", "SL-M") else None
        symbol = str(row.get("symbol") or row.get("instrument_id") or (plan or {}).get("instrument_id") or "")
        inst = str(row.get("instrument_id") or (plan or {}).get("instrument_id") or "")
        lots = int(row.get("lots") or (plan or {}).get("lots") or 0)
        lot_size = int(row.get("lot_size") or (plan or {}).get("lot_size") or 0)
        qty = int(row.get("qty") or 0)
        if (lots <= 0 or lot_size <= 0) and qty > 0:
            lots, lot_size = _lots_from_qty(qty, symbol or inst)
        if lots <= 0:
            lots = 1
        if lot_size <= 0:
            lot_size = 65
        px = float(price) if price is not None else None
        trig = float(trigger) if trigger is not None else None
        stop = row.get("stop_loss")
        if stop is None and kind not in ("SL", "SL-M"):
            stop = row.get("trigger_price")
        intent = TradeIntent(
            symbol=symbol or inst,
            side=str(row.get("side") or "BUY"),
            lots=lots,
            lot_size=lot_size,
            order_type=kind,
            price=px,
            trigger_price=trig,
            decision_price=px,
            purpose=str(row.get("purpose") or "ENTRY"),
            exit_reason=row.get("exit_reason"),
            instrument_id=inst,
            client_order_id=oid,
            stop_loss=float(stop) if stop is not None else None,
        )
        order = Order(
            intent=intent,
            broker="paper",
            mode="paper",
            on_transition=self._emit_transition,
            on_fill=self._emit_fill,
        )
        raw_state = str(row.get("status") or row.get("state") or "SUBMITTED")
        try:
            order.state = OrderState.SUBMITTED if raw_state == "NEW" else OrderState(raw_state)
        except ValueError:
            order.state = OrderState.SUBMITTED
        order.filled_qty = int(row.get("filled_qty") or 0)
        if row.get("avg_fill_price") is not None:
            order.avg_fill_price = float(row["avg_fill_price"])
        order.price = px
        order.trigger_price = trig
        self.orders[oid] = order
        self.remember(oid, **extras)
        return order

    def _restore_meta_fields(
        self, row: dict[str, Any], plan: dict[str, Any], stamp: datetime
    ) -> dict[str, Any]:
        sent = plan.get("sent_at")
        if isinstance(sent, str) and sent:
            sent = datetime.fromisoformat(sent)
        if not isinstance(sent, datetime):
            created = row.get("created_at")
            if isinstance(created, str) and created:
                sent = datetime.fromisoformat(created)
            elif isinstance(created, datetime):
                sent = created
            else:
                sent = stamp
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=IST)
        price = row.get("price")
        if price is None:
            price = plan.get("limit_price")
        kind = str(row.get("order_type") or "LIMIT")
        trigger = row.get("trigger_price") if kind in ("SL", "SL-M") else None
        moneyness = "ITM100"
        dec = plan.get("decision")
        shadow = getattr(dec, "shadow", None) if dec is not None else None
        if isinstance(shadow, dict) and shadow.get("chosen"):
            moneyness = str(shadow["chosen"])
        elif isinstance(plan.get("moneyness"), str):
            moneyness = str(plan["moneyness"])
        out: dict[str, Any] = {
            "side": str(row.get("side") or "BUY"),
            "order_type": kind,
            "available_ts": sent,
            "decision_ts": sent,
            "instrument_id": str(row.get("instrument_id") or plan.get("instrument_id") or ""),
            "moneyness": moneyness,
            "tick_size": self.tick_size,
            "latency_ms": self.latency_ms,
        }
        lots = int(row.get("lots") or plan.get("lots") or 0)
        lot_size = int(row.get("lot_size") or plan.get("lot_size") or 0)
        if lots > 0:
            out["lots"] = lots
        if lot_size > 0:
            out["lot_size"] = lot_size
        if price is not None:
            out["price"] = float(price)
        if trigger is not None:
            out["trigger_price"] = float(trigger)
        return out

    def modify_order(self, order_id: str, qty: int) -> Order:  # type: ignore[override]
        """In-place quantity modify (Dhan supports qty modify). Same client_order_id."""
        order = self.orders.get(order_id)
        if order is None or not order.is_open:
            raise OrderRefused(f"{order_id}: cannot modify a missing or closed order")
        lot = int(order.intent.lot_size or 1)
        new_qty = int(qty)
        if new_qty <= 0 or lot <= 0 or new_qty % lot != 0:
            raise OrderRefused(f"{order_id}: qty {new_qty} is not a whole-lot multiple of {lot}")
        if order.filled_qty > new_qty:
            raise OrderRefused(f"{order_id}: filled {order.filled_qty} exceeds new qty {new_qty}")
        new_lots = new_qty // lot
        order.intent = replace(order.intent, lots=new_lots)
        self.remember(order_id, lots=new_lots)
        return order

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
