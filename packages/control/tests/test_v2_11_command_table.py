"""each command has a table test (applied, rejected with reason)"""

from __future__ import annotations

import uuid

import pytest
from contracts.clock import SimClock
from helpers import NOW, make_handler

from control.handler import submit
from control.kinds import KINDS


def _id() -> str:
    return uuid.uuid4().hex[:12]


@pytest.mark.parametrize(
    "kind,args",
    [
        ("START", {}),
        ("STOP", {}),
        ("PAUSE", {"minutes": 15}),
        ("PAUSE", {"minutes": 0}),
        ("BLOCKED_WINDOWS", {"windows": [{"start": "12:00", "end": "12:30"}]}),
        ("SET_LOTS", {"lots": 2}),
        ("SET_LOTS", {"lots": None}),
        ("INDEX", {"underlying": "NIFTY", "enabled": False}),
        ("BASKET_REMOVE", {"strategy_id": "R8-E1-COIL-SIDE"}),
        ("MIN_CAPITAL", {"amount_inr": 300000}),
        ("ADD_FUNDS", {"amount_inr": 50000}),
        ("REARM", {}),
        ("KILL", {}),
        ("FLATTEN_ALL", {}),
    ],
)
def test_v2_11_command_table_applied(tmp_path: object, kind: str, args: dict) -> None:
    handler = make_handler(tmp_path, SimClock(NOW))
    ack = submit(handler, kind, args, actor="sahil", reason=f"table {kind}", command_id=_id())
    assert ack["status"] == "applied", ack
    assert ack["who"] == "sahil" and ack["why"] == f"table {kind}"
    assert ack["when"]


@pytest.mark.parametrize(
    "kind,args,needle",
    [
        ("PAUSE", {"minutes": -1}, "minutes"),
        ("PAUSE", {"minutes": 99999}, "minutes"),
        ("SET_LOTS", {"lots": 0}, "lots"),
        ("INDEX", {"underlying": "nifty", "enabled": True}, "underlying"),
        ("INDEX", {"underlying": "NIFTY"}, "enabled"),
        ("BASKET_REMOVE", {}, "strategy_id"),
        ("CUT_LOSS", {}, "position_id"),
        ("ADD_FUNDS", {"amount_inr": 0}, "amount_inr"),
        ("MIN_CAPITAL", {"amount_inr": -5}, "amount_inr"),
        ("FLATTEN_ALL", {"underlying": "x"}, "underlying"),
        ("NOPE", {}, "unknown kind"),
    ],
)
def test_v2_11_command_table_rejected(tmp_path: object, kind: str, args: dict, needle: str) -> None:
    handler = make_handler(tmp_path, SimClock(NOW))
    if kind not in KINDS:
        from control.kinds import validate_args

        assert validate_args(kind, args) is not None
        assert needle in (validate_args(kind, args) or "")
        return
    ack = submit(handler, kind, args, actor="sahil", reason="reject", command_id=_id())
    assert ack["status"] == "rejected", ack
    assert needle in str(ack.get("status_reason") or ack.get("reject_reason") or "")
