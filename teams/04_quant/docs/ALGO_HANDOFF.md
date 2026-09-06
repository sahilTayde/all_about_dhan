# ALGO_HANDOFF — coding / backtest shape (not a license to code)

**Team:** 04_quant (shape) · consumers later: 06_backtesting then 07_coding  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / `WAITING_FOR_EDIT`  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Date:** 2026-09-03  
**Ticket:** [`TASK_TRANSCRIPT_COALITION.md`](../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md)  
**Book:** [`MASTER_STRATEGY_PLAN.md`](MASTER_STRATEGY_PLAN.md)  
**Review notes:** [`COALITION_REVIEW.md`](../../09_review/docs/COALITION_REVIEW.md)

This file tells a later **engine** agent which fields a strategy spec must expose. It does **not** implement signals. It does **not** claim an edge. Read this only after 09 has at least **notes** on the coalition packets. Notes ≠ pass.

**Do not treat this file as a license for live orders.** Paper engine: `packages/backtest`.

Nightly recon cannot retune these fields. [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md): `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; default **keep current strategy**.

---

## When an algo agent may open this

| Condition | Allowed? |
|-----------|----------|
| Coalition packets missing | Read the YAML **schema** only. Do not invent values. |
| Packets on disk, 09 `WAITING` / notes only | Read schema + existing `STRAT-00x.md` YAML. Still `UNVALIDATED`. |
| 09 issued `RESEARCH_READY_FOR_PROGRAMMING` | **Has not happened.** Do not pretend it has. |
| User asks to “just code the 14” live | **Refuse live orders.** Paper/backtest of named STRATs is allowed; KEEP_ALL; no STRAT-015+. |

---

## Origin tags (do not collapse)

| Tag | Meaning | Coding implication |
|-----|---------|-------------------|
| `DHAN-DERIVED` | Speaker on enabled `@DhanHQ` (or other **enabled** yaml source) said the rule. Cite `video_id` + timestamp. | Still education, not a Dhan product endorsement. Params may be `[UNCERTAIN_TRANSCRIPT]`. |
| `PROJECT-DERIVED` | We transferred a stock/TA idea onto index options (or mixed two videos). | Must stay labelled. Red-team item: stock concept on index. |
| `EXTERNAL_RESEARCH` | Disabled-or-enabled non-Dhan row in `workspace.yaml`. | Ideas only. Production indicators stay Dhan-only unless `implementation.indicators` changes. |

A row may be `DHAN-DERIVED` **plus** a `PROJECT-DERIVED` transfer note (example: STRAT-011). Never relabel PROJECT as DHAN to look official.

---

## Status every spec must carry

```text
status: UNVALIDATED
layer_hypothesis: true
research_ready_for_programming: false
```

Until 09 **five-pass** passes, published product metrics stay **UNVALIDATED**. 06 may write **proxy** win_rate in recon + [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md) labeled FAIL/not option P/L. Do not invent.

---

## Machine-readable fields (YAML)

Copy this block into `teams/04_quant/docs/candidates/STRAT-00x.md` (index book) or a **separate** equity/ETF backlog file. Unknown → `UNKNOWN` or `DATA_INSUFFICIENT`. Do not guess.

```yaml
strategy_id: STRAT-00x          # index book: 001–014 only. Equity/ETF: EQ-* / ETF-* in the other file.
name: snake_or_Camel           # stable token for later engine
origin: DHAN-DERIVED           # or PROJECT-DERIVED (or both, listed)
origin_videos:                 # required if DHAN-DERIVED
  - {video_id: HAUSZx-hYdY, ts: "41:32", qa_flag: null}
book: INDEX_OPTIONS            # INDEX_OPTIONS | EQUITY | ETF | STOCK_OPTION
                               # INDEX_OPTIONS must not share IDs with the other books
market: [NIFTY, BANKNIFTY, SENSEX]   # equity book: NSE/BSE cash names, not this list
instrument:
  type: INDEX_OPTION           # INDEX_OPTION | INDEX_FUTURE | EQUITY | ETF | STOCK_OPTION
  side: BUY                    # BUY first in Phase-1; SELL stays WAITING (013–014)
  exchange: FROM_CONTRACT      # NSE vs BSE — SENSEX is BSE
lot_size: FROM_INSTRUMENT_MASTER
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata

regime:                        # engine mix later; still UNVALIDATED
  bull: true                   # long CE lean
  bear: true                   # long PE lean
  sideways: skip               # trade | skip | credit_WAITING
role: primary                  # primary | filter | overlay | confirm

timeframe:
  signal: 5m                   # chart TF for the rule
  confirm: 5m                  # lagging stack = confirm or kill, not entry
  hq_intervals: [1, 5, 15, 25, 60]  # official charts enum
  resample_hypothesis: null    # e.g. 3m / 2m — not an HQ interval

indicators:                    # name the surface; do not invent REST
  - name: MACD
    surface: OHLC_COMPUTE      # OHLC_COMPUTE | TRIGGER_ENUM | CHART_ONLY | QUOTE_ATP | UNKNOWN
    spoken: {fast: 12, slow: 26, signal: 9}
    hq_trigger: [MACD_12, MACD_26, MACD_HIST]  # if any
    series_api: false

data:                          # what the engine must load — see table below
  ohlc: FUTURES                # FUTURES | OPTION | EQUITY_CASH | FORBIDDEN_INDEX_VOLUME
  chain: true
  news: false
  cas: false
  order_flow: false            # likely DATA_INSUFFICIENT on DhanHQ history

costs:
  include: [brokerage, statutory, half_spread]
  fill: next_bar_open_or_conservative_ask
  look_ahead: forbidden

