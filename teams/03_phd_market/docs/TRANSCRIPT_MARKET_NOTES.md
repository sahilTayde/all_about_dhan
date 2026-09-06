# TRANSCRIPT_MARKET_NOTES — clocks, SENSEX, VWAP (coalition)

**Team:** 03_phd_market  
**Date:** 2026-09-03  
**Layer:** `VALIDATION` (this file). Transcript lines stay `SOURCE_FACT` on 01 packets.  
**Status:** `DRAFT` / `WAITING_FOR_EDIT`  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Ticket:** [`TASK_TRANSCRIPT_COALITION.md`](../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md)

Full market book: [`VALIDATION_MARKET.md`](VALIDATION_MARKET.md). Official CAS: [`../cas/RESEARCH.md`](../cas/RESEARCH.md). Desk fills: [`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md).

Lot sizes and expiry weekdays are **not eternal**. Load exchange / Dhan instrument master at the **as-of date**. Do not freeze a speaker’s weekday as the engine constant.

---

## 1. Expiry

**Exchange regime (VERIFY; secondary 2026 summaries, not an in-repo circular):** SEBI **one weekly index-options expiry per exchange**.

| Product | Weekly (typical) | Monthly (typical) | Notes |
|---------|------------------|-------------------|--------|
| NIFTY | Tuesday | last Tuesday | HAUS Thursday sequence is **dated** (Jun 2025-style). 6el9 Tuesday is **partially_supported** post-Sep-2025. |
| SENSEX | Thursday | last Thursday | **BSE**, not NSE. |
| BANKNIFTY | **none** (weekly discontinued) | last Tuesday (NSE) | Monthly only under the one-weekly-per-exchange regime. **VERIFY** current list. |

Holiday on expiry → **previous trading day** (standard). Always read `expiry_date` from the contract master.

**Transcript duty:** keep both Thursday and Tuesday claims as `SOURCE_FACT` with video_id + timestamp. 03 tags them **dated** vs **partially_supported**. 04 must not “pick the winner” and rewrite the quote.

**Algo:** `expiry: FROM_CONTRACT`. Nightly tags `EXPIRY` when nearest-expiry **equals** the session date — that day is **not** a retune sample ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

---

## 2. CAS close vs 15:40 F&O

Do **not** hardcode a single 15:30 close for cash, CAS names, and equity derivatives.

| Clock | IST (official, fetched 2026-09-01) | What it is |
|-------|-------------------------------------|------------|
| CAS (F&O **cash** names) | CTS ends **15:15**; CAS **15:15–15:35**; post-close **15:50–16:00** | **Closing Auction Session**. Official close = **equilibrium**, not last-30-min VWAP. Live **3 Aug 2026**. |
| Non-CAS cash | Continuous **09:15–15:30** | Still the old CTS close. |
| Equity **derivatives** (index F&O) | **09:15–15:40** | NSE CAS page + market-timings page. **Not** the cash CAS auction. |

NSE market-timings HTML (updated 04/08/2025) is **stale vs CAS**. Use the CAS product page + circulars 74466/74467 for F&O-cash names. Official PDFs are **not** all stored in-repo — treat 15:40 as **VERIFY**, not folklore.

**Transcript heuristics (not exchange rules):** flatten before 15:15 / no new entries after 14:30 or 15:00. Keep as trader `SOURCE_FACT`. Scalps into the last minutes face **CAS cash** effects **and** a later **F&O** print.

**CAS ≠** pre-open, **≠** PCA (illiquid), **≠** trader slang “cash vs F&O.” Daily `BOUNCE|SIDEWAYS|FALL` from the CAS analyst is `UNVALIDATED`.

**Algo:** parameterize `cash_cas` vs `fo_1540` vs `non_cas_cash`. Circuit-breaker days can **skip** CAS (then last-30-min VWAP / LTP as before).

---

## 3. SENSEX = BSE

| Underlying | Exchange | Segment |
|------------|----------|---------|
| NIFTY 50 | **NSE** | Index options + futures |
| BANKNIFTY | **NSE** | Index options + futures |
| SENSEX | **BSE** | Index options + futures |

Different strike steps, lot, tick, trading host, weekly weekday. Do not reuse a NIFTY chain client, lot constant, or expiry calendar on SENSEX.

FINNIFTY / MIDCPNIFTY / BANKEX appear in transcripts; **out of Phase-1 coding** unless later opened.

MWCB: index-wide halt if **NIFTY 50 or SENSEX** hits 10/15/20% vs prior close. No fills during halt.

---

## 4. VWAP-on-index pitfall

**Unsupported:** VWAP / VWMA / volume-delta on the **cash index** (NIFTY or SENSEX **calculation**). Spot index has **no authentic trade volume**. Charting-vendor “index volume” is not an exchange print.

**Supported:** session VWAP / VWMA / order-flow **delta** on **index futures** or on **the option** itself.

| Spoken pattern | Verdict |
|----------------|---------|
| Gokul 3m VWAP+VWMA+ST on **NIFTY futures** | Coherent object (still `UNVALIDATED` as a strategy) |
| Stock VWAP on cash names (PUkzVg / HAUS equity) | Real cash volume; **does not transfer** to cash index — tag `PROJECT-DERIVED` if forced onto NIFTY options |
| Quote `average_price` / feed ATP | Day VWAP-like **snapshot**, not AVWAP bands |

HQ has **no** session-VWAP series endpoint. Compute later from futures/option OHLC if an engine exists. Conditional Trigger names are **EQ/IDX**, not a documented OPTIDX VWAP scanner.

---

## What 04 / 06 must parameterize

```yaml
session_tz: Asia/Kolkata
expiry: FROM_CONTRACT
lot_size: FROM_INSTRUMENT_MASTER
sensex_exchange: BSE
vwap_tape: FUTURES_OR_OPTION    # never CASH_INDEX
close_model:                     # pick per product; do not hardcode one
  cas_cash_names: 15:15-15:35_equilibrium
  equity_derivatives: 15:40      # VERIFY circular
  non_cas_cash: 15:30
```

---

## UNKNOWN / blockers (unchanged)

- Official lot circular PDF not stored.  
- Official F&O 15:30 vs 15:40 circular not stored.  
- BSE SENSEX strike interval / tick: not extracted this pass.  
- Historical option quotes on DhanHQ: `DATA_INSUFFICIENT`.

**No profitability claimed.**
