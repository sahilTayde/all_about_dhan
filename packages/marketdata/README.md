# marketdata

V2 market data recorder: depth, quotes, and OI cadence (V2-D2).

## Scope

- Traded-strike set per basket underlying (NIFTY first; SENSEX config-ready)
- FULL-mode subscription through `dhan_client.feed` (reuses `MarketFeedCollector`)
- `DEPTH_QUOTE` at most once per second per instrument (throttled to 250ms, 1s heartbeat)
- `QUOTE_SNAPSHOT` with bid/ask every 5s
- `OI_CADENCE` every minute
- `TapeWriter` writes to `data/tape/v2/YYYY-MM-DD/` (append-only JSONL)
- Runs standalone, without the engine. No Redis required for recording.

## Usage

```bash
python -m runtime marketdata --record-only
```

## Testing

Paper only. No live orders. No credentials in tests.
