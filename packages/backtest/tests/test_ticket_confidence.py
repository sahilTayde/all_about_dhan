from backtest_engine.ticket_confidence import (
    CONFIDENCE_CAP,
    confidence_from_books,
    paper_levels,
    round_strike,
)
from backtest_engine.levels import build_levels, DESK_PLACEHOLDER_STOP_PTS


def test_round_strike_nifty():
    assert round_strike(24823, "NIFTY") == 24800
    assert round_strike(24826, "NIFTY") == 24850


def test_paper_levels_atr_rr_two():
    lv = paper_levels(
        underlying="NIFTY",
        lean="CE",
        spot=24800.0,
        state="CONFIRMED",
        method_id="MIX-SLTP-ATR-R2",
        atr_value=20.0,
        atr_mult=1.5,
        rr=2.0,
    )
    assert lv["levels_ready"] is True
    assert lv["levels_method"] == "MIX-SLTP-ATR-R2"
    assert lv["strike"] == 24800
    assert lv["entry"] == 24800.0
    # stop_d = 20*1.5=30; target_d=60
    assert lv["stop"] == 24770.0
    assert lv["target"] == 24860.0
    assert lv["unit"] == "INDEX_POINTS_PROXY"


def test_paper_levels_no_atr_refuses_hardcode():
    lv = paper_levels(
        underlying="NIFTY",
        lean="CE",
        spot=24800.0,
        state="CONFIRMED",
        method_id="MIX-SLTP-ATR-R2",
        atr_value=None,
    )
    assert lv["levels_ready"] is False
    assert "DATA_INSUFFICIENT" in lv["levels_note"]


def test_desk_placeholder_labeled_deprecated():
    lv = build_levels(
        underlying="NIFTY",
        lean="CE",
        spot=24800.0,
        state="CONFIRMED",
        method_id="DESK_PLACEHOLDER",
    )
    assert lv["levels_ready"] is True
    assert lv["deprecated"] is True
    assert lv["stop"] == 24800.0 - DESK_PLACEHOLDER_STOP_PTS["NIFTY"]


def test_paper_levels_hidden_on_watch():
    lv = paper_levels(underlying="NIFTY", lean="CE", spot=24800.0, state="WATCH")
    assert lv["levels_ready"] is False
    assert lv["entry"] is None


def test_confidence_caps_and_labels_not_winrate():
    conf = confidence_from_books(
        underlying="NIFTY",
        default_row={"lean": "CE", "state": "CONFIRMED"},
        club_row={"lean": "CE", "state": "CONFIRMED"},
    )
    assert conf["score_pct"] <= CONFIDENCE_CAP
    assert conf["eligible_count"] == 2
    assert conf["band"] == "higher_agreement"
    assert "win rate" in conf["fairness"].lower() or "NOT a win rate" in conf["fairness"]
    assert conf["customer_decide"] is True
    assert conf["orders"] == "refused"


def test_confidence_zero_when_vetoed():
    conf = confidence_from_books(
        underlying="NIFTY",
        default_row={"lean": "SKIP", "state": "VETOED"},
        club_row={"lean": "SKIP", "state": "VETOED"},
    )
    assert conf["score_pct"] == 0
    assert conf["eligible_count"] == 0
