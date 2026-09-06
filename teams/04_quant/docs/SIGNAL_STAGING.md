# SIGNAL_STAGING.md — WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED

**Team:** 04_quant  
**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Paper `/ws/signals` exists — **not** a fill. Do **not** place live orders.  
**Date:** 2026-09-01  
**Ticket:** [`teams/00_orchestrator/docs/TASK_STAGED_SIGNALS.md`](../../00_orchestrator/docs/TASK_STAGED_SIGNALS.md) · customer desk [`TASK_CUSTOMER_DESK.md`](../../00_orchestrator/docs/TASK_CUSTOMER_DESK.md)  
**Postmortem:** [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md)  
**Persona:** [`teams/00_orchestrator/docs/PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md)  
**Compliance:** education ≠ advice. EARLY is **not** a fill. No 1-minute omniscience.

This spec is the coding/backtest **handoff shape** for later teams. It does **not** claim that a 1-minute lead is achievable, measurable, or profitable. The ~1 minute figure is a **product target**, not a guarantee.

---

## Why this exists

Lagging stack (Supertrend wait-for-flip, then MACD cross) can print **after** a 5m impulse (~30 pts in the reported case). An expert desk does **not** sit on that stack alone. Mix: **price impulse + range + OI/chain + news**, then let Supertrend/MACD **promote or kill**.

Quality bar (product owner): a wrong call can cost the company **up to 30% of customer capital** as a penalty. Therefore:

- EARLY ≠ “spray the ticket.”
- Never present EARLY as a guaranteed fill.
- Prefer a honest WATCH / wait-copy over a reckless EARLY.
- VETOED must be cheaper to show than a confident miss.

---

## Color spec (UI must pair color **with** the state word)

Do not rely on color alone (accessibility + CE/PE direction). Always render **STATE** + **direction chip** + **honesty line**.

| State | Hex | RGB | Role | Required copy (examples) |
|-------|-----|-----|------|--------------------------|
| **WATCH** | `#C9A227` | 201, 162, 39 | Amber. Ingredients mixing. **No fill language.** | “WATCH — mixing. Not a signal.” |
| **EARLY** | `#E87722` | 232, 119, 34 | Orange field. Leading alert only. | “EARLY — **not confirmed**, wait ~2 min. **Not a guaranteed fill.**” |
| **CONFIRMED** CE | `#1B7A4E` | 27, 122, 78 | Green = **bull / BUY_CE lean**, not “good.” | “CONFIRMED CE — lagging stack agrees. Still not a fill promise.” |
| **CONFIRMED** PE | `#B42318` | 180, 35, 24 | Red = **bear / BUY_PE lean**, not “bad UI.” | “CONFIRMED PE — lagging stack agrees. Still not a fill promise.” |
| **IN-PROGRESS** | `#0E7490` | 14, 116, 144 | Teal. Ticket is **live** after CONFIRMED (user took or shadow paper). | “IN-PROGRESS — trade is live. Target/SL not hit yet. Still not a fill promise.” |
| **EXPIRED** | `#6B7280` | 107, 114, 128 | Slate. Window closed. | “EXPIRED — lead window closed. Do not chase.” |
| **VETOED** | `#5B2C6F` | 91, 44, 111 | Purple. Overlay killed the idea. | “VETOED — risk overlay. Do not take.” |

**Timer badge (not a state):** `#2563EB` — “wait ~2 min” countdown on EARLY. When the timer hits zero without promotion → **EXPIRED** (default) unless CONFIRMED or VETOED already fired.

**EARLY direction chips** (outline on orange field, not a fake CONFIRMED):

| Lean | Chip hex | Meaning |
|------|----------|---------|
| CE lean | `#1B7A4E` outline | Hypothetical BUY_CE **watch**, not confirmed |
| PE lean | `#B42318` outline | Hypothetical BUY_PE **watch**, not confirmed |
| Unclear | `#6B7280` outline | Do not pick a side |

**Forbidden:** green EARLY, “entry now,” fill prices on EARLY, treating orange as CONFIRMED.

---

## State machine

```text
                    ┌─────────────┐
                    │    idle     │
                    └──────┬──────┘
                           │ leading ingredient (see mix)
                           ▼
                    ┌─────────────┐
              ┌────►│    WATCH    │◄──────────────────┐
              │     └──────┬──────┘                   │
              │            │ lead threshold (honest)  │ re-mix / new bar
              │            ▼                          │
              │     ┌─────────────┐                   │
              │     │    EARLY    │── timer / spent ─►│ EXPIRED
              │     └──────┬──────┘                   │
              │       ┌────┼────────────┐             │
              │       │    │            │             │
              │       ▼    ▼            ▼             │
              │  CONFIRMED VETOED    EXPIRED          │
              │       │                               │
              │       ▼                               │
              │  IN-PROGRESS (live ticket)            │
              │       │    │            │             │
              │       ▼    ▼            ▼             │
              │  ACHIEVED / STOPPED / INVALIDATED     │
              │     (session clock / flatten)         │
              └───────────────────────────────────────┘
```

### Transitions (allowed)

| From | To | Trigger (HYPOTHESIS — not coded) |
|------|----|----------------------------------|
| idle | **WATCH** | Any **leading** ingredient: first impulsive red/green candle (1m preferred), range break, OI buildup vs last chain snapshot, or news shock (`MACRO_EVENT` / RISK_ON/OFF shift). |
| WATCH | **EARLY** | ≥2 independent leading ingredients **agree on direction**, event window not vetoing, opening-drive rule from PERSONA_DESK not failing, and honesty copy can be shown. **1m lead is a target** vs later 5m Supertrend/MACD — **not** a measured SLA. |
| EARLY | **CONFIRMED** | 5m Supertrend **flip** **and/or** 5m MACD cross **in the same direction**, after the EARLY stamp. RSI/EMA9 are **filters**, not the promotion gate. Desk CE/PE confirm checklist still applies (PERSONA_DESK). |
| EARLY | **VETOED** | Desk overlay: `MACRO_EVENT` undigested, fake-breakdown reclaim, RISK_OFF vs CE spray (or mirror), mixed indices, circuit/halt, chain vs headline contradiction. |
| EARLY | **EXPIRED** | ~2 min wait elapsed **without** CONFIRMED; **or** the impulse is already “spent” (move happened; lagging stack would only chase). Do not invent a point threshold as a law — parameter later. |
| WATCH | **VETOED** | Overlay fires before EARLY. |
| WATCH | **EXPIRED** | Ingredients decay (candle closed back in range; OI buildup reversed; headline already in the chain). |
| CONFIRMED | **IN-PROGRESS** | User took the idea **or** shadow paper is still open. Ticket is live. Not a terminal outcome. |
| CONFIRMED | **EXPIRED** | Session clock / flatten (STRAT-009 style) or expiry afternoon pin → size to no-trade. |
| CONFIRMED | **VETOED** | Late news shock **after** confirm — event wins until a **3m** chain (PERSONA_DESK). |
| IN-PROGRESS | **ACHIEVED** | Target hit while live. |
| IN-PROGRESS | **STOPPED** | Stop-loss hit while live. |
| IN-PROGRESS | **INVALIDATED** | Structure / reversal — withdraw. **Never** still valid. |
| IN-PROGRESS | **EXPIRED** | Session clock / flatten with no target/SL print. |
| Any | idle | New session / operator reset. |

### Outcomes (in addition to WATCH → EARLY → CONFIRMED → IN-PROGRESS)

Stages are the **alert**. **IN-PROGRESS** is the live ticket after CONFIRMED. Outcomes are the **ticket close** so a lunch-return is not a leftover CONFIRMED.

| Outcome | Meaning | still valid? |
|---------|---------|--------------|
| **ACHIEVED** | Target hit (paper or reported) | No |
| **STOPPED** | Stop-loss hit | No |
| **INVALIDATED** | Structure / reversal — signal **withdrawn** | **No. Never.** |
| **EXPIRED** | Time (session clock / lead spent). Close clock is **VERIFY** 15:30 vs 15:40. | No |
| **LOST** | Adverse vs entry without a clean SL print | No |
| **COMPLETED** | User **took** the trade and booked | No |
| **SHADOW_CLOSED** | User **skipped**; platform shadow-papered to target/SL/invalidation for learning | No |

If the user took the trade: track **lots / spot / reported P/L**. If not: still run the **shadow paper** path. Shadow ≠ live order. Jobs: [`TASK_PRE_POST_MARKET_JOBS.md`](../../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md). Nightly recon → PhD `NIGHTLY_YYYY-MM-DD.md` as **REVIEW** (not auto-apply). Session tag `NEWS_DAY` / `EXPIRY` / `NORMAL`; JSON `retune_proposal.status` is **`BACKTEST_REQUIRED`**. Default: **keep current strategy**. 06 backtests OOS + non-event days before any param/strategy promote ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)). Do not invent backtest results. Do not live-trade.