invalidation:                  # prose OK; engine later maps to REJECTED
  - "expectancy <= 0 after costs in two regimes"
  - "required history DATA_INSUFFICIENT"

status: UNVALIDATED
research_ready_for_programming: false
metrics:                       # never invent
  win_rate: null
  expectancy: null
  profit_factor: null
  max_drawdown: null
```

Existing candidates already use a **subset** of these keys. Coalition merge may **add missing keys**; it may not silently “correct” `[UNCERTAIN_TRANSCRIPT]` numbers.

---

## Regime (bull / bear / sideways)

The customer UI shows a staged lean, not a strategy catalog. The **engine** (later) may attach DRAFT IDs to regimes. That mix is **UNVALIDATED**.

| Regime | Meaning on this desk | Index-book IDs (v0.1, unchanged) |
|--------|----------------------|----------------------------------|
| **bull** | Long CE lean while trend filters agree | 001, 002, 003, 004, 005, 006, 007, 011 |
| **bear** | Long PE lean; same IDs mirrored | same; 001/003/006 explicit |
| **sideways** | Skip, time filter, or credit **WAITING** | 003 (ST vs VWAP disagree), 008, 009, 013–014 |

Filters 007–009 attach to primaries. They are not fourteen independent edges.

Equity/ETF backlog uses the **same three regime words** but **different IDs**. Do not reuse `STRAT-001` for a stock scanner.

---

## Data requirements

| Need | Use | Do not use |
|------|-----|------------|
| **OHLC + volume** | Index **futures** or the **option** tape. HQ `POST /charts/historical` + `/intraday` (1/5/15/25/60). | Cash-index “volume” for VWAP. Vendor index volume is **unsupported**. |
| **Session VWAP / VWMA / Supertrend series** | Compute from futures/option OHLC later. Chart-only on HQ. | `indicatorName` Supertrend (does not exist). Conditional Trigger is **EQ/IDX**, not a documented OPTIDX scanner. |
| **Day VWAP snapshot** | Quote `average_price` / feed ATP | Treating ATP as AVWAP bands |
| **Chain** | `POST /optionchain` documented fields: bid, ask, LTP, OI, IV, strike, expiry, lot, tick | Invented DEXT OI-profile history |
| **News** | Desk-intel RSS + calendar (`NEWS_DAY`) as **veto / no-trade**, not alpha | Scraping headlines into a STRAT entry |
| **CAS** | Cash close auction 15:15–15:35; daily `BOUNCE\|SIDEWAYS\|FALL` is `UNVALIDATED` | Hardcoding one 15:30 close for all products |
| **F&O clock** | Equity derivatives **09:15–15:40** IST (VERIFY circulars) | Assuming cash CTS 15:30 = option last print |
| **Order-flow / footprint** | `DATA_INSUFFICIENT` until HQ history is proven | Coding STRAT-010 as if DEXT history exists |

SENSEX tokens are **BSE**. NIFTY/BANKNIFTY are **NSE**. Do not reuse one chain client blindly.

---

## Paper / backtest compute path (KEEP_ALL — not Gokul’s 3m)

**Live HQ (2026-09-03):** `POST /charts/intraday` **interval `5`** works on **`IDX_I` / `INDEX`**. Official enum remains `{1, 5, 15, 25, 60}`. **3m is not an HQ interval.**

**Spoken STRAT-003:** **3m FUTIDX** (`2RnBT9DDDNI`, CONFIRMED). That recipe stays on the STRAT. KEEP_ALL — do not delete 003 or rewrite it as “Gokul said 5m index.”

| Path | Segment / TF | Origin tag | What it is |
|------|----------------|------------|------------|
| **Paper / backtest compute (now)** | HQ `{1,5,15,25,60}` — **5m INDEX** (`IDX_I`) | **`PROJECT`** / `PROJECT_MIX` vs spoken 3m FUTIDX | Proxy bars to count 003-style all-three. **Not** Gokul. **Not** option P/L. `win_rate` stays **null**. |
| **Spoken 003 (KEEP_ALL book)** | **3m FUTIDX** | `DHAN-DERIVED` | Teacher recipe. Resample vs native 5m remains an ablation. |
| **Do not freeze** | 5m INDEX as if 2Rn taught it | — | Relabeling 5m as Gokul is a spec fail |

Code pointer (OHLC compute only, no orders): [`packages/backtest`](../../../packages/backtest/) (`backtest_engine.run_index_5m` — 5m INDEX, STRAT-003-**style** all-three **count**, not a win rate).

`MIX-GOKUL-003` stays 3m FUTIDX in spec. A 5m INDEX run is a **separate** `PROJECT` compute path, not `STRAT-015+`.

---

## Confirm vs entry (lagging TA)

5m Supertrend / MACD / `RSI_14` are **confirmation or kill** ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md)). They are late on a news impulse. A coalition packet that promotes “wait for the MACD cross” as the **entry** fails 09 red-team (lagging TA as entry).

EARLY (~1 minute lead) is a **product target**, not a fill.

---

## What coding must not do

- Implement these YAML blocks as live signals or as `apps/` strategy modules.
- Implement WATCH / EARLY / CONFIRMED / IN-PROGRESS as live math or 1-minute omniscience.
- Rank by invented backtest return.
- Add `STRAT-015+` on the index book.
- Merge equity/ETF backlog IDs into `market: [NIFTY, BANKNIFTY, SENSEX]`.
- Write production params from nightly JSON or from a new transcript quote.
- Collapse `DHAN-DERIVED` and `PROJECT-DERIVED`.

Next engine work (when scheduled): fixtures only, costs + slippage, date-stamped lots, no look-ahead. Still `UNVALIDATED` until 09 passes.
