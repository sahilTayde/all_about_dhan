# Exam note — “smart money” as OI / chain snapshot language (no conspiracy)

**Layer:** `VALIDATION` (what the chain shows) + `HYPOTHESIS` (interpretation)  
**Chair:** phd_math + 03 + 05 dealer · **NO_PROMOTE**

## What the oral wants

There is **no** identified “smart money” entity in our APIs. Retail YouTube uses the phrase as a **story**. This desk translates it to **auditable snapshot language**:

- Open interest (`oi`, `previous_oi`) on a strike/side  
- Volume vs prior volume on that row  
- PCR / call-put OI tilt on the **3m** chain  
- Bid/ask and last — **who** is not in the file  

A large OI print is **inventory outstanding**, not a named fund, not insider knowledge, not a reason to delete a STRAT.

## Tokens for FTS

smart money, open interest, OI chain snapshot, PCR, previous_oi, no conspiracy, 3m optionchain, HOLD not alpha

## Desk mapping

| Folklore | Snapshot sentence we allow |
|----------|----------------------------|
| “Smart money bought PE” | “PE OI at strike K rose vs `previous_oi` on the 3m book” |
| “They know the level” | “Max OI / max volume strike on **this** snapshot” |
| Extreme PCR | **Hold the customer ticket** — not alpha, not a catalog delete ([`EVENT_MEMORY.md`](../../../../06_backtesting/docs/EVENT_MEMORY.md)) |
| News + OI | NEWS_DAY / analog type; **not** a retune sample |

**Compute:** OI deltas and PCR from fields Dhan returned.  
**Must not:** infer intent, plot a cabal, or invent strikes not in `oc`.

## DATA_INSUFFICIENT

Participant-wise OI (FII/DII/PRO) is **not** a DhanHQ chain field. WS has **no** full strike OI. Between 3m polls, OI is stale. Usman-class “India OI/greeks” recipes stay `DATA_INSUFFICIENT` unless mapped to these fields.

## Exam trap

“Smart money” in a customer `/` sentence. Dealer talk: **trend + 3m chain + cited news**. No conspiracy nouns.
