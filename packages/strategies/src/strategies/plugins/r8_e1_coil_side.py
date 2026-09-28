"""E1 COIL-SIDE: long the OI-predicted coil side, exit at the break. Shadow only.

Lab logistic coefficients, q10/q90 and r8_active.py coil params are not in the
repo (Round 8 §6 step 1). Default load is PENDING_LAB and refuses.
"""

from __future__ import annotations

from typing import Any

from contracts.ids import signal_id
from contracts.payloads import CatastrophicStop, ExitPlan, Level, StructuralStop, TimeStop

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
    logistic,
)

STRATEGY_ID = "R8-E1-COIL-SIDE"
VERSION = "1.0.0"
MODEL_FEATURES = (
    "range_over_em",
    "volume_trend",
    "oi_ce_chg_lagged",
    "oi_pe_chg_lagged",
    "oi_pc_chg_lagged",
    "twap_slope",
    "tod_frac",
    "prior_trend",
    "dte",
)

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="max_loss_inr", price=30000.0)),
    time_stops=(TimeStop(after_s=900, when="always"),),
    flat_by_ist="15:15",
)
PARAMS_DICT: dict[str, Any] = {
    "coil_min_age_min": 5,
    "d_min_pts": 12.0,
    "b_em_mult": 0.15,
    "b_floor_pts": 4.0,
    "entry_start_ist": "10:00",
    "entry_end_ist": "14:45",
    "strike": "ITM100",
    "one_per_coil": True,
    "exit_plan": EXIT_PLAN,
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


class CoilSidePlugin:
    """Buy before the break on the OI-predicted side. Never places orders."""

    meta = StrategyMeta(
        strategy_id=STRATEGY_ID,
        version=VERSION,
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("bars:1m", "chain"),
        features=(*MODEL_FEATURES, "coil_active", "coil_age_min", "box_high", "box_low", "em30"),
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
        self._entered: set[str] = set()
        self._n = 0

    def on_session_start(self, ctx: SessionContext) -> None:
        del ctx
        self._entered.clear()
        self._n = 0

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        ts = as_ist(bar.available_ts)
        minute = ts.hour * 60 + ts.minute
        if minute < 10 * 60 or minute > 14 * 60 + 45:
            return []
        if feat(view, "expiry_day") or feat(view, "event_day"):
            return []
        if feat(view, "coil_active") not in (True, 1, "1"):
            return []
        age = feat_f(view, "coil_age_min")
        if age is None or age < 5:
            return []
        coil_id = str(feat(view, "coil_id") or "coil")
        if coil_id in self._entered:
            return []
        weights = self.coefficients.get("weights")
        if not isinstance(weights, dict) or "q90" not in self.coefficients:
            return []
        features: dict[str, float] = {}
        for name in MODEL_FEATURES:
            val = feat_f(view, name)
            if val is None:
                return []
            features[name] = val
        wts = {str(k): float(v) for k, v in weights.items()}
        p_up = logistic(features, wts, float(self.coefficients.get("intercept") or 0.0))
        q90 = float(self.coefficients["q90"])
        q10 = float(self.coefficients["q10"])
        if p_up >= q90:
            side = "CE"
        elif p_up <= q10:
            side = "PE"
        else:
            return []
        spot = feat_f(view, "spot") or bar.close
        em30 = feat_f(view, "em30")
        box_high = feat_f(view, "box_high")
        box_low = feat_f(view, "box_low")
        if em30 is None or box_high is None or box_low is None:
            return []
        buf = max(0.15 * em30, 4.0)
        edge = box_high if side == "CE" else box_low
        dist = abs(edge - spot) + buf
        if dist < 12.0:
            return []
        self._entered.add(coil_id)
        self._n += 1
        stop = box_low if side == "CE" else box_high
        target = (box_high + buf) if side == "CE" else (box_low - buf)
        plan = ExitPlan(
            catastrophic=EXIT_PLAN.catastrophic,
            structural=StructuralStop(
                level=Level(kind="underlying", price=stop), trigger="bar_close"
            ),
            target=Level(kind="underlying", price=target),
            time_stops=EXIT_PLAN.time_stops,
            flat_by_ist="15:15",
        )
        return [
            Signal(
                signal_id=signal_id(STRATEGY_ID, VERSION, "NIFTY", bar.available_ts, self._n),
                strategy_id=STRATEGY_ID,
                underlying="NIFTY",
                side=side,
                strike_rule="ITM100",
                strike_choice=fixed_strike("ITM100"),
                decision_ts=bar.available_ts,
                confidence=p_up,
                exit_plan=plan,
                reasons=("COIL_SIDE", f"P_UP_{p_up:.3f}", f"D_{dist:.1f}"),
                features={"p_up": p_up, "box_d": dist, "em30": em30},
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


strategy = CoilSidePlugin()