Code stub (not live strategy): `packages/desk-intel` `outcomes.py` + `nightly.py` + `retune_gate.py`. Nightly **will not** write new params into production. 06/08 consume JSON later.

### Transitions (forbidden)

- EARLY → **order** / paper fill / “you are in.”
- idle → CONFIRMED (no skip of WATCH/EARLY **unless** lagging stack printed first — then start at CONFIRMED with copy “late; do not chase” and usually EXPIRED).
- Promoting on Supertrend **or** MACD **alone** while the other **contradicts** — stay EARLY or VETOED, do not CONFIRMED.
- Using 5m MACD/Supertrend as **entry**. They **promote or kill**. Entry language, if any, is a **later** paper-UI concern and still not a fill promise.

If lagging confirmation is the **first** thing you see (the missed-PE failure mode inverted): label **CONFIRMED-late** as copy, prefer **EXPIRED** for new entries. That is the postmortem: the cross after +30 pts is not an entry.

---

## Mix-and-match (do not wait on one lagging stack)

**Leading (can fire WATCH / EARLY):**

| Ingredient | Data (DhanHQ) | Note |
|------------|---------------|------|
| First impulsive 1m (or 5m) red/green candle | `/charts/intraday` OHLC | Range vs prior N bars is a **HYPOTHESIS** parameter. Not omniscience. |
| Range break | same | Prior session high/low, opening range, or marked level — **must** be named in a later spec. |
| OI buildup | `POST /optionchain` (**3m** default); optional 1m ATM±N quote | PCR-only is **not** enough (PERSONA_DESK). Δ vs **last snapshot**. |
| News shock | RSS / official feeds | Tag `MACRO_EVENT`. Shock can EARLY **and** VETO. |

