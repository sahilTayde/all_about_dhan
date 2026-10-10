# strategies

V2 strategy runtime, registry client, and strike router. Paper only; never places orders.

## Packages in this tree

- **V2-06** — `api.py`, `registry.py`, `runtime.py`, `params_hash.py`, `onboarding.py` (K9)
- **V2-06b** — `strikes.py` (unchanged from PR #43)
- `StrikeChoice` / `StrikeQuote` / `ExitPlan` come from `contracts.payloads` (single definition)

`FeatureView` in `feature_view_stub.py` is a **stub** to be replaced by `packages/indicators` (V2-05).

C5 paper research slots (option buying only; live refused) live in
`strategies.plugins.r01_pdiv_5_all_h20`, `r01_b3a_vol`, `b8b_b3a_ex_choppy`,
`r07_mom3_trend`, `b8a_r07_no_pre1030`. R01 / B3A math is called from
`desk_ml.research_rules` (not copied). Accounts stay disabled until Market ops
sets `strategy_id` on `customer-01`..`05`.

## Install

```bash
pip install -e packages/strategies
```

## Tests

```bash
pytest packages/strategies
mypy --strict packages/strategies/src
ruff check packages/strategies
```
