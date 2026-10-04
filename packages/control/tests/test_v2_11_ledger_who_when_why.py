"""every control action is logged to the ledger/audit with who/when/why"""

from __future__ import annotations

from contracts.clock import SimClock
from helpers import NOW, make_handler
from ledger.v2 import SqliteLedgerStore

from control.handler import submit
from control.store import LedgerCommandStore


def test_v2_11_logged_who_when_why(tmp_path) -> None:
    ledger = SqliteLedgerStore(tmp_path / "ctl.sqlite", migrate_schema=True)
    handler = make_handler(
        tmp_path,
        SimClock(NOW),
        store=LedgerCommandStore(ledger),
        ledger=ledger,
    )
    ack = submit(
        handler,
        "SET_LOTS",
        {"lots": 2},
        actor="sahil",
        reason="risk limit change",
        command_id="lots-1",
    )
    assert ack["status"] == "applied"
    row = ledger.get_founder_command("lots-1")
    assert row is not None
    assert row["actor"] == "sahil"
    assert row["reason"] == "risk limit change"
    assert row["who"] == "sahil"
    assert row["why"] == "risk limit change"
    assert row["when"]
    assert row["status"] == "applied"
    assert row["kind"] == "SET_LOTS"