**Lagging (promote to CONFIRMED or kill):**

| Ingredient | Data | Role |
|------------|------|------|
| Supertrend | **Compute from OHLC** (not an HQ series; not annexure) | Confirmation / kill, **not** entry |
| MACD (5m) | **Compute from close** (trigger names `MACD_12`/`MACD_26`/`MACD_HIST` are conditions only; no series REST) | Same |
| RSI | Compute; annexure name is **`RSI_14` only** | Filter, not the gate |
| EMA 9 | **Compute from OHLC** | Filter. **`EMA_9` is not** in Conditional Trigger annexure (5, 10, 20, 50, 100, 200 only) |

**Overlay (VETO / NO_TRADE):** news regime, opening 09:15–09:45 IST, expiry afternoon, mixed NIFTY vs BANKNIFTY vs SENSEX, circuit/halt — [`PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md).

---

## ~1 minute lead — target, not guarantee

| Claim | Layer |
|-------|--------|
| Product **wants** the customer to see EARLY **about 1 minute** before a 5m Supertrend flip / MACD cross **when the leading mix actually printed first** | `HYPOTHESIS` / product requirement |
| That lead is **always** available | **False.** Do not implement math that claims it. |
| 1m charts are in HQ interval enum `{1,5,15,25,60}` | `SOURCE_FACT` (docs 2026-09-01) |
| Chain OI does not update every minute; full-chain 1m poll is the **wrong** default | desk intel + HQ option-chain rate limit |

Honesty when the lead is **not** there: stay WATCH or say “lagging stack already late — do not chase.”

---

## 5m MACD / Supertrend = confirmation, not entry

The missed trade: Supertrend **waited**; after the big red candle it flipped; MACD cross **after** the ~30-pt 5m move. That path is **CONFIRMED-late → EXPIRED** for new risk, not a PE buy ticket.

Use 5m ST/MACD to:

- **Promote** EARLY → CONFIRMED if direction matches and overlay is clean.
- **Kill** EARLY → VETOED or EXPIRED if they never agree or agree the other way.

Do **not** use them as the first reason the customer sees a side.

---

## DhanHQ: compute, do not invent REST

| Need | Official HQ v2 | This desk |
|------|----------------|-----------|
| Supertrend series | **None** | OHLC compute (VALIDATION params vs Dhan **charts** later; spoken 10,3 is not an API field) |
| RSI series | **None**; trigger `RSI_14` only | OHLC compute |
| MACD series | **None**; trigger `MACD_12` / `MACD_26` / `MACD_HIST` | OHLC compute; signal length `UNKNOWN` in annexure |
| EMA 9 series | **None**; annexure EMA is **5, 10, 20, 50, 100, 200** — **no `EMA_9`** | OHLC compute. Do not send `EMA_9` to `/alerts/orders` |
| Bars | `/charts/historical`, `/charts/intraday` | 1m for leading candles; 5m for ST/MACD confirmation |

`packages/indicators` stays **empty** until review. No live-trade of Conditional Trigger.

---

## What coding must not do yet

- Implement this state machine as live signals.
- Claim a 1-minute SLA or omniscience.
- Place orders.
- Rank by backtest return.
- Collapse SOURCE_FACT / VALIDATION / HYPOTHESIS.

Still `UNVALIDATED`. Leave `WAITING_FOR_EDIT`.
