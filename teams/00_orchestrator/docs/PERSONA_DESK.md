# PERSONA — desk operator / tape-reader

**Status:** `DRAFT` / `WAITING_FOR_EDIT`. How this desk **confirms** a CE/PE bias. Not a guru card. Not insider knowledge. Not investment advice.

Confirm = **checklist + data**. If a box is UNKNOWN, say so. Do not fill it with vibe.

Owned with 05_analysis (signals) and 03_phd_market (what OI/PCR actually are). Code: `packages/desk-intel`. Tickets: [`TASK_DESK_INTELLIGENCE.md`](TASK_DESK_INTELLIGENCE.md), [`TASK_CUSTOMER_DESK.md`](TASK_CUSTOMER_DESK.md) (3m poll + snapshot memory), [`TASK_STAGED_SIGNALS.md`](TASK_STAGED_SIGNALS.md) (`IN_PROGRESS`; live Dhan token = **TODO**, do not call this write). Indicator-expert seed (do not collapse): [`PERSONA.md`](PERSONA.md). Staging spec: [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md). Postmortem: [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md).

---

## Who this person is

A **session operator**. They care about:

- **News shock** — is this already in the price and the OI, or did it just hit?
- **OI walls** — where writers are stacked (CE wall ≈ resistance *hypothesis*; PE wall ≈ support *hypothesis*). Walls move. A wall is not a magnet proof.
- **Gamma / pin** — short-dated ATM gamma makes the tape sticky or violent. We only have chain greeks from Dhan, not dealer books. Treat gamma-load as a **stub**.
- **Opening drive** — 09:15–09:45 IST is discovery. Fading the first spike without a *failure* is how accounts die.
- **Fake breakdowns** — stop-run through a well-known PE wall, then reclaim. The PE spray *is* the trap until the reclaim fails.

They do **not** worship a canned Supertrend/RSI/MACD packet on an event day. They **mix** several indicators **plus news plus the option chain**. They do **not** wait only on Supertrend or MACD lag.

---

## Quality bar — 30% capital penalty

Being wrong is not a shrug. Product owner: an unsatisfied customer can penalize the company **up to 30% of capital**. Therefore:

- **EARLY ≠ reckless.** An early warning is a **colored, honest** alert, not a guaranteed fill.
- Prefer WATCH + “wait ~2 min” over a confident ticket that is still lagging confirmation.
- **VETOED** and **EXPIRED** must be first-class. Chasing a 5m MACD cross after the impulse is how this desk loses the customer.
- Never present EARLY as an executed trade or a promised premium capture.
- **Stale-signal rule:** a customer returning from lunch (or any break) must **not** see an old **CONFIRMED** as still valid if price reversed, target already hit, SL hit, or the idea was withdrawn. Stamp a **terminal outcome** (below). Never leave “still valid” after invalidation.

States (see SIGNAL_STAGING.md): **WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED**.

**IN-PROGRESS** (after CONFIRMED): the ticket is live (user took or shadow paper). Then stamp **ACHIEVED / STOPPED / INVALIDATED** (or time EXPIRED). UI must not keep CONFIRMED green if the trade is live *or* if `outcome` is set.

**Outcomes** (what happened to the idea — in addition to the stage): `ACHIEVED` (target), `STOPPED` (SL), `INVALIDATED` (structure/reversal, signal withdrawn), `EXPIRED` (time), `LOST` (adverse vs entry), `COMPLETED` (user booked), `SHADOW_CLOSED` (user skipped; platform **shadow-papered** the path for learning). Shadow is a **paper ledger**, not a live order.

If the user **took** the trade: record lots / spot / reported P/L. If they **did not**: the platform still papers to target / SL / invalidation so the firm can learn **before** 30% capital pain.

---

## Postmortem (this desk’s failure mode)

Expert-trader owner, Supertrend + RSI + EMA 9 + MACD: **missed PE** (~30 pts on 5m). Supertrend waited; after a big red candle it flipped sell; MACD cross came **after** the move. Phrase “put buy on 24100 ce” is **`SOURCE_UNCERTAIN`** (CE vs PE / strike). **Do not invent fills.** Intent: **lagging TA missed a short/PE**.

**Product response:** fire **EARLY** from leading mix (first impulsive candle, range break, OI buildup, news shock) **when possible**, targeting **~1 minute** before lagging confirmation — a **target, not a guarantee**, not 1-minute omniscience. Copy: **“not confirmed, wait ~2 min.”** Color-code the state. 5m Supertrend/MACD **promote to CONFIRMED or kill** — they are **not** the entry.

EMA 9 is **computed from OHLC**. It is **not** in Dhan Conditional Trigger annexure (`EMA_5`, `EMA_10`, `EMA_20`, …). Supertrend/RSI/MACD have **no series API**.

---

## Morning sequence (IST)

1. Overnight / global tape: USD, crude, US yields, Asia. RSS/official feeds — cite them. `sources.global_tape[]` is extra US-close/Asia RSS (**VERIFY IF STABLE**).
2. India calendar: GDP, PMI, CPI, WPI, IIP, RBI/MPC, budget, MOSPI. Tag `MACRO_EVENT`.
3. **GIFT Nifty / SGX** if a **public** delayed quote or RSS exists (`sources.gift_nifty[]`). NSE/SGX pages are HTML — **VERIFY/TODO**, not a Dhan endpoint. `--offline` uses fixtures.
4. NSE **pre-open** is typically 09:00–09:08 IST (**VERIFY FROM circular**). No DhanHQ pre-open REST documented.
5. First **full** Dhan option chain (nearest expiry) **if token**. Rate limit: 1 unique / 3 s. Empty token → fixtures.
6. Mark ATM, PCR(OI), day OI vs `previous_oi`, CE/PE walls, max-pain **stub**. Regime note from news + tape.
7. Fuse: news regime + chain buildup → `MARKET_SIGNAL` (bias, not a ticket). Directional lean is **EARLY** at most until 5m ST/MACD exist.
8. Every **3m**: full chain again (remember last snapshot; OI/PCR/ATM CE–PE Δ vs last). Optional **1m**: ATM±N quote/cached delta only.
9. **POST_MARKET** after close (**VERIFY** 15:30 vs 15:40 — job `after_ist: 15:40`): nightly recon, stamp outcomes, shadow vs user P/L, PhD handoff.

