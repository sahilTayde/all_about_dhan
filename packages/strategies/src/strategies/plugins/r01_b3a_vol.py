"""R01_B3A_VOL — C5 paper slot c2. Reuses desk_ml.research_rules. Live refused."""

from strategies.plugins.research_common import build_plugin

STRATEGY_ID = "R01_B3A_VOL"
strategy = build_plugin(STRATEGY_ID)
PARAMS_HASH = strategy.meta.params_hash
