"""Ledger: trade lifecycle, slippage, charges, daily P&L, append-only, reload."""

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from ledger import Ledger, load_rates

RATES = load_rates(Path(__file__).resolve().parents[3] / "config" / "charges.yaml")
DAY = "2026-09-28"


def at(hhmm: str) -> datetime:
    return datetime.fromisoformat(f"{DAY}T{hhmm}:00+05:30")


def order(cid, side, qty, *, purpose="ENTRY", decision_price=None, exit_reason=None, symbol="NIFTY-CE", **kw):
    row = {
        "client_order_id": cid, "broker": "paper", "mode": "paper", "symbol": symbol, "instrument_id": "123",
        "side": side, "qty": qty, "order_type": "MARKET", "decision_price": decision_price,
        "purpose": purpose, "filled_qty": 0, "exit_reason": exit_reason,
    }
    row.update(kw)
    return row


def submit(led, row, ts):
    led.record_order(row, "NEW", "SUBMITTED", "test", ts)


@pytest.fixture
def led():
    ledger = Ledger(":memory:", rates=RATES)
    yield ledger
    ledger.close()


def test_round_trip_trade_net_after_charges_and_slippage(led):
    submit(led, order("E1", "BUY", 65, decision_price=99.5), at("10:00"))
    trade_id = led.record_fill("E1", 65, 100.0, at("10:00"))
    assert led.open_positions()[0]["net_qty"] == 65

    submit(led, order("X1", "SELL", 65, purpose="EXIT", decision_price=130.5, exit_reason="TARGET_HIT"), at("10:20"))
    assert led.record_fill("X1", 65, 130.0, at("10:20")) == trade_id

    t = led.trade(trade_id)
    assert t["status"] == "CLOSED" and t["exit_reason"] == "TARGET_HIT"
    assert (t["entry_price"], t["exit_price"]) == (100.0, 130.0)
    assert t["entry_slippage"] == 0.5    # paid 100 vs decided 99.5
    assert t["exit_slippage"] == -0.5    # got 130 vs decided 130.5
    assert t["gross_pnl"] == 1950.0
    assert t["charges"] == 66.28         # see test_charges.test_hand_computed_round_trip
    assert t["net_pnl"] == 1883.72
    assert led.open_positions() == []
    assert led.daily_pnl(DAY) == {"day": DAY, "n_trades": 1, "gross_pnl": 1950.0, "charges": 66.28, "net_pnl": 1883.72}


def test_partial_fills_charge_brokerage_once_per_order(led):
    submit(led, order("E1", "BUY", 130), at("10:00"))
    trade_id = led.record_fill("E1", 65, 100.0, at("10:00"))
    led.record_fill("E1", 65, 101.0, at("10:00"))
    rows = led.charges_for(trade_id)
    assert [r["brokerage"] for r in rows] == [20.0, 0.0]
    t = led.trade(trade_id)
    assert t["entry_qty"] == 130 and t["entry_price"] == 100.5
    assert led.open_positions()[0]["avg_price"] == 100.5


def test_daily_pnl_sums_trades_net_of_charges(led):
    for i, (buy, sell) in enumerate([(100.0, 130.0), (100.0, 90.0)]):
        submit(led, order(f"E{i}", "BUY", 65), at("10:00"))
        led.record_fill(f"E{i}", 65, buy, at("10:00"))
        submit(led, order(f"X{i}", "SELL", 65, purpose="EXIT", exit_reason="STOP_HIT"), at("10:30"))
        led.record_fill(f"X{i}", 65, sell, at("10:30"))
    trades = led.trades(DAY)
    day = led.daily_pnl(DAY)
    assert day["n_trades"] == 2
    assert day["gross_pnl"] == 1950.0 - 650.0
    assert day["charges"] == round(sum(t["charges"] for t in trades), 2)
    assert day["net_pnl"] == round(day["gross_pnl"] - day["charges"], 2)


def test_cancelled_entry_is_a_trade_row_with_cancel_reason(led):
    row = order("E1", "BUY", 65)
    submit(led, row, at("10:00"))
    with pytest.raises(ValueError):
        led.record_order(row, "SUBMITTED", "CANCELLED", "no reason", at("10:05"))
    led.record_order({**row, "cancel_reason": "TIMEOUT_UNFILLED"}, "SUBMITTED", "CANCELLED", "unfilled", at("10:05"))
    (t,) = led.trades(DAY)
    assert t["status"] == "CANCELLED" and t["cancel_reason"] == "TIMEOUT_UNFILLED" and t["net_pnl"] == 0
    assert [e["to_state"] for e in led.order_events("E1")] == ["SUBMITTED", "CANCELLED"]


def test_unknown_exit_reason_rejected(led):
    with pytest.raises(ValueError):
        submit(led, order("X1", "SELL", 65, purpose="EXIT", exit_reason="FELT_LIKE_IT"), at("10:00"))


def test_ledger_is_append_only(led):
    submit(led, order("E1", "BUY", 65), at("10:00"))
    led.record_fill("E1", 65, 100.0, at("10:00"))
    for sql in ("DELETE FROM fills", "UPDATE fills SET price = 1", "DELETE FROM orders", "DELETE FROM charges"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            led.conn.execute(sql)


def test_state_survives_restart(tmp_path):
    path = tmp_path / "ledger.sqlite"
    first = Ledger(path, rates=RATES)
    submit(first, order("E1", "BUY", 65), at("10:00"))
    first.record_fill("E1", 65, 100.0, at("10:00"))
    submit(first, order("X1", "SELL", 65, purpose="EXIT", exit_reason="STOP_HIT"), at("10:10"))
    first.record_fill("X1", 65, 80.0, at("10:10"))
    submit(first, order("E2", "BUY", 65, symbol="NIFTY-PE"), at("10:30"))
    first.record_fill("E2", 65, 50.0, at("10:30"))
    first.record_decision({"ts": at("10:30"), "client_order_id": "E2", "fingerprint": "NIFTY-PE|BUY|1",
                           "action": "ENTRY", "approved": True, "reason_code": "OK"})
    first.record_recon([{"kind": "ORPHAN_BROKER"}], at("10:31"))
    first.close()

    snap = Ledger(path, rates=RATES).risk_snapshot(at("10:30").replace(second=30), idempotency_seconds=60)
    assert snap["open_positions"] == 1
    assert snap["realized_pnl_today"] < -1300          # -1300 gross minus charges
    assert snap["last_loss_exit_at"] == at("10:10")
    assert snap["recent_fingerprints"] == [(at("10:30"), "NIFTY-PE|BUY|1")]
    assert snap["used_client_order_ids"] == {"E2"}
    assert snap["recon_ok"] is False
