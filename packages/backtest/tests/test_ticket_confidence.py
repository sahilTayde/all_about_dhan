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


def test_validate_pe_index_proxy_ok():
    from backtest_engine.levels import validate_index_proxy_levels

    bugs = validate_index_proxy_levels(
        lean="BUY_PE",
        entry=24840,
        stop=24895,
        target=24755,
        underlying="NIFTY",
    )
    assert bugs == []


def test_validate_pe_premium_shaped_flagged():
    from backtest_engine.levels import validate_index_proxy_levels

    bugs = validate_index_proxy_levels(
        lean="BUY_PE",
        entry=95,
        stop=62,
        target=155,
        underlying="NIFTY",
    )
    assert any("SUSPECT_PREMIUM_AS_INDEX" in b for b in bugs)
    assert any("PE_INDEX_LEVELS_INVERTED" in b for b in bugs)


def test_validate_ce_index_proxy_inverted():
    from backtest_engine.levels import validate_index_proxy_levels

    bugs = validate_index_proxy_levels(
        lean="CE",
        entry=24800,
        stop=24830,
        target=24740,
        underlying="NIFTY",
    )
    assert any("CE_INDEX_LEVELS_INVERTED" in b for b in bugs)


def test_customer_ticket_quarantines_index_proxy():
    from backtest_engine.ticket_confidence import customer_ticket_levels

    lv = customer_ticket_levels(
        underlying="NIFTY",
        lean="CE",
        spot=24800.0,
        state="CONFIRMED",
        method_id="MIX-SLTP-ATR-R2",
        atr_value=20.0,
    )
    assert lv["unit"] == "OPTION_PREMIUM"
    assert lv["levels_ready"] is False
    assert lv["entry"] is None
    assert lv["stop"] is None
    assert lv["target"] is None
    assert lv["index_entry"] == 24800.0
    assert lv["underlying_spot"] == 24800.0
    assert "DATA_INSUFFICIENT" in lv["levels_note"]


def test_customer_ticket_binds_option_ltp():
    from backtest_engine.ticket_confidence import customer_ticket_levels

    lv = customer_ticket_levels(
        underlying="NIFTY",
        lean="PE",
        spot=24840.0,
        state="CONFIRMED",
        method_id="MIX-SLTP-ATR-R2",
        atr_value=20.0,
        option_ltp=95.5,
        premium_meta={"source": "dhan_optionchain", "strike": 24850, "expiry": "2026-09-09"},
    )
    assert lv["unit"] == "OPTION_PREMIUM"
    assert lv["levels_ready"] is True
    assert lv["entry"] == 95.5
    assert lv["target"] == round(95.5 * 1.25, 2)
    assert lv["stop"] is None  # underlying swing UNDERDEFINED — honest DI
    assert lv["strike"] == 24850
    assert "MIX-SLTP-PREM-PCT" in lv["levels_note"]
    assert lv["underlying_spot"] == 24840.0
    # Index ATR still quarantined for chart
    assert lv.get("index_entry") == 24840.0


def test_bind_option_premium_levels_direct():
    from backtest_engine.levels import bind_option_premium_levels

    lv = bind_option_premium_levels(
        option_ltp=100.0,
        lean="CE",
        strike=24800,
        underlying_spot=24810.0,
        stop_pct=0.30,
    )
    assert lv["entry"] == 100.0
    assert lv["stop"] == 70.0
    assert lv["target"] == 125.0
    assert lv["levels_ready"] is True


def test_swing_stop_binds_index_not_premium():
    from backtest_engine.indicators import Bar
    from backtest_engine.levels import (
        SWING_STOP_METHOD,
        bind_option_premium_levels,
        recent_swing_underlying_stop,
    )

    # Synthetic: swing low at bar 3 (low=90), wing=2
    bars = [
        Bar(ts=i, open=100, high=110, low=95, close=100, volume=1)
        for i in range(8)
    ]
    bars[3] = Bar(ts=3, open=100, high=105, low=90, close=100, volume=1)
    swing = recent_swing_underlying_stop(bars, "CE", wing=2)
    assert swing == 90.0
    lv = bind_option_premium_levels(
        option_ltp=100.0,
        lean="CE",
        strike=24800,
        underlying_spot=24810.0,
        bars=bars,
    )
    assert lv["entry"] == 100.0
    assert lv["target"] == 125.0
    assert lv["stop"] is None  # premium Stop still DI
    assert lv["index_stop"] == 90.0
    assert lv["stop_underlying"] == 90.0
    assert lv["stop_method"] == SWING_STOP_METHOD
    assert "MIX-SLTP-SWING-STOP" in (lv.get("stop_gap") or "")


def test_validate_customer_rejects_index_as_premium():
    from backtest_engine.levels import validate_customer_option_premium_slots

    bugs = validate_customer_option_premium_slots(
        side="BUY_PE",
        entry=24840,
        stop=24895,
        target=24755,
        underlying="NIFTY",
        unit="OPTION_PREMIUM",
    )
    assert any("INDEX_AS_PREMIUM" in b for b in bugs)

    ok = validate_customer_option_premium_slots(
        side="BUY_PE",
        entry="DATA_INSUFFICIENT",
        stop="DATA_INSUFFICIENT",
        target="DATA_INSUFFICIENT",
        underlying="NIFTY",
        unit="OPTION_PREMIUM",
    )
    assert ok == []


def test_mock_fixture_levels_honest_after_fix():
    import json
    from pathlib import Path
    from backtest_engine.levels import validate_customer_option_premium_slots

    path = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "mock" / "signal.json"
    if not path.exists():
        path = Path(__file__).resolve().parents[4] / "apps" / "web" / "public" / "mock" / "signal.json"
    desk = json.loads(path.read_text())
    assert desk["todaysBook"]["label"] == "PAPER"
    assert desk["todaysBook"]["rows"] == []
    assert desk["fixtureBook"]["label"] == "FIXTURE"
    assert len(desk["fixtureBook"]["rows"]) >= 1
    times = [r["timeIst"] for r in desk["fixtureBook"]["rows"]]
    assert times == sorted(times, reverse=True)
    for und, sig in desk["signals"].items():
        bugs = validate_customer_option_premium_slots(
            side=sig["side"],
            entry=sig["entry"],
            stop=sig["stop"],
            target=sig["target"],
            underlying=und,
            unit=(sig.get("ticket") or {}).get("unit"),
        )
        assert bugs == [], (und, bugs)
        assert (sig.get("ticket") or {}).get("unit") == "OPTION_PREMIUM"
        # Chart may still carry index overlays — that is intentional.
        overlays = (sig.get("chart") or {}).get("overlays") or {}
        assert overlays.get("entrySpot") is not None
    for row in desk["fixtureBook"]["rows"]:
        bugs = validate_customer_option_premium_slots(
            side=row["side"],
            entry=row["entry"],
            stop=row["stop"],
            target=row["target"],
            underlying=row["underlying"],
            unit=row.get("unit"),
        )
        assert bugs == [], (row["id"], bugs)


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
