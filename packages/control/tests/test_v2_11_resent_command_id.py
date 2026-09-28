"""a resent command_id gets the stored ack"""

from __future__ import annotations

from contracts.clock import SimClock
from helpers import NOW, make_handler

from control.handler import submit


def test_v2_11_resent_command_id_gets_stored_ack(tmp_path) -> None:
    handler = make_handler(tmp_path, SimClock(NOW))
    first = submit(handler, "STOP", {}, actor="sahil", reason="halt", command_id="same-1")
    assert first["status"] == "applied"
    second = submit(handler, "START", {}, actor="other", reason="ignore", command_id="same-1")
    assert second["command_id"] == "same-1"
    assert second["status"] == "applied"
    assert second["kind"] == "STOP"
    assert second["reason"] == "halt"
    assert handler.book().state_at(NOW.timestamp()).running is False
