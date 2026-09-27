"""Runtime demo for V2-06: registry + basket + TEST-CROSS + isolation.

Paper / shadow only. Synthetic bars. No secrets, no orders.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from strategies.api import Bar, SessionContext
from strategies.plugins.test_cross import CrossPlugin
from strategies.registry import load_basket, load_registry
from strategies.runtime import LoadedStrategy, SessionRuntime, basket_loaded_event

_FIXTURE_BASKETS = Path(__file__).parent / "fixtures"


class _View:
    def __init__(self, values: dict[str, float]) -> None:
        self.values = values

    def get(self, name: str, instrument: str = "", tf: str = "") -> object | None:
        del instrument, tf
        return self.values.get(name)


class _Boom:
    def on_bar(self, bar: Bar, view: object) -> list[object]:
        del bar, view
        raise RuntimeError("planted raise")


def _bar(minute: int) -> Bar:
    return Bar(
        instrument_id="NSE_IDX:NIFTY",
        open=24500.0,
        high=24520.0,
        low=24490.0,
        close=24510.0,
        volume=1000,
        timestamp=f"2026-09-27T09:{minute:02d}:00+05:30",
        available_ts=f"2026-09-27T09:{minute:02d}:00+05:30",
    )


def main() -> int:
    registry = load_registry()
    print(f"registry_ids={sorted(registry)}")
    basket = load_basket(date(2026, 9, 27), "IN_INDEX_OPT", _FIXTURE_BASKETS)
    print(f"basket={'none' if basket is None else basket.basket_hash}")
    if basket is not None:
        print(f"BASKET_LOADED={basket_loaded_event(basket)}")

    good = CrossPlugin()
    good.on_session_start(SessionContext("2026-09-27", "IN_INDEX_OPT", {}))
    session = SessionRuntime(
        loaded={
            "TEST-CROSS": LoadedStrategy(strategy=good, registry_entry=None, enabled=True),
            "BOOM": LoadedStrategy(strategy=_Boom(), registry_entry=None, enabled=True),
        }
    )
    print("stage=shadow")
    session.on_bar(_bar(20), _View({"ema_5": 90.0, "ema_20": 95.0}))
    session.on_bar(_bar(21), _View({"ema_5": 101.0, "ema_20": 95.0}))
    print(f"enabled TEST-CROSS={session.loaded['TEST-CROSS'].enabled}")
    print(f"enabled BOOM={session.loaded['BOOM'].enabled}")
    print(f"disabled_reason BOOM={session.loaded['BOOM'].disabled_reason}")
    print(f"signals={[s.side for s in session.signals]}")
    print(f"alerts={[a.kind + ':' + a.strategy_id for a in session.alerts]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
