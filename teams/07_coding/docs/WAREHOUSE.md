# DATA-001 — paper warehouse

**Department:** D1 C2  
**Code:** `packages/warehouse`  
**Default file:** `data/knowledge/warehouse.sqlite` — do **not** git-add  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. No live orders.

Creates the append-only SQLite schema from [`PRODUCT_ARCHITECTURE_STANDARDS.md`](../../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md): raw events, 1m/5m bars, 3m chain snapshots, features, signals, ticket events, outcomes, research sources, counsel cache, model runs.

```bash
python -m warehouse init
python -m warehouse status
python -m warehouse check-ticket --entry 150 --stop 96 --target 250
python -m warehouse ingest --live    # one-shot; no poll loop
python -m warehouse ingest --offline # fixtures / DI only
python -m warehouse candles --live   # 1m/5m/15m/60m/1d + resample 3m/1w
python -m warehouse bars --symbol NIFTY --tf 3m --limit 8
python -m warehouse desk-book --live   # full strikes + ATM CE/PE levels + constituent LTPs
```

Faculty plan: [`DATA_PLAN_DESK_BOOK.md`](../../00_orchestrator/docs/DATA_PLAN_DESK_BOOK.md). Weights stay `DATA_INSUFFICIENT` until an official NSE/BSE file.

**OHLC book:** table `ohlc_bars`. HQ `SOURCE_FACT` = 1m / 5m / 15m / 60m / 1d. **3m** = 1m resample (not an HQ interval). **1w** = daily resample. Read via `Warehouse.load_bars(symbol, tf)` for live or history. Do not claim a 3m Dhan REST field.

Protected paths (open refused): `transcripts.sqlite`, `trading_agents_india.sqlite`, `agent_rag.sqlite`.

**Ingest (2026-09-10):** `ingest --live` writes compact ATM/PCR + last 180 INDEX 1m bars + paper MIX score + dealer reason. Full option-chain `oc` is **not** stored. **No** market-hours loop.

**Not this ticket:** `/pm` read model, local ML training, sqlite-vec, paper poll loop.
