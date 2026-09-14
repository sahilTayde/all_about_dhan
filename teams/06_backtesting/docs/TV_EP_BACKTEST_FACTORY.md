# TV Editor Picks backtest factory (NO_PROMOTE)

**Team:** 06 backtesting (harness) · 02 math (regime/costs REVIEW) · 04 quant (MIX ids) · 01 research (catalog fill)  
**Status:** `HYPOTHESIS` / harness **coded** / **UNVALIDATED**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Board (founder):** [`TV_EP_LEADERBOARD.md`](TV_EP_LEADERBOARD.md)  
**IDs:** `MIX-TV-EP-NNN` only. **KEEP_ALL** `STRAT-001`–`014`. Never `STRAT-015+`.  
**Orders:** refused. `ExecutionClient` stays SafeMode. Do not start npm / paper market-hours.

Catalog folder: [`refernece_tradingview/editors_picks/`](../../../refernece_tradingview/editors_picks/) — **2026-09-14 fill:** 23 listing-order EPs (`MIX-TV-EP-001`–`023`) with **named Python adapters** (not stub) plus factory calibrators `MIX-TV-EP-024` (`sma_cross`) / `025` (`macd_hist`). SMA/MACD **do not** own listing IDs 001/002. Rule cards: [`../../01_research/docs/TV_EP_RULE_CARDS.md`](../../01_research/docs/TV_EP_RULE_CARDS.md).  
Code: `packages/backtest/src/backtest_engine/tv_ep/`  
CLI: `python -m backtest_engine tv-ep-grid` · counsel: `python -m backtest_engine tv-ep-counsel`

---

## Honesty banner (same class as ITM champion board)

```text
mode:                 PAPER
promotion:            NO_PROMOTE
UNVALIDATED:          true
tv_strategy_tester:   NOT A CLONE
customer_slash:       false
research_ready:       false
mapping:              TV long/buy → BUY_CE; TV short/sell → BUY_PE
long_only_sell:       EXIT counted (not discarded; not equity short)
win_rate:             lab/fixture only — not customer truth
INDEX points:         ≠ option premium P/L
PREMIUM tape:         only when OPTIDX cache / universe exists — never invent 23500 PE
costs:                PREMIUM = HYPOTHESIS_OPTION_RT_1PCT; INDEX = proxy points (no option haircut); statutory UNKNOWN
SCORE_SAMPLE:         NEWS_CALENDAR days=[] → DATA_INSUFFICIENT
KEEP_ALL:             MIX-TV-EP-001–023 stay even FAIL / PARK / DATA_INSUFFICIENT / n=0
```

`WATCH` on this board is **not** a promote. `TESTED_FAIL` / `PARK` / `DATA_INSUFFICIENT` **stay**. Do not drop an EP without a row.

---

## What shipped

| Piece | Behavior |
|-------|----------|
| Registry | 23 listing ports in `tv_ep/ports.py` + `sma_cross` / `macd_hist` calibrators + `stub` fallback |
| Catalog JSON | `EP-NNN` → `MIX-TV-EP-NNN`. 2026-09-14 listing: EP-001–023 **named adapters**; EP-024/025 factory calibrators |
| Grid | TF `1/3/5/15` as bars allow × `NIFTY`/`SENSEX` (+ `BANKNIFTY` if cache) × tape `INDEX`/`PREMIUM` × param combos |
| Regime | `TREND` if `|SMA50(t)−SMA50(t−10)| / close ≥ 0.002` else `RANGE`; warmup `UNKNOWN` |
| Costs | `HYPOTHESIS_OPTION_RT_1PCT` on **PREMIUM** only. INDEX = proxy points, no option haircut |
| Board | `data/recon/tv_ep_leaderboard.{json,md}` + [`TV_EP_LEADERBOARD.md`](TV_EP_LEADERBOARD.md) |
| Mapping | TV long→BUY_CE, TV short→BUY_PE; long-only sell→EXIT |
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
  python -m backtest_engine tv-ep-grid --cache --tf 1 3 5 15 --write
```

History fetch (INDEX 1m + OPTIDX 47298 only; **never** `place_order`):

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src \
  python -m backtest_engine tv-ep-grid --cache --tf 1 --refresh-cache \
  --prefer-strike 23500 --write
```

Do **not** use `--live` as an order switch. Founder 1m note: [`TV_EP_1M_NIFTY_PREMIUM.md`](TV_EP_1M_NIFTY_PREMIUM.md).

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
| Named TV EP Pine ports | `catalog.json` adapters are named; many ports are **partial** (templates, FX session, martingale qty) — see rule cards |

---

## 01 / 04 notes — ports that survive premium tape

1. **Two tapes, two scores.** Never rank an INDEX-point SMA as option P/L. Same adapter, separate `tape=` cells.
2. **Fill = next bar open** (existing `simulate_leans`). Do not use signal-bar close.
3. **Port the public rule (cross / hist sign), not the overlay soup.** 5m ST/MACD stays confirm-or-kill on the customer path ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)); this factory may still *score* MACD as a named MIX row.
4. **Premium path:** ATM/ITM OPTIDX OHLC when tape exists; INDEX is a proxy label. If the EP needs volume profile / DOM / session boxes that HQ does not serve → `stub` + `DATA_INSUFFICIENT`, keep the id.
5. **Grid, not chat.** New EP = JSON entry + adapter id. Do not burn tokens re-explaining Pine.

---

## Paper-live / paper-tune (same board)

Append `paper_sessions[]` from `python -m backtest_engine tv-ep-paper-tune`. Dual-tape `PREMIUM_DIVERGENCE` blocks new paper tickets. Status stays `WATCH`/`PARK`/`TESTED_FAIL`. **Still `NO_PROMOTE`.** Do not write customer `/`. One green replay day is **not** OOS.

Retune: [`RETUNE_GATE.md`](RETUNE_GATE.md) — nightly `BACKTEST_REQUIRED`; paper tuner also emits `BACKTEST_REQUIRED` + local `data/recon/tv_ep_paper_params_*.json` only. Never auto-write `MIX-DEFAULT-BUY`. How-to: [`TV_EP_PAPER_TUNE.md`](TV_EP_PAPER_TUNE.md).

---

## HANDOFF

| Accepted | Rejected | UNKNOWN / DATA_INSUFFICIENT |
|----------|----------|------------------------------|
| KEEP_ALL 001–023; TV long→BUY_CE / short→BUY_PE; 1/3/5/15 × NIFTY/SENSEX/(BANKNIFTY if tape) | Promoting WATCH to `/`; copying Pine; live Dhan orders; auto-retune; fake 23500 PE; equity short as default | Real INDEX/OPTIDX history on this clone; OOS+NORMAL; SCORE_SAMPLE |

Next: `--cache --write` when warehouse INDEX/OPTIDX exists; paper-live attaches to the same board when founder starts PAPER (not this ticket).

## First fixture MIX rows (synthetic two-regime bars — not customer truth)

`python -m backtest_engine tv-ep-grid --write` regenerates [`TV_EP_LEADERBOARD.md`](TV_EP_LEADERBOARD.md). Listing **001–023 stay**. Fixture WATCH ≠ win rate. CACHE `--cache` with empty OHLC = all `DATA_INSUFFICIENT`.
