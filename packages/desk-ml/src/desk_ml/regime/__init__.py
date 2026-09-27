"""Regime service (PR-012 / PR-024): minute labels, intermarket regime, adaptive analyst weights, overlay.

Paper only. Default mode is `shadow` (config/regime.yaml): computed and logged next to the static
decision, trades unchanged.
"""

from desk_ml.regime.intermarket import intermarket_regime, overlay_decision, regime_for_session
from desk_ml.regime.labels import LabelConfig, RegimeLabeller, label_bars
from desk_ml.regime.shadow import RegimeConfig, RegimeShadow, boss_hook, load_config, use_runner
from desk_ml.regime.weights import WeightConfig, WeightState, cap_shares, weighted_picker

__all__ = [
    "LabelConfig", "RegimeConfig", "RegimeLabeller", "RegimeShadow", "WeightConfig", "WeightState",
    "boss_hook", "cap_shares", "intermarket_regime", "label_bars", "load_config", "overlay_decision",
    "regime_for_session", "use_runner", "weighted_picker",
]
