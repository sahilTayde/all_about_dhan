"""Tests for payload dataclasses (section 4.4 types)."""

import pytest

from contracts.payloads import (
    AtrStop,
    BarClosed,
    CatastrophicStop,
    ChainOptionData,
    ChainSnapshot,
    ChainStrike,
    Clock,
    CommandAck,
    Decision,
    DepthQuote,
    EntryPlan,
    EntryPlanResult,
    ExitPlan,
    FeedStatus,
    Fill,
    FounderCommand,
    GracePeriod,
    Level,
    OiCadence,
    OrderUpdate,
    PositionClosed,
    PositionUpdate,
    QuoteSnapshot,
    RiskDecision,
    Signal,
    SignalFlipExit,
    StrikeChoice,
    StrikeQuote,
    StructuralStop,
    Tick,
    TimeStop,
)


def test_tick_payload() -> None:
    """Test TICK payload (md:ticks)."""
    tick = Tick(
        instrument_id="NSE_IDX:NIFTY",
        ltp=24512.35,
        ltq=0,
        volume=None,
        oi=None,
        exchange_ts="2026-09-28T10:00:59.870+05:30",
    )
    assert tick.instrument_id == "NSE_IDX:NIFTY"
    assert tick.ltp == 24512.35


def test_depth_quote_payload() -> None:
    """Test DEPTH_QUOTE payload (md:depth)."""
    depth = DepthQuote(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=151.10,
        bid_qty=1950,
        ask=151.35,
        ask_qty=1300,
        ltp=151.20,
        oi=4412350,
        levels={
            "bid": [[151.10, 1950], [151.05, 2600]],
            "ask": [[151.35, 1300], [151.40, 2275]],
        },
        exchange_ts="2026-09-28T10:01:01.230+05:30",
        repeat=False,
        raw_b64=None,
    )
    assert depth.bid == 151.10
    assert len(depth.levels["bid"]) == 2


def test_quote_snapshot_payload() -> None:
    """Test QUOTE_SNAPSHOT payload (md:quotes)."""
    quote = QuoteSnapshot(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        rule="ITM100",
        side="CE",
        bid=151.10,
        ask=151.35,
        mid=151.225,
        spread=0.25,
        ltp=151.20,
        ltt="2026-09-28T10:01:04.910+05:30",
        oi=4412350,
        depth_age_ms=310,
        stale=False,
    )
    assert quote.rule == "ITM100"
    assert quote.mid == 151.225


def test_oi_cadence_payload() -> None:
    """Test OI_CADENCE payload (md:oi_cadence)."""
    oi_cad = OiCadence(
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        window_s=60,
        oi_updates=2,
        median_gap_s=31.0,
        p90_gap_s=58.0,
        last_oi_change="2026-09-28T10:00:47.100+05:30",
        sources=["feed_oi", "full", "chain"],
    )
    assert oi_cad.window_s == 60
    assert len(oi_cad.sources) == 3


def test_bar_closed_payload() -> None:
    """Test BAR_CLOSED payload (md:bars:1m)."""
    bar = BarClosed(
        instrument_id="NSE_IDX:NIFTY",
        tf="1m",
        start="2026-09-28T10:00:00+05:30",
        end="2026-09-28T10:01:00+05:30",
        o=24498.1,
        h=24515.0,
        l=24496.4,
        c=24512.35,
        v=None,
        n_ticks=57,
        gap=False,
        late_ticks=0,
    )
    assert bar.tf == "1m"
    assert bar.c == 24512.35
    assert bar.gap is False


def test_chain_snapshot_payload() -> None:
    """Test CHAIN_SNAPSHOT payload (md:chain)."""
    chain = ChainSnapshot(
        underlying="NIFTY",
        expiry="2026-09-29",
        spot=24512.35,
        strikes=[
            ChainStrike(
                strike=24500.0,
                ce=ChainOptionData(ltp=88.2, bid=88.1, ask=88.4, oi=5123400, oi_chg=84500, iv=11.8),
                pe=ChainOptionData(
                    ltp=76.9, bid=76.8, ask=77.1, oi=4987200, oi_chg=-22100, iv=12.1
                ),
            )
        ],
    )
    assert chain.underlying == "NIFTY"
    assert len(chain.strikes) == 1
    assert chain.strikes[0].ce.ltp == 88.2


