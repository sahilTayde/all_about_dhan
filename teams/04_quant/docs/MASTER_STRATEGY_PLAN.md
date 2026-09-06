# MASTER_STRATEGY_PLAN.md — v0.1 DRAFT

**Team:** 04_quant  
**Version:** 0.1  
**Status:** `DRAFT` / `HYPOTHESIS` / `UNVALIDATED` / `WAITING_FOR_EDIT`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Do not implement in `apps/` or `packages/`.  
**Date:** 2026-08-30 (coalition banner 2026-09-03)

> **COALITION IN PROGRESS (2026-09-03).** English-transcript packets (`OPTIONS_INDEX` / `TA_STRUCTURE` / `EQUITY_ETF`) merge into this file as **pointers and regime notes only**. Spoken-rule authority for the 14 IDs: [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) (English `normalized_en/` wins; prior mix copied STRAT timestamps). They do **not** add `STRAT-015+`. All **14** IDs stay `UNVALIDATED` / **`BACKTEST_BOOK`** ([`MIX_CATALOG.md`](MIX_CATALOG.md) `KEEP_ALL`; named clubs are `MIX-*`). **Phase-1 engine mix** (which IDs attach to BULL / BEAR / SIDEWAYS, in what role, conflicts left standing): [`ENGINE_MIX.md`](ENGINE_MIX.md) — `HYPOTHESIS`, metrics null, cites the bind, **not** `RESEARCH_READY_FOR_PROGRAMMING`. Equity / ETF / stock-options research is a **separate book** — not Phase-1 index options. Algo agents: YAML shape in [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md) only after 09 notes. Nightly recon still cannot auto-retune ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)). Ticket: [`TASK_TRANSCRIPT_COALITION.md`](../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md).

This is the **coding/backtest handoff** for later teams (06 then 09 then 07). Requirements **will change**. Leave room.

Education ≠ edge. **No profitability is claimed.** Prefer fewer honest candidates over invented ones.

Per-topic cluster stubs (not a transcript dump): [`topics/`](topics/). Customer source list: [`config/workspace.yaml`](../../../config/workspace.yaml).

**Official Dhan indicator defs (clubbed for PhDs):** [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md). Map to VALIDATION: [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md). KB: [`research/indicator_knowledge_base.md`](../../../research/indicator_knowledge_base.md). Ticket: [`teams/00_orchestrator/docs/TASK_DHAN_INDICATORS.md`](../../00_orchestrator/docs/TASK_DHAN_INDICATORS.md). Each [`topics/`](topics/) file cites the same.

**Staged signals (WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED)** after a missed lagging-TA PE: [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md). **IN-PROGRESS** = live after CONFIRMED. **Outcomes** (ACHIEVED/STOPPED/INVALIDATED/EXPIRED/LOST/COMPLETED/SHADOW_CLOSED): same file + [`TASK_PRE_POST_MARKET_JOBS.md`](../../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md). Paper daily + pre-prod recon only — **no live strategy rewrite**. 5m MACD/Supertrend = **confirmation not entry**. ~1 minute EARLY lead = **target not guarantee**. Leave `WAITING_FOR_EDIT`.

---

## CUSTOMER vs ENGINE (honesty)

The customer has **low confidence** in these defined strategies. That is correct. Do **not** invent more STRATs, win rates, or a polished catalog.

| Surface | What they see | What they must not see |
|---------|----------------|-------------------------|
| **Customer UI** | A staged lean (WATCH / EARLY / CONFIRMED / **IN-PROGRESS** / EXPIRED / VETOED) plus readable reasons. Direction chip + honesty copy. | Indicator soup (RSI + MACD + Supertrend + EMA stack as the product). Fake win rates. Extra unnamed “strategies.” |
| **Engine** (later) | May mix **regime-specific** candidates (bull / bear / sideways) from the 14 IDs below. Named Phase-1 mix: [`ENGINE_MIX.md`](ENGINE_MIX.md) (`UNVALIDATED`). | A claim that the mix is validated, profitable, or ready to code as live. |

**14 candidates are DRAFT.** Status on every ID: `HYPOTHESIS` / `UNVALIDATED`. There are **no backtest win rates** — do not invent them. Coalition packets do **not** change that count.

**Who owns mix-and-match:** 04 froze a **testable** mix in [`ENGINE_MIX.md`](ENGINE_MIX.md) (still `UNVALIDATED` / not a production book). Next: 02/03/05/09 sign or reject, then **06_backtesting** on fixtures. This file stays the ID catalog + pointers.

