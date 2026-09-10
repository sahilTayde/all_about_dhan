# Front desk — dealer + customer portal

**Department:** D5  
**Boss:** 05 Dealer  
**Talks to:** Faculty Dean, 03 clocks, 06 analog (often empty), 07 `/`, Gemini+OpenAI counsel  
**Product:** customer `/` — signal portal (Stratzy class). **No live orders.** UX: [`CUSTOMER_PORTAL_UX.md`](../../../docs/CUSTOMER_PORTAL_UX.md).  
**Stages:** WATCH → EARLY → CONFIRMED → **IN-PROGRESS** → ACHIEVED / STOPPED / INVALIDATED / EXPIRED / `DEALER_KILLED`.

---

## Job

Act like a **dealer**: publish a ticket only if trend + **3m** chain + cited news + **feasibility** agree. If Gemini/OpenAI say exit/reversal on **our** facts, the dealer **kills, holds, or issues a partial-book / exit-review warning** — they still do not invent a new strike from a vibe. Fast path uses local rules only; counsel is advisory and cached.

Nightly (or a background poll) stores the published ticket + outcome + **mistake note**. Faculty uses that note to propose the next parameter change. Do not keep a dead IN-PROGRESS on the portal.

---

## Feasibility (founder lesson)

Example that must never stay live: NIFTY CE premium near **150**, stop **96**, target **250** when that target is not reachable on a realistic same-session move (ATR / typical premium path / time-to-expiry).  

Code: `warehouse.feasibility.evaluate_long_premium` — `python -m warehouse check-ticket`. Not wired to customer `/` yet.

Rules (deterministic, no fill invented):

1. Stop and target must be on the **same side of reality** as a long premium (target > entry > stop for a long CE/PE).  
2. Target distance vs stop distance must not imply a fantasy R-multiple vs **today’s** index range / option ATR if we have those numbers; else `DATA_INSUFFICIENT` and **HOLD**, not a hero target.  
3. Ticket TTL must depend on stage and data freshness. A WATCH can wait; a CONFIRMED ticket with stale tape cannot stay live.
4. Exit / kill / expire has priority over new entry.
5. On kill: state `FEASIBILITY_REJECTED` or `DEALER_KILLED`, reason + rule id, ticket **off** the live board.

Counsel reviews the **reason**. Counsel does not draw the strike.

Minimum reason codes:

| Code | Meaning |
|------|---------|
| `TARGET_FEASIBILITY_FAIL` | Target too far vs premium path / day range / time |
| `STOP_FEASIBILITY_FAIL` | Stop unrealistic or inconsistent with long premium |
| `STALE_TAPE` | Data age exceeds stage TTL |
| `COUNSEL_SPLIT` | Gemini/OpenAI disagree on our reasoning |
| `OI_REVERSAL_REVIEW` | OI / premium path changed enough for live risk counsel |
| `PARTIAL_BOOK_REVIEW` | Favorable move exists but reversal risk rose; review booking some lots |
| `EXIT_REVIEW` | Setup invalidation/reversal risk rose; review exit / no new entry |
| `NEWS_HOLD` | Cited event makes entry unsafe |
| `CHAIN_DATA_INSUFFICIENT` | 3m chain not fresh enough |

## Live Counsel Loop

Triggered only when a material change happens:

- sudden OI unwind/build against ticket
- premium velocity fades near target
- spot rejects an important level
- news shock appears
- ticket approaches stop / target / invalidation

Input to LLM = compact JSON state. Output = advisory reason code. Final customer state still comes from local deterministic rules + dealer boss. Counsel cannot place orders or create a fresh ticket.

---

## Clubbing with `/pm`

One Vite app. **`/`** = customer. **`/pm`** = founder. Same process can feed both. Do not show key-expiry red banners as the customer hero.