def test_clock_payload() -> None:
    """Test CLOCK payload (md:clock)."""
    clock = Clock(session="2026-09-28", phase="MARKET", minute="10:01")
    assert clock.phase == "MARKET"
    assert clock.minute == "10:01"


def test_feed_status_payload() -> None:
    """Test FEED_STATUS payload (md:status)."""
    status = FeedStatus(
        status="STALE",
        instrument_id="BSE_IDX:SENSEX",
        since="2026-09-28T11:14:03+05:30",
        gap_s=7.2,
    )
    assert status.status == "STALE"
    assert status.gap_s == 7.2


def test_exit_plan_complete() -> None:
    """Test ExitPlan with all primitives."""
    plan = ExitPlan(
        catastrophic=CatastrophicStop(level=Level(kind="premium", price=118.0)),
        structural=StructuralStop(
            level=Level(kind="underlying", price=24488.0), trigger="bar_close"
        ),
        atr=AtrStop(k=2.0, trigger="bar_close"),
        time_stops=(
            TimeStop(after_s=180, when="entry_in:09:15-10:00"),
            TimeStop(after_s=900, when="always"),
        ),
        grace=GracePeriod(seconds=60),
        signal_flip=SignalFlipExit(on=("own_opposite",), trigger="bar_close"),
        target=Level(kind="underlying", price=24531.0),
        partials=(),
        trail=None,
        flat_by_ist="15:15",
        defaults_from=None,
    )
    assert plan.catastrophic.level.price == 118.0
    assert plan.flat_by_ist == "15:15"
    assert len(plan.time_stops) == 2


def test_strike_choice_with_alternatives() -> None:
    """Test StrikeChoice with 3 alternatives."""
    choice = StrikeChoice(
        chosen="ITM100",
        reason="LOWEST_BREAKEVEN_AT_HOLD",
        rule_version="router-1.0.0+9c2e",
        alternatives=(
            StrikeQuote(
                rule="ATM",
                instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
                bid=88.05,
                ask=88.25,
                mid=88.15,
                spread=0.20,
                quote_age_ms=640,
                est_delta=0.51,
                est_round_trip_pts=0.64,
            ),
            StrikeQuote(
                rule="ITM100",
                instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
                bid=151.10,
                ask=151.35,
                mid=151.23,
                spread=0.25,
                quote_age_ms=410,
                est_delta=0.66,
                est_round_trip_pts=0.88,
            ),
            StrikeQuote(
                rule="ITM200",
                instrument_id="NSE_FNO:NIFTY:2026-09-29:24300:CE",
                bid=226.00,
                ask=226.35,
                mid=226.18,
                spread=0.35,
                quote_age_ms=820,
                est_delta=0.79,
                est_round_trip_pts=1.26,
            ),
        ),
    )
    assert choice.chosen == "ITM100"
    assert len(choice.alternatives) == 3


def test_signal_payload() -> None:
    """Test SIGNAL payload (sig:signals)."""
    signal = Signal(
        signal_id="sg_r8-e1-coil-side-v1.0.0_f49f4b_nifty_20260928_1001_0",
        strategy_id="R8-E1-COIL-SIDE",
        version="1.0.0",
        params_hash="30416a4a",
        stage="shadow",
        underlying="NIFTY",
        side="CE",
        strike_rule="ROUTER",
        decision_ts="2026-09-28T10:01:01.512+05:30",
        confidence=0.63,
        exit_plan={},
        strike_choice={},
        reasons=["COIL_AGE_7M", "P_UP_GE_Q90"],
        features={"p_up": 0.63, "box_d": 16.0},
    )
    assert signal.strategy_id == "R8-E1-COIL-SIDE"
    assert signal.confidence == 0.63


