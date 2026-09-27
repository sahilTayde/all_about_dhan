# marketdata — V2-D2 depth, quote-snapshot and OI-cadence recorder

Records the Dhan live feed for one index (NIFTY by default) during the NSE session:
5-level depth at ≤ 1 s, bid/ask snapshots every 5 s, and how often OI actually changes.
**Record only.** It reads REST market-data endpoints and the websocket feed; it has no order
code path. It runs standalone, without the engine.

## Install (once)

From the repo root, in the repo's virtualenv (`.cursor/install.sh` does this too). In-repo
packages must be installed on one command, as everywhere in this repo
(`docs/PHASE2_NOTES.md`): `dhan-client` is pinned to the local version `0.1.0+aad`, which PyPI
can never satisfy, so `pip install -e packages/marketdata` on its own fails by design.

```bash
python3 -m venv .venv && source .venv/bin/activate      # skip if .venv exists
python -m pip install -e packages/dhan-client -e packages/marketdata
```

Python 3.10 or newer. For the tests add `pytest jsonschema rfc3339-validator`.

## Credentials

`DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN`, from the environment or the repo-root `.env`
(never commit it). Access tokens expire every 24 hours: generate a fresh one before the session.
Without them the recorder refuses to start (exit code 2). The token is scrubbed from every log
line at every level.

## Run (Monday)

```bash
source .venv/bin/activate
python -m marketdata --record-only
```

- Start it any time before the open. It loads instruments at once (so a bad token or network
  problem shows up immediately), then waits and connects at **09:13 IST**. It stops by itself
  at **15:30 IST**. Started after 15:30 or on a weekend, it waits for the next weekday session.
- Stop early with Ctrl-C or `kill <pid>` (SIGTERM): buffers are flushed and the coverage
  summary is written. Exit codes: 0 clean stop, 1 unexpected error, 2 credentials/startup.
- Keep the Mac awake for the session (`caffeinate -dimsu python -m marketdata --record-only`).
- Dhan allows 5 feed connections per user. Other feed consumers (the legacy data recorder,
  `apps/api` live proxy) count towards that; if Dhan closes the feed with code 805 the
  recorder logs it and reconnects.
- Options: `--underlying NIFTY|BANKNIFTY|SENSEX`, `--tape-root PATH`.
  `python -m marketdata --coverage YYYY-MM-DD` recomputes the coverage summary.

The live service (V2-12) is a **separate** entry point so Monday's `--record-only` CLI stays the same:

```bash
python -m marketdata.dhan_ws --mode live-data
python -m marketdata.dhan_ws --mode replay --tape /path/to/ticks.jsonl
```

`--mode live-data` refuses to start without `DHAN_CLIENT_ID` / `DHAN_ACCESS_TOKEN`. `--mode replay` needs no credentials and plays a tape into an in-process publisher (or Redis with `--redis-url`).

### Live bars (V2-12)

- **LTT or it does not make the bar.** A tick is published either way. `ts_source='ltt'` when packet LTT is present, non-zero, and within one hour of receive time; otherwise `ts_source='recv'`. Recv-stamped ticks (missing or zero LTT, or LTT outside the window) do **not** update bar OHLC. `BarBuilder` never sees them. They increment `unstamped_ticks` on the next closed bar for that instrument.
- **STALE / DOWN gap bars are not published.** A 1m bar whose `[start, end)` overlaps a STALE or DOWN period, or that closes while the feed is STALE or DOWN, is dropped (`suppressed_bars`). Downstream sees the hole via `FEED_STATUS` and the missing `BAR_CLOSED`. Published bars carry `feed_quality='OK'`. No clean-looking OHLC is emitted for the gap.
- **In-process publisher is bounded.** With no `--redis-url`, the live path uses `MemoryPublisher` (`deque`, default `maxlen=10_000`). It is not an unbounded list. Redis `XADD` stays the production sink.
- **No order client.** `python -m marketdata.dhan_ws` loads `dhan_client.feed` / REST instrument and chain helpers only. It does not import `dhan_client.client` or `dhan_client.execution`.

## What it records

At startup: the scrip master CSV (cached daily in `data/cache/marketdata/`), the nearest
expiry from `/optionchain/expirylist` (Tuesday for NIFTY weeklies), spot and per-strike
security ids from `/optionchain`, and the nearest index future. Network failures are retried
until 09:20 IST, then the last cached instrument set (same or later expiry) is used; bad
credentials fail at once with a one-line message.

Instruments: the index, the nearest future, and ATM / ITM100 / ITM200 on both sides
(CE ITM = strikes below spot, PE ITM = strikes above), subscribed in FULL mode. When spot moves
more than half a strike step (+ hysteresis) the set re-centres: new strikes are subscribed on
the open socket; strikes that left keep streaming for 10 minutes, then are unsubscribed.

Tapes: `data/tape/v2/YYYY-MM-DD/` (IST date; gitignored). Every row of the first four files is
an Envelope v2 (`timestamp`/`available_ts` = when written, `event_ts` = when the data arrived)
whose `payload` matches the V2-01 schema vendored in `src/marketdata/schemas/`.

| File | Contents |
|---|---|
| `depth_quotes.jsonl` | `DEPTH_QUOTE` per instrument: on change (≤ 1 per 250 ms) and a heartbeat (`repeat: true`) so there is a row at least once per second. `exchange_ts` = receive time of the packet the data came from, so a heartbeat shows the data age. `raw_b64` = the packet bytes while the FULL decoder is unverified. |
| `quote_snapshots.jsonl` | `QUOTE_SNAPSHOT` for the six traded strikes on every 5 s boundary: bid, ask, mid, spread, LTP, LTT, OI, `depth_age_ms`, `stale` (no packet for > 5 s). |
| `oi_cadence.jsonl` | `OI_CADENCE` per option/future for each minute window: changes, median and p90 seconds between changes, last change time. |
| `feed_status.jsonl` | `FEED_STATUS`: UP/DOWN (with gap), STALE/FRESH per instrument, disconnect codes. |
| `raw_frames.jsonl` | Every websocket frame, base64, while `DECODER_VERIFIED` is false. |
| `ingest_errors.jsonl` | Every bad frame or packet (reason, offset, sha256, bytes), text frames, unknown ids, and any tail repaired after a crash. |
| `subscriptions.jsonl` | Every subscribe/unsubscribe with reason, rule, spot and ATM. |
| `coverage_summary.json` | Written at stop: per instrument, % of subscribed market minutes with depth and the gap list (M1 gate ≥ 95%). |
| `recorder.log` | The run log. |

Crash safety: rows are appended in whole lines and fsynced every second on a background
thread. A kill loses at most the last second; on restart a partial last line or NUL tail is
cut back to the last newline and reported in `ingest_errors`. Restarting mid-day appends.

Known unknowns (kept verifiable through `raw_frames.jsonl`): the INDEX packet layout
(LTP read from the first float, as V2-D1 does) and whether the feed's LTT epoch is UTC or
IST-shifted (decided once per run from the first trade and logged). If no index tick arrives
for 20 s, spot for re-centring comes from the option chain every 30 s.

## Tests

```bash
python -m pytest packages/marketdata -q
PYTHONPATH=packages/marketdata/tests python packages/marketdata/tests/md_soak.py /tmp/soak 1519
```

Tests use an in-process websocket server on 127.0.0.1 and temporary directories only.
