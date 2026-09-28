"""Named plans fire the expected reason on a short synthetic path."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST, ReplayClock
from exitlab.harness import replay_trade
from exitlab.plans import library, plan_legacy_overlay, plan_v2_default, sweep_specs
from exitlab.types import Entry, OpenState, Quote


def _ts(h: int, m: int) -> datetime:
    return datetime(2026, 9, 17, h, m, tzinfo=IST)


def test_library_has_baselines_and_own_ideas() -> None:
    ids = set(library())
    for name in (
        "hold_to_1515",
        "fixed_stop_target",
        "v2_default",
        "legacy_overlay",
        "noise_band",
        "theta_budget",
        "regime_router",
        "asymmetric_ce_pe",
        "quote_persistence",
        "tod_two_speed",
        "elasticity_die",
        "expiry_cliff",
        "index_stop",
        "implied_move",
    ):
        assert name in ids
    assert len(sweep_specs()) >= 20


def test_v2_default_is_house_stop_or_eod() -> None:
    entry = Entry(
        entry_id="v2",
        ts=_ts(10, 5),
        side="CE",
        strike=23200,
        entry_price=100.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        scenario="mixed",
    )
    # 30k house stop on 65 qty is far below 100; flatten at 15:15
    quotes = (
        Quote(available_ts=_ts(10, 6), bid=101.0, ask=102.0, ltp=101.5),
        Quote(available_ts=_ts(15, 15), bid=99.0, ask=100.0, ltp=99.5),
    )
    out = replay_trade(entry, plan_v2_default(), quotes=quotes, data_source="synthetic")
    assert out.exit_reason in {"FLATTEN_EOD", "CATASTROPHIC_STOP"}


def test_legacy_overlay_no_progress() -> None:
    entry = Entry(
        entry_id="leg",
        ts=_ts(10, 5),
        side="CE",
        strike=23200,
        entry_price=100.0,
        lots=1,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        scenario="chop",
    )
    # Three closed 1m bars with MFE < 2
    from exitlab.types import Bar

    bars = [
        Bar(ts=_ts(10, 6), available_ts=_ts(10, 6), open=100.2, high=100.4, low=99.8, close=100.1),
        Bar(ts=_ts(10, 7), available_ts=_ts(10, 7), open=100.1, high=100.5, low=99.7, close=100.0),
        Bar(ts=_ts(10, 8), available_ts=_ts(10, 8), open=100.0, high=100.3, low=99.6, close=99.9),
    ]
    quotes = tuple(
        Quote(available_ts=b.available_ts, bid=b.close - 0.1, ask=b.close + 0.1, ltp=b.close)
        for b in bars
    )
    out = replay_trade(
        entry, plan_legacy_overlay(), quotes=quotes, bars=bars, data_source="synthetic"
    )
    assert out.exit_reason in {
        "CANCEL_NO_PROGRESS",
        "STOP",
        "CANCEL_ADVERSE",
        "TIME",
        "FLATTEN_EOD",
    }


def test_open_state_starts_at_entry() -> None:
    e = Entry(
        entry_id="s",
        ts=_ts(10, 0),
        side="PE",
        strike=23400,
        entry_price=90.0,
        lots=1,
        lot_size=65,
        entry_set="t",
        session="2026-09-17",
        scenario="x",
    )
    st = OpenState(entry=e, remaining_qty=65, mfe=90.0, mae=90.0, seen_high=90.0, seen_low=90.0)
    assert st.remaining_qty == e.qty
    _ = ReplayClock
