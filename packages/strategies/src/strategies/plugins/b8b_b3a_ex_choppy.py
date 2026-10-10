"""B8B_B3A_EX_CHOPPY — C5 paper slot c3. B3a + ER30>=0.20. Live refused."""

from strategies.plugins.research_common import build_plugin

STRATEGY_ID = "B8B_B3A_EX_CHOPPY"
strategy = build_plugin(STRATEGY_ID)
PARAMS_HASH = strategy.meta.params_hash
