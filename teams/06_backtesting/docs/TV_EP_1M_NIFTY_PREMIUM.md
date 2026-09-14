# TV Editors’ Picks — 1m NIFTY INDEX vs 23500 PE (NO_PROMOTE)

**Team:** 06 backtest + 03 tape. **Date:** 2026-09-14. **Layer:** VALIDATION measurement on Dhan cache / HYPOTHESIS ports.  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **Promotion:** **NO_PROMOTE**. Orders refused.

Founder ask: 1m backtest of TV Editors’ Picks on the **NIFTY chart** and on **option premium** (TV tester P/L on NIFTY 23500 PE 1m). This run used **real Dhan OHLC cache**, not synthetic fixture.

CLI:

```bash
PYTHONPATH=packages/backtest/src:packages/dhan-client/src \
  python -m backtest_engine tv-ep-grid --cache --tf 1 --tv-years 0.12 \
  --prefer-strike 23500 --refresh-cache --write
```

Board (gitignored recon): `data/recon/tv_ep_leaderboard.{json,md}`.

---

## Tapes used (exact)

| Key | Source | ID | Bars | Window (IST) |
|-----|--------|----|------|----------------|
| NIFTY INDEX 1m | `data/recon/ohlc/INDEX_IDX_I_13_1_*.json` | security_id **13** IDX_I | **11957** | 2026-07-22 09:15 → **2026-09-03 14:19** |
| NIFTY 23500 PE 1m | `data/recon/ohlc/OPTIDX_NSE_FNO_47298_1_*.json` | **47298** OPTIDX, expiry 2026-09-15 from `itm_strike_universe.json` | **7185** | 2026-08-18 11:23 → **2026-09-11 15:39** |
| SENSEX INDEX 1m | `INDEX_IDX_I_51_1_*` | **51** | 11958 | 2026-07-22 09:15 → 2026-09-03 14:20 |
| SENSEX PREMIUM 1m | `data/recon/premium_tape/SENSEX_ATM_1m_2026-09-09..11.json` **PE** | rolling ATM PE — **not** a SENSEX 23500 | 1146 | 2026-09-09 09:15 → 2026-09-11 15:30 |
| BANKNIFTY INDEX 1m | `INDEX_IDX_I_25_1_*` | **25** | 11958 | same INDEX window |
| BANKNIFTY PREMIUM 1m | `premium_tape/BANKNIFTY_ATM_1m_*` PE | rolling ATM | 1146 | 2026-09-09 → 2026-09-11 |

**Not used for this grid:** warehouse `bars_1m` (NIFTY ~2447 bars 2026-09-03–09-10 only); FUTIDX chunks; rolling ATM± CSVs except SENSEX/BN premium fallback.

**23500 PE:** present. Universe strike 23500 → sid `47298`. Grid **preferred that sid** (not 23400 which also has cache). No invented path.

`--refresh-cache` called Dhan **historical intraday only** (INDEX 13/25/51 + OPTIDX 47298). `place_order` not used. INDEX last bar is still **2026-09-03 14:19** — HQ did not extend the cash-index book through 09-11 in this fetch. Premium 23500 PE already had through **09-11**.

If 23500 PE cache is missing on another clone:

1. `data/recon/itm_strike_universe.json` must list strike 23500 / sid 47298 (this expiry **2026-09-15** dies after that Tuesday).
2. Fetch: `python -m backtest_engine tv-ep-grid --cache --tf 1 --refresh-cache --prefer-strike 23500` **or** `backtest_engine.fetch.fetch_range` / `fetch_chunk` with `instrument=OPTIDX`, `exchangeSegment=NSE_FNO`, `securityId=47298`, `interval=1`. Data only.

Warehouse ingest does **not** currently feed `tv-ep-grid`; the factory reads `data/recon/ohlc/`.

---

## What ran vs fixture

| | This pass | Earlier factory smoke |
|--|-----------|------------------------|
| Bars | Dhan INDEX + OPTIDX cache | `synthetic_bars()` 280 1m points |
| MIX 001–023 | Named Python ports (`tv_ep/ports.py`) | stubs → DATA_INSUFFICIENT |
| Cells | **228** (1m × NIFTY/SENSEX/BANKNIFTY × INDEX/PREMIUM × param sweep) | 400 fixture cells incl. 3/5/15m |
| Counts | WATCH 53 · TESTED_FAIL 124 · PARK 51 · DATA_INSUFFICIENT **0** | stubs DI |