def test_signal_schema_validation() -> None:
    """Test SIGNAL schema validation with nested exit_plan and strike_choice ($ref resolution)."""
    from contracts.validation import validate_payload

    # Valid signal with complete exit_plan and strike_choice
    valid_signal = {
        "signal_id": "sg_r8-e1-v1.0.0_bfe5cd_nifty_20260928_1001_0",
        "strategy_id": "R8-E1",
        "version": "1.0.0",
        "params_hash": "30416a4a",
        "stage": "shadow",
        "underlying": "NIFTY",
        "side": "CE",
        "strike_rule": "ROUTER",
        "decision_ts": "2026-09-28T10:01:01.512+05:30",
        "exit_plan": {
            "catastrophic": {"level": {"kind": "premium", "price": 300.0}},
            "flat_by_ist": "15:15",
        },
        "strike_choice": {
            "chosen": "ATM",
            "reason": "optimal delta",
            "rule_version": "v1",
            "alternatives": [
                {"rule": "ATM", "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24400:CE"},
                {"rule": "ITM100", "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24300:CE"},
                {"rule": "ITM200", "instrument_id": "NSE_FNO:NIFTY:2026-09-29:24200:CE"},
            ],
        },
        "reasons": ["COIL_AGE_7M"],
        "features": {"p_up": 0.63},
    }

    # Should not raise (validates with $ref resolution)
    validate_payload("signal", valid_signal)

    # Invalid exit_plan should raise
    from jsonschema import ValidationError

    invalid_signal = {**valid_signal, "exit_plan": {"foo": 1}}
    with pytest.raises(ValidationError):
        validate_payload("signal", invalid_signal)


def test_signal_schema_rejects_invalid_stage() -> None:
    """Test SIGNAL schema rejects invalid stage values."""
    from jsonschema import ValidationError

    from contracts.validation import validate_payload

    invalid_signal = {
        "signal_id": "sg_r8-e1-v1.0.0_bfe5cd_nifty_20260928_1001_0",
        "strategy_id": "R8-E1",
        "version": "1.0.0",
        "params_hash": "30416a4a",
        "stage": "VETOED",  # Invalid stage (not in enum)
        "underlying": "NIFTY",
        "side": "CE",
        "strike_rule": "ROUTER",
        "decision_ts": "2026-09-28T10:01:01.512+05:30",
        "exit_plan": {
            "catastrophic": {"level": {"kind": "premium", "price": 300.0}},
            "flat_by_ist": "15:15",
        },
        "strike_choice": {
            "chosen": "ATM",
            "reason": "optimal delta",
            "rule_version": "v1",
            "alternatives": [],
        },
        "reasons": ["VETOED_BY_RISK"],
        "features": {"p_up": 0.63},
    }

    # Should raise ValidationError for invalid stage
    with pytest.raises(ValidationError):
        validate_payload("signal", invalid_signal)
    with pytest.raises(Exception) as exc_info:
        validate_payload("signal", invalid_signal)
    assert "ValidationError" in type(exc_info.value).__name__ or "Schema" in str(exc_info.value)


def test_decision_payload() -> None:
    """Test DECISION payload (boss:decisions)."""
    decision = Decision(
        decision_id="dc_nifty_20260928_1001",
        underlying="NIFTY",
        decision="ENTER",
        signal_ids=["sg_r8-e1-v1.0.0_bfe5cd_nifty_20260928_1001_0"],
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        lots=14,
        lot_size=65,
        limit_price=151.35,
        sizing={"volsize": 17, "caplots": 14, "basket_max": 25},
        holds=[],
        basket_hash="b7e1",
        shadow={"regime": "trend_up"},
        entry_location=None,
        stretch=None,
    )
    assert decision.decision == "ENTER"
    assert decision.lots == 14


def test_entry_plan_payload() -> None:
    """Test ENTRY_PLAN payload (oms:plans)."""
    plan = EntryPlan(
        plan_id="ep_001",
        decision_id="dc_nifty_20260928_1001",
        signal_id="sg_r8-e1-v1.0.0_bfe5cd_nifty_20260928_1001_0",
        account_id="founder",
        action="CHASE",
        shadow_actions=["LIMIT:fvg", "WAIT"],
        stretch={"zone_atr": 1.6},
        zone="fvg",
        zone_price=24501.5,
        entry_distance_atr=1.6,
        signal_candle_atr=2.4,
        limit_price=144.10,
        est_delta=0.66,
        expires_at="2026-09-28T10:04:01.512+05:30",
        client_order_id="aad3f9",
    )
    assert plan.action == "CHASE"
    assert plan.zone == "fvg"


