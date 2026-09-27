"""REG-04: pending entry plans rebuild without duplicates (V2-08b)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from contracts.clock import SimClock
from helpers import NOW, SpyBroker, make_decision, make_router, quote_at, write_entry_cfg

from oms.planner import REPO_CHASE_YAML, EntryConfigStore, OrderPlanner


def test_reg_04_rebuild_does_not_duplicate_sent_plan(tmp_path: Path) -> None:
    entry = write_entry_cfg(
        tmp_path,
        default_entry_policy="pullback_limit",
        pullback_limit={"enabled": True, "limit_timeout_s": 60},
    )
    clock = SimClock(NOW)
    spy = SpyBroker(clock=clock)
    router = make_router(tmp_path, clock, broker=spy)
    cfg = EntryConfigStore(entry, chase_path=REPO_CHASE_YAML)
    planner = OrderPlanner(clock=clock, router=router, store=router.store, config_store=cfg)
    plan = planner.accept(make_decision(limit_price=144.10), bar_close_ts=NOW - timedelta(seconds=1))
    assert plan is not None
    planner.on_quote(quote_at(NOW, 151.35))
    revived = OrderPlanner(clock=clock, router=router, store=router.store, config_store=cfg)
    assert revived.rebuild() == 1
    assert revived.rebuild() == 0
    revived.accept(make_decision(limit_price=144.10), bar_close_ts=NOW)
    revived.on_quote(quote_at(NOW, 151.40))
    assert spy.place_calls == 1
