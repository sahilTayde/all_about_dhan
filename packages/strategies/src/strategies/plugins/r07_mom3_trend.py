"""R07_MOM3_TREND — C5 paper slot c4. MOM_3 0.0005 + ER30>=0.35. Live refused."""

from strategies.plugins.research_common import build_plugin

STRATEGY_ID = "R07_MOM3_TREND"
strategy = build_plugin(STRATEGY_ID)
PARAMS_HASH = strategy.meta.params_hash
