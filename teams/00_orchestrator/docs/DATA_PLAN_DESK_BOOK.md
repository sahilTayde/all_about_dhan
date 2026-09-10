# Data plan — chain + constituents (faculty)

**Date:** 2026-09-10  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**  
**00 ruling after 01–06 / 09 notes below.**

The founder asked why the warehouse lacked option-chain parameters, CE/PE strike/stop language, and the **stocks that move** NIFTY / BANKNIFTY / SENSEX. That gap is real. Compact ATM/PCR was a first ingest, not a desk book.

---

## Coalition (what each chair said)

```text
From: 03 PhD market
Cite: CHAIN_METRICS.md, SKILL.md, PERSONA_DESK.md
Accepted: POST /optionchain fields (strike, ce/pe last_price, oi, previous_oi,
  volume, security_id, greeks.*) are SOURCE_FACT when parsed. PCR(OI), ATM,
  walls, max-pain stub are VALIDATION definitions. Index is a weighted basket
  of cash names; cash-index volume is not a VWAP tape.
Rejected: Invent NSE/BSE official weights. 1m full-chain poll.
UNKNOWN: live bid/ask key names if missing on a row; lot size FROM_MASTER.

From: 02 PhD math
Cite: VALIDATION_MATH.md, DHAN_INDICATOR_API_MAP.md
Accepted: long CE/PE stop/target in *premium* must be target > entry > stop.
  Dhan greeks/IV methodology UNKNOWN — store numbers, do not treat as win odds.
Rejected: 0.75/1.25 SL-TP as a theorem. Conviction % = delta.
UNKNOWN: vendor Greek engine.

From: 04 Quant
Cite: SIGNAL_STAGING.md, lean_mix.py
Accepted: ATM CE and PE LTP are the only honest ticket numbers from gather.
  Empty SL/TP when LTP missing. 5m ST/MACD still confirm-or-kill.
Rejected: CONFIRMED from chain alone. Stock-options STRAT-015+.
UNKNOWN: whether a heavy-weight EQ dump should veto an index CE (HYPOTHESIS).

From: 05 Fusion / dealer
Cite: FRONT_DESK.md, CUSTOMER_TALK.md
Accepted: ticket = trend + 3m chain + cited news + feasibility.
  Extreme PCR without price = HOLD. Constituent shock = hold overlay, not alpha.
Rejected: Indicator soup on /. Live orders.
UNKNOWN: official weight file not in repo.

From: 06 Backtest
Cite: RETUNE_GATE.md, BACKTEST_HONEST
Accepted: need strike-level history for option-premium OOS later; do not
  promote from one snapshot. Tag NEWS_DAY / EXPIRY / NORMAL.
Rejected: Blind retune from one chain print.
UNKNOWN: continuous OPTIDX still DATA_INSUFFICIENT for promote.

From: 01 Research
Cite: OPTIONS_INDEX_PACKET.md, DHAN_OFFICIAL_INDICATORS.md
Accepted: spoken desk uses OI walls + ATM; no Supertrend series API.
Rejected: Invent HQ fields.
UNKNOWN: Dhan video does not publish a constituent-weight recipe.

From: 09 Review
Accepted: store layers. Notes ≠ pass. NO_PROMOTE.
Rejected: Treating this book as RESEARCH_READY_FOR_PROGRAMMING.
```

---

## What we store (DATA-002)

| Table | Layer | Use |
|-------|--------|-----|
| `chain_strike_rows` | SOURCE_FACT (parsed HQ) | Every strike CE/PE LTP, OI, prev OI, volume, security_id, greeks if present |
| `option_levels` | HYPOTHESIS | ATM CE and ATM PE: strike, entry=LTP, stop/target **premium** geometry (same 0.75/1.25 as lean_mix — **not** validated SL) |
| `index_constituents` | names VERIFY; **weight DATA_INSUFFICIENT** | Main EQ names for NIFTY / BANKNIFTY / SENSEX + Dhan security_id + LTP |
| `ohlc_bars` | SOURCE_FACT / resample | Index TFs (already) |

**Not stored as fact:** official index weights, fills, win rates, lots.

**Official weight next:** NSE/BSE factsheet / Indxx file when the founder points at a URL. Until then weight_pct stays NULL.

---

## How to pull (no poll loop)

```bash
python -m warehouse desk-book --live
```

Chain: 1 unique / 3s. Quote LTP: one batched `NSE_EQ` / `BSE_EQ` call (≤1000 ids).

---

## What this is not

A stock-trading book. Phase 0 product is still **index options**. Constituents exist so 04/05 can say “heavy bank dump → HOLD BANKNIFTY CE,” not so we ship EQ-* as customer default.
