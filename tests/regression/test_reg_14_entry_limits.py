"""REG-14 via the planner: a resting pullback limit fills only on a trade-through."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import yaml
from brokers.fills import Quote, limit_fill_price
from contracts.clock import SimClock
from helpers import INST, NOW, SIG, REPO, make_decision, make_router

from oms import Account, CardPolicy
from oms.planner import OrderPlanner, load_entry_config

BAR_CLOSE = NOW - timedelta(seconds=1)


def test_reg_14_planner_pullback_limit_fills_at_limit_on_trade_through(tmp_path: Path) -> None:
    entry = yaml.safe_load((REPO / "config/v2/entry_location.yaml").read_text())
    chase = yaml.safe_load((REPO / "config/v2/entry/chase_defaults.yaml").read_text())
    entry["pullback_limit"] = {"enabled": True, "limit_timeout_s": 30.0}
    epath = tmp_path / "entry_location.yaml"
    cpath = tmp_path / "chase_defaults.yaml"
    epath.write_text(yaml.safe_dump(entry))
    cpath.write_text(yaml.safe_dump(chase))
    clock = SimClock(NOW)
    planner = OrderPlanner(
        clock=clock,
        router=make_router(tmp_path, clock),
        config=load_entry_config(epath, cpath),
    )
    planner.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="pullback_limit"),
        zone_price=144.10,
    )
    planner.on_quote(Quote(clock.now(), 151.00, 151.20, 151.10, INST))
    order = next(iter(planner.router.broker.orders.values()))
    clock.advance_by(timedelta(milliseconds=200))
    planner.on_quote(Quote(clock.now(), 144.10, 144.20, 144.10, INST))
    assert order.state.value != "FILLED"
    assert limit_fill_price(144.10, 144.10, "BUY") is None
    clock.advance_by(timedelta(milliseconds=200))
    planner.on_quote(Quote(clock.now(), 143.90, 144.00, 144.00, INST))
    assert order.state.value == "FILLED"
    assert order.avg_fill_price == 144.10
