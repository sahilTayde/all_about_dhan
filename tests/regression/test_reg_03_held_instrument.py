"""REG-03b: forced close is built from the held position, never a new strike."""

from __future__ import annotations

from brokers import Position, exit_intent


def test_reg_03b_exit_intent_from_held_position() -> None:
    held = Position("NIFTY 24400 CE", 65, 112.5, "43210")
    intent = exit_intent(held, exit_reason="EOD")
    assert intent.instrument_id == "43210"
    assert intent.symbol == "NIFTY 24400 CE"
    assert intent.lots == 65
    assert intent.purpose == "EXIT"
    assert intent.side == "SELL"
