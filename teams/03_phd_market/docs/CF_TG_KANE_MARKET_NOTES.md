# 03 — Market notes on TG Capital + Trader Kane CF binds (Phase-6)

**Team:** 03_phd_market  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` microstructure / transfer  
**Binds:** [`ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md), [`HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)

## TG Capital — asset & session

| Spoken | NSE transfer |
|--------|----------------|
| FX USD pairs + gold primary; NQ named bullish | FX pip microstructure ≠ NIFTY OPTIDX lots/expiry |
| London killzone 3:00–~6:30 **NY**; prefer 2:30/3:00 FVG | London NY clock → IST ≈ midday NSE — **not** 1:1 killzone; map = `DATA_INSUFFICIENT` |
| 30m entry / daily TP | NSE OHLC proxy OK; 30m exact vs 3m resample = honesty gap |
| ~10 pip FX SL; gold close-below | Do **not** invent NIFTY point stops from pips |

## Trader Kane — asset & session

| Spoken | NSE transfer |
|--------|----------------|
| **NQ only** primary; **ES** for SMT divergence | Single NIFTY INDEX **cannot** host true SMT — mark `DATA_INSUFFICIENT` |
| Most active ~9:15–11 EST; 10 AM manipulate | NSE cash open 09:15 IST ≠ US RTH open; map = `DATA_INSUFFICIENT` |
| Asian range low probability | Asia mark transferable as concept; do not invent India Asia box from US hours |
| BTC/ETH multiasset anecdote | Crypto venue ≠ Dhan OPTIDX |
| Tariff/tweet news spikes | Event path — hold ticket / remember event type; not catalog delete |

## Shared gaps

- **GEX / dealer / option chain:** **not in either recipe** — do not invent India GEX filter.  
- **OF / footprint:** not required.  
- **Lots / fills / prop payouts:** do not invent from Apex / Think Capital stories.  
- **ASR quality:** `[ASR]` — killzone/FVG/PO3 noun errors → UNKNOWN.  
- **Title 90% wr (TG):** marketing — not product metric.

## CAS / clocks

No Closing Auction Session content. Do not attach `CAS-*`.

## Verdict

Keep `MIX-CF-TG-*` and `MIX-CF-KANE-*` as **EXTERNAL** separate books. India path = OHLC **proxy** or stay honest `DATA_INSUFFICIENT` on London/EST/SMT arms. **Do not veto** guest recipes for transfer risk alone.
