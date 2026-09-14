# Exam note — Derman, *Models.Behaving.Badly*

**Cite:** Emanuel Derman, *Models.Behaving.Badly.*, Free Press / S&S. **Chair:** phd_math.

## What the oral wants

Physics envy. A pricing or signal **model** is a **metaphor** for a sliver of the world. It **fails** when the story’s assumptions fail (crisis, holiday, IV crush, wrong strike). Humility is a risk control.

## Tokens for FTS

models behaving badly, metaphor, theory vs model, HOLD, PREMIUM_DIVERGENCE, dealer

## Desk mapping

| Failure mode | Human dealer | Our code |
|--------------|--------------|----------|
| Spot down, PE not up | Do not buy PE “because index” | `FOLLOW-GAP` / dual-tape `PREMIUM_DIVERGENCE` |
| ML cluster looks clean | Ask if holiday/stale | Ganesh Chaturthi = no SCORE_SAMPLE |
| Black-Scholes delta | Local, not a law | Do not invent IV; residual ε = r_opt − k r_idx |

Combine with **Volatility Smile**: even a “good” BS delta is **strike-shaped**. Combine with AFML: a badly specified **label** is a badly behaved model.

## Exam trap

“The model said 61% WR on index.” Derman: that is a **theory about the index book**, not about 23500 PE rupees.
