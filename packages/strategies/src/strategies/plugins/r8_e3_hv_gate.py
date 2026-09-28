"""E3 HV-GATE: shadow overlay that would skip the quietest third of days.

Never blocks a live entry and never emits one. Pre-open HAR only (V2-18).
Lab hash of the HAR forecast code is not recorded; default load is PENDING_LAB.
"""

from __future__ import annotations

from typing import Any

from contracts.payloads import CatastrophicStop, ExitPlan, Level

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
from strategies.plugins.lab_lock import PENDING_LAB, history_f, tercile

STRATEGY_ID = "R8-E3-HV-GATE"
VERSION = "1.0.0"

EXIT_PLAN = ExitPlan(
    catastrophic=CatastrophicStop(level=Level(kind="max_loss_inr", price=30000.0)),
    flat_by_ist="15:15",
)
PARAMS_DICT: dict[str, Any] = {
    "role": "overlay_flag_only",
    "skip_tercile": 1,
    "har_source": "preopen",
    "never_block": True,
    "exit_plan": EXIT_PLAN,
}
PARAMS_HASH = compute_params_hash(PARAMS_DICT)


class HvGatePlugin:
    """Flag quiet-HAR days. Never emits, never blocks, never places orders."""

    meta = StrategyMeta(
        strategy_id=STRATEGY_ID,
        version=VERSION,
        params_hash=PARAMS_HASH,
        markets=("IN_INDEX_OPT",),
        underlyings=("NIFTY",),
        inputs=("premarket",),
        features=("har_forecast_preopen",),
        stage="shadow",
        max_positions=0,
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
        self.would_skip = False

    def on_session_start(self, ctx: SessionContext) -> None:
        cfg = ctx.config
        band = cfg.get("har_tercile")
        har = cfg.get("har_forecast_preopen")
        hist = history_f(cfg.get("har_trailing_250"))
        if band is None and isinstance(har, (int, float)) and not isinstance(har, bool):
            band = tercile(float(har), hist)
        self.would_skip = int(band) == 1 if isinstance(band, (int, float)) else False

    def flag(self, view: FeatureView | None = None) -> bool:
        """Would-skip from pre-open state only. `view` is ignored (no look-ahead)."""
        del view
        return self.would_skip

    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]:
        del bar, view
        return []

    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]:
        del snap, view
        return []

    def on_position(self, update: PositionUpdate) -> list[ExitRequest]:
        del update
        return []

    def on_session_end(self) -> dict[str, Any]:
        return {"would_skip": self.would_skip, "signals_emitted": 0, "stage": "shadow"}


strategy = HvGatePlugin()
