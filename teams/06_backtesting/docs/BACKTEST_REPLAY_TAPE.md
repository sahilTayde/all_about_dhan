# BACKTEST_REPLAY_TAPE — queryable paper tape (NO_PROMOTE)

**Team:** 06_backtesting · 07 `desk_ml` / `trading_agents_india`  
**Status:** `HYPOTHESIS` / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`

Education ≠ advice. One-day P/L is not a promote. Do not invent Dhan fields.

SQLite lives in local `trading_agents_india.sqlite` (`replay_*` tables). **Do not git-add.** JSONL dual-tape stays the raw append log.

---

## Why this file exists

JSONL-only ticks made **DATA_INSUFFICIENT** whenever INDEX 1m REST failed even if ATM CE/PE printed. Replay of SIDEWAYS / trend / SL / ML needs **columns**, not a 3 MB blob.

**Carry rule:** if Dhan INDEX 1m misses, persist `INDEX_CARRY_PREV` last good LTP (`index_source=carry_prev`). That is not an invented quote.

**India VIX:** no Dhan field in this loop yet — `replay_features` / `replay_index` stay nullable. Do not fake VIX.

---

## Lightweight schema (`DualTapeStore`)

| Table | Grain | Use |
|--|--|--|
| `replay_index` | und × unix ts | INDEX LTP + OHLC/volume/OI if the 1m bar had them |
| `replay_premium` | und × ts | ATM + ~100pt ITM CE/PE LTP, volume, greeks if chain sent them, PCR |
| `replay_strike` | und × ts × strike | Wing quotes: CE/PE LTP + OI/delta when present |
| `replay_features` | und × ts | RSI14 + MACD(12,26,9) from stored INDEX closes |
| `replay_decision` | row | Desk verdict + paper OPEN justification |
| `dual_tape_ticks` | tick | Full JSON payload (debug) |

Query examples (paper):

```sql
SELECT und, datetime(ts, 'unixepoch') , ltp, src FROM replay_index WHERE und='NIFTY' ORDER BY ts;
SELECT rsi14, macd FROM replay_features WHERE und='NIFTY' ORDER BY ts DESC LIMIT 20;
SELECT strike, ce_ltp, pe_ltp, ce_oi, pe_oi FROM replay_strike WHERE und='NIFTY' AND ts=?;
SELECT action, reason, justification FROM replay_decision WHERE und='NIFTY' AND action LIKE '%PE%';
```

Paper tickets also stamp `justification` on OPEN/CLOSE (dashboard + model log).

---

## Improvements kept (ship for 18 Sep paper)

1. **Overlay:** NIFTY **CE or PE** + `nifty_need_strength` + max 4 fills/book + align impulse + skip CE after CE STOP. Skip BN and SENSEX NEW. No T2. PE-only was a 17 Sep dump keep, **not** an all-day lock.  
2. **Stops/targets:** NIFTY ATR+fib premium points (stop 6–18, trail 4–10, R:R 1.25–2.5). Strict first TARGET. Path SL until TARGET.  
3. **BIN:** ITM ~100pt wing; bin chooses side; last-3 does not override until pause-continue.  
4. **SL planning:** floor vs 1m premium ATR; do not ratchet to a 3–5₹ pocket; trail after fill.  
5. **Trend / reversal / sideways:** INDEX 1m TREND/SIDEWAYS; SIDEWAYS skips NEW; TREND_UP kills PE / TREND_DOWN kills CE; last-3 confirm vs trap.  
6. **Risk:** one open per book×und; Groww+STT; Mon–Fri 09:30 NEW; 15:16 flatten; ticks to 15:29 no trade; no Sat/Sun dual-tape; session fill cap.

---

## 17 Sep vs 18 Sep (paper unique, not a promote)

| Topic | 17 Sep (full tape replay) | 18 Sep (live paper from ~11:07 IST overlay) |
|--|--|--|
| Overlay | Best NIFTY: PE+strength+max4 unique **+3299** wr 75% n=8. CE+PE **−10172**. Combined NS +2696 was SENSEX hiding NIFTY red. | Same overlay **on**. Partial session; EOD write=false still required. |
| SL / target | Path SL; first TARGET booked; T2 parked (−54k if on). Med NIFTY stop ~16.5pt / target ~27pt. | Same point engine. |
| BIN | 12:37 CE STOP was ITM bin CE — that wing is now filtered. PE TARGET 13:24 was the working book. | PE-only so CE bin cannot open. |
| SL planning | Tight NIFTY ATR vs wide SENSEX. Skip-side-after-any-STOP killed TARGET (−1375). | Cap 4 fills/book cuts afternoon spray without a 13:30 clock. |
| Trend / reverse / sideways | Pause vs confirm identical on NIFTY that day. Session-lean still let CE (−1185). | SIDEWAYS still skips NEW. INDEX carry if 1m REST fails. |
| Risk | Do not trade NIFTY+SENSEX same time. BN parked. | Skip SENSEX+BN NEW. Justification on each OPEN. |

**What likely worked 17th for NIFTY:** skip CE (the bleed), require strength so PE is not a spray, cap tickets so late STOPs do not eat the TARGET.

**18th:** keep that overlay until EOD replay says otherwise. PE-only dies on a rally day — that is the known caveat.

**NO_PROMOTE.** OOS+`NORMAL` still missing.
