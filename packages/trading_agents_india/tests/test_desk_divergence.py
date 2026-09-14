"""Deterministic CE/PE vs INDEX dealer — no LLM, no fills."""

from __future__ import annotations

from trading_agents_india.desk_divergence import judge_tick


def test_index_down_pe_not_up_is_hold() -> None:
    note = judge_tick(
        underlying="NIFTY",
        index_delta=-8.0,
        ce_delta=-1.5,
        pe_delta=-0.4,
    )
    assert note.case == "PREMIUM_DIVERGENCE"
    assert note.verdict == "HOLD"
    assert note.allow_new_paper_ce_pe is False
    assert note.execution == "refused"
    assert "PE" in note.dealer_note


def test_index_down_ce_not_down_is_hold() -> None:
    note = judge_tick(
        underlying="SENSEX",
        index_delta=-12.0,
        ce_delta=1.0,
        pe_delta=2.0,
    )
    assert note.case == "PREMIUM_DIVERGENCE"
    assert note.allow_new_paper_ce_pe is False


def test_index_up_ce_follows_confirms_buy_ce() -> None:
    note = judge_tick(
        underlying="BANKNIFTY",
        index_delta=15.0,
        ce_delta=2.5,
        pe_delta=-1.0,
    )
    assert note.verdict == "BUY_CE_CONFIRM"
    assert note.case == "CE_FOLLOWS"
    assert note.allow_new_paper_ce_pe is True
    assert note.promote is False


def test_index_down_premiums_follow_confirms_buy_pe() -> None:
    note = judge_tick(
        underlying="NIFTY",
        index_delta=-10.0,
        ce_delta=-1.2,
        pe_delta=1.8,
    )
    assert note.verdict == "BUY_PE_CONFIRM"
    assert note.case == "PE_FOLLOWS"
    assert note.execution == "refused"


def test_stale_and_wrong_strike_hold() -> None:
    stale = judge_tick(
        underlying="NIFTY",
        index_delta=5.0,
        ce_delta=1.0,
        pe_delta=-1.0,
        stale=True,
    )
    assert stale.reason_code == "STALE"
    assert stale.allow_new_paper_ce_pe is False
    wrong = judge_tick(
        underlying="NIFTY",
        index_delta=5.0,
        ce_delta=1.0,
        pe_delta=-1.0,
        wrong_strike=True,
    )
    assert wrong.reason_code == "WRONG_STRIKE"


def test_missing_prints_are_di() -> None:
    note = judge_tick(
        underlying="NIFTY",
        index_delta=None,
        ce_delta=1.0,
        pe_delta=1.0,
    )
    assert note.verdict == "DATA_INSUFFICIENT"
    assert note.allow_new_paper_ce_pe is False
