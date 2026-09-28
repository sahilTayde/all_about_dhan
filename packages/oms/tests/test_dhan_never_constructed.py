"""DhanBroker is never constructed on the V2 path. Live cannot be enabled from tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from brokers.factory import LiveBrokerDisabled, live_brokers_enabled, make_broker
from contracts.clock import SimClock
from helpers import NOW
from risk_engine import LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE


def test_live_brokers_flag_is_hard_false() -> None:
    assert live_brokers_enabled() is False


@pytest.mark.parametrize("mode", ["live", "limited_live", "shadow", "dhan"])
def test_make_broker_refuses_non_paper(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)
    with pytest.raises(LiveBrokerDisabled):
        make_broker(mode=mode, clock=SimClock(NOW))


def test_make_broker_rejects_legacy_cost_model() -> None:
    with pytest.raises(LiveBrokerDisabled):
        make_broker(mode="paper", clock=SimClock(NOW), cost_model="legacy")


def test_v2_sources_never_construct_dhan() -> None:
    root = Path(__file__).resolve().parents[3]
    v2_files = [
        *root.joinpath("packages/oms/src").rglob("*.py"),
        root.joinpath("packages/brokers/src/brokers/fills.py"),
        root.joinpath("packages/brokers/src/brokers/factory.py"),
        root.joinpath("packages/risk-engine/src/risk_engine/last_good.py"),
    ]
    for path in v2_files:
        text = path.read_text(encoding="utf-8")
        assert "DhanBroker(" not in text, path
        assert "from brokers.dhan" not in text, path
        assert "import brokers.dhan" not in text, path


def test_importing_oms_does_not_import_dhan() -> None:
    import brokers.factory
    import brokers.fills

    import oms  # noqa: F401

    assert getattr(brokers.factory, "DhanBroker", None) is None
    assert getattr(brokers.fills, "DhanBroker", None) is None
