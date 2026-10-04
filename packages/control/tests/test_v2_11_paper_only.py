"""paper only: DhanBroker never constructed; no network"""

from __future__ import annotations

from pathlib import Path

import pytest
from brokers.factory import LiveBrokerDisabled, make_broker
from contracts.clock import SimClock
from helpers import NOW

from control.flatten import paper_broker


def test_v2_11_paper_only_dhan_never_constructed() -> None:
    with pytest.raises(LiveBrokerDisabled):
        make_broker(mode="dhan", clock=SimClock(NOW))
    with pytest.raises(LiveBrokerDisabled):
        make_broker(mode="live", clock=SimClock(NOW))
    broker = paper_broker(SimClock(NOW))
    assert broker.mode == "paper" and broker.is_paper is True
    root = Path(__file__).resolve().parents[2]
    for path in root.joinpath("src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "DhanBroker(" not in text, path
        assert "from brokers.dhan" not in text, path
        assert "import brokers.dhan" not in text, path
