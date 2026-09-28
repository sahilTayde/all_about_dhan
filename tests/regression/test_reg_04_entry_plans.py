"""REG-04: kill -9 with a pending limit recovers the plan and never duplicates."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from brokers.fills import Quote
from contracts.clock import SimClock
from helpers import INST, NOW, REPO, SIG, make_decision, make_router
from ledger.v2 import SqliteLedgerStore
from oms import Account, CardPolicy
from oms.planner import OrderPlanner, load_entry_config

BAR_CLOSE = NOW - timedelta(seconds=1)


@pytest.mark.parametrize("store_kind", ["memory", "sqlite"])
def test_reg_04_restart_rebuilds_pending_plans_without_duplicates(
    tmp_path: Path, store_kind: str
) -> None:
    entry = yaml.safe_load((REPO / "config/v2/entry_location.yaml").read_text())
    chase = yaml.safe_load((REPO / "config/v2/entry/chase_defaults.yaml").read_text())
    entry["pullback_limit"] = {"enabled": True, "limit_timeout_s": 30.0}
    epath = tmp_path / "entry_location.yaml"
    cpath = tmp_path / "chase_defaults.yaml"
    epath.write_text(yaml.safe_dump(entry))
    cpath.write_text(yaml.safe_dump(chase))
    cfg = load_entry_config(epath, cpath)
    clock = SimClock(NOW)
    store = (
        SqliteLedgerStore(tmp_path / "aad.sqlite", migrate_schema=True)
        if store_kind == "sqlite"
        else make_router(tmp_path, clock).store
    )
    first = OrderPlanner(
        clock=clock,
        router=make_router(tmp_path, clock, store=store),
        config=cfg,
        store=store,
    )
    first.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="pullback_limit"),
        zone_price=144.10,
    )
    first.on_quote(Quote(clock.now(), 151.00, 151.20, 151.10, INST))
    assert len(store.entry_plans) == 1
    assert len(first.router.broker.orders) == 1
    first_oid = next(iter(first.router.broker.orders))
    pid = next(iter(store.entry_plans))
    status = store.entry_plans[pid]["status"]
    assert status == "WORKING"

    # kill -9: new planner, same durable store, new paper broker
    clock2 = SimClock(clock.now())
    revived = OrderPlanner(
        clock=clock2,
        router=make_router(tmp_path, clock2, store=store),
        config=cfg,
        store=store,
    )
    submits = {"n": 0}
    orig = revived.router.submit

    def _count(*a, **k):  # type: ignore[no-untyped-def]
        submits["n"] += 1
        return orig(*a, **k)

    revived.router.submit = _count  # type: ignore[method-assign]
    revived.rebuild()
    revived.on_decision(
        make_decision(),
        account=Account("founder"),
        signal_id=SIG,
        bar_close_ts=BAR_CLOSE,
        policy=CardPolicy(mode="pullback_limit"),
        zone_price=144.10,
    )
    revived.on_quote(Quote(clock2.now(), 151.00, 151.20, 151.10, INST))
    assert len(store.entry_plans) == 1
    assert list(store.entry_plans) == [pid]
    assert submits["n"] == 0
    assert list(revived.router.broker.orders) == [first_oid]
