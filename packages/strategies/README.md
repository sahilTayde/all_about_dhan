# strategies

V2 strategy runtime, registry client, and strike router. Paper only; never places orders.

## Packages in this tree

- **V2-06** — `api.py`, `registry.py`, `runtime.py`, `params_hash.py`, `onboarding.py` (K9)
- **V2-06b** — `strikes.py` (unchanged from PR #43)
- `StrikeChoice` / `StrikeQuote` / `ExitPlan` come from `contracts.payloads` (single definition)

`FeatureView` in `feature_view_stub.py` is a **stub** to be replaced by `packages/indicators` (V2-05).

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