**Who retunes:** PhD **nightly recon** (`NIGHTLY_YYYY-MM-DD.md`) is **REVIEW only**, not auto-apply. Nightly never writes production params; it emits `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED` and tags the session `NEWS_DAY` / `EXPIRY` / `NORMAL`. Default: **keep current strategy**. Event days make the book look broken — retuning on that sample overfits. Team **06** promotes only after an OOS + non-event (`NORMAL`) backtest that beats current on expectancy / PF / DD (not one-day P/L), or a documented glitch fix that backtests clean. Gate: [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md). Nightly JSON is not a live rewrite. Do not invent backtest results.

Customer-facing poll/memory (not a strategy): option chain every **3m**, last snapshot remembered — [`TASK_CUSTOMER_DESK.md`](../../00_orchestrator/docs/TASK_CUSTOMER_DESK.md).

---

## How coalition packets merge

```text
01  OPTIONS_INDEX_PACKET.md     SOURCE_FACT  (index CE/PE, chain, expiry)
01  TRANSCRIPT_STRATEGY_BIND.md SOURCE_FACT  (spoken English vs STRAT-001–014)
01  TA_STRUCTURE_PACKET.md      SOURCE_FACT  (spoken TA / structure)
01  EQUITY_ETF_PACKET.md        SOURCE_FACT  (separate book — do not mix)
        │
02  TA_FROM_TRANSCRIPTS.md      VALIDATION math (parallel with 03)
03  TRANSCRIPT_MARKET_NOTES.md  VALIDATION market (expiry, CAS vs 15:40, SENSEX=BSE, VWAP)
        │
04  this file + STRAT-001–014   pointers / regime notes only (still 14 IDs)
04  ENGINE_MIX.md               Phase-1 BULL/BEAR/SIDEWAYS attachment (HYPOTHESIS)
04  MIX_CATALOG.md              KEEP_ALL: STRAT-001–014 BACKTEST_BOOK + MIX-* (no STRAT-015+)
04  ALGO_HANDOFF.md             YAML fields for a later engine — not code
04  EQUITY_ETF_BACKLOG.md       placeholders only (other book)
        │
09  COALITION_REVIEW.md         red-team notes — not a five-pass
```

| Packet | Lands here as | Forbidden |
|--------|---------------|-----------|
| OPTIONS_INDEX | Extra `origin_videos` / chain / expiry notes on **existing** 001–014 | New index STRAT IDs; invented fills |
| TA_STRUCTURE | Indicator **surface** (OHLC vs trigger vs spoken); confirm-vs-entry | Lagging TA as live entry; invented REST series |
| EQUITY_ETF | [`candidates/EQUITY_ETF_BACKLOG.md`](candidates/EQUITY_ETF_BACKLOG.md) only | Any bleed into `market: [NIFTY, BANKNIFTY, SENSEX]` |

If a packet is not on disk, treat it as `WAITING_FOR_PACKETS` ([`COALITION_REVIEW.md`](../../09_review/docs/COALITION_REVIEW.md)). Do not invent the merge.

---

## Equity / ETF book (separate — placeholders)

Phase-1 **coding** remains NIFTY / BANKNIFTY / SENSEX **index options**. The user also wants **research** on stock selection, stock options, and ETFs. That work must not contaminate the 14 IDs.

| Slot | Universe | Status | Spec path |
|------|----------|--------|-----------|
| EQ-* | Cash equity / stock selection / ScanX-style screens | `WAITING` / `UNVALIDATED` | [`candidates/EQUITY_ETF_BACKLOG.md`](candidates/EQUITY_ETF_BACKLOG.md) (create with the equity packet) |
| SO-* | Single-stock options | `WAITING` / `UNVALIDATED` | same backlog — **not** STRAT-015+ |
| ETF-* | ETFs | `WAITING` / `UNVALIDATED` | same backlog |

ScanX / stock scanners are **Dhan product copy**, not a backtested screen. Catalog `STOCK_ONLY` / `EXCLUDED` tags stay; extract into the equity packet, **do not delete**.

Do **not** assign `STRAT-015` or reuse `STRAT-001` for a stock idea. Origin on any transfer into the index book must stay `PROJECT-DERIVED`.

---

## One-page for the next team (do not re-read all transcripts)

