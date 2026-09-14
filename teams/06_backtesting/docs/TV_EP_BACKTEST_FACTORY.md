# TV Editor Picks backtest factory (NO_PROMOTE)

**Team:** 06 backtesting (harness) · 02 math (regime/costs REVIEW) · 04 quant (MIX ids) · 01 research (catalog fill)  
**Status:** `HYPOTHESIS` / harness **coded** / **UNVALIDATED**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**IDs:** `MIX-TV-EP-NNN` only. **KEEP_ALL** `STRAT-001`–`014`. Never `STRAT-015+`.  
**Orders:** refused. `ExecutionClient` stays SafeMode. Do not start npm / paper market-hours.

Catalog folder: [`refernece_tradingview/editors_picks/`](../../../refernece_tradingview/editors_picks/) — **2026-09-14 fill:** 23 listing-order EPs (`MIX-TV-EP-001`–`023`), `adapter: stub`, origin `WEB-DERIVED/TV-EDITOR-PICK`. SMA/MACD adapters stay in code for later ports; they **do not** own IDs 001/002.  
Code: `packages/backtest/src/backtest_engine/tv_ep/`  
CLI: `python -m backtest_engine tv-ep-grid` · counsel: `python -m backtest_engine tv-ep-counsel`

---

## Honesty banner (same class as ITM champion board)

```text
mode:                 PAPER
promotion:            NO_PROMOTE
customer_slash:       false
research_ready:       false
win_rate:             lab/fixture only — not customer truth
INDEX points:         ≠ option premium P/L
PREMIUM tape:         only when OPTIDX cache / universe exists
costs:                HYPOTHESIS_OPTION_RT_1PCT; statutory UNKNOWN
SCORE_SAMPLE:         NEWS_CALENDAR days=[] → DATA_INSUFFICIENT
```

`WATCH` on this board is **not** a promote. `TESTED_FAIL` / `PARK` / `DATA_INSUFFICIENT` **stay**. Do not drop an EP without a row.

---

## What shipped

| Piece | Behavior |
|-------|----------|
| Registry | `sma_cross`, `macd_hist` (public textbook rules), `stub` (unported EP) |
| Catalog JSON | `EP-NNN` → `MIX-TV-EP-NNN` + `input_schema.grid` |
| Grid | TF `1/3/5/15` as bars allow × `NIFTY`/`SENSEX` (+ `BANKNIFTY` if cache) × tape `INDEX`/`PREMIUM` × param combos |
| Regime | `TREND` if `|SMA50(t)−SMA50(t−10)| / close ≥ 0.002` else `RANGE`; warmup `UNKNOWN` |
| Board | `data/recon/tv_ep_leaderboard.{json,md}` (gitignored recon) |
| Tests | `packages/backtest/tests/test_tv_ep_factory.py` — no live Dhan |

**Not** copied: full Pine. Ports are Python adapters only.

---

## How to run

Fixture / CI (no Dhan, synthetic bars):

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src \
  python -m backtest_engine tv-ep-grid --write
```

Cache-only INDEX/OPTIDX (still no live fetch; empty cache → `DATA_INSUFFICIENT` rows):

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src \
  python -m backtest_engine tv-ep-grid --cache --write
```

Do **not** pass `--live` on this command. History fetch is a later founder ask.

One factory-design counsel shot (not per EP):

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src:packages/trading_agents_india/src \
  python -m backtest_engine tv-ep-counsel
```

---

## Data missing (honest)

| Need | Today |
|------|--------|
| INDEX 1m cache NIFTY/SENSEX | Often empty on a clean clone → cache grid is all `DATA_INSUFFICIENT` until warehouse/fetch |
| BANKNIFTY | Included **only** if INDEX cache exists |
| OPTIDX premium | Needs `data/recon/itm_strike_universe.json` + OPTIDX 1m chunks |
| NEWS_CALENDAR dated rows | Empty → cannot split SCORE_SAMPLE vs ANALOG ([`EVENT_MEMORY.md`](EVENT_MEMORY.md)) |
| Named TV EP Pine ports | `catalog.json` has 23 URLs/titles/inputs; adapters still `stub` until a public-rule port |

---

## 01 / 04 notes — ports that survive premium tape

1. **Two tapes, two scores.** Never rank an INDEX-point SMA as option P/L. Same adapter, separate `tape=` cells.
2. **Fill = next bar open** (existing `simulate_leans`). Do not use signal-bar close.
3. **Port the public rule (cross / hist sign), not the overlay soup.** 5m ST/MACD stays confirm-or-kill on the customer path ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)); this factory may still *score* MACD as a named MIX row.
4. **Premium path:** ATM/ITM OPTIDX OHLC when tape exists; INDEX is a proxy label. If the EP needs volume profile / DOM / session boxes that HQ does not serve → `stub` + `DATA_INSUFFICIENT`, keep the id.
5. **Grid, not chat.** New EP = JSON entry + adapter id. Do not burn tokens re-explaining Pine.

---

## Paper-live later (same board)

Append `paper_live[]` ticks onto `data/recon/tv_ep_leaderboard.json` after a founder-started paper session. Status stays `WATCH`/`PARK`/`TESTED_FAIL`. **Still `NO_PROMOTE`.** Do not write customer `/`. Same honesty banners as [`ITM_CHAMPION_PAPER_BOARD.md`](ITM_CHAMPION_PAPER_BOARD.md).

Retune: [`RETUNE_GATE.md`](RETUNE_GATE.md) — nightly `BACKTEST_REQUIRED`; event days out of SCORE_SAMPLE when the calendar has dates.

---

## HANDOFF

| Accepted | Rejected | UNKNOWN / DATA_INSUFFICIENT |
|----------|----------|------------------------------|
| Factory + stub rows so 1000 EPs can queue without STRAT-015+ | Promoting WATCH to `/`; copying Pine; live Dhan orders; auto-retune | Real INDEX/OPTIDX history on this clone; which named TV EPs are public-rule portable; OOS+NORMAL edge |

Next: catalog fills `editors_picks/catalog.json`; 06 ports adapters one family at a time; paper-live attaches to the same board when founder starts PAPER (not this ticket).
