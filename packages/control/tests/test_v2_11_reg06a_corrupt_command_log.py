"""REG-06a: a corrupt line mid-day in the command log never erases earlier trades;
later valid exit commands still apply; entries block from the last good command.
"""

from __future__ import annotations

from contracts.clock import SimClock
from helpers import INST, NOW, make_handler, open_one

from control.handler import submit
from control.kinds import UNREADABLE, CommandBook
from control.log import append_command, log_path, read_commands


def test_v2_11_reg06a_corrupt_command_log(tmp_path) -> None:
    clock = SimClock(NOW)
    handler = make_handler(tmp_path, clock)
    submit(handler, "START", {}, actor="sahil", reason="open", command_id="c1")
    submit(handler, "SET_LOTS", {"lots": 2}, actor="sahil", reason="size", command_id="c2")
    path = log_path(tmp_path)
    with path.open("ab") as fh:
        fh.write(b"{not-json\n")
        fh.write(b'{"command_id":"bad-schema"}\n')
        fh.write(b"truncated")
    loaded = read_commands(tmp_path)
    assert loaded.problems
    assert any(r.get("command_id") == "c1" for r in loaded.rows)
    assert any(r.get("command_id") == "c2" for r in loaded.rows)
    book = CommandBook(loaded.rows, loaded.problems, loaded.blocked_from)
    assert book.entry_reason(clock.now().timestamp()) == UNREADABLE
    assert book.state_at(clock.now().timestamp()).lots == 2

    pm, clock2 = open_one(tmp_path)
    pos = pm.open_book()[0]
    later = make_handler(tmp_path, clock2, manager=pm)
    ack = submit(
        later,
        "CUT_LOSS",
        {"position_id": pos["position_id"], "instrument_id": INST},
        actor="sahil",
        reason="still-exit",
        command_id="c-exit",
    )
    assert ack["status"] == "applied"
    assert pm.open_book() == []
    again = read_commands(tmp_path)
    ids = {r.get("command_id") for r in again.rows}
    assert {"c1", "c2", "c-exit"} <= ids
    assert again.problems
    _ = append_command
