"""V2-08b: boss records stretch with no veto power (K19 / addendum 6)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from contracts.clock import IST, SimClock
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

from boss.selector import (
    BarContext,
    BossSelector,
    SessionBasketGate,
    load_engine_config,
    record_stretch,
)

REPO_ENGINE = Path("config/v2/engine.yaml")


def _ist(hour: int = 10, minute: int = 5) -> datetime:
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
    return StrikeChoice(
        chosen="ITM100",
        reason="TEST_ROUTER",
        rule_version="router-test",
        alternatives=(quote,),
    )


def _signal(signal_id: str = "sg_a") -> Signal:
    when = _ist()
    return Signal(
        signal_id=signal_id,
        strategy_id="PAPER-A",
        underlying="NIFTY",
        side="CE",
        strike_rule="ROUTER",
        strike_choice=_choice(),
        decision_ts=when.isoformat(),
        confidence=0.6,
        exit_plan=ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0))
        ),
        reasons=("TEST",),
        features={"ema_5": 1.0},
    )


def _basket() -> SessionBasketGate:
    return SessionBasketGate(
        basket=Basket(
            session="2026-09-28",
            market="IN_INDEX_OPT",
            entries=(
                BasketEntry(
                    strategy_id="PAPER-A",
                    underlyings=("NIFTY",),
                    weight=1.0,
                    max_lots=25,
                    stage="paper",
                ),
            ),
            source="test",
            basket_hash="testhash08b",
        )
    )


def _location(*, zone_atr: float, ema: float, twap: float) -> dict[str, object]:
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


def _ctx(now: datetime, loc: dict[str, object], stretch_hash: str = "e4a0") -> BarContext:
    return BarContext(
        underlying="NIFTY",
        bar_ts=now,
        available_ts=now,
        feed_status="UP",
        em30=40.294117647058826,
        delta=0.5,
        stop=50.0,
        regime_label="trend_up",
        signal_stages={"PAPER-A": "paper"},
        entry_location=loc,
        entry_config_hash=stretch_hash,
    )


def test_stretch_record_only_identical_decisions() -> None:
    """Stretch far above any plausible threshold does not change ENTER/HOLD or lots."""
    clock = SimClock(_ist())
    sel = BossSelector(clock=clock, config=load_engine_config(REPO_ENGINE), basket=_basket())
    mild = _location(zone_atr=0.2, ema=0.3, twap=0.4)
    extreme = _location(zone_atr=99.0, ema=80.0, twap=70.0)
    now = clock.now()
    a = sel.decide([_signal()], _ctx(now, mild))
    b = sel.decide([_signal()], _ctx(now, extreme))
    da, db = a.decisions[0], b.decisions[0]
    assert da.decision == db.decision == "ENTER"
    assert da.lots == db.lots
    assert da.signal_ids == db.signal_ids
    assert list(da.holds) == list(db.holds)
    assert da.instrument_id == db.instrument_id
    assert da.sizing == db.sizing
    assert da.stretch is not None and db.stretch is not None
    assert da.stretch["record_only"] is True
    assert db.stretch["zone_atr"] == 99.0
    assert da.stretch["zone_atr"] == 0.2
    assert da.stretch["ema20_atr"] == 0.3
    assert da.stretch["twap_atr"] == 0.4
    assert set(da.stretch) >= {"record_only", "zone_atr", "ema20_atr", "twap_atr", "zone"}


def test_stretch_block_present_on_hold_and_enter() -> None:
    """Every decision carries the stretch block, including HOLD (no veto)."""
    clock = SimClock(_ist(9, 20))
    sel = BossSelector(clock=clock, config=load_engine_config(REPO_ENGINE), basket=_basket())
    loc = _location(zone_atr=1.6, ema=2.4, twap=3.1)
    out = sel.decide([_signal()], _ctx(clock.now(), loc))
    d = out.decisions[0]
    assert d.decision == "HOLD"
    assert d.stretch is not None
    assert d.stretch["record_only"] is True
    assert d.stretch["zone_atr"] == 1.6
    assert d.stretch["ema20_atr"] == 2.4
    assert d.stretch["twap_atr"] == 3.1
    empty = record_stretch(None, "abc")
    assert empty["record_only"] is True
    assert empty["config_hash"] == "abc"
