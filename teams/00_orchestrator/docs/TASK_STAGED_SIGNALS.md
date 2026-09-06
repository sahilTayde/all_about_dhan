# TASK — Staged signals (WATCH / EARLY / CONFIRMED) after missed lagging-TA PE

**Date opened:** 2026-09-01  
**Date closed:** —  
**Assigned teams:** **00_orchestrator** (ticket + persona) · **04_quant** (state machine spec) · **09_review** (postmortem)  
**Informed:** 05_analysis (desk intel), 02_phd_math (OHLC compute vs annexure), 07_coding (**blocked** — do not implement)  
**Owner paths:** `TASK_STAGED_SIGNALS.md`, [`PERSONA_DESK.md`](PERSONA_DESK.md), [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md), [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md)  
**Status:** `IN_PROGRESS` (docs) / `WAITING_FOR_EDIT` / **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Live APIs this ticket:** **do not call.** Token validation is **TODO** below.

---

## Requirement

Expert-trader product owner described a **missed PE** while running Supertrend + RSI + EMA 9 + MACD. Supertrend waited for confirmation; after a large red candle it flipped sell; the MACD cross arrived **after** an ~30-pt 5m move. Phrase “put buy on 24100 ce” is **`SOURCE_UNCERTAIN`** (CE vs PE / strike). Intent to capture: **lagging TA missed a short/PE**. Full case: [`MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md).

The product must:

1. Mix **multiple** indicators **plus** news **plus** option chain. Do **not** wait only on Supertrend / MACD lag.
2. Aim for an **EARLY** warning **~1 minute before** lagging confirmation **when possible** — a **target, not a guarantee**, and **not** 1-minute omniscience.
3. Honesty copy + **color coding**: e.g. “not confirmed, wait ~2 min.” Never present EARLY as a guaranteed fill.
4. Quality bar: being wrong is expensive — unsatisfied customer can penalize the company **up to 30% of capital**. EARLY ≠ reckless. States: **WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED**.

Spec: [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md). Persona overlay: [`PERSONA_DESK.md`](PERSONA_DESK.md).

---

## Constraints (kept)

- DhanHQ has **no** Supertrend / RSI / MACD / EMA9 **series API**. Compute from OHLC (`POST /charts/historical`, `/charts/intraday`; intervals **1, 5, 15, 25, 60** min). See [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md).
- Conditional Trigger annexure EMA set is **5, 10, 20, 50, 100, 200**. **`EMA_9` is not in the annexure.** Do not invent `EMA_9` as an HQ `indicatorName`.
- Conditional Trigger evaluates a **condition** and can place orders; it does **not** return series. Documented for **Equities and Indices** only. This workspace **must not** call `/alerts/orders` live.
- Education ≠ advice ([`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md)). Three layers stay separate.
- **No orders.** No live strategy math that claims 1-minute omniscience. Leave `WAITING_FOR_EDIT`.
- Tokens from `.env`. Never log secrets. **Do not hit live Dhan in this ticket.**

---

## Done (this write)

- [x] This ticket (IN_PROGRESS; live token still TODO)
- [x] Postmortem: [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md)
- [x] Staging spec: [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)
- [x] Persona update: [`PERSONA_DESK.md`](PERSONA_DESK.md)
- [x] Pointers: `MASTER_STRATEGY_PLAN.md`, `AGENT.md`, `docs/INDEX.md`

---

## TODO — live Dhan token (do **not** run this ticket)

Conceptual follow-up already exists on [`TASK_DESK_INTELLIGENCE.md`](TASK_DESK_INTELLIGENCE.md): when `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN` are present, run desk intel / chain **for real**. **This ticket does not call those APIs.**

- [ ] **TODO (later session):** If `DHAN_*` present in `.env`, validate **data** access only (no orders):
  - `python -m desk_intel --live morning`
  - `python -m desk_intel --live poll-chain --interval 3m`
  - Optional: `--live poll-chain --interval 1m` (ATM±N quote path — **not** full chain every minute)
  - Confirm HTTP success, rate-limit gate (chain 1 unique / 3 s), and that `dhan_client.execution` still **refuses** `place_order`
  - If tokens empty: keep dry-run fixtures; do not invent a live chain
- [ ] **TODO (later):** Wire staged-signal **schema** (WATCH/EARLY/…) **and outcomes** (ACHIEVED/STOPPED/INVALIDATED/EXPIRED/LOST/COMPLETED/SHADOW_CLOSED) to `MARKET_SIGNAL` adapter — **after** review. Desk-intel stamps stages/outcomes in paper/shadow; not a live fill. See [`TASK_PRE_POST_MARKET_JOBS.md`](TASK_PRE_POST_MARKET_JOBS.md).
- [ ] **TODO (later):** OHLC 1m/5m compute for Supertrend / RSI / MACD / EMA9 in `packages/indicators` — **only** after math VALIDATION + review. Empty by design today.

**Do not** treat a filled TODO checkbox as a live-trade green light.

---

## Not this ticket

- Live orders, paper fills, backtests, UI color implementation in `apps/web`
- Implementing TA in `packages/indicators` (still empty)
- Calling Conditional Trigger `/alerts/orders`
- Inventing fill prices or resolving “24100 ce” without the user
- Claiming a 1-minute lead as a measured edge

---

## Artifacts

- This file  
- [`PERSONA_DESK.md`](PERSONA_DESK.md)  
- [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)  
- [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../../09_review/docs/MISSED_TRADE_POSTMORTEM.md)
