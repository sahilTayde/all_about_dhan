"""DhanBroker: order intents -> Dhan v2 REST. Refuses to send unless the live gate is fully open.

Endpoints and fields from https://dhanhq.co/docs/v2/orders/, /super-order/, /portfolio/ and
/funds/ (read 2026-09-26). HTTP, auth headers and error parsing reuse dhan_client.RestClient.

Live gate (all three, checked on every order/modify/cancel/exit/flatten call):
  1. config/risk_limits.yaml mode is limited_live or live
  2. env ALL_ABOUT_DHAN_LIVE_CONFIRM == "I_UNDERSTAND_REAL_MONEY"
  3. a fresh, approved RiskDecision for exactly this action and client order id
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from dhan_client.config import load_settings
from dhan_client.errors import DhanApiError
from dhan_client.rest import RestClient

from brokers.orders import (
    BrokerAdapter,
    InvalidTransition,
    LiveOrderRefused,
    Order,
    OrderSnapshot,
    OrderState,
    Position,
)
from risk_engine import (
    DEFAULT_CONFIG_PATH,
    LIVE_CONFIRM_ENV,
    LIVE_MODES,
    RiskDecision,
    TradeIntent,
    live_confirmed,
    load_limits,
)

log = logging.getLogger("brokers.dhan")

ORDERS = "/orders"
ORDER = "/orders/{order_id}"
ORDER_BY_CORRELATION = "/orders/external/{correlation_id}"
SUPER_ORDERS = "/super/orders"
SUPER_ORDER = "/super/orders/{order_id}"
SUPER_ORDER_LEG = "/super/orders/{order_id}/{leg}"
POSITIONS = "/positions"  # GET = open positions, DELETE = exit all positions + cancel all orders
FUND_LIMIT = "/fundlimit"

ORDER_TYPES = {"MARKET": "MARKET", "LIMIT": "LIMIT", "SL": "STOP_LOSS", "SL-M": "STOP_LOSS_MARKET"}
STATUS = {
    "TRANSIT": OrderState.SUBMITTED,
    "PENDING": OrderState.SUBMITTED,
    "PART_TRADED": OrderState.PARTIAL,
    "TRADED": OrderState.FILLED,
    "CLOSED": OrderState.FILLED,  # super order: entry and one exit leg fully done
    "REJECTED": OrderState.REJECTED,
    "CANCELLED": OrderState.CANCELLED,
    "EXPIRED": OrderState.EXPIRED,
}
CORRELATION_ID = re.compile(r"^[A-Za-z0-9 _-]{1,30}$")


class DhanBroker(BrokerAdapter):
    name = "dhan"

    def __init__(self, rest: Optional[RestClient] = None, *, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        super().__init__()
        self.rest = rest or RestClient(load_settings())
        self.config_path = Path(config_path)
        self.mode = "unknown"

    @property
    def client_id(self) -> str:
        return self.rest.settings.credentials.client_id

    # ----------------------------------------------------------- the gate

    def _live_gate(self, decision: Any, action: str, client_order_id: str) -> None:
        problems = self.approval_problems(decision, action, client_order_id)
        try:
            mode = load_limits(self.config_path)["mode"]
        except Exception as exc:
            mode, problems = None, [f"risk config unreadable ({type(exc).__name__})", *problems]
        if mode not in LIVE_MODES:
            problems.insert(0, f"mode is {mode!r}, not limited_live/live")
        if not live_confirmed():
            problems.append(f"{LIVE_CONFIRM_ENV} is not set to the confirmation phrase")
        if self.rest.settings.dry_run:
            problems.append("Dhan credentials missing (dry-run)")
        if problems:
            log.error("LIVE ORDER REFUSED %s %s: %s", action, client_order_id, "; ".join(problems))
            raise LiveOrderRefused("; ".join(problems))
        self.mode = mode

    def _call(self, method: str, path: str, body: Any = None) -> dict[str, Any]:
        resp = self.rest.request(method, path, json_body=body)
        if resp.get("status") == "dry_run":
            raise DhanApiError("dry-run: no Dhan call was made")
        return resp

    @staticmethod
    def _rows(resp: dict[str, Any]) -> list[dict[str, Any]]:
        data = resp.get("data")
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------- orders

    def place_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        self._live_gate(decision, self.action_for(intent), intent.client_order_id)
        self._validate(intent)
        body = self._base_body(intent)
        body.update(
            orderType=ORDER_TYPES[intent.order_type], validity="DAY", afterMarketOrder=False,
            price=float(intent.price) if intent.order_type in ("LIMIT", "SL") else 0.0,
        )
        if intent.order_type in ("SL", "SL-M"):
            body["triggerPrice"] = float(intent.trigger_price)
        return self._submit(intent, ORDERS, body)

    def place_super_order(self, intent: TradeIntent, decision: RiskDecision) -> Order:
        if intent.target is None or intent.stop_loss is None:
            raise ValueError("super order needs target and stop_loss")
        if intent.order_type not in ("LIMIT", "MARKET"):
            raise ValueError("super order entry must be LIMIT or MARKET")
        self._live_gate(decision, "ENTRY", intent.client_order_id)
        self._validate(intent)
        body = self._base_body(intent)
        body.update(
            orderType=intent.order_type, price=float(intent.price) if intent.order_type == "LIMIT" else 0.0,
            targetPrice=float(intent.target), stopLossPrice=float(intent.stop_loss),
            trailingJump=float(intent.trailing_jump or 0),
        )
        return self._submit(intent, SUPER_ORDERS, body, is_super=True)

    def _validate(self, i: TradeIntent) -> None:
        problems = []
        if not CORRELATION_ID.match(i.client_order_id):
            problems.append("client_order_id must be 1-30 chars of [A-Za-z0-9 _-] (Dhan correlationId)")
        if not i.instrument_id:
            problems.append("instrument_id (Dhan securityId) is required")
        if i.side not in ("BUY", "SELL") or i.qty <= 0 or i.order_type not in ORDER_TYPES:
            problems.append(f"bad side/qty/order_type {i.side}/{i.qty}/{i.order_type}")
        if i.order_type in ("LIMIT", "SL") and not i.price:
            problems.append(f"{i.order_type} needs price")
        if i.order_type in ("SL", "SL-M") and not i.trigger_price:
            problems.append(f"{i.order_type} needs trigger_price")
        if problems:
            raise ValueError("; ".join(problems))

    def _base_body(self, i: TradeIntent) -> dict[str, Any]:
        return {
            "dhanClientId": self.client_id, "correlationId": i.client_order_id, "transactionType": i.side,
            "exchangeSegment": i.exchange, "productType": i.product_type, "securityId": i.instrument_id,
            "quantity": i.qty,
        }

    def _submit(self, intent: TradeIntent, path: str, body: dict[str, Any], **kw: Any) -> Order:
        order = self.orders.get(intent.client_order_id)
        if order and not order.needs_lookup:  # idempotent: never send the same client order id twice
            return order
        if order and self._adopt(order):
            return order
        order = order or self._register(intent, **kw)
        try:
            resp = self._call("POST", path, body)
        except DhanApiError as exc:
            if exc.status_code is None:
                order.needs_lookup = True
                log.error("submit %s: no response from Dhan; next retry looks it up first", order.client_order_id)
                raise
            order.transition(OrderState.REJECTED, f"HTTP {exc.status_code} {exc.error_code or ''} {exc}")
            return order
        order.needs_lookup = False
        order.broker_order_id = str(resp.get("orderId") or "") or None
        status = resp.get("orderStatus")
        if STATUS.get(status) == OrderState.REJECTED:
            order.transition(OrderState.REJECTED, "dhan REJECTED")
        else:
            order.transition(OrderState.SUBMITTED, f"dhan {status}")
        return order

    def _adopt(self, order: Order) -> bool:
        """After a lost response: True if Dhan already has this correlationId (no resend)."""
        try:
            resp = self._call("GET", ORDER_BY_CORRELATION.format(correlation_id=order.client_order_id))
        except DhanApiError as exc:
            raise DhanApiError(
                f"cannot confirm whether {order.client_order_id} reached Dhan; not resending", status_code=exc.status_code
            ) from exc
        if not resp.get("orderId"):
            return False
        order.needs_lookup = False
        order.broker_order_id = str(resp["orderId"])
        order.transition(OrderState.SUBMITTED, "found at Dhan by correlationId after lost response")
        self._apply(order, resp)
        return True

    def modify_order(
        self, order: Order, decision: RiskDecision, *, price: Optional[float] = None,
        trigger_price: Optional[float] = None, target: Optional[float] = None,
        stop_loss: Optional[float] = None, trailing_jump: Optional[float] = None,
    ) -> Order:
        self._live_gate(decision, "MODIFY", order.client_order_id)
        oid = order.broker_order_id
        if not oid:
            raise ValueError(f"{order.client_order_id} has no Dhan orderId yet")
        head = {"dhanClientId": self.client_id, "orderId": oid}
        trail = trailing_jump if trailing_jump is not None else (order.trailing_jump or 0)
        if order.is_super:
            legs = []
            if price is not None and order.state in (OrderState.SUBMITTED, OrderState.PARTIAL):
                legs.append({"orderType": order.intent.order_type, "legName": "ENTRY_LEG", "quantity": order.intent.qty,
                             "price": float(price), "targetPrice": float(target or order.target),
                             "stopLossPrice": float(stop_loss or order.stop_loss), "trailingJump": float(trail)})
            else:
                if target is not None:
                    legs.append({"legName": "TARGET_LEG", "targetPrice": float(target)})
                if stop_loss is not None or trailing_jump is not None:
                    # Dhan cancels trailing if trailingJump is omitted or 0, so always resend it.
                    legs.append({"legName": "STOP_LOSS_LEG", "stopLossPrice": float(stop_loss or order.stop_loss),
                                 "trailingJump": float(trail)})
            if not legs:
                raise ValueError("nothing to modify")
            for leg in legs:
                self._call("PUT", SUPER_ORDER.format(order_id=oid), {**head, **leg})
        else:
            if not order.is_open:
                raise InvalidTransition(f"{order.client_order_id}: cannot modify a {order.state.value} order")
            kind = order.intent.order_type
            body = {**head, "orderType": ORDER_TYPES[kind], "legName": "", "quantity": order.intent.qty,
                    "price": float(price if price is not None else order.price or 0), "validity": "DAY"}
            if kind in ("SL", "SL-M"):
                body["triggerPrice"] = float(trigger_price if trigger_price is not None else order.trigger_price)
            self._call("PUT", ORDER.format(order_id=oid), body)
        for name, value in (("price", price), ("trigger_price", trigger_price), ("target", target),
                            ("stop_loss", stop_loss), ("trailing_jump", trailing_jump)):
            if value is not None:
                setattr(order, name, value)
        log.info("dhan modify %s sent", order.client_order_id)
        return order

    def cancel_order(self, order: Order, decision: RiskDecision, reason: str = "USER_CANCEL") -> Order:
        self._live_gate(decision, "CANCEL", order.client_order_id)
        oid = order.broker_order_id
        if not oid:
            raise ValueError(f"{order.client_order_id} has no Dhan orderId yet")
        path = SUPER_ORDER_LEG.format(order_id=oid, leg="ENTRY_LEG") if order.is_super else ORDER.format(order_id=oid)
        resp = self._call("DELETE", path)
        order.cancel_reason = reason
        if STATUS.get(resp.get("orderStatus")) == OrderState.CANCELLED and order.is_open:
            order.transition(OrderState.CANCELLED, reason)
        return order

    def flatten_all(self, decision: RiskDecision) -> dict[str, Any]:
        self._live_gate(decision, "FLATTEN", "FLATTEN_ALL")
        resp = self._call("DELETE", POSITIONS)
        if str(resp.get("status", "")).upper() != "SUCCESS":
            raise DhanApiError(f"exit-all failed: {resp.get('message')}")
        log.warning("FLATTEN ALL accepted by Dhan: %s", resp.get("message"))
        return resp

    # --------------------------------------------------- reads (no orders)

    def get_order_status(self, order: Order) -> Order:
        if order.broker_order_id:
            self._apply(order, self._call("GET", ORDER.format(order_id=order.broker_order_id)))
        return order

    def _apply(self, order: Order, resp: dict[str, Any]) -> None:
        filled = int(resp.get("filledQty") or 0)
        if filled > order.filled_qty:
            avg = float(resp.get("averageTradedPrice") or 0)
            delta = filled - order.filled_qty
            order.apply_fill(delta, round((avg * filled - (order.avg_fill_price or 0) * order.filled_qty) / delta, 4))
        state = STATUS.get(resp.get("orderStatus"))
        if state in (OrderState.CANCELLED, OrderState.EXPIRED, OrderState.REJECTED) and order.is_open:
            if state == OrderState.CANCELLED:
                order.cancel_reason = order.cancel_reason or "BROKER_CANCELLED"
            order.transition(state, f"dhan {resp.get('orderStatus')} {resp.get('omsErrorDescription') or ''}".strip())

    def get_positions(self) -> list[Position]:
        return [
            Position(symbol=r.get("tradingSymbol") or "", net_qty=int(r["netQty"]),
                     avg_price=float(r.get("buyAvg") or r.get("costPrice") or 0), instrument_id=str(r.get("securityId") or ""))
            for r in self._rows(self._call("GET", POSITIONS))
            if int(r.get("netQty") or 0) != 0
        ]

    def get_orders(self) -> list[OrderSnapshot]:
        return [
            OrderSnapshot(client_order_id=r.get("correlationId") or "", broker_order_id=str(r.get("orderId") or ""),
                          state=STATUS.get(r.get("orderStatus")), filled_qty=int(r.get("filledQty") or 0),
                          symbol=r.get("tradingSymbol") or "")
            for r in self._rows(self._call("GET", ORDERS))
        ]

    def get_balance(self) -> float:
        resp = self._call("GET", FUND_LIMIT)
        for key in ("availabelBalance", "availableBalance"):  # docs spell it "availabelBalance"
            if key in resp:
                return float(resp[key])
        raise DhanApiError("fundlimit response has no available balance field")
