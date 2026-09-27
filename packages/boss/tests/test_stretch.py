"""V2-08b: boss stretch is record-only and never changes a decision (K19)."""

from __future__ import annotations

from datetime import datetime

from contracts.clock import IST, SimClock
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

from boss.selector import (
    BarContext,
    BossSelector,
    SessionBasketGate,
    load_engine_config,
    stretch_from_location,
)


def _ist(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 28, hour, minute, tzinfo=IST)


def _choice() -> StrikeChoice:
    quote = StrikeQuote(
        rule="ITM100",
        instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
        bid=140.0,
        ask=141.0,
        mid=140.5,
        spread=1.0,
        quote_age_ms=200,
        est_delta=0.65,
        est_round_trip_pts=2.0,
    )
    return StrikeChoice(chosen="ITM100", reason="TEST", rule_version="t", alternatives=(quote,))


def _loc(zone_atr: float, ema: float = 2.4, twap: float = 3.1) -> dict[str, object]:
    return {
        "signal_candle_atr": 2.4,
        "signal_body_atr": 1.9,
        "entry_distance_atr": zone_atr,
        "atr": 6.8,
        "spot": 24512.35,
        "nearest": {"zone": "fvg", "price": 24501.5, "distance_atr": zone_atr, "source": "1m"},
        "zones": [
            {"zone": "fvg", "price": 24501.5, "distance_atr": zone_atr, "source": "1m"},
            {"zone": "ema20", "price": 24496.0, "distance_atr": ema, "source": "1m"},
            {"zone": "vwap", "price": 24488.9, "distance_atr": twap, "source": "twap"},
        ],
    }


def _signal(loc: dict[str, object], signal_id: str = "sg_a") -> Signal:
    return Signal(
        signal_id=signal_id,
        strategy_id="PAPER-A",
        underlying="NIFTY",
        side="CE",
        strike_rule="ROUTER",
        strike_choice=_choice(),
        decision_ts=_ist(10, 5).isoformat(),
        confidence=0.6,
        exit_plan=ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0))
        ),
        reasons=("TEST",),
        features={},
        entry_location=loc,
    )


def _sel() -> BossSelector:
    basket = SessionBasketGate(
        Basket(
            session="2026-09-28",
            market="IN_INDEX_OPT",
            entries=(BasketEntry("PAPER-A", ("NIFTY",), 1.0, 25, "paper"),),
            source="test",
            basket_hash="stretch07",
        )
    )
    return BossSelector(
        clock=SimClock(_ist(10, 5)),
        config=load_engine_config(),
        basket=basket,
        entry_config_hash="testhash",
    )


def _ctx() -> BarContext:
    now = _ist(10, 5)
    return BarContext(
        underlying="NIFTY",
        bar_ts=now,
        available_ts=now,
        em30=40.294117647058826,
        delta=0.5,
        stop=50.0,
        signal_stages={"PAPER-A": "paper"},
    )


def test_stretch_never_changes_a_decision() -> None:
    sel = _sel()
    ctx = _ctx()
    mild = sel.decide([_signal(_loc(0.2), "sg_mild")], ctx).decisions[0]
    huge = sel.decide([_signal(_loc(99.0), "sg_huge")], ctx).decisions[0]
    assert mild.decision == huge.decision == "ENTER"
    assert mild.lots == huge.lots
    assert list(mild.holds) == list(huge.holds)
    assert mild.instrument_id == huge.instrument_id
    assert mild.stretch is not None and huge.stretch is not None
    for block in (mild.stretch, huge.stretch):
        assert block["record_only"] is True
        assert "zone_atr" in block
        assert "ema20_atr" in block
        assert "twap_atr" in block
    assert mild.stretch["zone_atr"] == 0.2
    assert huge.stretch["zone_atr"] == 99.0
    assert huge.stretch["ema20_atr"] == 2.4
    assert huge.stretch["twap_atr"] == 3.1


def test_stretch_present_on_hold_too() -> None:
    sel = _sel()
    ctx = _ctx()
    ctx_hold = BarContext(
        underlying="NIFTY",
        bar_ts=ctx.bar_ts,
        available_ts=ctx.available_ts,
        founder_pause=True,
        em30=ctx.em30,
        delta=ctx.delta,
        stop=ctx.stop,
        signal_stages={"PAPER-A": "paper"},
    )
    out = sel.decide([_signal(_loc(1.6))], ctx_hold).decisions[0]
    assert out.decision == "HOLD"
    assert out.stretch is not None
    assert out.stretch["record_only"] is True
    assert out.stretch["zone_atr"] == 1.6
    built = stretch_from_location(_loc(1.6), "testhash")
    assert built["config_hash"] == "testhash"
