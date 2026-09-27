# premarket (PR-017)

Pre-market context for the paper desk from free public sources. **Advisory only**: it never places
orders, needs no credentials, and nothing in the engine waits for it.

```bash
python -m premarket                      # live free sources -> data/premarket/india_index_<date>.{json,md}
python -m premarket --offline            # no network: only local sources (option-chain OI walls)
python -m premarket --fixtures packages/premarket/fixtures/synthetic \
    --root packages/premarket/fixtures/synthetic/root --date 2026-09-28 --now 2026-09-28T08:30:00+05:30
scripts/premarket_brief.sh               # cron wrapper (08:30 IST, Mon-Fri)
```

- Sources, symbols, feeds and the bias / event-risk rules live in `config/premarket.yaml`.
- Each source runs in its own thread with a request timeout and a whole-run deadline. A failure is
  recorded under `sources.<name>.error` and listed in `missing`; the file is still written.
- Output (`premarket-context-v1`): `bias` (label, score, inputs, coverage, confidence),
  `event_risk` (label, reasons), `hold_new_tickets_advice`, `levels` (previous day OHLC, floor
  pivots, OI call/put walls), `intermarket`, `flows`, `headlines`, `announcements`, `missing`, `stale`.
- The rules are HYPOTHESIS (not backtested). News and event risk mean "hold the ticket", not alpha.

## Another market

Source types are registered by name (`yahoo_quotes`, `prev_day_levels`, `rss`, `nse_fii_dii`,
`local_oi_walls`). A new market is a new block under `markets:` with its own timezone, sources and
rules; a new data type is a `Source` subclass with `@register_source_type("name")`.

```yaml
markets:
  forex_majors:
    timezone: Europe/London
    sources:
      - {name: fx, type: yahoo_quotes, symbols: {EURUSD: "EURUSD=X", DXY: "DX-Y.NYB"}}
    bias_rules:
      - {metric: DXY, field: change_pct, sign: -1, threshold: 0.3}
```