**WATCH on INDEX is proxy index points, not option P/L.** Every scored **NIFTY PREMIUM** cell with n≥5 is **TESTED_FAIL** after `HYPOTHESIS_OPTION_RT_1PCT`.

---

## MIX that actually traded (1m)

### NIFTY INDEX 1m (sid 13) — trades > 0

001, 002, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 018, 022, 023, 024, 025.

**Zero trades (PARK):** 003 (CSV replay, no file), 017 (PMax no flip this window), 019 (no session gap vs min rule), 020 (MACD martingale long-only), 021 (LUBE friction).

### NIFTY PREMIUM 1m (23500 PE sid 47298) — trades > 0

001, 002, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 018, 020, 022, 023, 024, 025.

Same zeros: 003, 017, 019, 021. **020** traded only on premium (n=12).

On PREMIUM the simulator **longs the cached PE**; opposite lean = exit. TV long/short on the **index** is not the same book as buying 23500 PE.

### SENSEX 1m

INDEX traded the same MIX family as NIFTY INDEX. PREMIUM used **3-day rolling ATM PE**, not a fixed strike — n is small; still after-cost **TESTED_FAIL** where n≥5.

---

## TV Strategy Tester vs this engine

| | TradingView tester (founder screen) | this factory |
|--|-------------------------------------|--------------|
| Series | Chart symbol (NIFTY or 23500 PE) | INDEX 1m **or** one OPTIDX sid |
| Fill | TV broker emulator (often signal close / tick) | **next bar open** |
| Session | Chart timezone; often 24x7 on US/crypto pines | IST; STRAT-009 flatten ≥15:15 on cache grid (`use_009=True`) |
| Costs | TV commission/slippage inputs (often 0) | INDEX: **no** option haircut. PREMIUM: **1% round-trip hypothesis**. Statutory India costs **UNKNOWN** |
| Qty / pyramiding | Pine `strategy.*` | 1 unit lean; martingale/Kelly **ignored** |
| Report | Per signed-in chart — **not in git** | `tv_ep_leaderboard.json` |

Do **not** expect TV net P/L on 23500 PE to match INDEX-point WATCH cells. Do **not** treat our PREMIUM after-cost as TV’s report until founder exports the tester CSV.

---

## Tune notes (not a retune write)

- **004** TV default 9/21 is INDEX **TESTED_FAIL** (−70 pts); nearby **13/34** is INDEX WATCH (+120). PREMIUM both **FAIL**.
- **001** harvest-month filter is a commodity calendar on 1m NSE — INDEX WATCH, PREMIUM FAIL.
- Faster oscillators (009, 010, 018) print huge trade counts; INDEX WATCH can be churn; PREMIUM FAIL after 1% haircut.
- **025 MACD** INDEX FAIL on this 0.12y 1m book (fixture had WATCH on synthetic trend).
- Next backtestable change: (1) align INDEX window to 23500 PE (need INDEX 1m **2026-08-18–09-11**); (2) score **3m** resample of the same 23500 PE; (3) walk-forward after 09-15 expiry using the **next** weekly PE sid — not this 47298 forever.

**NO_PROMOTE.** Customer `/` unchanged.

---

## Need from founder

1. **Export TV Strategy Tester** CSV/PNG for **NIFTY 23500 PE 1m** (and NIFTY INDEX 1m) with commission settings visible — listing page has no report table.
2. **More INDEX 1m after 2026-09-03** if HQ will serve it (this refresh did not fill 09-04–09-14).
3. After **2026-09-15** expiry: new universe + fetch for the **then** ATM/ITM PE (23500 sid 47298 will go stale).
4. Optional: SENSEX OPTIDX 1m universe (today only ATM premium_tape, 3 days).
5. Confirm whether TV chart is **NSE:NIFTY** cash or a futures continuous — we scored **IDX_I 13**, not FUTIDX.

---

## HANDOFF

| Accepted | Rejected | UNKNOWN / DATA_INSUFFICIENT |
|----------|----------|------------------------------|
| Real 1m INDEX NIFTY/SENSEX/BN cache + real 23500 PE OPTIDX 47298; premium_tape ATM for SENSEX/BN; 001–025 named ports; param sweep defaults vs nearby | Fake 23500 path; promoting INDEX WATCH; live orders; npm restart | TV tester numbers; statutory costs; INDEX tape 09-03→09-14; SCORE_SAMPLE (NEWS_CALENDAR empty); next-expiry PE |
