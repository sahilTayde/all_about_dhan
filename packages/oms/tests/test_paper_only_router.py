"""OrderRouter refuses a live-like or unmarked broker at the constructor boundary."""

from __future__ import annotations

import pytest
from brokers.factory import LiveBrokerDisabled, make_broker
from contracts.clock import SimClock
from helpers import NOW, make_decision, make_plan, make_router, write_risk_cfg
from risk_engine import V2RiskEngine

from oms import Account, MemoryLedger, Veto
from oms.router import OrderRouter, is_paper_desk_broker, require_paper_broker


class FakeLiveBroker:
    """Live-like name/mode; must never receive a place_order."""

    name = "dhan"
    mode = "live"
    is_paper = False
    placed = False

    def __init__(self) -> None:
        self.orders: dict[str, object] = {}

    def place_order(self, intent: object, decision: object) -> object:
        self.placed = True
        raise AssertionError("live-like broker must not receive place_order")


class DuckNoMarker:
    """Paper-shaped duck type without the is_paper marker."""

    name = "paper"
    mode = "paper"

    def __init__(self) -> None:
        self.orders: dict[str, object] = {}

    def place_order(self, intent: object, decision: object) -> object:
        raise AssertionError("unmarked duck broker must not receive place_order")


def test_fake_live_like_broker_is_refused(tmp_path: object) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, config_path=write_risk_cfg(tmp_path))  # type: ignore[arg-type]
    fake = FakeLiveBroker()
    with pytest.raises(LiveBrokerDisabled):
        OrderRouter(clock=clock, risk=risk, broker=fake, store=store)  # type: ignore[arg-type]
    assert fake.placed is False
    with pytest.raises(LiveBrokerDisabled):
        require_paper_broker(fake)


def test_duck_typed_object_without_marker_is_refused(tmp_path: object) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, config_path=write_risk_cfg(tmp_path))  # type: ignore[arg-type]
    duck = DuckNoMarker()
    assert is_paper_desk_broker(duck) is False
    with pytest.raises(LiveBrokerDisabled):
        OrderRouter(clock=clock, risk=risk, broker=duck, store=store)  # type: ignore[arg-type]


def test_default_paper_broker_still_works(tmp_path: object) -> None:
    clock = SimClock(NOW)
    router = make_router(tmp_path, clock)  # type: ignore[arg-type]
    assert is_paper_desk_broker(router.broker) is True
    assert router.broker.mode == "paper"
    assert router.broker.is_paper is True
    out = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(out, Veto)
    built = make_broker(clock=clock)
    assert is_paper_desk_broker(built) is True
    again = make_router(tmp_path, clock, broker=built)  # type: ignore[arg-type]
    assert again.broker is built
