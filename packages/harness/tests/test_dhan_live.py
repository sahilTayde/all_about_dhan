"""Live adapter payload tests use a fake REST client. No network."""

from __future__ import annotations

from typing import Any

import pytest

from harness.broker import live_ctor_calls
from harness.dhan_live import DhanLiveBroker
from harness.order import HarnessOrderError, default_intent


class FakeRest:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []
        self.response: dict[str, Any] = {"orderId": "5001", "orderStatus": "PENDING"}

    def request(self, method: str, path: str, *, json_body: object | None = None) -> dict[str, Any]:
        self.calls.append((method, path, json_body))
        return dict(self.response)


def test_live_broker_posts_limit_and_deletes(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = monkeypatch
    before = live_ctor_calls()
    rest = FakeRest()
    broker = DhanLiveBroker(rest, client_id="test-client")
    assert broker.is_live is True
    ack = broker.place_limit(default_intent(security_id="43210"))
    assert ack.broker_order_id == "5001"
    assert ack.filled_qty == 0
    method, path, body = rest.calls[0]
    assert method == "POST" and path == "/orders"
    assert isinstance(body, dict)
    assert body["orderType"] == "LIMIT"
    assert body["transactionType"] == "BUY"
    assert body["price"] == 1.0
    assert body["afterMarketOrder"] is False
    assert "MARKET" not in str(body)
    rest.response = {"orderStatus": "CANCELLED"}
    cancel = broker.cancel(ack.broker_order_id)
    assert cancel.state == "CANCELLED"
    assert rest.calls[1][:2] == ("DELETE", "/orders/5001")
    assert live_ctor_calls() == before + 1


def test_live_broker_refuses_dry_run_envelope() -> None:
    rest = FakeRest()
    rest.response = {"status": "dry_run", "note": "No HTTP call"}
    broker = DhanLiveBroker(rest, client_id="test-client")
    with pytest.raises(HarnessOrderError, match="dry-run"):
        broker.place_limit(default_intent())


def test_live_broker_refuses_fill_status() -> None:
    rest = FakeRest()
    rest.response = {"orderId": "9", "orderStatus": "TRADED"}
    broker = DhanLiveBroker(rest, client_id="test-client")
    with pytest.raises(HarnessOrderError, match="fill"):
        broker.place_limit(default_intent())
