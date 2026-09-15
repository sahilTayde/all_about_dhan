# Exam note — index price change vs premium residual (MIX-FORM-*)

**Layer:** `VALIDATION` (cache numbers) + `HYPOTHESIS` (formulas)  
**Chair:** phd_math · Artifact: [`INDEX_CE_PE_EDA.md`](../../INDEX_CE_PE_EDA.md) · **NO_PROMOTE**

## What the oral wants

If the index moves, a **textbook** CE/PE should move with a hedge ratio. On a **live weekly**, percent-of-premium returns, theta, and sticky OPTIDX quotes break that line. We therefore split:

1. **Explained** move: \(k\, r^{\mathrm{idx}}\)  
2. **Residual** ε = r_opt − k r_idx  

A large residual is “premium did not follow the index the way this **fitted k** expected.” That is a **HOLD / dual-tape** sentence, not a buy.

## Tokens for FTS

premium residual, MIX-FORM-BETA-RESID, MIX-FORM-DIVERGE-Z, MIX-FORM-FOLLOW-GAP, MIX-FORM-STRADDLE-RET, INDEX_CE_PE_EDA, price change vs premium

## Desk mapping

| ID | Formula (HYPOTHESIS) | Use |
|----|----------------------|-----|
| `MIX-FORM-BETA-RESID` | ε = r_opt − k r_idx, k = OLS no intercept | Not delta, not IV |
| `MIX-FORM-DIVERGE-Z` | z(ε) window 30 | Feature hygiene; constant residual → null |
| `MIX-FORM-FOLLOW-GAP` | idx↓ & r_PE≤0 or idx↑ & r_CE≤0 | Dual-tape HOLD language |
| `MIX-FORM-STRADDLE-RET` | r_CE + r_PE | Crude vol proxy, **not** IV |

**Measured (one book, 2173 1m returns, INDEX 13 ∩ 23500 CE 47297 ∩ 23500 PE 47298):** corr(idx, PE) **−0.823**; corr(idx, CE) **+0.551**; PE diverge \| idx↓ ≈ **0.30**; CE diverge \| idx↑ ≈ **0.85**. PE tracked inverse **tighter**. Does **not** say buy PE.

Code: `trading_agents_india/index_ce_pe_formulas.py` · CLI: `python -m trading_agents_india index-ce-pe-eda`

## DATA_INSUFFICIENT

INDEX cache last **2026-09-03 14:19**. ATM premium_tape ∩ INDEX = **0** → no triples on 2026-09-09..11. 23350 CE frozen print → CE beta `DATA_INSUFFICIENT`. No IV/delta on this EDA. BANKNIFTY/SENSEX not in the primary table. OOS+NORMAL not done.

## Exam trap

“Index down, buy PE” without residual / quote-live / FOLLOW-GAP. Dealer: **do not** buy the option merely because NIFTY printed.