1. Read this file + [`MIX_CATALOG.md`](MIX_CATALOG.md) + [`ENGINE_MIX.md`](ENGINE_MIX.md) + [`ALGO_HANDOFF.md`](ALGO_HANDOFF.md) + the `candidates/STRAT-00x.md` you will test.  
2. Provenance: [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) first (English wins), then other `teams/01_research/docs/handoffs/` (`SOURCE_FACT` only) — packets `OPTIONS_INDEX_PACKET.md` / `TA_STRUCTURE_PACKET.md`.  
3. Math: `teams/02_phd_math/docs/VALIDATION_MATH.md` + **API map** `DHAN_INDICATOR_API_MAP.md` + `TA_FROM_TRANSCRIPTS.md` when it exists.  
4. Market + desk: `teams/03_phd_market/docs/VALIDATION_MARKET.md`, [`TRANSCRIPT_MARKET_NOTES.md`](../../03_phd_market/docs/TRANSCRIPT_MARKET_NOTES.md), `DESK_EXECUTION_NOTES.md`; persona seed `teams/00_orchestrator/docs/PERSONA.md`; operator + staging [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md) + [`SIGNAL_STAGING.md`](SIGNAL_STAGING.md).  
5. Production indicators = **Dhan-spoken / Dhan charts**. Books = VALIDATION tags only.  
6. Instruments: NIFTY, BANKNIFTY, SENSEX **index options**, CE/PE **buy first**. Equity/ETF = **other book**.  
7. Lots, expiry weekday, F&O close: **parameters from instrument master**, never constants.  
8. VWAP/volume: **futures or option tape**, never cash-index volume.  
9. Hindi ASR numbers: `[UNCERTAIN_TRANSCRIPT]` — treat as search ranges, not truths.  
10. 09 notes: [`COALITION_REVIEW.md`](../../09_review/docs/COALITION_REVIEW.md) — still not a pass.

---

## Official Dhan indicators vs chart-only (do not invent REST)

