"""
TEST-CROSS: Moving average crossover test plugin (shadow only).

This is a TEST-ONLY strategy used to exercise code paths in V2-06.
It should NEVER be in a real basket or move beyond shadow stage.

Signal: When fast MA crosses above slow MA, emit CE signal.
When fast crosses below slow, emit PE signal.

Exit plan: Round 11 defaults (catastrophic only, structural invalidation).
"""

from typing import Any

from strategies import (
    Bar,
    ChainSnapshot,
    ExitPlan,
    ExitRequest,
    PositionUpdate,
    SessionContext,
    Signal,
    Strategy,
    StrategyMeta,
    StrikeChoice,
    StrikeQuote,
    compute_params_hash,
)
from strategies.feature_view_stub import FeatureView

# Test strategy parameters
FAST_PERIOD = 5
SLOW_PERIOD = 20
PARAMS_DICT = {
    "fast_period": FAST_PERIOD,
    "slow_period": SLOW_PERIOD,
    "exit_plan": {
        "catastrophic_max_loss": 30000,
        "structural_stop": {"kind": "premium", "price": 0.0},  # invalidation at 0
        "flat_by_ist": "15:15",
        "defaults_from": "round11_defaults",  # placeholder for K18
    },
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


class TestCrossStrategy:
    """
    Test moving average cross strategy.

    Shadow-only. Emits signals when MAs cross. Used only to exercise
    the strategy runtime code paths in tests.
    """

    meta = StrategyMeta(
        strategy_id="TEST-CROSS",
        version="1.0.0",
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("bars:1m",),
        features=("ema_5", "ema_20"),  # Will use stub feature view in tests
        stage="shadow",
        max_positions=1,
    )

    def __init__(self) -> None:
        self.fast_ma_prev: float | None = None
        self.slow_ma_prev: float | None = None
        self.signal_count = 0

    def on_session_start(self, ctx: SessionContext) -> None:
        """Reset state at session start."""
        self.fast_ma_prev = None
        self.slow_ma_prev = None
        self.signal_count = 0

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        """
        Check for MA cross and emit signal.

        Cross-up (fast > slow and prev fast <= prev slow) -> CE
        Cross-down (fast < slow and prev fast >= prev slow) -> PE
        """
        # Get MA values from feature view (stub will return None in tests)
        fast_ma = view.get("ema_5")
        slow_ma = view.get("ema_20")

        if fast_ma is None or slow_ma is None:
            return []

        # Check for cross
        signal: Signal | None = None

        if self.fast_ma_prev is not None and self.slow_ma_prev is not None:
            # Cross-up
            if fast_ma > slow_ma and self.fast_ma_prev <= self.slow_ma_prev:
                signal = self._create_signal("CE", bar.timestamp, view)
            # Cross-down
            elif fast_ma < slow_ma and self.fast_ma_prev >= self.slow_ma_prev:
                signal = self._create_signal("PE", bar.timestamp, view)

        # Update prev values
        self.fast_ma_prev = fast_ma
        self.slow_ma_prev = slow_ma

        return [signal] if signal else []

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        """Not used by TEST-CROSS."""
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        """Not used by TEST-CROSS."""
        return []

    def on_session_end(self) -> dict[str, Any]:
        """Return day stats."""
        return {
            "signals_emitted": self.signal_count,
            "fast_period": FAST_PERIOD,
            "slow_period": SLOW_PERIOD,
        }

    def _create_signal(self, side: str, decision_ts: str, view: FeatureView) -> Signal:
        """Create a signal with test defaults."""
        self.signal_count += 1

        # Signal ID: simplified for test (real one uses contracts.ids.signal_id)
        signal_id = f"sg_test-cross-v1.0.0_{decision_ts.replace(':', '').replace('-', '')}_{self.signal_count}"

        # Strike choice: test stub
        strike_choice = StrikeChoice(
            chosen="ITM100",
            reason="TEST_DEFAULT",
            rule_version="test_v1",
            alternatives=(
                StrikeQuote(
                    rule="ATM",
                    instrument_id="NSE_FNO:NIFTY:2026-09-29:24500:CE",
                    bid=150.0,
                    ask=151.0,
                    mid=150.5,
                    spread=1.0,
                    quote_age_ms=100,
                    est_delta=0.5,
                    est_round_trip_pts=25.0,
                ),
                StrikeQuote(
                    rule="ITM100",
                    instrument_id="NSE_FNO:NIFTY:2026-09-29:24400:CE",
                    bid=160.0,
                    ask=161.0,
                    mid=160.5,
                    spread=1.0,
                    quote_age_ms=100,
                    est_delta=0.6,
                    est_round_trip_pts=26.0,
                ),
                StrikeQuote(
                    rule="ITM200",
                    instrument_id="NSE_FNO:NIFTY:2026-09-29:24300:CE",
                    bid=170.0,
                    ask=171.0,
                    mid=170.5,
                    spread=1.0,
                    quote_age_ms=100,
                    est_delta=0.7,
                    est_round_trip_pts=27.0,
                ),
            ),
        )

        # Exit plan: Round 11 defaults
        exit_plan = ExitPlan(
            catastrophic_max_loss=30000,
            structural_stop=None,  # Native invalidation would go here
            flat_by_ist="15:15",
            defaults_from="round11_defaults",
        )

        # Feature snapshot
        features = {
            "ema_5": view.get("ema_5", 0.0) or 0.0,
            "ema_20": view.get("ema_20", 0.0) or 0.0,
        }

        return Signal(
            signal_id=signal_id,
            strategy_id="TEST-CROSS",
            underlying="NIFTY",
            side=side,
            strike_rule="ROUTER",
            strike_choice=strike_choice,
            decision_ts=decision_ts,
            confidence=0.5,  # Test default
            exit_plan=exit_plan,
            reasons=("MA_CROSS", f"Fast={FAST_PERIOD} crossed {'above' if side == 'CE' else 'below'} Slow={SLOW_PERIOD}"),
            features=features,
        )


# Module-level strategy instance (runtime expects this)
strategy = TestCrossStrategy()
