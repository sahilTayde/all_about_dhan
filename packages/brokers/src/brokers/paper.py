"""PaperBroker: simulated fills on the next tick, configurable slippage. Never calls a broker."""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from brokers.orders import (
    BrokerAdapter,
    InvalidTransition,
    Order,
    OrderSnapshot,
    OrderState,
    Position,
    exit_intent,
)
from risk_engine import RiskDecision, TradeIntent

log = logging.getLogger("brokers.paper")

# Longer names first so BANKNIFTY is not matched as NIFTY. Brokers must not import ledger.
_LOT_SIZES = (
    ("BANKNIFTY", 30),
    ("MIDCPNIFTY", 50),
    ("FINNIFTY", 40),
    ("BANKEX", 15),
    ("SENSEX", 20),
    ("NIFTY", 65),
)


def _lots_from_qty(qty: int, symbol: str) -> tuple[int, int]:
    text = (symbol or "").upper()
    lot = 65
    for name, size in _LOT_SIZES:
        if name in text:
            lot = size
            break
    if lot <= 0 or qty <= 0 or qty % lot != 0:
        raise ValueError(f"qty {qty} is not a whole multiple of lot size {lot}")
    return qty // lot, lot


class PaperBroker(BrokerAdapter):
    """Orders placed now are first looked at on the next `on_tick` for their symbol.

    MARKET fills at LTP ± slippage. LIMIT fills when LTP crosses the limit, at no worse than the
    limit. SL-M becomes MARKET once LTP touches the trigger; SL becomes LIMIT. A super order's
    target (LIMIT) and stop (SL-M, optionally trailing) legs appear after the entry fills; when
    one leg fills the other is cancelled (OCO).

    `cost_model="realistic"` (config/paper_costs.yaml): prices round against the order's side
    (buys up, sells down; limits never beyond the limit), and a LIMIT fills only when LTP trades
    through it by one tick, at the limit. `legacy` keeps nearest-tick rounding and touch fills.
    """

    name = "paper"
    mode = "paper"

    def __init__(
        self,
        *,
        slippage_ticks: int = 1,
        tick_size: float = 0.05,
        starting_cash: float = 0.0,
        cost_model: str = "legacy",
    ) -> None:
        super().__init__()
        if cost_model not in ("legacy", "realistic"):
            raise ValueError(
                f"cost_model must be legacy or realistic, got {cost_model!r}"
            )
        self.cost_model = cost_model
        self.tick_size = tick_size
        self.slippage = slippage_ticks * tick_size
        self.cash = starting_cash
        self.ltp: dict[str, float] = {}
        self._positions: dict[str, Position] = {}
        self._legs: dict[
            str, tuple[str, str]
        ] = {}  # super entry id -> (target leg id, stop leg id)
        self._trail_ref: dict[
            str, float
        ] = {}  # stop leg id -> price the trail last stepped from
        self._triggered: set[str] = set()

    # ------------------------------------------------------------- orders

    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        self.require_approval(decision, self.action_for(intent), intent.client_order_id)
        return self._accept(intent)

    def place_super_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        if intent.target is None or intent.stop_loss is None:
            raise ValueError("super order needs target and stop_loss")
        self.require_approval(decision, "ENTRY", intent.client_order_id)
        return self._accept(intent, is_super=True)

    def _accept(self, intent: TradeIntent, **kw: Any) -> Order:
        if intent.client_order_id in self.orders:  # idempotent retry
            return self.orders[intent.client_order_id]
        order = self._register(intent, **kw)
        order.transition(OrderState.SUBMITTED, "paper: fills on next tick")
        return order

    def modify_order(
        self,
        order: Order,
        decision: RiskDecision,
        *,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        target: Optional[float] = None,
        stop_loss: Optional[float] = None,
        trailing_jump: Optional[float] = None,
    ) -> Order:
        self.require_approval(decision, "MODIFY", order.client_order_id)
        legs = self._legs.get(order.client_order_id)
        if not order.is_open and not legs:
            raise InvalidTransition(
                f"{order.client_order_id}: cannot modify a {order.state.value} order"
            )
        for name, value in (
            ("price", price),
            ("trigger_price", trigger_price),
            ("target", target),
            ("stop_loss", stop_loss),
            ("trailing_jump", trailing_jump),
        ):
            if value is not None:
                setattr(order, name, value)
        if legs:
            tgt, stop = self.orders[legs[0]], self.orders[legs[1]]
            if target is not None:
                tgt.price = target
            if stop_loss is not None:
                stop.trigger_price = stop_loss
            if trailing_jump is not None:
                stop.trailing_jump = trailing_jump
        log.info(
            "paper modify %s price=%s trigger=%s target=%s stop=%s trail=%s",
            order.client_order_id,
            price,
            trigger_price,
            target,
            stop_loss,
            trailing_jump,
        )
        return order

    def cancel_order(
        self, order: Order, decision: RiskDecision, reason: str = "USER_CANCEL"
    ) -> Order:
        self.require_approval(decision, "CANCEL", order.client_order_id)
        if order.is_open:
            self._cancel(order, reason)
        for leg in self._legs.pop(order.client_order_id, ()):
            if self.orders[leg].is_open:
                self._cancel(self.orders[leg], reason)
        return order

    def _cancel(self, order: Order, reason: str) -> None:
        order.cancel_reason = reason
        order.transition(OrderState.CANCELLED, reason)

    def flatten_all(self, decision: RiskDecision) -> list[Order]:
        self.require_approval(decision, "FLATTEN", "FLATTEN_ALL")
        for order in list(self.orders.values()):
            if order.is_open:
                self._cancel(order, "KILL_SWITCH")
        self._legs.clear()
        return [
            self._accept(
                exit_intent(
                    p, exit_reason="KILL_SWITCH", decision_price=self.ltp.get(p.symbol)
                )
            )
            for p in self.get_positions()
        ]

    # --------------------------------------------------------------- ticks

    def on_tick(self, symbol: str, ltp: float, ts: Any = None) -> None:
        self.ltp[symbol] = ltp
        for order in [
            o for o in self.orders.values() if o.is_open and o.intent.symbol == symbol
        ]:
            if not order.is_open:  # cancelled by an OCO sibling earlier in this loop
                continue
            self._trail(order, ltp)
            px = self._fill_price(order, ltp)
            if px is not None:
                self._fill(order, px, ts)

    def _tick(self, x: float, side: Optional[str] = None) -> float:
        """Nearest tick (legacy), or against `side` in realistic mode: BUY rounds up, SELL down."""
        if self.cost_model != "realistic" or side not in ("BUY", "SELL"):
            return max(
                self.tick_size, round(round(x / self.tick_size) * self.tick_size, 2)
            )
        n = round(x / self.tick_size, 6)  # 230.05 / 0.05 = 4600.999... is 4601 ticks
        n = math.ceil(n) if side == "BUY" else math.floor(n)
        return max(self.tick_size, round(n * self.tick_size, 2))

    def _fill_price(self, order: Order, ltp: float) -> Optional[float]:
        buy = order.intent.side == "BUY"
        slip = self.slippage if buy else -self.slippage
        kind = order.intent.order_type
        if self.cost_model == "realistic":
            return self._fill_price_realistic(order, ltp, buy, slip, kind)
        if kind == "MARKET":
            return self._tick(ltp + slip)
        if kind in ("SL", "SL-M") and order.client_order_id not in self._triggered:
            if not (ltp >= order.trigger_price if buy else ltp <= order.trigger_price):
                return None
            self._triggered.add(order.client_order_id)
        if kind == "SL-M":
            return self._tick(ltp + slip)
        if buy and ltp <= order.price:
            return self._tick(min(order.price, ltp + slip))
        if not buy and ltp >= order.price:
            return self._tick(max(order.price, ltp + slip))
        return None

    def _fill_price_realistic(
        self, order: Order, ltp: float, buy: bool, slip: float, kind: str
    ) -> Optional[float]:
        side = "BUY" if buy else "SELL"
        if kind == "MARKET":
            return self._tick(ltp + slip, side)
        if kind in ("SL", "SL-M") and order.client_order_id not in self._triggered:
            if not (ltp >= order.trigger_price if buy else ltp <= order.trigger_price):
                return None
            self._triggered.add(order.client_order_id)
        if kind == "SL-M":
            return self._tick(ltp + slip, side)
        # Resting limit on-tick and never beyond itself (buy floors, sell ceils); trade-through, at the limit.
        n = round(order.price / self.tick_size, 6)
        ticks = math.floor(n) if buy else math.ceil(n)
        if ticks < 1:
            return None
        limit = round(ticks * self.tick_size, 2)
        eps = 1e-9
        if buy and ltp <= limit - self.tick_size + eps:
            return limit
        if not buy and ltp >= limit + self.tick_size - eps:
            return limit
        return None

    def _trail(self, order: Order, ltp: float) -> None:
        ref = self._trail_ref.get(order.client_order_id)
        if not order.trailing_jump or ref is None:
            return
        protects_long = order.intent.side == "SELL"
        steps = int(
            ((ltp - ref) if protects_long else (ref - ltp)) // order.trailing_jump
        )
        if steps > 0:
            move = steps * order.trailing_jump * (1 if protects_long else -1)
            order.trigger_price = self._tick(order.trigger_price + move)
            self._trail_ref[order.client_order_id] = ref + move
            log.info(
                "paper trail %s stop -> %s", order.client_order_id, order.trigger_price
            )

    def _fill(self, order: Order, px: float, ts: Any) -> None:
        qty = order.remaining_qty
        order.apply_fill(qty, px, ts)
        i = order.intent
        signed = qty if i.side == "BUY" else -qty
        pos = self._positions.get(i.symbol) or Position(
            i.symbol, 0, 0.0, i.instrument_id
        )
        new_net = pos.net_qty + signed
        if new_net == 0:
            self._positions.pop(i.symbol, None)
        else:
            if pos.net_qty == 0 or (pos.net_qty > 0) != (new_net > 0):
                pos.avg_price = px
            elif (pos.net_qty > 0) == (signed > 0):
                pos.avg_price = round(
                    (pos.avg_price * abs(pos.net_qty) + px * qty) / abs(new_net), 4
                )
            pos.net_qty = new_net
            self._positions[i.symbol] = pos
        self.cash -= signed * px
        if order.is_super:
            self._open_legs(order)
        for parent, legs in list(self._legs.items()):
            if order.client_order_id in legs:
                for leg in legs:
                    if self.orders[leg].is_open:
                        self._cancel(self.orders[leg], "OCO_SIBLING_FILLED")
                del self._legs[parent]

    def _open_legs(self, parent: Order) -> None:
        i = parent.intent
        common = dict(
            symbol=i.symbol,
            side="SELL" if i.side == "BUY" else "BUY",
            lots=i.lots,
            lot_size=i.lot_size,
            purpose="EXIT",
            instrument_id=i.instrument_id,
            exchange=i.exchange,
            product_type=i.product_type,
            trade_id=i.trade_id,
        )
        tgt = self._accept(
            TradeIntent(
                order_type="LIMIT",
                price=parent.target,
                decision_price=parent.target,
                exit_reason="TARGET_HIT",
                client_order_id=f"{i.client_order_id}-T",
                **common,
            )
        )
        stop = self._accept(
            TradeIntent(
                order_type="SL-M",
                trigger_price=parent.stop_loss,
                decision_price=parent.stop_loss,
                exit_reason="STOP_HIT",
                client_order_id=f"{i.client_order_id}-S",
                **common,
            ),
            trailing_jump=parent.trailing_jump,
        )
        self._legs[i.client_order_id] = (tgt.client_order_id, stop.client_order_id)
        self._trail_ref[stop.client_order_id] = parent.avg_fill_price

    # --------------------------------------------------------------- reads

    def get_order_status(self, order: Order) -> Order:
        return order

    def get_positions(self) -> list[Position]:
        return [
            Position(p.symbol, p.net_qty, p.avg_price, p.instrument_id)
            for p in self._positions.values()
        ]

    def get_orders(self) -> list[OrderSnapshot]:
        return [
            OrderSnapshot(
                o.client_order_id,
                o.client_order_id,
                o.state,
                o.filled_qty,
                o.intent.symbol,
            )
            for o in self.orders.values()
        ]

    def get_balance(self) -> float:
        return round(self.cash, 2)

    def rebuild_from_ledger(self, store: Any) -> int:
        """V2-10: restore open orders and positions from the durable ledger after restart."""
        from brokers.orders import Order, OrderState, Position
        from risk_engine import TradeIntent

        self.orders.clear()
        self._positions.clear()
        n = 0
        for row in store.open_orders():
            qty = max(1, int(row.get("qty") or 1))
            symbol = str(row.get("symbol") or row.get("instrument_id") or "")
            lots, lot_size = _lots_from_qty(qty, symbol)
            intent = TradeIntent(
                symbol=symbol,
                side=str(row.get("side") or "BUY"),
                lots=lots,
                lot_size=lot_size,
                order_type=str(row.get("order_type") or "LIMIT"),
                price=row.get("price"),
                trigger_price=row.get("trigger_price"),
                decision_price=row.get("decision_price"),
                purpose=str(row.get("purpose") or "ENTRY"),
                exit_reason=row.get("exit_reason"),
                instrument_id=str(row.get("instrument_id") or ""),
                client_order_id=str(row["client_order_id"]),
            )
            order = Order(intent=intent, broker=self.name, mode=self.mode)
            try:
                order.state = OrderState(str(row["status"]))
            except ValueError:
                order.state = OrderState.NEW
            order.filled_qty = int(row.get("filled_qty") or 0)
            order.avg_fill_price = row.get("avg_fill_price")
            self.orders[intent.client_order_id] = order
            n += 1
        for pos in store.open_positions():
            p = Position(
                str(pos.get("symbol") or pos.get("instrument_id") or ""),
                int(pos["net_qty"]),
                float(pos.get("avg_price") or 0),
                str(pos.get("instrument_id") or ""),
            )
            self._positions[p.key] = p
            n += 1
        return n
