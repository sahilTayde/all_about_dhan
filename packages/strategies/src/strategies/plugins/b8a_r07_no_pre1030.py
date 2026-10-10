"""B8A_R07_NO_PRE1030 — C5 paper slot c5. R07 after 10:30. Live refused."""

from strategies.plugins.research_common import build_plugin

STRATEGY_ID = "B8A_R07_NO_PRE1030"
strategy = build_plugin(STRATEGY_ID)
PARAMS_HASH = strategy.meta.params_hash
