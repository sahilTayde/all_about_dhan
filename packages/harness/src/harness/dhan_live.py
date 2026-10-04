"""Live Dhan transport. Imported only after gates + ``--transport dhan``. Not the desk live gate."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from harness.broker import CancelAck, OrderAck, note_live_ctor
from harness.gates import ACCESS_TOKEN_ENV, CLIENT_ID_ENV, HarnessRefused
from harness.order import HarnessOrderError, OffMarketIntent, validate_off_market

# Paths from Dhan v2 orders docs (same mapping as packages/brokers DhanBroker; no live gate here).
_ORDERS = "/orders"
_ORDER = "/orders/{order_id}"


class RestLike(Protocol):
    def request(
        self, method: str, path: str, *, json_body: object | None = None
    ) -> dict[str, Any]: ...


class DhanLiveBroker:
    """LIMIT submit + cancel only. No MARKET, super, flatten, or modify."""

    name = "dhan-shadow-harness"
    is_live = True

    def __init__(self, rest: RestLike, *, client_id: str) -> None:
        note_live_ctor()
        self._rest = rest
        self._client_id = client_id

    def place_limit(self, intent: OffMarketIntent) -> OrderAck:
        clean = validate_off_market(intent)
        body = {
            "dhanClientId": self._client_id,
            "correlationId": clean.client_order_id,
            "transactionType": "BUY",
            "exchangeSegment": clean.exchange,
            "productType": clean.product_type,
            "securityId": clean.security_id,
            "quantity": clean.qty,
            "orderType": "LIMIT",
            "validity": "DAY",
            "afterMarketOrder": False,
            "price": float(clean.limit_price),
        }
        resp = _call(self._rest, "POST", _ORDERS, body)
        oid = str(resp.get("orderId") or "")
        if not oid:
            raise HarnessOrderError("submit returned no order id")
        status = str(resp.get("orderStatus") or "ACKNOWLEDGED")
        if status.upper() in {"TRADED", "CLOSED"}:
            raise HarnessOrderError("submit reported a fill; off-market LIMIT must not fill")
        return OrderAck(clean.client_order_id, oid, "ACKNOWLEDGED", filled_qty=0)

    def cancel(self, broker_order_id: str) -> CancelAck:
        if not broker_order_id:
            raise HarnessOrderError("cancel needs a broker_order_id")
        resp = _call(self._rest, "DELETE", _ORDER.format(order_id=broker_order_id), None)
        status = str(resp.get("orderStatus") or "CANCELLED")
        if status.upper() in {"TRADED", "CLOSED"}:
            raise HarnessOrderError("cancel reported a fill")
        return CancelAck(broker_order_id, "CANCELLED", filled_qty=0)


def build_dhan_live_broker(env: Mapping[str, str]) -> DhanLiveBroker:
    """Construct the live REST client. Caller must already have passed gates."""
    client_id = (env.get(CLIENT_ID_ENV) or "").strip()
    token = (env.get(ACCESS_TOKEN_ENV) or "").strip()
    if not client_id or not token:
        raise HarnessRefused(
            "CREDENTIALS_MISSING",
            f"{CLIENT_ID_ENV} and {ACCESS_TOKEN_ENV} are required; values are not logged",
        )
    from dhan_client.config import Credentials, Settings
    from dhan_client.rest import RestClient

    settings = Settings(
        credentials=Credentials(client_id=client_id, access_token=token),
        dry_run=False,
    )
    return DhanLiveBroker(RestClient(settings), client_id=client_id)


def _call(rest: RestLike, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
    try:
        resp = rest.request(method, path, json_body=body)
    except Exception as exc:
        raise HarnessOrderError(f"Dhan {method} {path} failed ({type(exc).__name__})") from None
    if not isinstance(resp, dict):
        raise HarnessOrderError("Dhan response was not an object")
    if resp.get("status") == "dry_run":
        raise HarnessOrderError("dry-run envelope; no Dhan call was made")
    return resp
