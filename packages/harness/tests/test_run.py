"""Submit+cancel happy path on the mock broker. Marketable orders refused."""

from __future__ import annotations

import pytest

from harness.broker import MockOrderBroker, live_ctor_calls
from harness.gates import APPROVAL_ENV, APPROVAL_VALUE, HarnessRefused
from harness.order import (
    MAX_OFF_MARKET_LIMIT,
    HarnessOrderError,
    OffMarketIntent,
    default_intent,
    validate_off_market,
)
from harness.run import run_shadow_test

_OK = {
    APPROVAL_ENV: APPROVAL_VALUE,
    "DHAN_CLIENT_ID": "test-client",
    "DHAN_ACCESS_TOKEN": "test-token",
}


def test_submit_cancel_happy_path_on_mock() -> None:
    before = live_ctor_calls()
    broker = MockOrderBroker()
    result = run_shadow_test(mode="shadow", env=_OK, broker=broker, intent=default_intent())
    assert result.ok is True
    assert result.submitted == 1
    assert result.cancelled == 1
    assert result.fills == 0
    assert result.transport == "mock"
    assert result.states == ("ACKNOWLEDGED->CANCELLED",)
    assert len(broker.placed) == 1
    assert broker.placed[0].order_type == "LIMIT"
    assert broker.placed[0].limit_price <= MAX_OFF_MARKET_LIMIT
    assert broker.cancelled == ["5001"]
    assert live_ctor_calls() == before


def test_happy_path_five_cycles() -> None:
    broker = MockOrderBroker()
    result = run_shadow_test(mode="harness", env=_OK, broker=broker, count=5)
    assert result.submitted == 5 and result.cancelled == 5 and result.fills == 0
    assert len(result.client_order_ids) == 5
    assert len(set(result.client_order_ids)) == 5


def test_run_refuses_without_approval() -> None:
    broker = MockOrderBroker()
    with pytest.raises(HarnessRefused) as info:
        run_shadow_test(
            mode="shadow",
            env={"DHAN_CLIENT_ID": "x", "DHAN_ACCESS_TOKEN": "y"},
            broker=broker,
        )
    assert info.value.reason_code == "APPROVAL_MISSING"
    assert broker.placed == []


def test_run_refuses_without_credentials() -> None:
    broker = MockOrderBroker()
    with pytest.raises(HarnessRefused) as info:
        run_shadow_test(mode="shadow", env={APPROVAL_ENV: APPROVAL_VALUE}, broker=broker)
    assert info.value.reason_code == "CREDENTIALS_MISSING"
    assert broker.placed == []


def test_marketable_limit_refused() -> None:
    with pytest.raises(HarnessOrderError, match="off-market cap"):
        validate_off_market(
            OffMarketIntent(symbol="NIFTY CE", security_id="TEST", limit_price=50.0)
        )


def test_market_order_refused() -> None:
    with pytest.raises(HarnessOrderError, match="LIMIT"):
        validate_off_market(
            OffMarketIntent(symbol="NIFTY CE", security_id="TEST", order_type="MARKET")
        )


def test_sell_refused() -> None:
    with pytest.raises(HarnessOrderError, match="BUY"):
        validate_off_market(OffMarketIntent(symbol="NIFTY CE", security_id="TEST", side="SELL"))


def test_injected_live_broker_refused() -> None:
    class _Live:
        name = "fake-live"
        is_live = True

        def place_limit(self, intent: object) -> object:
            raise AssertionError("must not place")

        def cancel(self, broker_order_id: str) -> object:
            raise AssertionError("must not cancel")

    with pytest.raises(HarnessOrderError, match="must not be live"):
        run_shadow_test(mode="shadow", env=_OK, broker=_Live())  # type: ignore[arg-type]


def test_fill_on_submit_is_failure() -> None:
    broker = MockOrderBroker()
    intent = default_intent()
    broker.fills[intent.client_order_id] = 1
    # run_shadow_test mints a new client_order_id; force fill on every id
    broker.fills = _FillAll()
    with pytest.raises(HarnessOrderError, match="filled"):
        run_shadow_test(mode="shadow", env=_OK, broker=broker, intent=intent)


class _FillAll(dict[str, int]):  # type: ignore[type-arg]
    def get(self, key: str, default: int = 0) -> int:  # type: ignore[override]
        return 1