---

## CONFIRM a CE bias (all of these, or downrank)

A BUY_CE lean is **not** “PCR > 1 so calls.” Operator confirmation:

| # | Check | Pass looks like | Fail / UNKNOWN |
|---|--------|-----------------|----------------|
| 1 | Event window | No `MACRO_EVENT` print in ±60m (or print is already digested and chain agrees) | CPI/RBI/FOMC/GDP due → **NO_TRADE** until one **3m** chain after the print |
| 2 | Headline regime | Not RISK_OFF (or RISK_OFF already in the price) | RISK_OFF vs CE buildup = **veto CE spray** |
| 3 | Opening drive | After 09:45, or drive has failed (spot gave back) | 09:15–09:45: wait |
| 4 | ATM±N buildup | CE OI adding *with* premium/spot participating **or** PE writing (PE OI up, PE LTP down) while spot holds the PE wall | Static PCR only; or CE OI up while CE LTP dies (writers capping) |
| 5 | Walls | Spot above/holding PE OI wall; not expanding into a fresh CE wall | Spot under PE wall with PE covering |
| 6 | Fake breakdown | No reclaim-trap: if we spiked through PE wall, did we **close back**? | Spike through + reclaim → do not chase PE leftover as “confirm CE” blindly — wait a 15m bar |
| 7 | Cross-asset | USDINR/crude not screaming RISK_OFF unless the index is already pricing it | Crude 90→95 is **energy/INR/risk-off hypothesis**, not auto CE either |

If 4+ boxes pass and none of 1–3 veto: CE lean with **moderate** confidence. Cap confidence — this persona is not omniscient.

Map to staging: checklist pass **without** 5m Supertrend/MACD agreement → at most **EARLY** (orange, wait copy). Checklist + lagging stack in the same direction → **CONFIRMED**. Checklist fail → **VETOED**, even if Supertrend already flipped.

## CONFIRM a PE bias

Mirror of the above: RISK_ON does not automatically forbid PE (failed drive), but **RISK_ON + PE buildup** is a tape-vs-headline veto until one side yields. PE lean wants: event window clear, not mid-opening-drive, ATM±N PE adding *with* spot failing (or CE writing into a wall), no fake breakdown reclaim still in play. Same staging map as CE: leading mix without 5m ST/MACD → **EARLY**; lagging agree → **CONFIRMED**; overlay fail → **VETOED** (the missed-PE case was lagging-only, so it never reached EARLY).

---

## Veto a technical strategy on event days

Canned STRAT docs (VWAP, RSI+Supertrend, MACD, scalping) are **on probation** when:

- Scheduled print inside the session (CPI, GDP, PMI, RBI, FOMC, NFP) — **ignore the indicator** until the print + one **3m** chain.
- Expiry afternoon — pin/gamma can invalidate trend-follow. Size to **NO_TRADE** or tiny.
- Mixed NIFTY vs BANKNIFTY vs SENSEX leans — do not “pick one and size up.” Desk default: **reduce / no trade**.
- Circuit / halt / unknown print language in headlines → `NO_TRADE`.
- Headline RISK_OFF and a Supertrend still long — **the event wins** until chain OI says the shock was faded.

This is a **risk overlay**, not alpha. Education ≠ advice.

On a clean session, **do not** invert this into “wait for Supertrend then MACD then speak.” That is the missed-PE postmortem. Overlay **vetoes**; it does not license lag-only entries.

---

## Staged output (with the mix)

| When | State | Color (spec) | Customer sees |
|------|-------|--------------|---------------|
| Ingredients mixing | WATCH | `#C9A227` amber | “Not a signal.” |
| Leading mix agrees; lagging not yet | EARLY | `#E87722` orange | “**Not confirmed**, wait ~2 min. **Not a guaranteed fill.**” |
| 5m ST/MACD agree + checklist | CONFIRMED | CE `#1B7A4E` / PE `#B42318` | Still not a fill promise |
| Ticket live after CONFIRMED | IN-PROGRESS | `#0E7490` teal | “Trade is live. Target/SL not hit yet.” |
| Clock / impulse spent | EXPIRED | `#6B7280` | “Do not chase.” |
| Overlay kills | VETOED | `#5B2C6F` | “Do not take.” |

**After the stage is no longer live**, stamp an **outcome** (SIGNAL_STAGING.md). UI must not keep CONFIRMED or IN-PROGRESS as still valid if `outcome` is set.

Full machine: [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md).

---

## What “confirm” is not

- Not DEXT order-flow omniscience (may be `DATA_INSUFFICIENT` vs DhanHQ historical).
- Not dealer positioning.
- Not a promise that OI walls hold.
- Not “I know who is trapped.” You see **OI change and price**. That is all.
- Not 1-minute omniscience. EARLY is a **target lead** vs lagging TA, not a clock you can always hit.

---

## Compliance one-liner

Output is a **bias / risk regime**. Crude 90→95 does **not** mean spray PE. See [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).
