"""REG-05a/b/c: caps in the veto, missing key fails closed, kill switch."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from contracts.clock import SimClock
from helpers import NOW, make_decision, make_plan, make_router, write_risk_cfg
from oms import Account, MemoryLedger, Veto
from risk_engine import RiskState, TradeIntent, V2RiskEngine


def _intent(*, lots: int, price: float, stop: float, lot_size: int = 65) -> TradeIntent:
    return TradeIntent(
        symbol="NIFTY 24400 CE",
        side="BUY",
        lots=lots,
        lot_size=lot_size,
        decision_price=price,
        stop_loss=stop,
    )


def test_reg_05a_cap_table(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    risk = V2RiskEngine(ledger=store, config_path=write_risk_cfg(tmp_path))
    # max lots 25
    lots_over = risk.check_entry(
        _intent(lots=26, price=100.0, stop=99.0), now=NOW, state=RiskState()
    )
    assert lots_over.reason_code == "MAX_LOTS"
    # max loss per trade ₹30k: (100-50)*25*65 = 81,250
    loss = risk.check_entry(
        _intent(lots=25, price=100.0, stop=50.0), now=NOW, state=RiskState()
    )
    assert loss.reason_code == "MAX_LOSS_PER_TRADE"
    # would-cross daily cap: realized -80k, ticket risk 15k → would exceed 90k
    st = RiskState(realized_pnl_today=-80000.0)
    d = risk.check_entry(_intent(lots=25, price=100.0, stop=90.0), now=NOW, state=st)
    assert d.reason_code == "MAX_DAILY_LOSS"
    # max open positions 3
    st = RiskState(open_positions=3)
    open_cap = risk.check_entry(
        _intent(lots=1, price=100.0, stop=90.0), now=NOW, state=st
    )
    assert open_cap.reason_code == "MAX_OPEN_POSITIONS"
    ok = risk.check_entry(
        _intent(lots=2, price=100.0, stop=97.0), now=NOW, state=RiskState()
    )
    assert ok.approved
    _ = clock


def test_reg_05b_missing_cap_key_fails_validation(tmp_path: Path) -> None:
    src = Path(__file__).resolve().parents[2] / "config" / "risk_limits.yaml"
    raw = yaml.safe_load(src.read_text())
    del raw["modes"]["paper"]["max_lots_per_trade"]
    path = tmp_path / "risk_limits.yaml"
    path.write_text(yaml.safe_dump(raw))
    risk = V2RiskEngine(ledger=MemoryLedger(), config_path=path)
    d = risk.check_entry(
        _intent(lots=1, price=100.0, stop=90.0), now=NOW, state=RiskState()
    )
    assert not d.approved
    assert d.reason_code in ("CONFIG_INVALID", "ENGINE_ERROR")


def test_reg_05c_kill_switch_vetoes_entry_allows_exit(tmp_path: Path) -> None:
    clock = SimClock(NOW)
    store = MemoryLedger()
    cfg = write_risk_cfg(tmp_path)
    risk = V2RiskEngine(ledger=store, config_path=cfg)
    router = make_router(tmp_path, clock, store=store, risk=risk)
    first = router.submit(make_plan(), make_decision(), Account("founder"))
    assert not isinstance(first, Veto)
    cfg_on = write_risk_cfg(tmp_path, kill_switch=True)
    risk_on = V2RiskEngine(ledger=store, config_path=cfg_on)
    router_on = make_router(
        tmp_path, clock, store=store, risk=risk_on, broker=router.broker
    )
    # new signal id so order_id differs
    blocked = router_on.submit(
        make_plan(signal_id="sg_other_nifty_20260928_1002_0"),
        make_decision(lots=3),
        Account("founder"),
    )
    assert isinstance(blocked, Veto) and blocked.reason_code == "KILL_SWITCH"
    intent = _intent(lots=2, price=151.4, stop=140.0)
    # exits still allowed
    from dataclasses import replace

    exit_i = replace(
        intent, purpose="EXIT", side="SELL", client_order_id="aad" + "e" * 24
    )
    assert risk_on.check_exit(exit_i, "EXIT", now=NOW).approved
    _ = datetime
