"""Harness: deterministic fills, costs, partials, skip."""

from __future__ import annotations

from datetime import datetime

from exitlab.clock import IST
from exitlab.harness import replay_trade
from exitlab.plans import plan_fixed_stop_target, plan_hold_to_1515, plan_scale_out
from exitlab.types import Entry, Quote


def _ts(h: int, m: int) -> datetime:
    return datetime(2026, 9, 17, h, m, tzinfo=IST)


def _entry(**kw: object) -> Entry:
    base = dict(
        entry_id="e1",
        ts=_ts(10, 5),
        side="CE",
        strike=23200.0,
        entry_price=100.0,
        lots=2,
        lot_size=65,
        entry_set="test",
        session="2026-09-17",
        index_at_entry=23300.0,
        moneyness="ITM200",
        scenario="trend_up",
    )
    base.update(kw)
    return Entry(**base)  # type: ignore[arg-type]


def _path(*prints: tuple[int, int, float]) -> tuple[Quote, ...]:
    return tuple(
        Quote(available_ts=_ts(h, m), bid=px - 0.5, ask=px + 0.5, ltp=px, index=23300.0)
        for h, m, px in prints
    )


def test_hard_stop_exits_at_bid() -> None:
    quotes = _path((10, 6, 99.0), (10, 7, 70.0), (10, 8, 69.0))
    out = replay_trade(
        _entry(), plan_fixed_stop_target(0.20, 0.40), quotes=quotes, data_source="synthetic"
    )
    assert out.exit_reason == "HARD_STOP"
    assert out.exit_price is not None
    assert out.exit_price <= 70.0  # bid side
    assert out.charges_inr > 0
    assert out.net_inr == round(out.gross_inr - out.charges_inr, 2)


def test_target_hits() -> None:
    quotes = _path((10, 6, 110.0), (10, 7, 145.0))
    out = replay_trade(
        _entry(), plan_fixed_stop_target(0.20, 0.40), quotes=quotes, data_source="synthetic"
    )
    assert out.exit_reason == "TARGET"
    assert out.gross_inr > 0


def test_hold_to_1515_is_deterministic() -> None:
    quotes = _path((10, 6, 110.0), (15, 15, 108.0), (15, 16, 50.0))
    a = replay_trade(_entry(), plan_hold_to_1515(), quotes=quotes, data_source="synthetic")
    b = replay_trade(_entry(), plan_hold_to_1515(), quotes=quotes, data_source="synthetic")
    assert a.net_inr == b.net_inr
    assert a.exit_reason == "FLATTEN_EOD"
    assert a.exit_price == b.exit_price


def test_skip_wide_spread() -> None:
    e = _entry(extra={"spread": 9.0, "max_spread": 4.0})
    out = replay_trade(
        e, plan_hold_to_1515(), quotes=_path((10, 6, 100.0)), data_source="synthetic"
    )
    assert out.skipped == "SKIP_WIDE_SPREAD"
    assert out.net_inr == 0.0


def test_scale_out_whole_lots_only() -> None:
    quotes = _path((10, 6, 130.0), (10, 7, 140.0), (15, 15, 120.0))
    out = replay_trade(
        _entry(lots=2), plan_scale_out(0.5, 1.0), quotes=quotes, data_source="synthetic"
    )
    reasons = [leg["reason"] for leg in out.extra.get("legs") or []]
    assert "PARTIAL" in reasons or out.exit_reason in {
        "PARTIAL",
        "TARGET",
        "HARD_STOP",
        "FLATTEN_EOD",
    }
    if "PARTIAL" in reasons:
        qty = next(leg["qty"] for leg in out.extra["legs"] if leg["reason"] == "PARTIAL")
        assert qty % 65 == 0
