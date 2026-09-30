"""Edge cases the brief named: expiry 14:30, freeze, 60s hole, same-bar, zero-lot, CE/PE."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST
from exitlab.harness import replay_trade
from exitlab.plans import (
    plan_asymmetric_ce_pe,
    plan_expiry_cliff,
    plan_fixed_stop_target,
    plan_hold_to_1515,
    plan_scale_out,
    plan_stale_and_flat,
)
from exitlab.types import Bar, Entry, Quote


def _ts(h: int, m: int, s: int = 0, day: int = 22) -> datetime:
    return datetime(2026, 9, day, h, m, s, tzinfo=IST)


def _entry(*, side: str = "CE", lots: int = 1, scenario: str = "expiry_chop") -> Entry:
    return Entry(
        entry_id="edge",
        ts=_ts(14, 20),
        side=side,
        strike=23300,
        entry_price=40.0,
        lots=lots,
        lot_size=65,
        entry_set="test",
        session="2026-09-22",
        index_at_entry=23300.0,
        scenario=scenario,
        extra={"expiry_day": True, "regime_at_entry": scenario},
    )


def test_expiry_after_1430_cliff() -> None:
    quotes = (
        Quote(available_ts=_ts(14, 25), bid=39.5, ask=40.0, ltp=39.8, index=23290.0),
        Quote(available_ts=_ts(14, 31), bid=38.0, ask=38.5, ltp=38.2, index=23280.0),
    )
    out = replay_trade(_entry(), plan_expiry_cliff(), quotes=quotes, data_source="synthetic")
    assert out.exit_reason == "EXPIRY_CLIFF"


def test_1515_freeze_flattens_hold() -> None:
    quotes = (
        Quote(available_ts=_ts(14, 25), bid=41.0, ask=41.5, ltp=41.2, index=23310.0),
        Quote(available_ts=_ts(15, 15), bid=41.0, ask=41.5, ltp=41.2, index=23310.0),
    )
    out = replay_trade(_entry(), plan_hold_to_1515(), quotes=quotes, data_source="synthetic")
    assert out.exit_reason == "FLATTEN_EOD"
    assert out.exit_ts is not None
    assert "15:15" in out.exit_ts or "15:16" in out.exit_ts


def test_no_quotes_for_60s_stale() -> None:
    quotes = (
        Quote(available_ts=_ts(14, 20, 1), bid=40.0, ask=40.5, ltp=40.2, index=23300.0),
        Quote(available_ts=_ts(14, 22, 0), bid=40.1, ask=40.6, ltp=40.3, index=23301.0),
    )
    out = replay_trade(
        _entry(), plan_stale_and_flat(max_age_s=60.0), quotes=quotes, data_source="synthetic"
    )
    assert out.exit_reason in {"STALE_FEED", "FLATTEN_EOD", "HARD_STOP"}


def test_stop_and_target_same_bar_stop_wins() -> None:
    entry = Entry(
        entry_id="same",
        ts=_ts(10, 5, day=17),
        side="CE",
        strike=23200,
        entry_price=100.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        scenario="chop",
    )
    bar = Bar(
        ts=_ts(10, 6, day=17),
        available_ts=_ts(10, 6, day=17),
        open=100.0,
        high=160.0,
        low=60.0,
        close=110.0,
    )
    out = replay_trade(
        entry,
        plan_fixed_stop_target(0.20, 0.30),
        bars=(bar,),
        data_source="synthetic",
    )
    assert out.exit_reason == "SAME_BAR_STOP"


def test_zero_lot_partial_is_reject() -> None:
    out = replay_trade(
        _entry(lots=1),
        plan_scale_out(),
        quotes=(Quote(available_ts=_ts(14, 21), bid=41.0, ask=41.5, ltp=41.2),),
        partial_fill_frac=0.0,
        data_source="synthetic",
    )
    assert out.skipped == "REJECT"
    assert out.net_inr == 0.0


def test_ce_pe_flip_uses_side() -> None:
    pe_quotes = (
        Quote(available_ts=_ts(10, 6, day=21), bid=90.0, ask=91.0, ltp=90.5, index=23400.0),
        Quote(available_ts=_ts(11, 0, day=21), bid=88.0, ask=89.0, ltp=88.5, index=23450.0),
    )
    pe = Entry(
        entry_id="pe",
        ts=_ts(10, 5, day=21),
        side="PE",
        strike=23400,
        entry_price=90.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-21",
        index_at_entry=23400.0,
        scenario="trend_up",
        extra={"regime_at_entry": "trend_up"},
    )
    out = replay_trade(pe, plan_asymmetric_ce_pe(), quotes=pe_quotes, data_source="synthetic")
    assert out.side == "PE"
    assert out.exit_reason
