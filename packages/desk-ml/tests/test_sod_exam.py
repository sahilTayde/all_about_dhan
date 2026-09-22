"""06 SOD exam: fill contract + spill story. write=false. NO_PROMOTE."""

from desk_ml.fill_contract import grade_fill
from desk_ml.sod_exam import classify_spill, compact_exam_event


def test_fill_contract_atm_as_itm_fails() -> None:
    g = grade_fill(bar_closed_1m=True, opened=True, quote_src="ATM", tape_kind="ATM", rolled_1m=True)
    assert g["ok"] is False
    assert g["verdict"] == "ATM_AS_ITM"


def test_fill_contract_forming_bar_fails() -> None:
    g = grade_fill(bar_closed_1m=False, opened=True, quote_src="ITM_100", tape_kind="ITM")
    assert g["ok"] is False
    assert g["verdict"] == "FILL_ON_FORMING_BAR"


def test_fill_contract_next_bar_itm_ok() -> None:
    g = grade_fill(bar_closed_1m=True, opened=True, quote_src="ITM_100", tape_kind="ITM", rolled_1m=True)
    assert g["ok"] is True
    assert g["verdict"] == "FILL_ON_NEXT_BAR_ITM"


def test_atm_tape_skip_is_honest() -> None:
    g = grade_fill(bar_closed_1m=True, opened=False, quote_src=None, tape_kind="ATM")
    assert g["ok"] is True
    assert g["verdict"] == "ATM_TAPE_NO_ITM_SKIP"


def test_spill_stop_after_good_next_bar_names_booking() -> None:
    row = {"realized_pnl_inr": -400.0, "sl_hit": True, "exit_reason": "STOP"}
    spill = classify_spill(row, next_itm_helped=True)
    assert spill["room"] == "booking"
    assert spill["code"] == "ENTRY_OK_BOOKING_STOP"
    assert spill["pnl_inr"] == -400.0
    assert "overlay" in spill["plain"].lower() or "path-review" in spill["plain"].lower()


def test_spill_against_is_booking_not_overlay() -> None:
    row = {"realized_pnl_inr": -120.0, "exit_reason": "CANCEL_AGAINST"}
    spill = classify_spill(row, next_itm_helped=False)
    assert spill["room"] == "booking"
    assert spill["code"] == "CANCEL_AGAINST"


def test_spill_flatten_is_desk_clock() -> None:
    row = {"realized_pnl_inr": -50.0, "exit_reason": "FLATTEN_1516"}
    spill = classify_spill(row, next_itm_helped=False)
    assert spill["room"] == "desk-clock"
    assert spill["code"] == "FLATTEN_CUT"


def test_compact_event_keeps_rooms() -> None:
    ev = compact_exam_event(
        {
            "ts": 1,
            "underlying": "NIFTY",
            "picker": {"action": "TICKET", "side": "CE"},
            "observer": {"action": "ALLOW", "reason": "OK", "side": "CE"},
            "desk": {"opened_this_tick": True},
            "analyst_votes": [{"source": "follows", "side": "CE", "silent": False}],
            "exam": {"verdict": "FILL_ON_NEXT_BAR_ITM", "ok": True},
        },
        opened=True,
        quote_src="ITM_100",
    )
    assert ev["picker_side"] == "CE"
    assert ev["observer_action"] == "ALLOW"
    assert ev["desk_opened"] is True
    assert ev["votes"][0]["source"] == "follows"
