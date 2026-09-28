"""E2 P5-HV: fade the overnight gap at 09:30 on high-vol days. Shadow only.

Uses only pre-open HAR (V2-18 PRE_MARKET_SUMMARY). Never reads 09:59 HARI —
that look-ahead is confirmed in Round 8 §5. Lab hash of the HAR code is not
recorded; default load is PENDING_LAB and refuses.
"""

from __future__ import annotations

from typing import Any

from contracts.ids import signal_id
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StructuralStop

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
from strategies.plugins.lab_lock import (
    PENDING_LAB,
    as_ist,
    feat,
    feat_f,
    fixed_strike,
    history_f,
    tercile,
)

STRATEGY_ID = "R8-E2-P5-HV"
VERSION = "1.0.0"

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="max_loss_inr", price=30000.0)),
    time_stops=(),
    flat_by_ist="15:15",
)
PARAMS_DICT: dict[str, Any] = {
    "decision_ist": "09:30",
    "gap_min_atr": 0.1,
    "gap_max_atr": 2.0,
    "one_per_day": True,
    "har_source": "preopen",
    "strike_dte_ge2": "ITM100",
    "strike_else": "ITM200",
    "stop_em": 1.0,
    "target_em": 2.0,
    "exit_plan": EXIT_PLAN,
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


class P5HvPlugin:
    """Fade the overnight gap. Pre-open HAR only. Never places orders."""

    meta = StrategyMeta(
        strategy_id=STRATEGY_ID,
        version=VERSION,
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("bars:1m",),
        features=(
            "har_forecast_preopen",
            "session_open",
            "prev_close",
            "atr14_daily",
            "em30",
            "dte",
        ),
        stage="shadow",
        max_positions=1,
        entry_policy=EntryPolicy(),
        legacy_logic_from=(),
    )
    exit_plan = EXIT_PLAN
    prereg_status = PENDING_LAB
    prereg_lab_hash: str | None = None
    lab_coeff_hash: str | None = None

    def __init__(self, coefficients: dict[str, Any] | None = None) -> None:
        self.coefficients = dict(coefficients or {})
        self.prereg_status = str(self.coefficients.get("prereg_status") or PENDING_LAB)
        raw_hash = self.coefficients.get("sha256")
        self.lab_coeff_hash = str(raw_hash) if raw_hash else None
        self.prereg_lab_hash = (
            str(self.coefficients["prereg_sha256"])
            if self.coefficients.get("prereg_sha256")
            else None
        )
        self._used = False
        self._n = 0

    def on_session_start(self, ctx: SessionContext) -> None:
        del ctx
        self._used = False
        self._n = 0

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        ts = as_ist(bar.available_ts)
        if ts.hour != 9 or ts.minute != 30:
            return []
        if self._used:
            return []
        if feat(view, "event_day"):
            return []
        har = feat_f(view, "har_forecast_preopen")
        band = feat_f(view, "har_tercile")
        if band is None and har is not None:
            computed = tercile(har, history_f(feat(view, "har_trailing_250")))
            band = float(computed) if computed is not None else None
        if band != 3:
            return []
        open_px = feat_f(view, "session_open")
        prev = feat_f(view, "prev_close")
        atr = feat_f(view, "atr14_daily")
        em30 = feat_f(view, "em30")
        dte = feat_f(view, "dte")
        if open_px is None or prev is None or atr is None or em30 is None or dte is None:
            return []
        if atr <= 0:
            return []
        gap = open_px - prev
        if abs(gap) < 0.1 * atr or abs(gap) > 2.0 * atr:
            return []
        side = "PE" if gap > 0 else "CE"
        rule = "ITM100" if dte >= 2 else "ITM200"
        spot = bar.close
        stop = spot - em30 if side == "CE" else spot + em30
        target = spot + 2.0 * em30 if side == "CE" else spot - 2.0 * em30
        plan = ExitPlan(
            catastrophic=EXIT_PLAN.catastrophic,
            structural=StructuralStop(
                level=Level(kind="underlying", price=stop), trigger="bar_close"
            ),
            target=Level(kind="underlying", price=target),
            time_stops=(),
            flat_by_ist="15:15",
        )
        self._used = True
        self._n += 1
        return [
            Signal(
                signal_id=signal_id(STRATEGY_ID, VERSION, "NIFTY", bar.available_ts, self._n),
                strategy_id=STRATEGY_ID,
                underlying="NIFTY",
                side=side,
                strike_rule=rule,
                strike_choice=fixed_strike(rule),
                decision_ts=bar.available_ts,
                confidence=0.0,
                exit_plan=plan,
                reasons=("P5_HV", "FADE_GAP", "HAR_PREOPEN_TOP_TERCILE"),
                features={"gap": gap, "har_forecast_preopen": har or 0.0, "em30": em30},
            )
        ]

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        del snap, view
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        del update
        return []

    def on_session_end(self) -> dict[str, Any]:
        return {"signals_emitted": self._n, "stage": "shadow"}


strategy = P5HvPlugin()