def test_entry_plan_result_payload() -> None:
    """Test ENTRY_PLAN_RESULT payload (oms:plans)."""
    result = EntryPlanResult(
        plan_id="ep_001",
        status="FILLED",
        fill_price=151.35,
        filled_at="2026-09-28T10:01:01.800+05:30",
        waited_s=0.3,
        giveback_5m_pts=4.6,
        giveback_5m_atr=0.68,
        shadow={"LIMIT": {"status": "FILLED"}},
    )
    assert result.status == "FILLED"
    assert result.fill_price == 151.35


def test_risk_decision_payload() -> None:
    """Test RISK_DECISION payload (oms:risk)."""
    risk = RiskDecision(
        client_order_id="aad3f9",
        action="ENTRY",
        approved=False,
        reason_code="MAX_LOSS_PER_TRADE",
        reason="risk ₹31,200 exceeds max_loss_per_trade ₹30,000",
        critical=False,
        ticket_risk_inr=31200.0,
    )
    assert risk.approved is False
    assert risk.reason_code == "MAX_LOSS_PER_TRADE"


def test_order_update_payload() -> None:
    """Test ORDER_UPDATE payload (oms:orders)."""
    update = OrderUpdate(
        client_order_id="aad3f9",
        broker_order_id="PAPER-aad3f9",
        account_id="founder",
        from_="SUBMITTED",
        to_="FILLED",
        reason="fill 910 @ 151.35",
        purpose="ENTRY",
    )
    assert update.to_ == "FILLED"
    assert update.purpose == "ENTRY"


def test_fill_payload() -> None:
    """Test FILL payload (oms:fills)."""
    fill = Fill(
        client_order_id="aad3f9",
        qty=910,
        price=151.35,
        fill_model="depth",
        quote_available_ts="2026-09-28T10:01:01.800+05:30",
        charges_inr=None,
    )
    assert fill.qty == 910
    assert fill.fill_model == "depth"


def test_position_update_payload() -> None:
    """Test POSITION_UPDATE payload (pos:updates)."""
    pos = PositionUpdate(
        position_id="ps_001",
        account_id="founder",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        net_qty=910,
        avg_price=151.35,
        mark=153.10,
        unrealized_inr=1592.5,
        stop={"kind": "underlying", "price": 24488.0},
        protective_order="aad-S",
        strategy_id="R8-E1-COIL-SIDE",
    )
    assert pos.net_qty == 910
    assert pos.unrealized_inr == 1592.5


def test_position_closed_payload() -> None:
    """Test POSITION_CLOSED payload (pos:updates)."""
    closed = PositionClosed(
        position_id="ps_001",
        exit_reason="TIME_EXIT",
        gross_inr=1820.0,
        charges_inr=212.4,
        net_inr=1607.6,
        held_s=900,
        trade_id="tr_001",
    )
    assert closed.exit_reason == "TIME_EXIT"
    assert closed.net_inr == 1607.6


def test_founder_command_payload() -> None:
    """Test FOUNDER_COMMAND payload (ctl:commands)."""
    cmd = FounderCommand(
        command_id="cmd_01J",
        account_id="founder",
        kind="CUT_LOSS",
        args={"position_id": "ps_001"},
        actor="founder",
        reason="news",
        confirm_token="abc123",
    )
    assert cmd.kind == "CUT_LOSS"
    assert cmd.args["position_id"] == "ps_001"


def test_command_ack_payload() -> None:
    """Test COMMAND_ACK payload (ctl:acks)."""
    ack = CommandAck(
        command_id="cmd_01J",
        status="applied",
        applied_ts="2026-09-28T11:02:14.100+05:30",
        reason=None,
    )
    assert ack.status == "applied"
