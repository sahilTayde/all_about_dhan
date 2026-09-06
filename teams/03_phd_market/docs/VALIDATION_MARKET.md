# Team 03 — India market / microstructure VALIDATION

**Status:** `DRAFT` / `WAITING_FOR_EDIT`. Layer B.  
**Lot sizes and expiry weekdays are not eternal.** Always load from exchange / Dhan instrument master at the **as-of date**.

Validation retrieved: 2026-08-30.

---

## Instruments (Phase 1)

| Underlying | Exchange | Segment | Notes |
|------------|----------|---------|-------|
| NIFTY 50 | NSE | Index options + futures | Cash index is a **calculation**, not a tradable lot. |
| BANKNIFTY | NSE | Index options + futures | Weekly options **discontinued** under SEBI “one weekly expiry per exchange” (from Nov 2024 regime). Monthly remains. **VERIFY** current contract list. |
| SENSEX | **BSE** | Index options + futures | Different strike steps, lot, tick, trading host, and expiry weekday vs NSE. Do not reuse NIFTY chain code blindly. |

FINNIFTY, MIDCPNIFTY, BANKEX: mentioned in transcripts; **out of Phase-1 coding** unless later opened. Liquidity spoken as thinner.

---

## Session times — `VERIFY BEFORE IMPLEMENTATION`

Classic continuous session (cash + F&O, long-standing): **09:15–15:30 IST**.

**Closing Auction Session (CAS) — official, fetched 2026-09-01** ([NSE CAS page](https://www.nseindia.com/static/products-services/closing-auction-session), circular NSE/CMTR/74466, BSE 20260610-41): Phase 1 = **F&O cash** names. Those names: CTS ends **15:15**; CAS **15:15–15:35**; post-close **15:50–16:00**. **Equity derivatives: 09:15–15:40**. Non-CAS cash still CTS to **15:30**. Official close for CAS names is **equilibrium**, not last-30-min VWAP. Full book: [`../cas/RESEARCH.md`](../cas/RESEARCH.md).

**Team 03 verdict:** do **not** hardcode a single 15:30 close for all products. Backtests must **parameterize** cash-CAS vs F&O-15:40 vs non-CAS. NSE market-timings HTML is **stale** (updated 04/08/2025) vs the CAS product page. File official PDFs in-repo when downloaded.

Pre-open, special sessions (Muhurat), and holidays: exchange calendar. 08 Nov 2026 Diwali Laxmi Pujan: trading holiday + Muhurat (NSE holiday page note).

Transcripts:

- Ignore **09:15–09:45** (2RnBT9DDDNI) — **context-dependent** (auction + open volatility), not an exchange rule.
- Flatten **before 15:15** (2RnBT9DDDNI) / no new entries after **14:30** and not after **15:00** (HAUSZx) — **trader heuristics**, not exchange mandates.
- Scalps into the last minutes face CAS/close-VWAP effects if F&O close extends.

---

## Expiry — `VERIFY`; do not freeze weekday

SEBI: **one weekly index-options expiry per exchange**. Secondary summaries (2026):

| Product | Weekly | Monthly (typical) |
|---------|--------|-------------------|
| NIFTY | Tuesday | last Tuesday |
| SENSEX | Thursday | last Thursday |
| BANKNIFTY / FINNIFTY / MIDCPNIFTY | **none** (monthly only) | last Tuesday (NSE) |

Holiday on expiry → **previous trading day** (standard).

**Transcript conflicts (keep both as SOURCE_FACT, validate as dated):**

- HAUSZx (~16:14): NIFTY weekly **Thursday** sequence (Jun 2025-style).
- 6el9Jqnrdz8 (~41:42): NIFTY **Tuesday**.
- 2RnBT9DDDNI: FinNifty/Bankex more monthly; BANKNIFTY monthly mentioned.

**Verdict:** HAUS Thursday list is **dated**. Tuesday NIFTY weekly is **partially_supported** for post-Sep-2025. Always read the contract’s `expiry_date` from the master.

---

## Lot size — NEVER hardcode

Secondary 2026 blogs (Ventura / aggregators; **not exchange PDF attached**): NIFTY **65**, BANKNIFTY **30**, SENSEX **20**, after Jan 2026 re-basing (prior NIFTY 75 / BN 35 often cited).

2RnBT9DDDNI capital example uses **65 × premium** (~16:55). That matches **one** vintage, not history.

**Verdict:** `VERIFY` from NSE/BSE circular + DhanHQ instrument master **per date**. Historical backtests must use **then-current** lot, not today’s.

Strike steps: HAUS “NIFTY 50-point multiples” — **partially_supported** for NIFTY options (exchange can add/remove series). SENSEX/BANKNIFTY steps **UNKNOWN here** — look up.

---

## Option buy vs sell

| Topic | Verdict |
|-------|---------|
| Buy-first for small capital (Gokul) | **context-dependent** (margin vs premium) |
| Selling needs SPAN/exposure + hedges cut margin | **supported** as a market practice |
| Collateral can fund selling not buying (6el9) | **partially_supported** — product/broker policy; verify Dhan |
| Naked short index options | tail risk, gaps (BANKNIFTY 1600-pt anecdote) — **supported as risk class**, number `[UNCERTAIN_TRANSCRIPT]` |
| Phase-1 project policy | CE/PE **buy** first; selling candidates stay **WAITING** |

---

## VWAP / volume on index

**Pitfall:** NIFTY/SENSEX **spot index has no authentic trade volume.** Using index “volume” from a charting vendor is **unsupported** for VWAP.

**Supported:** VWAP/VWMA/order-flow **delta** on **index futures** or on **the option** itself.

YUXJv demo on NIFTY futures: coherent.

PUkzVg / HAUS stock VWAP: stock cash volume is real; **does not transfer** to cash index.

---

## Liquidity / bid-ask (desk input, conceptual)

- ATM and 100-point NIFTY strikes usually tighter than 50s (host opinion) — **context-dependent**; measure spread × size.
- ITM options: higher premium, better delta, **worse** % bid-ask sometimes.
- SENSEX vs NIFTY: do not assume equal depth.
- 3-leg baskets (1-3-2): **leg risk** and partial fills.
- Scalping 2m on option LTP: spread + latency dominate; beginner “don’t buy-scalp” (pvmvki) is a **risk comment**, not a math law.

---

## Circuit breakers (conceptual — NSE page)

Index-wide halt if **NIFTY 50 or SENSEX** hits **10% / 15% / 20%** vs prior close (whichever first). Coordinated equity + equity derivatives halt. Durations depend on **time of day** (SEBI 2013 table on [nseindia.com circuit breakers](https://www.nseindia.com/products-services/equity-market-circuit-breakers)). 20% → rest of day.

**Backtest implication:** no fills during halt; queues reopen via pre-open. Do not assume continuous 09:15–close paths on those days.

Stock-level bands ≠ index MWCB. Index options can still gap through a “stop on underlying.”

---

## European / settlement

Index options: **European, cash-settled** (standard NSE/BSE). HAUS “exercise now and short futures” arb story is **pedagogy** for intrinsic; live index options are not American-exercisable into the basket.

---

## UNKNOWN / blockers

- Official lot circular PDF not stored in-repo.
- Official F&O close 15:30 vs 15:40 circular not stored.
- BSE SENSEX strike interval / tick: not extracted this pass.
- Historical option quotes availability on DhanHQ: `DATA_INSUFFICIENT` (Phase 1 data team).
