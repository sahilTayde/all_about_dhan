"""One test per risk check, plus fail-closed and reload-from-ledger."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from ledger import Ledger, load_rates
from risk_engine import LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE, RiskEngine, RiskState, TradeIntent

REPO = Path(__file__).resolve().parents[3]
BASE_CFG = yaml.safe_load((REPO / "config" / "risk_limits.yaml").read_text())
NOW = datetime.fromisoformat("2026-09-28T10:00:00+05:30")  # a Monday, inside entry hours


@pytest.fixture(autouse=True)
def no_live_env(monkeypatch):
    monkeypatch.delenv(LIVE_CONFIRM_ENV, raising=False)


@pytest.fixture
def engine(tmp_path):
    return make_engine(tmp_path)


def make_engine(tmp_path, ledger=None, **overrides):
    cfg = {**BASE_CFG, "kill_switch_file": str(tmp_path / "KILL_SWITCH"), **overrides}
    path = tmp_path / "risk_limits.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return RiskEngine(ledger=ledger, config_path=path)


def intent(lots=25, price=100.0, stop=97.0, **kw):
    # 25 lots x 65 = 1625 qty; risk (100-97)*1625 = ₹4,875 <= ₹5,000 paper max_loss_per_trade
    return TradeIntent(symbol="NIFTY 25000 CE", side="BUY", lots=lots, lot_size=65,
                       decision_price=price, stop_loss=stop, **kw)


def code(decision):
    return decision.reason_code


def test_paper_trade_within_limits_passes(engine):
    d = engine.check_entry(intent(), NOW, RiskState())
    assert d.approved and code(d) == "OK"


def test_max_lots_per_trade(engine):
    d = engine.check_entry(intent(lots=200, stop=99.99), NOW, RiskState())
    assert not d.approved and code(d) == "MAX_LOTS" and "25" in d.reason


@pytest.mark.parametrize("mode", ["limited_live", "live"])
def test_mode_gate_live_needs_founder_confirmation(tmp_path, monkeypatch, mode):
    eng = make_engine(tmp_path, mode=mode)
    small = intent(lots=1, stop=90.0)  # risk ₹650, inside every mode's limits
    assert code(eng.check_entry(small, NOW, RiskState())) == "MODE_NOT_ENABLED"
    monkeypatch.setenv(LIVE_CONFIRM_ENV, "yes")
    assert code(eng.check_entry(small, NOW, RiskState())) == "MODE_NOT_ENABLED"
    monkeypatch.setenv(LIVE_CONFIRM_ENV, LIVE_CONFIRM_VALUE)
    assert eng.check_entry(small, NOW, RiskState()).approved


def test_unknown_mode_fails_closed(tmp_path):
    d = make_engine(tmp_path, mode="yolo").check_entry(intent(), NOW, RiskState())
    assert not d.approved and code(d) == "ENGINE_ERROR" and d.critical


def test_kill_switch_flag_and_file(tmp_path):
    d = make_engine(tmp_path, kill_switch=True).check_entry(intent(), NOW, RiskState())
    assert code(d) == "KILL_SWITCH" and d.critical
    eng = make_engine(tmp_path)
    (tmp_path / "KILL_SWITCH").touch()
    assert code(eng.check_entry(intent(), NOW, RiskState())) == "KILL_SWITCH"


@pytest.mark.parametrize(
    "hhmmss,ok", [("09:14:59", False), ("09:15:00", True), ("14:59:59", True), ("15:00:00", False), ("15:25:00", False)]
)
def test_time_gates(engine, hhmmss, ok):
    now = datetime.fromisoformat(f"2026-09-28T{hhmmss}+05:30")
    d = engine.check_entry(intent(), now, RiskState())
    assert d.approved is ok and (ok or code(d) == "TIME_GATE")


def test_time_gate_uses_ist_even_for_utc_clock(engine):
    utc_1000_ist = datetime.fromisoformat("2026-09-28T04:30:00+00:00")
    assert engine.check_entry(intent(), utc_1000_ist, RiskState()).approved


def test_configurable_cutoff(tmp_path):
    eng = make_engine(tmp_path, entry_cutoff_ist="14:30")
    now = datetime.fromisoformat("2026-09-28T14:30:00+05:30")
    assert code(eng.check_entry(intent(), now, RiskState())) == "TIME_GATE"


def test_max_open_positions(engine):
    assert code(engine.check_entry(intent(), NOW, RiskState(open_positions=3))) == "MAX_OPEN_POSITIONS"
    assert engine.check_entry(intent(), NOW, RiskState(open_positions=2)).approved


def test_max_daily_loss_would_exceed(engine):
    # -₹14k today, new trade risks ₹2,000 (1 lot, 100 -> 69.23) -> would breach -₹15k
    d = engine.check_entry(intent(lots=1, stop=69.2), NOW, RiskState(realized_pnl_today=-14000))
    assert code(d) == "MAX_DAILY_LOSS" and not d.critical


def test_max_daily_loss_already_hit_is_critical(engine):
    d = engine.check_entry(intent(lots=1, stop=99.0), NOW, RiskState(realized_pnl_today=-15000))
    assert code(d) == "MAX_DAILY_LOSS" and d.critical


def test_max_loss_per_trade(engine):
    assert code(engine.check_entry(intent(stop=96.0), NOW, RiskState())) == "MAX_LOSS_PER_TRADE"  # ₹6,500
    # No stop on a long option: worst case is the whole premium.
    assert code(engine.check_entry(intent(lots=1, stop=None), NOW, RiskState())) == "MAX_LOSS_PER_TRADE"


def test_invalid_intent_without_price(engine):
    d = engine.check_entry(intent(price=None), NOW, RiskState())
    assert code(d) == "INVALID_INTENT"


def test_cooldown_after_losing_exit(engine):
    ten_min_ago = RiskState(last_loss_exit_at=NOW - timedelta(minutes=10))
    assert code(engine.check_entry(intent(), NOW, ten_min_ago)) == "COOLDOWN"
    sixteen = RiskState(last_loss_exit_at=NOW - timedelta(minutes=16))
    assert engine.check_entry(intent(), NOW, sixteen).approved


def test_idempotency_duplicate_intent(engine):
    first = intent()
    recent = RiskState(recent_fingerprints=[(NOW - timedelta(seconds=30), first.fingerprint)])
    assert code(engine.check_entry(intent(), NOW, recent)) == "DUPLICATE"
    old = RiskState(recent_fingerprints=[(NOW - timedelta(seconds=61), first.fingerprint)])
    assert engine.check_entry(intent(), NOW, old).approved
    same_id = RiskState(used_client_order_ids={first.client_order_id})
    assert code(engine.check_entry(first, NOW, same_id)) == "DUPLICATE"


def test_recon_mismatch_halts_entries(engine):
    d = engine.check_entry(intent(), NOW, RiskState(recon_ok=False))
    assert code(d) == "RECON_MISMATCH" and d.critical


def test_fail_closed_on_any_exception(tmp_path):
    class BrokenLedger:
        def risk_snapshot(self, *_):
            raise OSError("disk gone")

        def record_decision(self, _):
            pass

    d = make_engine(tmp_path, ledger=BrokenLedger()).check_entry(intent(), NOW)
    assert not d.approved and code(d) == "ENGINE_ERROR" and d.critical
    assert code(make_engine(tmp_path).check_entry(intent(), NOW)) == "ENGINE_ERROR"  # no ledger, no state
    missing = RiskEngine(config_path=tmp_path / "nope.yaml")
    assert code(missing.check_entry(intent(), NOW, RiskState())) == "ENGINE_ERROR"


def test_unrecorded_approval_is_vetoed(tmp_path):
    class ReadOnlyLedger(Ledger):
        def record_decision(self, _):
            raise OSError("read-only")

    led = ReadOnlyLedger(":memory:", rates=load_rates(REPO / "config" / "charges.yaml"))
    assert code(make_engine(tmp_path, ledger=led).check_entry(intent(), NOW)) == "ENGINE_ERROR"


def test_exits_allowed_under_kill_switch_and_after_cutoff(tmp_path):
    eng = make_engine(tmp_path, kill_switch=True)
    exit_intent = TradeIntent(symbol="NIFTY 25000 CE", side="SELL", lots=1, lot_size=65,
                              purpose="EXIT", exit_reason="KILL_SWITCH")
    late = datetime.fromisoformat("2026-09-28T15:20:00+05:30")
    assert eng.check_exit(exit_intent, now=late).approved
    assert eng.check_flatten(now=late).approved
    assert eng.check_exit(intent(), action="CANCEL", now=late).approved
    assert code(eng.check_exit(intent(), now=late)) == "INVALID_INTENT"  # EXIT needs purpose EXIT


def test_state_reloads_from_ledger_after_restart(tmp_path):
    rates = load_rates(REPO / "config" / "charges.yaml")
    path = tmp_path / "ledger.sqlite"
    led = Ledger(path, rates=rates)
    base = {"broker": "paper", "mode": "paper", "symbol": "NIFTY 25000 PE", "instrument_id": "1",
            "qty": 65, "order_type": "MARKET", "filled_qty": 0}
    led.record_order({**base, "client_order_id": "E1", "side": "BUY", "purpose": "ENTRY"}, "NEW", "SUBMITTED")
    led.record_fill("E1", 65, 100.0, NOW - timedelta(minutes=20))
    led.record_order({**base, "client_order_id": "X1", "side": "SELL", "purpose": "EXIT", "exit_reason": "STOP_HIT"},
                     "NEW", "SUBMITTED")
    led.record_fill("X1", 65, 90.0, NOW - timedelta(minutes=5))

    first = make_engine(tmp_path, ledger=led)
    assert code(first.check_entry(intent(), NOW)) == "COOLDOWN"
    approved = first.check_entry(intent(), NOW + timedelta(minutes=11))
    assert approved.approved
    led.close()

    restarted = make_engine(tmp_path, ledger=Ledger(path, rates=rates))  # new process, same file
    d = restarted.check_entry(intent(), NOW + timedelta(minutes=11, seconds=20))
    assert code(d) == "DUPLICATE"
    rows = restarted.ledger._all("SELECT reason_code, critical FROM risk_decisions ORDER BY id")
    assert [r["reason_code"] for r in rows] == ["COOLDOWN", "OK", "DUPLICATE"]
