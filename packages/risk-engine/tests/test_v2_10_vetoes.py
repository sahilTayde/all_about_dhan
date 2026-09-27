"""V2-10: FEED_STALE and STRATEGY_DAILY_LOSS inside the entry veto."""

from datetime import datetime
from pathlib import Path

from risk_engine import RiskState, TradeIntent

from test_risk_engine import make_engine

NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")


def _intent(**kw):
    return TradeIntent(
        symbol="NIFTY 25000 CE",
        side="BUY",
        lots=1,
        lot_size=65,
        decision_price=100.0,
        stop_loss=90.0,
        **kw,
    )


def test_feed_stale_vetoes_entry(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    d = engine.check_entry(_intent(), NOW, RiskState(feed_status="STALE"))
    assert not d.approved and d.reason_code == "FEED_STALE"
    d2 = engine.check_entry(_intent(), NOW, RiskState(feed_status="DOWN"))
    assert d2.reason_code == "FEED_STALE"
    ok = engine.check_entry(_intent(), NOW, RiskState(feed_status="UP"))
    assert ok.approved


def test_strategy_daily_loss_vetoes_entry(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    d = engine.check_entry(
        _intent(strategy_id="TEST-CROSS"),
        NOW,
        RiskState(strategy_pnl={"TEST-CROSS": -90000.0}),
    )
    assert not d.approved and d.reason_code == "STRATEGY_DAILY_LOSS"
    ok = engine.check_entry(
        _intent(strategy_id="TEST-CROSS"),
        NOW,
        RiskState(strategy_pnl={"TEST-CROSS": -1000.0}),
    )
    assert ok.approved


def test_halt_unreadable_blocks_entries_allows_exits(tmp_path: Path) -> None:
    engine = make_engine(tmp_path)
    d = engine.check_entry(_intent(), NOW, RiskState(halt_unreadable=True))
    assert not d.approved and d.reason_code == "HALT_UNREADABLE"
    exit_ok = engine.check_exit(
        TradeIntent(symbol="NIFTY 25000 CE", side="SELL", lots=1, lot_size=65, purpose="EXIT", exit_reason="STOP_HIT"),
        now=NOW,
    )
    assert exit_ok.approved
