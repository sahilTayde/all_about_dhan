"""V2-07 runtime demo: boss selector on synthetic IST bars, shadow mode.

Paper / shadow only. No secrets, no orders, no Dhan client.
"""

from __future__ import annotations

from datetime import datetime

from contracts.clock import IST, SimClock
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote
from strategies.api import Signal
from strategies.registry import Basket, BasketEntry

from boss.selector import (
    BarContext,
    BossSelector,
    SelectorResult,
    SessionBasketGate,
    load_engine_config,
)


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


def _signal(sid: str, signal_id: str, side: str, ts: datetime) -> Signal:
    return Signal(
        signal_id=signal_id,
        strategy_id=sid,
        underlying="NIFTY",
        side=side,
        strike_rule="ROUTER",
        strike_choice=_choice(),
        decision_ts=ts.isoformat(),
        confidence=0.6,
        exit_plan=ExitPlan(
            catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0))
        ),
        reasons=("DEMO",),
        features={},
    )


def _ctx(now: datetime, **overrides: object) -> BarContext:
    base: dict[str, object] = {
        "underlying": "NIFTY",
        "bar_ts": now,
        "available_ts": now,
        "feed_status": "UP",
        "em30": 40.294117647058826,
        "delta": 0.5,
        "stop": 50.0,
        "regime_label": "trend_up",
        "intermarket": {"regime": "risk_on"},
        "weights": {"PAPER-A": 1.2, "PAPER-B": 0.8},
        "signal_stages": {"PAPER-A": "paper", "PAPER-B": "paper", "SHADOW-X": "shadow"},
    }
    base.update(overrides)
    return BarContext(**base)  # type: ignore[arg-type]


def _show(label: str, result: SelectorResult) -> None:
    decisions = result.decisions
    shadows = result.shadow_events
    print(f"--- {label} ---")
    for d in decisions:
        holds = list(d.holds) if d.holds else []
        print(
            f"decision={d.decision} id={d.decision_id} lots={d.lots} "
            f"lot_size={d.lot_size} sizing={d.sizing} holds={holds} "
            f"signals={d.signal_ids} basket={d.basket_hash}"
        )
        if d.shadow:
            print(
                f"shadow.regime={d.shadow.get('regime')} "
                f"shadow.mode={d.shadow.get('mode')} "
                f"strike_choice={d.shadow.get('strike_choice')}"
            )
    for ev in shadows:
        print(
            f"BOSS_SHADOW mode={ev.get('mode')} regime={ev.get('regime')} "
            f"unchanged={ev.get('decision_unchanged')} ranks={ev.get('ranks')}"
        )


def main() -> int:
    cfg = load_engine_config()
    print(f"engine_hash={cfg.config_hash} regime.mode={cfg.regime_mode} tz=+05:30")
    basket = SessionBasketGate(
        Basket(
            session="2026-09-28",
            market="IN_INDEX_OPT",
            entries=(
                BasketEntry("PAPER-A", ("NIFTY",), 1.0, 25, "paper"),
                BasketEntry("PAPER-B", ("NIFTY",), 1.0, 25, "paper"),
                BasketEntry("SHADOW-X", ("NIFTY",), 1.0, 10, "shadow"),
            ),
            source="demo",
            basket_hash="demo07",
        )
    )
    clock = SimClock(datetime(2026, 9, 28, 9, 20, tzinfo=IST))
    sel = BossSelector(clock=clock, config=cfg, basket=basket)
    print(f"clock={clock.now().isoformat()} stage=shadow")

    t0 = clock.now()
    _show("09:20 IST OPEN_NO_BUY", sel.decide([_signal("PAPER-A", "sg_open", "CE", t0)], _ctx(t0)))

    t1 = datetime(2026, 9, 28, 10, 5, tzinfo=IST)
    clock.advance_to(t1)
    print(f"clock={clock.now().isoformat()}")
    _show("10:05 IST ENTER paper", sel.decide([_signal("PAPER-A", "sg_enter", "CE", t1)], _ctx(t1)))

    _show(
        "10:05 IST HOLD CONFLICT",
        sel.decide(
            [
                _signal("PAPER-A", "sg_ce", "CE", t1),
                _signal("PAPER-B", "sg_pe", "PE", t1),
            ],
            _ctx(t1, weights={"PAPER-A": 1.0, "PAPER-B": 1.0}),
        ),
    )

    _show(
        "10:05 IST shadow stage dropped",
        sel.decide([_signal("SHADOW-X", "sg_sh", "CE", t1)], _ctx(t1)),
    )

    _show(
        "10:05 IST FEED_STALE",
        sel.decide([_signal("PAPER-A", "sg_stale", "CE", t1)], _ctx(t1, feed_status="STALE")),
    )

    _show(
        "10:05 IST BELOW_MIN_LOTS",
        sel.decide([_signal("PAPER-A", "sg_tiny", "CE", t1)], _ctx(t1, em30=685.0)),
    )

    sel.basket_remove("PAPER-A")
    _show(
        "10:05 IST after BASKET_REMOVE PAPER-A",
        sel.decide([_signal("PAPER-A", "sg_rm", "CE", t1)], _ctx(t1)),
    )

    try:
        sel.basket_add(BasketEntry("NEW-X", ("NIFTY",), 1.0, 10, "paper"))
        print("BASKET_ADD unexpectedly accepted")
    except Exception as exc:
        print(f"BASKET_ADD rejected: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
