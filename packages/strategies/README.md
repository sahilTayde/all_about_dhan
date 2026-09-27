# strategies

V2 strategy runtime and registry client for `all_about_dhan`.

## Overview

This package provides the foundational types and runtime for strategy plugins:

- **Strategy API**: `StrategyMeta`, `TimeStop`, `ExitPlan`, `Signal`, `Strategy` protocol
- **Registry**: Load strategies by module path, daily basket configuration
- **Runtime**: Isolation, per-call budgets, feature/market checking, `BASKET_LOADED` event
- **Test plugins**: `TEST-CROSS` (shadow-only moving average cross for testing)

## Installation

```bash
pip install -e packages/strategies[test,dev]
```

## Usage

```python
from strategies import Signal, ExitPlan, TimeStop
from strategies.runtime import load_strategy, load_basket
from strategies.registry import load_registry

# Load registry
registry = load_registry()

# Load strategy
strategy = load_strategy("TEST-CROSS", "1.0.0", registry)

# Load daily basket
basket = load_basket(date(2026, 9, 27), "IN_INDEX_OPT")
```

## Testing

```bash
# Run tests
pytest packages/strategies

# Type check
mypy --strict packages/strategies/src

# Lint
ruff check packages/strategies
```

## Requirements

- Python ≥3.11
- `contracts` package (V2-01)
