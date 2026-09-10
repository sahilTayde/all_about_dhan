# Customer portal UX standard

**Date:** 2026-09-09  
**Surface:** customer `/`  
**Goal:** beautiful, fast, simple, trustworthy signal portal.

---

## Experience Promise

The customer should understand the desk in five seconds:

1. Market view: CALL / PUT / HOLD.
2. Ticket: index, strike, entry, stop, target, time.
3. Status: WATCH / EARLY / CONFIRMED / IN-PROGRESS / HOLD / killed / closed.
4. Why: one plain-English line.
5. Risk: what invalidates it.

No indicator soup. No fake win rate. No dead ticket left live.

---

## Page Layout

| Zone | Content |
|------|---------|
| Hero | Current index + CALL / PUT / HOLD + status color |
| Ticket card | Strike, entry, stop, target, quantity note, expiry/time |
| Dealer note | Plain English: trend + 3m chain + cited news |
| Risk strip | “Invalid if...” + stale timer |
| Outcome strip | ACHIEVED / STOPPED / INVALIDATED / EXPIRED / DEALER_KILLED |
| Book | Today only, clearly MOCK/PAPER/SHADOW until real |
| Help | `(i)` legend, short |

Desktop may show extra panels. Mobile shows only hero, ticket, risk, and one book summary first.

---

## Visual Rules

| Color | Customer meaning |
|-------|------------------|
| Green | Valid / achieved / market data fresh |
| Blue | Watch / early setup |
| Amber | Hold / waiting / data insufficient |
| Red | Stopped / invalidated / dealer killed |
| Grey | Closed / stale / market off |

Use high contrast, large numbers, and touch-friendly buttons. Avoid tiny dense tables on the primary screen.

---

## Speed Rules

- Load from a single precomputed JSON payload.
- No Dhan calls from browser.
- No LLM calls from browser.
- Lazy-load charts and research panels.
- Show stale data banner if payload age exceeds the state TTL.
- Keep customer payload small: no raw chain, no full indicator arrays.

---

## Trust Rules

- If a signal is not usable, say **HOLD** or **DEALER_KILLED**.
- If data is missing, say `DATA_INSUFFICIENT`.
- If the book is mock/paper/shadow, label it in the card header.
- If counsel is split, do not present the ticket as clean.
- Never display backtest proxy win rate as customer performance.

---

## Founder Lesson Rule

A ticket like NIFTY option premium **150**, stop **96**, target **250** must pass feasibility before it ever reaches the hero card. If not:

```text
state: DEALER_KILLED
reason_code: TARGET_FEASIBILITY_FAIL
customer_copy: Target is not realistic for current premium path. Holding this call.
```

No fake fill, no silent target change, no leftover IN-PROGRESS.

