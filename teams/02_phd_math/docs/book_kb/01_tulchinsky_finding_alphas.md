# Exam note — Tulchinsky, *Finding Alphas*

**Cite:** Igor Tulchinsky (ed.), *Finding Alphas*, Wiley. **Chair:** phd_quant. **Layer:** VALIDATION.

## What the oral wants

WorldQuant’s public teaching: an **alpha** is a small, tested signal with an economic story, not a TradingView screenshot. Production is a **factory** (many candidates, harsh decay, costs) with a **gate**. Researchers do not each fire live.

## Tokens for FTS

alpha factory, decay, capacity, expression, KEEP_ALL, MIX-TV-EP, one ticket, RETUNE_GATE

## Desk mapping (our product)

| Book idea | We do | We do not |
|-----------|--------|-----------|
| Many hypotheses | MIX-TV-EP-001… + STRAT-001–014 KEEP_ALL | 23 live votes |
| Test then allocate | paper + OOS + 09 five-pass | “tune until green today” |
| Decay | premium 1% RT FAIL vs index WR | treat index WR as alpha |
| Expression language | Python adapters + MIX-FORM-* | dump Pine into `/` |

## Exam trap

“Best alpha wins the day” = **overfit**. AFML agrees (multiple testing). Combine: Tulchinsky **inventory** + López de Prado **purged CV** before any `MIX-DEFAULT-BUY` param write.

## Next 06 ask

Score **expression families** (MA cross vs residual-z) on **same-day** INDEX∩CE∩PE — not clock-aligned 09-03 vs 09-11.
