"""REG-16a/b: malformed cost config fails closed; last-good rates; no crash."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from brokers.factory import make_broker
from brokers.fills import Quote
from contracts.clock import SimClock
from helpers import INST, NOW, REPO, make_decision, make_plan, make_router
from oms import Account, MemoryLedger, Veto
from oms.router import load_cost_rates


def test_reg_16a_bad_charges_at_start_exits_only_no_crash(tmp_path: Path) -> None:
    bad = tmp_path / "charges.yaml"
    bad.write_text("brokerage_per_order_inr: 20\n")  # missing keys
    bus_alerts: list[str] = []

    class _Bus:
        def publish(
            self, typ: str, payload: dict[str, object], source: str = ""
        ) -> None:
            bus_alerts.append(str(payload.get("reason_code")))

    rates = load_cost_rates(bad, bus=_Bus())
    assert rates.exits_only is True
    assert rates.get() is None
    assert "CONFIG_INVALID" in bus_alerts
    clock = SimClock(NOW)
    store = MemoryLedger()
    router = make_router(tmp_path, clock, store=store, rates=rates)
    out = router.submit(make_plan(), make_decision(), Account("founder"))
    assert isinstance(out, Veto)
    assert out.reason_code == "CONFIG_INVALID"


def test_reg_16b_mid_session_keeps_last_good_and_blocks_entries(tmp_path: Path) -> None:
    good = tmp_path / "charges.yaml"
    good.write_text((REPO / "config" / "charges.yaml").read_text())
    rates = load_cost_rates(good)
    assert rates.last is not None and rates.exits_only is False
    clock = SimClock(NOW)
    store = MemoryLedger()
    broker = make_broker(clock=clock)
    router = make_router(tmp_path, clock, broker=broker, store=store, rates=rates)
    first = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(first, Veto)
    clock.advance_by(timedelta(milliseconds=250))
    broker.on_depth(
        Quote(
            available_ts=clock.now(),
            bid=151.00,
            ask=151.20,
            ltp=151.10,
            instrument_id=INST,
        )
    )
    assert store.charges[0].charges_status == "FINAL"
    last_good_nse = rates.last["exchange_txn_frac_by_exchange"]["NSE"]
    good.write_text("not: [valid")
    assert rates.get() is not None  # last-good
    assert rates.entries_blocked is True
    assert rates.last["exchange_txn_frac_by_exchange"]["NSE"] == last_good_nse
    second = router.submit(
        make_plan(signal_id="sg_later_nifty_20260928_1003_0"),
        make_decision(),
        Account("founder"),
    )
    assert isinstance(second, Veto)
    assert second.reason_code == "CONFIG_INVALID"
    # exit still charged at last-good (store.rates stays last-good)
    router._sync_rates()
    assert store.rates is not None
    assert store.rates["exchange_txn_frac_by_exchange"]["NSE"] == last_good_nse


def test_reg_16_pending_when_no_rates(tmp_path: Path) -> None:
    """V2-10 owns recharge; stub records PENDING, never zero."""
    store = MemoryLedger()
    store.rates = None
    row = store.record_fill(
        "aad" + "p" * 24,
        65,
        100.0,
        fill_model="fcmeas",
        side="BUY",
        symbol="NIFTY 24400 CE",
    )
    assert row.charges_status == "PENDING"
    assert row.components == {}
    assert row.components.get("total", None) != 0.0
