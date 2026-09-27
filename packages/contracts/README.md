# contracts

V2 event contracts, envelope, and market adapters for `all_about_dhan`.

## Overview

This package provides the foundational types for V2 architecture:

- **Event Envelope**: V2 event wrapper (extends legacy `events.schema.Event`)
- **Payload Types**: All section 4.4 event payloads (TICK, SIGNAL, DECISION, FILL, etc.)
- **JSON Schemas**: Draft 7 schemas with `additionalProperties: false` and format checkers
- **Validation**: JSON-to-dataclass loaders with schema validation
- **IDs**: Deterministic ID generation (`order_id`, `event_id`, `signal_id`)
- **Clock**: `SimClock` (deterministic) and `LiveClock` (IST wall-clock)
- **Market Adapters**: `India` adapter with NSE calendar, session hours, tick/lot sizes

## Installation

```bash
pip install -e packages/contracts[test,dev]
```

## Usage

```python
from contracts import Envelope, India, order_id, signal_id, load_tick

# Generate IDs
oid = order_id("acc123", "sg_r8e1_nifty_20260927_1001_0", "entry")
print(oid)  # "aad..." (27 chars)

# Market adapter
india = India()
print(india.is_open(datetime(2026, 9, 27, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))))  # True

# Load and validate payload
tick_data = {"instrument_id": "NSE_FNO:NIFTY:2026-09-29:24500:CE", "ltp": 150.0, ...}
tick = load_tick(tick_data)  # validates against JSON schema
```

## Testing

```bash
# Run tests
pytest packages/contracts

# Property tests (requires hypothesis)
pytest packages/contracts/tests/test_properties.py

# REG-11 guard tests
pytest packages/contracts/tests/test_reg_11.py -m reg11a_probe
```

## REG-11 Guard

The root `conftest.py` audit hook blocks test writes to `data/` and `config/`. Tests must use `tmp_path`.

## Requirements

- Python ≥3.11
- `jsonschema` (test extra)
- `hypothesis` (test extra, optional)
