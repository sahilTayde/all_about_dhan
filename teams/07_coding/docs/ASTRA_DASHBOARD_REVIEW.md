# Astra + desk — customer `/` paper dashboard UX

**Date (UTC):** 2026-09-06  
**Model:** `gpt-6-astra` (`OPENAI_MODEL`; key never logged)  
**Verdict:** `APPROVE_WITH_GUARDRAILS`  
**Raw JSON:** [`data/recon/ASTRA_DASHBOARD_UX_2026-09-06.json`](../../../data/recon/ASTRA_DASHBOARD_UX_2026-09-06.json)  
**Pointer:** [`teams/07_ui/docs/ASTRA_DASHBOARD_REVIEW.md`](../../07_ui/docs/ASTRA_DASHBOARD_REVIEW.md)  
**Customer rules:** [`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md) · [`CUSTOMER_TICKET.md`](../../05_analysis/docs/CUSTOMER_TICKET.md)  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.** Confidence ≠ win rate.

---

## Agreed layout (one job)

| Zone | Job |
|------|-----|
| Hero | One **suggested PAPER ticket** — side, underlying, strike, status, entry / SL / target (premium on ticket) |
| Chart | Underlying **index** path (MOCK OK) + markers; MT5-like via `lightweight-charts` |
| Right rail | Desk confidence % + ≤3 plain “why” bullets; **(i)** = HYPOTHESIS/paper tech detail |
| Below | Today’s **paper** book (MOCK labels) + optional sentiment/CAS (not above ticket) |
| Empty | Exact copy: **WAITING FOR NEXT SIGNAL** — blank ticket values, no fake lean |

Preserve existing dark desk + gold accent. No purple AI cliché. No STRAT / RSI / MACD / Supertrend on the hero.

---

## Honesty status labels (customer surface)

Map engine honesty → display. Display words are the UI source of truth on `/`.

| Engine / lifecycle | Customer label | Notes |
|--------------------|----------------|-------|
| no lean / HOLD / empty window | **WAITING FOR NEXT SIGNAL** | Empty signal window |
| WATCH (lean forming) | **NEW SIGNAL** | Not enterable |
| EARLY | **DO NOT ENTER** | Wait; not a fill |
| VETOED / news hold | **DO NOT ENTER** | Hold ticket, not catalog delete |
| CONFIRMED | **NEW ENTRY** | Eligible suggestion — still not broker fill |
| IN-PROGRESS (levels live) | **IN-PROGRESS** | Path open |
| ACHIEVED | **TARGET HIT** | |
| STOPPED | **STOP LOSS HIT** | |
| INVALIDATED | **INVALIDATED** | |
| EXPIRED (unfilled) | **INVALIDATED** | Filled+expired needs recorded exit |
| LOST (closed, not stop) | **TRADE COMPLETED** | Desk tweak vs Astra default INVALIDATED |
| reconciled close, no better label | **TRADE COMPLETED** | Keep stop/target wording in book when specific |

**Rejected claims:** confidence as future win rate; unlabeled MOCK; premium levels drawn on spot axis; live order buttons.

---

## Chart rules

- Lib: `lightweight-charts` (line or candles on **index points**).
- Markers: CE/PE BUY at signal time; entry/limit, stop, target **only when levels are index-unit**; exit markers when ledger supports.
- Premium SL/target stay on the **ticket**, not plotted as spot prices.
- Always label **MOCK** / **PAPER**. No predicted continuation ray.

---

## Confidence rail

- Hero: `N%` + “PAPER” + plain bullets from eligible playbooks (customer names only).
- Fairness line: agreement score, **not** a win probability.
- **(i)** drawer: HYPOTHESIS / PAPER — technical / liquidity / indicator notes OK here; layered honesty.

---

## Paper book + nightly ledger schema (short)

**UI columns (paper only):** time IST · underlying · side · strike · status · outcome · spot · entry · SL · target · lots (1 PAPER) · points · MOCK/PAPER.

**Summary:** cumulative realized points (PAPER); win% = wins / closed trades (exclude open); never feed confidence.

**Ledger fields for later daily/weekly review** (compatible with `paper_agents` / signal API shape):

```text
signal_id, trade_id, raw_status, displayed_status
signal_at, simulated_fill_at, simulated_exit_at, timezone=Asia/Kolkata
underlying, strike, side, expiry, lot_count=1, mode=PAPER|MOCK
spot_at_entry, entry_premium, stop_premium, target_premium, exit_premium
exit_reason, realized_points, outcome
confidence_score, reason_snapshot, data_as_of, is_mock
```

---

## HANDOFF

```text
HANDOFF
From: 00 + Astra (gpt-6-astra) + 07
To:   07 UI / 05 / 09
Accepted: Single-ticket hero; chart; confidence rail; paper book; status vocabulary; MOCK/PAPER honesty.
Rejected: Sentiment/CAS above ticket; indicator soup on /; confidence as win rate; live orders; premium-on-spot axis.
UNKNOWN: Live OPTIDX premium binding for chart overlays.
```
