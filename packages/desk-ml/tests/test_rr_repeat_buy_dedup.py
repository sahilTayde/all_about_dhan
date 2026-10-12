"""2026-10-12 repeat buys: R01_PDIV and R01_B3A_VOL both bought the same contract.
11:59 IST NIFTY 22350 PE and 12:33 IST SENSEX 72000 CE were same-minute duplicates (the live loop ran
4aa8778, which had no dedup); 12:38 IST NIFTY 22400 CE was a later buy of a contract still held, which the
same-minute dedup (8f59dc8) also missed. One desk position per contract while it is held."""

from __future__ import annotations

from desk_ml import research_rules as rr

R01, B3A = rr.R01, rr.R01_B3A


def _row(tid, rule, und, side, strike, entry, exit_, open_=False):
    return {"trade_id": tid, "rule_id": rule, "underlying": und, "side": side, "atm_strike": strike,
            "entry_min": entry, "sig_min": entry, "exit_min": exit_, "spec_exit_min": exit_,
            "realized_pnl_inr": 0.0, "status": "OPEN_PAPER" if open_ else "CLOSED"}


def _run(rows):
    return rr._desk_pass([], rows, "2026-10-12", [R01, B3A], {})


def test_same_minute_duplicates_tagged() -> None:
    rows = [_row("a", R01, "NIFTY", "PE", 22350.0, "11:59", "12:19"),
            _row("b", B3A, "NIFTY", "PE", 22350.0, "11:59", "12:19"),
            _row("c", R01, "SENSEX", "CE", 72000.0, "12:33", "12:53"),
            _row("d", B3A, "SENSEX", "CE", 72000.0, "12:33", "12:53")]
    _o, closed, _b, dups, _t = _run(rows)
    assert {r["trade_id"] for r in closed} == {"a", "c"}
    assert {(d["trade_id"], d["dup_of"], d["guard"]) for d in dups} == {("b", "a", rr.DUP_SAME_CONTRACT),
                                                                       ("d", "c", rr.DUP_SAME_CONTRACT)}


def test_buy_of_contract_still_held_is_a_duplicate() -> None:
    rows = [_row("a", R01, "NIFTY", "CE", 22400.0, "12:33", "12:52"),
            _row("b", B3A, "NIFTY", "CE", 22400.0, "12:38", "12:57")]
    _o, closed, _b, dups, _t = _run(rows)
    assert [r["trade_id"] for r in closed] == ["a"]
    assert [(d["trade_id"], d["dup_of"]) for d in dups] == [("b", "a")]


def test_open_position_blocks_repeat_and_after_exit_is_allowed() -> None:
    held = _row("a", R01, "NIFTY", "PE", 22350.0, "12:56", "13:16", open_=True)
    rep = _row("b", B3A, "NIFTY", "PE", 22350.0, "13:05", "13:25")
    opens, closed, _b, dups, _t = rr._desk_pass([held], [rep], "2026-10-12", [R01, B3A], {})
    assert [r["trade_id"] for r in opens] == ["a"] and not closed and dups[0]["trade_id"] == "b"
    later = [_row("a", R01, "NIFTY", "PE", 22350.0, "12:56", "13:16"),
             _row("b", B3A, "NIFTY", "PE", 22350.0, "13:17", "13:37"),
             _row("c", B3A, "NIFTY", "PE", 22400.0, "13:00", "13:20")]  # other strike: not a duplicate
    _o, closed, _b, dups, _t = _run(later)
    assert {r["trade_id"] for r in closed} == {"a", "b", "c"} and not dups