Fetched 2026-09-01 from [dhanhq.co/docs/v2](https://dhanhq.co/docs/v2/). Full tables in the official-indicators doc.

| Need | Official HQ v2 | Not an API series |
|------|----------------|-------------------|
| Named TA for **conditions** | Conditional Trigger `indicatorName` (SMA/EMA set **5,10,20,50,100,200**, `RSI_14`, `ATR_14`, BB upper/lower, stochastic, `MACD_12`/`MACD_26`/`MACD_HIST`). **Equities and Indices only.** Does **not** return a series. **`EMA_9` is not in the annexure.** Supertrend / RSI / MACD / EMA9 **series** do not exist on HQ — **compute from OHLC** (1m/5m) if a later engine needs them. | Supertrend, session VWAP, VWMA, ADX, Hull, Power Scalper, **EMA 9 as a trigger name** |
| Bars for **our** TA | `POST /charts/historical`, `/charts/intraday` → OHLC + volume (+ optional OI). Intervals **1, 5, 15, 25, 60** min | **3m** not in the enum (STRAT-003 is a resample **HYPOTHESIS**) |
| Day VWAP-like snapshot | Quote `average_price` (“Volume weighted average price of the day”); feed **ATP** | Chart VWAP bands / AVWAP |
| Chain / OI / Greeks | `POST /optionchain` documented fields only | DEXT OI Profile / order-flow history |

ScanX “Intraday Supertrend” and RSI 75/25 are **product** copy, not annexure fields. No scanner REST on HQ docs. **Do not live-trade** `/alerts/orders`.

---

## Regime coverage

**Roles and default ticket** are defined in [`ENGINE_MIX.md`](ENGINE_MIX.md) (still 14 IDs; `UNVALIDATED`). Pointers only:

| Regime | Candidates (IDs) |
|--------|------------------|
| Bullish (long CE) | 001, 002, 003, 004, 005, 006, 007, 011 — default primary **003** + 005 strike; see ENGINE_MIX |
| Bearish (long PE) | same IDs, mirrored; 001/003/006 explicit |
| Sideways / no-trade | 003 (ST vs VWAP disagree), 008 (mixed indices), 009 (session/time), 013–014 (credit/theta — **WAITING sell**) |
| Overlay only | 010 (order-flow — **PARKED** `DATA_INSUFFICIENT`), 012 (candles+S/R) |

---

## Candidate index (12 buy-default + 2 sell WAITING — all BACKTEST_BOOK)

`WAITING` / overlay-parked = **not customer default**, not deleted. Named clubs: [`MIX_CATALOG.md`](MIX_CATALOG.md).

| ID | Name | Origin | Phase-1 buy? | Regime |
|----|------|--------|--------------|--------|
| STRAT-001 | Dual-TF MACD×N + MA stack, long premium | DHAN-DERIVED (HAUSZx) | yes | trend |
| STRAT-002 | 1–2 strike OTM, 20–30% premium scale-out | DHAN-DERIVED (HAUSZx) | yes | strike/exit overlay |
| STRAT-003 | 3m futures VWAP+VWMA20+ST(10,3) | DHAN-DERIVED (2RnBT9) | yes | trend + sideways skip |
| STRAT-004 | Premium Super Scalper EMA confirm | DHAN-DERIVED (2RnBT9) | yes | confirm |
| STRAT-005 | High-delta 0.60–0.75 ITM/ATM buy | DHAN-DERIVED (2RnBT9) | yes | strike |
| STRAT-006 | 2m EMA10/20 ITM scalp | DHAN-DERIVED (pvmvki) | yes (speaker also said beginners should not buy-scalp) | scalp |
| STRAT-007 | Session clock 10:00–14:30 new entries | DHAN-DERIVED (HAUSZx) | filter | time |
| STRAT-008 | Mixed-index avoid / dominant only | DHAN-DERIVED (2RnBT9) | filter | sideways/confused |
| STRAT-009 | Open-noise skip 09:15–09:45 + flatten 15:15 | DHAN-DERIVED (2RnBT9) | filter | time |
| STRAT-010 | Futures order-flow delta/POC confirm | DHAN-DERIVED tool + PROJECT overlay | overlay | all |
| STRAT-011 | RSI divergence → Supertrend child (index transfer) | PROJECT-DERIVED from H_6kee + gA5 | yes | reversal |
| STRAT-012 | Candle + S/R confluence (index transfer) | PROJECT-DERIVED from njqeZc | overlay | all |
| STRAT-013 | Bull put credit (weekly) | DHAN-DERIVED (gA5) | **WAITING** sell | sideways-to-up |
| STRAT-014 | Hedged 1-3-2 call ratio Monday 09:45 | DHAN-DERIVED (6el9) | **WAITING** sell | sideways |

Filters 007–009 are **not** standalone edges; they attach to 001/003/006.

---

## Shared defaults (all UNVALIDATED)

```yaml
market: [NIFTY, BANKNIFTY, SENSEX]
instrument: {type: INDEX_OPTION, side: BUY}  # 013–014 excepted
lot_size: FROM_INSTRUMENT_MASTER  # never constant
expiry: FROM_CONTRACT
session_tz: Asia/Kolkata
costs: brokerage + statutory + half-spread minimum
fill: next_bar_open or conservative ask; no LTP fantasy
look_ahead: forbidden
status: UNVALIDATED
```

**Invalidation (global):** if after costs + 1 tick slippage expectancy ≤ 0 in **two** regimes (trend and chop), or if required history is missing (`DATA_INSUFFICIENT`), candidate is `REJECTED` or parked — not “optimized until it wins.”

---

## Data requirements (engine, later)

- Index futures OHLC + **true volume** (NSE/BSE F&O).
- Option chain: bid, ask, LTP, OI, IV, strike, expiry, lot, tick.
- Greeks if used: vendor methodology documented.
- Calendar: holidays, MWCB days.
- SENSEX on BSE tokens.

Order-flow footprint (010): likely **DATA_INSUFFICIENT** on DhanHQ history.

---

## What coding must not do yet

- Implement these as live signals.
- Implement staged WATCH/EARLY/CONFIRMED/IN-PROGRESS as live strategy math or 1-minute omniscience ([`SIGNAL_STAGING.md`](SIGNAL_STAGING.md)).
- Rank by backtest return **or invent win rates**.
- Add STRAT-015+ to look more complete. Fourteen DRAFT IDs is the honest **index** set. Equity/ETF uses EQ-*/SO-*/ETF-* on the other backlog.
- Merge SOURCE_FACT / VALIDATION / HYPOTHESIS in comments as if one layer.

Next: `teams/06_backtesting` only after 04 freezes a spec version (still UNVALIDATED) and 09 has **not** passed — engine can still be built on **fixtures**, not these as production.
