# boss

Paper only. Never calls a broker or constructs a Dhan client.

## Packages in this tree

- **Frozen PR-007** — `orchestrator.py` (do not edit). Votes → `paper_scalp.step_decide`.
- **V2-07** — `selector.py`. Basket gate, YAML holds, conflicts, VOLSIZE/CAPLOTS,
  `DECISION` + `BOSS_SHADOW`. Uses `desk_ml.regime` for ranks only. Does **not**
  import `desk_ml.paper_scalp`.

Holds and Round 8 §3.0 constants live in `config/v2/engine.yaml` (data, not code).
`StrikeChoice` / `ExitPlan` come from `contracts.payloads`. Signals come from
`strategies.api`. Lot size comes from `contracts.instruments.India`.

## Install

```bash
pip install -e packages/boss
```

## Tests

```bash
pytest packages/boss/tests/test_selector.py packages/boss/tests/test_reg_11_boss.py
mypy --strict --config-file packages/boss/pyproject.toml packages/boss/src/boss/selector.py
ruff check packages/boss/src/boss/selector.py packages/boss/tests/test_selector.py
python packages/boss/tests/demo_selector.py
```
