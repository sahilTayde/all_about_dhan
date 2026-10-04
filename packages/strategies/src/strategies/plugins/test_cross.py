"""TEST-CROSS: moving-average crossover. Shadow-only test plugin.

Never put this in a real basket. Used only to exercise V2-06 code paths.
"""

from __future__ import annotations

from typing import Any

from contracts.payloads import CatastrophicStop, ExitPlan, Level, StrikeChoice, StrikeQuote

from strategies.api import (
    Bar,
    ChainSnapshot,
    EntryPolicy,
    ExitRequest,
    PositionUpdate,
    SessionContext,
    Signal,
    StrategyMeta,
)
from strategies.feature_view_stub import FeatureView
from strategies.params_hash import compute_params_hash

FAST_PERIOD = 5
SLOW_PERIOD = 20

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="premium", price=30000.0)),
    structural=None,
    flat_by_ist="15:15",
    defaults_from=None,
)

PARAMS_DICT: dict[str, Any] = {
    "fast_period": FAST_PERIOD,
    "slow_period": SLOW_PERIOD,
    "exit_plan": EXIT_PLAN,
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


class CrossPlugin:
    """Shadow-only MA cross. Emits CE on cross-up, PE on cross-down."""

    meta = StrategyMeta(
        strategy_id="TEST-CROSS",
        version="1.0.0",
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("bars:1m",),
        features=("ema_5", "ema_20"),
        stage="shadow",
        max_positions=1,
        entry_policy=EntryPolicy(),
        legacy_logic_from=(),
    )
    exit_plan = EXIT_PLAN

    def __init__(self) -> None:
        self.fast_ma_prev: float | None = None
        self.slow_ma_prev: float | None = None
        self.signal_count = 0

    def on_session_start(self, ctx: SessionContext) -> None:
        del ctx
        self.fast_ma_prev = None
        self.slow_ma_prev = None
        self.signal_count = 0

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        fast_raw = view.get("ema_5")
        slow_raw = view.get("ema_20")
        if not isinstance(fast_raw, (int, float)) or not isinstance(slow_raw, (int, float)):
            return []
        fast_ma = float(fast_raw)
        slow_ma = float(slow_raw)
        signal: Signal | None = None
        if self.fast_ma_prev is not None and self.slow_ma_prev is not None:
            if fast_ma > slow_ma and self.fast_ma_prev <= self.slow_ma_prev:
                signal = self._create_signal("CE", bar.available_ts, fast_ma, slow_ma)
            elif fast_ma < slow_ma and self.fast_ma_prev >= self.slow_ma_prev:
                signal = self._create_signal("PE", bar.available_ts, fast_ma, slow_ma)
        self.fast_ma_prev = fast_ma
        self.slow_ma_prev = slow_ma
        return [signal] if signal else []

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        del snap, view
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        del update
        return []

    def on_session_end(self) -> dict[str, Any]:
        return {"signals_emitted": self.signal_count}

    def _create_signal(self, side: str, decision_ts: str, fast_ma: float, slow_ma: float) -> Signal:
        self.signal_count += 1
        stamp = decision_ts.replace(":", "").replace("-", "")
        signal_id = f"sg_test-cross-v1.0.0_{stamp}_{self.signal_count}"
        empty = StrikeQuote(
            rule="ATM",
            instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
            bid=None,
            ask=None,
            mid=None,
            spread=None,
            quote_age_ms=None,
            est_delta=None,
            est_round_trip_pts=None,
        )
        choice = StrikeChoice(
            chosen="ITM100",
            reason="TEST_DEFAULT",
            rule_version="test_v1",
            alternatives=(empty,),
        )
        direction = "above" if side == "CE" else "below"
        return Signal(
            signal_id=signal_id,
            strategy_id="TEST-CROSS",
            underlying="NIFTY",
            side=side,
            strike_rule="ROUTER",
            strike_choice=choice,
            decision_ts=decision_ts,
            confidence=0.5,
            exit_plan=self.exit_plan,
            reasons=("MA_CROSS", f"Fast={FAST_PERIOD} crossed {direction} Slow={SLOW_PERIOD}"),
            features={"ema_5": fast_ma, "ema_20": slow_ma},
        )


strategy = CrossPlugin()
