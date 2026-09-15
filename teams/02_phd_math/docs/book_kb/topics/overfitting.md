# Exam note — overfitting (research fraud vs this desk)

**Layer:** `VALIDATION` (method)  
**Chair:** phd_statistics · See also `07_afml.md` · **NO_PROMOTE**

## What the oral wants

**Overfitting** is fitting noise so in-sample metrics look like skill. On overlapping 1m bars, standard k-fold **leaks**. “Fit until profitable” on the **same** recon day is the definition of a bad oral.

Symptoms we already encode: one-day paper P/L as “proof”; NEWS_DAY / EXPIRY in the retune sample; promoting from cluster counts; infinite grid on one sid/expiry.

## Tokens for FTS

overfitting, leakage, purged CV, in-sample, SCORE_SAMPLE, ANALOG_MEMORY, one day pnl, research fraud

## Desk mapping

| Trap | Gate |
|------|------|
| Tune on the recon session | [`RETUNE_GATE.md`](../../../../06_backtesting/docs/RETUNE_GATE.md): OOS + `NORMAL` only |
| Event-day “broken book” | Exclude NEWS_DAY / EXPIRY from SCORE_SAMPLE |
| Thin labels | `DATA_INSUFFICIENT` — do not invent a logistic story |
| KEEP_ALL | Graveyard stays; do not delete STRAT-001–014 because one window failed |

**Allowed:** purged/embargoed splits (AFML language); walk-forward **after** a named candidate.  
**Forbidden:** writing `workspace.yaml` / MIX production params from nightly JSON.

## DATA_INSUFFICIENT

SCORE_SAMPLE is still thin / empty in honest leftover notes. No promote path ⇒ any “we fitted well” claim is **not evidence**.

## Exam trap

Calling a FAIL backtest “overfit” **and** deleting the id. FAIL is a **result**. Overfit is a **process**. KEEP_ALL until 06 OOS+NORMAL kills a **MIX**, not a teacher STRAT at spec time.
