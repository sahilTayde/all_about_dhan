# RETUNE_GATE — do not retune the book from nightly recon

**Team:** 06_backtesting (owns the gate) · 02_phd_math (REVIEW only) · 05_analysis (`packages/desk-intel` nightly stub)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Ticket:** [`TASK_RETUNE_GATE.md`](../../00_orchestrator/docs/TASK_RETUNE_GATE.md)  
**Code stub:** `packages/desk-intel` `retune_gate.py` + `nightly.py`  
**PhD packet:** [`teams/02_phd_math/docs/handoffs/README.md`](../../02_phd_math/docs/handoffs/README.md)

Education ≠ advice. **No live orders.** This file does **not** contain backtest results. Do not invent P/L, expectancy, PF, or DD.

---

## Why this exists (pro-trader recon rule)

News days and expiry days make the book look “broken.” Blindly updating Supertrend/MACD/veto knobs (or swapping STRAT-*) from **one nightly recon** overfits that sample. Default: **keep the current strategy**.

Nightly recon is a **learning packet**, not a production writer.

---

## Gate (must all hold)

### 1. Tag the session

Every POST_MARKET recon stamps a session kind from desk-intel **news + calendar** (RSS/official keywords, `CalendarPlaceholder`) and **chain expiry** vs session date:

| Kind | When | Use for retune sample? |
|------|------|------------------------|
| **NEWS_DAY** | Macro print / calendar event (CPI, RBI/MPC, FOMC, GDP, NFP, …) or a real `MACRO_EVENT` **keyword/calendar** hit — not merely a yaml source stamp | **No** |
| **EXPIRY** | Nearest-expiry sheet date **equals** the session date (gamma/pin; `expiry_day` veto) | **No** |
| **NORMAL** | Neither of the above | **Yes** (still not a one-day promote) |

A day can carry **both** `NEWS_DAY` and `EXPIRY` in `session_flags`. Then it is **not** `NORMAL`. 06 excludes any non-`NORMAL` day from the retune sample.

YAML `sources.news[]` often tags feeds `MACRO_EVENT` at the **source** level. Session tagging must use **calendar-style tags / keyword hits / `kind: calendar`**, not “any RSS item from a MACRO_EVENT feed.”

### 2. Candidate change → backtest (this team)

A candidate (knob, indicator param, STRAT mix, SL/target) **must** be backtested here on:

- **Out-of-sample** (not the recon day, not the window that suggested the change)
- **Non-event days** (`NORMAL` only)

Costs, slippage, no look-ahead. Engine **exists** (5y INDEX 1m 2026-09-03) — until a candidate beats current on **OOS + NORMAL**, **nothing promotes**.

### 3. Promote only if

**(a)** The new spec is **more profitable on robust metrics** than the **current** spec on that OOS + `NORMAL` set: expectancy, profit factor, max drawdown — **not** one-day paper/shadow P/L.

**or**

**(b)** A **documented glitch** (lookahead, wrong SL, bug in outcomes/staging) whose **fix** is profitable in the same backtest. A glitch report without a passing backtest is not a promote.

There are **no invented numbers** in this repo for (a) or (b). Empty engine ⇒ no promote.

### 4. Default

**Keep current strategy.** PhD handoff (`NIGHTLY_YYYY-MM-DD.md`) is **REVIEW**, not auto-apply.

---

## Nightly will / will not

| Nightly (`python -m desk_intel nightly`) **will** | Nightly **will not** |
|---------------------------------------------------|----------------------|
| Stamp `session_kind` + `session_flags` | Write new params into `config/workspace.yaml`, `teams/04_quant/docs/candidates/`, or `packages/indicators/` |
| Emit `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED` | Emit `PROMOTED` / `APPLIED` / live knobs |
| Copy existing UNVALIDATED param **hints** into the proposal | Invent backtest metrics or one-day “proof” |
| Keep `keep_current_strategy: true` | Auto-apply suggestions to production or paper live book |
| Hand markdown to 02 as **REVIEW** | Treat 02 as a writer of production params |
| Persist paper ledger + `data/recon/YYYY-MM-DD.json` | Live-trade or rewrite `apps/web` |

---

## `RETUNE_PROPOSAL` (JSON stub)

Nightly payload field `retune_proposal` (schema keys also on `desk_intel.nightly.RECON_JSON_KEYS`):

```text
kind: RETUNE_PROPOSAL
status: BACKTEST_REQUIRED          # nightly only; 06 may later set REJECTED / PROMOTE_CANDIDATE
keep_current_strategy: true
production_params_written: false
handoff: REVIEW                    # 02_phd_math
backtest_owner: 06_backtesting
oos_non_event_required: true
metrics_required: [expectancy, profit_factor, max_drawdown]
one_day_pnl_is_not_evidence: true
backtest_results: null             # never invent
candidate_notes: [...]             # hints only, not new live params
```

06 later statuses (not emitted by nightly): `REJECTED`, `PROMOTE_CANDIDATE` after a real engine run. Promotion into a spec freeze is still 04 + 09 — not this JSON.

---

## Pointers

- Staging: [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)  
- Book: [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md)  
- Jobs: [`TASK_PRE_POST_MARKET_JOBS.md`](../../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md)  
- Event memory (SCORE_SAMPLE vs ANALOG_MEMORY): [`EVENT_MEMORY.md`](EVENT_MEMORY.md) — outliers out of ranking, stored for analog type-match; no invented metrics  
- Smoke: `packages/desk-intel/tests/test_retune_gate.py`
