# BACKTEST_ML_GREEKS — MIX-ML-GREEKS on 2026-09-16 dual-tape

**Team:** 06 · **Book:** `MIX-ML-GREEKS` (`ml-greeks-v1`)  
**Layer:** `HYPOTHESIS` · **NO_PROMOTE** · gate not `RESEARCH_READY_FOR_PROGRAMMING`  
**CLI:** `python -m desk_ml paper-scalp --source dual-tape --live-session --no-write`

Walked **today IST** dual-tape JSONL (INDEX+ATM, ITM wings when present). Not a live fill. Not a five-pass.

| Book | n_closed | paper wr% | sum ₹ | n_open |
|------|----------|-----------|-------|--------|
| MIX-DEFAULT-BUY | 250 | 31.6 | −7933.75 | 3 |
| MIX-ML-GREEKS | 28 | 28.57 | −1575.75 | 2 |

Desk-wide replay (8 books) n_closed=1772 overall ₹−65562.5 — **not** a rank claim; MIX-ML-GREEKS only trades when Dhan greeks/IV parsed (most of the session wings were LTP-only until the 15:20 IST parser).

**Leaderboard slices (this book only):** NIFTY 15 closes wr 33.33% ₹−770; BANKNIFTY 13 closes wr 23.08% ₹−805. SENSEX mostly held out (high |theta|/entry and/or missing wings).

**Verdict:** `BACKTEST_REQUIRED` tomorrow live. Selectivity worked (28 vs 250). Hit rate did **not** beat dealer on this one session. Grid next: `IV_RICH_ABS` / `THETA_BLEED` / late clock. **NO_PROMOTE.**
