# BACKTEST_PROJECT — 2026-09-03 (MIX-MTF-TREND / MIX-CONFIRM-5M)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / engine ran / **not a promote**  
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Origin:** **`PROJECT_MIX`** — not DHAN-DERIVED. Charters: [`MIX_PROJECT_2026-09-03.md`](../../04_quant/docs/MIX_PROJECT_2026-09-03.md), [`MIX_PROJECT_VALIDATION.md`](../../02_phd_math/docs/MIX_PROJECT_VALIDATION.md).

Command: `python -m backtest_engine --live --years 5 --interval 1 project`  
Artifact (gitignored): `data/recon/BACKTEST_PROJECT_2026-09-03.json`

Universe: **NIFTY** and **SENSEX** only. Strike: **005 ITM** (CE ATM-2 / PE ATM+2). Flatten **009**. No 007/008/002. Costs **UNKNOWN**. News **not** stripped. INDEX 3m leans are **not** FUTIDX VWAP.

Book analyst (Murphy MTF + Natenberg theta / do not buy calls into a larger downtrend) + [OIC time decay](https://www.optionseducation.org/news/april-office-hours-faqs-options-strategy-time-decay-and-market-mechanics) tagged **VALIDATION language only** — not a win-rate.

## Scores (option premium, optimistic)

| Book | Underlying | OOS n | OOS wr | OOS exp | Rating |
|------|------------|------:|-------:|--------:|--------|
| MIX-MTF-TREND | NIFTY | 604 | 35.6% | −1.81 | FAIL |
| MIX-CONFIRM-5M | NIFTY | 1884 | 42.5% | −0.11 | FAIL |
| MIX-MTF-TREND | SENSEX | 562 | 36.3% | +7.45 | FAIL (wr < 45%) |
| MIX-CONFIRM-5M | SENSEX | 1917 | 40.5% | +6.96 | FAIL (wr < 45%) |

Fewer trades than naked 003 (MTF NIFTY n=3017 vs ~13k Gokul-009). **Still FAIL.** Do not grid MACD 12/26/9 or ST 10,3. Do not make either the customer default.

SENSEX **IS** wr ~10–12% is the same early rolling **EMPTY** gap as the teacher-club run — do not treat it as a mix theorem.

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: two PROJECT_MIX books ran on ingested rollingoption; ALL FAIL; KEEP_ALL.
Rejected: promote; CANDIDATE; ST/MACD p-hack; relabel DHAN-DERIVED; live orders.
UNKNOWN: costs; FUTIDX VWAP; SENSEX 2021 gap; Q12 fills.
```
