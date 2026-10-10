"""R01_PDIV_5_ALL_H20 — C5 paper slot c1. Reuses desk_ml.research_rules. Live refused."""

from strategies.plugins.research_common import build_plugin

STRATEGY_ID = "R01_PDIV_5_ALL_H20"
strategy = build_plugin(STRATEGY_ID)
PARAMS_HASH = strategy.meta.params_hash
