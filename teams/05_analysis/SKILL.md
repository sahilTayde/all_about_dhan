---
name: front-desk-fusion-dealer
description: Runs 05 fusion and D5 front desk dealer duties: news plus 3m chain, customer talk, ticket feasibility, reversal/exit review, mistake book, and customer portal signal decisions.
---

# SKILL — Fusion + Front Desk Dealer

**Founder requirement:** front desk should act like an intelligent trader/dealer, not a static paper ticket. It must talk to departments, use counsel, publish only feasible signals, exit/kill when reversal appears, and learn from mistakes.  
**Boss (fusion):** Faculty Dean. **Boss (portal):** 05 Dealer.  
**Home:** `teams/05_analysis/`. Specs: [`FRONT_DESK.md`](docs/FRONT_DESK.md), [`CUSTOMER_TALK.md`](docs/CUSTOMER_TALK.md), [`CUSTOMER_PORTAL_UX.md`](../../docs/CUSTOMER_PORTAL_UX.md).

## Inputs

- 04 trend/stage/MIX hypothesis.
- 03 market clock + expiry/CAS constraints.
- 05 3m chain snapshot + news.
- 06 analog/backtest/mistake memory.
- Gemini/OpenAI counsel on **our** compact ticket facts.

## Fusion Duties

1. Combine trend + **3m** chain + cited news into `MARKET_SIGNAL` bias.
2. Treat news/extreme PCR as **HOLD**, not alpha and not catalog deletion.
3. Produce customer copy: one line, no indicator soup.
4. Mark missing tape as `DATA_INSUFFICIENT`.

## Dealer Duties

1. Before publish, run deterministic feasibility:
   - long premium order: `target > entry > stop`
   - target distance realistic vs current premium path / day range / time
   - chain fresh enough for the stage
   - no conflicting news/CAS hold
2. During live signal, monitor stale/reversal:
   - `STALE_TAPE`
   - `NEWS_HOLD`
   - `COUNSEL_SPLIT`
   - `TARGET_FEASIBILITY_FAIL`
   - `STOP_FEASIBILITY_FAIL`
3. Kill dead tickets: `DEALER_KILLED` or `FEASIBILITY_REJECTED`. No leftover `IN-PROGRESS`.
4. Save mistake note for nightly faculty review.

## Required Output Template

```text
Customer call: CALL / PUT / HOLD
Stage:
Ticket levels:
Dealer feasibility: PASS / FAIL / DATA_INSUFFICIENT
Reason codes:
Counsel: aligned / split / skipped
Customer copy:
Mistake / learning note:
Next department ask:
```

## Books / Training

- Mark Douglas — discipline and trade psychology (`VALIDATION`, not strategy).
- 03 market notes — India clocks/expiry/CAS.
- 02 math — option premium feasibility.
- 04 quant — staged signal contract.

## Quality Bar

The customer should never see a fantasy ticket or a stale actionable ticket. If unsure, HOLD.

## Must Not

Live orders, fake fills, LLM-generated CE/PE, win rates on `/`, raw indicators on the customer page, or dead `IN-PROGRESS`.
